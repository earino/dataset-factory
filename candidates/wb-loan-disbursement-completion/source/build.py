#!/usr/bin/env python3
"""Construction for the `wb-loan-disbursement-completion` prediction task.

One row per matured IBRD loan. The question: at the instant the World Bank
Board approves an IBRD loan (board_approval_date, an event time documented by
the publisher as 'The date the World Bank approves the loan'), will that loan
disburse at least 90% of its original principal amount over its life?

This file ONLY constructs the artifact and its gate diagnostics:
public/train.csv, public/eval.csv, private/holdout.csv, meta.json,
quality.json, summary.json. No performance metric (AUC, accuracy, any model
score) is computed anywhere in it; references run in score.py after the gate
passed and --accept re-verified the exact bytes.

Population and label follow the candidate record exactly:
  * scope: IBRD instruments from DS00047 (latest available snapshot), dropping
    guarantee prefixes IBRDB/IBRDG and the B-loan/guarantee-facility types
    BLNR/BLNC/GURB/GUBF, and rows with original_principal_amount <= 0;
  * maturity (recorded rule): disbursement phase closed = terminal loan_status
    (Fully Repaid/Cancelled/Disbursed/Transferred, Terminated) OR 'Repaying'
    OR closed_date_most_recent <= data-as-of; 'Repaying' with
    undisbursed_amount > 0 is excluded by construction (measured: 2 rows);
  * censoring: board approvals through 2017 only (approvals 2018+ are 12-96%
    still open in the 2026-09-30 snapshot and are counted per year, never
    labeled); still-open approvals <= 2017 are counted per year and excluded;
  * label: completed90 = 1 iff disbursed_amount / original_principal_amount
    >= 0.90. Ratio 0 (fully cancelled, cancelled_amount == original) is a
    genuine negative, not missing data;
  * entity isolation: every project_id whose loans would span two split
    windows is dropped whole (measured: 83 projects / 172 rows), so no
    project_id appears in two splits and no cross-split project_id join can
    couple a labeled train row to an eval/holdout row.

Licence: CC BY 4.0 International (stated on the DS00047 dataset page and in
the metadata API; class A in the candidate record). Attribution 'Source:
World Bank Group Finances One' carries to any release. Derived research
dataset - never an official World Bank product.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

NAME = "wb-loan-disbursement-completion"
API = ("https://datacatalogapi.worldbank.org/dexapps/fone/api/apiservice"
       "?datasetId=DS00047&resourceId=RS00049&top=1000&skip={skip}&type=json")
UA = ("Scout-factory-build/1.0 (dataset-factory worker construction; "
      "contact: financesone@worldbank.org)")
PAGE = 1000

TARGET = "completed90"
POSITIVE_LABEL = 1
THRESHOLD = 0.90

ID_COLUMNS = ["loan_number", "project_id"]
CARRY_COLUMNS = ["board_approval_date"]
FEATURES = [
    "country",
    "country_code",
    "guarantor",
    "guarantor_country_code",
    "borrower",
    "loan_type",
    "original_principal_amount",
    "board_approval___calendar_year",
]
HIGH_CARDINALITY = ["loan_number", "project_id", "board_approval_date", "borrower"]
COLUMNS = ID_COLUMNS + CARRY_COLUMNS + FEATURES + [TARGET]
LAYOUT = {"train": "public/train.csv",
          "eval": "public/eval.csv",
          "holdout": "private/holdout.csv"}

# The label source and every post-instant field. None of these may appear in
# the written files; the build asserts their absence after writing.
LABEL_SOURCE_COLUMNS = [
    "disbursed_amount", "undisbursed_amount", "cancelled_amount",
    "loan_status", "closed_date_most_recent", "last_disbursement_date",
    "first_repayment_date", "last_repayment_date", "repaid_to_ibrd",
    "repaid_3rd_party", "due_to_ibrd", "due_3rd_party", "sold_3rd_party",
    "loans_held", "exchange_adjustment", "borrowers_obligation",
    "interest_rate", "effective_date_most_recent", "agreement_signing_date",
    "end_of_period",
]
POST_HOC_COLUMNS = LABEL_SOURCE_COLUMNS  # every field that postdates the instant

GUARANTEE_PREFIXES = ("IBRDB", "IBRDG")
EXCLUDED_TYPES = {"BLNR", "BLNC", "GURB", "GUBF"}
TERMINAL_STATUS = {"Fully Repaid", "Fully Cancelled", "Fully Disbursed",
                   "Fully Transferred", "Terminated"}
OPEN_DISBURSING = {"Disbursing", "Disbursing&Repaying", "Effective",
                   "Signed", "Approved"}
APPROVAL_CUTOFF_YEAR = 2017
DATA_AS_OF = date(2026, 9, 30)  # 'Data As Of' on the DS00047 page, 2026-10-28

TRAIN_END_YEAR = 1999
EVAL_END_YEAR = 2009

PREDICTION_QUESTION = (
    "At the instant the World Bank Board approves an IBRD loan "
    "(board_approval_date), will that loan disburse at least 90% of its "
    "original principal amount over its life? Answer 1 = yes (final "
    "disbursed_amount / original_principal_amount >= 0.90), 0 = no. "
    "Features are the approval-time attributes published in the IBRD "
    "Statement of Loans and Guarantees: country, guarantor, borrower, loan "
    "type, original principal, approval year. The outcome resolves later, "
    "at the end of the loan's disbursement window, so the whole target "
    "window follows the prediction instant.")
PREDICTION_TIME = (
    "Board Approval Date - an event time the publisher documents as 'The "
    "date the World Bank approves the loan' (DS00047 column description, "
    "financesone.worldbank.org; the same-day press release and "
    "projects.worldbank.org record carry it). Features are the static "
    "approval-time attributes of the same administrative register: "
    "country/economy + code, borrower, guarantor + code, loan type, "
    "original principal (USD), board approval calendar year. The publisher "
    "documents `region` with current-vintage administrative coding, so "
    "region is NOT shipped; currency_of_commitment is empty on 100% of "
    "scoped IBRD rows (measured in-build) and is NOT shipped. The label "
    "resolves at loan closing, after the instant.")


def log(message: str) -> None:
    print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] {message}", flush=True)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def parse_day(value) -> date | None:
    if not value:
        return None
    return datetime.strptime(str(value), "%d-%b-%Y").date()


def num(row: dict, key: str) -> float:
    value = row.get(key)
    return float(value) if isinstance(value, (int, float)) else 0.0


def fetch_pages(work_dir: Path) -> tuple[list[dict], dict]:
    """Page the documented anonymous API; pin every page's bytes by sha256."""
    rows: list[dict] = []
    pages = []
    payloads = []
    total_bytes = 0
    started = time.time()
    server_count = None
    skip = 0
    while True:
        url = API.format(skip=skip)
        request = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(request, timeout=180) as response:
            raw = response.read()
        payload = json.loads(raw.decode("utf-8", "replace"))
        page_rows = payload.get("data") or []
        count = payload.get("count")
        if server_count is None:
            server_count = count
        digest = sha256_bytes(raw)
        pages.append({"skip": skip, "url": url, "bytes": len(raw),
                      "sha256": digest, "rows": len(page_rows)})
        payloads.append(raw)
        total_bytes += len(raw)
        rows.extend(page_rows)
        log(f"page skip={skip}: {len(page_rows)} rows, {len(raw)} bytes, "
            f"sha256 {digest[:12]}")
        if not page_rows or (count is not None and len(rows) >= count):
            break
        skip += PAGE
    elapsed = round(time.time() - started, 1)
    if server_count is not None and len(rows) != server_count:
        raise SystemExit(f"row count {len(rows)} != server count {server_count}; "
                         "the register moved mid-fetch - rerun the job")
    joined = b"".join(payloads)
    fetch_info = {
        "url_template": API,
        "pages": pages,
        "page_count": len(pages),
        "rows": len(rows),
        "server_count": server_count,
        "total_bytes": total_bytes,
        "combined_sha256": sha256_bytes(joined),
        "wall_seconds": elapsed,
        "data_as_of": DATA_AS_OF.isoformat(),
        "mode": "worker fetch (documented anonymous API, descriptive UA)",
    }
    return rows, fetch_info


