#!/usr/bin/env python3
"""Construction script for the `who-flunet-activity-exceedance` candidate.

Task: for a WHO FluNet reporting country, will influenza test positivity in ISO
week W+4 exceed a fixed 10% activity threshold, given that country's weekly
laboratory series through ISO week W? One row per (country, prediction week W);
the label is computed from week W+4's row only.

Where this runs
---------------
On a temporary worker (the record's construction step says: single publisher
CSV, 30.8 MiB, one request). `--source-url` can point at a bounded year-filtered
slice for a local smoke exercise, with `--smoke` relaxing the split-capacity and
fixture-coverage assertions that a partial window cannot carry. The full run
uses the default URL and enforces everything.

Frame rules (from the candidate record; each is measured and reported)
----------------------------------------------------------------------
* Grain: country x ISO week, the three ORIGIN_SOURCE streams summed (the table
  grain is country x ISO week x ORIGIN_SOURCE; France 2025 measured 104 rows =
  52 weeks x 2 streams).
* Prediction instant: the Sunday closing week W. Every shipped feature is
  derived from weekly counts for weeks <= W. The target is week W+4's row.
* Label frame: positivity = INF_ALL / (INF_ALL + INF_NEGATIVE) on the target
  week, requiring denominator >= 50 (the record's floor) AND systematic
  negative reporting in the target week's country-year: >= 4 specimen-bearing
  weeks and >= 50% of them reporting INF_NEGATIVE >= 1. The negatives rule is
  the fix for the measured trap - pre-2015 rows mostly lack INF_NEGATIVE, so a
  positivity computed from them is 100% by construction (1995-2004 measured
  931/931 country-weeks positive, the uniform-result frame-error signature).
  The build reports pre-rule vs post-rule rates for that window as the
  acceptance test for the rule.
* Prediction week W also requires denominator >= 50 so the feature week is
  itself well measured.
* Threshold and lead are pinned by a named known-event fixture asserted at
  build time from the source: France's 2024-25 season - the blended peak
  weekly positivity must exceed 0.15 (measured 0.238 in the week of
  2025-01-27) and July-August off-season weeks must stay under 0.10 (measured
  0.007). The record's earlier ">40% at peak" was a candidate figure for a
  sentinel-only curve of a stronger season; this frame sums ORIGIN_SOURCE.

Leakage discipline
------------------
The label source columns (INF_ALL, INF_NEGATIVE of week W+4, and the derived
target rate) are NEVER written into any shipped file; only the binary `exceeds`
ships. A truncation self-check recomputes a sample of rows' features against a
series copy that physically contains no weeks after W, so any accidental
future-week access fails loudly instead of shipping.

Runner contract: public/train.csv, public/eval.csv, private/holdout.csv,
meta.json, quality.json - the layout `skills/dataset-qualification/` gates.
Splits are temporal by the prediction week's ISO year: train <= 2019,
eval 2020-2022, holdout 2023 onward.

Data dictionary (shipped columns)
---------------------------------
row_id          id: "<ISO2>-<iso_year>W<iso_week>" of the prediction week W.
week_start      Monday of prediction week W, ISO date (the time column).
country_year    "<ISO2>-<ISO year of the TARGET week W+4>" - the clustered-event
                key: positives arrive in country-seasons, so a score's
                uncertainty is quoted against distinct country-years.
exceeds         target: 1 iff week W+4 positivity > 0.10 under the label frame.
iso2            country code (publisher's ISO2 field).
whoregion,      publisher's static country metadata (VIW_FNT row of week W):
hemisphere,       WHO region, hemisphere, influenza transmission zone.
itz
iso_year,       calendar position of the prediction week, knowable at the
iso_week          prediction instant.
*_w             counts of week W itself, ORIGIN_SOURCE streams summed:
                specimens_w = SPEC_PROCESSED_NB; inf_a_w/inf_b_w = INF_A/INF_B
                detections; inf_all_w, inf_negative_w = INF_ALL, INF_NEGATIVE;
                denom_w = inf_all_w + inf_negative_w; positivity_w =
                inf_all_w / denom_w (never -1 here: the prediction week requires
                denom_w >= 50). Subtype/lineage counts: ah1_w, ah3_w,
                ah1n12009_w, bvic_w (sum of the four BVIC_* lineage columns),
                byam_w. Non-influenza respiratory detections: adeno_w, boca_w,
                human_corona_w, metapneumo_w, parainfluenza_w, rhino_w, rsv_w.
lag{1..4}_      positivity of week W-lag; -1.0 when that week has no measurable
positivity      positivity (absent or no specimens) - a sentinel outside [0,1].
lag{1,4}_       INF_ALL of week W-1 / W-4 (0 when the week is absent).
inf_all
lag1_inf_a,     INF_A, INF_B, RSV of week W-1 (0 when absent).
lag1_inf_b,
lag1_rsv
mean8_/max8_    mean and max weekly positivity over weeks W-7..W (measurable
positivity      weeks only); -1.0 when none.
weeks_above_    count of weeks in W-7..W with positivity > 0.10.
threshold_8
missing_weeks_8 count of weeks in W-1..W-7 with no measurable positivity.
sum4_inf_all    INF_ALL summed over W-3..W (absent weeks contribute 0).

Licence: WHO materials are issued under CC BY-NC-SA 3.0 IGO (WHO copyright
policy, recorded in the candidate record); NC/SA terms carry through unchanged
to any release. This is a derived research dataset, never WHO's official
product.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

DEFAULT_SOURCE_URL = "https://xmart-api-public.who.int/FLUMART/VIW_FNT?$format=csv"
NAME = "who-flunet-activity-exceedance"
TARGET = "exceeds"
POSITIVE_LABEL = 1
THRESHOLD = 0.10  # positivity proportion, pinned by the France fixture below
LEAD_WEEKS = 4
PRED_MIN_DENOM = 50   # feature week must be well measured
TGT_MIN_DENOM = 50    # label week must be well measured (the record's floor)
FIXTURE_COUNTRY = "FR"
FIXTURE_SEASON = (date.fromisocalendar(2024, 40, 1), date.fromisocalendar(2025, 15, 1))
FIXTURE_OFFSEASON = (date(2024, 7, 1), date(2024, 8, 31), date(2025, 7, 1), date(2025, 8, 31))
# Pinned at construction, not at discovery: the candidate record proposed ">40% at
# France's 2024-25 peak" as a *candidate* fixture; the measured blended peak
# (ORIGIN_SOURCE streams summed, denominator INF_ALL+INF_NEGATIVE) is 23.8% in
# the week of 2025-01-27, and off-season July-August weeks measure 0.7%. The
# 40% figure belonged to sentinel-only curves of stronger seasons, not to this
# frame. The pinned assertion is therefore: the season peak clears the 10%
# threshold with margin (peak > 0.15, measured 0.238) and off-season weeks stay
# below it (max 0.007 measured) - which is exactly what pins threshold and lead.
FIXTURE_PEAK_MIN = 0.15
FIXTURE_PEAK_MAX = 0.95
FIXTURE_OFFSEASON_MAX = 0.10

# ISO year boundaries for the splits, computed from the calendar so no
# hand-typed date can drift: eval starts at ISO week 2020-W01's Monday
# (2019-12-29), holdout at ISO week 2023-W01's Monday (2023-01-02).
EVAL_START = date.fromisocalendar(2020, 1, 1)
HOLDOUT_START = date.fromisocalendar(2023, 1, 1)

# Source columns summed into the task grain. Every one is documented in the
# publisher's own metadata view (VIW_FLU_METADATA, 53 fields, recorded in the
# candidate record): counts of specimens processed/received, influenza A
# detections by subtype, B detections by lineage, the processed total, the
# negative count, and non-influenza respiratory-virus detections.
COUNT_COLUMNS = [
    "SPEC_PROCESSED_NB", "SPEC_RECEIVED_NB", "AH1N12009", "AH1", "AH3", "AH5",
    "AH7N9", "ANOTSUBTYPED", "INF_A", "BVIC_2DEL", "BVIC_3DEL", "BVIC_NODEL",
    "BVIC_DELUNK", "BYAM", "BNOTDETERMINED", "INF_B", "INF_ALL", "INF_NEGATIVE",
    "ADENO", "BOCA", "HUMAN_CORONA", "METAPNEUMO", "PARAINFLUENZA", "RHINO",
    "RSV",
]
META_COLUMNS = ["WHOREGION", "HEMISPHERE", "ITZ", "COUNTRY_AREA_TERRITORY"]

STRUCTURAL = ["row_id", "week_start", "country_year"]
ID_COLUMNS = ["row_id"]
FEATURES = [
    "iso2", "whoregion", "hemisphere", "itz",
    "iso_year", "iso_week",
    "specimens_w", "inf_a_w", "inf_b_w", "inf_all_w", "inf_negative_w",
    "denom_w", "positivity_w",
    "ah1_w", "ah3_w", "ah1n12009_w", "bvic_w", "byam_w",
    "adeno_w", "boca_w", "human_corona_w", "metapneumo_w", "parainfluenza_w",
    "rhino_w", "rsv_w",
    "lag1_positivity", "lag2_positivity", "lag3_positivity", "lag4_positivity",
    "lag1_inf_all", "lag4_inf_all", "lag1_inf_a", "lag1_inf_b", "lag1_rsv",
    "mean8_positivity", "max8_positivity", "weeks_above_threshold_8",
    "missing_weeks_8", "sum4_inf_all",
]
CARRY_COLUMNS = ["week_start", "country_year"]
HIGH_CARDINALITY = ["week_start", "country_year", "iso2"]
LABEL_SOURCE_COLUMNS = ["INF_ALL", "INF_NEGATIVE"]
COLUMNS = [ID_COLUMNS[0]] + FEATURES + CARRY_COLUMNS + [TARGET]

LAYOUT = {"train": "public/train.csv", "eval": "public/eval.csv",
          "holdout": "private/holdout.csv"}

PREDICTION_TIME = ("End of ISO week W (the Sunday that closes it): every feature "
                   "is derived from that country's weekly FluNet laboratory counts "
                   "for weeks <= W; the target is week W+4's row, not yet observed.")
PREDICTION_QUESTION = (
    "For a WHO FluNet reporting country with systematic weekly negative "
    "reporting, will influenza test positivity in ISO week W+4 exceed 10% of "
    "processed specimens, given that country's weekly laboratory series "
    "through ISO week W?")


def log(message: str) -> None:
    print(message, flush=True)


def parse_count(raw: str | None) -> int:
    """FluNet writes missing counts as empty fields; absent is not zero."""
    if raw is None or raw == "":
        return 0
    return int(float(raw))


def fetch(url: str, dest: Path) -> dict:
    """One anonymous GET; the full table is a single request (measured 30.8 MiB)."""
    started = time.time()
    request = urllib.request.Request(url, headers={"User-Agent": "dataset-factory/1.0"})
    with urllib.request.urlopen(request, timeout=300) as response:
        body = response.read()
    dest.write_bytes(body)
    return {"url": url, "bytes": len(body), "seconds": round(time.time() - started, 1),
            "requests": 1, "sha256": hashlib.sha256(body).hexdigest()}


def week_key(row: dict) -> date:
    return date.fromisoformat(row["ISO_WEEKSTARTDATE"])


def load_series(path: Path) -> dict:
    """Country-week panel: ISO2 -> week-start date -> summed stream record."""
    series: dict[str, dict[date, dict]] = defaultdict(lambda: defaultdict(
        lambda: {"counts": defaultdict(int), "meta": {}, "present": False}))
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        total = 0
        for row in reader:
            total += 1
            iso2 = (row.get("ISO2") or "").strip()
            if not iso2:
                continue
            bucket = series[iso2][week_key(row)]
            for column in COUNT_COLUMNS:
                bucket["counts"][column] += parse_count(row.get(column))
            if not bucket["meta"]:
                bucket["meta"] = {column: (row.get(column) or "").strip()
                                  for column in META_COLUMNS}
            bucket["present"] = True
    return {"series": dict(series), "source_rows": total}


def denom(record: dict) -> int:
    counts = record["counts"]
    return counts["INF_ALL"] + counts["INF_NEGATIVE"]


def rate_of(record: dict | None):
    """Positivity of one summed country-week; None when no specimens were processed."""
    if record is None or not record["present"]:
        return None
    total = denom(record)
    if total <= 0:
        return None
    return record["counts"]["INF_ALL"] / total


def build_country_years(series: dict[str, dict[date, dict]]) -> dict:
    """Systematic-negative-reporting verdict per (ISO2, ISO year of the week).

    A country-year is systematic iff it has >= 4 specimen-bearing weeks and at
    least half of them report INF_NEGATIVE >= 1. This is the rule that removes
    the pre-2015 trap: years where negatives were simply never recorded fail it.
    """
    spec_weeks: dict[tuple, int] = defaultdict(int)
    neg_weeks: dict[tuple, int] = defaultdict(int)
    for iso2, weeks in series.items():
        for start, record in weeks.items():
            if not record["present"] or denom(record) <= 0:
                continue
            key = (iso2, start.isocalendar()[0])
            spec_weeks[key] += 1
            if record["counts"]["INF_NEGATIVE"] >= 1:
                neg_weeks[key] += 1
    verdicts = {}
    for key, weeks in spec_weeks.items():
        verdicts[key] = weeks >= 4 and neg_weeks[key] / weeks >= 0.5
    return {"verdicts": verdicts, "spec_weeks": dict(spec_weeks),
            "neg_weeks": dict(neg_weeks)}


def features_for(series: dict[str, dict[date, dict]], iso2: str, start: date) -> dict:
    """Features for the row keyed by prediction week W (week starting `start`).

    Reads weeks <= W only. A missing lag week yields count features of 0 and
    rate features of -1.0 (a sentinel outside [0,1]), counted by missing_weeks_8;
    nothing about weeks after W is touched.
    """
    weeks = series[iso2]
    current = weeks.get(start)
    if current is None or not current["present"]:
        raise KeyError(f"prediction week {iso2} {start} missing")
    counts = current["counts"]
    total = denom(current)
    out = {
        "iso2": iso2,
        "whoregion": current["meta"].get("WHOREGION", ""),
        "hemisphere": current["meta"].get("HEMISPHERE", ""),
        "itz": current["meta"].get("ITZ", ""),
        "iso_year": start.isocalendar()[0],
        "iso_week": start.isocalendar()[1],
        "specimens_w": counts["SPEC_PROCESSED_NB"],
        "inf_a_w": counts["INF_A"],
        "inf_b_w": counts["INF_B"],
        "inf_all_w": counts["INF_ALL"],
        "inf_negative_w": counts["INF_NEGATIVE"],
        "denom_w": total,
        "positivity_w": counts["INF_ALL"] / total if total > 0 else -1.0,
        "ah1_w": counts["AH1"],
        "ah3_w": counts["AH3"],
        "ah1n12009_w": counts["AH1N12009"],
        "bvic_w": counts["BVIC_2DEL"] + counts["BVIC_3DEL"] + counts["BVIC_NODEL"]
                  + counts["BVIC_DELUNK"],
        "byam_w": counts["BYAM"],
        "adeno_w": counts["ADENO"],
        "boca_w": counts["BOCA"],
        "human_corona_w": counts["HUMAN_CORONA"],
        "metapneumo_w": counts["METAPNEUMO"],
        "parainfluenza_w": counts["PARAINFLUENZA"],
        "rhino_w": counts["RHINO"],
        "rsv_w": counts["RSV"],
    }
    for lag in (1, 2, 3, 4):
        record = weeks.get(start.fromordinal(start.toordinal() - 7 * lag))
        out[f"lag{lag}_positivity"] = value_or_sentinel(rate_of(record))
    lag_counts = (("lag1_inf_all", 1, "INF_ALL"), ("lag4_inf_all", 4, "INF_ALL"),
                 ("lag1_inf_a", 1, "INF_A"), ("lag1_inf_b", 1, "INF_B"),
                 ("lag1_rsv", 1, "RSV"))
    for name, lag, column in lag_counts:
        record = weeks.get(start.fromordinal(start.toordinal() - 7 * lag))
        out[name] = record["counts"][column] if record is not None else 0
    rates, missing = [], 0
    inf_all_sum4 = 0
    above = 0
    for back in range(0, 8):
        record = weeks.get(start.fromordinal(start.toordinal() - 7 * back))
        rate = rate_of(record)
        if rate is None:
            missing += 1 if back > 0 else 0
            continue
        rates.append(rate)
        if rate > THRESHOLD:
            above += 1
        if back < 4 and record is not None:
            inf_all_sum4 += record["counts"]["INF_ALL"]
    out["mean8_positivity"] = sum(rates) / len(rates) if rates else -1.0
    out["max8_positivity"] = max(rates) if rates else -1.0
    out["weeks_above_threshold_8"] = above
    out["missing_weeks_8"] = missing
    out["sum4_inf_all"] = inf_all_sum4
    return out


def value_or_sentinel(rate):
    return rate if rate is not None else -1.0


def make_row(series: dict, years: dict, iso2: str, start: date) -> dict | None:
    """One candidate row, or None with a reason recorded by the caller."""
    current = series[iso2].get(start)
    if current is None or not current["present"]:
        return None
    if denom(current) < PRED_MIN_DENOM:
        return None
    target_start = start.fromordinal(start.toordinal() + 7 * LEAD_WEEKS)
    target = series[iso2].get(target_start)
    if target is None or not target["present"]:
        return None
    total = denom(target)
    if total < TGT_MIN_DENOM:
        return None
    target_year = target_start.isocalendar()[0]
    if not years["verdicts"].get((iso2, target_year)):
        return None
    rate = target["counts"]["INF_ALL"] / total
    features = features_for(series, iso2, start)
    row = {
        "row_id": f"{iso2}-{start.isocalendar()[0]}W{start.isocalendar()[1]:02d}",
        "week_start": start.isoformat(),
        "country_year": f"{iso2}-{target_year}",
        TARGET: 1 if rate > THRESHOLD else 0,
        **features,
    }
    return row


def split_of(start: date) -> str:
    if start < EVAL_START:
        return "train"
    if start < HOLDOUT_START:
        return "eval"
    return "holdout"


def write_splits(out: Path, rows_by_split: dict) -> dict:
    stats = {}
    for split, rel in LAYOUT.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = rows_by_split.get(split, [])
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="raise")
            writer.writeheader()
            writer.writerows(rows)
        positives = sum(row[TARGET] for row in rows)
        events = len({row["country_year"] for row in rows if row[TARGET] == POSITIVE_LABEL})
        stats[split] = {"rows": len(rows), "positives": positives,
                        "positive_rate": round(positives / len(rows), 6) if rows else None,
                        "distinct_events": events}
    return stats


def auc(labels: list[int], scores: list[float]) -> float | None:
    """Rank-based AUC (Mann-Whitney), stdlib only - the austin build's method."""
    pairs = sorted(zip(scores, labels), key=lambda pair: pair[0])
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        return None
    # average ranks for ties
    ranks = [0.0] * len(pairs)
    index = 0
    while index < len(pairs):
        stop = index
        while stop < len(pairs) and pairs[stop][0] == pairs[index][0]:
            stop += 1
        average = (index + stop + 1) / 2  # 1-based mean rank of the tied block
        for position in range(index, stop):
            ranks[position] = average
        index = stop
    positive_rank_sum = sum(rank for rank, (_, label) in zip(ranks, pairs) if label == 1)
    return (positive_rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def france_fixture(series: dict) -> dict:
    """Pin threshold and lead against France's 2024-25 season, from the source."""
    weeks = series.get(FIXTURE_COUNTRY, {})
    season = [(start, rate) for start, record in sorted(weeks.items())
              if FIXTURE_SEASON[0] <= start <= FIXTURE_SEASON[1]
              and (rate := rate_of(record)) is not None]
    offseason = [(start, rate) for start, record in sorted(weeks.items())
                 if any(lo <= start <= hi for lo, hi in
                       ((FIXTURE_OFFSEASON[0], FIXTURE_OFFSEASON[1]),
                        (FIXTURE_OFFSEASON[2], FIXTURE_OFFSEASON[3])))
                 and (rate := rate_of(record)) is not None]
    peak = max((rate for _, rate in season), default=None)
    peak_week = next((start.isoformat() for start, rate in season if rate == peak), None)
    off_max = max((rate for _, rate in offseason), default=None)
    return {"country": FIXTURE_COUNTRY, "season_weeks": len(season),
            "peak_positivity": peak, "peak_week": peak_week,
            "offseason_weeks": len(offseason), "offseason_max_positivity": off_max,
            "assertions": {
                "peak_exceeds_0.15": peak is not None and FIXTURE_PEAK_MIN < peak <= FIXTURE_PEAK_MAX,
                "offseason_under_0.10": off_max is not None and off_max < FIXTURE_OFFSEASON_MAX,
            }}


def trap_acceptance(series: dict, years: dict) -> dict:
    """Pre-rule vs post-rule positivity in 1995-2004, the measured trap window."""
    pre_rows = pre_rate = 0
    for iso2, weeks in series.items():
        for start, record in weeks.items():
            if not 1995 <= start.isocalendar()[0] <= 2004:
                continue
            if not record["present"] or denom(record) < TGT_MIN_DENOM:
                continue
            pre_rows += 1
            pre_rate += 1 if record["counts"]["INF_ALL"] / denom(record) > THRESHOLD else 0
    post_rows = post_rate = 0
    for iso2, weeks in series.items():
        for start, record in weeks.items():
            if not 1995 <= start.isocalendar()[0] <= 2004:
                continue
            if not record["present"] or denom(record) < TGT_MIN_DENOM:
                continue
            if not years["verdicts"].get((iso2, start.isocalendar()[0])):
                continue
            post_rows += 1
            post_rate += 1 if record["counts"]["INF_ALL"] / denom(record) > THRESHOLD else 0
    return {"window": "1995-2004",
            "pre_rule_rows": pre_rows,
            "pre_rule_positive_rate": round(pre_rate / pre_rows, 4) if pre_rows else None,
            "post_rule_rows": post_rows,
            "post_rule_positive_rate": round(post_rate / post_rows, 4) if post_rows else None,
            "note": "the discovery session measured 931/931 positive here; the "
                    "pre-rule rate reproduces that uniform result, and the rule is "
                    "judged by how few of those rows survive it"}


def timing_selfcheck(rows: list[dict], series: dict, sample: int) -> dict:
    """Recompute a sample of rows against a physically truncated series.

    If any feature path touches a week after W, the truncated copy raises
    KeyError here instead of shipping a post-hoc feature.
    """
    if not rows:
        return {"checked": 0}
    step = max(1, len(rows) // sample)
    checked = mismatches = 0
    for row in rows[::step]:
        start = date.fromisoformat(row["week_start"])
        iso2 = row["iso2"]
        truncated = {iso2: {w: r for w, r in series[iso2].items() if w <= start}}
        rebuilt = features_for(truncated, iso2, start)
        checked += 1
        for column in FEATURES:
            if rebuilt[column] != row[column]:
                mismatches += 1
                log(f"TIMING CHECK MISMATCH {row['row_id']} column {column}: "
                    f"shipped {row[column]!r} rebuilt {rebuilt[column]!r}")
                break
    return {"checked": checked, "mismatches": mismatches}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the who-flunet-activity-exceedance extract")
    parser.add_argument("--out", default="/output", help="extract root (runner layout written inside)")
    parser.add_argument("--work-dir", default="/tmp/flunet", help="scratch for the source download")
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL,
                        help="override for bounded smoke exercises")
    parser.add_argument("--smoke", action="store_true",
                        help="bounded exercise: skip split-capacity and fixture-coverage assertions")
    parser.add_argument("--built-at", default=None, help="pin the build timestamp (UTC)")
    parser.add_argument("--timing-check-sample", type=int, default=200)
    parser.add_argument("--max-rows", type=int, default=None,
                        help="cap eligible rows (bounded exercise only)")
    args = parser.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    built_at = args.built_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    log("== download ==")
    source = fetch(args.source_url, work / "flunet.csv")
    log(f"downloaded {source['bytes']} bytes in {source['seconds']}s "
        f"sha256={source['sha256'][:16]}...")

    log("== aggregate ==")
    panel = load_series(work / "flunet.csv")
    series = panel["series"]
    log(f"{panel['source_rows']} source rows, {len(series)} countries, "
        f"{sum(len(w) for w in series.values())} country-weeks")

    years = build_country_years(series)
    systematic = sum(1 for verdict in years["verdicts"].values() if verdict)
    log(f"systematic country-years: {systematic}/{len(years['verdicts'])}")

    fixture = france_fixture(series)
    log(f"france fixture: peak {fixture['peak_positivity']} at {fixture['peak_week']}, "
        f"off-season max {fixture['offseason_max_positivity']}")

    log("== rows ==")
    rows = []
    skipped = {"no_target": 0, "thin_pred": 0, "thin_target": 0, "not_systematic": 0}
    for iso2, weeks in series.items():
        for start in sorted(weeks):
            current = weeks[start]
            if not current["present"]:
                continue
            if denom(current) < PRED_MIN_DENOM:
                skipped["thin_pred"] += 1
                continue
            target_start = start.fromordinal(start.toordinal() + 7 * LEAD_WEEKS)
            target = weeks.get(target_start)
            if target is None or not target["present"]:
                skipped["no_target"] += 1
                continue
            if denom(target) < TGT_MIN_DENOM:
                skipped["thin_target"] += 1
                continue
            target_year = target_start.isocalendar()[0]
            if not years["verdicts"].get((iso2, target_year)):
                skipped["not_systematic"] += 1
                continue
            row = make_row(series, years, iso2, start)
            if row is not None:
                rows.append(row)
    if args.max_rows:
        rows = rows[:args.max_rows]
    rows.sort(key=lambda row: (row["iso2"], row["week_start"]))
    log(f"eligible rows: {len(rows)} (skipped: {skipped})")

    duplicates = len(rows) - len({row["row_id"] for row in rows})
    if duplicates:
        log(f"FAIL: {duplicates} duplicate row_ids")
        return 2

    rows_by_split = {"train": [], "eval": [], "holdout": []}
    for row in rows:
        rows_by_split[split_of(date.fromisoformat(row["week_start"]))].append(row)

    timing = timing_selfcheck(rows, series, args.timing_check_sample)
    log(f"timing self-check: {timing}")
    if timing["mismatches"]:
        log("FAIL: features are not reproducible from weeks <= W alone")
        return 2

    stats = write_splits(out, rows_by_split)
    for split, entry in stats.items():
        log(f"{split}: {entry['rows']} rows, {entry['positives']} positives, "
            f"rate {entry['positive_rate']}, {entry['distinct_events']} clustered events")

    # label-source columns must be absent from the shipped files
    with (out / LAYOUT["train"]).open(newline="") as handle:
        header = handle.readline()
    for column in LABEL_SOURCE_COLUMNS + ["target_positivity", "inf_all_target",
                                          "inf_negative_target", "denom_target"]:
        if column in header:
            log(f"FAIL: label source column {column} shipped in the CSV header")
            return 2

    baselines = {}
    for split, rel in LAYOUT.items():
        split_rows = rows_by_split[split]
        labels = [row[TARGET] for row in split_rows]
        baselines[split] = {
            "persistence_auc": auc(labels, [row["positivity_w"] for row in split_rows]),
            "rolling8_mean_auc": auc(labels, [row["mean8_positivity"] for row in split_rows]),
        }

    trap = trap_acceptance(series, years)

    summary = {
        "name": NAME,
        "built_at_utc": built_at,
        "source": source,
        "grain": "country x ISO week (ORIGIN_SOURCE streams summed)",
        "threshold": {"positivity_proportion": THRESHOLD, "comparison": "strictly greater than",
                      "lead_weeks": LEAD_WEEKS,
                      "min_denominator": {"prediction_week": PRED_MIN_DENOM,
                                          "target_week": TGT_MIN_DENOM}},
        "systematic_rule": ("target country-year has >= 4 specimen-bearing weeks and >= 50% "
                            "of them report INF_NEGATIVE >= 1; country-years judged "
                            "systematic: " + str(systematic) + "/" + str(len(years["verdicts"]))),
        "skipped_candidate_rows": skipped,
        "splits": stats,
        "clustered_events_note": ("distinct_events counts country-years of the target week "
                                  "carrying at least one positive - positives arrive in "
                                  "seasonal clusters, so this is the effective sample size "
                                  "figure, per the candidate record"),
        "france_fixture": fixture,
        "trap_acceptance": trap,
        "timing_selfcheck": timing,
        "duplicate_row_ids": duplicates,
        "reference_baselines": {"note": "stdlib rank AUC measured at construction on the written "
                                        "rows; scores are prediction-time-safe single features",
                                "per_split": baselines},
        "crosscheck_hint": ("the built France 2024-25 positivity curve (summary.france_fixture) "
                            "is the same series the publisher's FluNet chart app draws "
                            "(worldhealthorg.shinyapps.io/flunetchart); the fixture asserts "
                            "its peak and off-season levels from the source"),
    }

    if not args.smoke:
        # The France fixture pins the threshold and the frame; it must pass on the full window.
        if not all(fixture["assertions"].values()):
            log(f"FAIL: France fixture did not pass: {fixture['assertions']}")
            return 2
        # Split capacity: both classes present in every split, with clustered positives
        # above the qualification gate's minimums (30 positives / 20 events).
        for split in ("eval", "holdout"):
            entry = stats[split]
            if entry["rows"] == 0 or entry["positives"] == 0 or \
                    entry["positives"] == entry["rows"]:
                log(f"FAIL: {split} cannot carry a score: {entry}")
                return 2
            if entry["positives"] < 30 or entry["distinct_events"] < 20:
                log(f"FAIL: {split} too thin: {entry}")
                return 2
        if stats["train"]["rows"] == 0:
            log("FAIL: no training rows")
            return 2
        # Trap acceptance: the pre-rule rate must reproduce the discovery session's
        # uniform result (~931/931), proving this pipeline sees the same frame.
        if trap["pre_rule_rows"] < 500 or (trap["pre_rule_positive_rate"] or 0) < 0.95:
            log(f"FAIL: trap cross-check drifted from the recorded measurement: {trap}")
            return 2
    else:
        log("SMOKE MODE: split-capacity, fixture-coverage and trap assertions skipped")

    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")

    meta = {
        "name": NAME,
        "description": PREDICTION_QUESTION,
        "source": args.source_url,
        "license": "WHO CC BY-NC-SA 3.0 IGO (WHO copyright policy; NC/SA carry through). "
                   "Derived research dataset - not a WHO official product.",
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": ID_COLUMNS,
        "columns": COLUMNS,
        "rows": {split: stats[split]["rows"] for split in LAYOUT},
        "positive_rate": {split: stats[split]["positive_rate"] for split in LAYOUT},
        "split": {"strategy": "temporal by the prediction week's ISO year",
                  "boundaries": {"train": "ISO year <= 2019", "eval": "2020-2022",
                                 "holdout": "2023 onward"}},
        "threshold": {"positivity_proportion": THRESHOLD, "lead_weeks": LEAD_WEEKS},
        "label_rule": "target week (W+4) positivity INF_ALL/(INF_ALL+INF_NEGATIVE) > 0.10, "
                      "denominator >= 50 and systematic negative reporting in the target "
                      "country-year",
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "prediction_time": PREDICTION_TIME,
        "features": FEATURES,
        "built_at_utc": built_at,
        "source_sha256": source["sha256"],
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    quality = {
        "name": NAME,
        "task": {"question": PREDICTION_QUESTION, "prediction_time": PREDICTION_TIME},
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "threshold_positivity_proportion": THRESHOLD,
        "lead_weeks": LEAD_WEEKS,
        "time_column": "week_start",
        "event_key_column": "country_year",
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "feature_documentation": (
            "every source field is documented in the publisher's VIW_FLU_METADATA view "
            "(53 fields, fetched 2026-10-20, recorded in the candidate record); the "
            "derived-column dictionary lives in build.py's module docstring and ships in "
            "the release DATA_DICTIONARY"
        ),
        "carry_columns": CARRY_COLUMNS,
        "id_columns": ID_COLUMNS,
        "high_cardinality_columns": HIGH_CARDINALITY,
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "post_hoc_columns": [],
        "measurements": [
            {"column": "positivity_w",
             "unit": "proportion INF_ALL/(INF_ALL+INF_NEGATIVE), streams summed",
             "frame": "week W, the week whose Sunday is the prediction instant"},
            {"column": "country_year",
             "unit": "ISO2 '-' ISO year of the target week",
             "frame": "clustered-event key: positives of one country-season arrive "
                      "together, so scores are quoted against distinct_events"},
        ],
        "external_threshold": {
            "value": THRESHOLD,
            "unit": "proportion of processed specimens positive for influenza",
            "source": "activity threshold proposed in the candidate record and pinned at "
                      "construction by the France 2024-25 known-event fixture: the measured "
                      "blended peak is 23.8% (week of 2025-01-27) and July-August off-season "
                      "weeks measure 0.7%, so 10% separates season from off-season with "
                      "margin; asserted in summary.json",
        },
        "known_event": {
            "name": "France 2024-25 influenza season (peak week of 2025-01-27, measured "
                    "blended positivity 23.8%)",
            "expected_verdict": "exceeds",
            "source": "WHO FluNet VIW_FNT, asserted at build against the measured series "
                      "(summary.france_fixture): the season peak clears the 10% threshold "
                      "(pinned floor 0.15) and July-August 2024/2025 weeks stay under it; the "
                      "discovery session's cross-check of aggregate positivity against the "
                      "publisher's FluNet chart app is recorded in the candidate record "
                      "(2026-10-20). The record's proposed '>40% at peak' was a candidate "
                      "figure for a sentinel-only curve of a stronger season; the pinned "
                      "fixture uses the measured blended frame",
        },
        "split_windows": {
            "train": {"start": None, "end": EVAL_START.isoformat()},
            "eval": {"start": EVAL_START.isoformat(), "end": HOLDOUT_START.isoformat()},
            "holdout": {"start": HOLDOUT_START.isoformat(), "end": None},
        },
        "split_boundaries": {"train": "prediction week ISO year <= 2019",
                             "eval": "2020-2022", "holdout": "2023 onward"},
        "expected_duplicate_ids": 0,
        "id_columns_are_entity_keys": False,
        "id_columns_note": "row_id names one country-prediction-week; country_year names the "
                           "clustered event (country-season), not a one-label entity, so no "
                           "entity-key claim is made",
        "positive_events": {split: {"positives": stats[split]["positives"],
                                    "distinct_events": stats[split]["distinct_events"]}
                            for split in ("eval", "holdout")},
        "positive_events_note": "distinct_events are country-years of the target week with at "
                                "least one positive - the clustered effective sample size",
        "splits": LAYOUT,
        "built_at_utc": built_at,
        "shipped_columns": COLUMNS,
        "trap_acceptance": trap,
        "timing_selfcheck": timing,
    }
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")

    log("== done ==")
    log(json.dumps({"splits": stats, "fixture": fixture["assertions"],
                    "trap": trap, "baselines": baselines}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
