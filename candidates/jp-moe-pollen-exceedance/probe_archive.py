#!/usr/bin/env python3
"""Bounded discovery probe: MOE Hanako-san pollen archive (env.go.jp).

Answers, from the coordinator, anonymously and cheaply:
  1. Archive structure: which (year, region, file) pairs exist for the two
     download blocks (pollen data / AMEDAS data)?
  2. Sample schema: parse one region-season pollen file (2021 Kanto):
     layout, stations, hourly-row count, season span, missing-value codes.
  3. National 2021 enumeration: 7 pollen-region files - bytes, request
     count, wall clock, station-count estimate (conservative heuristic).
  4. Full-extraction arithmetic from the measured sample (labelled estimate).

Writes evidence JSON next to this script. ~8 HTTP requests, ~2 MB total.
"""
import io
import json
import re
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) dataset-factory-discovery/1.0"}
BASE = "https://www.env.go.jp"
ARCHIVE = BASE + "/page_00209.html"
OUT = Path(__file__).parent / "evidence_2026-10-28.json"

SUFFIX = ["測定局", "センター", "研究所", "役所", "庁舎", "保健所", "大学", "消防本部",
          "支所", "事務所", "庁", "気象台", "病院", "公所"]


def get(url, timeout=90, limit=None):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read(limit) if limit else r.read()


def parse_xlsx(data):
    z = zipfile.ZipFile(io.BytesIO(data))
    ss = z.read("xl/sharedStrings.xml").decode("utf-8", "replace")
    strings = re.findall(r"<t[^>]*>(.*?)</t>", ss, re.S)
    sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8", "replace")
    rows = []
    for rm in re.finditer(r"<row[^>]*>(.*?)</row>", sheet, re.S):
        cells = []
        for cm in re.finditer(r"<c\b[^>]*>(.*?)</c>", rm.group(1), re.S):
            tag, body = cm.group(0), cm.group(1)
            vm = re.search(r"<v>(.*?)</v>", body, re.S)
            val = vm.group(1) if vm else None
            if 't="s"' in tag and val is not None:
                try:
                    val = strings[int(val)]
                except ValueError:
                    pass
            cells.append(val)
        rows.append(cells)
    return rows


def main():
    ev = {"probe_date": "2026-10-28", "requests": 0}

    # 1. archive structure
    st, body = get(ARCHIVE)
    ev["requests"] += 1
    text = body.decode("utf-8", "replace")
    ev["archive_page"] = {"status": st, "bytes": len(body), "title":
                          (re.search(r"<title[^>]*>(.*?)</title>", text, re.S) or [None, "?"])[1]}
    # split page at the two download-block headings
    pollen_seg = text[text.find("〈花粉データ〉"): text.find("〈アメダスデータ〉")]
    amedas_seg = text[text.find("〈アメダスデータ〉"):]
    def files_of(seg):
        out = {}
        year = None
        # walk tokens in order: a year label, then region links
        for m in re.finditer(r'(20\d\d)年|href="(/content/\d+\.(?:xlsx|xls))"[^>]*>([^<]{2,12})<', seg):
            if m.group(1):
                year = m.group(1)
            else:
                out.setdefault(year, []).append(
                    {"region": m.group(3).strip(), "url": BASE + m.group(2)})
        return out
    pol = files_of(pollen_seg)
    ame = files_of(amedas_seg)
    ev["pollen_block"] = {y: len(v) for y, v in sorted(pol.items())}
    ev["amedas_block"] = {y: len(v) for y, v in sorted(ame.items())}
    ev["pollen_files_total"] = sum(len(v) for v in pol.values())
    ev["amedas_files_total"] = sum(len(v) for v in ame.values())

    # 2. sample schema: 2021 Kanto
    kanto_url = next(f["url"] for f in pol["2021"] if "関東" in f["region"])
    st, body2 = get(kanto_url)
    ev["requests"] += 1
    rows = parse_xlsx(body2)
    hdr = rows[1]  # row 2 = station names
    stations = [c for c in hdr if c and 6 <= len(c) <= 30 and any(x in c[-7:] for x in SUFFIX)]
    codes = [c for c in hdr if c and "欠測" in c]
    ev["kanto_2021"] = {
        "url": kanto_url, "status": st, "bytes": len(body2),
        "sheet_rows_total": len(rows),
        "hourly_data_rows": len(rows) - 2,
        "stations_in_header_est": len(stations),
        "station_names_sample": stations[:22],
        "missing_value_codes": codes,
        "first_data_row": rows[2][:6],
        "last_data_row": rows[-1][:6],
        "span_days_est": round((len(rows) - 2) / 24, 1),
    }

    # 3. national 2021 enumeration
    t0 = time.time()
    nat = {}
    total_bytes = 0
    station_total = 0
    for f in pol["2021"]:
        try:
            st, body3 = get(f["url"])
            ev["requests"] += 1
            total_bytes += len(body3)
            z = zipfile.ZipFile(io.BytesIO(body3))
            ss = z.read("xl/sharedStrings.xml").decode("utf-8", "replace")
            strs = re.findall(r"<t[^>]*>(.*?)</t>", ss, re.S)
            stn = sorted(set(s for s in strs if 6 <= len(s) <= 30
                             and any(x in s[-7:] for x in SUFFIX)
                             and "欠測" not in s and "データ" not in s))
            nat[f["region"]] = {"bytes": len(body3), "stations_est": len(stn)}
            station_total += len(stn)
        except Exception as e:
            nat[f["region"]] = {"error": repr(e)[:150]}
    ev["national_2021_pollen"] = {
        "requests": 7, "total_bytes": total_bytes,
        "wall_clock_s": round(time.time() - t0, 2),
        "stations_est_total_conservative": station_total,
        "note": "literature (Kawatsu et al 2019 PMC6685964, NBER w31593) says the "
                "network reached ~120 sites nationally; the suffix heuristic undercounts",
        "per_region": nat,
    }

    # 4. extraction arithmetic from the measured sample (ESTIMATE, labelled)
    seasons_full = len([y for y in pol if len(pol[y]) >= 7 and int(y) >= 2008])
    bytes_per_season = total_bytes
    ev["extraction_cost"] = {
        "measured_one_season_pollen": {
            "requests": 7, "bytes": total_bytes,
            "wall_clock_s": ev["national_2021_pollen"]["wall_clock_s"]},
        "estimate_full_panel": {
            "note": "arithmetic from the measured 2021 season, labelled ESTIMATE",
            "seasons_with_7_regions": seasons_full,
            "pollen_files": ev["pollen_files_total"],
            "amedas_files": ev["amedas_files_total"],
            "est_requests": ev["pollen_files_total"] + ev["amedas_files_total"],
            "est_bytes": round((ev["pollen_files_total"] + ev["amedas_files_total"])
                               * (bytes_per_season / 7)),
        },
    }

    OUT.write_text(json.dumps(ev, ensure_ascii=False, indent=1))
    print(f"wrote {OUT}")
    print(json.dumps({k: ev[k] for k in ("pollen_block", "amedas_block",
                                         "pollen_files_total", "amedas_files_total",
                                         "kanto_2021", "national_2021_pollen",
                                         "extraction_cost", "requests")},
                     ensure_ascii=False, indent=1)[:3500])


if __name__ == "__main__":
    sys.exit(main())
