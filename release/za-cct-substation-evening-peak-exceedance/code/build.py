#!/usr/bin/env python3
"""Construction of the za-cct-substation-evening-peak-exceedance artifact (za-cct-001).

Task: for a Cape Town switching substation (33/66/132kV), at 06:00 SAST on day
D, predict whether the evening peak load (max half-hourly MVA over 16:00-22:00
SAST) will exceed the station's trailing-90-evening p95 (min 30 prior evenings).

P0-safe feature design (the reason this shape was chosen before any build):
the label's operands are the day-D evening readings and the trailing-evening
p95. The record's cross-row concern ("a later same-station row's feature window
contains this row's evening label operand" - the abs-visitor-arrivals shape)
became a hard rule after the 2026-11-01 queue audit and the fts-appeal-003
rebuild: NO sliding quantile over evening values may ship, because its
day-over-day delta reconstructs the entering value's exceedance almost exactly
([p95(D+1) > p95(D)] equals [eve(D) > p95(D)] except for top-tail window swaps),
which is label-blind exact recovery - the operator's automatic DO-NOT-PUBLISH
class. Therefore:

  * no evening reading, evening peak, or evening-derived aggregate ships in any
    split file; the evening matrix is sealed into auxiliary/evening_peaks.csv
    (staging-side verification input, never a solver-visible frame);
  * the trailing-evening p95 threshold itself does NOT ship: the model predicts
    exceedance of an unseen threshold from identity, calendar, same-morning
    telemetry and a MORNING-history regime mean;
  * the only history-derived shipped column is hist_morningpeak_mean_90, the
    mean of the trailing <= 90 prior days' morning peaks (min 30). Morning
    telemetry is never a label operand, and the same delta attack on a mean
    recovers only [morning_peak(D) > trailing morning mean] - a ~50%-base-rate
    event, far from the ~9% evening label. The gate's cross-row probe
    (quality.json evaluation_contract.cross_row_audit.probes[0]) executes
    exactly that attack over the full artifact and records coverage and
    mismatches.

This file ONLY constructs files and gate diagnostics. It computes no
performance metric (no AUC, no accuracy, no model): row and positive counts,
fixture assertions and exclusion buckets are construction diagnostics. The
first performance number in the job is computed by score.py, which run.sh
allows to run only after the qualification gate passed over the full artifact
and --accept re-verified the exact bytes. The holdout is never opened by
score.py.

Worker order (run.sh): construct -> qualify -> accept exact bytes -> references.

Harvest (anonymous, stdlib): paged FeatureServer reads of the City of Cape
Town Switching Substation Load Profile table (item bebf20c25bfa4ffaa7fc07a1a94ba287),
Timestamp + the 41 double-typed substation columns only (Triangle_132kV is
string-typed and empty, Morgen_Gronde_132kV is string-typed numeric-as-text;
both are excluded so the panel reproduces the measured discovery counts
exactly - their exclusion is recorded, not silent). Every fetched page is
pinned by sha256 in summary.json; the ArcGIS item metadata (created/modified,
static-window evidence) is recorded as vintage evidence. Raw pages stay in the
job work-dir and are not uploaded (per-page digests are the evidence; the
item is static since 2026-03 so a re-fetch reproduces).

Acceptance criteria asserted in-build against the discovery measurements
(probe_fullscan.py / probe_cluster.py, 2026-11-01, commands in notes.md):
  * 52,608 half-hour rows = 1,096 gapless days x 48, 2022-01-01 00:00 ..
    2024-12-31 23:30 SAST; 41 double stations, 52,608/52,608 non-null;
  * labels by year exactly 1,539/13,735 (2022), 1,256/14,965 (2023),
    1,382/15,006 (2024); distinct exceedance days 227/246/247; 41/41
    stations with >= 1 positive every year;
  * dated fixture Grassy_Park_66kV 2024-07-15: evening peak 150.38 >
    trailing p95 146.82 -> label 1 (raw values asserted to the printed
    rounding); monthly mean evening peaks 2022-08 60.3, 2022-12 48.0,
    2023-07 60.6, 2023-12 45.9, 2024-07 61.9, 2024-12 44.1 MVA.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

NAME = "za-cct-substation-evening-peak-exceedance"
TARGET = "exceeds"
POSITIVE = 1
POSITIVE_LABEL_TEXT = ("evening peak (max half-hourly MVA over 16:00-22:00 SAST) "
                       "exceeds the station's trailing-90-evening p95")
ID_COLUMNS = ["station_day"]
TIME_COLUMN = "date"
EVENT_KEY_COLUMN = "date"

BASE = ("https://services6.arcgis.com/nyYfO9SxHU2ChQd9/arcgis/rest/services/"
        "Switching_Substation_Load_Profile/FeatureServer/0")
ITEM_URL = ("https://www.arcgis.com/sharing/rest/content/items/"
            "bebf20c25bfa4ffaa7fc07a1a94ba287?f=json")
SAST = datetime.timezone(datetime.timedelta(hours=2))  # Africa/Johannesburg, no DST
UA = {"User-Agent": "scout-factory-construction/1.0"}

MIN_PRIOR_EVENINGS = 30       # eligibility: >= 30 prior evenings for the p95
TRAILING_EVENINGS = 90        # the label threshold window (matches probe_cluster.py)
TRAILING_MORNING_DAYS = 90    # the morning-history window (parallel rule)
PAGE_ROWS = 1000

# Discovery measurements (candidates/.../notes.md, probe_fullscan.py + probe_cluster.py)
EXPECTED_TOTAL_ROWS = 52_608
EXPECTED_DAYS = 1_096
EXPECTED_STATIONS = 41
EXPECTED_LABEL_COUNTS = {"2022": (1_539, 13_735), "2023": (1_256, 14_965),
                         "2024": (1_382, 15_006)}
EXPECTED_DISTINCT_DAYS = {"2022": 227, "2023": 246, "2024": 247}
FIXTURE_STATION, FIXTURE_DATE = "Grassy_Park_66kV", "2024-07-15"
FIXTURE_PEAK = (150.375, 150.385)   # probe printed 150.38 at 2dp
FIXTURE_P95 = (146.815, 146.825)   # probe printed 146.82 at 2dp
MONTHLY_MEAN_FIXTURES = {"2022-08": 60.3, "2022-12": 48.0, "2023-07": 60.6,
                         "2023-12": 45.9, "2024-07": 61.9, "2024-12": 44.1}

SPLIT_WINDOWS = {
    "train": {"start": "2022-01-01", "end": "2023-01-01"},   # end exclusive
    "eval": {"start": "2023-01-01", "end": "2024-01-01"},
    "holdout": {"start": "2024-01-01", "end": "2025-01-01"},
}
EXPECTED_SPLIT_YEARS = (2022, 2023, 2024)   # asserted on the real harvest
SPLIT_NAMES = ("train", "eval", "holdout")

MORNING_COLS = [f"m{h:02d}_{m:02d}" for h in range(0, 6) for m in (0, 30)]
# one column list, in one place (the fts lesson: never compose it twice)
COLUMNS = (["station_day", "station", "date",
            "day_of_week", "day_of_year", "doy_sin", "doy_cos", "month"]
           + MORNING_COLS
           + ["morning_mean", "morning_max", "morning_min",
              "hist_morningpeak_mean_90", TARGET])
FEATURES = [c for c in COLUMNS if c not in ID_COLUMNS + [TARGET]]


class BuildError(RuntimeError):
    pass


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch_bytes(url: str, tries: int = 4) -> bytes:
    last = None
    for attempt in range(tries):
        try:
            request = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except Exception as exc:  # noqa: BLE001 - retried transport errors
            last = exc
            time.sleep(2 ** attempt)
    raise BuildError(f"fetch failed after {tries} tries: {url}: {last}")


def fetch_json(url: str, tries: int = 4):
    return json.loads(fetch_bytes(url, tries))


def harvest(work: Path, stats: dict) -> list[Path]:
    """Paged anonymous read of the whole table; each page pinned to disk."""
    work.mkdir(parents=True, exist_ok=True)
    info = fetch_json(f"{BASE}?f=json")
    double_fields = [f["name"] for f in info["fields"]
                     if f["type"] == "esriFieldTypeDouble"]
    if len(double_fields) != EXPECTED_STATIONS:
        raise BuildError(f"layer now exposes {len(double_fields)} double-typed "
                         f"fields, expected {EXPECTED_STATIONS}: the source "
                         f"schema moved; diagnose before building")
    item = fetch_json(ITEM_URL)
    stats["layer"] = {
        "service_item_id": info.get("serviceItemId"),
        "name": info.get("name"),
        "double_fields": double_fields,
        "object_count_field": bool(info.get("supportsPagination")),
    }
    stats["item"] = {"id": item.get("id"), "title": item.get("title"),
                     "created": item.get("created"),
                     "modified": item.get("modified"),
                     "access": item.get("access"),
                     "size": item.get("size")}
    out_fields = ",".join(["Timestamp"] + double_fields)
    pages, page, n_req, n_bytes = [], 0, 0, 0
    while True:
        query = urllib.parse.urlencode({
            "where": "1=1", "outFields": out_fields, "orderByFields": "ObjectId",
            "resultOffset": page * PAGE_ROWS, "resultRecordCount": PAGE_ROWS,
            "f": "json"})
        raw = fetch_bytes(f"{BASE}/query?{query}")
        n_req += 1
        n_bytes += len(raw)
        path = work / f"page-{page:03d}.json"
        path.write_bytes(raw)
        pages.append(path)
        if not json.loads(raw).get("features"):
            break
        page += 1
    stats["fetch"] = {"requests": n_req, "bytes": n_bytes,
                     "pages": len(pages),
                     "page_sha256": {p.name: sha256_of(p) for p in pages}}
    return pages


def load_pages(pages: list[Path]) -> tuple[list[dict], list[str]]:
    """Read the fetched pages into raw attribute rows (Timestamp + stations)."""
    rows, stations = [], []
    for path in pages:
        payload = json.loads(path.read_text())
        for feature in payload.get("features", []):
            rows.append(feature.get("attributes") or {})
    for key in (rows[0] if rows else {}):
        if key not in ("Timestamp", "ObjectId"):
            stations.append(key)
    return rows, sorted(stations)


def build_panel(rows: list[dict], stations: list[str], stats: dict,
                real_fixtures: bool) -> list[dict]:
    """Station-day panel rows in a deterministic (station, date) order.

    The label arithmetic replicates probe_cluster.py exactly: trailing <= 90
    prior evenings (min 30), p95 = sorted(history)[int(0.95 * (n - 1))],
    label = evening_peak > p95 on raw unrounded values.
    """
    morning = defaultdict(dict)      # (station, day) -> {slot: value}
    evening_peak = defaultdict(dict)  # (station, day) -> {"v": max evening value}
    day_rows = defaultdict(int)
    ts_first = ts_last = None
    for attributes in rows:
        ts = attributes.get("Timestamp")
        if ts is None:
            continue
        dt = datetime.datetime.fromtimestamp(ts / 1000, tz=SAST)
        day = dt.strftime("%Y-%m-%d")
        ts_first = ts_first or dt
        ts_last = dt
        day_rows[day] += 1
        for station in stations:
            value = attributes.get(station)
            if value is None:
                continue
            if dt.hour < 6:
                slot = f"m{dt.hour:02d}_{dt.minute:02d}"
                morning[(station, day)][slot] = value
            elif 16 <= dt.hour < 22:
                peak = evening_peak[(station, day)]
                if value > peak.get("v", float("-inf")):
                    peak["v"] = value

    days = sorted(day_rows)
    stats["grid"] = {
        "raw_rows": len(rows),
        "days": len(days),
        "first_day": days[0] if days else None,
        "last_day": days[-1] if days else None,
        "ts_first": str(ts_first), "ts_last": str(ts_last),
        "bad_days": {d: n for d, n in day_rows.items() if n != 48},
        "stations": len(stations),
    }
    if real_fixtures:
        if len(rows) != EXPECTED_TOTAL_ROWS:
            raise BuildError(f"fetched {len(rows)} rows, expected "
                             f"{EXPECTED_TOTAL_ROWS}: the live table moved")
        if len(days) != EXPECTED_DAYS or stats["grid"]["bad_days"]:
            raise BuildError(f"grid is not 1,096 gapless days: {stats['grid']}")

    # per-station day series (all days carry morning slots and an evening peak;
    # a missing slot or peak is a construction defect, never silently skipped)
    for (station, day), slots in morning.items():
        if len(slots) != len(MORNING_COLS):
            raise BuildError(f"{station} {day} has {len(slots)} morning readings, "
                             f"expected {len(MORNING_COLS)}")
        if evening_peak.get((station, day), {}).get("v") is None:
            raise BuildError(f"{station} {day} has no evening peak reading")

    series = defaultdict(list)
    for (station, day), peak in evening_peak.items():
        series[station].append((day, peak["v"], morning[(station, day)]))

    panel = []
    burn_in = 0
    monthly_peaks = defaultdict(list)
    for station in stations:
        vals = sorted(series[station])
        for i, (day, peak, slots) in enumerate(vals):
            hist = [v for _, v, _ in vals[max(0, i - TRAILING_EVENINGS):i]]
            year = day[:4]
            monthly_peaks[day[:7]].append(peak)
            if len(hist) < MIN_PRIOR_EVENINGS:
                burn_in += 1
                continue
            ordered = sorted(hist)
            p95 = ordered[int(0.95 * (len(ordered) - 1))]
            morning_values = [slots[c] for c in MORNING_COLS]
            morning_max = max(morning_values)
            prior_morning_peaks = [
                max(vals[j][2][c] for c in MORNING_COLS)
                for j in range(max(0, i - TRAILING_MORNING_DAYS), i)]
            if len(prior_morning_peaks) < MIN_PRIOR_EVENINGS:
                raise BuildError(f"{station} {day}: morning history shorter than "
                                 f"the evening history - the parallel-window "
                                 f"invariant broke")
            date = datetime.date.fromisoformat(day)
            doy = date.timetuple().tm_yday
            panel.append({
                "station_day": f"{station}|{day}",
                "station": station,
                "date": day,
                "day_of_week": str(date.weekday()),
                "day_of_year": str(doy),
                "doy_sin": f"{math.sin(2 * math.pi * (doy - 1) / 365.25):.6f}",
                "doy_cos": f"{math.cos(2 * math.pi * (doy - 1) / 365.25):.6f}",
                "month": str(date.month),
                **{c: f"{slots[c]:.3f}" for c in MORNING_COLS},
                "morning_mean": f"{sum(morning_values) / len(morning_values):.3f}",
                "morning_max": f"{morning_max:.3f}",
                "morning_min": f"{min(morning_values):.3f}",
                "hist_morningpeak_mean_90": f"{sum(prior_morning_peaks) / len(prior_morning_peaks):.3f}",
                "_evening_peak_raw": peak,
                "_trailing_p95_raw": p95,
                "_year": year,
                TARGET: "1" if peak > p95 else "0",
            })
    panel.sort(key=lambda row: (row["station"], row["date"]))
    stats["exclusions"] = {
        "burn_in_under_30_prior_evenings": burn_in,
        "note": ("burn-in station-days (the first 30 days of each station's "
                 "series) lack the 30 prior evenings the p95 needs; they are "
                 "counted here, never scored as negatives"),
    }
    stats["monthly_mean_evening_peak_mva"] = {
        month: round(sum(v) / len(v), 4) for month, v in sorted(monthly_peaks.items())}
    return panel


def check_fixtures(panel: list[dict], stats: dict) -> None:
    """Assert the discovery measurements on the real harvest (counts + fixtures)."""
    by_year = defaultdict(lambda: [0, 0])
    distinct_days = defaultdict(set)
    per_station_year = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for row in panel:
        year = row["_year"]
        positive = row[TARGET] == "1"
        by_year[year][1] += 1
        per_station_year[row["station"]][year][1] += 1
        if positive:
            by_year[year][0] += 1
            distinct_days[year].add(row["date"])
            per_station_year[row["station"]][year][0] += 1
    stats["labels_by_year"] = {y: {"positives": p, "rows": t,
                                   "distinct_days": len(distinct_days[y])}
                               for y, (p, t) in sorted(by_year.items())}
    for year, (positives, rows) in EXPECTED_LABEL_COUNTS.items():
        if (by_year[year][0], by_year[year][1]) != (positives, rows):
            raise BuildError(f"{year}: built {by_year[year]} vs measured "
                             f"({positives} positives / {rows} rows) - the live "
                             f"table drifted from the 2026-11-01 harvest")
    for year, expected in EXPECTED_DISTINCT_DAYS.items():
        if len(distinct_days[year]) != expected:
            raise BuildError(f"{year}: {len(distinct_days[year])} distinct "
                             f"exceedance days, measured {expected}")
    good = sum(1 for s in per_station_year
               if all(per_station_year[s].get(y, [0, 0])[0] > 0
                      for y in ("2022", "2023", "2024")))
    if good != EXPECTED_STATIONS:
        raise BuildError(f"{good} stations with a positive in every year, "
                         f"measured {EXPECTED_STATIONS}")

    fixture = next((r for r in panel if r["station"] == FIXTURE_STATION
                    and r["date"] == FIXTURE_DATE), None)
    if fixture is None:
        raise BuildError("dated fixture row missing from the panel")
    peak, p95 = fixture["_evening_peak_raw"], fixture["_trailing_p95_raw"]
    if not (FIXTURE_PEAK[0] <= peak < FIXTURE_PEAK[1]):
        raise BuildError(f"fixture evening peak {peak} outside the measured "
                         f"rounding of 150.38")
    if not (FIXTURE_P95[0] <= p95 < FIXTURE_P95[1]):
        raise BuildError(f"fixture trailing p95 {p95} outside the measured "
                         f"rounding of 146.82")
    if fixture[TARGET] != "1":
        raise BuildError("dated fixture must be a positive (150.38 > 146.82)")
    for month, expected in MONTHLY_MEAN_FIXTURES.items():
        actual = stats["monthly_mean_evening_peak_mva"].get(month)
        if actual is None or abs(actual - expected) > 0.05:
            raise BuildError(f"monthly mean evening peak {month}: {actual} vs "
                             f"measured {expected} MVA")
    stats["fixtures"] = {
        "dated_example": {"station": FIXTURE_STATION, "date": FIXTURE_DATE,
                          "evening_peak_mva": round(peak, 4),
                          "trailing_p95_mva": round(p95, 4), "label": 1},
        "monthly_means_asserted": MONTHLY_MEAN_FIXTURES,
        "labels_match_discovery_measurement": True,
    }


def split_rows(panel: list[dict]) -> tuple[dict[str, list[dict]], list[int]]:
    """Split by target-day year: the earliest year trains, the next evaluates,
    the last is the holdout. Exactly three years are expected; the real harvest
    must be 2022/2023/2024 (asserted by the caller under --real-fixtures)."""
    years = sorted({int(row["date"][:4]) for row in panel})
    if len(years) != 3:
        raise BuildError(f"expected exactly three target-day years, found {years}")
    splits = {name: [] for name in SPLIT_NAMES}
    for row in panel:
        year = int(row["date"][:4])
        splits[SPLIT_NAMES[years.index(year)]].append(row)
    return splits, years


def write_artifact(out: Path, splits: dict[str, list[dict]], built_at: str,
                   years: list[int]) -> dict:
    (out / "public").mkdir(parents=True, exist_ok=True)
    (out / "private").mkdir(parents=True, exist_ok=True)
    (out / "auxiliary").mkdir(parents=True, exist_ok=True)

    shipped = [c for c in COLUMNS]  # the single ordered column list
    stats_by_split = {}
    for name, rows in splits.items():
        if not rows:
            raise BuildError(f"split {name} is empty; the panel cannot carry a score")
        seen = set()
        for row in rows:
            if row["station_day"] in seen:
                raise BuildError(f"duplicate id within {name}: {row['station_day']}")
            seen.add(row["station_day"])
        positives = sum(1 for row in rows if row[TARGET] == str(POSITIVE))
        stats_by_split[name] = {
            "rows": len(rows), "positives": positives,
            "negatives": len(rows) - positives,
            "positive_rate": round(positives / len(rows), 6),
            "stations": len({row["station"] for row in rows}),
        }

    destinations = {"train": "public/train.csv", "eval": "public/eval.csv",
                    "holdout": "private/holdout.csv"}
    for name, relative in destinations.items():
        with (out / relative).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=shipped,
                                    extrasaction="ignore", lineterminator="\n")
            writer.writeheader()
            for row in splits[name]:
                writer.writerow({column: row[column] for column in shipped})

    # sealed evening matrix: every station-day with an evening peak, the label
    # operands (raw values), the computed threshold and the scored flag. This is
    # a staging-side verification input only - never a solver-visible frame.
    all_rows = sorted((row for rows in splits.values() for row in rows),
                      key=lambda row: (row["station"], row["date"]))
    with (out / "auxiliary" / "evening_peaks.csv").open(
            "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["station", "date", "evening_peak_mva",
                         "trailing_evening_p95_mva", "scored", "exceeds"])
        # burn-in station-days are not in the panel (their p95 window is not yet
        # 30 evenings deep); the aux matrix therefore lists the scored rows,
        # and the burn-in count is recorded in summary.json exclusions
        for row in all_rows:
            writer.writerow([row["station"], row["date"],
                             f"{row['_evening_peak_raw']:.4f}",
                             f"{row['_trailing_p95_raw']:.4f}",
                             "1", row[TARGET]])

    meta = {
        "name": NAME,
        "description": (
            "For a Cape Town switching substation (33/66/132kV), at 06:00 SAST "
            "on day D, will the evening peak load (maximum half-hourly MVA over "
            "16:00-22:00 SAST) exceed the station's trailing-90-evening p95 "
            "(minimum 30 prior evenings)? Features are the station identity, the "
            "calendar, the same-day 00:00-06:00 half-hourly readings and the "
            "mean of the trailing <= 90 prior days' morning peaks. No "
            "evening-derived value ships: evening readings, evening peaks and "
            "the trailing-evening p95 threshold are sealed outside the artifact "
            "(a sliding evening quantile's day-over-day delta reconstructs "
            "labels - the fts-appeal-003 P0 lesson), so the model predicts "
            "exceedance of a threshold it never sees. A useful prediction at "
            "06:00 lets the distribution desk flag evenings that will stress a "
            "substation before the evening ramp, in a city whose publisher "
            "notes readings are not corrected for load shifts."),
        "target": TARGET,
        "positive_label": POSITIVE,
        "positive_label_text": POSITIVE_LABEL_TEXT,
        "id_columns": ID_COLUMNS,
        "columns": shipped,
        "rows": {name: stats_by_split[name]["rows"] for name in stats_by_split},
        "positive_rate": {name: stats_by_split[name]["positive_rate"]
                          for name in stats_by_split},
        "split": (f"temporal on the target day: train {years[0]}, eval "
                  f"{years[1]}, holdout {years[2]}"),
        "split_description": (
            f"temporal on the target day (Africa/Johannesburg): train "
            f"{years[0]}, eval {years[1]}, holdout {years[2]}; the first 30 "
            "days of each station's series are burn-in (no 30 prior evenings "
            "for the p95) and are excluded, counted, never scored"),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1, sort_keys=True) + "\n",
                                   encoding="utf-8")
    return stats_by_split


def morning_group(status="assumed"):
    return {
        "source": ("the station's own same-day 00:00-06:00 SAST half-hourly "
                   "readings in the City of Cape Town Switching Substation "
                   "Load Profile table (item bebf20c25bfa4ffaa7fc07a1a94ba287)"),
        "availability": ("within the artifact's closed 2022-2024 window every "
                         "half-hour slot ending at or before 06:00 SAST on the "
                         "target day is complete at the instant (gapless grid "
                         "asserted: 48 half-hours every day, 41 stations "
                         "non-null); real-world availability at historical "
                         "instants is unverified because the publisher "
                         "exposes only the current closed window"),
        "status": status,
        "assumption": ("current-snapshot vintage: values are the single "
                       "static table published 2026-02..03 (item created "
                       "2026-02-28, modified 2026-03-02, read pinned by "
                       "per-page sha256 in summary.json); no historical "
                       "vintages exist to prove availability at past instants"),
    }


def build_quality(stats_by_split: dict, harvest_stats: dict, built_at: str,
                  years: list[int]) -> dict:
    morning = morning_group()
    fe = {
        "station_day": {
            "source": "row key <station>|<date>; the identity of one "
                      "station-day",
            "availability": "identity of the row, complete at the instant",
            "status": "verified"},
        "station": {
            "source": "the substation's column name in the City's Switching "
                      "Substation Load Profile table (one of the 41 "
                      "double-typed 33/66/132kV switching stations)",
            "availability": "fixed attribute of the telemetry column; known "
                            "at the instant",
            "status": "verified"},
        "date": {
            "source": "the target day (Africa/Johannesburg, UTC+2, no DST)",
            "availability": "calendar identity of the row; known at the instant",
            "status": "verified"},
        "day_of_week": {
            "source": "derived from date (0 = Monday)",
            "availability": "calendar; known at the instant", "status": "verified"},
        "day_of_year": {
            "source": "derived from date (ordinal 1-366)",
            "availability": "calendar; known at the instant", "status": "verified"},
        "doy_sin": {
            "source": "cyclical encoding sin(2*pi*(day_of_year-1)/365.25)",
            "availability": "calendar; known at the instant", "status": "verified"},
        "doy_cos": {
            "source": "cyclical encoding cos(2*pi*(day_of_year-1)/365.25)",
            "availability": "calendar; known at the instant", "status": "verified"},
        "month": {
            "source": "calendar month derived from date",
            "availability": "calendar; known at the instant", "status": "verified"},
        "hist_morningpeak_mean_90": {
            "source": ("mean of the daily maximum 00:00-06:00 reading over the "
                       "trailing <= 90 prior days (>= 30 required, the same "
                       "eligibility rule as the label's evening window)"),
            "availability": ("every window member day ends strictly before the "
                             "instant (the latest member is D-1, whose morning "
                             "window closed at 06:00 SAST on D-1)"),
            "status": "assumed",
            "assumption": morning["assumption"],
        },
    }
    for column in MORNING_COLS:
        fe[column] = {**morning,
                       "source": morning["source"] + f" -> {column}: the "
                       f"{column[1:].replace('_', ':')} half-hour slot of the target day"}
    for column in ("morning_mean", "morning_max", "morning_min"):
        fe[column] = {**morning,
                      "source": morning["source"] + f" -> {column}: the "
                      f"{column.split('_')[1]} of the target day's 12 morning "
                      "slots"}

    measurements = [
        {"column": column,
         "unit": "megavolt-amperes (MVA) as published",
         "frame": "half-hourly substation load reading, SAST grid; publisher "
                  "caveat: readings are not corrected for load shifts or load "
                  "shedding"}
        for column in MORNING_COLS
    ] + [
        {"column": "morning_mean", "unit": "MVA",
         "frame": "mean of the target day's 12 morning slots (00:00-06:00 SAST)"},
        {"column": "morning_max", "unit": "MVA",
         "frame": "maximum of the target day's 12 morning slots"},
        {"column": "morning_min", "unit": "MVA",
         "frame": "minimum of the target day's 12 morning slots"},
        {"column": "hist_morningpeak_mean_90", "unit": "MVA",
         "frame": "mean of trailing <= 90 prior days' morning maxima (>= 30 "
                  "required); a MORNING telemetry aggregate - never an evening "
                  "value, never a label operand"},
        {"column": "day_of_week", "unit": "day of week (0 = Monday)",
         "frame": "calendar, Africa/Johannesburg"},
        {"column": "day_of_year", "unit": "ordinal day of year (1-366)",
         "frame": "calendar, Africa/Johannesburg"},
        {"column": "doy_sin", "unit": "dimensionless cyclical encoding",
         "frame": "sin(2*pi*(day_of_year-1)/365.25)"},
        {"column": "doy_cos", "unit": "dimensionless cyclical encoding",
         "frame": "cos(2*pi*(day_of_year-1)/365.25)"},
        {"column": "month", "unit": "calendar month (1-12)",
         "frame": "calendar, Africa/Johannesburg"},
        {"column": "station", "unit": "publisher column name (station identity)",
         "frame": "one of the 41 double-typed switching substation columns"},
        {"column": "date", "unit": "ISO date",
         "frame": "Africa/Johannesburg (SAST, UTC+2, no DST)"},
    ]

    positive_events = {}
    for name in ("train", "eval", "holdout"):
        rows = stats_by_split[name]
        positive_events[name] = {
            "positives": rows["positives"],
            "distinct_events": rows["distinct_positive_days"],
        }

    split_windows = {
        "train": {"start": f"{years[0]}-01-01", "end": f"{years[1]}-01-01"},
        "eval": {"start": f"{years[1]}-01-01", "end": f"{years[2]}-01-01"},
        "holdout": {"start": f"{years[2]}-01-01", "end": f"{years[2] + 1}-01-01"},
    }
    split_boundaries = {
        "train": f"target days {years[0]}-01-01..{years[0]}-12-31 (window end exclusive)",
        "eval": f"target days {years[1]}-01-01..{years[1]}-12-31 (window end exclusive)",
        "holdout": f"target days {years[2]}-01-01..{years[2]}-12-31 (window end exclusive)",
    }
    if tuple(years) != EXPECTED_SPLIT_YEARS:
        # the synthetic/re-run path: same structure, different vintage; the
        # real harvest asserts the expected years before this point
        split_boundaries["_note"] = ("split years derived from the supplied "
                                    f"pages: {years}")

    quality = {
        "name": NAME,
        "built_at_utc": built_at,
        "task": {
            "question": (
                "For a Cape Town switching substation, at 06:00 SAST on day D, "
                "will the evening peak load (max half-hourly MVA over "
                "16:00-22:00 SAST) exceed the station's trailing-90-evening p95 "
                "(min 30 prior evenings)? A useful prediction at 06:00 flags, "
                "before the evening ramp, the station-days that will stress a "
                "substation beyond its recent high-load regime."),
            "prediction_time": (
                "06:00 SAST (Africa/Johannesburg, UTC+2, no DST) on the target "
                "day D. Features are the target day's 00:00-06:00 half-hour "
                "slots (each slot ends at or before the instant; the 05:30 slot "
                "ends exactly at 06:00), the calendar of D, the station "
                "identity, and the mean of the trailing <= 90 prior days' "
                "morning peaks (the latest window member is D-1). The evening "
                "window 16:00-22:00 SAST lies entirely after the instant. "
                "Worked example: Grassy_Park_66kV 2024-07-15 (Monday, "
                "mid-winter), instant 06:00 SAST, trailing-90-evening p95 "
                "146.82 MVA, evening peak 150.38 MVA -> label 1 (exceeds). "
                "The evening peak and the p95 are label operands and ship in "
                "NO split file; they are sealed in auxiliary/evening_peaks.csv "
                "outside every solver-visible frame."),
        },
        "target": TARGET,
        "positive_label": POSITIVE,
        "positive_label_text": POSITIVE_LABEL_TEXT,
        "id_columns": ID_COLUMNS,
        "id_columns_are_entity_keys": True,
        "id_columns_note": ("station_day = <station>|<date> names one "
                            "station-day with one label; unique across the "
                            "panel, asserted at construction"),
        "time_column": TIME_COLUMN,
        "event_key_column": EVENT_KEY_COLUMN,
        "event_key_note": (
            "an event is one positive station-day; the gate's clustering takes "
            "the date part, so the recomputed count is the distinct exceedance "
            "day count (measured 227/246/247 by year). Positives cluster "
            "city-wide on regime days (cold-front evenings), so distinct days "
            "are the conservative independent-observation count; station-days "
            "within one day are dependent, recorded as a limitation"),
        "split_windows": split_windows,
        "split_boundaries": split_boundaries,
        "splits": {"train": "public/train.csv", "eval": "public/eval.csv",
                   "holdout": "private/holdout.csv"},
        "positive_events": positive_events,
        "positive_events_note": (
            "each positive is one station-day; the dependence structure that "
            "matters for inference is the exceedance day (city-wide regime) "
            "and the station series, both declared in event_key_note"),
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "shipped_columns": COLUMNS,
        "label_source_columns": [
            "the target day's evening half-hourly MVA readings (16:00-21:30 "
            "SAST) - the label numerator; sealed in "
            "auxiliary/evening_peaks.csv, never shipped in any split",
            "the trailing-90-evening p95 threshold (min 30 prior evenings) - "
            "the label comparator; sealed in auxiliary/evening_peaks.csv, "
            "never shipped in any split",
        ],
        "post_hoc_columns": [
            "every evening reading of the target day (16:00-22:00 SAST) - "
            "post-hoc at the 06:00 instant and the label's own operand; "
            "excluded from all split files by construction",
            "the evening peak and the trailing-evening p95 in any form "
            "(raw, rounded, windowed or differenced) - a sliding evening "
            "quantile's day-over-day delta reconstructs the entering value's "
            "exceedance (the fts-appeal-003 P0 lesson), so no evening-derived "
            "aggregate ships",
            "day-of evening readings of ANY prior day (an evening value is "
            "always some scored row's label operand)",
        ],
        "expected_duplicate_ids": 0,
        "high_cardinality_columns": ["date"],
        "high_cardinality_columns_note": (
            "date is the time column (the gate's join key) and the calendar "
            "day identity every row legitimately carries. On smaller panels "
            "(the synthetic rehearsal, or any v2 subset) its level count "
            "exceeds the gate's relative threshold (levels > rows/5), so it "
            "is declared here as a free high-cardinality field rather than "
            "treated as a leak: a date level is not one row - it is every "
            "station's station-day of that date, its label varies across "
            "stations, and per-level statistics cannot memorise individual "
            "rows. On the full 41-station panel each date level carries 41 "
            "rows and the column is scored normally, with its AUC reported "
            "as a measured property"),
        "external_threshold": False,
        "threshold_note": (
            "the threshold is internal to the panel (the station's own "
            "trailing-90-evening p95, min 30 prior evenings), not an external "
            "standard, so no external known-event fixture is required; the "
            "dated worked example (Grassy_Park_66kV 2024-07-15: 150.38 > "
            "146.82 -> 1) and the six monthly-mean fixtures are asserted "
            "in-build against the 2026-11-01 discovery measurements, and the "
            "label counts per year are asserted exactly"),
        "measurements": measurements,
        "timing": {
            "prediction_instant": {
                "kind": "period_end",
                "period": "the half-hour telemetry grid of the target day's "
                          "00:00-06:00 SAST window; the instant is its end "
                          "(the 05:30 slot completes at 06:00)",
                "days_after_period_end": 0,
                "citation": (
                    "the publisher's half-hourly telemetry table itself (City "
                    "of Cape Town Switching Substation Load Profile, ArcGIS "
                    "item bebf20c25bfa4ffaa7fc07a1a94ba287); every shipped "
                    "feature is a slot ending at or before 06:00 SAST on the "
                    "target day or an aggregate of strictly prior days. "
                    "Within-artifact timeliness is asserted at construction "
                    "(gapless 48-slot days, all slots non-null). The table is "
                    "a closed 2022-2024 window published 2026-02..03, so "
                    "real-world availability at historical instants is "
                    "unverified - the artifact is retrospective research"),
            },
            "features": {
                "period": "the target day's 00:00-06:00 slots plus strictly "
                          "prior days' morning aggregates (latest member D-1)",
                "published_days_after_period_end": 0,
                "source_kind": "administrative_record",
            },
            "row_selection": {
                "latest_period_used": f"{years[2]}-12-31",
                "fields": [
                    "station is one of the 41 double-typed columns (the two "
                    "string-typed columns Triangle_132kV and "
                    "Morgen_Gronde_132kV are excluded so the panel reproduces "
                    "the measured discovery counts; exclusion recorded)",
                    "the station-day has >= 30 prior evenings in the sealed "
                    "evening matrix (the p95 window's minimum); the first 30 "
                    "days of each station's series are burn-in, counted, "
                    "never scored",
                ],
                "basis": (
                    "eligibility counts only days strictly before the target "
                    "day - decidable at the instant with no target-period or "
                    "future field; the burn-in rows are unobserved-threshold "
                    "censoring counted in their own bucket, never scored as "
                    "negatives"),
            },
            "observations": [],
        },
        "evaluation_contract": {
            "use": "retrospective_research",
            "access": "isolated_rows",
            "training_label_timing": "unverified",
            "scope_note": (
                "each row is one station-day. The label's operands (the "
                "evening readings and the trailing-evening p95) are sealed "
                "outside every solver-visible frame, so no shipped column is a "
                "function of any row's evening outcome; the only history-"
                "derived shipped column is a mean of MORNING peaks, which are "
                "never label operands. The isolated-rows declaration is the "
                "required posture for the probe-measured morning-history "
                "exposure and is not an enforcement claim: the illustrative "
                "runner still passes the whole eval feature table to the "
                "predictor in one call, nothing in this package enforces "
                "isolation, and the absence of a known recovery is not a "
                "proof against future attacks - the independent pre-flip "
                "audit must attack the shipped bytes before any publication. "
                "Labeled eval is development/validation; the holdout is the "
                "final test and stays sealed"),
            "feature_evidence": fe,
            "vintage": {
                "kind": "current_snapshot",
                "evidence": (
                    "single closed-window table: the ArcGIS item "
                    "bebf20c25bfa4ffaa7fc07a1a94ba287 was created 2026-02-28, "
                    "modified 2026-03-02 and is static (hasStaticData); the "
                    "2022-2024 grid is gapless (1,096 days x 48 half-hours) "
                    "and the publisher exposes no revised vintages, so the "
                    "artifact reads the only snapshot that exists. Harvest "
                    "pinned per-page by sha256 (summary.json), read "
                    + str(harvest_stats.get("fetch", {}).get("requests"))
                    + " requests"),
            },
            "selection": {
                "kind": "prediction_time",
                "evidence": (
                    "a station-day enters the scored panel iff it has >= 30 "
                    "prior evenings in the sealed evening matrix (count of "
                    "strictly earlier days) and its station is one of the 41 "
                    "double-typed columns; membership is decidable at the "
                    "instant and reads no target-period or post-instant "
                    "field; burn-in rows are counted, never scored"),
            },
            "limitations": [
                "retrospective closed window: the table was published "
                "2026-02..03 as one static 2022-2024 snapshot; no historical "
                "vintages exist, so no operational forecasting claim is made "
                "and training-label timing stays unverified",
                "evening label operands are sealed outside the artifact; the "
                "trailing-evening p95 threshold is not a shipped feature, so "
                "the model predicts exceedance of a threshold it never sees",
                "the publisher's own caveat: readings are not corrected for "
                "load shifts or load shedding, and Cape Town's 2022-2024 "
                "load-shedding regime suppresses observed peaks",
                "one city, 41 substations, 1,096 days; generalisation beyond "
                "Cape Town's grid and regime is not established",
                "positive rate drifts across splits (11.20% train 2022, 8.39% "
                "eval 2023, 9.21% holdout 2024): an out-of-distribution as "
                "well as temporal test, recorded not repaired",
                "positives cluster on city-wide regime days (227/246/247 "
                "distinct exceedance days): station-days within a day are "
                "dependent, and clustered intervals must be used for "
                "inference",
                "the string-typed columns Triangle_132kV (empty) and "
                "Morgen_Gronde_132kV (numeric-as-text) are excluded to "
                "reproduce the measured discovery counts exactly; their "
                "inclusion is a v2 question, not a silent gap",
            ],
            "cross_row_audit": {
                "rationale": (
                    "the abs-visitor-arrivals shape applies by construction to "
                    "any sliding evening history: a later same-station row's "
                    "window would contain this row's evening label operand. "
                    "The mitigation is structural, not declared: NO "
                    "evening-derived value ships in any split file - evening "
                    "readings, evening peaks and the trailing-evening p95 "
                    "live only in auxiliary/evening_peaks.csv outside every "
                    "solver-visible frame, and no sliding quantile ships "
                    "because its day-over-day delta equals the entering "
                    "evening's exceedance except for top-tail window swaps "
                    "(label-blind exact recovery, the operator's automatic "
                    "DO-NOT-PUBLISH class per the 2026-11-01 queue audit and "
                    "the fts-appeal-003 rebuild). The single history-derived "
                    "shipped column, hist_morningpeak_mean_90, aggregates "
                    "MORNING peaks (never label operands); the same delta "
                    "attack on it recovers only [morning_peak(D) > trailing "
                    "morning mean], a ~50%-base-rate event far from the ~9% "
                    "evening label. Probe 0 executes exactly that attack over "
                    "the full artifact and records coverage and mismatches; a "
                    "covered probe requires the isolated_rows access declared "
                    "above. Same-day rows of different stations share only "
                    "the calendar (identity is per-station); each station's "
                    "evening peak is its own telemetry and never appears in "
                    "another station's row"),
                "auxiliary_files_review": (
                    "the artifact ships exactly public/train.csv, "
                    "public/eval.csv, private/holdout.csv, meta.json and "
                    "quality.json. auxiliary/evening_peaks.csv (station, "
                    "date, evening_peak_mva, trailing_evening_p95_mva, "
                    "scored, exceeds) is uploaded to private staging for "
                    "label verification and reproduction only - it is never "
                    "mounted into an evaluated agent's workspace and never a "
                    "solver input; no other outcome-bearing file exists. The "
                    "raw fetch pages stay in the job work-dir with per-page "
                    "sha256 recorded in summary.json and are not uploaded"),
                "probes": [
                    {"name": "morning_history_delta_attack",
                     "entity_columns": ["station"],
                     "time_column": "date",
                     "offset_days": 1,
                     "left": "hist_morningpeak_mean_90",
                     "right": "hist_morningpeak_mean_90",
                     "right_row": "earlier",
                     "operation": "gt",
                     "note": ("predicts label(D) = [hist(D+1) > hist(D)], i.e. "
                              "whether the entering morning peak raised the "
                              "trailing morning mean: the strongest label-"
                              "recovery join expressible over the shipped "
                              "frame; mismatch rate is the measured bound on "
                              "the morning-history exposure")},
                ],
            },
        },
    }
    return quality


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="extract directory")
    parser.add_argument("--work-dir", required=True,
                        help="scratch dir for fetched pages (kept off the artifact)")
    parser.add_argument("--built-at", required=True,
                        help="ISO timestamp pinned as build input (byte-identical rebuilds)")
    parser.add_argument("--summary-out", required=True)
    parser.add_argument("--pages-dir",
                        help="reuse previously fetched pages (synthetic/re-run path); "
                             "disables the live harvest and the source fixtures")
    parser.add_argument("--real-fixtures", action="store_true",
                        help="assert the 2026-11-01 discovery measurements "
                             "(live construction only)")
    args = parser.parse_args()

    out = Path(args.out)
    work = Path(args.work_dir)
    out.mkdir(parents=True, exist_ok=True)
    stats: dict = {}
    real = args.pages_dir is None
    if real:
        pages = harvest(work, stats)
    else:
        pages = sorted(Path(args.pages_dir).glob("page-*.json"))
        if not pages:
            raise BuildError(f"no pages found in {args.pages_dir}")
        stats["fetch"] = {"requests": 0, "bytes": 0, "pages": len(pages),
                          "page_sha256": {p.name: sha256_of(p) for p in pages},
                          "note": "pages supplied via --pages-dir (synthetic or "
                                  "re-run path); no live harvest"}
    rows, stations = load_pages(pages)
    panel = build_panel(rows, stations, stats, real_fixtures=bool(args.real_fixtures))
    if args.real_fixtures:
        check_fixtures(panel, stats)

    splits, years = split_rows(panel)
    if args.real_fixtures and tuple(years) != EXPECTED_SPLIT_YEARS:
        raise BuildError(f"target-day years {years} do not match the measured "
                         f"harvest {EXPECTED_SPLIT_YEARS}: the live table moved")
    for name in splits:
        positives = sum(1 for row in splits[name] if row[TARGET] == "1")
        if name in ("eval", "holdout") and (positives == 0 or positives == len(splits[name])):
            raise BuildError(f"{name} is single-class; it cannot carry a score")
    distinct_by_split = {}
    for name, rows_ in splits.items():
        distinct_by_split[name] = len({row["date"] for row in rows_
                                       if row[TARGET] == "1"})
    stats_by_split = write_artifact(out, splits, args.built_at, years)
    for name in stats_by_split:
        stats_by_split[name]["distinct_positive_days"] = distinct_by_split[name]

    quality = build_quality(stats_by_split, stats, args.built_at, years)
    (out / "quality.json").write_text(json.dumps(quality, indent=1, sort_keys=True) + "\n",
                                     encoding="utf-8")

    stats["split_stats"] = stats_by_split
    stats["columns"] = COLUMNS
    stats["artifact_sha256"] = {
        "public/train.csv": sha256_of(out / "public" / "train.csv"),
        "public/eval.csv": sha256_of(out / "public" / "eval.csv"),
        "private/holdout.csv": sha256_of(out / "private" / "holdout.csv"),
        "meta.json": sha256_of(out / "meta.json"),
        "quality.json": sha256_of(out / "quality.json"),
        "auxiliary/evening_peaks.csv": sha256_of(out / "auxiliary" / "evening_peaks.csv"),
    }
    stats["built_at_utc"] = args.built_at
    stats["name"] = NAME
    Path(args.summary_out).write_text(json.dumps(stats, indent=1, sort_keys=True) + "\n",
                                      encoding="utf-8")
    print(json.dumps({"name": NAME, "splits": stats_by_split,
                      "exclusions": stats["exclusions"]}, indent=1))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
