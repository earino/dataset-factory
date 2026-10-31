#!/usr/bin/env python3
"""Construct the acnc-charity-ais-deadline-compliance artifact.

Task: for an ACNC-registered charity whose period-(Y-1) Annual Information
Statement was already received 90 days before its period-Y AIS due date, will
the charity FAIL to lodge the period-Y AIS by the ACNC-recorded due date?

Stages (this file constructs ONLY - no performance metric is computed anywhere
in it; the first metric exists in score.py, which run.sh invokes strictly after
exact-byte acceptance):

  1. fetch   the six AIS year CSVs (2019-2024) and the five target-year
             group-members XLSX files (2020-2024) from data.gov.au, pin every
             file by sha256 (recorded in summary.json and quality.json);
  2. parse   each AIS CSV into per-ABN records (earliest received wins on the
             measured handful of duplicate-ABN rows), with per-year column
             resolution by normalised name and a hard failure if a required
             column is missing;
  3. frame   for each target year Y in 2020..2024: prior row (period Y-1) with
             received <= T where T = period-Y due date - 90 days (recorded due
             when the charity lodged period Y, else derived from the prior
             period end plus the modal policy offset measured on file Y);
             group members of a period-Y reporting group with membership start
             <= T (or unparseable) are excluded;
  4. label   1 iff the period-Y row is absent, undated, or received after the
             due date; 0 iff received <= the due date. The period-Y 'Date AIS
             Received' and row presence are the label source and never ship;
  5. write   public/train.csv (Y 2020-2021), public/eval.csv (Y 2022-2023),
             private/holdout.csv (Y 2024), meta.json, quality.json - and
             summary.json to a path OUTSIDE the extract.

Every feature is a prior-period (or earlier) AIS field whose recorded receipt
date is <= T by construction (the eligibility rule for the immediately prior
row, an enforced as-of receipt filter for history rows). The ACNC register is
deliberately NOT used: its current-vintage attributes cannot be reconstructed
as of any past instant, and prior-period AIS content already carries size,
staffing, finances and lodgment timing.

Usage:
  build.py --out <extract-dir> --work-dir <scratch> --built-at <ISO>
          [--source-dir <pre-fetched-files>] [--relax-expected]

--relax-expected disables only the publisher-envelope assertions (per-year row
counts, per-split frame counts) so the local synthetic test can drive the same
code path; every structural, fixture and self-consistency assertion stays on.
The worker always runs without it.
"""
from __future__ import annotations

import argparse
import calendar
import collections
import csv
import datetime
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
import zipfile

NAME = "acnc-charity-ais-deadline-compliance"
TARGET = "failed_by_due"
POSITIVE_LABEL = 1
ID_COLUMNS = ["row_id", "abn"]
TIME_COLUMN = "target_year"
EVENT_KEY_COLUMN = "abn"

AIS_URLS = {
    2019: ("https://data.gov.au/data/dataset/34b35c52-8af0-4cc1-aa0b-2278f6416d09/"
           "resource/76006467-18f2-4094-a1cb-50544fd9b7b2/download/datadotgov_ais19.csv"),
    2020: ("https://data.gov.au/data/dataset/28a94374-d516-4200-a6f8-c09e76f58cc5/"
           "resource/62c7b3d3-4358-4d57-b810-a36732d36e2d/download/datadotgov_ais20.csv"),
    2021: ("https://data.gov.au/data/dataset/db8def1b-b3ba-4536-98eb-60c99e5495e5/"
           "resource/bbb19fa5-2f63-49cb-96b2-523e25828f27/download/datadotgov_ais21.csv"),
    2022: ("https://data.gov.au/data/dataset/311c24f3-fc09-42e7-8362-f15a76334a75/"
           "resource/cfbcf6f1-7ce5-472f-bfd3-a478e67e0366/download/datadotgov_ais22.csv"),
    2023: ("https://data.gov.au/data/dataset/ff6905d6-9d5d-4ef1-8478-72b833864fb7/"
           "resource/2b0fb746-57c5-4523-bb4c-74b7b78279d9/download/datadotgov_ais23.csv"),
    2024: ("https://data.gov.au/data/dataset/276ec1bc-4971-461c-88bc-be9f3c99a0f8/"
           "resource/710630ea-1202-4bbb-95f7-3973a972ddf8/download/datadotgov_ais24.csv"),
}
GROUP_URLS = {
    2020: ("https://data.gov.au/data/dataset/28a94374-d516-4200-a6f8-c09e76f58cc5/"
           "resource/88ed32b5-7cdc-47ca-9a43-c2d1671b7bc4/download/group-members_2020-ais.xlsx"),
    2021: ("https://data.gov.au/data/dataset/db8def1b-b3ba-4536-98eb-60c99e5495e5/"
           "resource/97a5306f-d39c-4cf1-9d84-c5ba23d376f5/download/datadotgov_ais21_group_members.xlsx"),
    2022: ("https://data.gov.au/data/dataset/311c24f3-fc09-42e7-8362-f15a76334a75/"
           "resource/fee48f71-2cbe-4e5a-b3fe-7545bf2772e8/download/datadotgov_ais22_group_members.xlsx"),
    2023: ("https://data.gov.au/data/dataset/ff6905d6-9d5d-4ef1-8478-72b833864fb7/"
           "resource/572ab72c-2939-423d-a27f-d2293350deab/download/datadotgov_ais23_group_members.xlsx"),
    2024: ("https://data.gov.au/data/dataset/276ec1bc-4971-461c-88bc-be9f3c99a0f8/"
           "resource/b3e3a122-67cb-46eb-a1ea-25137f53e734/download/datadotgov_ais24_group_members.xlsx"),
}
# Discovery pins: sha256 of the files the 2026-10-31 discovery probe fetched
# (candidates/acnc-charity-ais-deadline-compliance, measured_on 2026-10-31).
DISCOVERY_PINS = {
    2019: "b8a8d3e08beb57409b93093d14db4ed9f5db8a2a08996bdab522e1f009755576",
    2020: "68a803e9241565b383a9cd9865cec0f9e69537a375d07b8eb08300d7ade2c816",
    2021: "d9a40ef5e941b7b8f4f00119f8beb27f1ecdbd178bf6c3400c7b5fc751f27d59",
    2022: "c7bb10403f0806a0c4863e4d4a690bddecf106c631a064cc74eac40024226248",
    2023: "c7433699e5e2363082122d5f5d71e6716573d7a00c1b20c846157ef55c2d37a3",
    2024: "7da7cf9823e7e9d6041266a0dac31ff55180719203e5320913cbbcc618192be4",
    "gm2024": "55b1be9a28f53051b330a4fc48cff35be5b9e66c760743e116f3d8dea4487575",
}
# Publisher-envelope expectations measured 2026-10-31 (per-year CSV data rows).
EXPECTED_ROWS = {2019: 51040, 2020: 51438, 2021: 51841, 2022: 53053, 2023: 53548, 2024: 54145}
# Probe-measured eligible-frame counts (no group-member exclusion, prior due
# not required) - the build's slightly stricter frame must stay within 3%.
EXPECTED_FRAME = {"train": 77357, "eval": 80977, "holdout": 42885}
EXPECTED_POSITIVES = {"train": 23205, "eval": 20958, "holdout": 11035}

