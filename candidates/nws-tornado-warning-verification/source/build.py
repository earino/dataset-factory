#!/usr/bin/env python3
"""Construction for nws-tornado-warning-verification (nws-tornado-build-001).

CONSTRUCT ONLY. This script computes no AUC, no accuracy, no model, and no
reference score - the first performance metric in the job is score.py, which
runs only after the full-artifact gate passed and exact-byte --accept
re-verified the artifact (see run.sh).

Source: IEM cow API (mesonet.agron.iastate.edu/api/1/cow.json), one national
TOR-warning year pull per year 2008-2024 (storm-based polygons began
2007-10-01, so 2008 is the first full year). Label = the per-warning `verify`
boolean: >=1 tornado local storm report (cow's default 15 km LSR buffer)
inside the storm-based polygon during the valid window. The label is
REPORT-based (LSR archive), not survey-based - the build pins that distinction
with the 2022-04-16 phantom-storm fixture: Wolff et al. 2025 (arXiv
2510.25011) document all three of that storm's tornado-emergency warnings as
false alarms on NCEI-survey evidence, while cow reads verify=TRUE for two of
them (LZK 2022 #49, #50) because the false real-time tornado LSrs remain in
the LSR archive, and verify=FALSE for the third (MEG 2022 #40).

Determinism: rows are keyed (year, wfo, eventid); byte-identical duplicate
features (measured: 2013 FWD#33 x2; Joplin day file #28/#30 x2) are dropped;
same-key features with DISAGREEING verify refuse the build loudly; same-key
features with agreeing verify keep the earliest product_id. All output bytes
derive from the fetched year files plus --built-at (no wall clock).
"""
import argparse
import csv
import hashlib
import json
import math
import os
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

NAME = "nws-tornado-warning-verification"
TARGET = "verified"
POSITIVE_LABEL = 1

API = "https://mesonet.agron.iastate.edu/api/1/cow.json"
YEARS = list(range(2008, 2025))          # 17 construction units
TRAIN_YEARS = (2008, 2018)
EVAL_YEARS = (2019, 2021)
HOLDOUT_YEARS = (2022, 2024)

# Hard anchors, measured on the record-pinned probes 2026-10-19 and
# re-verified EXACTLY 2026-11-05 (bytes drift 28,389,049 -> 28,383,984 on the
# 2023 file while counts stayed identical: live recomputation, stable counts).
# The build refuses if either anchor year moved (vintage change or defect).
ANCHORS = {
    2013: {"raw_features": 1832, "verified": 441},
    2023: {"raw_features": 2531, "verified": 656},
}

# Known-event fixtures, pinned from measurements 2026-11-05 BEFORE launch:
#   (year, wfo, eventid, expected cow verify, note)
# Joplin EF-5 2011-05-22: the tornado's LSrs must verify the SGF warnings that
#   covered it (externally certain; NWS service assessment / NCEI track).
# Phantom storm 2022-04-16 (northern Arkansas, Wolff et al. 2025 + IEM
#   tornado-emergency archive): the three emergency warnings' MEASURED cow
#   verdicts, two TRUE via the false real-time LSrs, one FALSE.
FIXTURES = [
    (2011, "SGF", 31, 1, "Joplin tornado 2011-05-22: warning in effect over "
                          "Jasper/Newton/Lawrence MO as the EF-5 crossed Joplin"),
    (2011, "SGF", 32, 1, "Joplin tornado 2011-05-22: follow-up warning over "
                          "Newton/Lawrence/Jasper MO"),
    (2022, "LZK", 49, 1, "phantom storm 2022-04-16 00:09Z: tornado emergency "
                         "(IEM archive); cow verify TRUE via the false real-time "
                         "tornado LSR - survey later found straight-line winds "
                         "(Wolff et al. 2025; Navarro 2022)"),
    (2022, "LZK", 50, 1, "phantom storm 2022-04-16 00:45Z: tornado emergency "
                         "in the issued text; cow verify TRUE via the same "
                         "false LSR class"),
    (2022, "MEG", 40, 0, "phantom storm 2022-04-16 01:05Z (eastern AR, same "
                         "storm): tornado emergency per IEM archive; cow verify "
                         "FALSE - no LSR arrived in this polygon"),
]