def maturity(row: dict) -> str | None:
    """Recorded rule: terminal status, Repaying, or closing date already past.

    Returns the pathway that closed the loan, or None while still open.
    'Repaying' with undisbursed_amount > 0 must be excluded by the caller
    (measured: 2 rows) - its ratio is not final.
    """
    status = str(row.get("loan_status") or "")
    closed = parse_day(row.get("closed_date_most_recent"))
    if status in TERMINAL_STATUS:
        return "terminal_status"
    if status == "Repaying":
        return "repaying"
    if status in OPEN_DISBURSING:
        if closed and closed <= DATA_AS_OF:
            return "closed_date_passed"
        return None
    if closed and closed <= DATA_AS_OF:
        return "closed_date_passed"
    return None


def scope_population(rows: list[dict]) -> tuple[list[dict], dict]:
    """Apply the recorded scoping and censoring rules; count every bucket."""
    excluded: Counter = Counter()
    matured: list[dict] = []
    censored_open: dict[int, int] = defaultdict(int)
    censored_year: dict[int, int] = defaultdict(int)
    pathways: dict[str, int] = Counter()
    for row in rows:
        number = str(row.get("loan_number") or "")
        loan_type = str(row.get("loan_type") or "")
        original = row.get("original_principal_amount")
        if number.startswith(GUARANTEE_PREFIXES):
            excluded["guarantee_prefix"] += 1
            continue
        if loan_type in EXCLUDED_TYPES:
            excluded[f"loan_type_{loan_type}"] += 1
            continue
        if not isinstance(original, (int, float)) or original <= 0:
            excluded["nonpositive_original"] += 1
            continue
        if str(row.get("loan_status") or "") == "Repaying" and num(row, "undisbursed_amount") > 0:
            excluded["repaying_with_undisbursed"] += 1
            continue
        approval = parse_day(row.get("board_approval_date"))
        if approval is None:
            excluded["missing_approval_date"] += 1
            continue
        if approval.year > APPROVAL_CUTOFF_YEAR:
            censored_year[approval.year] += 1
            continue
        pathway = maturity(row)
        if pathway is None:
            censored_open[approval.year] += 1
            continue
        pathways[pathway] += 1
        matured.append(row)
    diagnostics = {
        "excluded": dict(excluded),
        "excluded_total": sum(excluded.values()),
        "censoring": {
            "rule": f"board approvals through {APPROVAL_CUTOFF_YEAR} only; "
                    "later approvals are 12-96% still open at the snapshot "
                    "and counted here, never labeled",
            "censored_by_approval_year": {str(k): v for k, v in sorted(censored_year.items())},
            "censored_open_within_cutoff": {str(k): v for k, v in sorted(censored_open.items())},
        },
        "maturity_pathways": dict(pathways),
    }
    return matured, diagnostics


