#!/usr/bin/env python3
"""Construction script for the `chicago-food-inspections` candidate.

Task: given everything documented about an establishment and its own prior
inspections before the visit begins, which violation code will this inspection
record? The multi-label formulation is realized as one binary runner config
per floor violation code, because the existing runner scores one binary target
per task (task.json reads one `target`; the benchmark score is holdout AUC).
The per-level pattern is the one `noaa-tide-flooding` shipped as its `temporal`
and `station_disjoint` levels: each level is a complete runner layout, gated
on its own.

Runner-contract decision (recorded in the candidate record before this build):
ship `code_<NN>/` per floor code - a full `public/train.csv`,
`public/eval.csv`, `private/holdout.csv`, `meta.json`, `quality.json` - with
target column `code_<NN>` = 1 iff code NN is in the inspection's violation set.
The OTHER codes' label columns are NOT shipped inside a config: they parse from
the same post-visit `violations` blob as the target, so as features they would
be post-hoc cross-label leakage. `labels.csv` at the extract root carries the
joint multi-label matrix (one row per inspection, one column per floor code)
so the set formulation is consumable without re-pulling the source.

Where this runs
---------------
**On a temporary worker, not on the coordinator.** The pool is ~226,000 rows
whose `violations` blob averages 1,447 bytes/row (~458 MB streamed, measured
in the candidate record); the coordinator has 1.9 GiB RAM and ~6 GB disk. Use
`--limit` for a bounded local exercise that proves the script works.

Leakage discipline, from the candidate notes
--------------------------------------------
Prediction instant: the moment the inspection is opened, before any
observation. Shipped features are static facility attributes, the
inspection's own type, the calendar position of `inspection_date`, and fields
of the SAME licence's strictly-earlier pool inspections (prior results, code
counts, and whether the target code was cited last time). The row's own
`violations` blob (label source), `results` (the inspector's outcome) and the
per-violation comment text are fetched to derive labels and priors, then
excluded from every shipped file. Priors use pool inspections with
`inspection_date` STRICTLY earlier than the current row's date, so a same-day
re-inspection of the same licence can never serve as its own history.

`aka_name` is not fetched: free-text facility alias, restates the dba
association already carried by `license_` and `facility_type`; withheld as a
publication decision, mirroring the `respondents` decision recorded for
chicago-doah-adjudication.

Floor rule (stated in advance, measured at construction): a code ships as a
config iff it appears in >= `--min-rate` (default 1%) of the modelling pool
AND carries >= 30 positives on >= 20 distinct positive days in BOTH the eval
and holdout windows - the qualification gate's own minimums, so every config
that is written is one the gate can score. Codes the window minimums drop are
recorded in the manifest, not silently lost.

The output directory is checked by `skills/dataset-qualification/`, which is
the project's gate before a candidate goes to the benchmark.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date as date_cls
from datetime import datetime, timezone
from pathlib import Path

DATASET = "4ijn-s7e5"
BASE = "https://data.cityofchicago.org"
USER_AGENT = {"User-Agent": "scout-dataset-factory/0.1 (construction)"}

# The modelling pool, exactly as probed in the candidate record: result in
# (Pass, Fail, Pass w/ Conditions) AND a non-null violations blob. Non-outcome
# rows can carry stale text (No Entry 777, Not Ready 82, Out of Business 44),
# so the pool is defined by `results`, never by `violations IS NOT NULL` alone.
POOL_WHERE = ("results IN ('Pass','Fail','Pass w/ Conditions') "
              "AND violations IS NOT NULL")

# Fetched to derive labels and priors; never written to any shipped file.
LABEL_SOURCE = "violations"
OUTCOME_COLUMN = "results"

# Static facility attributes + the visit's own type + calendar position, all
# documented by the publisher and known when a canvass is scheduled or a
# complaint triggers a visit. `license_` ships as a feature (declared
# high-cardinality): the runner may legitimately model per-establishment
# effects, and the same licence spans split windows BY DESIGN because prior
# history is the point of the task - so it is NOT an id column (the gate's
# cross-split check applies to id columns only).
FEATURES = [
    "license_",
    "inspection_date",
    "facility_type",
    "risk",
    "zip",
    "latitude",
    "longitude",
    "inspection_type",
    "day_of_week",
    "month",
    "prior_inspections",
    "days_since_previous",
    "previous_result",
    "prior_fail_rate",
    "prior_mean_code_count",
    "prev_code_present",
]

ID_COLUMNS = ["inspection_id"]
HIGH_CARDINALITY = ["license_", "inspection_date", "latitude", "longitude"]
CARRY_COLUMNS: list[str] = []

EXCLUDED_POST_HOC = [LABEL_SOURCE, OUTCOME_COLUMN]

SPLIT_WINDOWS = {
    "train": {"start": "2010-01-01", "end": "2021-01-01"},
    "eval": {"start": "2021-01-01", "end": "2024-01-01"},
    "holdout": {"start": "2024-01-01", "end": "2026-10-01"},
}

LAYOUT = {"train": Path("public") / "train.csv",
          "eval": Path("public") / "eval.csv",
          "holdout": Path("private") / "holdout.csv"}

POSITIVE_LABEL = 1

# Floor-rule constants: the gate's own scoring minimums (MIN_EVAL_POSITIVES=30,
# MIN_DISTINCT_EVENTS=20 in skills/dataset-qualification), asserted per window
# at build time so an unscoreable code is dropped with its name in the manifest.
MIN_POSITIVES = 30
MIN_DISTINCT_DAYS = 20

# Codes are parsed by number, never by description string: 28 of 61 codes have
# more than one rendering across the 16.7-year history (notes.md).
CODE_RE = re.compile(r"(?:^|\|)\s*(\d{1,3})\.")

# The City's mandatory derivative disclaimer, verbatim as in
# candidates/chicago-doah-adjudication (license.json requires it verbatim).
DISCLAIMER = ("This site provides applications using data that has been "
              "modified for use from its original source, www.cityofchicago.org, "
              "the official website of the City of Chicago. The City of Chicago "
              "makes no claims as to the content, accuracy, timeliness, or "
              "completeness of any of the data provided at this site. The data "
              "provided at this site is subject to change at any time. It is "
              "understood that the data provided at this site is being used at "
              "one's own risk.")

OWNED_MARKER = ".dataset-factory-extract"
FORBIDDEN_OUT = ("/", "/etc", "/usr", "/var", "/opt/data", "/root", "/home")

PREDICTION_TIME = ("The moment the inspection is opened, before any "
                   "observation: inspection_date is known when a canvass is "
                   "scheduled or a complaint triggers a visit, and every "
                   "feature is a static facility attribute, the inspection's "
                   "own type, or a field of an earlier inspection of the "
                   "same licence.")


def prepare_output(out: Path) -> None:
    """Clear a previously generated extract, or refuse.

    Mirrors the austin-911-response rule: an arbitrary `--out` is never
    recursively deleted. The protected-path check runs before the existence
    check so the behaviour does not depend on the host.
    """
    resolved = out.expanduser()
    if resolved.resolve() in {Path(p).resolve() for p in FORBIDDEN_OUT}:
        raise SystemExit(f"refusing --out {resolved}: that is a protected path")
    if resolved.exists():
        if (resolved / ".git").exists():
            raise SystemExit(f"refusing --out {resolved}: it contains a .git directory")
        if not resolved.is_dir():
            raise SystemExit(f"refusing --out {resolved}: it exists and is not a directory")
        if not (resolved / OWNED_MARKER).is_file():
            entries = sorted(entry.name for entry in resolved.iterdir())
            if entries:
                raise SystemExit(
                    f"refusing to clear {resolved}: it was not created by this "
                    f"script (no {OWNED_MARKER}) and holds {len(entries)} "
                    f"entr{'y' if len(entries) == 1 else 'ies'}: {entries[:8]}. "
                    "Point --out at an empty directory or a previous extract.")
        else:
            for child in sorted(resolved.iterdir()):
                if child.name == OWNED_MARKER:
                    continue
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
    resolved.mkdir(parents=True, exist_ok=True)
    (resolved / OWNED_MARKER).write_text(
        "Generated by candidates/chicago-food-inspections/source/build.py. "
        "Safe to clear.\n")


def get_json(url: str, attempts: int = 4, timeout: int = 180):
    last = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers=USER_AGENT)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:160]}"
        except Exception as exc:  # noqa: BLE001
            last = repr(exc)
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"request failed after {attempts} attempts: {last}")


def resource_url(params: dict) -> str:
    return f"{BASE}/resource/{DATASET}.json?" + urllib.parse.urlencode(params)


def count(where: str) -> int:
    rows = get_json(resource_url({"$select": "count(*) AS n", "$where": where}))
    return int(rows[0]["n"]) if rows else 0


def stream_rows(where: str, select: str, page_size: int, limit: int | None = None,
                order: str = "inspection_id", tally: dict | None = None):
    """Yield pool rows in a total order. `inspection_id` is unique per row
    (316,205 distinct in 316,205 rows, measured in the candidate record), so it
    is its own tiebreaker and offset paging is deterministic. `tally` counts
    HTTP pages so the manifest records a measured request count."""
    offset = 0
    seen = 0
    while True:
        want = page_size if limit is None else min(page_size, limit - seen)
        if want <= 0:
            return
        params = {"$select": select, "$where": where, "$order": order,
                  "$limit": str(want), "$offset": str(offset)}
        rows = get_json(resource_url(params))
        if tally is not None:
            tally["pages"] = tally.get("pages", 0) + 1
        if not rows:
            return
        for row in rows:
            yield row
        seen += len(rows)
        offset += len(rows)
        if len(rows) < want:
            return


def parse_codes(blob: str) -> set[int]:
    """The violation codes cited in one inspection's blob, by number only."""
    return {int(match.group(1)) for match in CODE_RE.finditer(blob or "")}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def auc_from_scores(labels: list[int], scores: list[float]) -> float | None:
    """Rank-based ROC AUC, ties averaged. Pure stdlib (austin-911 pattern)."""
    if len(labels) != len(scores):
        raise ValueError("labels and scores must align")
    pairs = sorted(zip(scores, labels), key=lambda pair: pair[0])
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    rank_sum = 0.0
    index = 0
    while index < len(pairs):
        end = index
        while end + 1 < len(pairs) and pairs[end + 1][0] == pairs[index][0]:
            end += 1
        average_rank = (index + end) / 2.0 + 1.0
        for position in range(index, end + 1):
            if pairs[position][1] == 1:
                rank_sum += average_rank
        index = end + 1
    return (rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def window_of(inspection_date: str) -> str:
    for window_name, window in SPLIT_WINDOWS.items():
        if window["start"] <= inspection_date < window["end"]:
            return window_name
    return "outside"


def enrich_with_priors(rows: list[dict]) -> list[dict]:
    """Walk the licence panel in (licence, date) order, attaching priors that
    use only STRICTLY-earlier dates of the same licence.

    Rows of the same licence and date form one group: they all see the same
    prior state, and the group's own inspections update the state only after
    every row of the group is enriched - so a same-day re-inspection can never
    serve as its own history. Within a group the state's "most recent"
    snapshot is the group's last row in inspection_id order, deterministic
    because the sort key is total.
    """
    rows.sort(key=lambda r: (r["license_"], r["inspection_date"],
                             str(r["inspection_id"])))
    enriched: list[dict] = []
    state = {"license": None, "count": 0, "prev_date": None, "prev_result": "",
             "prev_codes": frozenset(), "fails": 0, "code_sum": 0}
    index = 0
    while index < len(rows):
        current_license = rows[index]["license_"]
        if state["license"] != current_license:
            state = {"license": current_license, "count": 0, "prev_date": None,
                     "prev_result": "", "prev_codes": frozenset(), "fails": 0,
                     "code_sum": 0}
        current_date = rows[index]["inspection_date"]
        end = index
        while (end < len(rows) and rows[end]["license_"] == current_license
               and rows[end]["inspection_date"] == current_date):
            end += 1
        group = rows[index:end]
        has_prior = bool(state["count"])
        delta = None
        if has_prior:
            delta = ((date_cls.fromisoformat(current_date)
                     - date_cls.fromisoformat(state["prev_date"])).days)
        year, month, day = (int(part) for part in current_date.split("-"))
        weekday = date_cls(year, month, day).weekday()
        for record in group:
            entry = dict(record)
            entry["day_of_week"] = weekday
            entry["month"] = month
            entry["prior_inspections"] = state["count"]
            entry["days_since_previous"] = delta if has_prior else -1
            entry["previous_result"] = state["prev_result"] if has_prior else ""
            entry["prior_fail_rate"] = (round(state["fails"] / state["count"], 6)
                                        if has_prior else -1)
            entry["prior_mean_code_count"] = (round(state["code_sum"] / state["count"], 4)
                                              if has_prior else -1)
            entry["has_prior"] = has_prior
            entry["prev_codes"] = state["prev_codes"]
            enriched.append(entry)
        for record in group:
            state["count"] += 1
            state["prev_date"] = current_date
            state["prev_result"] = record["result"]
            state["prev_codes"] = frozenset(record["codes"])
            state["fails"] += int(record["result"] == "Fail")
            state["code_sum"] += len(record["codes"])
        index = end
    return enriched


def write_meta(config_dir: Path, name: str, code: int, fieldnames: list[str],
               rows: dict, positive_rate: dict, built_at: str) -> None:
    meta = {
        "name": f"chicago-food-inspections-{name}",
        "description": ("Will this inspection of a Chicago food establishment "
                        f"cite violation code {code}? Predicted at the moment "
                        "the inspection opens, from facility attributes, the "
                        "inspection's own type, the calendar position, and the "
                        "establishment's own strictly-earlier inspection history "
                        "under its licence."),
        "source": f"{BASE}/resource/{DATASET}.json (City of Chicago Food Inspections)",
        "license": "City of Chicago Data Terms of Use "
                   "(LicenseRef-CityOfChicago-DataTermsOfUse); see LICENSE.md",
        "derivative_disclaimer": DISCLAIMER,
        "target": name,
        "positive_label": POSITIVE_LABEL,
        "id_columns": list(ID_COLUMNS),
        "columns": fieldnames,
        "rows": rows,
        "positive_rate": positive_rate,
        "split": {
            "strategy": "temporal by inspection_date",
            "windows": SPLIT_WINDOWS,
        },
        "label_rule": f"{name} = 1 if code {code} is parsed from the row's "
                      "violations blob, else 0",
        "label_source_column": LABEL_SOURCE,
        "prediction_time": PREDICTION_TIME,
        "features": FEATURES,
        "excluded_post_hoc": EXCLUDED_POST_HOC,
        "carry_columns": CARRY_COLUMNS,
        "built_at_utc": built_at,
    }
    (config_dir / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")


def write_quality(config_dir: Path, name: str, code: int, fieldnames: list[str],
                  positives: dict, positive_days: dict, built_at: str) -> None:
    quality = {
        "name": f"chicago-food-inspections-{name}",
        "task": {
            "question": f"Will this inspection cite violation code {code}?",
            "prediction_time": PREDICTION_TIME,
        },
        "target": name,
        "positive_label": POSITIVE_LABEL,
        "target_code": code,
        "time_column": "inspection_date",
        "event_key_column": "inspection_date",
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "carry_columns": CARRY_COLUMNS,
        "id_columns": list(ID_COLUMNS),
        "id_columns_are_entity_keys": True,
        "expected_duplicate_ids": 0,
        "high_cardinality_columns": list(HIGH_CARDINALITY),
        "high_cardinality_note": "license_ is the panel entity and spans split "
                                 "windows by design (prior history is the point "
                                 "of the task); inspection_date is the time "
                                 "column; latitude/longitude are quasi-identifiers "
                                 "with missing values, as published.",
        "label_source_columns": [LABEL_SOURCE],
        "post_hoc_columns": EXCLUDED_POST_HOC,
        "measurements": [
            {"column": "latitude", "unit": "decimal degrees",
             "frame": "WGS84 (EPSG:4326) as published by the City in dataset "
                      "4ijn-s7e5; empty when the City publishes no coordinates"},
            {"column": "longitude", "unit": "decimal degrees",
             "frame": "WGS84 (EPSG:4326) as published by the City in dataset "
                      "4ijn-s7e5; empty when the City publishes no coordinates"},
            {"column": "day_of_week", "unit": "weekday index, 0=Monday..6=Sunday",
             "frame": "computed from inspection_date; known at scheduling"},
            {"column": "month", "unit": "calendar month, 1-12",
             "frame": "computed from inspection_date; known at scheduling"},
            {"column": "prior_inspections", "unit": "count",
             "frame": "the licence's pool inspections with inspection_date "
                      "strictly earlier than this row's"},
            {"column": "days_since_previous", "unit": "days; -1 when the licence "
             "has no strictly-earlier pool inspection",
             "frame": "calendar days between the licence's inspection_date values"},
            {"column": "previous_result", "unit": "category",
             "frame": "results value of the licence's most recent strictly-earlier "
                      "pool inspection; empty when none exists"},
            {"column": "prior_fail_rate", "unit": "share in [0,1]; -1 when no prior",
             "frame": "share of the licence's strictly-earlier pool inspections "
                      "whose results value is Fail"},
            {"column": "prior_mean_code_count", "unit": "mean distinct violation "
             "codes; -1 when no prior",
             "frame": "mean over the licence's strictly-earlier pool inspections"},
            {"column": "prev_code_present", "unit": "1/0/-1",
             "frame": "1 if the target code was cited in the licence's most recent "
                      "strictly-earlier pool inspection, 0 if it was not, -1 when "
                      "no prior inspection exists"},
        ],
        "external_threshold": False,
        "split_windows": {key: dict(window)
                          for key, window in SPLIT_WINDOWS.items()},
        "positive_events": {
            key: {"positives": positives[key],
                  "distinct_events": len(positive_days[key])}
            for key in ("eval", "holdout")
        },
        "positive_events_note": "distinct_events counts calendar days carrying at "
                                "least one positive for this code, the gate's "
                                "conservative reading of clustering.",
        "splits": {"train": "public/train.csv", "eval": "public/eval.csv",
                   "holdout": "private/holdout.csv"},
        "grain": "one row per inspection_id; the pool is one row per inspection "
                 "with result in (Pass, Fail, Pass w/ Conditions) and a non-null "
                 "violations blob",
        "disclaimer": DISCLAIMER,
        "notes": "A multi-label suite: this config is one floor code. The other "
                 "codes' label columns are not shipped in this config's files - "
                 "they parse from the same post-visit violations blob as the "
                 "target, so as features they would be post-hoc cross-label "
                 "leakage. The joint label matrix is labels.csv at the extract "
                 "root. aka_name is not fetched (free-text facility alias, "
                 "restates the dba association carried by license_ and "
                 "facility_type; withheld as a publication decision).",
        "built_at_utc": built_at,
        "shipped_columns": fieldnames,
    }
    (config_dir / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the chicago-food-inspections per-code extracts")
    parser.add_argument("--out", default="/output",
                        help="output directory (default /output on a worker)")
    parser.add_argument("--page-size", type=int, default=5000)
    parser.add_argument("--min-rate", type=float, default=0.01,
                        help="floor rule: a code ships iff it appears in at "
                             "least this share of the pool (default 1%%)")
    parser.add_argument("--built-at", default=None,
                        help="pin built_at_utc (ISO 8601) so a rebuild is byte-identical")
    parser.add_argument("--limit", type=int, default=None,
                        help="cap total pool rows pulled; bounded exercise only")
    parser.add_argument("--codes", default=None,
                        help="explicit comma-separated code list, overriding the "
                             "floor rule (tests only)")
    args = parser.parse_args(argv)

    built_at = args.built_at or datetime.now(timezone.utc).isoformat()
    out = Path(args.out)
    prepare_output(out)

    print(f"dataset {DATASET}: pool rows {count(POOL_WHERE)}")
    select = ", ".join(["inspection_id", "license_", "inspection_date",
                        "inspection_type", "facility_type", "risk", "zip",
                        "latitude", "longitude", LABEL_SOURCE, OUTCOME_COLUMN])

    # Pass 1: stream the pool, parse the code set per row, keep a compact
    # projection. The blob is discarded immediately.
    rows: list[dict] = []
    prevalence: dict[int, int] = {}
    dropped = {"unparsable_blob": 0, "missing_license": 0, "missing_date": 0,
               "outside_windows": 0}
    tally = {"pages": 0}

    for row in stream_rows(POOL_WHERE, select, args.page_size, args.limit,
                           tally=tally):
        codes = parse_codes(row.get(LABEL_SOURCE) or "")
        if not codes:
            dropped["unparsable_blob"] += 1
            continue
        license_ = (row.get("license_") or "").strip()
        if not license_:
            dropped["missing_license"] += 1
            continue
        inspection_date = (row.get("inspection_date") or "")[:10]
        if not inspection_date:
            dropped["missing_date"] += 1
            continue
        if window_of(inspection_date) == "outside":
            dropped["outside_windows"] += 1
            continue
        rows.append({
            "inspection_id": row.get("inspection_id", ""),
            "license_": license_,
            "inspection_date": inspection_date,
            "inspection_type": row.get("inspection_type") or "",
            "facility_type": row.get("facility_type") or "",
            "risk": row.get("risk") or "",
            "zip": row.get("zip") or "",
            "latitude": row.get("latitude") or "",
            "longitude": row.get("longitude") or "",
            "result": row.get(OUTCOME_COLUMN) or "",
            "codes": codes,
        })
        for code in codes:
            prevalence[code] = prevalence.get(code, 0) + 1

    pool_rows = len(rows)
    print(f"pulled {pool_rows} pool rows in {tally['pages']} pages; "
          f"dropped {dropped}")

    # Pass 2: per-window code statistics, measured in memory before anything is
    # written, so the floor rule both selects and guarantees scoreability.
    stats = {code: {key: {"positives": 0, "days": set()}
                    for key in SPLIT_WINDOWS} for code in prevalence}
    window_rows = {key: 0 for key in SPLIT_WINDOWS}
    for record in rows:
        key = window_of(record["inspection_date"])
        window_rows[key] += 1
        for code in record["codes"]:
            stats[code][key]["positives"] += 1
            stats[code][key]["days"].add(record["inspection_date"])

    candidates = sorted(code for code, seen in prevalence.items()
                        if seen >= args.min_rate * pool_rows)
    dropped_by_windows: list[int] = []
    dropped_by_rate: list[int] = []
    if args.codes:
        requested = {int(code) for code in args.codes.split(",") if code.strip()}
        unknown = sorted(requested - set(prevalence))
        if unknown:
            raise SystemExit(f"--codes names codes absent from the pool: {unknown}")
        floor = sorted(requested)
        dropped_by_rate = sorted(set(prevalence) - requested)
    else:
        floor = []
        for code in candidates:
            window_ok = all(stats[code][key]["positives"] >= MIN_POSITIVES
                            and len(stats[code][key]["days"]) >= MIN_DISTINCT_DAYS
                            for key in ("eval", "holdout"))
            if window_ok:
                floor.append(code)
        dropped_by_windows = sorted(set(candidates) - set(floor))
    print(f"floor rule ({args.min_rate:.2%} of {pool_rows} pool rows, "
          f">= {MIN_POSITIVES} positives on >= {MIN_DISTINCT_DAYS} days in eval "
          f"and holdout): {len(floor)} codes")
    if not args.codes:
        print(f"  candidates {len(candidates)}; dropped by window minimums: "
              f"{dropped_by_windows}")
    if not floor:
        raise SystemExit("floor rule selected no codes; nothing to build")

    # Pass 3: licence-panel priors, strictly-earlier dates only.
    enriched = enrich_with_priors(rows)
    print(f"enriched {len(enriched)} rows with licence priors")

    # Pass 4: write one runner config per floor code, plus the joint label
    # matrix. All configs share the feature block; they differ in the target
    # column and in prev_code_present.
    config_name = {code: f"code_{code:02d}" for code in floor}
    fieldnames = (ID_COLUMNS + FEATURES)
    header_of = {code: fieldnames + [config_name[code]] for code in floor}
    writers: dict[int, dict[str, csv.writer]] = {}
    handles: dict[int, list] = {}
    written = {code: {key: {"rows": 0, "positives": 0} for key in LAYOUT}
               for code in floor}
    positive_days = {code: {key: set() for key in LAYOUT} for code in floor}

    for code in floor:
        config_dir = out / config_name[code]
        for key, relative in LAYOUT.items():
            path = config_dir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = path.open("w", newline="", encoding="utf-8")
            handles.setdefault(code, []).append(handle)
            writer = csv.writer(handle)
            writer.writerow(header_of[code])
            writers.setdefault(code, {})[key] = writer

    labels_path = out / "labels.csv"
    labels_handle = labels_path.open("w", newline="", encoding="utf-8")
    labels_writer = csv.writer(labels_handle)
    labels_writer.writerow(["inspection_id", "inspection_date", "license_"]
                           + [config_name[code] for code in floor])

    for entry in enriched:
        key = window_of(entry["inspection_date"])
        # The feature block is shared by every config; only prev_code_present
        # (its last FEATURES entry) and the target column differ per code.
        prefix = [str(entry[column]) for column in fieldnames[:-1]]
        has_prior = entry["has_prior"]
        prev_codes = entry["prev_codes"]
        label_row = [entry["inspection_id"], entry["inspection_date"],
                     entry["license_"]]
        for code in floor:
            name = config_name[code]
            prev_present = (int(code in prev_codes) if has_prior else -1)
            target = int(code in entry["codes"])
            writers[code][key].writerow(prefix + [str(prev_present), str(target)])
            written[code][key]["rows"] += 1
            written[code][key]["positives"] += target
            if target:
                positive_days[code][key].add(entry["inspection_date"])
            label_row.append(target)
        labels_writer.writerow(label_row)

    for code in floor:
        for handle in handles[code]:
            handle.close()
    labels_handle.close()
    del enriched, rows

    # The floor rule guaranteed these; assert so a construction bug cannot
    # write a config the gate would refuse.
    for code in floor:
        for key in ("eval", "holdout"):
            assert written[code][key]["positives"] >= MIN_POSITIVES, (code, key)
            assert len(positive_days[code][key]) >= MIN_DISTINCT_DAYS, (code, key)

    # Persistence baseline per config: can prev_code_present alone rank the
    # target on eval? This is the headroom evidence the release will quote.
    baselines = {}
    for code in floor:
        name = config_name[code]
        with (out / name / LAYOUT["eval"]).open(newline="", encoding="utf-8") as fh:
            eval_rows = list(csv.DictReader(fh))
        labels = [int(row[name]) for row in eval_rows]
        scores = [float(row["prev_code_present"]) for row in eval_rows]
        auc = auc_from_scores(labels, scores)
        baselines[code] = {
            "persistence_prev_code_present_eval_auc": round(auc, 6) if auc is not None else None,
            "eval_base_rate": round(sum(labels) / len(labels), 6) if labels else None,
        }

    manifest_configs = []
    total_bytes = 0
    for code in floor:
        name = config_name[code]
        config_dir = out / name
        rows_by_split = {key: written[code][key]["rows"] for key in LAYOUT}
        rate_by_split = {key: (round(written[code][key]["positives"]
                                     / written[code][key]["rows"], 6)
                               if written[code][key]["rows"] else None)
                         for key in LAYOUT}
        write_meta(config_dir, name, code, header_of[code],
                   rows_by_split, rate_by_split, built_at)
        write_quality(config_dir, name, code, header_of[code],
                      {key: written[code][key]["positives"] for key in LAYOUT},
                      {key: positive_days[code][key] for key in LAYOUT},
                      built_at)
        entry = {
            "name": name,
            "target": name,
            "code": code,
            "rows": rows_by_split,
            "positive_rate": rate_by_split,
            "positives": {key: written[code][key]["positives"] for key in LAYOUT},
            "persistence_baseline": baselines[code],
            "files": {},
        }
        for key, relative in LAYOUT.items():
            path = config_dir / relative
            entry["files"][key] = {"file": str(relative), "sha256": sha256_of(path),
                                   "bytes": path.stat().st_size}
            total_bytes += path.stat().st_size
        for small in ("meta.json", "quality.json"):
            path = config_dir / small
            entry["files"][small] = {"file": small, "sha256": sha256_of(path),
                                     "bytes": path.stat().st_size}
        manifest_configs.append(entry)
        print(f"  {name}: rows {rows_by_split} rates {rate_by_split} "
              f"persistence {baselines[code]['persistence_prev_code_present_eval_auc']}")

    manifest = {
        "candidate": "chicago-food-inspections",
        "dataset": DATASET,
        "endpoint": f"{BASE}/resource/{DATASET}.json",
        "built_at_utc": built_at,
        "prediction_time": PREDICTION_TIME,
        "formulation": "one binary runner config per floor violation code; the "
                       "joint multi-label matrix is labels.csv",
        "pool_where": POOL_WHERE,
        "pool_rows": pool_rows,
        "dropped_rows": dropped,
        "pages": tally["pages"],
        "floor_rule": {"min_pool_rate": args.min_rate,
                       "min_positives_per_window": MIN_POSITIVES,
                       "min_distinct_days_per_window": MIN_DISTINCT_DAYS},
        "floor_codes": floor,
        "floor_candidates_above_rate": candidates,
        "floor_dropped_by_window_minimums": dropped_by_windows,
        "codes_dropped_by_rate_or_override": dropped_by_rate,
        "code_prevalence": {str(code): prevalence.get(code, 0) for code in floor},
        "features": FEATURES,
        "id_columns": ID_COLUMNS,
        "label_source_column": LABEL_SOURCE,
        "excluded_post_hoc": EXCLUDED_POST_HOC,
        "not_fetched": {"aka_name": "free-text facility alias; withheld as a "
                                    "publication decision"},
        "split_windows": SPLIT_WINDOWS,
        "configs": manifest_configs,
        "labels_csv": {"file": "labels.csv", "sha256": sha256_of(labels_path),
                       "bytes": labels_path.stat().st_size},
        "shipped_columns_per_config": fieldnames + ["code_<NN>"],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")

    build_summary = {
        "candidate": "chicago-food-inspections",
        "status": "extract-built",
        "built_at_utc": built_at,
        "pool_rows": pool_rows,
        "dropped_rows": dropped,
        "floor_codes": floor,
        "configs": {config_name[code]: {
            "rows": {key: written[code][key]["rows"] for key in LAYOUT},
            "positives": {key: written[code][key]["positives"] for key in LAYOUT},
            "positive_days": {key: len(positive_days[code][key]) for key in LAYOUT},
            "persistence_baseline": baselines[code],
        } for code in floor},
        "total_split_bytes": total_bytes,
        "labels_csv_bytes": labels_path.stat().st_size,
        "note": "Measured extract with checksums, in the runner's "
                "public/private layout per floor code. Not a scored result.",
    }
    (out / "build_summary.json").write_text(json.dumps(build_summary, indent=1) + "\n")
    (out / "summary.json").write_text(json.dumps(
        {"candidate": "chicago-food-inspections", "status": "extract-built",
         "built_at_utc": built_at, "pool_rows": pool_rows,
         "floor_codes": floor,
         "configs": [config_name[code] for code in floor]},
        indent=1) + "\n")

    print(f"\nwrote {len(floor)} configs under {out}, plus labels.csv, "
          f"manifest.json, build_summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
