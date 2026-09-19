#!/usr/bin/env python3
"""Build the NOAA tide-flooding task from NOAA's verified daily maxima.

Target: does a station's daily maximum observed water level exceed that station's published NOS
*minor* flood threshold on the following local day?

Two contract-complete levels are emitted from one row set, because the runner's contract is one
task (`task.json` + `data/train.csv` + `data/eval.csv` + a private holdout) with one eval set:

  * `temporal`          - all 122 stations, train 2006-2021, eval 2022-2023, holdout 2024-2025.
  * `station_disjoint`  - the station holdout (group0, by station-id order) is never in training;
                          train on group1+group2, eval on group0 2022-2023, holdout on group0 2024-2025.

Source route: `product=daily_max_min`, `interval=6`, `datum=STND`, `time_zone=GMT`, one request per
station-year (~2,440 requests, ~178 MB for 122 stations x 20 years). Verified maxima with a
completeness percentage, not preliminary rows, and not the 29,160-request raw-series route.

Datum matters: the published `nos_minor` threshold is in the station datum (STND). Comparing an
MLLW series against it rejects Boston's record 2018 tide, which is how the trap was found.

Features are observations only and station-relative, and every one of them uses data up to the
previous local day - station statistics come from *trailing* windows, so the future cannot leak into
a row. NOAA tide predictions and model guidance are deliberately excluded: they are not
observations, and including them is the way an agent defeats the task.

  python3 build.py --probe 8443970 --year 2024      # one station-year, parses and prints rows
  python3 build.py --out <dir> [--stations N]       # the build (intended for a worker)
"""

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
UA = {"User-Agent": "scout-dataset-factory/0.1 (bounded research build)"}
YEARS = list(range(2006, 2026))
TRAIN_YEARS = (2006, 2021)
EVAL_YEARS = (2022, 2023)
HOLDOUT_YEARS = (2024, 2025)
LOOKBACK = 30           # trailing window for station-relative scale
FLOOD_WINDOW = 7        # trailing window for recent exceedance count

FEATURES = ["margin_ft", "margin_ratio", "trailing7_mean", "trailing30_mean", "trailing30_std",
            "exceed_last7", "days_since_exceedance", "day_of_year", "latitude", "threshold_rank"]
COLUMNS = ["station_id", "station_name", "date", "latitude", "longitude", "threshold_ft"] + FEATURES + ["observed_max_ft", "late"]


def fetch_json(url, attempts=3, timeout=120):
    last = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode())
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed after {attempts} attempts: {last}")


def daily_maxima(station_id, year):
    """One request: a whole station-year of 6-minute daily maxima, verified, with completeness."""
    url = (f"{API}?begin_date={year}0101&end_date={year}1231&station={station_id}"
           f"&product=daily_max_min&interval=6&datum=STND&time_zone=GMT&units=english"
           f"&application=dataset-factory&format=json")
    payload = fetch_json(url)
    block = (payload.get("data") or [{}])[0]
    out = {}
    for row in block.get("dailyMax6Min") or []:
        # The product answers an ISO date ("2024-01-01"); YYYYMMDD is accepted defensively. A
        # length-8 digit check here silently dropped all 366 rows, so both forms are parsed.
        raw = str(row.get("date6Min") or "").strip()
        if len(raw) == 8 and raw.isdigit():
            raw = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
        if len(raw) != 10 or raw[4] != "-" or raw[7] != "-":
            continue
        value = row.get("value6Min")
        if value in (None, "", "null"):
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        try:
            complete = float(row.get("pcComplete6Min"))
        except (TypeError, ValueError):
            complete = None
        out[raw] = {"max_ft": value, "complete_pct": complete,
                    "flag": str(row.get("flag6Min") or "")}
    return out


def flood_days(station_id, year):
    """NOAA's own minor-flood days for the station-year, one request per station-year.

    Measured against the annual product on four stations for 2024: these flags match NOAA's counts
    exactly (25/26/23/20 = 94), where a reconstruction from 6-minute daily maxima gave 113-114 and
    an hourly reconstruction 98. The label is therefore the publisher's own determination rather
    than a competing definition of ours.
    """
    url = (f"https://api.tidesandcurrents.noaa.gov/dpapi/prod/webapi/htf/htf_daily.json"
           f"?station={station_id}&start_date={year}0101&end_date={year}1231")
    payload = fetch_json(url)
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