ID_COLUMNS = ["row_id"]
FEATURES = [
    "wfo", "fcster",
    "issue_doy", "issue_hour", "issue_weekday", "issue_month", "duration_min",
    "hail_tag_in", "wind_tag_mph",
    "svr_tornado_possible", "tor_in_svrtorpossible",
    "county_count", "county_area_km2", "polygon_area_km2", "perimeter",
    "shared_border_pct", "size_reduction_pct", "polygon_county_ratio",
    "lat0", "lon0",
]
CARRY_COLUMNS = ["issue_ts", "issue_date"]
HIGH_CARDINALITY = ["row_id", "fcster", "issue_ts", "issue_date"]
LABEL_SOURCE_COLUMNS = [
    "verify, stormreports, stormreports_all, lead0, areaverify, statuses, "
    "status, product_text, link (cow per-event fields that encode or time the "
    "outcome, or URL payloads never fetched for v1) - never shipped"],
POST_HOC_COLUMNS = [
    "stormreports, stormreports_all, lead0, areaverify, statuses, status "
    "(outcome fields the publisher computes after the valid window) - never "
    "shipped",
]
COLUMNS = ID_COLUMNS + FEATURES + CARRY_COLUMNS + [TARGET]
LAYOUT = {"train": "public/train.csv", "eval": "public/eval.csv",
          "holdout": "private/holdout.csv"}

PREDICTION_QUESTION = (
    "For an NWS tornado warning at the moment it is issued (its storm-based "
    "polygon, its tags, its issuing office), will it be verified - will at "
    "least one tornado local storm report fall inside the polygon during the "
    "warning's valid time?")
PREDICTION_TIME = (
    "The warning's issue instant (event_time): every shipped feature is a "
    "field of the issued warning product itself - issuing WFO, forecaster of "
    "record, issue/expire timestamps (hence calendar and duration), the "
    "hail/wind tags and the tornado-possible lineage flags as served by the "
    "IEM cow per-event record, the warned county list (count), and the "
    "storm-based polygon geometry (area, perimeter, shared-border ratio, "
    "size reduction, reference point). The label is decided afterwards by "
    "which tornado reports occur inside the polygon while the warning is "
    "live; the cow fields that encode it never ship.")


def log(message: str) -> None:
    print(f"[build {time.strftime('%H:%M:%S')}] {message}", flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url: str, dest: Path, attempts: int = 3, backoff: float = 5.0) -> dict:
    last = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url)  # honest default urllib UA
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=300) as r, \
                    open(dest, "wb") as handle:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    handle.write(chunk)
            size = dest.stat().st_size
            if size == 0:
                raise RuntimeError("zero-length body")
            return {"url": url, "bytes": size,
                    "seconds": round(time.time() - t0, 1),
                    "sha256": sha256_file(dest)}
        except Exception as exc:  # noqa: BLE001
            last = exc
            log(f"fetch attempt {attempt + 1} failed: {type(exc).__name__}: {exc}")
            time.sleep(backoff * (attempt + 1))
    raise RuntimeError(f"fetch failed after {attempts} attempts: {url}: {last}")


def year_url(year: int) -> str:
    return (f"{API}?begints={year}-01-01T00:00Z&endts={year}-12-31T23:59Z"
            "&phenomena=TO&significance=W")


def parse_timestamp(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:19], "%Y-%m-%dT%H:%M:%S").replace(
            tzinfo=timezone.utc)
    except ValueError:
        return None


def to_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int_or_none(value):
    f = to_float(value)
    return None if f is None else int(round(f))