def split_of_year(year: int) -> str:
    if year <= TRAIN_END_YEAR:
        return "train"
    if year <= EVAL_END_YEAR:
        return "eval"
    return "holdout"


def build_rows(matured: list[dict]) -> tuple[dict, dict]:
    """Row dicts per split after the project-entity isolation drop.

    A zero-disbursement row is kept as a genuine negative only when the
    in-row cancelled_amount documents a full cancellation (the candidate
    record's standard); otherwise the register contradicts itself about the
    loan's lifecycle and the outcome is counted unverified and excluded.
    """
    windows: dict[str, set] = defaultdict(set)
    for row in matured:
        year = parse_day(row["board_approval_date"]).year
        windows[str(row.get("project_id") or "")].add(split_of_year(year))
    straddling = sorted(project for project, sides in windows.items() if len(sides) > 1)
    straddle_rows = Counter()
    unverified_zero = Counter()
    keep: dict[str, list[dict]] = {split: [] for split in LAYOUT}
    for row in matured:
        project = str(row.get("project_id") or "")
        year = parse_day(row["board_approval_date"]).year
        split = split_of_year(year)
        if project in straddling:
            straddle_rows[split] += 1
            continue
        disbursed = num(row, "disbursed_amount")
        original = num(row, "original_principal_amount")
        ratio = disbursed / original
        if disbursed == 0.0 and row.get("cancelled_amount") != original:
            # 18 rows measured (2026-10-28): status Fully Repaid/Terminated
            # with disbursed=undisbursed=cancelled=0 against a positive
            # commitment (succession-era records). The register does not
            # document a genuine zero outcome for these instruments.
            unverified_zero[split] += 1
            continue
        keep[split].append({
            "loan_number": str(row.get("loan_number") or ""),
            "project_id": project,
            "board_approval_date": parse_day(row["board_approval_date"]).isoformat(),
            "country": str(row.get("country") or ""),
            "country_code": str(row.get("country_code") or ""),
            "guarantor": str(row.get("guarantor") or ""),
            "guarantor_country_code": str(row.get("guarantor_country_code") or ""),
            "borrower": str(row.get("borrower") or ""),
            "loan_type": str(row.get("loan_type") or ""),
            "original_principal_amount": original,
            "board_approval___calendar_year": year,
            TARGET: int(ratio >= THRESHOLD),
            "_ratio": ratio,
            "_cancelled": row.get("cancelled_amount"),
        })
    for split in keep:
        keep[split].sort(key=lambda r: (r["board_approval_date"], r["loan_number"]))
    diagnostics = {
        "straddling_projects": len(straddling),
        "straddling_projects_list_sample": straddling[:10],
        "straddling_rows_dropped_by_split": dict(straddle_rows),
        "straddling_rows_total": sum(straddle_rows.values()),
        "isolation_rule": ("a project_id whose matured loans span two split "
                           "windows is dropped whole so no project appears in "
                           "two splits; the reason is entity position, never "
                           "the label value"),
        "zero_disbursement_unverified_by_split": dict(unverified_zero),
        "zero_disbursement_unverified_total": sum(unverified_zero.values()),
        "zero_disbursement_rule": (
            "a ratio-0 row is a genuine negative only when cancelled_amount "
            "== original_principal_amount (a documented full cancellation); "
            "rows with disbursed=0 and cancelled != original have an "
            "internally contradictory register record (status Fully Repaid/"
            "Terminated with all amount fields zero) - their outcome is "
            "counted unverified and excluded, never labeled"),
    }
    return keep, diagnostics


def check_isolation(rows_by_split: dict) -> dict:
    """Post-drop assertion and measurement of the project isolation rule."""
    owners: dict[str, set] = defaultdict(set)
    for split, rows in rows_by_split.items():
        for row in rows:
            owners[row["project_id"]].add(split)
    cross = sorted(p for p, sides in owners.items() if len(sides) > 1)
    if cross:
        raise SystemExit(f"project isolation failed: {len(cross)} projects in "
                         f"two splits, e.g. {cross[:3]}")
    repeats = {}
    for split, rows in rows_by_split.items():
        counts = Counter(row["project_id"] for row in rows)
        repeats[split] = {
            "projects": len(counts),
            "repeated_projects": sum(1 for c in counts.values() if c > 1),
            "max_loans_per_project": max(counts.values()) if counts else 0,
        }
    return {"cross_split_projects": 0, "within_split_repeats": repeats}


