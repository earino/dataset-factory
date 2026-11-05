#!/usr/bin/env python3
"""Construction script for the `unhcr-corridor-entry-surge` candidate.

Task: an asylum corridor (country of origin O, country of asylum H) has just
FIRST reached at least 500 government-procedure applications in year T0 (its
entry year - the annual publication-lag nowcast instant is the first HDX
refresh carrying year-T0 data). Predict whether the corridor's total
applications over the TWO following years (T0+1 and T0+2) reach at least twice
the T0 total (label `cum2_2x`). ONE ROW PER CORRIDOR, taken once at first
crossing - the one-shot redesign of the dropped panel task
(unhcr-refugee-data-finder, operator decision 2026-11-02): no corridor
contributes two rows, so no row can ship another row's label operand at
corridor grain. The operator's recorded reopen condition is formulated and
measured in the candidate record (opened READY 2026-11-04).

Population rule (all measured at discovery on the pinned source and
re-asserted here as hard anchors - see ANCHORS_* below):

* Stream: Procedure Type G (government procedure) and Application Data Type P
  (persons) only; the corridor-year total is the SUM over all
  application-type rows (the sum rule the parent record validated against
  BAMF). Exactly the two probe scripts' loader
  (probe_hdx_oneshot*.py): int-parsed counts, zero-value cells kept as
  published cells, host_years = every year with any G/P row for the host.
* Entry year T0 = the FIRST year with corridor total >= 500 (eligibility 500,
  the recorded threshold; never re-tuned after scores).
* Momentum eligibility (the parent task's own rule, capacity measured for
  exactly this variant in the record): the corridor has a PUBLISHED,
  strictly positive year-(T0-1) value. Left-censored T0=2000 entrants (no
  1999 data) and corridors with no positive prior cell are excluded and
  counted per split - never silently dropped. Chosen BEFORE any score; the
  full-population variant is measured in-build as a cross-check only.
* Label cum2_2x = 1 iff total(T0+1) + total(T0+2) >= 2 x total(T0). A missing
  corridor row while the host still reports that year is an observed 0; a
  year in which the host files no G/P report at all leaves the outcome
  UNOBSERVED (row excluded, counted per split - never a value-conditioned
  decision). Entries whose outcome window extends beyond the fetched vintage
  (T0 >= 2024 on the 2000-2025 snapshot) are the live edge: excluded,
  counted, never shipped as scored rows.
* Splits (entry years, fixed): train 2000-2014, eval 2015-2020, holdout
  2021-2023. Windows are entry-year windows; the outcome window extends two
  years past T0 and NEVER enters split assignment (membership is decided
  before the outcome is looked up).
* Event key: surge_cluster = origin|entry-year (positives cluster when one
  displacement event hits many corridors in one year).
* Prediction instant: the first refresh of the HDX global package that
  carries year-T0 data (observed refreshes 2025-11-05, 2026-02-25,
  2026-06-11, 2026-06-19, 2026-06-22, 2026-08-20; the 2026-08-20 file
  carries 2000-2025, 232 days after the 2025 period end). A NOWCAST for
  historical rows: the outcome window has partially elapsed at the instant
  but both outcome years are unpublished on this channel; corridors entering
  2025 are live strict forecasts. No "window follows the instant" claim.
* Vintage: HDX distributes one in-place-revised resource, no historical
  vintages - values are construction-time current-vintage, sha256-pinned;
  the same documented posture as the parent record. No operational
  point-in-time availability is claimed anywhere.

Cross-row exposure (recorded limitation the record requires the gate to
measure): rows share ORIGINS and HOSTS across windows, so a later entrant's
origin-level (or host-level) aggregate feature can contain an earlier
entrant's outcome-year value as a component - and when the earlier corridor
is the only flow from that origin (or into that host) in that year, the
aggregate EQUALS the earlier row's label operand exactly. That is partial
information, not the parent's corridor-grain exact-copy exposure (which is
structurally gone: one row per corridor). The build MEASURES the exact
recovery count (cross_row_label_operand_recovery in summary.json) and the
gate runs four declared probes on the built artifact (quality.json
evaluation_contract.cross_row_audit): the corridor-grain probe must read
coverage 0; the origin/host aggregate probes measure the joinable exposure,
which is why evaluation access is isolated_rows.

NO performance metric of any kind is computed here - no AUC, no accuracy, no
rate presented as a finding. Split positive counts, prevalence and clustered
event counts are gate diagnostics the gate recomputes from the rows;
everything else that looks like evidence waits for the post-acceptance
reference stage (score.py, after the gate passes and --accept re-verifies
the exact bytes).

Runner contract: public/train.csv, public/eval.csv, private/holdout.csv,
meta.json, quality.json - the layout skills/dataset-qualification gates.

Licence: CC BY 3.0 IGO (the HDX package record, the publisher's own licence
choice; class A recorded in the candidate record, re-verified 2026-11-04).
Attribution, no implied UNHCR endorsement, derived-research labelling and no
added restrictions carry through to any release. Derived research dataset -
never an official UNHCR product.
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

NAME = "unhcr-corridor-entry-surge"
TARGET = "cum2_2x"
POSITIVE_LABEL = 1

PANEL_URL = ("https://data.humdata.org/dataset/74cdbe77-0a0b-441b-9535-bacc263be2a8/"
             "resource/295cd9e4-8464-43ee-ad17-47196991a1f7/download/"
             "asylum_applications_residing_world.csv")
PINNED_SHA256 = "d5808616c3d10d33925d4df5a3182a2028dd574d111e843cc207455ba45fe950"

MIN_APPS = 500          # eligibility: entry-year corridor G/P total (recorded)
DOUBLING = 2            # label: (T0+1 + T0+2) >= DOUBLING x T0
PANEL_FIRST_YEAR = 2000  # measured panel start on the pinned snapshot
PANEL_LAST_YEAR = 2025  # measured last year the pinned snapshot carries

# Entry-year windows (the candidate record's primary design, measured on the
# pinned source 2026-11-04; fixed - never re-drawn after scores).
TRAIN_ENTRIES = (2000, 2014)
EVAL_ENTRIES = (2015, 2020)
HOLDOUT_ENTRIES = (2021, 2023)

# Hard anchors measured by probe_hdx_oneshot_designs.py on the pinned source
# (sha256 d5808616..., designs.json capacity_with_published_t0m1.cum2_2x for
# the momentum-eligible build population, elig500_cum2_2x.splits for the
# full-population cross-check). A vintage drift or logic defect that moves
# ANY of these fails the build loudly.
ANCHORS = {
    "train": {"rows": 363, "positives": 127, "events": 106},
    "eval": {"rows": 202, "positives": 98, "events": 80},
    "holdout": {"rows": 159, "positives": 72, "events": 64},
}
ANCHORS_FULL_POP = {
    "train": {"rows": 653, "positives": 214, "events": 153},
    "eval": {"rows": 230, "positives": 103, "events": 83},
    "holdout": {"rows": 170, "positives": 73, "events": 64},
}

# Known-event fixtures: (origin, asylum, T0, apps_t0, apps_t0m1,
#                        apps_t0p1, apps_t0p2, expected label)
# Values verified in the pinned bytes at discovery (notes.md); asserted here
# against the fetched panel, together with the entry-year and prior checks.
FIXTURES = [
    ("AFG", "USA", 2021, 533, 44, 25082, 19320, 1,
     "post-Aug-2021 Taliban takeover (AFG->USA)"),
    ("VEN", "COL", 2017, 582, 316, 2592, 10479, 1,
     "Venezuelan displacement (VEN->COL)"),
    ("UKR", "POL", 2014, 2511, 41, 2295, 1194, 0,
     "sub-doubling corridor (UKR->POL; 2022 temporary protection absent)"),
]
# Corridors whose first crossing is the panel's first year: no published
# prior exists, so momentum eligibility must EXCLUDE them (left censoring
# exercised on real bytes, not as a shipped row).
LEFT_CENSORED_FIXTURE = ("SYR", "DEU", 2000, 3069)
# Live-edge fixture: entry 2025, outcome window 2026-2027 beyond the fetched
# vintage - excluded and counted, the strict-forecast case.
LIVE_EDGE_FIXTURE = ("SSD", "ETH", 2025, 50148)
# Below-threshold no-re-entry: UKR->POL's 2021 value is 458 (< 500) and the
# corridor must NOT re-enter - its one row stays at the 2014 first crossing.
NO_REENTRY_FIXTURE = ("UKR", "POL", 2021, 458, 2014)

# Shipped layout: id, features, carry, target.
ID_COLUMNS = ["row_id"]
FEATURES = ["origin", "asylum", "entry_year",
            "apps_t0", "apps_t0m1", "log_growth_into_entry", "surged_into_entry",
            "years_since_first_seen", "prior_history_len", "prior_max",
            "host_apps_t0", "host_apps_t0m1", "host_growth",
            "origin_apps_t0", "origin_apps_t0m1", "origin_growth",
            "share_of_host_t0", "share_of_origin_t0"]
CARRY_COLUMNS = ["entry_date", "surge_cluster"]
HIGH_CARDINALITY = ["row_id", "surge_cluster", "origin", "asylum"]
COLUMNS = ID_COLUMNS + FEATURES + CARRY_COLUMNS + [TARGET]
LAYOUT = {"train": "public/train.csv", "eval": "public/eval.csv",
          "holdout": "private/holdout.csv"}

MIN_SPLIT_POSITIVES = 30   # gate threshold: eval/holdout scorable positives
MIN_SPLIT_EVENTS = 20      # gate threshold: distinct positive surge clusters

PREDICTION_QUESTION = (
    "An asylum corridor (country of origin O, country of asylum H) has just "
    "first reached at least 500 government-procedure asylum applications in "
    "year T0 (its entry year), in the UNHCR HDX annual data. Will the "
    "corridor's total applications over the two following years (T0+1 and "
    "T0+2) reach at least twice the T0 total? One row per corridor, taken "
    "once at first crossing.")
PREDICTION_TIME = (
    "Publication-lag nowcast at the annual instant: the first refresh of the "
    "UNHCR HDX global package (data.humdata.org, dataset "
    "unhcr-population-data-for-world) that carries the entry year T0's data "
    "(observed refreshes 2025-11-05, 2026-02-25, 2026-06-11, 2026-06-19, "
    "2026-06-22 and 2026-08-20T15:33:49Z; the 2026-08-20 file carries years "
    "2000-2025, 232 days after the 2025 period end). Features are the "
    "corridor's and its origin/host countries' published yearly totals for "
    "years <= T0 only. The outcome years T0+1/T0+2 are unpublished on this "
    "channel at the instant (first published ~mid T0+2/T0+3); for historical "
    "rows the outcome window has partially elapsed at the instant - no "
    "'window follows the instant' claim is made. Corridors entering 2025 are "
    "live strict forecasts: their whole outcome window 2026-2027 follows the "
    "2026-08-20 instant.")


def log(message: str) -> None:
    print(message, flush=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url: str, dest: Path, attempts: int = 3, backoff_seconds: float = 5.0) -> dict:
    """Download a source file, refusing WAF challenges and empty bodies.

    data.humdata.org fronts its downloads with AWS WAF (awselb). A
    User-Agent it does not recognise is answered with HTTP 202,
    `x-amzn-waf-action: challenge` and a zero-length body; urllib treats
    202 as success, so the first worker run wrote an empty file and only
    failed far downstream ("panel CSV has no header"). Measured
    2026-11-05 from the coordinator: this build's former custom UA and a
    browser UA are challenged, while urllib's own default UA
    (Python-urllib/3.x) and the curl/wget/requests strings are served the
    file - so no UA override is sent: the default both passes the WAF and
    truthfully names this client. A challenge header, a non-200 status or
    a zero-length body fails the attempt with the observed evidence;
    bounded retries cover transient failures, then the fetch gives up
    loudly rather than leaving a plausible empty file.
    """
    started = time.time()
    failure = "not attempted"
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(url)
        partial = dest.with_name(dest.name + ".part")
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                status = response.status
                waf_action = response.headers.get("X-Amzn-Waf-Action")
                last_modified = response.headers.get("Last-Modified")
                if waf_action is not None or status != 200:
                    failure = (f"attempt {attempt}: HTTP {status} "
                               f"x-amzn-waf-action={waf_action!r}")
                else:
                    with partial.open("wb") as handle:
                        size = 0
                        while True:
                            chunk = response.read(1 << 20)
                            if not chunk:
                                break
                            handle.write(chunk)
                            size += len(chunk)
                    if size:
                        # Only a complete, non-empty body ever lands at dest.
                        partial.replace(dest)
                        return {"url": url, "bytes": size,
                                "last_modified": last_modified,
                                "seconds": round(time.time() - started, 1),
                                "sha256": sha256_file(dest)}
                    failure = f"attempt {attempt}: HTTP 200 with a zero-length body"
        except OSError as exc:
            # URLError (connection refused/timeout/DNS) is an OSError subclass.
            failure = f"attempt {attempt}: {type(exc).__name__}: {exc}"
        if partial.exists():
            partial.unlink()
        if attempt < attempts:
            time.sleep(backoff_seconds)
    raise SystemExit(f"source fetch failed after {attempts} attempts: "
                     f"{url} ({failure})")


def fmt_num(value) -> str:
    """Strings pass through; integral floats print without a tail; else 6 decimals."""
    if isinstance(value, str):
        return value
    if value == int(value):
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def load_panel(path: Path):
    """Read the HDX CSV into the G/P corridor-year panel plus context tables.

    Exactly the two probe scripts' loader (the recorded anchors were
    measured with these rules): int-parsed application counts (unparseable
    rows skipped and counted), zero-value cells KEPT as published cells,
    host_years = every year with any G/P row for the host.

    Returns (cells, host_years, host_totals, origin_totals, first_seen,
    diagnostics). cells[(year, origin, asylum)] = summed persons count;
    host/origin totals are all-corridor sums of the same stream.
    """
    cells: dict[tuple, int] = defaultdict(int)
    host_years: dict[str, set] = defaultdict(set)
    host_totals: dict[tuple, int] = defaultdict(int)
    origin_totals: dict[tuple, int] = defaultdict(int)
    first_seen: dict[tuple, int] = {}
    mixes = {"Procedure Type": Counter(), "Application Data Type": Counter(),
             "Application Type Code": Counter()}
    rows = gp_rows = skipped_numeric = 0
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
                value = int(raw)
            except (TypeError, ValueError):
                skipped_numeric += 1
                continue
            year = int(row["Year"])
            origin = (row["Country of Origin Code"] or "").strip()
            asylum = (row["Country of Asylum Code"] or "").strip()
            cells[(year, origin, asylum)] += value          # zero cells kept
            host_years[asylum].add(year)
            host_totals[(year, asylum)] += value
            origin_totals[(year, origin)] += value
            corridor = (origin, asylum)
            if corridor not in first_seen or year < first_seen[corridor]:
                first_seen[corridor] = year
    diagnostics = {
        "data_rows": rows,
        "gp_rows": gp_rows,
        "unparseable_skipped": skipped_numeric,
        "distinct_corridor_year_cells": len(cells),
        "mixes": {key: dict(counts) for key, counts in mixes.items()},
    }
    return dict(cells), dict(host_years), dict(host_totals), dict(origin_totals), \
        first_seen, diagnostics


def entry_years(cells: dict) -> dict:
    """First year >= MIN_APPS per corridor (knowable at the instant: reads
    only the corridor's own published yearly values <= that year)."""
    entries: dict[tuple, int] = {}
    series: dict[tuple, dict] = defaultdict(dict)
    for (year, origin, asylum), value in cells.items():
        if value >= MIN_APPS:
            series[(origin, asylum)][year] = value
    for corridor, years in series.items():
        entries[corridor] = min(years)
    return entries


def split_of_entry_year(entry_year: int) -> str | None:
    if TRAIN_ENTRIES[0] <= entry_year <= TRAIN_ENTRIES[1]:
        return "train"
    if EVAL_ENTRIES[0] <= entry_year <= EVAL_ENTRIES[1]:
        return "eval"
    if HOLDOUT_ENTRIES[0] <= entry_year <= HOLDOUT_ENTRIES[1]:
        return "holdout"
    return None


def build_rows(cells: dict, host_years: dict, host_totals: dict,
               origin_totals: dict, first_seen: dict, max_year: int):
    """Emit ONE row per momentum-eligible corridor at its first crossing.

    Membership order (the skill's rule: eligibility reads only published
    years <= T0; the outcome is looked up afterwards, and an unobservable
    outcome is missing data - counted, never a membership decision):
      1. entry year T0 (first crossing) - at-instant information;
      2. momentum eligibility: published, strictly positive T0-1 value;
      3. split assignment by entry year (before any outcome read);
      4. outcome observability (host silent in T0+1/T0+2, or the outcome
         window extends beyond the fetched vintage) -> excluded, counted.
    """
    entries = entry_years(cells)
    rows_by_split: dict[str, list[dict]] = {"train": [], "eval": [], "holdout": []}
    excluded = Counter()
    excluded_detail = Counter()
    entries_by_year: dict[int, int] = Counter()

    for (origin, asylum), t0 in sorted(entries.items(), key=lambda kv: (kv[1], kv[0])):
        entries_by_year[t0] += 1
        # --- momentum eligibility (published years <= T0 only)
        prior = cells.get((t0 - 1, origin, asylum))
        if prior is None or prior <= 0:
            reason = ("left_censored_panel_start" if t0 == PANEL_FIRST_YEAR
                      else "no_positive_published_prior_cell")
            excluded["missing_published_prior"] += 1
            excluded_detail[("missing_published_prior", reason,
                             split_of_entry_year(t0) or "outside")] += 1
            continue
        # --- split assignment by entry year (before the outcome is read)
        split = split_of_entry_year(t0)
        # --- outcome observability (never value-conditioned)
        if t0 + 2 > max_year:
            excluded["live_edge_outcome_beyond_vintage"] += 1
            excluded_detail[("live_edge_outcome_beyond_vintage", "outcome_unpublished",
                             split or "outside")] += 1
            continue
        if split is None:
            excluded["outside_declared_windows"] += 1
            continue
        outcome_values = []
        unobserved = False
        for year in (t0 + 1, t0 + 2):
            if year not in host_years.get(asylum, set()):
                unobserved = True
                break
            outcome_values.append(cells.get((year, origin, asylum), 0))
        if unobserved:
            excluded["host_silent_outcome_year"] += 1
            excluded_detail[("host_silent_outcome_year", "label_undefined", split)] += 1
            continue

        value_t0 = cells[(t0, origin, asylum)]
        host_t0 = host_totals.get((t0, asylum))
        host_t0m1 = host_totals.get((t0 - 1, asylum))
        origin_t0 = origin_totals.get((t0, origin))
        origin_t0m1 = origin_totals.get((t0 - 1, origin))
        if (host_t0 is None or host_t0m1 is None or origin_t0 is None
                or origin_t0m1 is None or host_t0 <= 0 or origin_t0 <= 0):
            raise SystemExit(f"construction defect: missing context totals for "
                             f"{origin}->{asylum} entry {t0}")
        prior_years = sorted({year for (year, o, a) in cells
                              if (o, a) == (origin, asylum) and year <= t0 - 1})
        row = {
            "row_id": f"{origin}-{asylum}-{t0}",
            "origin": origin,
            "asylum": asylum,
            "entry_year": t0,
            "apps_t0": value_t0,
            "apps_t0m1": prior,
            "log_growth_into_entry": round(
                math.log(value_t0 + 1) - math.log(prior + 1), 6),
            "surged_into_entry": int(value_t0 >= DOUBLING * prior),
            "years_since_first_seen": t0 - first_seen[(origin, asylum)],
            "prior_history_len": len(prior_years),
            "prior_max": max(cells[(year, origin, asylum)] for year in prior_years),
            "host_apps_t0": host_t0,
            "host_apps_t0m1": host_t0m1,
            "host_growth": round(math.log(host_t0 + 1) - math.log(host_t0m1 + 1), 6),
            "origin_apps_t0": origin_t0,
            "origin_apps_t0m1": origin_t0m1,
            "origin_growth": round(math.log(origin_t0 + 1) - math.log(origin_t0m1 + 1), 6),
            "share_of_host_t0": round(value_t0 / host_t0, 6),
            "share_of_origin_t0": round(value_t0 / origin_t0, 6),
            "entry_date": f"{t0}-12-31",
            "surge_cluster": f"{origin}|{t0}",
            TARGET: int(outcome_values[0] + outcome_values[1] >= DOUBLING * value_t0),
        }
        rows_by_split[split].append(row)

    for split in rows_by_split:
        rows_by_split[split].sort(key=lambda r: (r["entry_year"], r["origin"], r["asylum"]))

    diagnostics = {
        "entries_by_year": dict(sorted(entries_by_year.items())),
        "excluded": dict(sorted(excluded.items())),
        "excluded_detail": {"|".join(key): count
                            for key, count in sorted(excluded_detail.items())},
    }
    return rows_by_split, diagnostics


def full_population_cross_check(cells: dict, host_years: dict, max_year: int):
    """The full-population variant (no momentum eligibility) measured in-build
    as a cross-check against the recorded full-population anchors. Rows are
    never written from this path; it exists so the momentum-eligibility
    refinement is auditable rather than silent (the parent's pattern)."""
    entries = entry_years(cells)
    rows_by_split: dict[str, list] = {"train": [], "eval": [], "holdout": []}
    for (origin, asylum), t0 in entries.items():
        if t0 + 2 > max_year:
            continue
        values = []
        unobserved = False
        for year in (t0 + 1, t0 + 2):
            if year not in host_years.get(asylum, set()):
                unobserved = True
                break
            values.append(cells.get((year, origin, asylum), 0))
        if unobserved:
            continue
        split = split_of_entry_year(t0)
        if split is None:
            continue
        value_t0 = cells[(t0, origin, asylum)]
        label = int(values[0] + values[1] >= DOUBLING * value_t0)
        rows_by_split[split].append({"origin": origin, "label": label, "t0": t0})
    stats = {}
    for split, rows in rows_by_split.items():
        positives = [r for r in rows if r["label"]]
        stats[split] = {
            "rows": len(rows),
            "positives": len(positives),
            "events": len({f"{r['origin']}|{r['t0']}" for r in positives}),
        }
    return stats


def measure_label_operand_recovery(rows_by_split: dict, cells: dict,
                                   host_totals: dict, origin_totals: dict,
                                   host_years: dict) -> dict:
    """The exact cross-row exposure the record requires measured: does any
    BUILT row's shipped aggregate feature EQUAL another row's label operand?

    Row A (origin O, host H, entry T0A) has label operands v1 = A's value at
    T0A+1 and v2 = at T0A+2. A later-built row B from the same origin (or
    into the same host) entering year T0B ships origin_apps_t0[T0B] and
    origin_apps_t0m1[T0B-1] (host equivalents) - sums that include A's
    value at that year as a component. When A is the ONLY corridor with a
    nonzero value from O (or into H) in that year, the shipped sum EQUALS
    the operand exactly. Count exposed target rows per split and whether
    the recovered operand alone already determines the label (>= 2 x T0A).
    """
    built = [(row["origin"], row["asylum"], row["entry_year"], row["apps_t0"],
              split) for split, rows in rows_by_split.items() for row in rows]
    # indexes over built rows: by origin and by host, entry-year -> rows
    by_origin: dict[str, dict[int, list]] = defaultdict(lambda: defaultdict(list))
    by_host: dict[str, dict[int, list]] = defaultdict(lambda: defaultdict(list))
    for origin, host, t0, _, split in built:
        by_origin[origin][t0].append(split)
        by_host[host][t0].append(split)
    exposed: dict[str, Counter] = {s: Counter() for s in ("train", "eval", "holdout")}
    for origin, host, t0a, apps_t0a, split in built:
        for offset, operand_year in ((1, t0a + 1), (2, t0a + 2)):
            if operand_year not in host_years.get(host, set()):
                continue  # unobserved years cannot be recovered
            value = cells.get((operand_year, origin, host), 0)
            label_determining = value >= DOUBLING * apps_t0a
            for scope, totals, index in (("origin", origin_totals, by_origin),
                                          ("host", host_totals, by_host)):
                total = totals.get((operand_year, origin if scope == "origin" else host))
                if total is None or total != value:
                    continue  # not exactly recoverable from this aggregate
                donor_splits = set()
                for donor_year in (operand_year, operand_year + 1):
                    donor_splits.update(index[origin if scope == "origin" else host]
                                        .get(donor_year, ()))
                if donor_splits:
                    exposed[split][f"{scope}_aggregate_exposed_rows"] += 1
                    if label_determining:
                        exposed[split][f"{scope}_aggregate_label_determining"] += 1
    return {split: dict(sorted(counts.items())) for split, counts in exposed.items()}


def check_fixtures(cells: dict, host_years: dict, rows_by_split: dict,
                   excluded_detail: Counter, max_year: int) -> list[dict]:
    """Assert the known-event fixtures against the fetched panel (hard fail)."""
    results = []
    row_keys = {(row["origin"], row["asylum"]): row
                for rows in rows_by_split.values() for row in rows}
    for origin, asylum, t0, want_t0, want_prior, want_v1, want_v2, want_label, name in FIXTURES:
        got_t0 = cells.get((t0, origin, asylum))
        got_prior = cells.get((t0 - 1, origin, asylum))
        got_v1 = (cells.get((t0 + 1, origin, asylum), 0)
                  if t0 + 1 in host_years.get(asylum, set()) else None)
        got_v2 = (cells.get((t0 + 2, origin, asylum), 0)
                  if t0 + 2 in host_years.get(asylum, set()) else None)
        got_label = None
        if got_v1 is not None and got_v2 is not None and got_t0:
            got_label = int(got_v1 + got_v2 >= DOUBLING * got_t0)
        row = row_keys.get((origin, asylum))
        entry_ok = row is not None and row["entry_year"] == t0 \
            and row["apps_t0"] == want_t0 and row["apps_t0m1"] == want_prior
        shipped_label_ok = row is not None and row[TARGET] == want_label
        ok = (got_t0 == want_t0 and got_prior == want_prior
              and got_v1 == want_v1 and got_v2 == want_v2
              and got_label == want_label and entry_ok and shipped_label_ok)
        results.append({"event": name, "corridor": f"{origin}->{asylum}",
                        "entry_year": t0, "apps_t0": got_t0, "apps_t0m1": got_prior,
                        "apps_t0p1": got_v1, "apps_t0p2": got_v2,
                        "expected_label": want_label, "measured_label": got_label,
                        "shipped_row": row is not None, "ok": bool(ok)})
        if not ok:
            log(f"FIXTURE MISMATCH {origin}->{asylum} T0={t0}: "
                f"{got_t0} (prior {got_prior}) -> {got_v1}+{got_v2}, "
                f"label {got_label} vs {want_label}, shipped={row is not None}")
    # left-censored: first crossing at the panel start must NOT be built
    origin, asylum, t0, want_t0 = LEFT_CENSORED_FIXTURE
    got_t0 = cells.get((t0, origin, asylum))
    excluded_ok = ((origin, asylum) not in row_keys
                   and got_t0 == want_t0
                   and excluded_detail[("missing_published_prior",
                                        "left_censored_panel_start", "train")] >= 1)
    results.append({"event": "left-censored first-crossing excluded (SYR->DEU 2000)",
                    "corridor": f"{origin}->{asylum}", "entry_year": t0,
                    "apps_t0": got_t0, "shipped_row": (origin, asylum) in row_keys,
                    "expected": "excluded: no published 1999 prior",
                    "ok": bool(excluded_ok)})
    if not excluded_ok:
        log(f"LEFT-CENSORING FIXTURE MISMATCH {origin}->{asylum} T0={t0}: "
            f"shipped={(origin, asylum) in row_keys}")
    # live edge: entry 2025, outcome beyond the vintage -> excluded, counted
    origin, asylum, t0, want_t0 = LIVE_EDGE_FIXTURE
    got_t0 = cells.get((t0, origin, asylum))
    live_ok = ((origin, asylum) not in row_keys and got_t0 == want_t0
               and t0 + 2 > max_year)
    results.append({"event": "live-edge strict forecast excluded (SSD->ETH 2025)",
                    "corridor": f"{origin}->{asylum}", "entry_year": t0,
                    "apps_t0": got_t0, "shipped_row": (origin, asylum) in row_keys,
                    "expected": "excluded: outcome window beyond the fetched vintage",
                    "ok": bool(live_ok)})
    if not live_ok:
        log(f"LIVE-EDGE FIXTURE MISMATCH {origin}->{asylum} T0={t0}: "
            f"{got_t0}, shipped={(origin, asylum) in row_keys}")
    # no re-entry: a below-threshold later year must not create a second row
    origin, asylum, year, want_value, want_entry = NO_REENTRY_FIXTURE
    got_value = cells.get((year, origin, asylum))
    reentry_ok = (got_value == want_value and got_value < MIN_APPS
                  and row_keys[(origin, asylum)]["entry_year"] == want_entry)
    results.append({"event": "no re-entry below threshold (UKR->POL 2021 = 458)",
                    "corridor": f"{origin}->{asylum}", "apps_2021": got_value,
                    "one_row_entry_year": row_keys[(origin, asylum)]["entry_year"],
                    "ok": bool(reentry_ok)})
    if not reentry_ok:
        log(f"NO-REENTRY FIXTURE MISMATCH {origin}->{asylum} 2021: {got_value}")
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
            "min_entry_year": min((row["entry_year"] for row in rows), default=None),
            "max_entry_year": max((row["entry_year"] for row in rows), default=None),
        }
        log(f"{split}: {stats[split]['rows']} rows, {stats[split]['positives']} "
            f"positives ({stats[split]['distinct_positive_clusters']} events)")
    return stats