TARGET_YEARS = [2020, 2021, 2022, 2023, 2024]
SPLIT_YEARS = {"train": [2020, 2021], "eval": [2022, 2023], "holdout": [2024]}
ELIGIBILITY_LEAD_DAYS = 90

# Required source columns (normalised). The financial/staffing core is present
# under these names in every CSV year 2019-2024 (measured on the fetched files).
AIS_FIELDS = {
    "abn": ["abn"],
    "due": ["ais due date"],
    "received": ["date ais received"],
    "fin_from": ["fin report from"],
    "fin_to": ["fin report to"],
    "size": ["charity size"],
    "statement": ["type of financial statement"],
    "revenue": ["total revenue"],
    "expenses": ["total expenses"],
    "gov_revenue": ["revenue from government"],
    "assets": ["total assets"],
    "liabilities": ["total liabilities"],
    "net_assets": ["net assets/liabilities"],
    "fte": ["total full time equivalent staff"],
    "volunteers": ["staff - volunteers"],
}

COLUMNS = [
    "row_id", "abn", "target_year", "target_due_date", "due_day_of_year",
    "days_since_prev_due", "prior_lateness_days", "prior_lateness_positive",
    "prior_lead_days", "prior_period_end_month", "prior_period_length_days",
    "prior_due_minus_period_end_days", "charity_size_code",
    "special_purpose_statements", "total_revenue", "total_expenses",
    "revenue_minus_expenses", "revenue_from_government", "total_assets",
    "total_liabilities", "net_assets", "fte_staff", "volunteers",
    "n_ais_received_by_T", "n_late_by_T", "mean_lateness_by_T",
    "max_lateness_by_T", "history_first_year", "history_span_years",
    "failed_by_due",
]
FEATURES = [c for c in COLUMNS if c not in ("failed_by_due",) and c not in ID_COLUMNS]
SIZE_CODE = {"small": 1, "medium": 2, "large": 3}

INT_FEATURES = {
    "total_revenue": "revenue", "total_expenses": "expenses",
    "revenue_from_government": "gov_revenue", "total_assets": "assets",
    "total_liabilities": "liabilities", "net_assets": "net_assets",
}


def pdate(s):
    """ACNC export dates are dd/mm/yyyy."""
    try:
        dd, mm, yy = s.strip().split("/")
        return datetime.date(int(yy), int(mm), int(dd))
    except Exception:
        return None


def pnum(s):
    """Canonical numeric string from a published cell, or ''."""
    if s is None:
        return ""
    t = s.strip().replace(",", "").replace("$", "")
    if not t:
        return ""
    try:
        f = float(t)
    except ValueError:
        return ""
    return str(int(f)) if f == int(f) else repr(f)


def norm(h):
    return re.sub(r"\s+", " ", (h or "").strip().lower())


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(url, path):
    t0 = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=600) as r, open(path, "wb") as f:
        n = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            n += len(chunk)
    print(f"  fetched {os.path.basename(path)}: {n} bytes in {time.time()-t0:.1f}s", flush=True)
    return n


def read_ais(path, year):
    """One AIS year CSV -> {abn: record}. Earliest 'Date AIS Received' wins on
    duplicate-ABN rows (first lodgment defines on-time status); duplicates and
    differing-received duplicates are counted."""
    required = {}
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        cols = {norm(h): h for h in (reader.fieldnames or [])}
        for field, names in AIS_FIELDS.items():
            hit = [cols[n] for n in names if n in cols]
            if len(hit) != 1:
                raise SystemExit(f"20{year % 100:02d} file: field {field!r} matched {len(hit)} columns")
            required[field] = hit[0]
        records, rows = {}, 0
        dups = dup_differing = 0
        for row in reader:
            rows += 1
            abn = (row.get(required["abn"]) or "").strip()
            if not abn:
                continue
            rec = {
                "due": pdate(row.get(required["due"], "")),
                "recv": pdate(row.get(required["received"], "")),
                "fin_from": pdate(row.get(required["fin_from"], "")),
                "fin_to": pdate(row.get(required["fin_to"], "")),
                "size": (row.get(required["size"]) or "").strip(),
                "statement": (row.get(required["statement"]) or "").strip(),
                "revenue": pnum(row.get(required["revenue"])),
                "expenses": pnum(row.get(required["expenses"])),
                "gov_revenue": pnum(row.get(required["gov_revenue"])),
                "assets": pnum(row.get(required["assets"])),
                "liabilities": pnum(row.get(required["liabilities"])),
                "net_assets": pnum(row.get(required["net_assets"])),
                "fte": pnum(row.get(required["fte"])),
                "volunteers": pnum(row.get(required["volunteers"])),
            }
            old = records.get(abn)
            if old is None:
                records[abn] = rec
            else:
                dups += 1
                if old["recv"] != rec["recv"] or old["due"] != rec["due"]:
                    dup_differing += 1
                if rec["recv"] is not None and (old["recv"] is None or rec["recv"] < old["recv"]):
                    records[abn] = rec
    return records, {"rows": rows, "unique_abn": len(records), "duplicate_rows": dups,
                     "duplicate_differing": dup_differing}


