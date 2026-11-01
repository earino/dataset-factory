#!/usr/bin/env python3
"""Probe 1/2 for za-cct-substation-evening-peak-exceedance (retained recipe).

Full scan + streaming reduce of the CCT Switching Substation Load Profile
table: paged anonymous REST fetch (53 x 1,000 rows), reduced in flight to
per-station-day day-peak / evening-peak (16:00-22:00 SAST) aggregates.
Measures requests, bytes, wall clock, gap structure, per-column null counts.
No raw table is stored. Run: python3 probe_fullscan.py [output.json]"""

import datetime
import json
import sys
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "scout-probe/1.0"}
BASE = ("https://services6.arcgis.com/nyYfO9SxHU2ChQd9/arcgis/rest/services/"
        "Switching_Substation_Load_Profile/FeatureServer/0")
SAST = datetime.timezone(datetime.timedelta(hours=2))
OUT = sys.argv[1] if len(sys.argv) > 1 else "loadprofile_reduce.json"

info = json.load(urllib.request.urlopen(
    urllib.request.Request(BASE + "?f=json", headers=UA), timeout=60))
DBL = [f["name"] for f in info["fields"] if f["type"] == "esriFieldTypeDouble"]
STR = [f["name"] for f in info["fields"] if f["type"] == "esriFieldTypeString"]
ALL = ["Timestamp"] + DBL + STR

non_null = {c: 0 for c in DBL}
string_vals = {c: set() for c in STR}
day_peak, eve_peak, day_rows = {}, {}, {}
ts_first, ts_last = None, None
n_req, n_bytes = 0, 0
t0 = time.time()
page = 0
while True:
    u = (f"{BASE}/query?where=1%3D1&outFields={urllib.parse.quote(','.join(ALL))}"
         f"&orderByFields=ObjectId&resultOffset={page * 1000}&resultRecordCount=1000&f=json")
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120) as r:
        raw = r.read()
    n_req += 1
    n_bytes += len(raw)
    feats = json.loads(raw).get("features", [])
    if not feats:
        break
    for f in feats:
        a = f["attributes"]
        ts = a.get("Timestamp")
        if ts is None:
            continue
        dt = datetime.datetime.fromtimestamp(ts / 1000, tz=SAST)
        day = dt.strftime("%Y-%m-%d")
        ts_first, ts_last = ts_first or dt, dt
        day_rows[day] = day_rows.get(day, 0) + 1
        for c in DBL:
            v = a.get(c)
            if v is not None:
                non_null[c] += 1
                k = (day, c)
                if v > day_peak.get(k, float("-inf")):
                    day_peak[k] = v
                if 16 <= dt.hour < 22 and v > eve_peak.get(k, float("-inf")):
                    eve_peak[k] = v
        for c in STR:
            v = a.get(c)
            if v is not None and len(string_vals[c]) < 30:
                string_vals[c].add(str(v))
    page += 1

elapsed = time.time() - t0
days = sorted(day_rows)
bad = {d: n for d, n in day_rows.items() if n != 48}
print(f"requests={n_req} bytes={n_bytes} wall_clock_s={elapsed:.1f}")
print(f"days={len(days)} first={days[0]} last={days[-1]} bad_days={bad}")
print(f"ts range {ts_first} .. {ts_last}")
print(f"non-null min/max: {min(non_null.values())}/{max(non_null.values())}")
print(f"strings: { {c: sorted(v)[:4] for c, v in string_vals.items()} }")
json.dump({
    "fetched_at": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
    "requests": n_req, "bytes": n_bytes, "wall_clock_s": round(elapsed, 1),
    "ts_first": str(ts_first), "ts_last": str(ts_last), "days": days,
    "bad_days": bad, "non_null": non_null,
    "string_vals": {c: sorted(v) for c, v in string_vals.items()},
    "day_peak": {f"{d}|{c}": v for (d, c), v in day_peak.items()},
    "eve_peak": {f"{d}|{c}": v for (d, c), v in eve_peak.items()},
}, open(OUT, "w"))
print(f"reduced aggregates -> {OUT}")
