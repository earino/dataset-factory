#!/usr/bin/env python3
"""Construct the ab-wildfire-ia-escape extract from the pinned Alberta wildfire CSV.

Design (frozen for this attempt, abwildfire-build-001)
------------------------------------------------------
Population: ALL assessed wildfires in Alberta's Forest Protection Area, 2006-2025
(27,828 rows; every discovered wildfire is assessed, so eligibility is assessment-based
with no outcome-conditioned rule; winter rows are kept and counted).

Prediction instant: the fire's own assessment_datetime, the publisher-documented
"date and time the wildfire was originally assessed". Every shipped feature is the
publisher's own assessment record ("at the time of initial assessment") or a
pre-instant field (reported/discovered/estimated-start timestamps, detection channel)
or calendar/geography. Timestamps carry no timezone and are read as local Alberta
operational time (America/Edmonton) - confirmed against the Government of Alberta's
official 2016 Horse River review, which documents detection at 16:03h MDT on
2016-05-01 (the record's naive 16:03) and matching under-control/extinguished dates.

Label (the only shipped target): escape = final area burned (current_size,
"final area burned of the wildfire") >= 100 ha. Label sources and every post-instant
family (cause investigation, dispatch block, suppression milestones, fire name) are
excluded by the column policy below and asserted absent from every written header.

Splits: by the ASSESSMENT instant's calendar year - train 2006-2015 / eval 2016-2020 /
holdout 2021-2025. The record year (YEAR) differs from the assessment year for 356
winter carryover fires; the gate checks windows against the time column, so the split
follows the time column. Label-side counts are identical under either rule.

Ordering: this script only CONSTRUCTS files and gate diagnostics. It computes no
performance metric; run.sh qualifies, exact-byte-accepts, and only then scores.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

SHA256_CSV = "8b6ed447ab0f958dbe845a53dc15362b8ef5c0810ad9420d2143f9f5ee010a72"
CSV_BYTES = 10400030
EXPECTED_TOTAL = 27828
ESCAPE_THRESHOLD_HA = 100.0

# Forest-area prefixes measured over the full compilation (FIRE_NUMBER's first three
# letters name the managing forest area; assigned when the fire is recorded).
PREFIXES = {"CWF", "HWF", "SWF", "LWF", "PWF", "EWF", "MWF", "RWF", "GWF", "WWF"}

# Windows follow the assessment instant's year (the time column).
WINDOWS = {"train": range(2006, 2016), "eval": range(2016, 2021), "holdout": range(2021, 2026)}

# Named-fire fixtures: (YEAR, FIRE_NUMBER, exact CURRENT_SIZE string, escape label).
# Values read from the pinned CSV and cross-checked against the publisher's own
# season statistics and the official Horse River review (see notes.md).
FIXTURES = [
    ("2011", "MWF007", "577646.8", 1),   # Richardson Fire
    ("2011", "SWF057", "87659.4", 1),    # Utikuma Complex
    ("2012", "HWF106", "134603", 1),     # Zama Complex
    ("2016", "MWF009", "485123.6", 1),   # Horse River / Fort McMurray
    ("2019", "HWF042", "334772.6", 1),   # Chuckegg Creek
    ("2019", "SWF049", "222837.2", 1),   # McMillan Complex
    ("2023", "HWF058", "234061", 1),     # Basset Fire
    ("2023", "HWF036", "203022", 1),     # Long Lake Complex
    ("2023", "EWF031", "201913", 1),     # Pembina Complex
    ("2023", "LWF002", "0.01", 0),       # already-controlled small-fire negative
]

# Publisher season-total hectares (probe_publisher_crosscheck.py; Alberta Wildfire
# season statistics PDFs). 2019 is the documented spring aerial-photography revision.
SEASON_HECTARES = {2019: 883411, 2020: 3269, 2021: 54047, 2022: 130858,
                   2023: 2211900, 2024: 708528}

# Column policy. Shipped columns in write order; everything else in the source is
# excluded. Label sources and post-hoc families are asserted absent from the headers.
ID_COLUMNS = ["fire_id"]
TARGET = "escape"
FEATURES = [
    "assessment_ts", "assessment_date", "day_of_week", "month", "doy_sin", "doy_cos",
    "forest_area", "latitude", "longitude",
    "assessment_hectares", "fire_spread_rate", "fire_type", "fire_position_on_slope",
    "weather_conditions_over_fire", "temperature", "relative_humidity", "wind_speed",
    "wind_direction", "fuel_type", "detection_agent_type",
    "hours_report_to_assessment", "hours_discovery_to_assessment",
    "hours_start_to_assessment",
]
HIGH_CARDINALITY = ["assessment_ts", "assessment_date", "latitude", "longitude",
                    "hours_report_to_assessment", "hours_discovery_to_assessment",
                    "hours_start_to_assessment"]
COLUMNS = ID_COLUMNS + FEATURES + [TARGET]

LABEL_SOURCE_COLUMNS = ["current_size", "size_class", "first_uc_date"]
POST_HOC_COLUMNS = [
    # label sources and the containment/milestone family (secondary formulation only)
    "current_size", "size_class", "first_uc_date", "first_uc_size", "first_bh_date",
    "first_bh_size", "first_to_date", "first_to_size", "first_ex_date",
    "first_ex_size_perimeter",
    # cause investigation family
    "general_cause", "true_cause", "industry_identifier", "responsible_group",
    "activity_class",
    # dispatch block (mixed ordering measured: 2.41% of dispatch timestamps after assessment)
    "dispatched_resource", "dispatch_date", "start_for_fire_date",
    # suppression/action block
    "initial_action_by", "ia_arrival_at_fire_date", "ia_access",
    "fire_fighting_start_date", "fire_fighting_start_size", "bucketing_on_fire",
    "distance_from_water_source", "first_bucket_drop_date",
    # other excluded fields
    "fire_name",       # assigned to notable fires after the event; outcome-revealing
    "fire_origin",     # no publisher definition transcribed; timing undocumented
    "discovered_size", # not in the reviewed feature contract; structurally blank for the
                        # majority unplanned detection channel (superseded by the
                        # assessment size)
    "detection_agent", # 151-level sub-channel codes; the coarse channel ships
]

# Per-window counts measured on the pinned CSV (probe_escape_base_rates.py, full
# population). Asserted so a silent construction change cannot pass quietly.
EXPECTED_POSITIVES = {"train": 297, "eval": 104, "holdout": 257}
EXPECTED_DISTINCT_DATES = {"train": 156, "eval": 79, "holdout": 128}
EXPECTED_CONTAINMENT_72H = {"train": 514, "eval": 189, "holdout": 611}
EXPECTED_ALREADY_CONTROLLED = 11688
EXPECTED_DISPATCH_AFTER = 670
SIZE_CLASS_BOUNDS = {"A": (0.0, 0.1), "B": (0.1, 4.0), "C": (4.0, 40.0),
                    "D": (40.0, 200.0), "E": (200.0, float("inf"))}

DT_FORMATS = ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]


def parse_dt(value: str):
    value = (value or "").strip()
    if not value:
        return None
    for fmt in DT_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return "UNPARSED"


def fnum(value: str):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fail(message: str):
    print(json.dumps({"ok": False, "stage": "build", "error": message}), flush=True)
    raise SystemExit(1)


def window_of(year: int) -> str:
    for name, years in WINDOWS.items():
        if year in years:
            return name
    return "outside"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", default="/data/fp-historical-wildfire-data-2006-2025.csv")
    parser.add_argument("--out", default="/output/extract")
    parser.add_argument("--job-file", default="/workspace/job.json")
    args = parser.parse_args()

    source = Path(args.source)
    out = Path(args.out)
    if not source.is_file():
        fail(f"source CSV not found at {source}")

    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != SHA256_CSV:
        fail(f"source digest {digest} != pinned {SHA256_CSV}")
    if source.stat().st_size != CSV_BYTES:
        fail(f"source size {source.stat().st_size} != expected {CSV_BYTES}")

    fetch_receipt = None
    job_path = Path(args.job_file)
    if job_path.is_file():
        try:
            job = json.loads(job_path.read_text())
            fetch_receipt = job.get("fetch")
        except (ValueError, OSError):
            fetch_receipt = None

    # ---- parse -------------------------------------------------------------
    with source.open(newline="", encoding="utf-8-sig") as handle:
        raw_rows = list(csv.DictReader(handle))
    if len(raw_rows) != EXPECTED_TOTAL:
        fail(f"expected {EXPECTED_TOTAL} rows, found {len(raw_rows)}")

    trimmed_cells = 0
    unparsed = Counter()
    rows = []
    for raw in raw_rows:
        record = {}
        for key, value in raw.items():
            value = value if value is not None else ""
            if value != value.strip():
                trimmed_cells += 1
            record[key] = value.strip()
        rows.append(record)

    # ---- structural checks -------------------------------------------------
    ids = Counter((r["YEAR"], r["FIRE_NUMBER"]) for r in rows)
    if max(ids.values()) != 1:
        fail(f"(YEAR, FIRE_NUMBER) not unique: {sum(1 for v in ids.values() if v > 1)} duplicates")

    for field in ("ASSESSMENT_DATETIME", "REPORTED_DATE"):
        bad = sum(1 for r in rows if parse_dt(r[field]) == "UNPARSED")
        if bad:
            fail(f"{bad} unparseable {field} values")
    bad = sum(1 for r in rows if fnum(r["CURRENT_SIZE"]) is None)
    if bad:
        fail(f"{bad} unparseable CURRENT_SIZE values")
    for field in ("DISCOVERED_DATE", "FIRE_START_DATE", "FIRST_UC_DATE"):
        unparsed[field] = sum(1 for r in rows if parse_dt(r[field]) == "UNPARSED")

    seconds_truncated = 0
    for r in rows:
        a = parse_dt(r["ASSESSMENT_DATETIME"])
        if a.second:
            seconds_truncated += 1
    if seconds_truncated:
        fail(f"{seconds_truncated} assessment timestamps carry seconds; canonicalization "
             f"assumed zero-second grain")

    # pre-instant ordering (measured: reported 27,828/27,828, discovered 21,977,
    # start 27,109 at or before assessment)
    violations = Counter()
    present = Counter()
    for field in ("REPORTED_DATE", "DISCOVERED_DATE", "FIRE_START_DATE"):
        for r in rows:
            a = parse_dt(r["ASSESSMENT_DATETIME"])
            b = parse_dt(r[field])
            if b is None:
                continue
            present[field] += 1
            if b > a:
                violations[field] += 1
    if any(violations.values()):
        fail(f"pre-instant ordering violations: {dict(violations)}")
    dispatch_after = sum(1 for r in rows
                         if parse_dt(r["DISPATCH_DATE"]) is not None
                         and parse_dt(r["DISPATCH_DATE"]) > parse_dt(r["ASSESSMENT_DATETIME"]))
    if dispatch_after != EXPECTED_DISPATCH_AFTER:
        fail(f"dispatch-after-assessment count {dispatch_after} != measured {EXPECTED_DISPATCH_AFTER}")

    for r in rows:
        if r["FIRE_NUMBER"][:3] not in PREFIXES:
            fail(f"unexpected forest-area prefix: {r['FIRE_NUMBER']!r}")

    # ---- fixtures ----------------------------------------------------------
    by_id = {(r["YEAR"], r["FIRE_NUMBER"]): r for r in rows}
    fixture_results = []
    for year, fire_number, size_text, expected_escape in FIXTURES:
        row = by_id.get((year, fire_number))
        if row is None:
            fail(f"fixture fire {year}/{fire_number} not found")
        if row["CURRENT_SIZE"] != size_text:
            fail(f"fixture {year}/{fire_number}: current_size {row['CURRENT_SIZE']!r} "
                 f"!= published {size_text!r}")
        label = int(fnum(row["CURRENT_SIZE"]) >= ESCAPE_THRESHOLD_HA)
        if label != expected_escape:
            fail(f"fixture {year}/{fire_number}: label {label} != expected {expected_escape}")
        fixture_results.append({"year": year, "fire_number": fire_number,
                                "current_size": row["CURRENT_SIZE"], "escape": label})
    negative = by_id[("2023", "LWF002")]
    if parse_dt(negative["FIRST_UC_DATE"]) != parse_dt(negative["ASSESSMENT_DATETIME"]):
        fail("LWF002 2023 negative-control: assessment != first under control")
    horse_river = by_id[("2016", "MWF009")]
    if horse_river["REPORTED_DATE"] != "2016-05-01 16:03":
        fail("Horse River reported_date mismatch against the official review's 16:03h MDT")

    # ---- units and frames cross-checks --------------------------------------
    size_class_bad = 0
    for r in rows:
        size, size_class = fnum(r["CURRENT_SIZE"]), r["SIZE_CLASS"]
        if size_class in SIZE_CLASS_BOUNDS and size is not None:
            low, high = SIZE_CLASS_BOUNDS[size_class]
            ok = (low <= size <= high) if size_class != "A" else (size <= 0.1)
            if not ok:
                size_class_bad += 1
    if size_class_bad:
        fail(f"{size_class_bad} SIZE_CLASS vs CURRENT_SIZE inconsistencies")

    csv_hectares = Counter()
    for r in rows:
        csv_hectares[int(r["YEAR"])] += fnum(r["CURRENT_SIZE"])
    season_deltas = {}
    for year, published in SEASON_HECTARES.items():
        measured = csv_hectares[year]
        delta = (measured - published) / published
        season_deltas[year] = {"csv_ha": round(measured, 1), "published_ha": published,
                               "delta_frac": round(delta, 4)}
        if year == 2019:
            if not (-0.109 <= delta <= -0.099):
                fail(f"2019 revision delta {delta:.4f} outside the documented -10.4% band")
        elif abs(delta) > 0.011:
            fail(f"{year} season-hectares delta {delta:.4f} exceeds 1.1%")
    if fnum(by_id[("2023", "LWF002")]["CURRENT_SIZE"]) != 0.01:
        fail("LWF002 current_size is not the documented 0.01 ha")

    # ---- build records ------------------------------------------------------
    built = {"train": [], "eval": [], "holdout": []}
    outside = 0
    carryover = Counter()
    containment = {w: {"gt_72h": 0, "le_72h": 0, "already_controlled_at_assessment": 0,
                       "unusable": 0} for w in ("train", "eval", "holdout")}
    for r in rows:
        assessed = parse_dt(r["ASSESSMENT_DATETIME"])
        window = window_of(assessed.year)
        if window == "outside":
            outside += 1
            continue
        if assessed.year != int(r["YEAR"]):
            carryover[window] += 1
        under_control = parse_dt(r["FIRST_UC_DATE"])
        stats = containment[window]
        if not isinstance(under_control, datetime) or under_control < assessed:
            stats["unusable"] += 1
        else:
            if under_control == assessed:
                stats["already_controlled_at_assessment"] += 1
            if (under_control - assessed).total_seconds() / 3600 > 72:
                stats["gt_72h"] += 1
            else:
                stats["le_72h"] += 1
        reported = parse_dt(r["REPORTED_DATE"])
        discovered = parse_dt(r["DISCOVERED_DATE"])
        started = parse_dt(r["FIRE_START_DATE"])
        doy = assessed.timetuple().tm_yday
        record = {
            "fire_id": f"{r['YEAR']}-{r['FIRE_NUMBER']}",
            "assessment_ts": assessed.strftime("%Y-%m-%d %H:%M"),
            "assessment_date": assessed.strftime("%Y-%m-%d"),
            "day_of_week": str(assessed.weekday()),
            "month": str(assessed.month),
            "doy_sin": f"{math.sin(2 * math.pi * doy / 365.25):.6f}",
            "doy_cos": f"{math.cos(2 * math.pi * doy / 365.25):.6f}",
            "forest_area": r["FIRE_NUMBER"][:3],
            "latitude": r["LATITUDE"],
            "longitude": r["LONGITUDE"],
            "assessment_hectares": r["ASSESSMENT_HECTARES"],
            "fire_spread_rate": r["FIRE_SPREAD_RATE"],
            "fire_type": r["FIRE_TYPE"],
            "fire_position_on_slope": r["FIRE_POSITION_ON_SLOPE"],
            "weather_conditions_over_fire": r["WEATHER_CONDITIONS_OVER_FIRE"],
            "temperature": r["TEMPERATURE"],
            "relative_humidity": r["RELATIVE_HUMIDITY"],
            "wind_speed": r["WIND_SPEED"],
            "wind_direction": r["WIND_DIRECTION"],
            "fuel_type": r["FUEL_TYPE"],
            "detection_agent_type": r["DETECTION_AGENT_TYPE"],
            "hours_report_to_assessment": f"{(assessed - reported).total_seconds() / 3600:.2f}",
            "hours_discovery_to_assessment":
                "" if discovered is None else f"{(assessed - discovered).total_seconds() / 3600:.2f}",
            "hours_start_to_assessment":
                "" if started is None else f"{(assessed - started).total_seconds() / 3600:.2f}",
            "escape": str(int(fnum(r["CURRENT_SIZE"]) >= ESCAPE_THRESHOLD_HA)),
        }
        if not record["assessment_hectares"]:
            fail(f"{record['fire_id']}: assessment_hectares blank (100% coverage expected)")
        built[window].append(record)
    if outside:
        fail(f"{outside} rows fall outside the three assessment-year windows")

    # ---- per-window measured counts ----------------------------------------
    counts = {}
    for window, records in built.items():
        positives = [x for x in records if x["escape"] == "1"]
        dates = {x["assessment_date"] for x in positives}
        counts[window] = {
            "rows": len(records),
            "positives": len(positives),
            "positive_rate": round(len(positives) / len(records), 6),
            "distinct_positive_dates": len(dates),
            "carryover_from_record_year": carryover[window],
        }
    for window, records in built.items():
        if counts[window]["positives"] != EXPECTED_POSITIVES[window]:
            fail(f"{window}: {counts[window]['positives']} positives != "
                 f"measured {EXPECTED_POSITIVES[window]}")
        if counts[window]["distinct_positive_dates"] != EXPECTED_DISTINCT_DATES[window]:
            fail(f"{window}: {counts[window]['distinct_positive_dates']} distinct positive "
                 f"dates != measured {EXPECTED_DISTINCT_DATES[window]}")

    # Secondary containment formulation (measured, not shipped; its design decisions
    # - notably the 42% already-controlled-at-assessment stratum - belong to a separate
    # task instance if it is ever built).
    already_controlled = sum(v["already_controlled_at_assessment"] for v in containment.values())
    for window in ("train", "eval", "holdout"):
        if containment[window]["gt_72h"] != EXPECTED_CONTAINMENT_72H[window]:
            fail(f"{window}: containment>72h {containment[window]['gt_72h']} != measured "
                 f"{EXPECTED_CONTAINMENT_72H[window]}")
    if already_controlled != EXPECTED_ALREADY_CONTROLLED:
        fail(f"already-controlled total {already_controlled} != measured "
             f"{EXPECTED_ALREADY_CONTROLLED}")

    # ---- write files ---------------------------------------------------------
    public_dir = out / "public"
    private_dir = out / "private"
    public_dir.mkdir(parents=True, exist_ok=True)
    private_dir.mkdir(parents=True, exist_ok=True)
    split_paths = {"train": public_dir / "train.csv", "eval": public_dir / "eval.csv",
                   "holdout": private_dir / "holdout.csv"}
    for window, path in split_paths.items():
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(COLUMNS)
            for record in built[window]:
                writer.writerow([record[column] for column in COLUMNS])

    # The column policy is enforced on the written bytes, not on a convention.
    for path in split_paths.values():
        with path.open(newline="", encoding="utf-8") as handle:
            header = next(csv.reader(handle))
        if header != COLUMNS:
            fail(f"{path.name}: written header differs from the declared column policy")
        forbidden = [c for c in header if c in set(LABEL_SOURCE_COLUMNS) | set(POST_HOC_COLUMNS)]
        if forbidden:
            fail(f"{path.name}: excluded columns present in the written header: {forbidden}")

    # ---- meta.json ------------------------------------------------------------
    meta = {
        "name": "ab-wildfire-ia-escape",
        "target": TARGET,
        "positive_label": 1,
        "id_columns": ID_COLUMNS,
        "columns": COLUMNS,
        "rows": {w: counts[w]["rows"] for w in ("train", "eval", "holdout")},
        "positive_rate": {w: counts[w]["positive_rate"] for w in ("train", "eval", "holdout")},
        "split_description": "temporal split on the assessment instant (America/Edmonton local "
            "operational time): train 2006-2015, eval 2016-2020, holdout 2021-2025, by the "
            "assessment instant's calendar year (356 winter carryover fires assessed in the "
            "year after their record year move with their assessment); population is ALL "
            "assessed Forest Protection Area wildfires (27,828), winter rows kept; label = "
            "final area burned >= 100 ha",
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    # ---- quality.json ----------------------------------------------------------
    coverage = {}
    for window, records in built.items():
        entry = {"n": len(records)}
        for column in FEATURES:
            entry[column] = round(sum(1 for x in records if x[column] != "") / len(records), 4)
        coverage[window] = entry

    quality = {
        "name": "ab-wildfire-ia-escape",
        "target": TARGET,
        "positive_label": 1,
        "id_columns": ID_COLUMNS,
        "features": FEATURES,
        "high_cardinality_columns": HIGH_CARDINALITY,
        "carry_columns": [],
        "splits": {"train": "public/train.csv", "eval": "public/eval.csv",
                   "holdout": "private/holdout.csv"},
        "time_column": "assessment_ts",
        "event_key_column": "assessment_date",
        "expected_duplicate_ids": 0,
        "id_columns_are_entity_keys": True,
        "external_threshold": True,
        "known_event": {
            "name": "2016 Horse River Fire (MWF009): final area burned 485,123.6 ha "
                    "in the publisher's record",
            "expected_verdict": "exceeds",
            "source": "asserted in-build against the pinned CSV ((2016, MWF009) current_size "
                      "485,123.6 -> escape 1) and corroborated by the Government of Alberta's "
                      "official review (open.alberta.ca, 'A Review of the 2016 Horse River "
                      "Wildfire', March 2017, dataset 7cc619bd-56ce-488e-b007-cada28430589), "
                      "which documents detection at 16:03h MDT on 2016-05-01 - the record's "
                      "naive local timestamp - under control 2016-07-04 and extinguished "
                      "2017-08-02, matching the record's milestone dates; nine further named "
                      "fires asserted at their publisher-documented final sizes",
        },
        "negative_control_fixture": {
            "name": "already-controlled small-fire stratum (LWF002 2023: final 0.01 ha, "
                    "first under control at the assessment instant)",
            "expected": "escape 0 with duration 0 h; 11,688/27,828 fires (42.0%) are "
                        "already under control at the assessment instant - asserted in-build "
                        "and reported per split",
            "source": "the pinned publisher CSV, asserted in-build; the stratum is a "
                      "measured property of the secondary containment formulation (not "
                      "shipped) and of the easy-negative tail of the escape label",
        },
        "features_documented_at": "prediction_time",
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "post_hoc_columns": POST_HOC_COLUMNS,
        "task": {
            "prediction_time": "the wildfire's own assessment_datetime - 'the date and time "
                "the wildfire was originally assessed by Alberta Wildfire employees' "
                "(publisher dictionary p11); every shipped feature is the crew-observed "
                "assessment record ('at the time of initial assessment'), a pre-instant "
                "timestamp (reported/discovered/estimated start), the detection channel, or "
                "calendar/geography; timestamps are naive local Alberta operational time "
                "(America/Edmonton), confirmed against the official 2016 Horse River review",
            "target_definition": "escape: final area burned (current_size, the publisher's "
                "'final area burned of the wildfire') at or above 100 ha, on the current "
                "compilation's recorded value (>= 100.0, exact on the recorded decimal); "
                "threshold-flip exposure from post-hoc area revision is bounded by the "
                "measured 89 fires within +-20% of the threshold",
            "description": "at the recorded initial assessment of a newly discovered "
                "wildfire in Alberta's Forest Protection Area, predict from the regulator's "
                "own crew-observed assessment record whether the fire will escape initial "
                "attack (final area burned >= 100 ha)",
        },
        "measurements": [
            {"column": "assessment_hectares", "unit": "hectares",
             "frame": "size of the wildfire at the time of assessment, recorded to the "
                      "nearest hectare or hundredth of a hectare (dictionary p12)"},
            {"column": "fire_spread_rate", "unit": "metres per minute",
             "frame": "rate of spread at the time of initial assessment (dictionary p12)"},
            {"column": "temperature", "unit": "degrees Celsius",
             "frame": "temperature at the wildfire site at the time of initial assessment"},
            {"column": "relative_humidity", "unit": "percent",
             "frame": "relative humidity at the wildfire site at the time of initial assessment"},
            {"column": "wind_speed", "unit": "kilometres per hour",
             "frame": "wind speed at the wildfire site at the time of initial assessment"},
            {"column": "latitude", "unit": "decimal degrees",
             "frame": "location of the ignition area recorded as GPS; originally captured "
                      "during the assessment, may be further investigated as the wildfire "
                      "progresses - the shipped value is the current confirmed ignition-area "
                      "location (dictionary p6; flagged in evaluation_contract)"},
            {"column": "longitude", "unit": "decimal degrees",
             "frame": "as latitude, longitude component"},
            {"column": "hours_report_to_assessment", "unit": "hours",
             "frame": "elapsed time from REPORTED_DATE (the time the wildfire was first "
                      "reported to Alberta Wildfire) to the assessment instant; 100% coverage"},
            {"column": "hours_discovery_to_assessment", "unit": "hours",
             "frame": "elapsed time from DISCOVERED_DATE to the assessment instant; blank "
                      "where the discovery timestamp is absent (the dictionary documents "
                      "unplanned-detection blanks)"},
            {"column": "hours_start_to_assessment", "unit": "hours",
             "frame": "elapsed time from FIRE_START_DATE (the estimated or witnessed fire "
                      "start) to the assessment instant; blank where absent"},
            {"column": "escape", "unit": "binary label",
             "frame": "1 when final area burned >= 100 ha on the current compilation's "
                      "recorded value; 0 otherwise"},
        ],
        "timing": {
            "prediction_instant": {
                "kind": "event_time",
                "period": "instant",
                "days_after_period_end": 0,
                "citation": "assessment_datetime is 'the date and time the wildfire was "
                            "originally assessed by Alberta Wildfire employees' (dictionary "
                            "p11); the assessment block (FP41 quick or full assessment) is the "
                            "administrative record written at the event. Measured ordering on "
                            "the pinned CSV: reported_date at or before assessment for "
                            "27,828/27,828, discovered_date 21,977/21,977, fire_start_date "
                            "27,109/27,109; dispatch_date falls after assessment for 670/27,813 "
                            "(2.41%), so the dispatch block is excluded. Timestamps carry no "
                            "timezone and are read as local Alberta operational time "
                            "(America/Edmonton), confirmed against the official 2016 Horse "
                            "River review (detection 16:03h MDT 2016-05-01 = the record's "
                            "naive 16:03; under-control 2016-07-04 and extinguished "
                            "2017-08-02 match the record)",
            },
            "features": {
                "period": "instant",
                "published_days_after_period_end": 0,
                "source_kind": "administrative_record",
            },
            "row_selection": {
                "latest_period_used": "2025",
                "fields": ["YEAR", "FIRE_NUMBER", "ASSESSMENT_DATETIME"],
                "basis": "every discovered wildfire in the Forest Protection Area is "
                         "assessed (measured: 27,828/27,828 rows carry an assessment "
                         "instant), so eligibility is assessment-based with no "
                         "outcome-conditioned rule and no censoring; all rows of the "
                         "2006-2025 compilation are retained, including 587 November-February "
                         "assessments and 356 winter carryover fires assessed in the year "
                         "after their record year; splits follow the assessment instant's "
                         "calendar year",
            },
            "observations": [],
        },
        "evaluation_contract": {
            "use": "retrospective_research",
            "access": "isolated_rows",
            "training_label_timing": "unverified",
            "scope_note": "each row is one wildfire escape prediction at its own assessment "
                "instant; features are the publisher's own assessment record and the runner "
                "predicts row-wise from the shipped columns. Labeled eval is "
                "development/validation; private holdout is the final test and stays outside "
                "evaluated agents' workspaces. Training-label timing is UNVERIFIED: the "
                "publisher ships a single current compilation (no historical per-fire "
                "vintages, no first-publication ledger), so no full-row availability ledger "
                "can be constructed - retrospective research only, never a certified "
                "historical forecasting setup",
            "vintage": {
                "kind": "current_snapshot",
                "evidence": "the archive is one living compilation (portal updated "
                    "2026-02-17, covering through 2025); the dictionary documents in-place "
                    "revision of area burned (spring aerial-photography interpretation "
                    "removes waterbodies and unburnt islands), cause "
                    "(under-investigation -> final) and location (assessment GPS -> "
                    "confirmed ignition area). Aggregate evidence measured: the 2019 "
                    "published season total was 883,411 ha while the current archive carries "
                    "791,838 ha (-10.4%). Label-flip exposure is bounded: 89 fires lie "
                    "within +-20% of the 100 ha threshold (measured). Every shipped feature "
                    "is the current-vintage value of a field documented at/before the "
                    "assessment instant; no as-of value is claimed",
            },
            "selection": {
                "kind": "prediction_time",
                "evidence": "membership is fixed at the assessment instant: a row exists "
                    "because the wildfire was discovered and assessed, never because of an "
                    "outcome; no completeness or volume gate is applied (unlike panel "
                    "releases), there is no censoring rule (every row carries a terminal "
                    "status), and both label values are retained in every window. The "
                    "population definition (all FPA wildfires) is stable; the detection "
                    "channel mix drifts (lookouts 34% of 2006 -> 21% of 2025; unplanned "
                    "42% -> 59%) and ships as the detection_agent_type feature",
            },
            "limitations": [
                "current_snapshot vintage: a single living compilation; per-fire historical "
                "values (assessment size, weather, location, area burned) cannot be "
                "reproduced as they stood at past instants",
                "latitude/longitude are the current confirmed ignition-area coordinates, "
                "revised from the originally captured assessment GPS (dictionary p6); the "
                "original assessment-era coordinates are not recoverable",
                "fire_start_date is an estimate when the exact start is unknown (dictionary "
                "p10); hours_start_to_assessment inherits that estimation",
                "timestamps carry no timezone; they are read as local Alberta operational "
                "time (America/Edmonton), an assumption confirmed against the official 2016 "
                "Horse River review but not guaranteed for every row",
                "the holdout 2021-2025 escape rate (4.11%) exceeds train (1.86%) and eval "
                "(1.85%) because 2021-2025 contains the 2023 record season - real, "
                "documented non-stationarity, not a construction defect",
                "positives cluster on extreme fire-weather days (156/79/128 distinct "
                "positive assessment dates per window): row-level scores overstate "
                "independent evidence; the day is the independence scale",
                "holdout fires are real, publicly documented events; an agent with "
                "uncontrolled internet access could look up outcomes by fire identity. The "
                "benchmark protocol keeps the holdout outside the evaluated agent's "
                "workspace, and this exposure is inherent to any retrospective public-record "
                "task, not specific to this artifact",
                "labeled eval is development/validation, never an untouched final test; the "
                "holdout is the final test and remains sealed until the design is frozen",
                "training_label_timing is unverified: no as-of ledger exists for when any "
                "per-fire record first appeared in the compilation",
            ],
            "cross_row_audit": {
                "probes": [
                    {
                        "entity_columns": ["forest_area"],
                        "time_column": "assessment_date",
                        "offset_days": 1,
                        "left": "assessment_hectares",
                        "operation": "gt",
                        "threshold": 100,
                        "name": "next_day_neighbour_size",
                        "note": "the nearest joinable structure: a same-forest-area fire "
                            "assessed the next day donates its assessment size. It is a "
                            "shared-weather covariate, not an outcome operand, so agreement "
                            "with this row's escape label is expected to be weak; declared "
                            "to measure the neighbour-day join a row-joining solver could "
                            "reach, not to argue the cluster away",
                    },
                ],
                "probes_note": "each wildfire appears exactly once ((YEAR, FIRE_NUMBER) "
                    "unique, asserted), so no serial per-entity join exists and no shipped "
                    "column of any row is derived from another row's outcome: the label "
                    "source (final area burned) and the milestone fields ship in no column "
                    "(asserted on the written headers). The remaining structure is the "
                    "same-day weather cluster, which the declared probe measures at its "
                    "nearest joinable edge",
                "rationale": "rows are per-wildfire event predictions; the runner predicts "
                    "row-wise from shipped columns, which are the crew-observed assessment "
                    "record of that fire alone. Same-day neighbours share fire weather - a "
                    "shared cause of both feature and label, not a donated outcome",
                "auxiliary_files_review": "the extract ships exactly the runner layout - "
                    "public/train.csv, public/eval.csv, private/holdout.csv, meta.json, "
                    "quality.json - plus summary.json, which carries the fetch receipt, "
                    "structural assertions, per-window coverage, per-year counts and the "
                    "measured secondary-containment diagnostics; no row-level source data "
                    "beyond the three split files and no performance metric",
            },
            "feature_evidence": {
                "fire_id": {
                    "source": "derived: YEAR + FIRE_NUMBER, the publisher's own wildfire "
                              "identity",
                    "availability": "assigned when the fire is recorded by the dispatching "
                                    "forest area; known before/at the assessment instant",
                    "status": "verified",
                },
                "assessment_ts": {
                    "source": "ASSESSMENT_DATETIME, 'the date and time the wildfire was "
                              "originally assessed' (dictionary p11)",
                    "availability": "the prediction instant itself, in naive local Alberta "
                                    "operational time",
                    "status": "verified",
                },
                "assessment_date": {
                    "source": "the calendar date of the assessment instant",
                    "availability": "calendar part of the prediction instant",
                    "status": "verified",
                },
                "day_of_week": {
                    "source": "derived arithmetically from the assessment instant",
                    "availability": "calendar",
                    "status": "verified",
                },
                "month": {
                    "source": "derived arithmetically from the assessment instant",
                    "availability": "calendar",
                    "status": "verified",
                },
                "doy_sin": {
                    "source": "derived: sin(2*pi*day_of_year/365.25) of the assessment instant",
                    "availability": "calendar",
                    "status": "verified",
                },
                "doy_cos": {
                    "source": "derived: cos(2*pi*day_of_year/365.25) of the assessment instant",
                    "availability": "calendar",
                    "status": "verified",
                },
                "forest_area": {
                    "source": "the first three letters of FIRE_NUMBER, the managing forest "
                              "area's code (10 areas measured over the full compilation)",
                    "availability": "assigned when the fire is recorded, before/at the "
                                    "assessment instant",
                    "status": "verified",
                },
                "latitude": {
                    "source": "LATITUDE, the ignition-area GPS location (dictionary p6)",
                    "availability": "a pre-instant fact of the fire's location, but the "
                                    "shipped value is the current confirmed ignition-area "
                                    "coordinate, revised from the originally captured "
                                    "assessment GPS",
                    "status": "assumed",
                    "assumption": "current-vintage revision of a pre-instant fact; the "
                                    "assessment-era coordinates are not recoverable",
                },
                "longitude": {
                    "source": "LONGITUDE, as latitude",
                    "availability": "as latitude",
                    "status": "assumed",
                    "assumption": "current-vintage revision of a pre-instant fact",
                },
                "assessment_hectares": {
                    "source": "ASSESSMENT_HECTARES, 'the size of the wildfire at the time of "
                              "assessment' (dictionary p12); 100% coverage measured",
                    "availability": "observed by the assessing crew at the instant",
                    "status": "verified",
                },
                "fire_spread_rate": {
                    "source": "FIRE_SPREAD_RATE, 'the rate of spread of the wildfire at the "
                              "time of initial assessment' in m/min (dictionary p12)",
                    "availability": "observed by the assessing crew at the instant",
                    "status": "verified",
                },
                "fire_type": {
                    "source": "FIRE_TYPE, 'the predominant fire behaviour that was observed "
                              "when the fire was originally assessed' (dictionary p12)",
                    "availability": "observed at the instant; blank where not recorded",
                    "status": "verified",
                },
                "fire_position_on_slope": {
                    "source": "FIRE_POSITION_ON_SLOPE, 'the position of the wildfire "
                              "relative to the slope it is travelling on at the time of "
                              "initial assessment' (dictionary p12)",
                    "availability": "observed at the instant; blank where not recorded",
                    "status": "verified",
                },
                "weather_conditions_over_fire": {
                    "source": "WEATHER_CONDITIONS_OVER_FIRE, 'description of the weather "
                              "conditions over the wildfire at the time of initial "
                              "assessment' (dictionary p12)",
                    "availability": "observed at the instant; blank where not recorded",
                    "status": "verified",
                },
                "temperature": {
                    "source": "TEMPERATURE, 'the temperature at the wildfire site at the "
                              "time of initial assessment', degrees Celsius (dictionary p12)",
                    "availability": "observed at the instant; blank where not recorded",
                    "status": "verified",
                },
                "relative_humidity": {
                    "source": "RELATIVE_HUMIDITY, 'the relative humidity at the wildfire "
                              "site at the time of initial assessment' (dictionary p12)",
                    "availability": "observed at the instant; blank where not recorded",
                    "status": "verified",
                },
                "wind_speed": {
                    "source": "WIND_SPEED, 'the wind speed at the wildfire site at the time "
                              "of initial assessment', km/h (dictionary p12)",
                    "availability": "observed at the instant; blank where not recorded",
                    "status": "verified",
                },
                "wind_direction": {
                    "source": "WIND_DIRECTION, 'the wind direction at the wildfire site at "
                              "the time of initial assessment' (dictionary p12)",
                    "availability": "observed at the instant; blank where not recorded",
                    "status": "verified",
                },
                "fuel_type": {
                    "source": "FUEL_TYPE, 'the predominant fuel type (vegetation cover) in "
                              "which the wildfire is burning, at the time of initial "
                              "assessment', Canadian FBP codes (dictionary p12)",
                    "availability": "observed at the instant; blank where not recorded",
                    "status": "verified",
                },
                "detection_agent_type": {
                    "source": "DETECTION_AGENT_TYPE, 'the general type of detection agent "
                              "responsible for discovering the wildfire' (dictionary p10); "
                              "5 categories, no blanks measured",
                    "availability": "fixed at discovery, before the instant",
                    "status": "verified",
                },
                "hours_report_to_assessment": {
                    "source": "derived: REPORTED_DATE ('the time and date the wildfire was "
                              "first reported to Alberta Wildfire', dictionary p11) to the "
                              "assessment instant",
                    "availability": "difference of two pre-instant timestamps; 100% coverage",
                    "status": "verified",
                },
                "hours_discovery_to_assessment": {
                    "source": "derived: DISCOVERED_DATE ('the time the detection agent first "
                              "discovered the wildfire', dictionary p10) to the assessment "
                              "instant",
                    "availability": "pre-instant; blank where the discovery timestamp is "
                                    "absent (the dictionary documents unplanned-detection "
                                    "blanks)",
                    "status": "verified",
                },
                "hours_start_to_assessment": {
                    "source": "derived: FIRE_START_DATE (estimated or witnessed fire start, "
                              "dictionary p10) to the assessment instant",
                    "availability": "pre-instant estimate; blank where absent",
                    "status": "assumed",
                    "assumption": "the start time is an estimate when unknown, and the "
                                    "current compilation may have refined it after the "
                                    "instant",
                },
            },
        },
        "positive_events": {w: {"positives": counts[w]["positives"],
                                "distinct_events": counts[w]["distinct_positive_dates"]}
                            for w in ("train", "eval", "holdout")},
        "split_windows": {"train": {"start": "2006-01-01", "end": "2016-01-01"},
                          "eval": {"start": "2016-01-01", "end": "2021-01-01"},
                          "holdout": {"start": "2021-01-01", "end": "2026-01-01"}},
        "split_counts": counts,
        "excluded_counts": {"rows_dropped": 0,
                            "note": "all 27,828 assessed wildfires are retained; the "
                                    "excluded source columns are listed in "
                                    "post_hoc_columns and label_source_columns"},
    }
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")

    # ---- summary.json ---------------------------------------------------------
    per_year = Counter(int(r["YEAR"]) for r in rows)
    winter = Counter()
    for r in rows:
        window = window_of(parse_dt(r["ASSESSMENT_DATETIME"]).year)
        if parse_dt(r["ASSESSMENT_DATETIME"]).month in (11, 12, 1, 2):
            winter[window] += 1
    band = sum(1 for r in rows if 80 <= fnum(r["CURRENT_SIZE"]) <= 120)
    final_below_assessment = sum(1 for r in rows
                                 if fnum(r["CURRENT_SIZE"]) < fnum(r["ASSESSMENT_HECTARES"]))
    assessed_at_or_above_threshold = sum(1 for r in rows
                                         if fnum(r["ASSESSMENT_HECTARES"]) >= ESCAPE_THRESHOLD_HA)
    summary = {
        "ok": True,
        "stage": "build",
        "candidate": "ab-wildfire-ia-escape",
        "source": {
            "path": str(source),
            "sha256": digest,
            "bytes": CSV_BYTES,
            "fetch_receipt": fetch_receipt,
            "provenance": "pinned publisher fetch measured on the coordinator 2026-11-06 "
                "through the cleared browser context (open.alberta.ca Cloudflare-challenges "
                "plain HTTP clients, curl 403 measured); staged at "
                "earino/dataset-factory-staging release source-abwildfire-001 "
                "(437116894, asset 718748383) and re-verified by this build",
        },
        "population": {
            "total_rows": EXPECTED_TOTAL,
            "split_rule": "assessment instant's calendar year (America/Edmonton local "
                          "operational time)",
            "per_year_record_counts": dict(sorted(per_year.items())),
            "rows_per_window": {w: counts[w]["rows"] for w in ("train", "eval", "holdout")},
            "record_year_split_rows": {"train": 15944, "eval": 5627, "holdout": 6257},
            "carryover_rows_by_window": dict(carryover),
            "winter_nov_feb_rows": {**{w: winter[w] for w in ("train", "eval", "holdout")},
                                    "total": sum(winter.values())},
        },
        "label": {
            "threshold_ha": ESCAPE_THRESHOLD_HA,
            "positives_per_window": {w: counts[w]["positives"] for w in
                                     ("train", "eval", "holdout")},
            "positive_rate_per_window": {w: counts[w]["positive_rate"] for w in
                                         ("train", "eval", "holdout")},
            "distinct_positive_dates_per_window": {w: counts[w]["distinct_positive_dates"]
                                                    for w in ("train", "eval", "holdout")},
            "band_80_120_ha": band,
            "final_below_assessment_size": final_below_assessment,
            "assessed_at_or_above_100ha": assessed_at_or_above_threshold,
        },
        "secondary_containment_not_shipped": {
            "note": "measured diagnostics of the secondary formulation only; the shipped "
                    "target is escape. The 42.0% already-controlled-at-assessment stratum "
                    "needs its own design decision and would be a separate task instance",
            "gt_72h_per_window": {w: containment[w]["gt_72h"] for w in
                                  ("train", "eval", "holdout")},
            "already_controlled_at_assessment": {
                **{w: containment[w]["already_controlled_at_assessment"]
                   for w in ("train", "eval", "holdout")},
                "total": already_controlled},
        },
        "fixtures_asserted": fixture_results,
        "cross_checks": {
            "size_class_inconsistencies": 0,
            "season_hectares_deltas": season_deltas,
            "timezone_confirmation": "official 2016 Horse River review: detected 16:03h MDT "
                "2016-05-01; record REPORTED_DATE 2016-05-01 16:03 naive local",
            "pre_instant_ordering_violations": dict(violations),
            "pre_instant_present": dict(present),
            "dispatch_after_assessment": dispatch_after,
            "unparsed_timestamps": dict(unparsed),
        },
        "normalization": {
            "cells_whitespace_trimmed": trimmed_cells,
            "timestamps_seconds_truncated": seconds_truncated,
        },
        "feature_coverage_by_window": coverage,
        "column_policy": {
            "shipped": COLUMNS,
            "label_source_columns_excluded": LABEL_SOURCE_COLUMNS,
            "post_hoc_columns_excluded": POST_HOC_COLUMNS,
        },
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")

    print(json.dumps({
        "ok": True, "stage": "build",
        "rows": {w: counts[w]["rows"] for w in ("train", "eval", "holdout")},
        "positives": {w: counts[w]["positives"] for w in ("train", "eval", "holdout")},
        "distinct_positive_dates": {w: counts[w]["distinct_positive_dates"]
                                     for w in ("train", "eval", "holdout")},
        "output": str(out),
    }), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
