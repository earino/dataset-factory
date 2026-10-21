#!/usr/bin/env python3
"""Construction script for the `msha-enforcement-citations` candidate.

Task: at the moment an MSHA inspection opens (`INSPECTION_BEGIN_DT`), which
parts of 30 CFR will it cite? The answer is a SET, so this is a genuine
multi-label task. It is realized as one binary runner config per floor section,
because the existing runner scores one binary target per task (`task.json` reads
one `target`; the benchmark score is holdout AUC). That per-level pattern is the
one `chicago-food-inspections` and `noaa-tide-flooding` shipped.

Runner-contract decision (recorded in the candidate record before this build):
ship `sec_<slug>/` per floor section - a complete `public/train.csv`,
`public/eval.csv`, `private/holdout.csv`, `meta.json`, `quality.json` - with
target column `sec_<slug>` = 1 iff that 30 CFR section was cited at the
inspection. The OTHER sections' label columns are NOT shipped inside a config:
they come from the same post-visit citation list as the target, so as features
they would be post-hoc cross-label leakage. `labels.csv` at the extract root
carries the joint multi-label matrix (one row per inspection, one column per
floor section) so the set formulation is consumable without re-pulling the
source.

Where this runs
---------------
**On a temporary worker, not on the coordinator.** The three published files are
Violations.zip (120,838,828 bytes), Inspections.zip (73,667,437 bytes) and
Mines.zip (7,308,890 bytes); `Violations.txt` unpacks to ~1.44 GB and holds
3.1 M citation rows. Nothing is extracted to disk: the zip members are streamed.
Use `--limit-events` for a bounded local exercise that proves the script works.

Leakage discipline, from the candidate notes
--------------------------------------------
Prediction instant: the start of the inspection, before any observation.
Shipped features are the mine's structural attributes (Mines table), the
inspection's own recorded activity/program area, the calendar position of the
begin date, and counts from the SAME mine's strictly-earlier inspections.
Everything the inspector learns - the citations themselves, their
gravity/negligence/likelihood assessments, penalties, docket and contest state,
end-of-visit hour and sample counts, and every date after the begin date - is
fetched only to derive labels and priors, then excluded from every shipped file.

Two documented caveats about the feature surface:
  * The Mines table is a CURRENT snapshot, not an as-of-inspection one. Fields
    that move with status or ownership (CURRENT_MINE_STATUS, CURRENT_103I,
    CURRENT_*_DT, ASSESS_CTRL_NO, controller/operator id and name) are NOT
    shipped, and neither is NO_EMPLOYEES. What ships (coal/metal indicator, mine
    type, state, county, canvass, company type, operating schedule,
    portability) is structural and is declared as a current-snapshot join in
    quality.json.
  * Inspections that cite nothing are outside this pool: the pool is the set of
    events that carry at least one violation row, exactly as probed in the
    candidate record. An inspection citing nothing is a real and common outcome,
    so this suite is a conditioned view of the task - recorded, not hidden.

Floor rule (stated in advance, measured at construction): a section ships as a
config iff it is cited in >= `--min-rate` (default 1%) of the modelling pool AND
carries >= 30 positives on >= 20 distinct positive days in BOTH the eval and
holdout windows - the qualification gate's own minimums, so every config that is
written is one the gate can score. Survivors are then capped at `--max-configs`
(default 60, most prevalent first) so the suite stays shippable; sections above
the rate floor that the cap or the window minimums drop are named in the
manifest and still appear in labels.csv, not silently lost.

The output directory is checked by `skills/dataset-qualification/`, which is the
project's gate before a candidate goes to the benchmark. Licence: MSHA publishes
no terms; the operator decided 2026-10-12 (option A) to treat this US federal
work as public domain for publication with attribution preserved - see
candidates/msha-enforcement-citations/license.json.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import re
import shutil
import sys
import time
import urllib.request
import zipfile
from datetime import date as date_cls
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://arlweb.msha.gov/OpenGovernmentData/DataSets"
SOURCES = {"violations": "Violations.zip",
           "inspections": "Inspections.zip",
           "mines": "Mines.zip"}
USER_AGENT = {"User-Agent": "scout-dataset-factory/0.1 (construction)"}

# Every field written to a shipped file, in shipped order: the first 17 are the
# base block (mine attributes, the inspection's own recorded fields, and the
# calendar position of the begin date), the next five are priors from the mine's
# strictly-earlier inspections, and the last is the per-config persistence
# feature. A change here changes the artifact.
FEATURES = [
    "mine_id",
    "inspection_date",
    "coal_metal_ind",
    "mine_type",
    "state",
    "fips_cnty_cd",
    "primary_canvass",
    "company_type",
    "days_per_week",
    "hours_per_shift",
    "prod_shifts_per_day",
    "portable_operation",
    "activity_code",
    "program_area",
    "inspect_office_cd",
    "month",
    "day_of_week",
    "prior_inspections",
    "days_since_previous",
    "prior_citation_count",
    "prior_mean_citations",
    "prior_distinct_sections",
    "prev_target_cited",
]
BASE_BLOCK = 17          # FEATURES[:BASE_BLOCK] travel with every row
PRIOR_BLOCK = 5          # prior_inspections .. prior_distinct_sections

ID_COLUMNS = ["event_no"]

# mine_id is the panel entity and spans split windows BY DESIGN because prior
# history is the point of the task, so it is a feature, not an id column;
# inspection_date is the time column. Declared for the gate's awareness.
HIGH_CARDINALITY = ["mine_id", "inspection_date"]

CARRY_COLUMNS: list[str] = []

# Fetched to derive labels and priors, never written to a shipped file. The
# citation-side entries are the post-visit record; the inspection-side entries
# are recorded as the visit runs; the Mines-side entries move with the mine's
# status, ownership or fortune.
LABEL_SOURCE = "PART_SECTION"
EXCLUDED_POST_HOC = [
    "PART_SECTION", "SECTION_OF_ACT", "SECTION_OF_ACT_1", "SECTION_OF_ACT_2",
    "VIOLATION_NO", "SIG_SUB", "NEGLIGENCE", "LIKELIHOOD", "INJ_ILLNESS",
    "NO_AFFECTED", "ENFORCEMENT_AREA", "SPECIAL_ASSESS", "CIT_ORD_SAFE",
    "VIOLATION_ISSUE_DT", "VIOLATION_ISSUE_TIME", "ORIG_TERM_DUE_DT",
    "LATEST_TERM_DUE_DT", "TERMINATION_DT", "VACATE_DT",
    "FINAL_ORDER_ISSUE_DT", "PROPOSED_PENALTY", "AMOUNT_DUE", "AMOUNT_PAID",
    "INSPECTION_END_DT", "TOTAL_ON_SITE_HOURS", "TOTAL_INSP_HOURS",
    "NBR_INSPECTORS", "ACTIVE_SECTIONS", "IDLE_SECTIONS", "SHAFT_SLOPE_SINK",
    "IMPOUND_CONSTR", "BLDG_CONSTR_SITES", "DRAGLINES", "UNCLASSIFIED_CONSTR",
    "SAMPLE_CNT_AIR", "SAMPLE_CNT_DUSTSPOT", "SAMPLE_CNT_DUSTSURVEY",
    "SAMPLE_CNT_RESPDUST", "SAMPLE_CNT_NOISE", "SAMPLE_CNT_OTHER",
    "CO_RECORDS", "SURF_UG_MINE", "SURF_FACILITY_MINE", "REFUSE_PILES",
    "EXPLOSIVE_STORAGE", "OUTBY_AREAS", "MAJOR_CONSTR", "SHAFTS_SLOPES",
    "IMPOUNDMENTS", "MISC_AREA", "CURRENT_MINE_STATUS", "CURRENT_STATUS_DT",
    "CURRENT_103I", "CURRENT_103I_DT", "ASSESS_CTRL_NO",
    "CURRENT_CONTROLLER_ID", "CURRENT_CONTROLLER_NAME", "CURRENT_OPERATOR_ID",
    "CURRENT_OPERATOR_NAME", "NO_EMPLOYEES",
]

# Temporal, no random component. 2000 (the earliest year) is dropped with 2026
# (partial) so the windows match the recorded probe exactly.
SPLIT_WINDOWS = {
    "train": {"start": "2001-01-01", "end": "2021-01-01"},
    "eval": {"start": "2021-01-01", "end": "2024-01-01"},
    "holdout": {"start": "2024-01-01", "end": "2026-01-01"},
}

LAYOUT = {"train": Path("public") / "train.csv",
          "eval": Path("public") / "eval.csv",
          "holdout": Path("private") / "holdout.csv"}

POSITIVE_LABEL = 1
MIN_POSITIVES = 30
MIN_DISTINCT_DAYS = 20

PREDICTION_TIME = (
    "The start of the inspection, before any observation: inspection_date is "
    "the published INSPECTION_BEGIN_DT, and every feature is a structural mine "
    "attribute, the inspection's own recorded activity and program area, the "
    "calendar position of the begin date, or a count from an earlier inspection "
    "of the same mine.")

LICENSE_NOTE = ("US federal government work. MSHA publishes no terms; the "
                "operator decided on 2026-10-12 (option A) to treat it as "
                "public domain for publication with attribution preserved. See "
                "LICENSE.md and candidates/msha-enforcement-citations/"
                "license.json.")

ATTRIBUTION = ("Source: U.S. Department of Labor, Mine Safety and Health "
               "Administration (MSHA) Open Government Data Sets "
               "(arlweb.msha.gov/OpenGovernmentData). This dataset is a derived "
               "work: features, labels and splits are ours.")

OWNED_MARKER = ".dataset-factory-extract"
FORBIDDEN_OUT = ("/", "/etc", "/usr", "/var", "/opt/data", "/root", "/home")


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
        "Generated by candidates/msha-enforcement-citations/source/build.py. "
        "Safe to clear.\n")


def download(name: str, work_dir: Path, attempts: int = 4) -> Path:
    """Fetch one published zip, or reuse a complete cached copy."""
    filename = SOURCES[name]
    target = work_dir / filename
    if target.is_file() and target.stat().st_size > 0:
        print(f"  {filename}: cached, {target.stat().st_size} bytes")
        return target
    url = f"{BASE}/{filename}"
    last = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers=USER_AGENT)
            with urllib.request.urlopen(request, timeout=600) as response:
                expected = response.headers.get("Content-Length")
                with target.open("wb") as handle:
                    shutil.copyfileobj(response, handle, 1 << 20)
            size = target.stat().st_size
            if expected is not None and size != int(expected):
                raise RuntimeError(f"short read: {size} of {expected} bytes")
            print(f"  {filename}: {size} bytes")
            return target
        except Exception as exc:  # noqa: BLE001
            last = repr(exc)
            target.unlink(missing_ok=True)
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"download failed for {url} after {attempts} attempts: {last}")


def zip_member(zip_path: Path) -> str:
    """The single data member of a published zip (the .txt)."""
    with zipfile.ZipFile(zip_path) as archive:
        names = [info.filename for info in archive.infolist()
                 if info.filename.lower().endswith(".txt")]
    if not names:
        raise RuntimeError(f"{zip_path.name} holds no .txt member")
    if len(names) > 1:
        preferred = [name for name in names
                     if Path(name).stem.lower() == zip_path.stem.lower()]
        names = preferred or names
        if len(names) > 1:
            raise RuntimeError(f"{zip_path.name} holds several .txt members: {names}")
    return names[0]


def iter_rows(zip_path: Path, tally: dict):
    """Yield pipe-delimited rows from a published zip, as dicts, streamed.

    Nothing is extracted to disk: the member is read through the archive and
    decoded as cp1252, the encoding MSHA publishes. A row whose field count does
    not match the header is counted in `tally` and skipped, never guessed at.
    """
    member = zip_member(zip_path)
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open(member) as raw:
            text = io.TextIOWrapper(raw, encoding="cp1252", errors="replace",
                                    newline="")
            reader = csv.reader(text, delimiter="|", quotechar='"')
            header = [column.strip().upper() for column in next(reader)]
            for values in reader:
                if not values or all(value == "" for value in values):
                    continue
                if len(values) != len(header):
                    tally["malformed"] = tally.get("malformed", 0) + 1
                    continue
                yield dict(zip(header, values))


def parse_mmddyyyy(raw: str | None) -> str | None:
    """`mm/dd/yyyy` as published, to ISO. Anything else is missing."""
    text = (raw or "").strip()
    if not text:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def normalise_section(raw: str | None) -> str | None:
    """One cited 30 CFR section, normalised for identity.

    Whitespace is collapsed and the string is upper-cased: the publisher writes
    the same section in more than one rendering, and the label space is the
    section, not the rendering of it.
    """
    text = re.sub(r"\s+", "", (raw or "")).upper()
    return text or None


SECTION_RE = re.compile(r"[^0-9A-Za-z]+")


def config_name(section: str) -> str:
    return "sec_" + SECTION_RE.sub("_", section).strip("_")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def auc_from_scores(labels: list[int], scores: list[float]) -> float | None:
    """Rank-based ROC AUC, ties averaged. Pure stdlib."""
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


def days_between(earlier: str, later: str) -> int:
    return (date_cls.fromisoformat(later) - date_cls.fromisoformat(earlier)).days


def enrich_with_priors(rows: list) -> list:
    """Walk each mine's inspection history in (mine, date) order, attaching
    priors that use only STRICTLY-earlier dates of the same mine.

    Rows of the same mine and date form one group: they all see the same prior
    state, and the group's own inspections update the state only after every row
    of the group is enriched - so a same-day follow-up can never serve as its own
    history. In-tuple layout: 17 base values, then the citation set, then the
    event number (the sort's total tiebreaker).

    Two different accumulators, deliberately:

    * ``citations`` / ``distinct`` accumulate over EVERY strictly-earlier
      inspection of the mine - they are counts of the mine's history, which is
      what ``prior_citation_count``, ``prior_mean_citations`` and
      ``prior_distinct_sections`` document;
    * ``last_sections`` is the snapshot of the most recent strictly-earlier
      group only, which is what ``prev_target_cited`` documents ("1 if the
      target section was cited on the mine's most recent strictly-earlier
      pooled inspection"). Collapsing that into the cumulative set instead
      would make the feature read "ever cited in this mine's history" and
      disagree with the shipped quality.json.
    """
    rows.sort(key=lambda row: (row[0], row[1], row[18]))
    enriched: list = []
    current_mine = None
    count = 0
    prev_date: str | None = None
    citations = 0
    distinct: set = set()
    last_sections: frozenset = frozenset()
    index = 0
    while index < len(rows):
        mine_id = rows[index][0]
        if mine_id != current_mine:
            current_mine, count, prev_date = mine_id, 0, None
            citations, distinct, last_sections = 0, set(), frozenset()
        current_date = rows[index][1]
        end = index
        while (end < len(rows) and rows[end][0] == mine_id
               and rows[end][1] == current_date):
            end += 1
        group = rows[index:end]
        has_prior = bool(count)
        delta = days_between(prev_date, current_date) if (has_prior and prev_date) else -1
        for record in group:
            enriched.append(record + (
                count,
                delta,
                citations if has_prior else -1,
                round(citations / count, 4) if has_prior else -1,
                len(distinct) if has_prior else -1,
                has_prior,
                last_sections,
            ))
        group_sections: set = set()
        for record in group:
            count += 1
            prev_date = current_date
            citations += len(record[17])
            distinct.update(record[17])
            group_sections.update(record[17])
        last_sections = frozenset(group_sections)
        index = end
    return enriched


def write_meta(config_dir: Path, name: str, section: str, fieldnames: list[str],
               rows: dict, positive_rate: dict, built_at: str) -> None:
    meta = {
        "name": f"msha-enforcement-citations-{name}",
        "description": (f"Will this MSHA inspection cite 30 CFR {section}? "
                        "Predicted at the moment the inspection begins, from "
                        "structural mine attributes, the inspection's own "
                        "recorded activity and program area, the calendar "
                        "position of the begin date, and the mine's own "
                        "strictly-earlier inspection history."),
        "source": (f"{BASE}/Violations.zip, {BASE}/Inspections.zip, "
                   f"{BASE}/Mines.zip (MSHA Open Government Data Sets)"),
        "license": "US federal government work, published as public domain "
                   "(operator decision 2026-10-12, option A); see LICENSE.md",
        "attribution": ATTRIBUTION,
        "target": name,
        "positive_label": POSITIVE_LABEL,
        "id_columns": list(ID_COLUMNS),
        "columns": fieldnames,
        "rows": rows,
        "positive_rate": positive_rate,
        "split": {"strategy": "temporal by inspection begin date, no random "
                              "component",
                  "windows": SPLIT_WINDOWS},
        "label_rule": (f"{name} = 1 if 30 CFR {section} appears among the "
                       "sections cited at this inspection (PART_SECTION on its "
                       "violation rows), else 0"),
        "label_source_column": LABEL_SOURCE,
        "prediction_time": PREDICTION_TIME,
        "features": FEATURES,
        "excluded_post_hoc": EXCLUDED_POST_HOC,
        "carry_columns": CARRY_COLUMNS,
        "built_at_utc": built_at,
    }
    (config_dir / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")


def write_quality(config_dir: Path, name: str, section: str,
                  fieldnames: list[str], positives: dict, positive_days: dict,
                  pool_rate: float, built_at: str) -> None:
    quality = {
        "name": f"msha-enforcement-citations-{name}",
        "task": {"question": f"Will this inspection cite 30 CFR {section}?",
                 "prediction_time": PREDICTION_TIME},
        "target": name,
        "positive_label": POSITIVE_LABEL,
        "target_section": section,
        "time_column": "inspection_date",
        "event_key_column": "inspection_date",
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "timing": {
            "prediction_instant": {
                "kind": "event_time",
                "period": "event_date",
                "days_after_period_end": 0,
                "citation": "each row is predicted at its own event date from records already "
                            "present in the source system",
            },
            "features": {"period": "event_date", "published_days_after_period_end": 0,
                         "source_kind": "administrative_record"},
            "row_selection": {"latest_period_used": "event_date",
                              "fields": sorted(set(FEATURES) | set(CARRY_COLUMNS)),
                              "basis": "eligibility uses only records dated at or before the event"},
            "observations": [],
        },
        "carry_columns": CARRY_COLUMNS,
        "id_columns": list(ID_COLUMNS),
        "id_columns_are_entity_keys": True,
        "expected_duplicate_ids": 0,
        "high_cardinality_columns": list(HIGH_CARDINALITY),
        "high_cardinality_note": "mine_id is the panel entity and spans split "
                                 "windows by design (prior history is the point "
                                 "of the task); inspection_date is the time "
                                 "column. Both are declared, neither is an id "
                                 "column.",
        "label_source_columns": [LABEL_SOURCE],
        "post_hoc_columns": EXCLUDED_POST_HOC,
        "measurements": [
            {"column": "inspection_date", "unit": "ISO 8601 date",
             "frame": "the published INSPECTION_BEGIN_DT (mm/dd/yyyy in the "
                      "source): the moment the inspection opens"},
            {"column": "month", "unit": "calendar month, 1-12",
             "frame": "computed from inspection_date; known when the inspection "
                      "opens"},
            {"column": "day_of_week", "unit": "weekday index, 0=Monday..6=Sunday",
             "frame": "computed from inspection_date; known when the inspection "
                      "opens"},
            {"column": "days_per_week", "unit": "days per week",
             "frame": "Mines table, mine information form; a CURRENT snapshot of "
                      "the mine, not an as-of-inspection one"},
            {"column": "hours_per_shift", "unit": "hours",
             "frame": "Mines table, current snapshot, as above"},
            {"column": "prod_shifts_per_day", "unit": "shifts per day",
             "frame": "Mines table, current snapshot, as above"},
            {"column": "prior_inspections", "unit": "count",
             "frame": "the mine's pooled inspections with a begin date strictly "
                      "earlier than this row's"},
            {"column": "days_since_previous", "unit": "days; -1 when the mine "
             "has no strictly-earlier pooled inspection",
             "frame": "calendar days between the mine's begin dates"},
            {"column": "prior_citation_count", "unit": "count; -1 when no prior",
             "frame": "count of violations cited on the mine's strictly-earlier "
                      "pooled inspections"},
            {"column": "prior_mean_citations", "unit": "mean; -1 when no prior",
             "frame": "mean violations per strictly-earlier pooled inspection of "
                      "the same mine"},
            {"column": "prior_distinct_sections", "unit": "count; -1 when no prior",
             "frame": "distinct 30 CFR sections cited across the mine's "
                      "strictly-earlier pooled inspections"},
            {"column": "prev_target_cited", "unit": "1/0/-1",
             "frame": "1 if the target section was cited on the mine's most "
                      "recent strictly-earlier pooled inspection, 0 if not, -1 "
                      "when no prior inspection exists"},
        ],
        "external_threshold": False,
        "split_windows": {key: dict(window) for key, window in SPLIT_WINDOWS.items()},
        "pool_citation_rate": round(pool_rate, 6),
        "positive_events": {
            key: {"positives": positives[key],
                  "distinct_events": len(positive_days[key])}
            for key in ("eval", "holdout")},
        "positive_events_note": "distinct_events counts calendar days carrying "
                                "at least one positive for this section, the "
                                "gate's conservative reading of clustering.",
        "splits": {"train": "public/train.csv", "eval": "public/eval.csv",
                   "holdout": "private/holdout.csv"},
        "grain": "one row per event_no (one inspection); the pool is the set of "
                 "events carrying at least one violation row with a parseable "
                 "INSPECTION_BEGIN_DT inside a split window",
        "attribution": ATTRIBUTION,
        "license": LICENSE_NOTE,
        "notes": "A multi-label suite: this config is one 30 CFR section. The "
                 "other sections' label columns are not shipped in this config's "
                 "files - they come from the same post-visit citation list as the "
                 "target, so as features they would be post-hoc cross-label "
                 "leakage. The joint label matrix is labels.csv at the extract "
                 "root. Inspections citing nothing are outside the pool (the task "
                 "is conditioned on at least one citation, as probed); the Mines "
                 "table is a current snapshot and its status, ownership and "
                 "employment fields are not shipped.",
        "built_at_utc": built_at,
        "shipped_columns": fieldnames,
    }
    (config_dir / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the msha-enforcement-citations per-section extracts")
    parser.add_argument("--out", default="/output",
                        help="output directory (default /output on a worker)")
    parser.add_argument("--work-dir", default="/tmp/msha",
                        help="where the published zips are cached")
    parser.add_argument("--min-rate", type=float, default=0.01,
                        help="floor rule: a section ships iff it is cited in at "
                             "least this share of the pool (default 1%%)")
    parser.add_argument("--max-configs", type=int, default=60,
                        help="cap on shipped configs, most prevalent first "
                             "(default 60; labels.csv keeps every floor section)")
    parser.add_argument("--sections", default=None,
                        help="explicit comma-separated section list, overriding "
                             "the floor rule (bounded exercise only)")
    parser.add_argument("--limit-events", type=int, default=None,
                        help="deterministically sample at most this many pooled "
                             "events, applied after the citation pass; bounded "
                             "exercise only")
    parser.add_argument("--seed", type=int, default=20261012,
                        help="sampling seed for --limit-events")
    parser.add_argument("--no-window-assert", action="store_true",
                        help="skip the floor rule's window minimums (bounded "
                             "exercise only)")
    parser.add_argument("--built-at", default=None,
                        help="pin built_at_utc (ISO 8601) so a rebuild is "
                             "byte-identical")
    args = parser.parse_args(argv)

    built_at = args.built_at or datetime.now(timezone.utc).isoformat()
    out = Path(args.out)
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    prepare_output(out)

    tally = {"malformed": 0}
    print("== download ==")
    zips = {name: download(name, work_dir) for name in SOURCES}
    zip_bytes = {name: path.stat().st_size for name, path in zips.items()}

    print("== mines ==")
    mines: dict[str, tuple] = {}
    for row in iter_rows(zips["mines"], tally):
        mine_id = (row.get("MINE_ID") or "").strip()
        if not mine_id:
            continue
        mines[mine_id] = tuple(sys.intern((row.get(key) or "").strip()) for key in (
            "COAL_METAL_IND", "CURRENT_MINE_TYPE", "STATE", "FIPS_CNTY_CD",
            "PRIMARY_CANVASS", "COMPANY_TYPE", "DAYS_PER_WEEK",
            "HOURS_PER_SHIFT", "PROD_SHIFTS_PER_DAY", "PORTABLE_OPERATION"))
    print(f"  mines {len(mines)}")

    print("== inspections ==")
    inspections: dict[str, tuple] = {}
    duplicate_events = 0
    for row in iter_rows(zips["inspections"], tally):
        event_no = (row.get("EVENT_NO") or "").strip()
        if not event_no:
            continue
        begin = parse_mmddyyyy(row.get("INSPECTION_BEGIN_DT"))
        if event_no in inspections:
            duplicate_events += 1
            if inspections[event_no][0] is not None:
                continue
        inspections[event_no] = (
            begin,
            sys.intern((row.get("ACTIVITY_CODE") or "").strip()),
            sys.intern((row.get("PROGRAM_AREA") or "").strip()),
            sys.intern((row.get("INSPECT_OFFICE_CD") or "").strip()),
            sys.intern((row.get("MINE_ID") or "").strip()))
    print(f"  inspections {len(inspections)} (duplicate EVENT_NO rows "
          f"{duplicate_events})")

    print("== violations ==")
    citations: dict[str, set] = {}
    event_mine: dict[str, str] = {}
    citation_rows = 0
    empty_sections = 0
    distinct_sections: set[str] = set()
    for row in iter_rows(zips["violations"], tally):
        event_no = (row.get("EVENT_NO") or "").strip()
        if not event_no:
            continue
        citation_rows += 1
        if not event_mine.get(event_no):
            mine = (row.get("MINE_ID") or "").strip()
            if mine:
                event_mine[event_no] = sys.intern(mine)
        section = normalise_section(row.get(LABEL_SOURCE))
        if section is None:
            empty_sections += 1
            continue
        section = sys.intern(section)
        distinct_sections.add(section)
        citations.setdefault(event_no, set()).add(section)
    print(f"  {citation_rows} citation rows, {len(citations)} events, "
          f"{len(distinct_sections)} distinct sections, {empty_sections} empty "
          f"PART_SECTION")

    # ------------------------------------------------------------- the pool
    # One row per event that carries at least one violation row, joined to its
    # inspection row (begin date, activity, program area, office) and its mine.
    print("== pool ==")
    rows: list = []
    dropped_no_inspection = dropped_no_begin = dropped_outside = dropped_no_mine = 0
    for event_no, sections in citations.items():
        inspection = inspections.get(event_no)
        if inspection is None:
            dropped_no_inspection += 1
            continue
        begin = inspection[0]
        if begin is None:
            dropped_no_begin += 1
            continue
        if window_of(begin) == "outside":
            dropped_outside += 1
            continue
        mine_id = inspection[4] or event_mine.get(event_no, "")
        if not mine_id:
            dropped_no_mine += 1
            continue
        year, month, day = (int(part) for part in begin.split("-"))
        rows.append((mine_id, begin) + mines.get(mine_id, ("",) * 10)
                    + (inspection[1], inspection[2], inspection[3],
                       month, date_cls(year, month, day).weekday())
                    + (frozenset(sections), event_no, window_of(begin)))
        if len(rows) % 100000 == 0:
            print(f"  pooled {len(rows)} events")
    print(f"  pool {len(rows)} events (no inspection row {dropped_no_inspection}, "
          f"no begin date {dropped_no_begin}, no mine id {dropped_no_mine}, "
          f"outside windows {dropped_outside})")

    sampled = None
    if args.limit_events is not None and args.limit_events < len(rows):
        sampler = random.Random(args.seed)
        rows = [rows[index] for index in sorted(
            sampler.sample(range(len(rows)), args.limit_events))]
        sampled = args.limit_events
        print(f"  bounded exercise: sampled {len(rows)} events (seed {args.seed})")

    # ------------------------------------------------------- the floor rule
    # The pool is an events table; the pool composition of a row is the citation
    # set it carries. Rates come from the event rows, not from the event ids, so
    # a sampled pool measures honestly.
    pool_rows = len(rows)
    section_hits: dict[str, int] = {}
    for record in rows:
        for section in record[17]:
            section_hits[section] = section_hits.get(section, 0) + 1
    prevalence = {section: hits / pool_rows for section, hits in section_hits.items()}
    candidates = sorted((section for section, rate in prevalence.items()
                         if rate >= args.min_rate),
                        key=lambda section: (-prevalence[section], section))
    print(f"  {len(candidates)} sections cited in >= {args.min_rate:.2%} of "
          f"{pool_rows} pooled events")

    window_stats = {section: {key: {"positives": 0, "days": set()}
                              for key in ("eval", "holdout")}
                    for section in candidates}
    for record in rows:
        window = record[19]
        if window not in ("eval", "holdout"):
            continue
        codes = record[17]
        for section in codes:
            if section in window_stats:
                window_stats[section][window]["positives"] += 1
                window_stats[section][window]["days"].add(record[1])
    survivors, dropped_by_windows = [], []
    for section in candidates:
        if all(window_stats[section][key]["positives"] >= MIN_POSITIVES
               and len(window_stats[section][key]["days"]) >= MIN_DISTINCT_DAYS
               for key in ("eval", "holdout")):
            survivors.append(section)
        else:
            dropped_by_windows.append(section)
    print(f"  {len(survivors)} survive the window minimums "
          f"({len(dropped_by_windows)} dropped by them)")

    by_name = {config_name(section): section for section in survivors
               + [section for section in candidates if section not in survivors]}
    if len(by_name) != len(set(by_name)):
        raise SystemExit("config name collision after slug normalisation")
    if args.sections:
        wanted = [part.strip().upper() for part in args.sections.split(",")
                  if part.strip()]
        missing = [section for section in wanted if section not in section_hits]
        if missing:
            raise SystemExit(f"--sections names sections absent from the pool: {missing}")
        shipped = wanted
        dropped_by_cap = [section for section in survivors if section not in wanted]
    else:
        shipped = survivors[:args.max_configs]
        dropped_by_cap = survivors[args.max_configs:]
    if not shipped:
        raise SystemExit("the floor rule selected no section; nothing to write")
    print(f"  shipping {len(shipped)} configs; {len(dropped_by_cap)} above-floor "
          f"sections held back by the cap")

    # ------------------------------------------------------------ the writes
    enriched = enrich_with_priors(rows)
    del rows

    fieldnames = ID_COLUMNS + FEATURES
    headers = {section: fieldnames + [config_name(section)] for section in shipped}
    writers: dict[str, dict[str, csv.writer]] = {}
    handles: list = []
    written = {section: {key: {"rows": 0, "positives": 0} for key in LAYOUT}
               for section in shipped}
    positive_days = {section: {key: set() for key in LAYOUT} for section in shipped}
    for section in shipped:
        config_dir = out / config_name(section)
        for key, relative in LAYOUT.items():
            path = config_dir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = path.open("w", newline="", encoding="utf-8")
            handles.append(handle)
            writer = csv.writer(handle)
            writer.writerow(headers[section])
            writers.setdefault(section, {})[key] = writer

    # Every floor section gets a column in the joint matrix, including the ones
    # the cap held back, so the multi-label target is complete.
    all_floor = sorted(survivors, key=lambda section: (-prevalence[section], section))
    labels_path = out / "labels.csv"
    labels_handle = labels_path.open("w", newline="", encoding="utf-8")
    labels_writer = csv.writer(labels_handle)
    labels_writer.writerow(["event_no", "inspection_date", "mine_id"]
                           + [config_name(section) for section in all_floor])
    floor_index = {section: position for position, section in enumerate(all_floor)}

    for record in enriched:
        # Base row tuple: 0 mine_id, 1 begin date, 2..11 mine attributes,
        # 12..14 the inspection's own fields, 15 month, 16 day_of_week,
        # 17 citation set, 18 event_no, 19 window; the prior block appended by
        # enrich_with_priors is 20..24 and then 25 has_prior, 26 prev_codes.
        window = record[19]
        base = [record[18]] + [str(value) for value in record[:BASE_BLOCK]]
        prior = [str(record[20 + offset]) for offset in range(PRIOR_BLOCK)]
        codes = record[17]
        prev_codes = record[26]
        has_prior = record[25]
        label_row = [0] * len(all_floor)
        for section in codes:
            if section in floor_index:
                label_row[floor_index[section]] = 1
        for section in shipped:
            target = 1 if section in codes else 0
            prev_present = int(section in prev_codes) if has_prior else -1
            writers[section][window].writerow(
                base + prior + [str(prev_present), str(target)])
            written[section][window]["rows"] += 1
            written[section][window]["positives"] += target
            if target:
                positive_days[section][window].add(record[1])
        labels_writer.writerow([record[18], record[1], record[0]] + label_row)

    for handle in handles:
        handle.close()
    labels_handle.close()

    if not args.no_window_assert:
        for section in shipped:
            for key in ("eval", "holdout"):
                assert written[section][key]["positives"] >= MIN_POSITIVES, (section, key)
                assert len(positive_days[section][key]) >= MIN_DISTINCT_DAYS, (section, key)
    del enriched

    baselines = {}
    for section in shipped:
        name = config_name(section)
        with (out / name / LAYOUT["eval"]).open(newline="", encoding="utf-8") as fh:
            eval_rows = list(csv.DictReader(fh))
        labels = [int(row[name]) for row in eval_rows]
        scores = [float(row["prev_target_cited"]) for row in eval_rows]
        auc = auc_from_scores(labels, scores)
        baselines[section] = {
            "persistence_prev_target_cited_eval_auc": round(auc, 6) if auc is not None else None,
            "eval_base_rate": round(sum(labels) / len(labels), 6) if labels else None,
            "eval_positives": sum(labels)}

    manifest_configs = []
    total_bytes = 0
    for section in shipped:
        name = config_name(section)
        config_dir = out / name
        rows_by_split = {key: written[section][key]["rows"] for key in LAYOUT}
        rate_by_split = {key: (round(written[section][key]["positives"]
                                     / written[section][key]["rows"], 6)
                               if written[section][key]["rows"] else None)
                         for key in LAYOUT}
        write_meta(config_dir, name, section, headers[section], rows_by_split,
                   rate_by_split, built_at)
        write_quality(config_dir, name, section, headers[section],
                      {key: written[section][key]["positives"] for key in LAYOUT},
                      {key: positive_days[section][key] for key in LAYOUT},
                      prevalence.get(section, 0.0), built_at)
        entry = {"name": name, "target": name, "section": section,
                 "rows": rows_by_split, "positive_rate": rate_by_split,
                 "positives": {key: written[section][key]["positives"] for key in LAYOUT},
                 "positive_days": {key: len(positive_days[section][key]) for key in LAYOUT},
                 "persistence_baseline": baselines[section], "files": {}}
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
        print(f"  {name} ({section}): rows {rows_by_split} rates {rate_by_split} "
              f"persistence {baselines[section]['persistence_prev_target_cited_eval_auc']}")

    manifest = {
        "candidate": "msha-enforcement-citations",
        "source_files": {name: {"file": SOURCES[name], "url": f"{BASE}/{SOURCES[name]}",
                                "bytes": zip_bytes[name]} for name in SOURCES},
        "built_at_utc": built_at,
        "prediction_time": PREDICTION_TIME,
        "formulation": "one binary runner config per floor 30 CFR section; the "
                       "joint multi-label matrix is labels.csv",
        "pool": {"definition": "events carrying at least one violation row, with "
                               "a parseable INSPECTION_BEGIN_DT inside a split "
                               "window",
                 "events": pool_rows,
                 "citation_rows": citation_rows,
                 "sampled_events": sampled,
                 "dropped_no_inspection_row": dropped_no_inspection,
                 "dropped_no_begin_date": dropped_no_begin,
                 "dropped_no_mine_id": dropped_no_mine,
                 "dropped_outside_windows": dropped_outside,
                 "empty_part_section_rows": empty_sections,
                 "malformed_rows": tally["malformed"]},
        "floor_rule": {"min_pool_rate": args.min_rate,
                       "min_positives_per_window": MIN_POSITIVES,
                       "min_distinct_days_per_window": MIN_DISTINCT_DAYS,
                       "max_configs": args.max_configs},
        "sections_seen": len(distinct_sections),
        "floor_candidates_above_rate": candidates,
        "floor_sections": all_floor,
        "floor_dropped_by_window_minimums": dropped_by_windows,
        "floor_dropped_by_config_cap": dropped_by_cap,
        "shipped_configs": [config_name(section) for section in shipped],
        "section_prevalence": {section: round(prevalence.get(section, 0.0), 6)
                               for section in all_floor},
        "features": FEATURES,
        "id_columns": ID_COLUMNS,
        "label_source_column": LABEL_SOURCE,
        "excluded_post_hoc": EXCLUDED_POST_HOC,
        "split_windows": SPLIT_WINDOWS,
        "configs": manifest_configs,
        "labels_csv": {"file": "labels.csv", "sha256": sha256_of(labels_path),
                       "bytes": labels_path.stat().st_size,
                       "columns": len(all_floor)},
        "shipped_columns_per_config": fieldnames + ["sec_<slug>"],
        "attribution": ATTRIBUTION,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")

    build_summary = {
        "candidate": "msha-enforcement-citations",
        "status": "extract-built",
        "built_at_utc": built_at,
        "pool_events": pool_rows,
        "floor_sections": all_floor,
        "shipped_configs": [config_name(section) for section in shipped],
        "configs": {config_name(section): {
            "rows": {key: written[section][key]["rows"] for key in LAYOUT},
            "positives": {key: written[section][key]["positives"] for key in LAYOUT},
            "positive_days": {key: len(positive_days[section][key]) for key in LAYOUT},
            "persistence_baseline": baselines[section]} for section in shipped},
        "total_split_bytes": total_bytes,
        "labels_csv_bytes": labels_path.stat().st_size,
        "note": "Measured extract with checksums, in the runner's public/private "
                "layout per floor section. Not a scored result.",
    }
    (out / "build_summary.json").write_text(json.dumps(build_summary, indent=1) + "\n")
    (out / "summary.json").write_text(json.dumps(
        {"candidate": "msha-enforcement-citations", "status": "extract-built",
         "built_at_utc": built_at, "pool_events": pool_rows,
         "floor_sections": all_floor,
         "configs": [config_name(section) for section in shipped]}, indent=1) + "\n")

    print(f"\nwrote {len(shipped)} configs under {out}, plus labels.csv, "
          f"manifest.json, build_summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