def check_fixtures(rows_by_split: dict) -> list[dict]:
    """Known rows asserted in-build against the fetched register."""
    by_number = {}
    for rows in rows_by_split.values():
        for row in rows:
            by_number[row["loan_number"]] = row
    fixtures = [
        {"loan_number": "IBRD00010",
         "expect": {"country": "France", "board_approval_date": "1947-05-09",
                    TARGET: 1, "_ratio": 1.0},
         "note": "IBRD's first loan: 250,000,000 USD disbursed of "
                 "250,000,000 committed, Fully Repaid - ratio 1.0, positive"},
        {"loan_number": "IBRD00130",
         "expect": {"country": "Mexico", TARGET: 0, "_ratio": 0.0},
         "note": "fully cancelled with cancelled_amount == original "
                 "(10,000,000 USD): a genuine zero-disbursement negative, "
                 "not missing data"},
        {"loan_number": "IBRD00230",
         "expect": {"country": "India", TARGET: 1},
         "note": "boundary row: 16,720,500 / 18,500,000 = 0.903811 - just "
                 "above the inclusive 0.90 threshold, positive"},
        {"loan_number": "IBRD00550",
         "expect": {"country": "Paraguay", TARGET: 0},
         "note": "just below: 4,488,990.46 / 5,000,000 = 0.897798 < 0.90, "
                 "negative - the threshold bites"},
    ]
    for fixture in fixtures:
        row = by_number.get(fixture["loan_number"])
        if row is None:
            raise SystemExit(f"fixture {fixture['loan_number']} missing from "
                             "the labeled population; the register changed")
        for key, expected in fixture["expect"].items():
            actual = row[key]
            if key == "_ratio":
                ok = abs(actual - expected) < 1e-9 if expected in (0.0, 1.0) \
                    else abs(actual - expected) < 1e-4
            else:
                ok = actual == expected
            if not ok:
                raise SystemExit(f"fixture {fixture['loan_number']}: "
                                 f"{key} = {actual!r}, expected {expected!r}")
        fixture["observed"] = {k: row[k] for k in fixture["expect"]}
    return fixtures


def write_splits(out: Path, rows_by_split: dict) -> dict:
    stats = {}
    for split, relative in LAYOUT.items():
        path = out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = rows_by_split[split]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(COLUMNS)
            for row in rows:
                writer.writerow([row[column] for column in COLUMNS])
        positives = sum(row[TARGET] for row in rows)
        stats[split] = {
            "rows": len(rows),
            "positives": positives,
            "negatives": len(rows) - positives,
            "positive_rate": round(positives / len(rows), 6) if rows else None,
            "distinct_positive_projects": len({row["project_id"] for row in rows if row[TARGET]}),
            "distinct_positive_country_years": len({
                (row["country_code"], row["board_approval___calendar_year"])
                for row in rows if row[TARGET]}),
            "min_approval_date": min((row["board_approval_date"] for row in rows), default=None),
            "max_approval_date": max((row["board_approval_date"] for row in rows), default=None),
        }
        log(f"{split}: {stats[split]['rows']} rows, {positives} positives "
            f"({stats[split]['distinct_positive_projects']} positive projects)")
    return stats


def assert_label_sources_absent(out: Path) -> None:
    """The register's outcome fields must not appear in any written file."""
    for relative in LAYOUT.values():
        with (out / relative).open(newline="", encoding="utf-8") as handle:
            header = next(csv.reader(handle))
        forbidden = sorted(set(header) & set(LABEL_SOURCE_COLUMNS))
        if forbidden:
            raise SystemExit(f"{relative} ships label-source columns: {forbidden}")
        missing = [column for column in COLUMNS if column not in header]
        if missing:
            raise SystemExit(f"{relative} misses declared columns: {missing}")