def station_metadata(station_ids):
    """Published thresholds and coordinates. nos_minor is the label's threshold - kept physical."""
    url = ("https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json"
           "?type=waterlevels&expand=floodlevels")
    payload = fetch_json(url)
    wanted = {str(s) for s in station_ids}
    meta = {}
    for station in payload.get("stations") or []:
        station_id = str(station.get("id"))
        if station_id not in wanted:
            continue
        flood = station.get("floodlevels") or {}
        minor = flood.get("nos_minor")
        if isinstance(minor, dict):
            minor = minor.get("nos_minor")
        if not isinstance(minor, (int, float)):
            continue
        meta[station_id] = {"name": station.get("name"), "state": station.get("state"),
                            "latitude": station.get("lat"), "longitude": station.get("lng"),
                            "threshold_ft": float(minor)}
    return meta


def frozen_stations():
    data = json.loads((HERE / "station_list_result.json").read_text())
    return [str(station["id"]) for station in data["frozen_station_list"]["stations"]]


def group_of(station_id, order):
    """The recorded rule: sort by station id, every third station is the station holdout (group0)."""
    return order.index(station_id) % 3


def features_for(series, threshold, latitude, threshold_rank):
    """Station-relative features from trailing data only. `series` is date-ordered observations."""
    rows = []
    maxima = [point["max_ft"] for point in series]
    for index, point in enumerate(series):
        if index < LOOKBACK:                            # no trailing window yet: drop, do not guess
            continue
        previous = maxima[index - 1]
        window30 = maxima[index - LOOKBACK:index]
        window7 = maxima[index - 7:index]
        mean30 = sum(window30) / len(window30)
        mean7 = sum(window7) / len(window7)
        variance = sum((value - mean30) ** 2 for value in window30) / len(window30)
        exceed_last7 = sum(1 for value in window7 if value > threshold)
        days_since = None
        for back in range(1, LOOKBACK + 1):
            if maxima[index - back] > threshold:
                days_since = back - 1
                break
        if days_since is None:
            days_since = LOOKBACK                        # censored: "at least LOOKBACK days"
        day = date.fromisoformat(point["date"])
        rows.append({
            "station_id": point["station_id"],
            "station_name": point["station_name"],
            "date": point["date"],
            "latitude": latitude,
            "longitude": point["longitude"],
            "threshold_ft": threshold,
            "margin_ft": round(previous - threshold, 4),
            "margin_ratio": round(previous / threshold, 6) if threshold else None,
            "trailing7_mean": round(mean7, 4),
            "trailing30_mean": round(mean30, 4),
            "trailing30_std": round(variance ** 0.5, 4),
            "exceed_last7": exceed_last7,
            "days_since_exceedance": days_since,
            "day_of_year": day.timetuple().tm_yday,
            "threshold_rank": threshold_rank,
            "observed_max_ft": point["max_ft"],
            "label_date": (day + timedelta(days=1)).isoformat(),
        })
    return rows


