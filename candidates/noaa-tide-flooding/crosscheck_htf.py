#!/usr/bin/env python3
"""Cross-check the computed 2025 base rates against NOAA's own historical product.

`htf_daily.json` is NOAA's High Tide Flooding daily record: for each station it reports
DailyFloodCount, the number of days that exceeded the minor threshold, with NOAA doing
its own datum handling. If my STND reconstruction is right, my 2025 per-station counts
should match NOAA's, and my MLLW reconstruction should match nothing.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

UA = {"User-Agent": "scout-dataset-factory/0.1 (bounded research probe)"}
BASE = "https://api.tidesandcurrents.noaa.gov/dpapi/prod/webapi"

STATIONS = [
    ("8418150", "Portland, ME"),
    ("8443970", "Boston, MA"),
    ("8518750", "The Battery, NY"),
    ("8531680", "Sandy Hook, NJ"),
    ("8534720", "Atlantic City, NJ"),
    ("8638610", "Sewells Point, VA"),
    ("8665530", "Charleston, SC"),
    ("8724580", "Key West, FL"),
    ("8771450", "Galveston Pier 21, TX"),
    ("9414290", "San Francisco, CA"),
    ("9447130", "Seattle, WA"),
    ("1612340", "Honolulu, HI"),
]

# What my own datum=STND reconstruction produced for 2025 (see noaa_rates_stnd.txt).
MINE_STND = {
    "8418150": 0, "8443970": 2, "8518750": 7, "8531680": 7, "8534720": 4,
    "8638610": 17, "8665530": 7, "8724580": 0, "8771450": 4, "9414290": 0,
    "9447130": 0, "1612340": 12,
}
# And what the rejected MLLW comparison produced for the same station-year.
MINE_MLLW = {sid: 0 for sid, _ in STATIONS}


def get(url, attempts=3):
    last = None
    for i in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:120]}"
        except Exception as e:  # noqa: BLE001
            last = repr(e)
    raise RuntimeError(last)


print("NOAA htf_daily, 2025-01-01..2025-12-31, versus my reconstruction")
print()
print(f"{'station':<24} {'id':<9} {'NOAA':>5} {'mine STND':>10} {'match':>6} {'mine MLLW':>10}")
print("-" * 72)

noaa_total = stnd_total = mllw_total = 0
rows = []
for sid, name in STATIONS:
    url = (f"{BASE}/htf/htf_daily.json?" +
           urllib.parse.urlencode({"station": sid, "start_date": "20250101", "end_date": "20251231"}))
    data = get(url)
    noaa = int(data.get("count") or 0)
    detail = data.get("DailyFloodCount")
    mine_s = MINE_STND[sid]
    mine_m = MINE_MLLW[sid]
    noaa_total += noaa
    stnd_total += mine_s
    mllw_total += mine_m
    print(f"{name:<24} {sid:<9} {noaa:>5} {mine_s:>10} {str(noaa == mine_s):>6} {mine_m:>10}")
    rows.append({"station": name, "id": sid, "noaa_2025_flood_days": noaa,
                 "mine_stnd_flood_days": mine_s, "mine_mllw_flood_days": mine_m,
                 "stnd_matches_noaa": noaa == mine_s, "units": data.get("units")})

print("-" * 72)
print(f"{'TOTAL':<24} {'':<9} {noaa_total:>5} {stnd_total:>10} "
      f"{str(noaa_total == stnd_total):>6} {mllw_total:>10}")
print()
print("NOAA units field:", rows[0]["units"] if rows else "?")
print()
print("Annual counts (htf_annual.json) for the same stations:")
for sid, name in STATIONS:
    try:
        ann = get(f"{BASE}/htf/htf_annual.json?station={sid}")
    except RuntimeError as e:
        print(f"  {name:<24} {e}")
        continue
    entries = ann.get("AnnualFloodCount") or []
    y2025 = [e for e in entries if str(e.get("year")) == "2025"]
    print(f"  {name:<24} years={len(entries)} 2025={json.dumps(y2025[0]) if y2025 else 'n/a'}")

print()
print("JSON:")
print(json.dumps(rows, indent=1))
