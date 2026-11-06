#!/usr/bin/env python3
"""Decisive reconciliation probe (2026-11-06): re-fetch TWO months with the
exact request shape of probe_cpcb_full_window_2026_11_05.py and the build, and
compare the deduped (station, day) counts with that probe's recorded per_month
totals. 4 requests, anonymous, counts only - no labels, no score."""
import csv
import io
import json
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://airquality.xkdr.org"
KEY = "aqi_demo_wbf92Qx21zX-Wa_Tg8Dx1nXe"
HDRS = {"Authorization": "Bearer " + KEY,
        "User-Agent": "Mozilla/5.0 (dataset-factory-cpcb-probe/1.0)"}
OUT = Path(__file__).resolve().parent / "out" / "reconcile_two_months_2026_11_06.json"
STATIONS = Path(__file__).resolve().parent / "out" / "xkdr_stations_2026_11_04.json"
MONTHS = {"2019-01": ("2019-01-01", "2019-01-31"),
          "2025-08": ("2025-08-01", "2025-08-31")}


def main() -> int:
    doc = json.loads(STATIONS.read_text())
    data = doc.get("data", doc)
    if isinstance(data, dict):
        data = data.get("data", [])
    cpcb = [s for s in data if s.get("source") == "cpcb_caaqm"
            and "PM2.5" in (s.get("parameters") or [])]
    batches = [cpcb[i:i + 275] for i in range(0, len(cpcb), 275)]
    result = {"method": ("same request shape as the 2026-11-05 panel probe and the build: "
                         "parameter=PM2.5&agg=daily&format=csv, 275-station batches, "
                         "counts deduped per (station, day)"),
              "months": {}}
    for month, (start, end) in MONTHS.items():
        seen = set()
        requests = 0
        for batch in batches:
            params = [("parameter", "PM2.5"), ("agg", "daily"), ("start", start),
                      ("end", end), ("format", "csv")]
            for s in batch:
                params.append(("station", s["station_id"]))
            url = BASE + "/v1/measurements?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(url, headers=HDRS)
            with urllib.request.urlopen(req, timeout=120) as response:
                body = response.read()
                truncated = str(response.headers.get("X-Truncated", "")).lower()
                row_count = response.headers.get("X-Row-Count")
            requests += 1
            n_rows = 0
            for row in csv.DictReader(io.StringIO(body.decode("utf-8", "replace"))):
                seen.add((row["station_id"], row["period_start"][:10]))
                n_rows += 1
            print(f"{month} batch rows={n_rows} x_truncated={truncated!r} "
                  f"x_row_count={row_count}", flush=True)
        result["months"][month] = {"station_days_deduped": len(seen),
                                   "requests": requests}
    recorded = json.loads((Path(__file__).resolve().parent / "out" /
                           "xkdr_daily_counts_2019_2025_2026_11_05.json").read_text())
    for month in MONTHS:
        result["months"][month]["recorded_2026_11_05"] = \
            recorded["per_month"].get(month, {}).get("station_days")
        result["months"][month]["delta"] = (
            result["months"][month]["station_days_deduped"]
            - (result["months"][month]["recorded_2026_11_05"] or 0))
    OUT.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result["months"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
