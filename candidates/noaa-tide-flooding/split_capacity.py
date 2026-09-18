#!/usr/bin/env python3
"""Are there enough positive events in the proposed splits for reliable scoring?

Uses NOAA's own annual flood-day counts (htf_annual, up to 107 years per station) rather
than the hourly reconstruction, so the counts are authoritative and the whole history is
available. Counts positive station-days per year for a candidate station set, then
evaluates a temporal split's train / eval / holdout positive counts.

A rare-event task with a handful of positives cannot support an AUC claim, so the point
of this measurement is to find a station set and split that do.
"""
import json
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

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

SPLITS = [
    ("train", 2006, 2021),
    ("eval", 2022, 2023),
    ("holdout", 2024, 2025),
]


def get(url, attempts=3):
    last = None
    for i in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:120]}"
        except Exception as e:  # noqa: BLE001
            last = repr(e)
    raise RuntimeError(last)


def main():
    per_station_year = {}
    per_station_year_mod = {}
    print("Fetching NOAA authoritative annual flood-day counts")
    for sid, name in STATIONS:
        ann = get(f"{BASE}/htf/htf_annual.json?station={sid}")
        entries = ann.get("AnnualFloodCount") or []
        years = {}
        mods = {}
        for e in entries:
            try:
                y = int(e.get("year"))
            except (TypeError, ValueError):
                continue
            if e.get("minCount") is None:
                continue
            years[y] = int(e["minCount"])
            mods[y] = int(e.get("modCount") or 0)
        per_station_year[name] = years
        per_station_year_mod[name] = mods
        span = f"{min(years)}-{max(years)}" if years else "none"
        print(f"  {name:<24} years={len(years):>3} span={span:<10} "
              f"2025={years.get(2025, 'n/a')}")

    all_years = sorted({y for d in per_station_year.values() for y in d})
    print()
    print("Total minor-flood days per year across all 12 stations")
    yearly = defaultdict(int)
    for years in per_station_year.values():
        for y, n in years.items():
            yearly[y] += n
    for y in all_years:
        if y >= 2005:
            print(f"  {y}: {yearly[y]:>4}")

    print()
    print("Proposed temporal split, positive station-days and base rates")
    print(f"{'split':<9} {'years':<12} {'station-days':>13} {'positives':>10} {'rate':>8} "
          f"{'mod+':>6}")
    print("-" * 66)
    summary = []
    for label, y0, y1 in SPLITS:
        span_years = list(range(y0, y1 + 1))
        stations_with_data = 0
        days = 0
        pos = 0
        modplus = 0
        for name, years in per_station_year.items():
            have = [y for y in span_years if y in years]
            if not have:
                continue
            stations_with_data += 1
            days += 365 * len(have)
            pos += sum(years[y] for y in have)
            modplus += sum(per_station_year_mod[name][y] for y in have)
        rate = pos / days if days else 0.0
        print(f"{label:<9} {y0}-{y1:<8} {days:>13} {pos:>10} {rate:>8.4f} {modplus:>6}")
        summary.append({"split": label, "years": f"{y0}-{y1}",
                        "stations_with_data": stations_with_data,
                        "station_days": days, "positive_days": pos,
                        "exceedance_rate": round(rate, 6),
                        "moderate_or_worse_days": modplus})

    print()
    print("Same, restricted to the six most active stations "
          "(Sewells Point, Honolulu, The Battery, Sandy Hook, Charleston, Atlantic City)")
    active = ["Sewells Point, VA", "Honolulu, HI", "The Battery, NY",
              "Sandy Hook, NJ", "Charleston, SC", "Atlantic City, NJ"]
    print(f"{'split':<9} {'years':<12} {'station-days':>13} {'positives':>10} {'rate':>8}")
    print("-" * 60)
    for label, y0, y1 in SPLITS:
        span_years = list(range(y0, y1 + 1))
        days = 0
        pos = 0
        for name in active:
            years = per_station_year[name]
            have = [y for y in span_years if y in years]
            days += 365 * len(have)
            pos += sum(years[y] for y in have)
        print(f"{label:<9} {y0}-{y1:<8} {days:>13} {pos:>10} "
              f"{(pos / days if days else 0):>8.4f}")

    out = Path(__file__).with_name("split_capacity_result.json")
    out.write_text(json.dumps({
        "question": "Do the proposed evaluation splits contain enough positive events?",
        "source": f"{BASE}/htf/htf_annual.json (minCount / modCount), the authoritative product",
        "station_set": [n for _, n in STATIONS],
        "total_flood_days_per_year_all_stations": {str(k): v for k, v in sorted(yearly.items())},
        "splits": summary,
        "measured_on": "2026-09-18",
    }, indent=1) + "\n")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