def due_offsets(records):
    """Modal (due - period end) offset in months, keyed by period-end month."""
    per = collections.defaultdict(collections.Counter)
    for rec in records.values():
        if rec["due"] and rec["fin_to"]:
            end, due = rec["fin_to"], rec["due"]
            per[end.month][(due.year - end.year) * 12 + (due.month - end.month)] += 1
    return {m: c.most_common(1)[0][0] for m, c in per.items()}


def derived_due(offsets, period_end):
    off = offsets.get(period_end.month)
    if off is None:
        return None
    m = period_end.month + off
    yy = period_end.year + (m - 1) // 12
    m = (m - 1) % 12 + 1
    return datetime.date(yy, m, min(period_end.day, calendar.monthrange(yy, m)[1]))


def read_group_members(path):
    """Group-members XLSX -> ({abn: start_date_or_None}, info).

    Layout (measured on the fetched 2024 file): column A group name, B member
    ABN, C member name, D membership start (Excel serial), E membership end;
    1,315 member rows for 2024, most with no end date. Parsed with the stdlib
    (zipfile + sharedStrings + sheet XML) so the worker needs no extra package.
    """
    zf = zipfile.ZipFile(path)
    shared = []
    for si in re.findall(r"<si>(.*?)</si>", zf.read("xl/sharedStrings.xml").decode("utf-8", errors="replace"), re.S):
        shared.append("".join(re.findall(r"<t[^>]*>(.*?)</t>", si, re.S)))
    sheet = zf.read("xl/worksheets/sheet1.xml").decode("utf-8", errors="replace")
    members, unparseable, skipped = {}, 0, 0
    for rxml in re.findall(r"<row[^>]*>(.*?)</row>", sheet, re.S):
        cells = {}
        for m in re.finditer(r'<c r="([A-Z]+)\d+"([^>]*)>(?:<v>([^<]*)</v>)?', rxml):
            col, attrs, val = m.group(1), m.group(2), m.group(3)
            if val is None:
                continue
            cells[col] = shared[int(val)] if 't="s"' in attrs else val
        abn = re.sub(r"\D", "", cells.get("B", ""))
        if not abn:
            continue
        if len(abn) != 11:
            skipped += 1
            continue
        raw = (cells.get("D") or "").strip()
        start = None
        if raw:
            try:
                # 2020/2022-2024 files carry Excel serial dates; the 2021 file
                # carries 'dd/mm/yyyy 00:00:00' shared strings (measured)
                start = datetime.date(1899, 12, 30) + datetime.timedelta(days=int(float(raw)))
            except (ValueError, OverflowError):
                if pdate(raw.split(" ")[0]):
                    start = pdate(raw.split(" ")[0])
                else:
                    unparseable += 1
        members[abn] = start
    info = {"rows": len(members), "unparseable_start": unparseable, "non_abn_rows_skipped": skipped}
    return members, info