def as_flag(value):
    """cow booleans arrive as 't'/'f'/True/False/None."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    text = str(value).strip().lower()
    if text in ("t", "true", "1", "y", "yes"):
        return 1
    if text in ("f", "false", "0", "n", "no"):
        return 0
    return None


def fmt(value):
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return f"{value:g}"
    return value


def build_rows_from_features(feats: list, year: int, ledger: dict):
    """Dedupe + derive one row per (year, wfo, eventid)."""
    groups = defaultdict(list)
    for feat in feats:
        p = feat.get("properties", {})
        key = (p.get("year"), p.get("wfo"), p.get("eventid"))
        groups[(key[0] or year, key[1], key[2])].append(p)

    rows = []
    dup_identical = 0
    dup_kept_earliest = 0
    for (y, wfo, eventid), props in sorted(groups.items(), key=lambda kv: str(kv[0])):
        if len(props) > 1:
            serialized = {json.dumps(p, sort_keys=True, default=str) for p in props}
            verifies = {as_flag(p.get("verify")) for p in props}
            if None in verifies or len(verifies - {None}) > 1:
                raise RuntimeError(
                    f"DUPLICATE EVENT WITH DISAGREEING verify: {y} {wfo} "
                    f"#{eventid} - refusing; named source evidence in ledger")
            if len(serialized) == 1:
                dup_identical += 1
            else:
                dup_kept_earliest += 1
                ledger["duplicate_kept_earliest_events"].append(
                    {"year": y, "wfo": wfo, "eventid": eventid})
            props = sorted(props, key=lambda p: str(p.get("product_id") or ""))
            props = [props[0]]
        p = props[0]

        issue = parse_timestamp(p.get("issue"))
        expire = parse_timestamp(p.get("expire"))
        if issue is None or expire is None or expire <= issue:
            ledger["unparsable_window_rows"].append(
                {"year": y, "wfo": wfo, "eventid": eventid,
                 "issue": p.get("issue"), "expire": p.get("expire")})
            continue
        verify = as_flag(p.get("verify"))
        if verify is None:
            raise RuntimeError(f"missing verify on {y} {wfo} #{eventid}")
        ugc = p.get("ar_ugc") or []
        if isinstance(ugc, str):
            ugc = [ugc] if ugc else []
        carea = to_float(p.get("carea"))
        parea = to_float(p.get("parea"))
        ratio = (parea / carea) if (parea is not None and carea) else None
        reduction = (((carea - parea) / carea) * 100.0
                     if (parea is not None and carea and carea > 0) else None)
        row = {
            "row_id": f"{y}-{wfo}-{eventid:04d}",
            "year": y, "wfo": wfo, "eventid": eventid,
            "issue_ts": issue.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "issue_date": issue.date().isoformat(),
            "issue_doy": issue.timetuple().tm_yday,
            "issue_hour": issue.hour,
            "issue_weekday": issue.weekday(),
            "issue_month": issue.month,
            "duration_min": (expire - issue).total_seconds() / 60.0,
            "hail_tag_in": to_float(p.get("hailtag")),
            "wind_tag_mph": to_float(p.get("windtag")),
            "svr_tornado_possible": as_flag(p.get("svr_tornado_possible")),
            "tor_in_svrtorpossible": as_flag(p.get("tor_in_svrtorpossible")),
            "county_count": len(ugc),
            "county_area_km2": carea,
            "polygon_area_km2": parea,
            "perimeter": to_float(p.get("perimeter")),
            "shared_border_pct": to_float(p.get("sharedborder")),
            "size_reduction_pct": reduction,
            "polygon_county_ratio": ratio,
            "lat0": to_float(p.get("lat0")),
            "lon0": to_float(p.get("lon0")),
            "verified": verify,
        }
        rows.append(row)
    return rows, dup_identical, dup_kept_earliest


def split_of(year: int) -> str:
    if TRAIN_YEARS[0] <= year <= TRAIN_YEARS[1]:
        return "train"
    if EVAL_YEARS[0] <= year <= EVAL_YEARS[1]:
        return "eval"
    if HOLDOUT_YEARS[0] <= year <= HOLDOUT_YEARS[1]:
        return "holdout"
    return "out_of_window"


def check_anchor(year: int, raw_features: int, verified: int):
    anchor = ANCHORS.get(year)
    if not anchor:
        return
    if raw_features != anchor["raw_features"] or verified != anchor["verified"]:
        raise RuntimeError(
            f"ANCHOR MISMATCH {year}: measured raw_features={raw_features} "
            f"verified={verified}, pinned anchor={anchor}. The vintage moved "
            "or the parse is wrong; refusing.")


def check_fixtures(all_rows: list, dry_run: bool = False):
    by_key = {(r["year"], r["wfo"], r["eventid"]): r for r in all_rows}
    results = []
    for (year, wfo, eventid, expected, note) in FIXTURES:
        row = by_key.get((year, wfo, eventid))
        if row is None:
            if dry_run:
                # a dry run constructs only the cached years; the full run
                # must contain every fixture warning
                continue
            raise RuntimeError(
                f"FIXTURE ROW MISSING: {year} {wfo} #{eventid} ({note}) - the "
                "window must contain every fixture warning")
        if row["verified"] != expected:
            raise RuntimeError(
                f"FIXTURE MISMATCH: {year} {wfo} #{eventid} expected "
                f"verify={expected} measured verify={row['verified']} ({note})")
        results.append({"year": year, "wfo": wfo, "eventid": eventid,
                        "expected": expected, "measured": row["verified"],
                        "issue_ts": row["issue_ts"], "note": note,
                        "status": "asserted"})
    log(f"fixtures: {len(results)}/{len(FIXTURES)} asserted OK")
    return results


def write_split(path: Path, rows: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        for row in rows:
            writer.writerow([fmt(row.get(c)) for c in COLUMNS])


def write_meta(out: Path, split_stats: dict):
    meta = {
        "name": NAME,
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": ID_COLUMNS,
        "columns": COLUMNS,
        "split_description": (
            "temporal by issue year: train 2008-2018, eval 2019-2021, "
            "holdout 2022-2024 (windows contiguous and disjoint)"),
        "rows": {k: v["rows"] for k, v in split_stats.items()},
        "positive_rate": {k: v["positive_rate"] for k, v in split_stats.items()},
        "built_at": BUILT_AT,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")


def quality_document(out: Path, split_stats: dict, fixtures: list,
                     fetch_info: dict, ledger: dict, built_at: str):
    positive_events = {k: {"positives": v["positives"],
                           "distinct_events": v["positive_days"]}
                       for k, v in split_stats.items()}
    quality = {
        "name": NAME,
        "task": {"question": PREDICTION_QUESTION,
                 "prediction_time": PREDICTION_TIME},
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "time_column": "issue_date",
        "event_key_column": "issue_date",
        "event_key_note": (
            "issue_date (UTC) is the warning's issue day: verified warnings "
            "cluster on outbreak days, so the conservative independent-event "
            "count is the distinct positive issue days per split, which the "
            "gate recomputes from the rows"),
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "feature_documentation": (
            "every shipped feature is a field of the issued warning product "
            "as served by the IEM cow per-event record: wfo/fcster are the "
            "issuing office and forecaster of record; issue_doy/hour/weekday/"
            "month and duration_min derive from the issue/expire timestamps "
            "printed on the product; hail_tag_in/wind_tag_mph are the "
            "product's IBW hail (inches) and wind (mph) tags (empty when the "
            "product carried none); svr_tornado_possible and "
            "tor_in_svrtorpossible are the cow lineage flags for the "
            "tornado-possible tag on the parent SVR; county_count and "
            "county_area_km2 come from the warned UGC county list; "
            "polygon_area_km2, perimeter, shared_border_pct and lat0/lon0 "
            "are the storm-based polygon statistics (EPSG 9311, publisher "
            "documented on the cow page); size_reduction_pct = "
            "(C-P)/C x 100 and polygon_county_ratio = P/C are derived from "
            "the same two areas. The outcome fields (verify, stormreports, "
            "stormreports_all, lead0, areaverify, statuses, status) and the "
            "never-fetched product_text/link URLs are excluded from every "
            "shipped column."),
        "carry_columns": CARRY_COLUMNS,
        "id_columns": ID_COLUMNS,
        "high_cardinality_columns": HIGH_CARDINALITY,
        "high_cardinality_note": (
            "row_id is unique per row; issue_ts is row-unique; issue_date "
            "(~5,900 distinct days over ~37k rows) and fcster (~2,600 "
            "distinct forecasters) carry many levels with fewer than five "
            "rows in the narrow splits. All four are declared rather than "
            "scored: issue_ts and issue_date are the timing/cluster carry "
            "columns (the stock runner drops both as >1000-level strings), "
            "fcster is a genuine at-issuance feature whose per-forecaster "
            "statistics would be memorization at this density, and row_id is "
            "the row key. None is a leak: none encodes the outcome."),
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "post_hoc_columns": POST_HOC_COLUMNS,
        "measurements": [
            {"column": "issue_doy", "unit": "day of year 1-366 (UTC)",
             "frame": "calendar day of the warning's issue instant"},
            {"column": "issue_hour", "unit": "hour 0-23 (UTC)",
             "frame": "clock hour of the issue instant"},
            {"column": "issue_weekday", "unit": "weekday index 0=Monday (UTC)",
             "frame": "weekday of the issue instant"},
            {"column": "issue_month", "unit": "month 1-12 (UTC)",
             "frame": "calendar month of the issue instant"},
            {"column": "duration_min", "unit": "minutes",
             "frame": "expire - issue as printed on the product"},
            {"column": "hail_tag_in", "unit": "inches (IBW hail tag)",
             "frame": "the product's own hail tag; empty = no tag issued"},
            {"column": "wind_tag_mph", "unit": "mph (IBW wind tag)",
             "frame": "the product's own wind tag; empty = no tag issued"},
            {"column": "svr_tornado_possible", "unit": "binary 0/1",
             "frame": "cow per-event flag as served; empty when absent"},
            {"column": "tor_in_svrtorpossible", "unit": "binary 0/1",
             "frame": "cow per-event flag as served; empty when absent"},
            {"column": "county_count", "unit": "count of UGC county codes",
             "frame": "length of the product's warned county list"},
            {"column": "county_area_km2", "unit": "square kilometres",
             "frame": "total area of the warned counties, EPSG 9311 "
                      "(publisher-documented on the cow page)"},
            {"column": "polygon_area_km2", "unit": "square kilometres",
             "frame": "storm-based polygon area, EPSG 9311 "
                      "(publisher-documented)"},
            {"column": "perimeter",
             "unit": "cow 'perimeter' statistic (publisher does not document "
                     "its unit; planar length of the polygon in the same "
                     "EPSG 9311 computation)",
             "frame": "storm-based polygon, as served"},
            {"column": "shared_border_pct", "unit": "percent 0-100",
             "frame": "portion of the SBW perimeter coinciding with a "
                      "political boundary (publisher-documented)"},
            {"column": "size_reduction_pct", "unit": "percent 0-100",
             "frame": "(county_area - polygon_area)/county_area x 100, the "
                      "cow 'Size %' statistic recomputed from the two "
                      "served areas"},
            {"column": "polygon_county_ratio", "unit": "ratio",
             "frame": "polygon_area_km2 / county_area_km2"},
            {"column": "lat0", "unit": "degrees (cow lat0 reference point)",
             "frame": "as served by the cow per-event record"},
            {"column": "lon0", "unit": "degrees (cow lon0 reference point)",
             "frame": "as served by the cow per-event record"},
        ],
        "known_event": {
            "name": "Joplin MO EF-5 tornado, 2011-05-22 (and the 2022-04-16 "
                    "northern-Arkansas phantom-storm warnings)",
            "expected_verdict": "exceeds",
            "per_warning": fixtures,
            "source": (
                "Joplin: NWS service assessment and the NCEI storm-event "
                "record - SGF warnings #31/#32 (2011) must read verify=1. "
                "Phantom storm: Wolff et al. 2025, arXiv 2510.25011 ('all 3 "
                "tornado emergency false alarms... same nontornadic "
                "thunderstorm in northern Arkansas on 16 April 2022') with "
                "the IEM tornado-emergency archive (api/1/nws/emergencies.json) "
                "identifying LZK #49, LZK #50, MEG #40; cow's LSR-based "
                "verify reads 1/1/0 for them because the false real-time "
                "tornado LSrs remain in the LSR archive - the label is "
                "report-based, the paper's false-alarm stat is survey-based, "
                "and the difference is the documented semantics caveat"),
        },
        "timing": {
            "prediction_instant": {
                "kind": "event_time",
                "period": "the warning's issue instant",
                "days_after_period_end": 0,
                "citation": (
                    "the warning product IS the event: an NWS TOR warning is "
                    "a complete administrative record at its issue "
                    "timestamp, and every shipped feature is printed on that "
                    "product (issuing WFO, forecaster, issue/expire, county "
                    "list, polygon, tags). The verification outcome is "
                    "decided by LSRs that occur during the valid window, "
                    "after the instant."),
            },
            "features": {
                "period": "the warning's issue instant",
                "published_days_after_period_end": 0,
                "source_kind": "administrative_record",
            },
            "row_selection": {
                "latest_period_used": "the warning's own issue instant",
                "fields": ["issue/expire window year (split assignment)",
                           "wfo", "eventid", "issue/expire", "county list",
                           "polygon statistics", "tags"],
                "basis": (
                    "every TOR warning (phenomena=TO, significance=W) issued "
                    "in the split years 2008-2024 is a row: selection is by "
                    "issue time only and never conditions on the outcome or "
                    "on any post-instant field. The storm-based-warning era "
                    "begins 2007-10-01, so 2008 is the first full window "
                    "year; no warning is dropped for verification status, "
                    "thin days, or any label-related property."),
            },
            "observations": [],
        },
        "split_windows": {
            "train": {"start": f"{TRAIN_YEARS[0]}-01-01",
                      "end": f"{EVAL_YEARS[0]}-01-01"},
            "eval": {"start": f"{EVAL_YEARS[0]}-01-01",
                     "end": f"{HOLDOUT_YEARS[0]}-01-01"},
            "holdout": {"start": f"{HOLDOUT_YEARS[0]}-01-01",
                        "end": f"{HOLDOUT_YEARS[1] + 1}-01-01"},
        },
        "split_boundaries": {
            "train": "issue years 2008-2018 (window end exclusive)",
            "eval": "issue years 2019-2021 (window end exclusive)",
            "holdout": "issue years 2022-2024 (window end exclusive)",
        },
        "positive_events": positive_events,
        "positive_events_note": (
            "positives and distinct positive issue days per split, "
            "recomputed from the written rows; the gate re-verifies"),
        "expected_duplicate_ids": 0,
        "id_columns_are_entity_keys": True,
        "id_columns_note": (
            "row_id = year-WFO-eventid names exactly one TOR warning with "
            "exactly one cow verify verdict; after the measured "
            "byte-identical duplicate features are dropped the identifier "
            "never repeats within or across splits"),
        "splits": LAYOUT,
        "evaluation_contract": {
            "use": "retrospective_research",
            "access": "isolated_rows",
            "training_label_timing": "unverified",
            "vintage": {
                "kind": "as_of",
                "evidence": (
                    "the cow API is a live recomputation over the NWS "
                    "warning archive and the LSR archive; no historical "
                    "vintages exist. Measured 2026-11-05: the 2023 year "
                    "file changed bytes (28,389,049 on 2026-10-19 -> "
                    "28,383,984) while its counts stayed exactly 2,531 / "
                    "656, and the 2013 anchor stayed exactly 1,832 / 441. "
                    "The artifact is therefore a current-vintage snapshot "
                    "declared as such; historical forecasting is not "
                    "claimed and no point-in-time reconstruction is."),
            },
            "selection": {
                "kind": "prediction_time",
                "evidence": (
                    "rows are every TOR warning in the window years keyed "
                    "and split by issue time only; the anchor-year and "
                    "fixture assertions ran at construction on the fetched "
                    "bytes; no outcome-conditioned selection exists anywhere "
                    "in the build."),
            },
            "limitations": [
                "the label is LSR-based (a tornado report inside the polygon "
                "during the valid window), not survey-based: a false "
                "real-time tornado LSR verifies a warning that a later "
                "damage survey classified as a false alarm (the pinned "
                "2022-04-16 phantom-storm fixture exists to document exactly "
                "this), and an LSR arriving after the valid window does not "
                "verify even if a tornado occurred",
                "training-label timing is UNVERIFIED: no historical cow "
                "vintages exist, so when past instants' labels were "
                "finalized cannot be established; the artifact is "
                "retrospective research, never a certified historical "
                "forecasting setup",
                "IEM states the data is unofficial and for educational "
                "purposes; the verification label is IEM's computation over "
                "official NWS warnings and reports, not an NWS official "
                "verification product",
                "warnings issued by offices for US territories and Alaska/"
                "Hawaii are included in the national pulls; base-rate drift "
                "across the era (warning POD/FAR evolution) is a documented "
                "source property and is reported per issue year",
                "pre-2016 era warnings may sparsely carry the IBW tags and "
                "lineage flags; missing tags are empty cells, not zeros",
            ],
            "feature_evidence": {
                "row_id": {"source": "row key year-WFO-eventid",
                           "availability": "identity of the row, printed on "
                                           "the product at issuance",
                           "status": "verified"},
                "wfo": {"source": "cow per-event field wfo",
                        "availability": "issuing office, on the product at "
                                        "issuance",
                        "status": "verified"},
                "fcster": {"source": "cow per-event field fcster (forecaster "
                                     "of record)",
                           "availability": "printed on the product at "
                                           "issuance",
                           "status": "assumed",
                           "assumption": "current-vintage archive value; the "
                                         "cow record is a live "
                                         "recomputation with no historical "
                                         "vintages"},
                "issue_doy": {"source": "derived from the product's issue "
                                        "timestamp",
                              "availability": "on the product at issuance",
                              "status": "verified"},
                "issue_hour": {"source": "derived from the product's issue "
                                         "timestamp",
                               "availability": "on the product at issuance",
                               "status": "verified"},
                "issue_weekday": {"source": "derived from the product's issue "
                                            "timestamp",
                                  "availability": "on the product at "
                                                  "issuance",
                                  "status": "verified"},
                "issue_month": {"source": "derived from the product's issue "
                                          "timestamp",
                                "availability": "on the product at issuance",
                                "status": "verified"},
                "duration_min": {"source": "expire - issue, both printed on "
                                           "the product",
                                 "availability": "on the product at "
                                                  "issuance",
                                 "status": "verified"},
                "hail_tag_in": {"source": "cow per-event field hailtag "
                                          "(product's IBW hail tag)",
                                "availability": "on the product at issuance; "
                                                "empty = no tag",
                                "status": "assumed",
                                "assumption": "inherits the current-vintage "
                                              "assumption"},
                "wind_tag_mph": {"source": "cow per-event field windtag "
                                           "(product's IBW wind tag)",
                                 "availability": "on the product at issuance; "
                                                  "empty = no tag",
                                 "status": "assumed",
                                 "assumption": "inherits the current-vintage "
                                               "assumption"},
                "svr_tornado_possible": {
                    "source": "cow per-event flag (tornado-possible lineage)",
                    "availability": "derivable from the warning's own "
                                    "product lineage at issuance",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "tor_in_svrtorpossible": {
                    "source": "cow per-event flag (tornado-possible tag "
                              "lineage)",
                    "availability": "derivable from the warning's own "
                                    "product lineage at issuance",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "county_count": {"source": "length of the product's warned "
                                           "UGC county list",
                                 "availability": "on the product at issuance",
                                 "status": "verified"},
                "county_area_km2": {
                    "source": "cow per-event field carea (county area sum, "
                              "EPSG 9311)",
                    "availability": "geography of the warned counties, fixed "
                                    "at issuance",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "polygon_area_km2": {
                    "source": "cow per-event field parea (polygon area, "
                              "EPSG 9311)",
                    "availability": "the polygon printed on the product at "
                                    "issuance",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "perimeter": {
                    "source": "cow per-event field perimeter",
                    "availability": "the polygon printed on the product at "
                                    "issuance",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "shared_border_pct": {
                    "source": "cow per-event field sharedborder (political-"
                              "boundary perimeter share)",
                    "availability": "the polygon and county geography, fixed "
                                    "at issuance",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "size_reduction_pct": {
                    "source": "derived: (county_area_km2 - polygon_area_km2)"
                              " / county_area_km2 x 100 (the cow 'Size %')",
                    "availability": "derived from two at-issuance values",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "polygon_county_ratio": {
                    "source": "derived: polygon_area_km2 / county_area_km2",
                    "availability": "derived from two at-issuance values",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "lat0": {"source": "cow per-event reference point lat0",
                         "availability": "the polygon printed on the product "
                                         "at issuance",
                         "status": "assumed",
                         "assumption": "inherits the current-vintage "
                                       "assumption"},
                "lon0": {"source": "cow per-event reference point lon0",
                         "availability": "the polygon printed on the product "
                                         "at issuance",
                         "status": "assumed",
                         "assumption": "inherits the current-vintage "
                                       "assumption"},
                "issue_ts": {"source": "the product's issue timestamp",
                              "availability": "the instant itself",
                              "status": "verified"},
                "issue_date": {"source": "UTC date of the issue timestamp",
                               "availability": "the instant itself",
                               "status": "verified"},
            },
            "cross_row_audit": {
                "probes": [],
                "rationale": (
                    "no cross-row probe applies: every shipped feature is a "
                    "within-row field of the warning's own issued product, "
                    "and no shipped column aggregates, copies or references "
                    "another row's values or outcome. The only outcome-"
                    "bearing field (verify) is the target and ships only as "
                    "the target. A solver may of course derive priors from "
                    "training-row labels it can already see - that is "
                    "ordinary training-data usage under isolated_rows "
                    "access, not an artifact exposure. The same-day-earlier-"
                    "warning exposure the record flagged lives in the "
                    "PERSISTENCE REFERENCE (score.py), which by design uses "
                    "an earlier warning's outcome with a declared 30-minute "
                    "outcome-availability assumption; references are not "
                    "shipped columns, so no blind join over shipped bytes "
                    "can recover a later row's label."),
                "auxiliary_files_review": (
                    "the artifact ships exactly public/train.csv, "
                    "public/eval.csv, private/holdout.csv, meta.json and "
                    "quality.json; no joint label matrix, no auxiliary "
                    "features file, no solver-visible file beyond these"),
            },
        },
        "built_at": built_at,
        "source_fetches": fetch_info,
        "row_ledger": {k: v for k, v in ledger.items()},
    }
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")


def main(argv=None) -> int:
    global BUILT_AT
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--built-at", required=True)
    parser.add_argument("--summary-out", required=True)
    parser.add_argument("--dry-run", action="store_true",
                        help="construct only from cached year files (no "
                             "gate-relevant anchor years may be skipped)")
    parser.add_argument("--cache-dir", default=None,
                        help="directory holding cached cow_<year>.json files "
                             "for --dry-run")
    args = parser.parse_args(argv)
    BUILT_AT = args.built_at

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)

    fetch_info = {}
    ledger = {
        "per_year": {},
        "duplicate_identical_dropped_total": 0,
        "duplicate_kept_earliest_events": [],
        "unparsable_window_rows": [],
        "raw_feature_total": 0,
    }
    all_rows = []
    for year in YEARS:
        dest = work / f"cow_{year}.json"
        cached = args.cache_dir and (Path(args.cache_dir) / f"cow_{year}.json").is_file()
        if args.dry_run and not cached:
            log(f"dry run: no cached file for {year}, skipping year")
            continue
        if cached:
            source = str(Path(args.cache_dir) / f"cow_{year}.json")
            import shutil
            shutil.copyfile(source, dest)
            info = {"url": year_url(year), "bytes": dest.stat().st_size,
                    "seconds": 0.0, "sha256": sha256_file(dest), "cached": True}
        else:
            info = fetch(year_url(year), dest)
        fetch_info[str(year)] = info

        with dest.open() as handle:
            data = json.load(handle)
        feats = data.get("events", {}).get("features", [])
        stats = data.get("stats", {})
        raw_verified = sum(1 for f in feats
                           if as_flag(f["properties"].get("verify")) == 1)
        ledger["raw_feature_total"] += len(feats)
        check_anchor(year, len(feats), raw_verified)
        rows, dup_identical, dup_kept = build_rows_from_features(feats, year, ledger)
        ledger["duplicate_identical_dropped_total"] += dup_identical
        if dup_identical or dup_kept:
            ledger["duplicate_kept_earliest_events"] = ledger.get(
                "duplicate_kept_earliest_events", [])
        verified_rows = sum(r["verified"] for r in rows)
        # stats cross-check: the publisher's own aggregate must agree
        if stats.get("events_total") not in (None, len(feats)):
            raise RuntimeError(
                f"{year}: stats.events_total={stats.get('events_total')} "
                f"!= features {len(feats)}")
        if stats.get("events_verified") not in (None, raw_verified):
            raise RuntimeError(
                f"{year}: stats.events_verified={stats.get('events_verified')}"
                f" != counted {raw_verified}")
        ledger["per_year"][str(year)] = {
            "raw_features": len(feats), "rows": len(rows),
            "verified_rows": verified_rows, "verified_rate": round(
                verified_rows / len(rows), 4) if rows else None,
            "distinct_wfos": len({r["wfo"] for r in rows}),
            "active_days": len({r["issue_date"] for r in rows}),
            "positive_days": len({r["issue_date"] for r in rows
                                  if r["verified"]}),
            "sha256": info["sha256"], "bytes": info["bytes"],
            "duplicate_identical": dup_identical,
        }
        log(f"{year}: {len(feats)} features -> {len(rows)} rows, "
            f"{verified_rows} verified, dup_identical={dup_identical}")
        all_rows.extend(rows)
        del data, feats

    if args.dry_run:
        present = sorted(ledger["per_year"])
        missing_anchors = [y for y in ANCHORS if str(y) not in present]
        if missing_anchors:
            raise RuntimeError(f"dry run must include the anchor years: {missing_anchors}")

    fixtures = check_fixtures(all_rows, dry_run=args.dry_run)

    rows_by_split = {"train": [], "eval": [], "holdout": []}
    out_of_window = 0
    for row in sorted(all_rows, key=lambda r: (r["issue_ts"], r["wfo"], r["eventid"])):
        split = split_of(row["year"])
        if split == "out_of_window":
            out_of_window += 1
        else:
            rows_by_split[split].append(row)
    if out_of_window:
        raise RuntimeError(f"{out_of_window} rows outside the split windows")

    split_stats = {}
    for split, rel in LAYOUT.items():
        rows = rows_by_split[split]
        write_split(out / rel, rows)
        positives = sum(r["verified"] for r in rows)
        split_stats[split] = {
            "rows": len(rows), "positives": positives,
            "negative": len(rows) - positives,
            "positive_rate": round(positives / len(rows), 6) if rows else None,
            "positive_days": len({r["issue_date"] for r in rows
                                  if r["verified"]}),
            "issue_years": sorted({r["year"] for r in rows}),
            "missing_cells": {c: sum(1 for r in rows if r.get(c) is None)
                             for c in FEATURES},
        }
        log(f"{split}: {split_stats[split]['rows']} rows, "
            f"{positives} positives "
            f"({split_stats[split]['positive_days']} positive days)")

    write_meta(out, split_stats)
    quality_document(out, split_stats, fixtures, fetch_info, ledger, BUILT_AT)

    summary = {
        "name": NAME,
        "built_at": BUILT_AT,
        "dry_run": args.dry_run,
        "years_fetched": sorted(fetch_info),
        "fetch_info": fetch_info,
        "split_stats": split_stats,
        "fixtures": fixtures,
        "row_ledger": ledger,
        "quality_sha256": sha256_file(out / "quality.json"),
        "meta_sha256": sha256_file(out / "meta.json"),
    }
    Path(args.summary_out).write_text(json.dumps(summary, indent=1) + "\n")
    log(f"done: {sum(v['rows'] for v in split_stats.values())} rows written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