def quality_document(out: Path, stats: dict, fetch_info: dict, scope_diag: dict,
                     straddle_diag: dict, isolation: dict, fixtures: list,
                     built_at: str, currency_empty: int) -> None:
    positive_events = {split: {
        "positives": stats[split]["positives"],
        "distinct_events": stats[split]["distinct_positive_projects"]}
        for split in LAYOUT}
    quality = {
        "name": NAME,
        "task": {"question": PREDICTION_QUESTION,
                 "prediction_time": PREDICTION_TIME},
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "time_column": "board_approval_date",
        "event_key_column": "project_id",
        "event_key_note": (
            "one World Bank project can carry several IBRD loans that share "
            "an implementation fate, so the conservative independent-event "
            "count is distinct project_id among positives; distinct "
            "(country, approval-year) positive clusters are recorded beside "
            "it in summary.json split_stats as the coarser country-year view"),
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "feature_documentation": (
            "every shipped feature is a static approval-time attribute of "
            "the IBRD Statement of Loans register: country/country_code and "
            "guarantor/guarantor_country_code are the publisher's borrower "
            "and guarantor identities at approval; borrower is the "
            "contracting entity named at approval (free text); loan_type is "
            "the instrument type approved (CPL, NPL, FSL, SCL, SCPD, SCPM, "
            "SCPY in the shipped population); original_principal_amount is "
            "the USD commitment approved by the Board; "
            "board_approval___calendar_year is the calendar year of the "
            "approval event. Not shipped, with reasons: `region` (the "
            "publisher's own description documents current-vintage "
            "administrative-region coding - back-coded for pre-2011 "
            "approvals); `currency_of_commitment` (empty on 100% of scoped "
            "IBRD rows, measured in-build); `interest_rate` (a "
            "current-vintage value for variable-rate types, not an "
            "approval-time attribute); `project_name` (free text duplicating "
            "the project_id grouping); `board_approval___fiscal_year` "
            "(derivable from the shipped approval date); "
            "agreement_signing_date and effective_date_most_recent (events "
            "that happen after the approval instant); every disbursement, "
            "repayment, cancellation, transfer and status field (the label "
            "source and other post-instant outcomes)."),
        "carry_columns": CARRY_COLUMNS,
        "id_columns": ID_COLUMNS,
        "high_cardinality_columns": HIGH_CARDINALITY,
        "high_cardinality_note": (
            "loan_number is unique per row; project_id groups a project's "
            "loans (1,192 projects repeat within train by the source's "
            "grain); board_approval_date is a free event date; borrower is "
            "free text with 175 levels carrying >= 5 rows. All four are "
            "declared rather than scored. The runner's id_columns exclude "
            "loan_number and project_id from default model input; a custom "
            "solver could still read them, and they carry no label "
            "information: project isolation (below) keeps every project on "
            "one side of every split boundary, so a project_id join across "
            "splits finds nothing"),
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "post_hoc_columns": POST_HOC_COLUMNS,
        "measurements": [
            {"column": "original_principal_amount",
             "unit": "USD (current dollars as recorded in the register)",
             "frame": "the Board-approved commitment at the instant; "
                      "positive by the scoping rule"},
            {"column": "board_approval___calendar_year",
             "unit": "calendar year (integer)",
             "frame": "the year of the approval event; equals the year of "
                      "board_approval_date"},
            {"column": "board_approval_date",
             "unit": "ISO date",
             "frame": "the prediction instant itself (carry column and "
                      "split time column)"},
            {"column": "country", "unit": "publisher country/economy name",
             "frame": "borrower country identity at approval"},
            {"column": "country_code", "unit": "publisher country code",
             "frame": "borrower country identity at approval"},
            {"column": "guarantor", "unit": "publisher guarantor name",
             "frame": "guarantor identity at approval (often the state "
                      "itself)"},
            {"column": "guarantor_country_code", "unit": "publisher code",
             "frame": "guarantor identity at approval"},
            {"column": "borrower", "unit": "free text (contracting entity)",
             "frame": "the entity named as borrower at approval"},
            {"column": "loan_type", "unit": "publisher instrument code",
             "frame": "the approved instrument type; guarantees and "
                      "B-loan/guarantee-facility types are excluded by "
                      "the scoping rule"},
            {"column": "loan_number", "unit": "publisher instrument number",
             "frame": "row identifier; unique per instrument"},
            {"column": "project_id", "unit": "publisher project code",
             "frame": "the World Bank project the loan finances; the "
                      "cluster key for independent-event counting"},
            {"column": TARGET,
             "unit": "binary 0/1",
             "frame": f"1 iff final disbursed_amount / "
                      f"original_principal_amount >= {THRESHOLD}; measured "
                      "on the matured (disbursement-closed) population only; "
                      "ratio 0 is a genuine negative only when "
                      "cancelled_amount == original (a documented full "
                      "cancellation; asserted in-build on every shipped "
                      "ratio-0 row); zero-disbursement rows without that "
                      "documentation are excluded as unverified and "
                      "counted in summary.json (18 rows measured "
                      "2026-10-28)"},
        ],
        "external_threshold": False,
        "known_event": {
            "name": "in-build register fixtures (IBRD00010, IBRD00130, "
                    "IBRD00230, IBRD00550)",
            "expected_verdict": "exceeds",
            "detail": "four named loans asserted against the fetched bytes: "
                      "ratio 1.0 positive, ratio 0.0 genuine negative, a "
                      "0.903811 boundary positive and a 0.897798 just-below "
                      "negative - the threshold is internal to the task, so "
                      "the fixture set pins units and inclusivity rather "
                      "than an external standard",
            "source": "the fetched DS00047 register itself (values cross-"
                      "checked at discovery against the dataset page's "
                      "documented columns)",
        },
        "timing": {
            "prediction_instant": {
                "kind": "event_time",
                "period": "day",
                "days_after_period_end": 0,
                "citation": (
                    "DS00047 column description, read 2026-10-28: "
                    "board_approval_date is 'The date the World Bank "
                    "approves the loan' (financesone.worldbank.org/d/DS00047 "
                    "and the metadata API); the same-day press release and "
                    "projects.worldbank.org record publish it at the event"),
            },
            "features": {
                "period": "day",
                "published_days_after_period_end": 0,
                "source_kind": "administrative_record",
            },
            "row_selection": {
                "latest_period_used": f"{APPROVAL_CUTOFF_YEAR} (approval-date censoring)",
                "fields": ["loan_number prefix", "loan_type", "original_principal_amount",
                           "board_approval_date", "loan_status",
                           "closed_date_most_recent", "undisbursed_amount"],
                "basis": (
                    "membership reads the approval date (year <= 2017) and "
                    "the scoping rules (guarantee prefixes, facility types, "
                    "positive commitment). Maturity censoring reads "
                    "loan_status/closed_date to exclude loans whose outcome "
                    "is not yet observed in the fetched snapshot: this is "
                    "outcome-OBSERVABILITY conditioning, never a label-value "
                    "condition, and it is bounded and recorded (13 "
                    "still-open approvals <= 2017, counted per year in "
                    "summary.json). The label is computed only after "
                    "membership is fixed. The project-entity isolation drop "
                    "reads only each project's approval-year position, "
                    "never any label"),
            },
            "observations": [],
        },
        "split_windows": {
            "train": {"start": "1947-01-01", "end": "2000-01-01"},
            "eval": {"start": "2000-01-01", "end": "2010-01-01"},
            "holdout": {"start": "2010-01-01", "end": "2018-01-01"},
        },
        "split_boundaries": {
            "train": "board approval years 1947-1999 (window end exclusive)",
            "eval": "board approval years 2000-2009 (window end exclusive)",
            "holdout": f"board approval years 2010-{APPROVAL_CUTOFF_YEAR} "
                       "(window end exclusive; the censoring cutoff)",
        },
        "positive_events": positive_events,
        "positive_events_note": (
            "positives and distinct project_id events per split, recomputed "
            "from the written rows; the gate re-verifies. Distinct "
            "(country, approval-year) positive clusters are recorded in "
            "summary.json as the coarser view"),
        "expected_duplicate_ids": 0,
        "id_columns_are_entity_keys": True,
        "id_columns_note": (
            "loan_number names one IBRD instrument with one final outcome; "
            "project_id repeats within a split by the source's grain (a "
            "project carries several loans) and is the cluster key, not a "
            "one-label entity key - it is declared high-cardinality and "
            "excluded from default model input via task id_columns"),
        "splits": LAYOUT,
        "evaluation_contract": {
            "use": "retrospective_research",
            "access": "isolated_rows",
            "training_label_timing": "unverified",
            "scope_note": (
                "each row is one IBRD loan whose features are approval-time "
                "register attributes; the runner predicts row-wise from the "
                "shipped columns. Labeled eval is development/validation; "
                "the holdout is the final test and stays outside evaluated "
                "agents' workspaces. Training-label timing is UNVERIFIED: "
                "the label resolves at loan closing years after the "
                "instant, and the register publishes no historical as-of "
                "ledger for closure dates, so no full-row availability "
                "ledger can be constructed - retrospective research only, "
                "never a certified historical forecasting setup"),
            "feature_evidence": {
                "loan_number": {
                    "source": "register column 'Loan Number'",
                    "availability": "the instrument's own identity, assigned "
                                    "at approval",
                    "status": "verified"},
                "project_id": {
                    "source": "register column 'Project ID'",
                    "availability": "the WB project code assigned at "
                                    "approval",
                    "status": "verified"},
                "board_approval_date": {
                    "source": "register column 'Board Approval Date' "
                              "('The date the World Bank approves the loan')",
                    "availability": "the prediction instant itself",
                    "status": "verified"},
                "country": {
                    "source": "register column 'Country/Economy'",
                    "availability": "borrower identity recorded at approval",
                    "status": "assumed",
                    "assumption": "current-vintage register value of a "
                                  "static approval attribute; no as-of "
                                  "reconstruction performed"},
                "country_code": {
                    "source": "register column 'Country Code'",
                    "availability": "borrower identity recorded at approval",
                    "status": "assumed",
                    "assumption": "current-vintage register value of a "
                                  "static approval attribute"},
                "guarantor": {
                    "source": "register column 'Guarantor'",
                    "availability": "guarantor identity recorded at approval",
                    "status": "assumed",
                    "assumption": "current-vintage register value of a "
                                  "static approval attribute"},
                "guarantor_country_code": {
                    "source": "register column 'Guarantor Country Code'",
                    "availability": "guarantor identity recorded at approval",
                    "status": "assumed",
                    "assumption": "current-vintage register value of a "
                                  "static approval attribute"},
                "borrower": {
                    "source": "register column 'Borrower'",
                    "availability": "the contracting entity named at "
                                    "approval",
                    "status": "assumed",
                    "assumption": "current-vintage register value of a "
                                  "static approval attribute; free text "
                                  "(MINISTRY OF FINANCE and 908 other levels)"},
                "loan_type": {
                    "source": "register column 'Loan Type'",
                    "availability": "the approved instrument type",
                    "status": "assumed",
                    "assumption": "current-vintage register value of a "
                                  "static approval attribute"},
                "original_principal_amount": {
                    "source": "register column 'Original Principal Amount'",
                    "availability": "the Board-approved USD commitment",
                    "status": "assumed",
                    "assumption": "current-vintage register value of a "
                                  "static approval attribute"},
                "board_approval___calendar_year": {
                    "source": "register column 'Board Approval (Calendar "
                              "Year)', derivable from board_approval_date",
                    "availability": "calendar arithmetic on the instant",
                    "status": "verified"},
            },
            "vintage": {
                "kind": "current_snapshot",
                "evidence": (
                    "DS00047 is one in-place-updated latest-available "
                    "snapshot ('Data As Of' 2026-09-30, read 2026-10-28). "
                    "A monthly historical-vintage dataset exists (DS00975, "
                    "April 2011 onward, 1,585,498 rows), but the documented "
                    "API filter silently ignored end_of_period values in "
                    "all four formats tried (probe 2026-10-28: server count "
                    "stayed 1,585,498), so no per-month as-of slice was "
                    "established and none was used. Shipped features are "
                    "approval-time attributes the publisher documents as "
                    "fixed at approval; the one field it documents as "
                    "current-vintage (region) is not shipped. No historical "
                    "point-in-time availability is claimed"),
            },
            "selection": {
                "kind": "prediction_time",
                "evidence": (
                    "membership is fixed by approval-date attributes "
                    "(year <= 2017) and instrument scoping rules; the "
                    "maturity censoring excludes loans whose outcome is "
                    "unobserved at the snapshot (13 rows for approvals "
                    "<= 2017, counted per year) and never reads the label "
                    "value; the zero-disbursement rule excludes register "
                    "records that contradict themselves about the loan's "
                    "lifecycle (disbursed=0 without a documented full "
                    "cancellation; 18 rows, counted per split) - an "
                    "outcome-observability exclusion, not a label-value "
                    "condition, decided and recorded before any scoring; "
                    "the project-entity drop reads only approval-year "
                    "position. The label (a ratio of two register fields) "
                    "is computed after membership is fixed and never "
                    "decides membership"),
            },
            "limitations": [
                "One-shot outcome per loan: there is no within-entity "
                "history in the shipped columns, so the persistence "
                "analogue is a country's last earlier matured train loan, "
                "not a value observed on the row itself.",
                "18 register rows with a positive commitment and a "
                "terminal status but all amount fields zero (succession-"
                "era records, e.g. IBRD14699 Croatia 1977) have no "
                "documented disbursement outcome; they are excluded as "
                "unverified and counted, never labeled - a recorded "
                "outcome-observability exclusion, not a label-value "
                "condition.",
                f"Population conditions on disbursement closure observed at "
                f"the fetched snapshot; for approvals <= {APPROVAL_CUTOFF_YEAR} "
                "this excludes 13 still-open loans (0.16%), counted per year "
                "- a bounded, recorded censoring choice, not a label-value "
                "condition.",
                "Current-vintage register with no as-of reconstruction: "
                "retrospective research, not certified historical "
                "forecasting; DS00975 monthly vintages exist but their API "
                "slicing was unconfirmed at discovery.",
                f"{straddle_diag.get('straddling_rows_total')} rows in "
                f"{straddle_diag.get('straddling_projects')} projects are "
                "dropped because their loans span split boundaries (entity "
                "isolation); counted per split in summary.json.",
                "currency_of_commitment is empty on 100% of scoped IBRD "
                f"rows ({currency_empty} rows checked) and is not shipped; "
                "IBRD commitments are recorded in USD.",
                "region is not shipped: the publisher documents it with "
                "current-vintage administrative coding.",
                "Accounting identity disbursed+undisbursed+cancelled == "
                "original mismatches on 763/8,474 matured rows (sold-3rd-"
                "party transfers, e.g. IBRD00010 France 1947); the label "
                "uses disbursed/original directly and is unaffected.",
                "Guarantees (IBRDB/IBRDG) and B-loan/guarantee-facility "
                "types (BLNR, BLNC, GURB, GUBF) are excluded; counts in "
                "summary.json.",
                "The IDA Statement of Credits (DS00001) is excluded from "
                "v1: its label semantics fail the accounting identity on "
                "7,575/9,298 closed rows and need their own verification.",
                "The 0.90 threshold is this task's own operational choice "
                "(the >= 99% near-balanced alternative is measured in "
                "summary.json, base rate 51.5% among matured rows, not "
                "shipped).",
            ],
            "cross_row_audit": {
                "probes": [],
                "probes_note": (
                    "no generic probe applies, reviewed per "
                    "docs/PREDICTION-CONTRACT.md: the generic machinery "
                    "donates a LATER row's feature to an EARLIER row's "
                    "label, and every shipped feature is a static "
                    "approval-time attribute (identity, instrument type, "
                    "commitment amount, year) - no later row's feature "
                    "encodes any earlier row's outcome, so the forward "
                    "donation has nothing to expose. The reverse-direction "
                    "exposure - an earlier same-project loan's label "
                    "readable through a project_id join - is eliminated by "
                    "construction: the build drops every project whose "
                    "loans span two splits and asserts zero cross-split "
                    "projects after the drop, so a train->eval or "
                    "train->holdout project_id join finds no rows. Within "
                    "one split, same-project and same-country joins read "
                    "that split's own labels - the standard labeled-"
                    "development protocol, not cross-row exposure"),
                "rationale": (
                    "rows are one-shot loan outcomes with no panel "
                    "self-answering structure: the label is a ratio of two "
                    "register fields absent from the shipped columns, and "
                    "no shipped column is another row's outcome. The audit "
                    "reviewed the full configuration on the worker: "
                    "cross-split project_id joins are empty by the "
                    "isolation assertion, and access is isolated_rows"),
                "auxiliary_files_review": (
                    "the extract ships exactly the runner layout - "
                    "public/train.csv, public/eval.csv, "
                    "private/holdout.csv, meta.json, quality.json; the "
                    "fetched API pages and all diagnostics stay outside "
                    "the artifact; no joint label matrices or other "
                    "solver-visible files exist in the dataset directory"),
                "reverse_history": (
                    "partially available and NOT used: DS00975 ships "
                    "monthly statement vintages from April 2011 (probed "
                    "2026-10-28), but the documented apiservice filter "
                    "ignored end_of_period values in all four formats "
                    "tried, so no as-of slice was reconstructed; the "
                    "current-vintage posture above is the recorded "
                    "consequence"),
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
    parser.add_argument("--work-dir", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    work = Path(args.work_dir)
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    built_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    log("== fetch (documented anonymous API, every page pinned) ==")
    rows, fetch_info = fetch_pages(work)

    log(f"== scope: {len(rows)} fetched rows ==")
    matured, scope_diag = scope_population(rows)
    log(f"matured (disbursement-closed, approved <= {APPROVAL_CUTOFF_YEAR}): "
        f"{len(matured)}")

    currency_nonempty = sum(
        1 for row in matured if str(row.get("currency_of_commitment") or "").strip())
    if currency_nonempty:
        raise SystemExit("currency_of_commitment is no longer empty on the "
                         "scoped population; the feature contract needs a "
                         "fresh review")

    rows_by_split, straddle_diag = build_rows(matured)
    isolation = check_isolation(rows_by_split)

    # Fixtures first: they read the private _ratio/_cancelled keys, which the
    # strip loop below removes before the rows are written.
    fixtures = check_fixtures(rows_by_split)
    log(f"fixtures: {len(fixtures)} asserted OK")

    for split_rows in rows_by_split.values():
        for row in split_rows:
            if row["_ratio"] == 0.0 and row["_cancelled"] != row["original_principal_amount"]:
                raise SystemExit(f"ratio-0 row {row['loan_number']} is not a "
                                 "documented cancellation - the exclusion rule "
                                 "was bypassed")
            del row["_ratio"]
            del row["_cancelled"]

    log("== write ==")
    stats = write_splits(out, rows_by_split)
    assert_label_sources_absent(out)
    log("label-source columns absent from all three files")

    total_rows = sum(stats[split]["rows"] for split in LAYOUT)
    meta = {
        "name": NAME,
        "description": PREDICTION_QUESTION,
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": ID_COLUMNS,
        "columns": COLUMNS,
        "rows": {split: stats[split]["rows"] for split in LAYOUT},
        "positive_rate": {split: stats[split]["positive_rate"] for split in LAYOUT},
        "split": (f"temporal on board approval year: train 1947-{TRAIN_END_YEAR}, "
                  f"eval {TRAIN_END_YEAR + 1}-{EVAL_END_YEAR}, holdout "
                  f"{EVAL_END_YEAR + 1}-{APPROVAL_CUTOFF_YEAR}"),
        "split_description": (
            f"temporal on board approval year: train 1947-{TRAIN_END_YEAR}, "
            f"eval {TRAIN_END_YEAR + 1}-{EVAL_END_YEAR}, holdout "
            f"{EVAL_END_YEAR + 1}-{APPROVAL_CUTOFF_YEAR}; population is "
            "matured IBRD loans (disbursement-closed in the 2026-09-30 "
            "snapshot), guarantees and B-loan facility types excluded, "
            "positive original principal only, every project_id wholly "
            "inside one split"),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    quality_document(out, stats, fetch_info, scope_diag, straddle_diag,
                     isolation, fixtures, built_at, len(matured))

    per_year = {}
    for split, split_rows in rows_by_split.items():
        by_year = defaultdict(lambda: [0, 0])
        for row in split_rows:
            entry = by_year[row["board_approval___calendar_year"]]
            entry[0] += 1
            entry[1] += row[TARGET]
        per_year[split] = {str(year): {"rows": v[0], "positives": v[1]}
                           for year, v in sorted(by_year.items())}

    summary = {
        "name": NAME,
        "stage": "construction (no performance metric computed anywhere here)",
        "fetch": fetch_info,
        "scope": {
            "fetched_rows": len(rows),
            "matured_rows": len(matured),
            **scope_diag,
        },
        "currency_of_commitment": {
            "nonempty_rows_on_matured_population": currency_nonempty,
            "note": "empty on 100% of scoped IBRD rows - not shipped",
        },
        "entity_isolation": {**straddle_diag, **isolation},
        "split_stats": stats,
        "per_approval_year": per_year,
        "label_threshold": {
            "primary": "final disbursed / original >= 0.90 (shipped)",
            "alternative_measured_not_shipped":
                ">= 0.99 (near-balanced; base rate among all matured rows "
                "recorded by the discovery probe as 51.52%)",
        },
        "fixtures": fixtures,
        "built_at_utc": built_at,
        "shipped_rows": total_rows,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    log(f"== done: {total_rows} rows written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