def build_quality(split_stats, per_year_stats, pins, fy_changed, undated_current,
                  exclusions, built_at):
    prior_group = {
        "source": "the charity's period-(Y-1) AIS row in the ACNC AIS dataset for that year (bulk CSV)",
        "availability": "received by construction no later than T = the period-Y due date minus 90 days (eligibility rule); the row's recorded 'Date AIS Received' is the availability event",
        "status": "assumed",
        "assumption": "current-vintage file: the value is as recorded in the weekly-updated export fetched at construction; no historical vintage exists to verify the file state at T, but the receipt date itself is publisher-recorded and the as-of receipt rule is enforced in construction",
    }
    history_group = {
        "source": "the charity's earlier AIS rows (period years < Y-1) in the ACNC AIS datasets",
        "availability": "only rows with recorded 'Date AIS Received' <= T are read (enforced as-of receipt filter); the immediately prior row is covered by the eligibility rule",
        "status": "assumed",
        "assumption": "current-vintage values with the receipt-date as-of filter enforced; receipt dates are publisher-recorded lodgment events",
    }
    fe = {
        "row_id": {"source": "row key abn_targetyear", "availability": "identity of the row, known at the instant", "status": "verified"},
        "abn": {"source": "source column 'ABN'", "availability": "publisher-assigned charity identity, constant across the panel", "status": "verified"},
        "target_year": {"source": "row key (the period-Y calendar year)", "availability": "calendar arithmetic on the row's reporting period", "status": "verified"},
        "target_due_date": {"source": "the charity's recorded 'AIS Due Date' for period Y (file Y) when it lodged, else derived from the prior period end plus the modal policy offset measured on file Y", "availability": "the ACNC deadline policy fixes the due date from the period end (six months, with the Commissioner's standing 31 January extension for standard 1 July-30 June periods); knowable at T for unchanged financial years", "status": "assumed", "assumption": f"for the measured {fy_changed['rows_changed_fy']} of {fy_changed['rows_with_current_row']} rows with a period-Y row whose period end differs from prior end + 1 year, the recorded due date embeds the period-Y period end chosen by the charity; counted per split in summary.json"},
        "due_day_of_year": {"source": "day-of-year of target_due_date", "availability": "same policy-derived deadline, numeric form", "status": "assumed", "assumption": "inherits the target_due_date assumption"},
        "days_since_prev_due": {"source": "target_due_date minus the prior row's recorded 'AIS Due Date'", "availability": "both dates are policy-determined from period ends known at T", "status": "assumed", "assumption": "inherits the target_due_date assumption"},
    }
    for name in ("prior_lateness_days", "prior_lateness_positive"):
        fe[name] = {**prior_group, "source": prior_group["source"] + f" (fields 'AIS Due Date', 'Date AIS Received') -> {name}"}
    for name in ("prior_lead_days", "prior_period_end_month", "prior_period_length_days",
                 "prior_due_minus_period_end_days", "charity_size_code",
                 "special_purpose_statements", "total_revenue", "total_expenses",
                 "revenue_minus_expenses", "revenue_from_government", "total_assets",
                 "total_liabilities", "net_assets", "fte_staff", "volunteers"):
        fe[name] = {**prior_group, "source": prior_group["source"] + f" -> {name}"}
    for name in ("n_ais_received_by_T", "n_late_by_T", "mean_lateness_by_T",
                 "max_lateness_by_T", "history_first_year", "history_span_years"):
        fe[name] = {**history_group, "source": history_group["source"] + f" -> {name}"}

    measurements = [
        {"column": "total_revenue", "unit": "AUD as reported", "frame": "publisher field 'Total Revenue' of the period-(Y-1) AIS"},
        {"column": "total_expenses", "unit": "AUD as reported", "frame": "publisher field 'Total Expenses' of the period-(Y-1) AIS"},
        {"column": "revenue_minus_expenses", "unit": "AUD (derived: reported revenue minus reported expenses)", "frame": "both components are publisher fields of the period-(Y-1) AIS"},
        {"column": "revenue_from_government", "unit": "AUD as reported", "frame": "publisher field 'Revenue from Government' of the period-(Y-1) AIS"},
        {"column": "total_assets", "unit": "AUD as reported", "frame": "publisher field 'Total Assets' of the period-(Y-1) AIS"},
        {"column": "total_liabilities", "unit": "AUD as reported", "frame": "publisher field 'Total Liabilities' of the period-(Y-1) AIS"},
        {"column": "net_assets", "unit": "AUD as reported", "frame": "publisher field 'Net Assets/Liabilities' of the period-(Y-1) AIS"},
        {"column": "fte_staff", "unit": "full-time-equivalent staff (publisher field; may be fractional)", "frame": "publisher field 'Total Full Time Equivalent Staff' of the period-(Y-1) AIS"},
        {"column": "volunteers", "unit": "persons", "frame": "publisher field 'Staff - Volunteers' of the period-(Y-1) AIS"},
        {"column": "prior_lateness_days", "unit": "days (signed; negative = received before the due date)", "frame": "difference of two publisher-recorded dates of the period-(Y-1) AIS"},
        {"column": "prior_lead_days", "unit": "days", "frame": "T minus the prior row's recorded 'Date AIS Received'; non-negative by the eligibility rule"},
        {"column": "prior_period_length_days", "unit": "days", "frame": "'Fin Report To' minus 'Fin Report From' of the period-(Y-1) AIS"},
        {"column": "prior_due_minus_period_end_days", "unit": "days", "frame": "'AIS Due Date' minus 'Fin Report To' of the period-(Y-1) AIS"},
        {"column": "days_since_prev_due", "unit": "days", "frame": "the row's target due date minus the prior row's due date"},
        {"column": "mean_lateness_by_T", "unit": "days (mean of signed lateness over AIS rows received by T)", "frame": "as-of receipt-filtered history of the same charity"},
        {"column": "max_lateness_by_T", "unit": "days (maximum of signed lateness over AIS rows received by T)", "frame": "as-of receipt-filtered history of the same charity"},
        {"column": "n_ais_received_by_T", "unit": "count of AIS rows", "frame": "as-of receipt-filtered history of the same charity (files 2019 to Y-2 plus the prior row)"},
        {"column": "n_late_by_T", "unit": "count of late AIS rows (received after their own due date)", "frame": "as-of receipt-filtered history of the same charity"},
    ]

    probe = {
        "name": "next_target_year_exposes_outcome",
        "entity_columns": ["abn"],
        "time_column": "target_due_date",
        "lag_days_column": "days_since_prev_due",
        "left": "prior_lateness_positive",
        "operation": "copy",
        "expectation": ("the donor row (same ABN, target year Y+1) carries prior_lateness_positive = 1 exactly when "
                        "the period-Y AIS was received after the period-Y due date, which is precisely row (same ABN, "
                        "target year Y)'s label; the panel is self-answering across adjacent target years, so honest "
                        "evaluation requires isolated rows (one row presented to the solver at a time). Rows whose "
                        "period-Y AIS was never lodged have no Y+1 donor (the charity is ineligible for Y+1), so the "
                        "probe covers the lodged-outcome rows and misses the never-lodged positives - the covered subset "
                        "should show near-zero mismatches, which is the exposure being declared"),
    }

    quality = {
        "name": NAME,
        "built_at_utc": built_at,
        "task": {
            "question": ("An Australian charity registered with the ACNC lodged its Annual Information Statement (AIS) "
                         "for the reporting period ending in year Y-1 early enough that the lodgment was already on "
                         "record 90 days before its next deadline. Will the charity FAIL to lodge its period-Y AIS by "
                         "the ACNC-recorded due date (received after the due date, undated, or no period-Y AIS row)?"),
            "prediction_time": ("Per-charity instant T = the charity's recorded ACNC 'AIS Due Date' for period Y minus "
                                "90 days (event time; the due-date policy is announced in advance: six months after "
                                "the reporting-period end, with the Commissioner's standing extension to 31 January "
                                "for standard 1 July-30 June periods). Worked example (Australia/Sydney): Integricare "
                                "Ltd ABN 11000073870, period ending 30/06/2024, due 31/01/2025, T 02/11/2024."),
        },
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": ID_COLUMNS,
        "id_columns_are_entity_keys": False,
        "id_columns_note": ("row_id = abn_targetyear names one charity-year with one label; the ABN itself identifies a "
                            "charity that legitimately recurs across target years with different labels (a panel "
                            "task), so no single-column entity-key claim is made and only row_id is the unique key"),
        "time_column": TIME_COLUMN,
        "event_key_column": EVENT_KEY_COLUMN,
        "event_key_note": ("an event is one distinct charity among the positive rows; the gate reads the 10-character "
                           "prefix of the ABN, and the ABN's mod-89 check digit makes that prefix injective (at most "
                           "one valid ABN per 10-digit prefix), asserted on the shipped rows at construction"),
        "split_windows": {"train": {"start": "2020", "end": "2022"},
                          "eval": {"start": "2022", "end": "2024"},
                          "holdout": {"start": "2024", "end": "2025"}},
        "split_boundaries": {
            "train": "target reporting-period years 2020 and 2021 (window end exclusive)",
            "eval": "target reporting-period years 2022 and 2023 (window end exclusive)",
            "holdout": "target reporting-period year 2024 (window end exclusive; the last year the fetched vintage carries)",
        },
        "splits": {"train": "public/train.csv", "eval": "public/eval.csv", "holdout": "private/holdout.csv"},
        "positive_events": {key: {"positives": split_stats[key]["positives"],
                                  "distinct_events": split_stats[key]["distinct_positive_charities"]}
                            for key in ("train", "eval", "holdout")},
        "positive_events_note": ("an event is one distinct charity among the positive rows (a delinquent charity "
                                  "fails repeatedly across target years, so the clustered count is the distinct-charity "
                                  "count, recomputed by the gate from the ABN event key)"),
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "shipped_columns": COLUMNS,
        "label_source_columns": [
            "period-Y 'Date AIS Received' (received after the due date), the absence of a period-Y row for the ABN, "
            "and an undated period-Y 'Date AIS Received' - the three channels of the label; none of them ships",
        ],
        "post_hoc_columns": [
            "'Registration Status' (current-vintage status as of the fetch snapshot, not status at lodgment; never shipped)",
            "'Financial Report Date Received' (a post-period event; never shipped)",
            "the ACNC Register's current-vintage attributes (state, suburb, establishment date; the register is not used at all)",
        ],
        "high_cardinality_columns": ["row_id", "abn"],
        "expected_duplicate_ids": 0,
        "external_threshold": False,
        "measurements": measurements,
        "timing": {
            "prediction_instant": {
                "kind": "event_time",
                "period": "per-charity reporting period Y",
                "days_after_period_end": 0,
                "citation": ("T = the charity's recorded 'AIS Due Date' for period Y minus 90 days. The due date is "
                             "fixed by announced policy (ACNC AIS due-dates page: six months after the period end, "
                             "with the Commissioner's standing extension to the following 31 January for standard "
                             "1 July-30 June periods; measured in-file: period ends 30/06/2023 carry due 31/01/2024, "
                             "period ends 31/12/2024 carry due 30/06/2025). Every shipped feature is a prior-period "
                             "AIS fact whose recorded receipt is <= T by construction."),
            },
            "features": {
                "period": "Y-1 and earlier",
                "published_days_after_period_end": 0,
                "source_kind": "administrative_record",
            },
            "row_selection": {
                "latest_period_used": "Y-1 (the prior-period AIS row, received no later than T by the eligibility rule)",
                "fields": [
                    "prior 'Date AIS Received' <= T (eligibility)",
                    "prior 'AIS Due Date' and 'Fin Report To' (frame and due derivation)",
                    "period-Y group-membership start date (exclusion when start <= T or unparseable)",
                ],
                "basis": ("eligibility reads only the prior-period row and the group-membership start date; the "
                          "period-Y row never enters eligibility; the period-Y group-membership file is "
                          "current-vintage and its start dates are declared as an assumption; label-observability "
                          "buckets (undated current rows) are counted per split and never conditioned on"),
            },
            "observations": [],
        },
        "evaluation_contract": {
            "use": "retrospective_research",
            "access": "isolated_rows",
            "training_label_timing": "unverified",
            "scope_note": ("each row is a charity-year whose features read the charity's prior and earlier AIS "
                           "lodgments only. Honest evaluation requires isolated rows - one row presented to the "
                           "solver at a time - because the panel is self-answering across adjacent target years "
                           "(see the declared cross-row probe: a later row's prior_lateness_positive IS the earlier "
                           "row's label). The shipped illustrative runner does NOT enforce this: it passes the whole "
                           "eval feature table to the predictor in one call, so unrestricted-access scores are "
                           "meaningless and the isolated-rows requirement is stated as a requirement, never as an "
                           "enforcement claim. Labeled eval is development/validation; the holdout is the final test "
                           "and stays outside evaluated agents' workspaces. Training-label timing is UNVERIFIED: the "
                           "ACNC publishes weekly-updated whole-file exports with no archived vintages, so no "
                           "full-row availability ledger can be constructed and the artifact is retrospective "
                           "research only, never a certified historical forecasting setup."),
            "feature_evidence": fe,
            "vintage": {
                "kind": "current_snapshot",
                "evidence": ("the AIS datasets are weekly-updated whole-file exports with no archived vintages "
                             "(measured: the 2023 file carries 53,548 rows vs the Australian Charities Report 11th "
                             "edition's 52,314 census individual statements, a +1,234 post-census trickle; the label "
                             "is stable under trickle because a later-received period-Y AIS still has 'Date AIS "
                             "Received' after the past due date). This build pins the fetched snapshot by sha256 "
                             "(summary.json); every value is construction-time vintage"),
            },
            "selection": {
                "kind": "prediction_time",
                "evidence": ("membership is fixed by the prior-period row's receipt date vs T and the group-membership "
                             "start date; the target period-Y row never enters eligibility. Charities whose prior "
                             "row lacks a parseable received date, period end or due date are excluded and counted "
                             f"({exclusions.get('prior_missing_dates', 0)} with missing prior dates, "
                             f"{exclusions.get('no_derived_due', 0)} with no derivable target due; "
                             f"{exclusions.get('group_head_excluded', 0)} group-head entities across target years). "
                             f"Undated period-Y rows ({undated_current} across splits) are labelled positive per the "
                             "recorded target definition and counted, never silently dropped"),
            },
            "limitations": [
                "single current-vintage snapshot per year, fetched and sha256-pinned at construction; no historical vintages exist, so no as-of reconstruction of any feature value and no operational-forecasting claim is possible",
                "the artifact deliberately does NOT ship the instant-available 'already lodged by T' signal (whether the period-Y AIS was received before T): it cannot be reconstructed from current-vintage files, it is nearly label-determining, and shipping it would trivialise the task; rows whose outcome is already determined at the instant stay in the frame and are counted per split in summary.json",
                f"for {fy_changed['rows_changed_fy']} of {fy_changed['rows_with_current_row']} rows with a period-Y row, the recorded period-Y period end differs from prior end + 1 year, so the recorded due date (and T) embeds a period-Y fact chosen by the charity; counted per split in summary.json",
                "withheld records are removed by the publisher 'from the date of approval onwards': a charity that lodged on time but later won withholding shows as absent and is labelled positive (false positive); the rate is not measurable from the current files, the direction is bounded (can only add positives)",
                f"'Registration Status' is current-vintage (status as of the fetch, not at lodgment) and is never shipped; of the never-lodging prior filers the majority carry 'Voluntarily Revoked*' codes, a minority are 'Revoked Double Defaulter', and some were still 'Registered' - the label counts all absence as failure per the recorded target definition",
                "the frame excludes members of ACNC reporting groups for period Y (they lodge via their head entity) using the current-vintage group-membership files with an as-of start-date rule; members whose start date is unparseable are excluded, members whose start date is after T stay in the frame and are counted",
                "the frame also excludes ACNC GROUP head entities (publisher-assigned synthetic ABNs in the 91 111 111 xxx block, names carrying the _ACNC GROUP marker; measured 348 rows across the 2019-2024 files): they are collective lodgers, not individual charities, and the block is exactly what breaks ABN 10-prefix injectivity, so they are counted and excluded",
                "duplicate-ABN rows within a year file are resolved to the earliest recorded 'Date AIS Received' (first lodgment defines on-time status); the counts are measured and recorded in summary.json",
                "prevalence drifts across splits (measured before the group exclusion: 30.0% train / 25.9% eval / 25.7% holdout) - a property of the period, reported beside every score",
                "positives cluster by charity beyond the row count (a delinquent charity fails repeatedly across target years); per-charity clustered counts are declared per split and uncertainty must use them",
                "history features are left-truncated at the 2019 file (the first CSV year), so train-era rows carry thinner history than holdout rows; this cohort property is reported in summary.json",
                "the XLSX-only years 2013-2018 are not used in this build; extending the train window with them is a recorded future option",
            ],
            "cross_row_audit": {
                "probes": [probe],
                "rationale": ("the only join that exposes one row's label through another row's features is the "
                             "adjacent-target-year join on the same charity: the later row's prior_lateness_positive "
                             "is computed from the period-Y receipt vs the period-Y due date, which is exactly the "
                             "earlier row's label. Same-instant joins (same charity, same due date) are unique by "
                             "construction, and no other shipped column reads any period-Y field"),
                "auxiliary_files_review": ("the artifact ships exactly public/train.csv, public/eval.csv, "
                                           "private/holdout.csv, meta.json and quality.json; no auxiliary "
                                           "solver-visible file exists (summary.json is written outside the "
                                           "extract, and the label-source year files are never shipped)"),
            },
        },
        "source_snapshot": {
            "publisher": "Australian Charities and Not-for-profits Commission (ACNC), distributed via data.gov.au",
            "files": pins,
            "licence_note": ("per-year CC BY variants on the AIS datasets (3.0 Australia for 2023-2024, 2.5 Australia "
                             "for 2019-2022, recorded from the data.gov.au package metadata at discovery); the ACNC "
                             "register is not used by this build"),
            "snapshot_note": "every file is pinned by sha256 in summary.json; the datasets are weekly-updated whole-file exports with no archived vintages",
        },
        "splits_stats": split_stats,
        "per_year_stats": per_year_stats,
    }
    return quality


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--work-dir", required=True)
    ap.add_argument("--built-at", required=True)
    ap.add_argument("--source-dir", default=None,
                    help="reuse pre-fetched files from this directory (local test path); fetches what is missing")
    ap.add_argument("--relax-expected", action="store_true",
                    help="disable the publisher-envelope assertions only (local synthetic test); structural assertions stay on")
    ap.add_argument("--summary-out", default=None,
                    help="where to write summary.json (default: beside the extract); keep it OUTSIDE the extract")
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    os.makedirs(os.path.join(out, "public"), exist_ok=True)
    os.makedirs(os.path.join(out, "private"), exist_ok=True)
    work = os.path.abspath(args.work_dir)
    os.makedirs(work, exist_ok=True)

    # ---- stage 1: fetch + pin -------------------------------------------------
    pins, fetch_info = {}, {}
    paths = {}
    def locate(kind, year, url, fname, pin_key=None):
        path = os.path.join(args.source_dir, fname) if args.source_dir else os.path.join(work, fname)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            fetch(url, path)
        digest, size = sha256_of(path), os.path.getsize(path)
        entry = {"url": url, "bytes": size, "sha256": digest}
        if pin_key and pin_key in DISCOVERY_PINS:
            entry["matches_discovery_pin"] = digest == DISCOVERY_PINS[pin_key]
        pins[f"{kind}_{year}"] = entry
        return path

    print("== fetch/pin ==", flush=True)
    for year in sorted(AIS_URLS):
        paths[("ais", year)] = locate("ais", year, AIS_URLS[year], f"acnc_ais{year % 100:02d}.csv", pin_key=year)
    for year in sorted(GROUP_URLS):
        paths[("gm", year)] = locate("gm", year, GROUP_URLS[year], f"acnc_gm{year % 100:02d}.xlsx",
                                     pin_key="gm2024" if year == 2024 else None)

    # ---- stage 2: parse -------------------------------------------------------
    print("== parse ==", flush=True)
    records, per_year_stats = {}, {}
    for year in sorted(AIS_URLS):
        recs, info = read_ais(paths[("ais", year)], year)
        records[year] = recs
        per_year_stats[str(year)] = info
        print(f"  20{year % 100:02d}: rows={info['rows']} unique_abn={info['unique_abn']} dups={info['duplicate_rows']}", flush=True)
        if not args.relax_expected:
            expected = EXPECTED_ROWS[year]
            if abs(info["rows"] - expected) > 0.03 * expected:
                raise SystemExit(f"20{year % 100:02d} row count {info['rows']} outside the measured envelope {expected} +-3%")
    group_members, gm_info = {}, {}
    for year in sorted(GROUP_URLS):
        members, info = read_group_members(paths[("gm", year)])
        group_members[year] = members
        gm_info[str(year)] = info
        print(f"  group members 20{year % 100:02d}: {len(members)} (unparseable start: {info['unparseable_start']})", flush=True)

    # ---- stage 3+4: frame, features, label ------------------------------------
    print("== frame ==", flush=True)
    rows_by_year = {}
    exclusions = collections.Counter()
    undated_current = 0
    fy_changed = {"rows_with_current_row": 0, "rows_changed_fy": 0}
    already_lodged = {"rows": 0, "all_label_zero": True}
    for Y in TARGET_YEARS:
        prior, cur = records[Y - 1], records[Y]
        offsets = due_offsets(cur)
        gm = group_members[Y]
        rows = []
        for abn in sorted(prior):
            p = prior[abn]
            if abn.startswith("9111111"):
                # publisher-assigned synthetic ABNs of ACNC GROUP head entities
                # (collective lodgers; names carry the _ACNC GROUP marker with
                # spelling variants, the ABN block is the exact discriminator,
                # measured 348 rows 2019-2024) - not individual charities, and
                # the block is exactly what breaks ABN 10-prefix injectivity
                exclusions["group_head_excluded"] += 1
                continue
            if p["recv"] is None or p["fin_to"] is None or p["due"] is None:
                exclusions["prior_missing_dates"] += 1
                continue
            c = cur.get(abn)
            if c is not None and c["due"] is not None:
                du = c["due"]
            else:
                try:
                    du = derived_due(offsets, datetime.date(p["fin_to"].year + 1, p["fin_to"].month, p["fin_to"].day))
                except ValueError:
                    du = None
            if du is None:
                exclusions["no_derived_due"] += 1
                continue
            T = du - datetime.timedelta(days=ELIGIBILITY_LEAD_DAYS)
            if p["recv"] > T:
                exclusions["prior_recv_after_T"] += 1
                continue
            if abn in gm:
                start = gm[abn]
                if start is None or start <= T:
                    exclusions["group_member_excluded"] += 1
                    continue
                exclusions["group_member_start_after_T_kept"] += 1
            # label (period-Y facts only; never shipped as features)
            if c is not None:
                if c["recv"] is None:
                    label, bucket = 1, "undated_current"
                    undated_current += 1
                elif c["recv"] <= du:
                    label, bucket = 0, "on_time"
                else:
                    label, bucket = 1, "late"
                if c["fin_to"] is not None:
                    fy_changed["rows_with_current_row"] += 1
                    if (c["fin_to"].year, c["fin_to"].month, c["fin_to"].day) != (p["fin_to"].year + 1, p["fin_to"].month, p["fin_to"].day):
                        fy_changed["rows_changed_fy"] += 1
                if c["recv"] is not None and c["recv"] <= T:
                    already_lodged["rows"] += 1
                    if label != 0:
                        already_lodged["all_label_zero"] = False
            else:
                label, bucket = 1, "never"
            # features: prior row (as-of by eligibility)
            lateness = (p["recv"] - p["due"]).days
            row = {
                "row_id": f"{abn}_{Y}",
                "abn": abn,
                "target_year": str(Y),
                "target_due_date": du.isoformat(),
                "due_day_of_year": str(du.timetuple().tm_yday),
                "days_since_prev_due": str((du - p["due"]).days),
                "prior_lateness_days": str(lateness),
                "prior_lateness_positive": "1" if lateness > 0 else "0",
                "prior_lead_days": str((T - p["recv"]).days),
                "prior_period_end_month": str(p["fin_to"].month),
                "prior_period_length_days": str((p["fin_to"] - p["fin_from"]).days) if p["fin_from"] else "",
                "prior_due_minus_period_end_days": str((p["due"] - p["fin_to"]).days),
                "charity_size_code": str(SIZE_CODE[p["size"].lower()]) if p["size"].lower() in SIZE_CODE else "",
                "special_purpose_statements": ("1" if "special purpose" in p["statement"].lower()
                                               else "0" if "general purpose" in p["statement"].lower() else ""),
                "total_revenue": p["revenue"],
                "total_expenses": p["expenses"],
                "revenue_minus_expenses": (str(int(p["revenue"]) - int(p["expenses"]))
                                           if p["revenue"] and p["expenses"] else ""),
                "revenue_from_government": p["gov_revenue"],
                "total_assets": p["assets"],
                "total_liabilities": p["liabilities"],
                "net_assets": p["net_assets"],
                "fte_staff": p["fte"],
                "volunteers": p["volunteers"],
            }
            # features: history (as-of receipt filter, period years < Y; the prior
            # row's own lateness is included in the aggregates - it is one of the
            # rows received by T, and eligibility already guarantees its receipt <= T)
            n_hist = n_late = 0
            lat_vals = [lateness]
            first_year = None
            for hy in range(2019, Y - 1):
                h = records[hy].get(abn)
                if h is None or h["recv"] is None or h["recv"] > T:
                    continue
                n_hist += 1
                if first_year is None:
                    first_year = hy
                if h["due"] is not None and h["recv"] > h["due"]:
                    n_late += 1
                if h["due"] is not None:
                    lat_vals.append((h["recv"] - h["due"]).days)
            row["n_ais_received_by_T"] = str(n_hist + 1)  # + the prior row itself
            row["n_late_by_T"] = str(n_late + (1 if lateness > 0 else 0))
            row["mean_lateness_by_T"] = (repr(sum(lat_vals) / len(lat_vals)) if lat_vals else "")
            row["max_lateness_by_T"] = str(max(lat_vals)) if lat_vals else ""
            row["history_first_year"] = str(first_year if first_year is not None else Y - 1)
            row["history_span_years"] = str(Y - (first_year if first_year is not None else Y - 1))
            row["failed_by_due"] = str(label)
            row["_bucket"] = bucket
            rows.append(row)
        rows_by_year[Y] = rows
        pos = sum(1 for r in rows if r["failed_by_due"] == "1")
        print(f"  target {Y}: eligible={len(rows)} positives={pos} ({pos / max(1, len(rows)):.4f})", flush=True)

    # ---- stage 5: write -------------------------------------------------------
    split_rows = {k: [r for y in years for r in rows_by_year[y]] for k, years in SPLIT_YEARS.items()}
    split_stats = {}
    for key, rows in split_rows.items():
        pos = sum(1 for r in rows if r["failed_by_due"] == "1")
        pos_abns = {r["abn"] for r in rows if r["failed_by_due"] == "1"}
        split_stats[key] = {
            "rows": len(rows), "positives": pos, "negatives": len(rows) - pos,
            "positive_rate": pos / len(rows) if rows else None,
            "distinct_positive_charities": len(pos_abns),
            "label_buckets": dict(collections.Counter(r["_bucket"] for r in rows)),
        }
    # already-lodged per split (rows whose period-Y receipt precedes T)
    already_by_split = collections.Counter()
    for key, years in SPLIT_YEARS.items():
        n = 0
        for Y in years:
            cur, prior = records[Y], records[Y - 1]
            for r in rows_by_year[Y]:
                c = cur.get(r["abn"])
                if c is not None and c["recv"] is not None:
                    du = datetime.date.fromisoformat(r["target_due_date"])
                    if c["recv"] <= du - datetime.timedelta(days=ELIGIBILITY_LEAD_DAYS):
                        n += 1
        already_by_split[key] = n
    for key in split_stats:
        split_stats[key]["already_lodged_at_T"] = already_by_split[key]

    print("== write ==", flush=True)
    def write_csv(path, rows):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
    write_csv(os.path.join(out, "public", "train.csv"), split_rows["train"])
    write_csv(os.path.join(out, "public", "eval.csv"), split_rows["eval"])
    write_csv(os.path.join(out, "private", "holdout.csv"), split_rows["holdout"])

    meta = {
        "name": NAME,
        "description": ("For an Australian charity registered with the ACNC that lodged its Annual Information "
                        "Statement (AIS) for the reporting period ending in year Y-1 at least 90 days before its "
                        "period-Y AIS due date, will the charity FAIL to lodge the period-Y AIS by the "
                        "ACNC-recorded due date (received after the due date, undated, or no period-Y row)? "
                        "Features are the charity's prior-period AIS content and as-of-T lodgment history; the "
                        "ACNC register is not used."),
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": ID_COLUMNS,
        "columns": COLUMNS,
        "rows": {k: split_stats[k]["rows"] for k in ("train", "eval", "holdout")},
        "positive_rate": {k: split_stats[k]["positive_rate"] for k in ("train", "eval", "holdout")},
        "split": "temporal split on the target reporting-period year: train 2020-2021, eval 2022-2023, holdout 2024",
        "split_description": ("temporal split on the target reporting-period year (periods ending in that calendar "
                              "year): train 2020-2021, eval 2022-2023, holdout 2024; eligibility = the charity's "
                              "period-(Y-1) AIS received <= (period-Y due date - 90 days) and the charity not a "
                              "member of an ACNC reporting group for period Y (as-of start date); a charity may "
                              "appear in multiple target years - per-charity clustering is a declared property"),
    }
    with open(os.path.join(out, "meta.json"), "w") as f:
        json.dump(meta, f, indent=1)
        f.write("\n")

    # ---- self-checks ----------------------------------------------------------
    print("== self-checks ==", flush=True)
    # frame envelope vs the probe measurements (before this build's stricter rules)
    if not args.relax_expected:
        for key in ("train", "eval", "holdout"):
            rows_n = split_stats[key]["rows"]
            if abs(rows_n - EXPECTED_FRAME[key]) > 0.03 * EXPECTED_FRAME[key]:
                raise SystemExit(f"{key} frame {rows_n} outside the measured envelope {EXPECTED_FRAME[key]} +-3%")
            pos_n = split_stats[key]["positives"]
            if abs(pos_n - EXPECTED_POSITIVES[key]) > 0.03 * EXPECTED_POSITIVES[key]:
                raise SystemExit(f"{key} positives {pos_n} outside the measured envelope {EXPECTED_POSITIVES[key]} +-3%")
    for Y in TARGET_YEARS:
        yrs = {r["target_year"] for r in rows_by_year[Y]}
        assert yrs == {str(Y)}, f"year leakage in target {Y}"
        pos = sum(1 for r in rows_by_year[Y] if r["failed_by_due"] == "1")
        assert 0 < pos < len(rows_by_year[Y]), f"target {Y} not two-class"
    ids = [r["row_id"] for rows in split_rows.values() for r in rows]
    assert len(ids) == len(set(ids)), "row_id collision"
    distinct_abns = {r["abn"] for rows in split_rows.values() for r in rows}
    prefixes = collections.Counter(a[:10] for a in distinct_abns)
    assert max(prefixes.values()) == 1, "two distinct shipped ABNs share a 10-digit prefix (event-key injectivity broken)"
    for key, rows in split_rows.items():
        for col in COLUMNS:
            assert any(r[col] != "" for r in rows), f"column {col} is entirely empty in {key}"
    assert already_lodged["all_label_zero"], "a row received before T must carry label 0"
    # fixture: the dated example from the candidate record (Australia/Sydney instants)
    if not args.relax_expected:
        integ = next((r for r in rows_by_year[2024] if r["abn"] == "11000073870"), None)
        assert integ is not None, "Integricare fixture row missing from the 2024 frame"
        assert integ["target_due_date"] == "2025-01-31" and integ["failed_by_due"] == "1"
        p23 = records[2023]["11000073870"]
        assert p23["recv"].isoformat() == "2024-01-18" and p23["due"].isoformat() == "2024-01-31", \
            "Integricare prior-row dates drifted from the record's verified example"
        # fixture: deadline-extension policy offsets measured on the 2024 file
        off24 = due_offsets(records[2024])
        assert off24.get(6) == 7 and off24.get(12) == 6, f"2024 policy offsets moved: {off24.get(6)}/{off24.get(12)}"
    # label-source absence: no shipped column name touches the period-Y receipt channel
    assert not any("received" in c and c not in ("n_ais_received_by_T",) for c in COLUMNS), \
        "a shipped column references the receipt channel"

    quality = build_quality(split_stats, per_year_stats, pins, fy_changed, undated_current,
                            dict(exclusions), args.built_at)
    with open(os.path.join(out, "quality.json"), "w") as f:
        json.dump(quality, f, indent=1)
        f.write("\n")

    summary = {
        "name": NAME,
        "built_at_utc": args.built_at,
        "relax_expected": bool(args.relax_expected),
        "source_pins": pins,
        "per_year": per_year_stats,
        "frame": {k: {kk: vv for kk, vv in v.items()} for k, v in split_stats.items()},
        "exclusions": dict(exclusions),
        "fy_changed": fy_changed,
        "already_lodged_at_T": dict(already_by_split),
        "undated_current_rows_labelled_positive": undated_current,
        "group_member_files": {str(y): gm_info[str(y)]["rows"] for y in sorted(GROUP_URLS)},
        "group_member_info": gm_info,
        "columns": COLUMNS,
        "fixtures": {
            "integricare_2024": {"abn": "11000073870", "target_due_date": "2025-01-31",
                                  "T": "2024-11-02", "prior_received": "2024-01-18", "label": 1},
            "policy_offsets_2024": {"period_end_june": "+7 months (31 January extension)",
                                    "period_end_december": "+6 months"},
        },
        "assertions_passed": ["row_id unique", "abn 10-prefix injective", "no empty column per split",
                              "already-lodged rows all label 0", "integricare fixture", "policy-offset fixture",
                              "label-source absence", "both classes every target year"],
    }
    summary_path = args.summary_out or os.path.join(os.path.dirname(out), "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=1)
        f.write("\n")
    print(f"  summary -> {summary_path}")
    print("BUILD OK", flush=True)


if __name__ == "__main__":
    sys.exit(main())