def quality_document(out: Path, stats: dict, fetch_info: dict, panel_diag: dict,
                     fixtures: list, built_at: str, recovery: dict) -> None:
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
        "time_column": "entry_date",
        "event_key_column": "surge_cluster",
        "event_key_note": (
            "surge_cluster = origin|entry-year: one displacement event hits "
            "many corridors in one year, so the conservative independent-"
            "event count is the distinct (origin, entry-year) pair among "
            "positives. Rows are one per corridor, so the corridor grain "
            "itself never repeats."),
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "feature_documentation": (
            "every shipped feature is a corridor-year or country-context "
            "total for published years <= T0 (the entry year), or a "
            "corridor/calendar identity. origin/asylum are the publisher's "
            "ISO-3-style codes; entry_year is the first-crossing year's "
            "calendar identity; apps_t0 is the corridor's entry-year total "
            "(the doubling baseline, published at the instant); apps_t0m1 is "
            "the published prior-year total (momentum eligibility requires "
            "it, strictly positive); log_growth_into_entry = ln(apps_t0+1) "
            "- ln(apps_t0m1+1); surged_into_entry flags apps_t0 >= 2 x "
            "apps_t0m1 (the corridor doubled INTO its entry year); "
            "years_since_first_seen is years since the corridor's first "
            "cell in the fetched panel; prior_history_len/prior_max are the "
            "count and maximum of published prior-year cells; host_apps_t0/"
            "host_apps_t0m1/host_growth and origin_apps_t0/origin_apps_t0m1/"
            "origin_growth are the host-country and origin-country "
            "all-corridor totals for years T0/T0-1 and their log growth "
            "(reception-capacity and displacement-pressure context); "
            "share_of_host_t0/share_of_origin_t0 are apps_t0 over those "
            "same-year totals. The T0+1/T0+2 corridor values (the label "
            "operands) and every year > T0 value are excluded from the "
            "shipped columns."),
        "carry_columns": CARRY_COLUMNS,
        "id_columns": ID_COLUMNS,
        "high_cardinality_columns": HIGH_CARDINALITY,
        "high_cardinality_note": (
            "row_id is unique per row; surge_cluster (origin|entry-year), "
            "origin and asylum all carry more levels than rows/5 in the "
            "narrow splits. The one-shot design makes country identity "
            "near-row-unique: 1,129 crossing corridors spread over ~215 "
            "origins and ~130 hosts, so most origin levels carry 1-3 rows "
            "and per-level statistics are memorization, not signal. All "
            "four are declared rather than scored; the identity-only "
            "references in the post-acceptance scoring stage measure "
            "exactly how much country identity alone predicts, and their "
            "information is fully recoverable from the shipped origin/"
            "asylum columns (row_id and surge_cluster from origin, asylum "
            "and entry_year)"),
        "label_source_columns": [
            "corridor G/P totals at Year=T0+1 and Year=T0+2 (source column "
            "'Number of Applications' summed over all application types, "
            "G/P rows only) - never shipped, never entered into any feature"],
        "post_hoc_columns": [],
        "measurements": [
            {"column": "apps_t0", "unit": "persons (integer applications)",
             "frame": "corridor government-procedure persons applications in "
                      "the entry year T0, summed over all application types, "
                      "current-vintage; the doubling baseline"},
            {"column": "apps_t0m1", "unit": "persons (integer applications)",
             "frame": "the same corridor total for year T0-1 (published, "
                      "strictly positive - momentum eligibility)"},
            {"column": "log_growth_into_entry", "unit": "log (natural) point difference",
             "frame": "ln(apps_t0+1) - ln(apps_t0m1+1), the corridor's "
                      "growth into its entry year"},
            {"column": "surged_into_entry", "unit": "binary flag 0/1",
             "frame": "apps_t0 >= 2 x apps_t0m1, the corridor's own last-step "
                      "doubling observed at the instant"},
            {"column": "years_since_first_seen", "unit": "years (integer)",
             "frame": "T0 minus the corridor's first year in the fetched "
                      "panel (panel start 2000 truncates true age; >= 1 by "
                      "the momentum-eligibility rule)"},
            {"column": "prior_history_len", "unit": "years (integer)",
             "frame": "number of published prior-year cells <= T0-1"},
            {"column": "prior_max", "unit": "persons (integer applications)",
             "frame": "maximum published prior-year corridor total <= T0-1"},
            {"column": "host_apps_t0", "unit": "persons (integer applications)",
             "frame": "all-corridor government-procedure total received by "
                      "the host country in the entry year T0"},
            {"column": "host_apps_t0m1", "unit": "persons (integer applications)",
             "frame": "the same host-country total for year T0-1"},
            {"column": "host_growth", "unit": "log (natural) point difference",
             "frame": "ln(host_apps_t0+1) - ln(host_apps_t0m1+1)"},
            {"column": "origin_apps_t0", "unit": "persons (integer applications)",
             "frame": "all-host government-procedure total from the origin "
                      "country in the entry year T0"},
            {"column": "origin_apps_t0m1", "unit": "persons (integer applications)",
             "frame": "the same origin-country total for year T0-1"},
            {"column": "origin_growth", "unit": "log (natural) point difference",
             "frame": "ln(origin_apps_t0+1) - ln(origin_apps_t0m1+1)"},
            {"column": "share_of_host_t0", "unit": "fraction 0-1",
             "frame": "apps_t0 / host_apps_t0, the corridor's share of its "
                      "host's entry-year intake"},
            {"column": "share_of_origin_t0", "unit": "fraction 0-1",
             "frame": "apps_t0 / origin_apps_t0, the corridor's share of its "
                      "origin's entry-year outflow"},
            {"column": "entry_year", "unit": "calendar year (integer)",
             "frame": "the first-crossing year T0; calendar identity of the "
                      "prediction instant"},
            {"column": "entry_date", "unit": "ISO date (year-end of T0)",
             "frame": "calendar identity of the instant's period end; the "
                      "split time column, not an observation"},
            {"column": "surge_cluster", "unit": "origin|entry-year string",
             "frame": "event key for clustered positive counting"},
            {"column": "origin", "unit": "publisher ISO-3-style code",
             "frame": "country of origin identity"},
            {"column": "asylum", "unit": "publisher ISO-3-style code",
             "frame": "country of asylum identity"},
            {"column": "row_id", "unit": "origin-asylum-entryyear string",
             "frame": "row identifier; unique per row (one row per corridor)"},
            {"column": TARGET, "unit": "binary 0/1",
             "frame": "1 iff corridor total(T0+1) + total(T0+2) >= 2 x "
                      "total(T0); a missing corridor row with the host still "
                      "reporting that year counts as 0 applications"},
        ],
        "external_threshold": False,
        "known_event": {
            "name": "post-Aug-2021 Taliban takeover (AFG->USA, entry 2021)",
            "expected_verdict": "exceeds",
            "detail": ("533 in the entry year 2021 (2020: 44) with outcome "
                       "25,082 + 19,320 = 44,402 >= 1,066 -> cum2_2x TRUE - "
                       "asserted in-build with the VEN->COL 2017 TRUE and "
                       "UKR->POL 2014 FALSE fixtures, the SYR->DEU 2000 "
                       "left-censored exclusion, the SSD->ETH 2025 live-edge "
                       "exclusion and the UKR->POL 2021 no-re-entry check"),
            "source": ("UNHCR asylum statistics via HDX (the fetched panel "
                       "itself; values verified at discovery against the "
                       "publisher's own interactive Data Finder and in the "
                       "candidate record's notes.md)"),
        },
        "timing": {
            "prediction_instant": {
                "kind": "publication",
                "period": "Y",
                "days_after_period_end": 232,
                "citation": (
                    "HDX resource update history observed 2026-10-23 and "
                    "unchanged on the 2026-11-04 re-pin: refreshes "
                    "2025-11-05, 2026-02-25, 2026-06-11, 2026-06-19, "
                    "2026-06-22 and 2026-08-20; the 2026-08-20 refresh "
                    "carries complete data through year 2025 (max Year = "
                    "2025 measured on the fetched bytes), 232 days after "
                    "the 2025 period end; UNHCR's Global Trends cycle lands "
                    "mid-T0+1. The instant for a row is the first refresh "
                    "carrying its entry year T0."),
            },
            "features": {
                "period": "Y",
                "published_days_after_period_end": 232,
                "source_kind": "statistical_release",
            },
            "row_selection": {
                "latest_period_used": "Y (the entry year T0, the corridor's first >=500 year)",
                "fields": ["apps_t0 (entry-year corridor total >= 500)",
                           "apps_t0m1 (published positive prior-year value)"],
                "basis": (
                    "eligibility reads only published years <= T0: the "
                    "corridor's first year >= 500 (entry year T0) and a "
                    "published, strictly positive year-(T0-1) value (the "
                    "momentum feature family needs it; capacity measured "
                    "for exactly this variant in the candidate record). "
                    "Label-observability censoring - the host files no G/P "
                    "report at all in T0+1 or T0+2, or the outcome window "
                    "extends beyond the fetched vintage (entries >= 2024 "
                    "on the 2000-2025 snapshot, the live edge) - excludes "
                    "rows whose label is undefined and counts them per "
                    "split in summary.json; it never conditions on the "
                    "label value. The outcome years T0+1/T0+2 never enter "
                    "eligibility or split assignment."),
            },
            "observations": [
                {"period": "2025", "period_end": "2025-12-31",
                 "published": "2026-08-20"},
            ],
        },
        "split_windows": {
            "train": {"start": f"{TRAIN_ENTRIES[0]}-01-01",
                      "end": f"{EVAL_ENTRIES[0]}-01-01"},
            "eval": {"start": f"{EVAL_ENTRIES[0]}-01-01",
                     "end": f"{HOLDOUT_ENTRIES[0]}-01-01"},
            "holdout": {"start": f"{HOLDOUT_ENTRIES[0]}-01-01",
                        "end": f"{HOLDOUT_ENTRIES[1] + 1}-01-01"},
        },
        "split_boundaries": {
            "train": ("entry years 2000-2014 (window end exclusive; entry-year "
                      "2000 rows are all excluded as left-censored by the "
                      "momentum-eligibility rule - counted in summary.json)"),
            "eval": "entry years 2015-2020 (window end exclusive)",
            "holdout": ("entry years 2021-2023 (window end exclusive; entries "
                        "whose outcome window extends beyond the fetched "
                        "vintage are the live edge, excluded and counted - "
                        "57 rows for this design on the 2000-2025 snapshot)"),
        },
        "positive_events": positive_events,
        "positive_events_note": (
            "positives and distinct (origin, entry-year) surge clusters per "
            "split, recomputed from the written rows; the gate re-verifies"),
        "expected_duplicate_ids": 0,
        "id_columns_are_entity_keys": True,
        "id_columns_note": (
            "row_id = origin-asylum-entryyear names ONE corridor at its one "
            "first crossing; the one-shot design never repeats a corridor, "
            "so every identifier carries exactly one row and one label"),
        "splits": LAYOUT,
        "evaluation_contract": {
            "use": "retrospective_research",
            "access": "isolated_rows",
            "training_label_timing": "unverified",
            "scope_note": (
                "each row is a corridor taken once at its first crossing; "
                "features read published years <= T0 only; the runner "
                "predicts row-wise from the shipped columns. Labeled eval "
                "is development/validation; the holdout is the final test "
                "and stays outside evaluated agents' workspaces. "
                "Training-label timing is UNVERIFIED: HDX distributes one "
                "in-place-revised resource with no historical vintages, so "
                "no full-row availability ledger can be constructed and "
                "the artifact is retrospective research only, never a "
                "certified historical forecasting setup. Historical rows "
                "are publication-lag nowcasts (the outcome window has "
                "partially elapsed at the instant but both outcome years "
                "are unpublished on this channel); corridors entering 2025 "
                "are live strict forecasts but are NOT shipped as scored "
                "rows because their outcome is unobserved in the fetched "
                "vintage."),
            "feature_evidence": {
                "row_id": {
                    "source": "row key origin-asylum-entryyear",
                    "availability": "identity of the row; corridor and entry "
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
                "entry_year": {
                    "source": "row key (the corridor's first year >= 500)",
                    "availability": "calendar arithmetic on published years "
                                    "<= T0; the instant is the refresh "
                                    "carrying year T0",
                    "status": "verified"},
                "apps_t0": {
                    "source": "sum of 'Number of Applications' over G/P "
                              "application-type rows at Year T0",
                    "availability": "the refresh carrying year T0 IS the "
                                    "instant (observed 2026-08-20 carrying "
                                    "complete data through 2025)",
                    "status": "assumed",
                    "assumption": "current-vintage value; the value "
                                  "published at past instants is "
                                  "unverifiable (no historical vintages)"},
                "apps_t0m1": {
                    "source": "the same summed panel at Year T0-1",
                    "availability": "published one refresh before the "
                                    "instant, so available at it",
                    "status": "assumed",
                    "assumption": "current-vintage value (see apps_t0)"},
                "log_growth_into_entry": {
                    "source": "deterministic function of apps_t0 and apps_t0m1",
                    "availability": "derivable at the instant from published "
                                    "years <= T0",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "surged_into_entry": {
                    "source": "deterministic flag on apps_t0 >= 2 x apps_t0m1",
                    "availability": "derivable at the instant",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "years_since_first_seen": {
                    "source": "T0 minus the corridor's first year in the "
                              "fetched panel",
                    "availability": "derivable at the instant from published "
                                    "years <= T0",
                    "status": "assumed",
                    "assumption": "panel start 2000 truncates true corridor "
                                  "age for pre-2000 corridors; the value is "
                                  "'years since first observed in the "
                                  "fetched panel'"},
                "prior_history_len": {
                    "source": "count of published prior-year cells <= T0-1",
                    "availability": "derivable at the instant",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "prior_max": {
                    "source": "maximum published prior-year corridor total "
                              "<= T0-1",
                    "availability": "derivable at the instant",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "host_apps_t0": {
                    "source": "all-corridor sum of the same G/P stream at "
                              "(Year T0, asylum)",
                    "availability": "published at the instant (same refresh "
                                    "as apps_t0)",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "host_apps_t0m1": {
                    "source": "all-corridor sum at (Year T0-1, asylum)",
                    "availability": "published one refresh before the instant",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "host_growth": {
                    "source": "deterministic function of host totals at T0 "
                              "and T0-1",
                    "availability": "derivable at the instant",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "origin_apps_t0": {
                    "source": "all-host sum of the same G/P stream at "
                              "(Year T0, origin)",
                    "availability": "published at the instant",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "origin_apps_t0m1": {
                    "source": "all-host sum at (Year T0-1, origin)",
                    "availability": "published one refresh before the instant",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "origin_growth": {
                    "source": "deterministic function of origin totals at T0 "
                              "and T0-1",
                    "availability": "derivable at the instant",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "share_of_host_t0": {
                    "source": "deterministic ratio apps_t0 / host_apps_t0",
                    "availability": "derivable at the instant",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "share_of_origin_t0": {
                    "source": "deterministic ratio apps_t0 / origin_apps_t0",
                    "availability": "derivable at the instant",
                    "status": "assumed",
                    "assumption": "inherits the current-vintage assumption"},
                "entry_date": {
                    "source": "calendar year-end of the entry year T0",
                    "availability": "calendar arithmetic; the carry column "
                                    "is the split time column, not an "
                                    "observation",
                    "status": "verified"},
                "surge_cluster": {
                    "source": "origin + entry year (event key)",
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
                    "snapshot is pinned by sha256 (byte-identical to the "
                    "2026-10-23 and 2026-11-04 discovery pins) and the "
                    "build asserts the recorded known-event fixtures and "
                    "split anchors against it; values are construction-time "
                    "current-vintage and no historical point-in-time "
                    "availability is claimed. Same documented posture as "
                    "unhcr-refugee-data-finder and "
                    "abs-visitor-arrivals-direction."),
            },
            "selection": {
                "kind": "prediction_time",
                "evidence": (
                    "membership reads only published years <= T0: the "
                    "corridor's first >= 500 year (T0) plus a published "
                    "strictly positive T0-1 value. The outcome years are "
                    "looked up afterwards solely to compute the label; a "
                    "host-silent outcome year or a live-edge entry (outcome "
                    "beyond the vintage) excludes the row as UNOBSERVED "
                    "TARGET and is counted per split in summary.json - it "
                    "never conditions on the label value and never decides "
                    "another row's membership. Left-censored T0=2000 "
                    "entrants are excluded by the momentum rule with "
                    "per-split counts."),
            },
            "limitations": [
                "Annual grain only on the machine-fetchable channel; a "
                "monthly variant would need the WAF-gated UNHCR Data Finder "
                "app or an operator decision on browser-captured exports.",
                "Current-vintage panel with no historical vintages: "
                "retrospective research, not certified historical "
                "forecasting; intra-basis revision size is unmeasurable "
                "without archived vintages.",
                "Historical rows are publication-lag nowcasts: the outcome "
                "window has partially elapsed at the instant; what is "
                "claimed is value-unavailability on this channel, not that "
                "the window follows the instant.",
                "The momentum association of the cum2_2x label is NOT "
                "monotone: measured positive rate by growth into entry is "
                "42.0% (<1.5x) / 45.6% (1.5-3x) / 37.5% (>3x) - past-peak "
                "corridors revert. The task's phenomenon includes mean "
                "reversion; it is not the parent task's momentum "
                "continuation, and every document must describe it that way.",
                "Prevalence drifts across splits (32.8% train / 44.8% eval "
                "/ 42.9% holdout full-population; the momentum-eligible "
                "variant is re-measured in summary.json) - a property of "
                "the period, reported beside every score.",
                "Positives cluster by (origin, entry-year) displacement "
                "events beyond the row count; clustered counts and "
                "cluster-aware intervals are reported beside every score.",
                "Momentum eligibility excludes 369 full-population rows "
                "(192 left-censored T0=2000 entrants plus corridors with no "
                "positive published prior cell) - the excluded population "
                "is counted per split in summary.json, never silently "
                "dropped.",
                "Temporary-protection registrations (Ukrainians in the EU "
                "from 2022) are not asylum applications and do not enter "
                "the stream - the 2022 Ukraine displacement is largely "
                "absent by construction (UKR->POL fixture).",
                "Rows share origins and hosts across windows: a later "
                "entrant's origin/host aggregate features can contain an "
                "earlier entrant's outcome-year value as a component, and "
                "when the earlier corridor is the only flow on that side "
                "in that year the aggregate EQUALS the label operand "
                "exactly (measured: cross_row_label_operand_recovery in "
                "summary.json). Partial information, declared; access is "
                "isolated_rows and the gate's probes measure the exposure.",
                "Corridor age and prior-history depth are measured from the "
                "fetched panel's 2000 start, truncating true history for "
                "older corridors.",
                "The live edge (entries 2024-2025: 57 corridors on this "
                "snapshot, including SSD->ETH at 50,148) carries no "
                "observable outcome and ships NO scored row; a deployment "
                "surface would need a future vintage.",
            ],
            "cross_row_audit": {
                "probes": [
                    {"name": "corridor_grain_no_donor_exists",
                     "entity_columns": ["origin", "asylum"],
                     "time_column": "entry_date",
                     "operation": "copy",
                     "left": "surged_into_entry",
                     "offset_months": 12,
                     "expectation": (
                         "the parent task's exact failure mode: a same-"
                         "corridor donor row one period later shipping the "
                         "target's label operand. The one-shot design gives "
                         "every corridor exactly one row, so NO donor can "
                         "exist at any offset - coverage MUST read 0 in "
                         "every split; nonzero coverage means the build "
                         "shipped two rows per corridor")},
                    {"name": "origin_aggregate_next_year_exposure",
                     "entity_columns": ["origin"],
                     "time_column": "entry_date",
                     "operation": "gt",
                     "left": "origin_apps_t0",
                     "right": "apps_t0",
                     "right_row": "earlier",
                     "offset_months": 12,
                     "expectation": (
                         "a same-origin corridor entering T0+1 ships "
                         "origin_apps_t0 = the origin's total in the "
                         "target's first outcome year, which CONTAINS the "
                         "target's first label operand as a component "
                         "(and EQUALS it when the target is the origin's "
                         "only flow that year - see "
                         "cross_row_label_operand_recovery). The probe "
                         "measures how often that donated aggregate, "
                         "compared with the target's own baseline, "
                         "predicts the label: coverage is the exposure "
                         "bound at corridor grain, mismatches are "
                         "reported, not a pass/fail")},
                    {"name": "origin_aggregate_two_year_exposure",
                     "entity_columns": ["origin"],
                     "time_column": "entry_date",
                     "operation": "gt",
                     "left": "origin_apps_t0",
                     "right": "apps_t0",
                     "right_row": "earlier",
                     "offset_months": 24,
                     "expectation": (
                         "the same exposure through the second outcome year "
                         "T0+2: a same-origin corridor entering T0+2 ships "
                         "the origin's total for that year, containing the "
                         "target's second label operand as a component")},
                    {"name": "host_aggregate_next_year_exposure",
                     "entity_columns": ["asylum"],
                     "time_column": "entry_date",
                     "operation": "gt",
                     "left": "host_apps_t0",
                     "right": "apps_t0",
                     "right_row": "earlier",
                     "offset_months": 12,
                     "expectation": (
                         "the host-side mirror: a corridor into the same "
                         "host entering T0+1 ships host_apps_t0 = the "
                         "host's total in the target's first outcome year, "
                         "which contains the target's operand as a "
                         "component")},
                ],
                "rationale": (
                    "the dropped panel task self-answered at corridor grain "
                    "(a label-year T+1 row shipped the year-T total that "
                    "was the T row's label operand; frozen recovery AUC "
                    "0.975/0.983). The one-shot redesign removes that "
                    "exposure STRUCTURALLY - one row per corridor - and "
                    "the corridor-grain probe must read coverage 0. The "
                    "residual exposure is through ORIGIN- and HOST-level "
                    "aggregate features, which the generic probes cannot "
                    "express as equality: the build measures exactly "
                    "whether any shipped aggregate EQUALS another row's "
                    "label operand (cross_row_label_operand_recovery in "
                    "summary.json) and the three declared probes measure "
                    "the joinable exposure on the built artifact. Covered "
                    "rows make this restricted retrospective research under "
                    "an enforced isolated-rows protocol; no historical "
                    "forecasting claim is made."),
                "auxiliary_files_review": (
                    "the extract ships exactly the runner layout - "
                    "public/train.csv, public/eval.csv, "
                    "private/holdout.csv, meta.json, quality.json; the "
                    "fetched source CSV, the panel and all diagnostics "
                    "stay outside the artifact; no joint label matrices or "
                    "other solver-visible files exist in the dataset "
                    "directory"),
                "reverse_history": (
                    "not performable: HDX retains no archived vintages of "
                    "this resource (observed in-place revision 2025-11-05 "
                    "through 2026-08-20), so no as-of reconstruction can "
                    "be probed; the current-vintage posture above is the "
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
    parser.add_argument("--work-dir", default="/tmp/unhcr-corridor")
    parser.add_argument("--csv", default=None,
                        help="local panel copy for a dry run (worker fetches)")
    parser.add_argument("--built-at", default=None,
                        help="pin the build timestamp for byte-identical rebuilds")
    parser.add_argument("--summary-out", default=None,
                        help="optional path for summary.json (default: <out>/../summary.json)")
    parser.add_argument("--rehearsal", action="store_true",
                        help="synthetic rehearsal mode: skip the real-data "
                             "anchor asserts and known-event fixtures (a "
                             "synthetic panel cannot reproduce them); every "
                             "structural check, the gate minimums, the "
                             "exclusion buckets, the recovery measurement "
                             "and all writer code still run. Never set by "
                             "the worker entrypoint.")
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
            "asserting the known-event fixtures and split anchors against it")

    cells, host_years, host_totals, origin_totals, first_seen, panel_diag = \
        load_panel(csv_path)
    years = sorted({key[0] for key in cells})
    max_year = years[-1]
    log(f"panel: {panel_diag['distinct_corridor_year_cells']} corridor-year "
        f"cells, years {years[0]}..{max_year}")
    if years[0] > PANEL_FIRST_YEAR or max_year < PANEL_LAST_YEAR:
        raise SystemExit(f"unexpected panel year range {years[0]}..{max_year}")
    if max_year > PANEL_LAST_YEAR:
        log(f"NOTE: the fetched vintage carries years beyond {PANEL_LAST_YEAR}; "
            "the declared entry-year windows stay fixed (2021-2023 holdout) "
            "and later entries are counted, never shipped")

    rows_by_split, build_diag = build_rows(
        cells, host_years, host_totals, origin_totals, first_seen, max_year)

    total_rows = sum(len(rows) for rows in rows_by_split.values())
    if total_rows == 0:
        raise SystemExit("no rows built - the eligibility filter matched nothing")

    # ---- hard anchors (recorded discovery measurements, pinned source) ----
    full_pop = full_population_cross_check(cells, host_years, max_year)
    if args.rehearsal:
        log("== rehearsal mode: real-data anchor asserts and known-event "
            "fixtures skipped (synthetic panel); gate minimums still enforced")
        fixtures = [{"event": "synthetic rehearsal: real-data anchors and "
                              "known-event fixtures skipped", "ok": True}]
    else:
        log("== anchor check (momentum-eligible primary design)")
        for split in ("train", "eval", "holdout"):
            rows = rows_by_split[split]
            positives = sum(row[TARGET] for row in rows)
            events = len({row["surge_cluster"] for row in rows if row[TARGET]})
            want = ANCHORS[split]
            if (len(rows), positives, events) != (want["rows"], want["positives"],
                                                  want["events"]):
                raise SystemExit(
                    f"{split} anchor mismatch: built {len(rows)} rows / "
                    f"{positives} positives / {events} events, recorded "
                    f"{want['rows']}/{want['positives']}/{want['events']} - "
                    "vintage drift or construction defect; do not ship")
            log(f"{split}: {len(rows)}/{positives}/{events} == anchor")
        for split in ("train", "eval", "holdout"):
            want = ANCHORS_FULL_POP[split]
            if (full_pop[split]["rows"], full_pop[split]["positives"],
                    full_pop[split]["events"]) != (want["rows"], want["positives"],
                                                    want["events"]):
                raise SystemExit(
                    f"{split} full-population cross-check mismatch: measured "
                    f"{full_pop[split]}, recorded {want} - vintage drift or "
                    "construction defect; do not ship")
        log("full-population cross-check matches the recorded design table")

        excluded_detail = Counter()
        for key, count_str in build_diag["excluded_detail"].items():
            parts = key.split("|")
            excluded_detail[tuple(parts[:2] + [parts[2]])] = int(count_str)
        fixtures = check_fixtures(cells, host_years, rows_by_split,
                                  excluded_detail, max_year)

    for split in ("eval", "holdout"):
        if sum(row[TARGET] for row in rows_by_split[split]) < MIN_SPLIT_POSITIVES:
            raise SystemExit(f"{split} below the {MIN_SPLIT_POSITIVES} gate "
                             "positives threshold")
        events = len({row["surge_cluster"] for row in rows_by_split[split]
                      if row[TARGET]})
        if events < MIN_SPLIT_EVENTS:
            raise SystemExit(f"{split} has {events} distinct positive events - "
                             f"below the {MIN_SPLIT_EVENTS} gate threshold")

    log("== cross-row label-operand recovery measurement")
    recovery = measure_label_operand_recovery(
        rows_by_split, cells, host_totals, origin_totals, host_years)
    for split, counts in recovery.items():
        log(f"{split}: {counts}")

    log("== write splits")
    stats = write_splits(out, rows_by_split)

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
        "split": (f"temporal on the entry year T0: train {TRAIN_ENTRIES[0]}-"
                  f"{TRAIN_ENTRIES[1]}, eval {EVAL_ENTRIES[0]}-{EVAL_ENTRIES[1]}, "
                  f"holdout {HOLDOUT_ENTRIES[0]}-{HOLDOUT_ENTRIES[1]}"),
        "split_description": (
            f"temporal on the entry year (first year >= {MIN_APPS} "
            "government-procedure applications): train 2000-2014, eval "
            "2015-2020, holdout 2021-2023; one row per corridor at first "
            "crossing; momentum eligibility requires a published, strictly "
            "positive year-(T0-1) corridor value; label = corridor total "
            "over T0+1..T0+2 >= 2 x T0 total"),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    quality_document(out, stats, fetch_info, panel_diag, fixtures, built_at,
                     recovery)

    # ---- summary.json: construction diagnostics; NO performance numbers ----
    per_entry_year = {}
    for split, rows in rows_by_split.items():
        by_year = defaultdict(lambda: [0, 0])
        for row in rows:
            entry = by_year[row["entry_year"]]
            entry[0] += 1
            entry[1] += row[TARGET]
        per_entry_year[split] = {year: {"rows": entry[0], "positives": entry[1]}
                                 for year, entry in sorted(by_year.items())}
    summary = {
        "name": NAME,
        "stage": "construction (no performance metric computed anywhere here)",
        "fetch": fetch_info,
        "fetch_matches_discovery_pin": fetch_info["sha256"] == PINNED_SHA256,
        "panel": panel_diag,
        "panel_year_range": [years[0], max_year],
        "entries_by_year": build_diag["entries_by_year"],
        "exclusions": build_diag["excluded"],
        "exclusion_detail": build_diag["excluded_detail"],
        "split_stats": stats,
        "anchors_checked": ANCHORS,
        "full_population_cross_check": {
            "recorded_on": "pinned 2026-11-04 snapshot (designs.json "
                           "elig500_cum2_2x.splits)",
            "measured": full_pop,
            "note": ("the full-population variant (no momentum eligibility) "
                     "is measured in-build as a cross-check only; shipped "
                     "rows are the momentum-eligible variant"),
        },
        "per_entry_year": per_entry_year,
        "cross_row_label_operand_recovery": {
            "method": (
                "for every built row A and each outcome year y in "
                "{T0+1, T0+2}: A's value at y is EXACTLY recoverable from "
                "another built row's shipped aggregate when A is the only "
                "corridor with a nonzero value on that side (origin or "
                "host) in year y AND some other built row from that "
                "origin/host entered y or y+1 (shipping the aggregate as "
                "origin_apps_t0/origin_apps_t0m1 or host_apps_t0/"
                "host_apps_t0m1). label_determining = the recovered operand "
                "alone is >= 2 x apps_t0, so the label is already decided"),
            "per_split": recovery,
        },
        "fixtures": fixtures,
        "built_at_utc": built_at,
        "shipped_rows": total_rows,
    }
    summary_path = Path(args.summary_out) if args.summary_out else out.parent / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=1) + "\n")
    log(f"== done: {total_rows} rows written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
