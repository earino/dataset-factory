#!/usr/bin/env python3
"""Construction script for the `unhcr-refugee-data-finder` candidate.

Task: the UNHCR asylum-applications distribution on HDX has just been refreshed
to carry complete data for year D (the prediction instant - an annual
publication-lag nowcast, the accepted abs-visitor-arrivals-direction pattern).
For an established asylum corridor (country of origin O, country of asylum H)
whose government-procedure applications in year D are at least 500 and whose
year-D-1 value is already published, will the corridor's year-D+1 total reach
at least twice the year-D total?

Where this runs
---------------

On a temporary worker: one anonymous GET of the HDX applications CSV
(8,669,567 bytes, sha256 d5808616c3d10d33925d4df5a3182a2028dd574d111e843cc207455ba45fe950
measured 2026-10-23; `--csv` accepts a local copy for a full dry run on the
coordinator-class machine - a dry run never substitutes for the worker's gate).

Frame rules (each measured at discovery and re-asserted here)
------------------------------------------------------------
* Stream: Procedure Type G (government procedure) and Application Data Type P
  (persons) only; the corridor-year total is the SUM of all application-type
  rows (N/V/A/R/... - applications are additive across types; the BAMF
  cross-check in the candidate record validates the sum rule). U/J procedure
  rows and C (case-level) rows are counted in the provenance mix and never
  used. 105,862 G rows / 13,955 U / 780 J measured; 113,635 P / 6,962 C.
* Grain: one row per (origin, asylum, label year T = D+1). Eligibility reads
  only published years <= D: corridor year-D total >= 500 AND a published
  year-D-1 corridor value (the momentum feature family needs it; corridors
  without one - 386 rows, 5.0% - are counted per split with reason, never
  silently dropped). Label-observability censoring, counted per split and
  never a value-conditioned decision: the host files no G/P report at all in
  D+1 (33 rows on the pinned snapshot; the label is undefined, not zero), and
  label-year-2026 rows (D=2025, live edge) whose outcome year is not yet in
  the fetched vintage.
* Label: doubled = 1 iff year-D+1 corridor total >= 2 x year-D total; a
  missing corridor row with the host still reporting counts as 0
  applications. The year-D+1 value (the label operand) never ships; the
  year-D value does - it is published at the instant and is the doubling
  baseline.
* Prediction instant: the HDX resource refresh carrying complete year-D data.
  Observed refreshes: 2025-11-05, 2026-02-25, 2026-06-11, 2026-06-19,
  2026-06-22, 2026-08-20; the 2026-08-20 refresh carries complete data
  through 2025 (max Year = 2025 measured on the fetched bytes), 232 days
  after the 2025 period end. UNHCR's Global Trends cycle lands mid-D+1.
  This is a NOWCAST: the instant lies INSIDE target year D+1, whose value is
  unpublished on this channel until ~mid D+2; no part of "the target window
  follows the instant" is claimed. For most non-EU hosts no public monthly
  corridor data exists at all in the interim.
* Splits (label years): train 2001-2016, eval 2017-2021, holdout
  2022..last year in the vintage (2025 on the pinned snapshot). With the
  year-D-1 requirement, label-year 2001 contributes no rows (the panel
  starts 2000; all 193 eligible corridors lack a published 1999 value) -
  counted, never silently dropped.
* Event key: surge_cluster = origin|label-year. Positives cluster when one
  displacement event hits many corridors in one year (SYR->many hosts 2015),
  so the conservative independent-event count is the distinct (origin,
  label-year) pair among positives, not the row count.
* Known-event fixtures (verified in-panel at discovery, asserted in-build):
  SYR->DEU 2014->2015 41,100 -> 162,510 label TRUE (2015 Syrian surge into
  Germany); AFG->USA 2021->2022 533 -> 25,082 label TRUE (post-Aug-2021
  Taliban takeover); AFG->DEU 2021->2022 37,245 -> 48,602 label FALSE (large
  growth, sub-doubling); UKR->POL 2021->2022 458 -> 1,593 BELOW eligibility
  (Ukrinians in the EU mostly registered temporary protection, not asylum
  applications - the task measures application surges).
* Vintage: HDX distributes one in-place-revised resource; no historical
  vintages are retained, so values are construction-time current-vintage,
  pinned by the fetched snapshot's sha256. The same documented posture as
  abs-visitor-arrivals-direction. No operational point-in-time claim.

NO performance metric of any kind is computed here - no AUC, no baseline, no
rate presented as a finding. Split positive counts and prevalence are gate
diagnostics (the gate recomputes them from the rows); everything else that
looks like evidence waits for the post-acceptance reference stage.

Runner contract: public/train.csv, public/eval.csv, private/holdout.csv,
meta.json, quality.json - the layout `skills/dataset-qualification/` gates.

Licence: CC BY 3.0 IGO (the HDX dataset record, the publisher's own channel
and licence choice; class A recorded in the candidate record). Attribution,
no implied UNHCR endorsement, derived-research labelling and no added
restrictions carry through to any release. Derived research dataset - never
an official UNHCR product.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

NAME = "unhcr-refugee-data-finder"
TARGET = "doubled"
POSITIVE_LABEL = 1

PANEL_URL = ("https://data.humdata.org/dataset/74cdbe77-0a0b-441b-9535-bacc263be2a8/"
             "resource/295cd9e4-8464-43ee-ad17-47196991a1f7/download/"
             "asylum_applications_residing_world.csv")
PINNED_SHA256 = "d5808616c3d10d33925d4df5a3182a2028dd574d111e843cc207455ba45fe950"

MIN_APPS = 500          # eligibility: year-D corridor G/P total
DOUBLING = 2            # label: year-D+1 total >= DOUBLING x year-D total
PANEL_FIRST_YEAR = 2000  # measured panel start on the pinned snapshot

# Label-year windows. The holdout end adapts to the fetched vintage (the last
# year the panel actually carries); on the pinned snapshot that is 2025.
TRAIN_YEARS = (2001, 2016)
EVAL_YEARS = (2017, 2021)
HOLDOUT_START_YEAR = 2022

# Known-event fixtures: (origin, asylum, year D, expected D value, expected
# D+1 value, expected label). Asserted against the fetched panel in-build.
FIXTURES = [
    ("SYR", "DEU", 2014, 41100, 162510, 1, "2015 Syrian surge into Germany"),
    ("AFG", "USA", 2021, 533, 25082, 1, "post-Aug-2021 Taliban takeover"),
    ("AFG", "DEU", 2021, 37245, 48602, 0, "large growth, sub-doubling"),
]
BELOW_ELIGIBILITY_FIXTURE = ("UKR", "POL", 2021, 458, 1593)

# Shipped layout: id, features, carry, target.
ID_COLUMNS = ["row_id"]
FEATURES = ["origin", "asylum", "target_year",
            "apps_d", "apps_d1", "log_growth_d", "surged_recently",
            "host_apps_d", "host_growth_d",
            "origin_apps_d", "origin_growth_d", "corridor_age"]
CARRY_COLUMNS = ["target_date", "surge_cluster"]
HIGH_CARDINALITY = ["row_id", "surge_cluster"]
COLUMNS = ID_COLUMNS + FEATURES + CARRY_COLUMNS + [TARGET]
LAYOUT = {"train": "public/train.csv", "eval": "public/eval.csv",
          "holdout": "private/holdout.csv"}

MIN_SPLIT_POSITIVES = 30   # gate threshold: eval/holdout scorable positives
MIN_SPLIT_EVENTS = 20      # gate threshold: distinct positive surge clusters

PREDICTION_QUESTION = (
    "The UNHCR asylum-applications distribution has just been refreshed to "
    "carry complete data for year D. For an asylum corridor (country of "
    "origin O, country of asylum H) whose government-procedure applications "
    "in year D are at least 500 and whose year-D-1 value is published, will "
    "the corridor's year-D+1 government-procedure application total reach at "
    "least twice the year-D total?")
PREDICTION_TIME = (
    "The publication instant of the UNHCR asylum-applications annual data "
    "for year D on the machine-fetchable HDX channel: an observed refresh "
    "cycle (2025-11-05, 2026-02-25, 2026-06-11, 2026-06-19, 2026-06-22, "
    "2026-08-20) whose 2026-08-20 refresh carries complete data through "
    "year 2025 (max Year = 2025 measured on the fetched bytes), 232 days "
    "after the 2025 period end; UNHCR's Global Trends cycle lands mid-D+1. "
    "At that instant every feature is a corridor-year total for years <= D. "
    "The target year D+1 has partially elapsed at the instant but its value "
    "is entirely unpublished on this channel (first available ~mid D+2), so "
    "this is an annual publication-lag nowcast, not a future-event forecast.")

# Recorded on the pinned 2026-10-23 snapshot WITHOUT the year-D-1 requirement
# (the candidate record's split_strategy); the build re-measures with it and
# records the delta, so the refinement is auditable rather than silent.
RECORDED_WITHOUT_D1 = {
    "train": {"rows": 3677, "positives": 302},
    "eval": {"rows": 1918, "positives": 166},
    "holdout": {"rows": 1994, "positives": 234},
}


def log(message: str) -> None:
    print(message, flush=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url: str, dest: Path) -> dict:
    started = time.time()
    request = urllib.request.Request(
        url, headers={"User-Agent": "dataset-factory/unhcr-build"})
    with urllib.request.urlopen(request, timeout=300) as response:
        last_modified = response.headers.get("Last-Modified")
        with dest.open("wb") as handle:
            size = 0
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                handle.write(chunk)
                size += len(chunk)
    return {"url": url, "bytes": size, "last_modified": last_modified,
            "seconds": round(time.time() - started, 1),
            "sha256": sha256_file(dest)}


def fmt_num(value) -> str:
    """Strings pass through; integral floats print without a tail; else 6 decimals."""
    if isinstance(value, str):
        return value
    if value == int(value):
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def load_panel(path: Path) -> tuple[dict, dict, dict, dict, dict, dict]:
    """Read the HDX CSV into the G/P corridor-year panel plus context tables.

    Returns (panel, host_years, host_totals, origin_totals, first_observed,
    diagnostics). panel[(year, origin, asylum)] = summed persons count over
    all application-type rows; host/origin totals are all-origin/all-host sums
    of the same stream (published context, never label operands).
    """
    panel: dict[tuple, int] = defaultdict(int)
    host_years: dict[str, set] = defaultdict(set)
    host_totals: dict[tuple, int] = defaultdict(int)
    origin_totals: dict[tuple, int] = defaultdict(int)
    first_observed: dict[tuple, int] = {}
    mixes = {"Procedure Type": Counter(), "Application Data Type": Counter(),
             "Application Type Code": Counter()}
    rows = gp_rows = zero_persons = bad_numeric = 0
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise SystemExit(f"panel CSV has no header: {path}")
        for row in reader:
            rows += 1
            for key in mixes:
                mixes[key][(row.get(key) or "").strip()] += 1
            if row["Procedure Type"] != "G" or row["Application Data Type"] != "P":
                continue
            gp_rows += 1
            raw = (row.get("Number of Applications") or "").strip()
            try:
                value = float(raw)
            except ValueError:
                bad_numeric += 1
                continue
            if value != int(value):
                bad_numeric += 1
                continue
            if value == 0:
                zero_persons += 1
                continue
            year = int(row["Year"])
            origin = (row["Country of Origin Code"] or "").strip()
            asylum = (row["Country of Asylum Code"] or "").strip()
            key = (year, origin, asylum)
            panel[key] += int(value)
            host_years[asylum].add(year)
            host_totals[(year, asylum)] += int(value)
            origin_totals[(year, origin)] += int(value)
            corridor = (origin, asylum)
            if corridor not in first_observed or year < first_observed[corridor]:
                first_observed[corridor] = year
    if bad_numeric:
        raise SystemExit(f"{bad_numeric} non-integer application counts - "
                         "the sum rule requires integer persons counts")
    diagnostics = {
        "data_rows": rows,
        "gp_persons_rows": gp_rows,
        "zero_persons_rows_skipped": zero_persons,
        "mixes": {key: dict(counts) for key, counts in mixes.items()},
    }
    return dict(panel), dict(host_years), dict(host_totals), dict(origin_totals), \
        first_observed, diagnostics


def split_of_label_year(label_year: int) -> str | None:
    if TRAIN_YEARS[0] <= label_year <= TRAIN_YEARS[1]:
        return "train"
    if EVAL_YEARS[0] <= label_year <= EVAL_YEARS[1]:
        return "eval"
    if label_year >= HOLDOUT_START_YEAR:
        return "holdout"
    return None


def build_rows(panel: dict, host_years: dict, host_totals: dict,
               origin_totals: dict, first_observed: dict) -> tuple[dict, dict]:
    """Emit one row per eligible corridor-year; count every exclusion."""
    years = sorted({key[0] for key in panel})
    max_year = years[-1]
    rows_by_split: dict[str, list[dict]] = {"train": [], "eval": [], "holdout": []}
    excluded = Counter()                 # bucket -> count
    excluded_detail = Counter()          # (bucket, reason, split) -> count
    eligible_by_year: dict[int, int] = Counter()

    for (year_d, origin, asylum), value in sorted(panel.items()):
        if value < MIN_APPS:
            continue
        eligible_by_year[year_d] += 1
        label_year = year_d + 1
        split = split_of_label_year(label_year)

        # --- censoring: label observability, never a value-conditioned rule
        if label_year > max_year:
            excluded["unobserved_target"] += 1
            excluded_detail[("unobserved_target", "target_year_beyond_vintage",
                             "live_edge")] += 1
            continue
        if label_year not in host_years.get(asylum, set()):
            excluded["unobserved_target"] += 1
            excluded_detail[("unobserved_target", "host_files_no_gp_report",
                             split or "outside")] += 1
            continue
        # --- eligibility: published years <= D only
        prior = panel.get((year_d - 1, origin, asylum))
        if prior is None:
            reason = ("panel_starts_2000_no_prior_year" if year_d == years[0]
                      else "no_published_prior_year_cell")
            excluded["missing_history"] += 1
            excluded_detail[("missing_history", reason, split or "outside")] += 1
            continue
        if split is None:
            excluded["outside_split_windows"] += 1
            continue

        # --- context totals are implied present by the corridor's own rows
        host_d = host_totals.get((year_d, asylum))
        host_d1 = host_totals.get((year_d - 1, asylum))
        origin_d = origin_totals.get((year_d, origin))
        origin_d1 = origin_totals.get((year_d - 1, origin))
        if (host_d is None or host_d1 is None or origin_d is None
                or origin_d1 is None or host_d <= 0 or host_d1 <= 0
                or origin_d <= 0 or origin_d1 <= 0):
            raise SystemExit(f"construction defect: missing context totals for "
                             f"{origin}->{asylum} year {year_d}")

        next_value = panel.get((label_year, origin, asylum), 0)
        row = {
            "row_id": f"{origin}-{asylum}-{label_year}",
            "origin": origin,
            "asylum": asylum,
            "target_year": label_year,
            "apps_d": value,
            "apps_d1": prior,
            "log_growth_d": round(math.log(value + 1) - math.log(prior + 1), 6),
            "surged_recently": int(value >= DOUBLING * prior),
            "host_apps_d": host_d,
            "host_growth_d": round(math.log(host_d + 1) - math.log(host_d1 + 1), 6),
            "origin_apps_d": origin_d,
            "origin_growth_d": round(math.log(origin_d + 1) - math.log(origin_d1 + 1), 6),
            "corridor_age": year_d - first_observed[(origin, asylum)],
            "target_date": f"{label_year}-12-31",
            "surge_cluster": f"{origin}|{label_year}",
            TARGET: int(next_value >= DOUBLING * value),
        }
        rows_by_split[split].append(row)

    for split in rows_by_split:
        rows_by_split[split].sort(key=lambda r: (r["target_year"], r["origin"], r["asylum"]))

    diagnostics = {
        "panel_year_range": [years[0], max_year],
        "eligible_by_year": dict(sorted(eligible_by_year.items())),
        "excluded": dict(sorted(excluded.items())),
        "excluded_detail": {"|".join(key): count
                            for key, count in sorted(excluded_detail.items())},
    }
    return rows_by_split, diagnostics


def check_fixtures(panel: dict) -> list[dict]:
    """Assert the known-event fixtures against the fetched panel (hard fail)."""
    results = []
    for origin, asylum, year_d, want_d, want_d1, want_label, name in FIXTURES:
        got_d = panel.get((year_d, origin, asylum), 0)
        got_d1 = panel.get((year_d + 1, origin, asylum), 0)
        got_label = int(got_d1 >= DOUBLING * got_d) if got_d >= MIN_APPS else None
        ok = (got_d == want_d and got_d1 == want_d1 and got_label == want_label)
        results.append({"event": name, "corridor": f"{origin}->{asylum}",
                        "years": f"{year_d}->{year_d + 1}", "apps_d": got_d,
                        "apps_d1": got_d1, "expected_label": want_label,
                        "measured_label": got_label, "ok": bool(ok)})
        if not ok:
            log(f"FIXTURE MISMATCH {origin}->{asylum} {year_d}: "
                f"{got_d} -> {got_d1} (expected {want_d} -> {want_d1}, "
                f"label {got_label} vs {want_label})")
    origin, asylum, year_d, want_d, want_d1 = BELOW_ELIGIBILITY_FIXTURE
    got_d = panel.get((year_d, origin, asylum), 0)
    got_d1 = panel.get((year_d + 1, origin, asylum), 0)
    below = got_d < MIN_APPS
    ok = (got_d == want_d and got_d1 == want_d1 and below)
    results.append({"event": "Ukraine temporary-protection exclusion",
                    "corridor": f"{origin}->{asylum}",
                    "years": f"{year_d}->{year_d + 1}", "apps_d": got_d,
                    "apps_d1": got_d1, "expected_label": "below-eligibility",
                    "measured_label": "below-eligibility" if below else "eligible",
                    "ok": bool(ok)})
    if not ok:
        log(f"BELOW-ELIGIBILITY FIXTURE MISMATCH {origin}->{asylum} "
            f"{year_d}: {got_d} -> {got_d1}")
    if not all(entry["ok"] for entry in results):
        raise SystemExit("known-event fixtures failed against the fetched panel - "
                          "the vintage contradicts the recorded evidence; do not ship")
    return results


def write_splits(out: Path, rows_by_split: dict) -> dict:
    stats = {}
    for split, rel in LAYOUT.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = rows_by_split[split]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(COLUMNS)
            for row in rows:
                writer.writerow([fmt_num(row[column]) for column in COLUMNS])
        positives = sum(row[TARGET] for row in rows)
        stats[split] = {
            "rows": len(rows),
            "positives": positives,
            "negative": len(rows) - positives,
            "positive_rate": round(positives / len(rows), 6) if rows else None,
            "distinct_positive_clusters": len({row["surge_cluster"]
                                                for row in rows if row[TARGET]}),
            "min_year": min((row["target_year"] for row in rows), default=None),
            "max_year": max((row["target_year"] for row in rows), default=None),
        }
        log(f"{split}: {stats[split]['rows']} rows, "
            f"{stats[split]['positives']} positives "
            f"({stats[split]['distinct_positive_clusters']} clusters)")
    return stats


def quality_document(out: Path, stats: dict, fetch_info: dict, panel_diag: dict,
                     fixtures: list, built_at: str, holdout_end_year: int) -> None:
    """quality.json: every declaration the gate recomputes from the rows."""
    positive_events = {split: {"positives": stats[split]["positives"],
                               "distinct_events": stats[split]["distinct_positive_clusters"]}
                       for split in LAYOUT}
    quality = {
        "name": NAME,
        "task": {"question": PREDICTION_QUESTION,
                 "prediction_time": PREDICTION_TIME},
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "time_column": "target_date",
        "event_key_column": "surge_cluster",
        "event_key_note": (
            "surge_cluster = origin|label-year: one displacement event hits "
            "many corridors in one year (SYR->many hosts 2015), so the "
            "conservative independent-event count is the distinct "
            "(origin, label-year) pair among positives"),
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "feature_documentation": (
            "every shipped feature is a corridor-year or context total for "
            "published years <= D, or a corridor/calendar identity: origin and "
            "asylum are the publisher's ISO-3-style codes; target_year is the "
            "label year's calendar identity; apps_d/apps_d1 are the corridor's "
            "government-procedure persons totals for years D and D-1 (the "
            "year-D value is the doubling baseline, published at the instant); "
            "log_growth_d is ln(apps_d+1)-ln(apps_d1+1); surged_recently flags "
            "apps_d >= 2*apps_d1 (the corridor already doubled into D); "
            "host_apps_d/host_growth_d and origin_apps_d/origin_growth_d are "
            "the same-year host-country and origin-country all-corridor totals "
            "and their log growth (reception-capacity and displacement-pressure "
            "context); corridor_age is years since the corridor first appears "
            "in the fetched panel. The year-D+1 value (the label operand) and "
            "every year > D value are excluded from the shipped columns."),
        "carry_columns": CARRY_COLUMNS,
        "id_columns": ID_COLUMNS,
        "high_cardinality_columns": HIGH_CARDINALITY,
        "high_cardinality_note": (
            "row_id is unique per row and surge_cluster (origin|label-year) "
            "carries more levels than rows/5 in the narrower splits; both are "
            "declared rather than scored, and their information is fully "
            "recoverable from origin, asylum and target_year"),
        "label_source_columns": [
            "year-D+1 corridor G/P total (source column 'Number of "
            "Applications' at Year=D+1, all application types summed)"],
        "post_hoc_columns": [],
        "measurements": [
            {"column": "apps_d", "unit": "persons (integer applications)",
             "frame": "corridor government-procedure persons applications in "
                      "year D, summed over all application types, current-vintage"},
            {"column": "apps_d1", "unit": "persons (integer applications)",
             "frame": "the same corridor total for year D-1"},
            {"column": "log_growth_d", "unit": "log (natural) point difference",
             "frame": "ln(apps_d+1) - ln(apps_d1+1), the observed momentum at D"},
            {"column": "surged_recently", "unit": "binary flag 0/1",
             "frame": "apps_d >= 2 x apps_d1, the corridor's own last-step "
                      "doubling observed at D"},
            {"column": "host_apps_d", "unit": "persons (integer applications)",
             "frame": "all-corridor government-procedure total received by the "
                      "host country in year D"},
            {"column": "host_growth_d", "unit": "log (natural) point difference",
             "frame": "ln(host total D + 1) - ln(host total D-1 + 1)"},
            {"column": "origin_apps_d", "unit": "persons (integer applications)",
             "frame": "all-host government-procedure total from the origin "
                      "country in year D"},
            {"column": "origin_growth_d", "unit": "log (natural) point difference",
             "frame": "ln(origin total D + 1) - ln(origin total D-1 + 1)"},
            {"column": "corridor_age", "unit": "years (integer)",
             "frame": "D minus the corridor's first year in the fetched panel "
                      "(>= 1 by the eligibility rule)"},
            {"column": "target_year", "unit": "calendar year (integer)",
             "frame": "the label year D+1"},
            {"column": "target_date", "unit": "ISO date (year-end of the label year)",
             "frame": "calendar identity of the outcome window; used as the "
                      "split time column"},
            {"column": "surge_cluster", "unit": "origin|label-year string",
             "frame": "event key for clustered positive counting"},
            {"column": "origin", "unit": "publisher ISO-3-style code",
             "frame": "country of origin identity"},
            {"column": "asylum", "unit": "publisher ISO-3-style code",
             "frame": "country of asylum identity"},
            {"column": "row_id", "unit": "origin-asylum-labelyear string",
             "frame": "row identifier; unique per row"},
            {"column": TARGET, "unit": "binary 0/1",
             "frame": "1 iff year-D+1 corridor total >= 2 x year-D total; a "
                      "missing corridor row with the host still reporting "
                      "counts as 0 applications"},
        ],
        "external_threshold": False,
        "known_event": {
            "name": "2015 Syrian surge into Germany (SYR->DEU 2014->2015)",
            "expected_verdict": "exceeds",
            "detail": "41,100 -> 162,510, x2 label TRUE - asserted in-build "
                      "with the AFG->USA 2021->2022 TRUE and AFG->DEU "
                      "2021->2022 FALSE fixtures and the UKR->POL "
                      "below-eligibility case",
            "source": "UNHCR asylum statistics via HDX (the fetched panel "
                      "itself; values verified at discovery against the "
                      "publisher's own interactive Data Finder)",
        },
        "timing": {
            "prediction_instant": {
                "kind": "publication",
                "period": "Y",
                "days_after_period_end": 232,
                "citation": (
                    "HDX resource update history observed 2026-10-23: "
                    "refreshes 2025-11-05, 2026-02-25, 2026-06-11, 2026-06-19, "
                    "2026-06-22 and 2026-08-20; the 2026-08-20 refresh carries "
                    "complete data through year 2025 (max Year = 2025 measured "
                    "on the fetched bytes, 232 days after the 2025 period "
                    "end); UNHCR's Global Trends cycle lands mid-D+1"),
            },
            "features": {
                "period": "Y",
                "published_days_after_period_end": 232,
                "source_kind": "statistical_release",
            },
            "row_selection": {
                "latest_period_used": "Y (year D, the last fully published year)",
                "fields": ["apps_d (year-D corridor total >= 500)",
                           "apps_d1 (published year-D-1 corridor value)"],
                "basis": (
                    "eligibility reads only published years <= D: the corridor's "
                    "year-D government-procedure total >= 500 and a published "
                    "year-D-1 corridor value. Label-observability censoring "
                    "excludes corridors whose host files no G/P report at all "
                    "in D+1 (label undefined, never counted as zero) and "
                    "live-edge label years beyond the fetched vintage; both are "
                    "counted per split in summary.json and never condition on "
                    "the label value. The target year D+1 never enters "
                    "eligibility."),
            },
            "observations": [
                {"period": "2025", "period_end": "2025-12-31",
                 "published": "2026-08-20"},
            ],
        },
        "split_windows": {
            "train": {"start": f"{TRAIN_YEARS[0]}-01-01",
                      "end": f"{EVAL_YEARS[0]}-01-01"},
            "eval": {"start": f"{EVAL_YEARS[0]}-01-01",
                     "end": f"{HOLDOUT_START_YEAR}-01-01"},
            "holdout": {"start": f"{HOLDOUT_START_YEAR}-01-01",
                        "end": f"{holdout_end_year + 1}-01-01"},
        },
        "split_boundaries": {
            "train": "label years 2001-2016 (window end exclusive; label-year "
                     "2001 contributes no rows: the panel starts 2000 so no "
                     "corridor has a published 1999 value - counted in "
                     "summary.json)",
            "eval": "label years 2017-2021 (window end exclusive)",
            "holdout": f"label years {HOLDOUT_START_YEAR}-{holdout_end_year} "
                       "(window end exclusive; through the last year the "
                       "fetched vintage carries; 2025 on the pinned snapshot)",
        },
        "positive_events": positive_events,
        "positive_events_note": (
            "positives and distinct (origin, label-year) surge clusters per "
            "split, recomputed from the written rows; the gate re-verifies"),
        "expected_duplicate_ids": 0,
        "id_columns_are_entity_keys": True,
        "id_columns_note": (
            "row_id = origin-asylum-labelyear names one corridor-year with "
            "one label; the corridor itself recurs across label years by "
            "design (a panel task), which is why the corridor pair ships as "
            "features and only row_id is the identifier"),
        "splits": LAYOUT,
        "evaluation_contract": {
            "use": "retrospective_research",
            "access": "isolated_rows",
            "training_label_timing": "unverified",
            "scope_note": (
                "each row is a corridor-year whose features read published "
                "years <= D only; the runner predicts row-wise from the "
                "shipped columns. Labeled eval is development/validation; "
                "the holdout is the final test and stays outside evaluated "
                "agents' workspaces. Training-label timing is UNVERIFIED: HDX "
                "distributes one in-place-revised resource with no "
                "historical vintages, so no full-row availability ledger can "
                "be constructed and the artifact is retrospective research "
                "only, never a certified historical forecasting setup."),
            "feature_evidence": {
                "row_id": {
                    "source": "row key origin-asylum-labelyear",
                    "availability": "identity of the row; corridor and label "
                                    "year are both known at the instant",
                    "status": "verified"},
                "origin": {
                    "source": "source column 'Country of Origin Code'",
                    "availability": "publisher-assigned corridor identity, "
                                    "constant across the panel",
                    "status": "verified"},
                "asylum": {
                    "source": "source column 'Country of Asylum Code'",
                    "availability": "publisher-assigned corridor identity, "
                                    "constant across the panel",
                    "status": "verified"},
                "target_year": {
                    "source": "row key (year D + 1)",
                    "availability": "calendar arithmetic on the instant's "
                                    "last published year",
                    "status": "verified"},
                "apps_d": {
                    "source": "sum of 'Number of Applications' over G/P "
                              "application-type rows at Year D",
                    "availability": "the year-D refresh is the instant "
                                    "itself (observed 2026-08-20 carrying "
                                    "complete data through 2025)",
                    "status": "assumed",
                    "assumption": "current-vintage value; the value "
                                  "published at past instants is "
                                  "unverifiable (no historical vintages)"},
                "apps_d1": {
                    "source": "the same summed panel at Year D-1",
                    "availability": "published one refresh before the "
                                    "instant, so available at it",
                    "status": "assumed",
                    "assumption": "current-vintage value (see apps_d)"},
                "log_growth_d": {
                    "source": "deterministic function of apps_d and apps_d1",
                    "availability": "derivable at the instant from published "
                                    "years <= D",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "surged_recently": {
                    "source": "deterministic flag on apps_d >= 2 x apps_d1",
                    "availability": "derivable at the instant",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "host_apps_d": {
                    "source": "all-corridor sum of the same G/P stream at "
                              "(Year D, asylum)",
                    "availability": "published at the instant (same refresh "
                                    "as apps_d)",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "host_growth_d": {
                    "source": "deterministic function of host totals at D "
                              "and D-1",
                    "availability": "derivable at the instant",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "origin_apps_d": {
                    "source": "all-host sum of the same G/P stream at "
                              "(Year D, origin)",
                    "availability": "published at the instant",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "origin_growth_d": {
                    "source": "deterministic function of origin totals at D "
                              "and D-1",
                    "availability": "derivable at the instant",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "corridor_age": {
                    "source": "D minus the corridor's first year in the "
                              "fetched panel",
                    "availability": "derivable at the instant from published "
                                    "years <= D",
                    "status": "assumed",
                    "assumption": "panel start 2000 truncates true corridor "
                                  "age for pre-2000 corridors; age is "
                                  "'years since first observed in the "
                                  "fetched panel'"},
                "target_date": {
                    "source": "calendar year-end of the label year",
                    "availability": "calendar arithmetic; the carry column "
                                    "is the split time column, not an "
                                    "observation",
                    "status": "verified"},
                "surge_cluster": {
                    "source": "origin + label year (event key)",
                    "availability": "identity of the row's cluster; both "
                                    "parts known at the instant",
                    "status": "verified"},
            },
            "vintage": {
                "kind": "current_snapshot",
                "evidence": (
                    "HDX distributes one in-place-revised resource: the "
                    "record observed refreshes 2025-11-05, 2026-02-25, "
                    "2026-06-11, 2026-06-19, 2026-06-22, 2026-08-20 and no "
                    "archived vintages are retained, so a reverse-history "
                    "probe is not performable on this channel. The fetched "
                    "snapshot is pinned by sha256 and the build asserts the "
                    "recorded known-event fixtures against it; values are "
                    "construction-time current-vintage and no historical "
                    "point-in-time availability is claimed. Same documented "
                    "posture as abs-visitor-arrivals-direction."),
            },
            "selection": {
                "kind": "prediction_time",
                "evidence": (
                    "eligibility reads only published years <= D (year-D "
                    "corridor total >= 500 and a published year-D-1 value). "
                    "Label-observability censoring - host files no G/P "
                    "report at all in D+1, or the label year lies beyond the "
                    "fetched vintage - excludes rows whose label is "
                    "undefined and counts them per split in summary.json; "
                    "it never conditions on the label value and never "
                    "decides another row's membership (the same "
                    "pending-censored pattern the accepted "
                    "ec-merger-phase2-opening artifact uses)"),
            },
            "limitations": [
                "Annual grain only on the machine-fetchable channel; a "
                "monthly variant would need the WAF-gated UNHCR Data Finder "
                "app or an operator decision on browser-captured exports.",
                "Current-vintage panel with no historical vintages: this is "
                "retrospective research, not certified historical "
                "forecasting; intra-basis revision size is unmeasurable "
                "without archived vintages.",
                "The prediction instant lies inside the target year "
                "(publication-lag nowcast): the target year has partially "
                "elapsed at the instant; what is claimed is "
                "value-unavailability on this channel, not that the window "
                "follows the instant.",
                "Temporary-protection registrations (Ukrainians in the EU "
                "from 2022) are not asylum applications and do not enter "
                "the stream - the 2022 Ukraine displacement is largely "
                "absent from this task by construction (UKR->POL fixture).",
                "Prevalence drifts across splits (more surges in later "
                "years; recorded 8.2% train / 8.7% eval / 11.7% holdout "
                "before the year-D-1 refinement) - a property of the period, "
                "reported beside every score.",
                "Positives cluster by (origin, label-year) surge events "
                "beyond the row count; clustered counts are reported beside "
                "every score.",
                "386 rows (5.0% of eligible corridor-years on the pinned "
                "snapshot) lack a published year-D-1 value and are excluded "
                "with per-split counts (mostly label-year 2001, where the "
                "panel start makes every prior year unpublished).",
                "Unsplit-V application-type rows live mostly in the "
                "training era (1,238 of 3,677 recorded train rows); the "
                "sum-across-types rule is what the BAMF cross-check "
                "validates.",
                "Corridor age is measured from the fetched panel's 2000 "
                "start, truncating true age for older corridors.",
            ],
            "cross_row_audit": {
                "probes": [
                    {"name": "next_label_year_exposes_outcome",
                     "entity_columns": ["origin", "asylum"],
                     "time_column": "target_date",
                     "operation": "copy",
                     "left": "surged_recently",
                     "offset_months": 12,
                     "expectation": (
                         "the donor row (same corridor, label year T+1) "
                         "carries surged_recently = (year-T total >= 2 x "
                         "year-T-1 total), which is exactly the earlier "
                         "row's label: a panel is self-answering across rows "
                         "one year apart. Coverage therefore measures the "
                         "cross-row outcome exposure inherent to the task; "
                         "it requires the restricted prediction protocol and "
                         "is why access is isolated_rows with this audit "
                         "recorded - not a construction defect")},
                ],
                "rationale": (
                    "rows are corridor-years on a self-answering panel: a "
                    "row with label year T+1 ships the year-T corridor total "
                    "as apps_d, which is the label operand of the row with "
                    "label year T. The probe measures that exposure from "
                    "the artifact itself on every full configuration "
                    "(train, eval, holdout); covered rows make this "
                    "restricted retrospective research under an enforced "
                    "protocol, and no historical forecasting claim is "
                    "made."),
                "auxiliary_files_review": (
                    "the extract ships exactly the runner layout - "
                    "public/train.csv, public/eval.csv, "
                    "private/holdout.csv, meta.json, quality.json; the "
                    "fetched source CSV, the panel and all diagnostics stay "
                    "outside the artifact; no joint label matrices or other "
                    "solver-visible files exist in the dataset directory"),
                "reverse_history": (
                    "not performable: HDX retains no archived vintages of "
                    "this resource (observed in-place revision 2025-11-05 "
                    "through 2026-08-20), so no as-of reconstruction can be "
                    "probed; the current-vintage posture above is the "
                    "recorded consequence"),
            },
        },
        "source_snapshot": fetch_info,
        "built_at_utc": built_at,
        "shipped_columns": COLUMNS,
    }
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--work-dir", default="/tmp/unhcr")
    parser.add_argument("--csv", default=None,
                        help="local panel copy for a dry run (worker fetches)")
    parser.add_argument("--built-at", default=None,
                        help="pin the build timestamp for byte-identical rebuilds")
    args = parser.parse_args(argv)

    built_at = args.built_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)

    if args.csv:
        csv_path = Path(args.csv)
        fetch_info = {"url": PANEL_URL, "bytes": csv_path.stat().st_size,
                      "last_modified": None, "seconds": None,
                      "sha256": sha256_file(csv_path),
                      "mode": "local dry run from --csv (not a worker fetch)"}
    else:
        csv_path = work / "asylum_applications_residing_world.csv"
        log(f"== fetch {PANEL_URL}")
        fetch_info = fetch(PANEL_URL, csv_path)
        fetch_info["mode"] = "worker fetch"
    log(f"panel sha256 {fetch_info['sha256']} ({fetch_info['bytes']} bytes)")
    if fetch_info["sha256"] != PINNED_SHA256:
        log("WARNING: fetched sha256 differs from the recorded discovery pin "
            f"{PINNED_SHA256}; proceeding with the vintage recorded here and "
            "asserting the known-event fixtures against it")

    panel, host_years, host_totals, origin_totals, first_observed, panel_diag = \
        load_panel(csv_path)
    years = sorted({key[0] for key in panel})
    log(f"panel: {len(panel)} corridor-year cells, years {years[0]}..{years[-1]}, "
        f"{len(first_observed)} corridors")
    if years[0] > PANEL_FIRST_YEAR or years[-1] < 2025:
        raise SystemExit(f"unexpected panel year range {years[0]}..{years[-1]}")

    fixtures = check_fixtures(panel)

    rows_by_split, build_diag = build_rows(
        panel, host_years, host_totals, origin_totals, first_observed)

    total_rows = sum(len(rows) for rows in rows_by_split.values())
    if total_rows == 0:
        raise SystemExit("no rows built - the eligibility filter matched nothing")
    for split in ("eval", "holdout"):
        stats_pos = sum(row[TARGET] for row in rows_by_split[split])
        if stats_pos < MIN_SPLIT_POSITIVES:
            raise SystemExit(f"{split} has {stats_pos} positives - below the "
                             f"{MIN_SPLIT_POSITIVES} gate threshold")
        clusters = len({row["surge_cluster"] for row in rows_by_split[split]
                        if row[TARGET]})
        if clusters < MIN_SPLIT_EVENTS:
            raise SystemExit(f"{split} has {clusters} distinct positive "
                             f"clusters - below the {MIN_SPLIT_EVENTS} gate "
                             "threshold")

    log("== write splits")
    stats = write_splits(out, rows_by_split)

    holdout_end_year = stats["holdout"]["max_year"]

    # meta.json: the facts the runner reads, computed from the written rows.
    meta = {
        "name": NAME,
        "description": PREDICTION_QUESTION,
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": ID_COLUMNS,
        "columns": COLUMNS,
        "rows": {split: stats[split]["rows"] for split in LAYOUT},
        "positive_rate": {split: stats[split]["positive_rate"] for split in LAYOUT},
        "split": (f"temporal on the label year: train {TRAIN_YEARS[0]}-"
                  f"{TRAIN_YEARS[1]}, eval {EVAL_YEARS[0]}-{EVAL_YEARS[1]}, "
                  f"holdout {HOLDOUT_START_YEAR}-{holdout_end_year}"),
        "split_description": (
            f"temporal on the label year (D+1): train {TRAIN_YEARS[0]}-"
            f"{TRAIN_YEARS[1]}, eval {EVAL_YEARS[0]}-{EVAL_YEARS[1]}, "
            f"holdout {HOLDOUT_START_YEAR}-{holdout_end_year}; eligibility "
            f"requires a published year-D corridor total >= {MIN_APPS} "
            "persons and a published year-D-1 value"),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    quality_document(out, stats, fetch_info, panel_diag, fixtures, built_at,
                     holdout_end_year)

    # ---- summary.json: construction diagnostics; NO performance numbers ----
    per_label_year = {}
    for split, rows in rows_by_split.items():
        by_year = defaultdict(lambda: [0, 0])
        for row in rows:
            entry = by_year[row["target_year"]]
            entry[0] += 1
            entry[1] += row[TARGET]
        per_label_year[split] = {year: {"rows": entry[0], "positives": entry[1]}
                                 for year, entry in sorted(by_year.items())}
    cross_check = {
        "recorded_on": "pinned 2026-10-23 snapshot, WITHOUT the year-D-1 "
                       "eligibility refinement (candidate record split_strategy)",
        "recorded": RECORDED_WITHOUT_D1,
        "measured_with_d1_required": {split: {"rows": stats[split]["rows"],
                                              "positives": stats[split]["positives"]}
                                      for split in LAYOUT},
        "delta_note": (
            "the build adds the published-year-D-1 requirement (the momentum "
            "feature family needs it); the difference per split is the "
            "missing_history bucket in exclusions, dominated by label-year "
            "2001 where the panel start leaves no corridor with a "
            "published 1999 value"),
    }
    summary = {
        "name": NAME,
        "stage": "construction (no performance metric computed anywhere here)",
        "fetch": fetch_info,
        "fetch_matches_discovery_pin": fetch_info["sha256"] == PINNED_SHA256,
        "panel": panel_diag,
        "panel_year_range": build_diag["panel_year_range"],
        "eligible_by_year": build_diag["eligible_by_year"],
        "exclusions": build_diag["excluded"],
        "exclusion_detail": build_diag["excluded_detail"],
        "split_stats": stats,
        "per_label_year": per_label_year,
        "fixtures": fixtures,
        "cross_check": cross_check,
        "built_at_utc": built_at,
        "shipped_rows": total_rows,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    log(f"== done: {total_rows} rows written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
