#!/usr/bin/env python3
"""Probe ABS OAD_COUNTRY (dataflow ABS,OAD_COUNTRY,1.0.0) end to end.

Re-runnable discovery probe for abs-visitor-arrivals-direction. Fetches:
  1. the dataflow structure with references (codelists: traveller category, country,
     series type), and
  2. the full monthly panel 1991-01.. as CSV,
then prints the panel shape, MoM/YoY direction base rates per year, and split-window
class counts for the candidate partition (train 1991-2014 / eval 2015-2019 /
holdout 2022-2026).

Usage: python3 candidates/abs-visitor-arrivals-direction/probe_oad_country.py
"""
import csv
import io
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone

BASE = "https://data.api.abs.gov.au/rest"


def fetch(url, timeout=180):
    req = urllib.request.Request(url, headers={"User-Agent": "scout-factory-probe/1.0"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    return data, len(data), time.time() - t0


print(f"probe start {datetime.now(timezone.utc).isoformat()}")

# --- structure + codelists ---
data, nbytes, secs = fetch(f"{BASE}/dataflow/ABS/OAD_COUNTRY?references=all")
print(f"STRUCT bytes={nbytes} secs={secs:.2f}")
root = ET.fromstring(data)
wanted = {"CL_OAD_CAT_TRAVEL", "CL_OAD_ARRIVALS_COUNTRY", "CL_TSEST"}
for cl in root.iter():
    if cl.tag.split("}")[-1] != "Codelist" or cl.get("id") not in wanted:
        continue
    codes = {}
    for code in cl:
        if code.tag.split("}")[-1] != "Code":
            continue
        for ch in code:
            if ch.tag.split("}")[-1] == "Name":
                codes[code.get("id")] = (ch.text or "").strip()
    print(f"codelist {cl.get('id')}: {len(codes)} codes, sample "
          f"{dict(list(codes.items())[:3])}")

# --- full panel ---
data, nbytes, secs = fetch(f"{BASE}/data/ABS,OAD_COUNTRY,1.0.0/all?format=csv&startPeriod=1991-01")
print(f"DATA bytes={nbytes} secs={secs:.2f}")
rows = list(csv.DictReader(io.StringIO(data.decode("utf-8"))))
months = sorted({r["TIME_PERIOD"] for r in rows})
print(f"obs rows={len(rows)} months={len(months)} range={months[0]}..{months[-1]}")
print(f"CAT_TRAVELLER={sorted({r['CAT_TRAVELLER'] for r in rows})} "
      f"TSEST={sorted({r['TSEST'] for r in rows})} "
      f"countries={len({r['COUNTRY_RESID'] for r in rows})} "
      f"missing={sum(1 for r in rows if r['OBS_VALUE'].strip() == '')}")

series = defaultdict(dict)
for r in rows:
    if r["OBS_VALUE"].strip():
        series[(r["CAT_TRAVELLER"], r["COUNTRY_RESID"])][r["TIME_PERIOD"]] = float(r["OBS_VALUE"])


def sign(x):
    return 1 if x > 0 else (0 if x < 0 else None)


mom = defaultdict(lambda: [0, 0, 0])
yoy = defaultdict(lambda: [0, 0, 0])
for key, s in series.items():
    keys = sorted(s)
    for prev, cur in zip(keys, keys[1:]):
        py, cy = int(prev[5:7]), int(cur[5:7])
        if cy == py + 1 or (py == 12 and cy == 1):
            d = sign(s[cur] - s[prev])
            if d is not None:
                mom[cur[:4]][d] += 1
    for k in keys:
        prev_y = f"{int(k[:4]) - 1}-{k[5:7]}"
        if prev_y in s:
            d = sign(s[k] - s[prev_y])
            if d is not None:
                yoy[k[:4]][d] += 1

for year in sorted(yoy):
    m, v = mom.get(year, [0, 0, 0]), yoy[year]
    print(f"{year}  MoM up/down {m[1]}/{m[0]}  YoY up/down {v[1]}/{v[0]}")

WINDOWS = {"train": ("1991", "2014"), "eval": ("2015", "2019"), "holdout": ("2022", "2026")}
for name, (y0, y1) in WINDOWS.items():
    up = down = 0
    for key, s in series.items():
        for k, val in s.items():
            y = k[:4]
            if y0 <= y <= y1:
                prev_y = f"{int(y) - 1}-{k[5:7]}"
                if prev_y in s:
                    d = sign(val - s[prev_y])
                    up += d == 1
                    down += d == 0
    print(f"window {name} {y0}-{y1}: up={up} down={down}")
print(f"probe end {datetime.now(timezone.utc).isoformat()}")