def build(out_dir, limit=None, years=None):
    stations = frozen_stations()
    order = sorted(stations)
    meta = station_metadata(stations)
    thresholds = sorted(entry["threshold_ft"] for entry in meta.values())
    rows_by_station = {}
    station_days = {}
    quality = {}
    requests = 0
    errors = []
    targets = stations[:limit] if limit else stations
    for station_id in targets:
        info = meta.get(station_id)
        if not info:
            errors.append({"station": station_id, "error": "no published numeric nos_minor"})
            continue
        series = []
        flood = set()
        for year in (years or YEARS):
            try:
                maxima = daily_maxima(station_id, year)
                flags = flood_days(station_id, year)
                requests += 2
            except RuntimeError as exc:
                errors.append({"station": station_id, "year": year, "error": str(exc)[:160]})
                continue
            flood |= flags
            for day, value in sorted(maxima.items()):
                # Incomplete days are kept and counted. Dropping them would quietly delete positive
                # days, so the count is reported instead and the sensitivity is measured separately.
                series.append({"station_id": station_id, "station_name": info["name"], "date": day,
                               "max_ft": value["max_ft"], "longitude": info["longitude"],
                               "complete_pct": value["complete_pct"], "flag": value["flag"]})
        series.sort(key=lambda point: point["date"])
        incomplete = [point for point in series
                      if point["complete_pct"] is not None and point["complete_pct"] < 100]
        flagged = [point for point in series if point["flag"] not in ("", "0")]
        quality.setdefault(station_id, {"days": len(series), "incomplete_days": len(incomplete),
                                        "incomplete_above_threshold":
                                            sum(1 for point in incomplete
                                                if point["max_ft"] > info["threshold_ft"]),
                                        "flagged_days": len(flagged)})
        rank = (thresholds.index(info["threshold_ft"]) + 1) / len(thresholds)
        for row in features_for(series, info["threshold_ft"], info["latitude"], round(rank, 5)):
            rows_by_station.setdefault(station_id, []).append(row)
        # The publisher's flood days for this station, kept beside its rows for the labelling step.
        station_days.setdefault(station_id, set()).update(flood)
        print(f"  {station_id} {info['name'][:28]:28} {len(series):5} days", flush=True)

    # Attach the next-day label from the same station's series, then split.
    labelled = []
    for station_id, rows in rows_by_station.items():
        flags = station_days.get(station_id, set())
        for row in rows:
            # The label is the publisher's flag for the *next* local day. A row whose next day is
            # outside the fetched window is dropped rather than labelled from nothing.
            if not (row["label_date"][:4].isdigit() and int(row["label_date"][:4]) in YEARS):
                continue
            row = dict(row)
            row["late"] = 1 if row["label_date"] in flags else 0
            row.pop("label_date")
            labelled.append(row)

    levels = {}
    temporal = {"train": [], "eval": [], "holdout": []}
    station_disjoint = {"train": [], "eval": [], "holdout": []}
    for row in labelled:
        year = int(row["date"][:4])
        group = group_of(row["station_id"], order)
        if TRAIN_YEARS[0] <= year <= TRAIN_YEARS[1]:
            temporal["train"].append(row)
            if group != 0:
                station_disjoint["train"].append(row)
        elif EVAL_YEARS[0] <= year <= EVAL_YEARS[1]:
            temporal["eval"].append(row)
            if group == 0:
                station_disjoint["eval"].append(row)
        elif HOLDOUT_YEARS[0] <= year <= HOLDOUT_YEARS[1]:
            temporal["holdout"].append(row)
            if group == 0:
                station_disjoint["holdout"].append(row)
    levels["temporal"] = temporal
    levels["station_disjoint"] = station_disjoint

    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"stations": len(rows_by_station), "requests": requests, "errors": errors,
               "label_source": "NOAA HTF daily product, minFlag (the publisher's own minor-flood "
                               "days), one request per station-year; features come from "
                               "daily_max_min observations",
               "requests_per_station_year": 2,
               "levels": {}, "features": FEATURES, "columns": COLUMNS,
               "day_quality": {
                   "days": sum(v["days"] for v in quality.values()),
                   "incomplete_days": sum(v["incomplete_days"] for v in quality.values()),
                   "incomplete_days_above_threshold":
                       sum(v["incomplete_above_threshold"] for v in quality.values()),
                   "flagged_days": sum(v["flagged_days"] for v in quality.values()),
                   "rule": "incomplete days are kept; the label uses the reported maximum. The "
                           "counts are reported so the choice is visible rather than silent."}}
    for level, splits in levels.items():
        summary["levels"][level] = {}
        for split, rows in splits.items():
            rows.sort(key=lambda row: (row["station_id"], row["date"]))
            path = out_dir / f"{level}.{split}.csv"
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=COLUMNS)
                writer.writeheader()
                writer.writerows(rows)
            positives = sum(row["late"] for row in rows)
            summary["levels"][level][split] = {
                "rows": len(rows), "positives": positives,
                "rate": round(positives / len(rows), 5) if rows else None,
                "stations": len({row["station_id"] for row in rows}),
                "path": path.name,
            }
    (out_dir / "build_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["levels"], indent=2))
    return summary


def probe(station_id, year):
    info = station_metadata([station_id]).get(str(station_id))
    if not info:
        sys.exit(f"no published nos_minor for {station_id}")
    maxima = daily_maxima(station_id, year)
    print(f"{station_id} {info['name']}: {len(maxima)} days returned for {year}, "
          f"threshold {info['threshold_ft']} ft STND, lat {info['latitude']}")
    days = sorted(maxima.items())
    print("  first:", days[0], "last:", days[-1])
    above = [day for day, value in days if value["max_ft"] > info["threshold_ft"]]
    print(f"  days above the minor threshold: {len(above)} {above[:6]}")
    series = [{"station_id": str(station_id), "station_name": info["name"], "date": day,
               "max_ft": value["max_ft"], "longitude": info["longitude"]} for day, value in days]
    rows = features_for(series, info["threshold_ft"], info["latitude"], 0.5)
    print(f"  feature rows from one station-year: {len(rows)}")
    if rows:
        print("  sample:", json.dumps(rows[-1], indent=None)[:400])
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--limit", type=int, help="first N frozen stations, for a bounded run")
    parser.add_argument("--probe", help="one station id: fetch one year and print parsed rows")
    parser.add_argument("--year", type=int, default=2024, help="year for --probe")
    parser.add_argument("--years", help="comma-separated years, e.g. 2024,2025")
    args = parser.parse_args()
    if args.probe:
        return probe(args.probe, args.year)
    if not args.out:
        raise SystemExit("--out is required for a build (or use --probe)")
    years = [int(y) for y in args.years.split(",")] if args.years else None
    build(args.out, limit=args.limit, years=years)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())