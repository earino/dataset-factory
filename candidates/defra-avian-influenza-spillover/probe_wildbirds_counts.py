#!/usr/bin/env python3
"""Discovery probe: measure the APHA wild-bird HPAI findings files (per-year
CSVs on gov.uk) as a feature panel: schemas, row counts, county/week coverage
per calendar year, and total positive birds.

The 2024 and 2025 files are XLSX and are only recorded (not parsed here);
CSV years 2020-2023 and the current 2026 file are fetched and counted.

Writes probe_wildbirds_result.json next to this script.

    python3 candidates/defra-avian-influenza-spillover/probe_wildbirds_counts.py
"""

import csv
import datetime as dt
import io
import json
import re
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "probe_wildbirds_result.json"

FILES = {
    "2026": "https://assets.publishing.service.gov.uk/media/6ae49bfd3d3bf10d23546209/Avian_influenza_in_wild_birds_for_week_44_2026.csv",
    "2023": "https://assets.publishing.service.gov.uk/media/659d5598aa18b1000da199e8/ai-findings-2023.csv",
    "2022": "https://assets.publishing.service.gov.uk/media/63d915ccd3bf7f25288c158a/ai-findings-2022.csv",
    "2021": "https://assets.publishing.service.gov.uk/media/61d725f58fa8f505953f4ed1/ai-findings-2021.csv",
    "2020": "https://assets.publishing.service.gov.uk/media/5ff49169d3bf7f65d9e357bd/ai-findings-2020.csv",
    "2018": "https://assets.publishing.service.gov.uk/media/5c53126540f0b62545d8ca0c/ai-findings-2018.csv",
    "2016-17": "https://assets.publishing.service.gov.uk/media/5a82c66040f0b6230269ca2c/ai-findings-1617.csv",
}
XLSX_ONLY = {
    "2025": "https://assets.publishing.service.gov.uk/media/695d199c34c664251c38a109/Avian_Influenza_in_wild_birds_findings_2025_.xlsx",
    "2024": "https://assets.publishing.service.gov.uk/media/67727b88743b5171e596ac6d/Avian_Influenza_in_wild_birds_findings_2024_-_Week_52.xlsx",
}

WEEK_RE = re.compile(r"(\d+)\s*\((\d{4})\)")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "dataset-factory-discovery/1.0"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    return data, time.time() - t0


def main():
    t_start = time.time()
    result = {
        "probed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "publication_page": "https://www.gov.uk/government/publications/avian-influenza-in-wild-birds",
        "files": {},
        "xlsx_only_note": (
            "2024 and 2025 findings files are XLSX (67.5 KB and 16.6 KB): recorded, not parsed "
            "on the coordinator; parse on the worker if this candidate advances."
        ),
    }
    total_requests = 0
    for year, url in FILES.items():
        data, elapsed = fetch(url)
        total_requests += 1
        text = data.decode("utf-8", "replace")
        reader = csv.DictReader(io.StringIO(text))
        rows = [
            {(k or "").strip(): (v or "") for k, v in r.items()} for r in reader
        ]
        header = [k.strip() for k in (reader.fieldnames or [])]
        schema = "county-country-normalized" if header and header[0].startswith("Week (Year)") else (
            "county-normalized-2023" if header and header[0] == "Week" else (
                "location-legacy" if header and header[0].lstrip("\ufeff").startswith("Week number") else "unknown"
            )
        )
        counties, weeks = set(), set()
        pos_col = None
        for cand in ("Total (Positive)", "Total number of birds testing positive", "Total"):
            if cand in header:
                pos_col = cand
                break
        loc_col = None
        for cand in ("County", "Location", "Location (county)"):
            if cand in header:
                loc_col = cand
                break
        total_pos = 0
        n_pos_rows = 0
        for r in rows:
            wk = WEEK_RE.search((r.get(header[0]) or "").strip())
            if wk:
                weeks.add(wk.group(0))
            loc = (r.get(loc_col) or "").strip() if loc_col else ""
            if loc:
                counties.add(loc)
            if pos_col:
                try:
                    v = int(float(r[pos_col]))
                    total_pos += v
                    n_pos_rows += 1
                except (ValueError, TypeError):
                    pass
        result["files"][year] = {
            "url": url,
            "bytes": len(data),
            "fetch_seconds": round(elapsed, 2),
            "schema": schema,
            "header": header,
            "rows": len(rows),
            "distinct_weeks": len(weeks),
            "distinct_locations": len(counties),
            "positive_birds_total": total_pos,
            "rows_with_positive_count": n_pos_rows,
        }
        print(year, "->", len(rows), "rows,", len(counties), "locations, schema", schema)
        time.sleep(0.3)
    result["total_requests"] = total_requests
    result["wall_seconds"] = round(time.time() - t_start, 1)
    OUT.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    print("DONE ->", OUT.name)


if __name__ == "__main__":
    main()
