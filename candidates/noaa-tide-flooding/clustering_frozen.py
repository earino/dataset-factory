#!/usr/bin/env python3
"""Clustered event counts for the frozen station list.

The annual product gives positive station-days, but flood days cluster at several stations at
once, so the independent-event count is what confidence intervals must use. NOAA's HTF daily
product lists the individual flood days per station; one request per station covers a multi-year
range, and the distinct calendar days across stations are the independent events.

Reads the frozen list written by .factory/noaa_station_list.py. Train is deliberately not
measured: 16 years of daily rows per station, over 122 stations, is not worth the request budget
to quote a number the eval and holdout splits already carry.
"""
import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

UA = {"User-Agent": "scout-dataset-factory/0.1 (bounded research probe)"}
DPAPI = "https://api.tidesandcurrents.noaa.gov/dpapi/prod/webapi"
RESULT = Path(__file__).with_name("station_list_result.json")
SPLITS = [("train", 2006, 2021), ("eval", 2022, 2023), ("holdout", 2024, 2025)]


def fetch(url, attempts=3, timeout=120):
    last = None
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:120]}"
        except Exception as exc:  # noqa: BLE001
            last = repr(exc)[:120]
    raise RuntimeError(last)


def days_for(station_id, year):
    payload = json.loads(fetch(f"{DPAPI}/htf/htf_daily.json?station={station_id}"
                               f"&start_date={year}0101&end_date={year}1231"))
    out = set()
    for row in payload.get("DailyFloodCount") or []:
        if str(row.get("minFlag")) not in ("1", "1.0"):
            continue
        raw = str(row.get("day") or "")
        if "/" in raw:
            month, day, year_part = raw.split("/")
            raw = f"{year_part}-{month}-{day}"
        out.add(raw[:10])
    return out


def main():
    result = json.loads(RESULT.read_text())
    frozen = result["frozen_station_list"]["stations"]
    print(f"frozen stations: {len(frozen)}")
    clustering = {}
    for label, y0, y1 in SPLITS:
        if label == "train":
            clustering[label] = {
                "measured": False,
                "reason": "skipped: 16 years of daily rows per station x 122 stations; the eval "
                          "and holdout splits are the ones a score is quoted from",
            }
            print(f"  {label}: not measured (recorded as unmeasured, not guessed)")
            continue

        def one(entry):
            try:
                found = set()
                for year in range(y0, y1 + 1):
                    found |= days_for(entry["id"], year)
                return entry["id"], found, None
            except Exception as exc:  # noqa: BLE001
                return entry["id"], set(), repr(exc)[:120]

        per_day = {}
        errors = []
        with ThreadPoolExecutor(max_workers=6) as pool:
            for sid, days, error in pool.map(one, frozen):
                if error:
                    errors.append({"station": sid, "error": error})
                    continue
                for day in days:
                    per_day.setdefault(day, []).append(sid)
        positives = sum(len(v) for v in per_day.values())
        busiest = max(per_day.values(), key=len) if per_day else []
        clustering[label] = {
            "measured": True, "years": f"{y0}-{y1}",
            "positive_station_days": positives,
            "distinct_flood_days": len(per_day),
            "mean_stations_per_flood_day": round(positives / len(per_day), 2) if per_day else None,
            "busiest_day": max(per_day, key=lambda d: len(per_day[d])) if per_day else None,
            "busiest_day_stations": len(busiest),
            "stations_reporting": len(frozen) - len(errors),
            "errors": errors,
        }
        print(f"  {label}: {positives} positive station-days, {len(per_day)} distinct flood days, "
              f"mean {clustering[label]['mean_stations_per_flood_day']}/day, "
              f"busiest {len(busiest)} stations"
              + (f", {len(errors)} errors" if errors else ""))

    result["clustering_measured"] = clustering
    result["clustering_note"] = ("Independent-event counts for the splits a score is quoted from, "
                                "recomputed over the frozen station list from NOAA's own HTF "
                                "daily product (hft/daily.json, field 'day' with minFlag).")
    RESULT.write_text(json.dumps(result, indent=1) + "\n")
    print("wrote", RESULT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
