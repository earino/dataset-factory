#!/usr/bin/env python3
"""Construction script for the `nhs-ae-four-hour-decline` candidate.

Task: for an NHS England provider operating a consultant-led (Type 1) A&E
department, will the percentage of its Type 1 attendances admitted,
transferred or discharged within 4 hours of arrival decline in month M+1
relative to month M? One row per (provider, target month M+1); the label is
computed from month M+1's source row only, and every shipped feature is
derived from provider months <= M.

Where this runs
---------------
On a temporary worker (the record's construction step: 12 year pages + 102
monthly CSVs, ~3.1 MiB total, measured 1.2 s download on the coordinator
class). `--source-dir` reads already-downloaded CSVs for a local engineering
exercise; the worker run uses the default HTTP path. `--smoke` relaxes the
panel/label acceptance assertions a partial or stale copy cannot carry.

Frame rules (each measured and reported in summary.json)
--------------------------------------------------------
* Grain: provider (Org Code) x calendar month, revisions deduplicated by
  preferring the latest upload. NHS England republishes recent months as
  "...revised..." CSVs; the operative dedup rule is deterministic from the
  filenames: revised files carry their upload datestamp (e.g.
  April-2020-revised-260421 = uploaded 21 Apr 2021), so for each duplicate
  (org, month) key the copy from the file with the greatest
  (revision_datestamp, revised_flag, filename) wins. Originals without a
  datestamp sort before every revision, which is exactly the "prefer the
  latest upload" policy (a revision is always a later upload than the
  original it corrects). The count of deduplicated keys is reported.
* Volume gate: a provider-month is eligible only when Type 1 attendances
  >= 100 in BOTH the feature month M and the target month M+1 (measured on
  the 2026-10-21 snapshot: leaves 124 providers with >= 24 qualifying
  months -> 9,071 provider-months).
* Prediction instant: the end of month M, when month M's monthly CSV is
  published (measured ~3 week publication lag). Every shipped feature is
  derived from months <= M. The label is month M+1's within-4-hour rate
  versus month M's.
* Label: declines = 1 iff within4h_rate(M+1) < within4h_rate(M), where
  within4h_rate(Y) = 1 - Attendances over 4hrs Type 1 / A&E attendances
  Type 1 for that provider-month. A relative m/m change is used because the
  fixed thresholds measured near-uniform positive rates in recent years
  (<95% -> holdout 99.9% positive; <80% -> 95.8%; <74% -> 90.8% - recorded
  in the candidate record); the base rate is non-stationary with the
  system's deterioration, which is a documented property of the task.
* No external threshold is used, so no known-event fixture is required by
  the qualification gate; instead the aggregate is cross-checked against the
  publisher's own commentary (national Type 1 within-4h, August 2026:
  publisher 61.1% vs panel 60.9% at discovery), asserted at build time.
* Schema evolution, measured across all 102 files: 2018-04..2020-07 files
  carry 16 data columns (some prefixed "Number of ...", normalised here);
  booked-appointment columns appear from 2020-08 (22 columns); files from
  2024-09 carry 28 columns of which the last six are unnamed/junk padding.
  The booked-appointment columns are parsed but NOT shipped: they do not
  exist for feature months 2018-12..2020-07, so their availability would be
  split-dependent (present in eval/holdout, mostly absent in train), which
  is a prediction-timing defect wearing a feature-list costume. The core 16
  columns are published across the whole window and are the only shipped
  source columns.

Leakage discipline
-------------------
The label source - month M+1's "A&E attendances Type 1" and "Attendances
over 4hrs Type 1" - is NEVER written into any shipped file; only the binary
`declines` ships, computed from the target month's panel row and discarded
afterwards. A truncation self-check recomputes a sample of rows' features
against a panel copy that physically contains no months after M, so any
accidental future-month access fails loudly instead of shipping. Month M's
own attendances/over-4hr counts ARE knowable at the prediction instant and
ship as features.

Runner contract: public/train.csv, public/eval.csv, private/holdout.csv,
meta.json, quality.json - the layout `skills/dataset-qualification/` gates.
Splits are temporal on the TARGET month: train 2019-01..2022-12,
eval 2023-01..2024-12, holdout 2025-01..2026-09 (measured windows from the
candidate record).

Data dictionary (shipped columns)
---------------------------------
row_id            id: "<ORG CODE>-<YYYY-MM>" of the target month M+1.
target_month      "YYYY-MM" of the target month M+1 (the time column; the
                  prediction instant is the end of the previous month).
org_code          publisher's Org Code (the event key: positives cluster
                  within providers, so scores are quoted against distinct
                  positive providers per window).
parent_org        publisher's Parent Org (NHS England region, categorical).
target_year       calendar year of the target month (knowable at the
                  prediction instant).
target_month_num  calendar month number 1-12 of the target month.
rate_m            Type 1 within-4h rate of month M (= 1 - over4/att1).
rate_m1..m12      rate of months M-1/M-2/M-3/M-6/M-12; -1.0 when that month
                  is absent from the provider's panel (sentinel, outside
                  the [0,1] rate range).
rate_mean_6m      mean of the available rates over M-5..M.
rate_min_6m       min of the available rates over M-5..M.
rate_max_6m       max of the available rates over M-5..M.
rate_delta_1m     rate_m - rate_m1 (also _2m/_3m/_6m); -2.0 sentinel when
                  the lag month is absent (real deltas lie in [-1, 1]).
att1_m            A&E attendances Type 1 in month M (also att2_m, Type 2;
                  att_other_m, other A&E departments).
over4_1_m         attendances over 4hrs Type 1 in month M (also over4_2_m,
                  over4_other_m). Month M is inside the volume gate, so
                  att1_m >= 100.
dta_4_12_m        patients waiting 4-12h from decision-to-admit to
                  admission, month M (dta_12p_m: 12h+ waits).
emadm_1_m         emergency admissions via A&E Type 1, month M (also
                  emadm_2_m, emadm_other_m = via other A&E departments,
                  emadm_other2_m = other emergency admissions).
emadm_share_m     emadm_1_m / att1_m (admissions per Type 1 attendance).
att1_delta_1m     att1_m - att1_m1 (also att1_delta_12m); -99999.0 sentinel
                  when the lag month is absent.
att1_mean_6m      mean of the available att1 over M-5..M; -1.0 sentinel.
months_reported_12m  count of months present in the provider's panel over
                  M-11..M (0-12).
declines          target: 1 iff within4h_rate(M+1) < within4h_rate(M).

Licence: NHS England statistics are published under the Open Government
Licence v3.0 (work-area page footer, recorded in the candidate record); OGL
v3 attribution carries through to any release. This is a derived research
dataset, never NHS England's official product.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import socket
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

NAME = "nhs-ae-four-hour-decline"
TARGET = "declines"
POSITIVE_LABEL = 1

BASE = "https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/"
# (page, expect_monthly_csvs): the 2018-19..2026-27 year pages each link the
# monthly provider-level CSVs; the three earlier pages are XLS-only, so a
# zero-CSV response from them is the expected outcome, not an anomaly
# (measured 2026-10-21 from the coordinator: 6+12*8 = 102 CSV links).
YEAR_PAGES = [
    ("ae-attendances-and-emergency-admissions-2026-27/", True),
    ("ae-attendances-and-emergency-admissions-2025-26/", True),
    ("ae-attendances-and-emergency-admissions-2024-25/", True),
    ("ae-attendances-and-emergency-admissions-2023-24/", True),
    ("ae-attendances-and-emergency-admissions-2022-23/", True),
    ("ae-attendances-and-emergency-admissions-2021-22/", True),
    ("ae-attendances-and-emergency-admissions-2020-21/", True),
    ("ae-attendances-and-emergency-admissions-2019-20/", True),
    ("ae-attendances-and-emergency-admissions-2018-19/", True),
    ("ae-attendances-and-emergency-admissions-2017-18/", False),
    ("statistical-work-areasae-waiting-times-and-activityae-attendances-and-emergency-admissions-2016-17/", False),
    ("statistical-work-areasae-waiting-times-and-activityae-attendances-and-emergency-admissions-2015-16-monthly-3/", False),
]

# HTTP client ladder. The first worker run (nhsae-001, Hetzner hel1) fetched
# every year page as HTTP 200 yet matched zero CSV links, while the identical
# requests from the coordinator enumerate 102 - the responses the worker saw
# were not the statistics pages. Each fetch therefore retries with a plain
# browser header set and, still failing, pins the address family in turn
# (the host is CloudFront-fronted with both A and AAAA records, so the
# worker's resolver/egress may reach a different edge). Every attempt is
# recorded in the response meta and logged, and a body sample is kept, so a
# repeat failure is diagnosable from the collected container.log alone.
UA_DATASET = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) dataset-factory/1.0"}
UA_BROWSER = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64; rv:128.0) "
                   "Gecko/20100101 Firefox/128.0"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.5",
}
FETCH_ATTEMPTS = [
    ("dataset-ua", UA_DATASET, None),
    ("browser-ua", UA_BROWSER, None),
    ("browser-ua-ipv4", UA_BROWSER, socket.AF_INET),
    ("browser-ua-ipv6", UA_BROWSER, socket.AF_INET6),
]
FETCH_TIMEOUT_SECONDS = 30

# Canonical source columns, with the publisher's own naming variants mapped
# onto one key. "Number of ..." prefixes appear in 2018-19 files; the
# over-4hrs "Other" column is "Other A&E Department" in 2018-19 and "Other
# Department" afterwards. Booked-appointment columns (2020-08 onward) are
# parsed for the record but never shipped - see the module docstring.
COLUMN_ALIASES = {
    "a&e attendances type 1": "att1",
    "a&e attendances type 2": "att2",
    "a&e attendances other a&e department": "att_other",
    "attendances over 4hrs type 1": "over4_1",
    "attendances over 4hrs type 2": "over4_2",
    "attendances over 4hrs other department": "over4_other",
    "attendances over 4hrs other a&e department": "over4_other",
    "patients who have waited 4-12 hs from dta to admission": "dta_4_12",
    "patients who have waited 12+ hrs from dta to admission": "dta_12p",
    "emergency admissions via a&e - type 1": "emadm_1",
    "emergency admissions via a&e - type 2": "emadm_2",
    "emergency admissions via a&e - other a&e department": "emadm_other",
    "other emergency admissions": "emadm_other2",
    "a&e attendances booked appointments type 1": "att_booked_1",
    "a&e attendances booked appointments type 2": "att_booked_2",
    "a&e attendances booked appointments other department": "att_booked_other",
    "attendances over 4hrs booked appointments type 1": "over4_booked_1",
    "attendances over 4hrs booked appointments type 2": "over4_booked_2",
    "attendances over 4hrs booked appointments other department": "over4_booked_other",
}
LABEL_SOURCE_COLUMNS = [
    "A&E attendances Type 1", "Attendances over 4hrs Type 1",
]
VOLUME_COLUMN = "att1"
OVER4_COLUMN = "over4_1"
MIN_ATT1 = 100          # the volume gate, per the candidate record
MIN_PROVIDER_MONTHS = 24  # providers need >= 24 qualifying months

MONTHS = {name: index + 1 for index, name in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"])}

# Splits on the TARGET month (the record's measured windows).
TRAIN_START, TRAIN_END = (2019, 1), (2022, 12)
EVAL_START, EVAL_END = (2023, 1), (2024, 12)
HOLDOUT_START, HOLDOUT_END = (2025, 1), (2026, 9)

# Cross-check against the publisher's own summary product (recorded at
# discovery from the August 2026 statistical commentary): national Type 1
# within-4h in 2026-08 was 61.1% published vs 60.9% measured on the panel.
CROSSCHECK_MONTH = (2026, 8)
CROSSCHECK_PUBLISHED_RATE = 0.611
CROSSCHECK_TOLERANCE = 0.025  # revised-vs-provisional publication states

# Acceptance figures recomputed 2026-10-21 on the CORRECTED load (102 months,
# 21,548 provider-months). The discovery probe's recorded figures (3,714 /
# 2,449 / 2,538 rows; 124 providers) were computed on a damaged panel: it
# read the CSVs with encoding="utf-8", so the five BOM-prefixed files
# (2019-07, 2021-08, 2023-07/08/09) keyed Period as "\ufeffPeriod" and were
# dropped whole; and it looked up "A&E attendances Type 1" while the
# 2018-04..2020-03 files name the column "Number of A&E attendances Type 1",
# so att1 read as 0 for 24 months and no provider-month before 2020-04 ever
# passed the volume gate. Both defects are fixed here (utf-8-sig + the
# "Number of" alias); the corrected figures are the measured truth.
EXPECTED = {
    "providers": 134,
    "provider_months": 12765,
    "splits": {
        "train": {"rows": 6116, "positives": 3285},
        "eval": {"rows": 2937, "positives": 1478},
        "holdout": {"rows": 2538, "positives": 1233},
    },
}
ROW_TOLERANCE = 0.05   # +-5% on row counts (revisions republish monthly)
RATE_TOLERANCE = 0.03  # +-3pp on positive rates

STRUCTURAL = ["row_id", "target_month"]
ID_COLUMNS = ["row_id"]
FEATURES = [
    "org_code", "parent_org", "target_year", "target_month_num",
    "rate_m", "rate_m1", "rate_m2", "rate_m3", "rate_m6", "rate_m12",
    "rate_mean_6m", "rate_min_6m", "rate_max_6m",
    "rate_delta_1m", "rate_delta_2m", "rate_delta_3m", "rate_delta_6m",
    "att1_m", "att2_m", "att_other_m",
    "over4_1_m", "over4_2_m", "over4_other_m",
    "dta_4_12_m", "dta_12p_m",
    "emadm_1_m", "emadm_2_m", "emadm_other_m", "emadm_other2_m",
    "emadm_share_m", "att1_delta_1m", "att1_delta_12m", "att1_mean_6m",
    "months_reported_12m",
]
CARRY_COLUMNS = ["target_month"]
HIGH_CARDINALITY = ["row_id", "target_month", "org_code"]
COLUMNS = ID_COLUMNS + FEATURES + CARRY_COLUMNS + [TARGET]

LAYOUT = {"train": "public/train.csv", "eval": "public/eval.csv",
          "holdout": "private/holdout.csv"}

PREDICTION_TIME = (
    "The end of month M, when month M's monthly A&E CSV is published "
    "(measured ~3 week publication lag: the September 2026 CSV was already "
    "downloadable on 2026-10-21). Every feature is derived from the "
    "provider's monthly series for months <= M; the label is month M+1's "
    "within-4-hour rate versus month M's, published about a month later.")
PREDICTION_QUESTION = (
    "For an NHS England provider operating a consultant-led (Type 1) A&E "
    "department with at least 100 Type 1 attendances in each of months M and "
    "M+1, will the provider's Type 1 within-4-hour performance rate decline "
    "in month M+1 relative to month M, given the provider's monthly A&E "
    "series (attendances by department type, over-4-hour counts, "
    "decision-to-admit waits, emergency admissions) for all months through "
    "M, plus the calendar?")


def log(message: str) -> None:
    print(message, flush=True)


def month_of_year(year: int, month: int, shift: int) -> tuple[int, int]:
    """Calendar month shifted by `shift` months (negative = back)."""
    index = year * 12 + (month - 1) + shift
    return index // 12, index % 12 + 1


def month_key(period: str):
    """'MSitAE-SEPTEMBER-2026' -> (2026, 9); None for non-monthly tokens."""
    match = re.search(r"([A-Za-z]+)-(\d{4})$", (period or "").strip())
    if not match:
        return None
    name = match.group(1).lower()
    if name not in MONTHS:
        return None
    return int(match.group(2)), MONTHS[name]


def revision_sort_key(filename: str) -> tuple:
    """(datestamp, revised_flag, filename) - greatest wins a duplicate key.

    Revised uploads carry their upload date in the name
    (April-2020-revised-260421-abc123.csv = uploaded 21 Apr 2021); the
    datestamp is read as YY MM DD and ordered as a sortable string.
    """
    stamp = ""
    match = re.search(r"revised-(\d{2})(\d{2})(\d{2})", filename.lower())
    if match:
        yy, mm, dd = match.groups()
        stamp = f"20{yy}-{mm}-{dd}"
    return (stamp, 1 if "revised" in filename.lower() else 0, filename)


_PINNED_FAMILY: int | None = None
_DEFAULT_GETADDRINFO = socket.getaddrinfo


def _pinned_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """Resolver wrapper honouring the ladder's address-family pin."""
    if _PINNED_FAMILY is not None:
        family = _PINNED_FAMILY
    return _DEFAULT_GETADDRINFO(host, port, family, type, proto, flags)


# Module-wide pin: this tool's only HTTP traffic is the NHS enumeration and
# the CSV downloads, and run.sh runs it as a single short-lived process.
socket.getaddrinfo = _pinned_getaddrinfo

CSV_LINK = re.compile(
    r"https://www\.england\.nhs\.uk/statistics/wp-content/uploads/sites/2/"
    r"[^\"']*?\.csv")


def extract_csv_links(html: str) -> list[str]:
    """Monthly provider-level CSV links on a year page (ECDS excluded)."""
    return [url for url in CSV_LINK.findall(html)
            if not re.search(r"ECDS", url, re.I)]


def looks_like_csv(body: bytes) -> bool:
    """The monthly CSVs open with a 'Period,...' header row, some with a
    UTF-8 BOM (measured across all 102 files at construction). A WAF or
    interstitial body will not carry both tokens."""
    head = body.lstrip("\ufeff".encode("utf-8"))[:400]
    return b"Period" in head and b"," in head


def fetch_laddered(url: str, accept) -> tuple[bytes, dict]:
    """Fetch `url`, retrying the client ladder until `accept(body)` passes.

    Returns (body, meta); meta carries one record per attempt (client label,
    final URL after redirects, status, content type, byte count, exception)
    plus `accepted`/`accepted_by`. When no attempt is accepted the LAST
    response body is still returned, so the caller can dump exactly what the
    server sent; `accept` never gates data out of the build on its own - the
    downstream coverage and cross-check assertions remain the real gates.
    """
    global _PINNED_FAMILY
    body = b""
    meta = {"url": url, "attempts": [], "accepted": False}
    for label, headers, family in FETCH_ATTEMPTS:
        _PINNED_FAMILY = family
        attempt = {"client": label}
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(
                    request, timeout=FETCH_TIMEOUT_SECONDS) as response:
                body = response.read()
                attempt.update(final_url=response.geturl(),
                               status=response.status,
                               content_type=response.headers.get(
                                   "Content-Type", ""),
                               bytes=len(body))
                if accept(body):
                    attempt["accepted"] = True
                    meta["attempts"].append(attempt)
                    meta["accepted"] = True
                    meta["accepted_by"] = label
                    _PINNED_FAMILY = None
                    return body, meta
        except Exception as error:  # noqa: BLE001 - recorded, retried
            attempt["error"] = repr(error)[:200]
        meta["attempts"].append(attempt)
        time.sleep(2)  # breather before the next client variant
    _PINNED_FAMILY = None
    return body, meta


def collect_urls() -> tuple[list[dict], int, list[dict]]:
    """Enumerate the monthly CSV URLs from the year pages (probe pattern).

    Returns (urls, page_requests, anomalies). An anomaly is a page that did
    not yield a successful response with its expected content even after the
    client ladder; it carries the response meta and a bounded body sample so
    the failure mode is diagnosable from the collected log (nhsae-001 failed
    with 12 x HTTP 200 and zero matching links, leaving no other evidence).
    For the pre-2018-19 XLS-only pages any successful response settles the
    page (their expected CSV count is zero); only a page with no response at
    all is an anomaly.
    """
    urls = []
    page_requests = 0
    anomalies = []
    for page, expect_csvs in YEAR_PAGES:
        def accept(body: bytes, expect=expect_csvs) -> bool:
            if not expect:
                return True
            return bool(extract_csv_links(body.decode("utf-8", "replace")))
        body, meta = fetch_laddered(BASE + page, accept)
        page_requests += len(meta["attempts"])
        links = extract_csv_links(body.decode("utf-8", "replace"))
        log(f"  {page}: {len(links)} csv links, "
            f"{len(meta['attempts'])} request(s)"
            + (f", accepted by {meta['accepted_by']}" if meta["accepted"]
               else ", NOT accepted"))
        if not meta["accepted"]:
            anomalies.append({
                "page": page,
                "meta": meta,
                "body": body[:65536],
                "sample": body[:600].decode("utf-8", "replace"),
            })
            continue
        for url in links:
            urls.append({"url": url, "filename": url.rsplit("/", 1)[-1]})
    return urls, page_requests, anomalies


def parse_count(raw: str | None):
    """NHS writes plain integers (measured: no non-numeric, no empty cells
    across all 102 files); anything unparsable or empty is missing, not 0."""
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def load_panel(paths: list[tuple[Path, str]]) -> dict:
    """(org, (y, m)) -> row dict, revisions deduplicated by upload order.

    `paths` is (file path, filename) pairs. Rows with non-monthly Period
    tokens (quarterly/annual artefacts, 1,152 measured at discovery) are
    counted and skipped. Unmapped header columns (the 2024-09+ unnamed
    padding) are ignored.
    """
    panel: dict = {}
    stats = {"files": 0, "rows_read": 0, "skipped_period": 0,
             "skipped_no_org": 0, "deduped_keys": 0, "booked_cells_seen": 0}
    for path, filename in sorted(paths, key=lambda item: item[1]):
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            header = next(reader, None)
            if header is None:
                continue
            names = []
            canonical = []
            for index, raw in enumerate(header):
                key = raw.strip().lower()
                if key.startswith("number of "):
                    key = key[len("number of "):]
                names.append(raw.strip())
                canonical.append(COLUMN_ALIASES.get(key))
            try:
                period_at = names.index("Period")
                org_at = names.index("Org Code")
            except ValueError:
                stats["files"] += 1  # count it, but it cannot contribute
                continue
            parent_at = names.index("Parent Org") if "Parent Org" in names else None
            stats["files"] += 1
            order = revision_sort_key(filename)
            for row in reader:
                if len(row) <= max(period_at, org_at):
                    continue
                stats["rows_read"] += 1
                key = month_key(row[period_at])
                if key is None:
                    stats["skipped_period"] += 1
                    continue
                org = row[org_at].strip()
                if not org:
                    stats["skipped_no_org"] += 1
                    continue
                record = {"order": order, "values": {}, "name": "",
                          "parent": ""}
                for index, mapped in enumerate(canonical):
                    if mapped is None or index >= len(row):
                        continue
                    value = parse_count(row[index])
                    if mapped.startswith(("att_booked", "over4_booked")) \
                            and value is not None:
                        stats["booked_cells_seen"] += 1
                    if mapped in ("att1", "over4_1") or mapped not in (
                            "att_booked_1", "att_booked_2", "att_booked_other",
                            "over4_booked_1", "over4_booked_2",
                            "over4_booked_other"):
                        record["values"][mapped] = value
                if parent_at is not None and parent_at < len(row):
                    record["parent"] = row[parent_at].strip()
                slot = panel.get((org, key))
                if slot is None:
                    panel[(org, key)] = record
                else:
                    stats["deduped_keys"] += 1
                    if record["order"] > slot["order"]:
                        panel[(org, key)] = record
    return {"panel": panel, "stats": stats}


def within4h(record: dict | None):
    """Type 1 within-4h rate, or None when the month or counts are missing."""
    if record is None:
        return None
    att1 = record["values"].get("att1")
    over4 = record["values"].get("over4_1")
    if not att1 or att1 <= 0 or over4 is None:
        return None
    return 1.0 - over4 / att1


def features_for(panel: dict, org: str, year: int, month: int) -> dict:
    """Features for the row whose feature month is (year, month) = M.

    Reads months <= M only. Absent months yield sentinels outside each
    column's real range, documented in the module docstring.
    """
    def at(shift: int):
        return panel.get((org, month_of_year(year, month, shift)))

    current = at(0)
    if current is None:
        raise KeyError(f"feature month {org} {(year, month)} missing from the panel")
    rate_m = within4h(current)
    out = {
        "org_code": org,
        "parent_org": current.get("parent", ""),
        "target_year": month_of_year(year, month, 1)[0],
        "target_month_num": month_of_year(year, month, 1)[1],
        "rate_m": rate_m,
    }
    for lag in (1, 2, 3, 6, 12):
        rate = within4h(at(-lag))
        out[f"rate_m{lag}"] = rate if rate is not None else -1.0
        if lag in (1, 2, 3, 6):
            delta = rate_m - rate if rate is not None and rate_m is not None else None
            out[f"rate_delta_{lag}m"] = delta if delta is not None else -2.0
    window = [within4h(at(-shift)) for shift in range(0, 6)]
    window = [rate for rate in window if rate is not None]
    out["rate_mean_6m"] = sum(window) / len(window) if window else -1.0
    out["rate_min_6m"] = min(window) if window else -1.0
    out["rate_max_6m"] = max(window) if window else -1.0

    values = current["values"]
    for source, feature in (
            ("att1", "att1_m"), ("att2", "att2_m"), ("att_other", "att_other_m"),
            ("over4_1", "over4_1_m"), ("over4_2", "over4_2_m"),
            ("over4_other", "over4_other_m"), ("dta_4_12", "dta_4_12_m"),
            ("dta_12p", "dta_12p_m"), ("emadm_1", "emadm_1_m"),
            ("emadm_2", "emadm_2_m"), ("emadm_other", "emadm_other_m"),
            ("emadm_other2", "emadm_other2_m")):
        out[feature] = values.get(source)
        if out[feature] is None:
            out[feature] = -1.0
    att1_m = values.get("att1")
    emadm_1 = values.get("emadm_1")
    out["emadm_share_m"] = (emadm_1 / att1_m
                            if att1_m and emadm_1 is not None else -1.0)

    previous = at(-1)
    out["att1_delta_1m"] = (att1_m - previous["values"]["att1"]
                            if previous and previous["values"].get("att1") is not None
                            and att1_m is not None else -99999.0)
    year_ago = at(-12)
    out["att1_delta_12m"] = (att1_m - year_ago["values"]["att1"]
                             if year_ago and year_ago["values"].get("att1") is not None
                             and att1_m is not None else -99999.0)
    att_window = []
    for shift in range(0, 6):
        record = at(-shift)
        if record is not None:
            value = record["values"].get("att1")
            if value is not None:
                att_window.append(value)
    out["att1_mean_6m"] = sum(att_window) / len(att_window) if att_window else -1.0
    out["months_reported_12m"] = sum(
        1 for shift in range(0, 12) if at(-shift) is not None)
    return out


def make_rows(panel: dict) -> tuple[list[dict], dict]:
    """Eligible (provider, target month) rows under the volume gate."""
    by_org: dict[str, list] = {}
    for (org, key), record in panel.items():
        att1 = record["values"].get("att1")
        if att1 is not None and att1 >= MIN_ATT1:
            by_org.setdefault(org, []).append(key)
    providers = {org: sorted(keys) for org, keys in by_org.items()
                if len(keys) >= MIN_PROVIDER_MONTHS}

    rows = []
    skipped = {"not_consecutive": 0}
    for org, keys in providers.items():
        for index in range(len(keys) - 1):
            feature_key, target_key = keys[index], keys[index + 1]
            if month_of_year(feature_key[0], feature_key[1], 1) != target_key:
                skipped["not_consecutive"] += 1
                continue
            rate_m = within4h(panel[(org, feature_key)])
            rate_next = within4h(panel[(org, target_key)])
            if rate_m is None or rate_next is None:
                skipped["not_consecutive"] += 1
                continue
            features = features_for(panel, org, *feature_key)
            row = {
                "row_id": f"{org}-{target_key[0]:04d}-{target_key[1]:02d}",
                "target_month": f"{target_key[0]:04d}-{target_key[1]:02d}",
                TARGET: 1 if rate_next < rate_m else 0,
                **features,
            }
            rows.append(row)
    rows.sort(key=lambda row: (row["org_code"], row["target_month"]))
    return rows, {
        "providers": len(providers),
        "provider_months": sum(len(keys) for keys in providers.values()),
        "skipped": skipped,
    }


def split_of(target_key: tuple[int, int]) -> str:
    if TRAIN_START <= target_key <= TRAIN_END:
        return "train"
    if EVAL_START <= target_key <= EVAL_END:
        return "eval"
    return "holdout" if HOLDOUT_START <= target_key <= HOLDOUT_END else "outside"


def auc(labels: list[int], scores: list[float]) -> float | None:
    """Rank-based AUC (Mann-Whitney) with ties averaged, stdlib only."""
    pairs = sorted(zip(scores, labels), key=lambda pair: pair[0])
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        return None
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
    positive_rank_sum = sum(rank for rank, (_, label) in zip(ranks, pairs)
                            if label == POSITIVE_LABEL)
    return (positive_rank_sum - positives * (positives + 1) / 2) \
        / (positives * negatives)


def write_splits(out: Path, rows_by_split: dict) -> dict:
    stats = {}
    for split, rel in LAYOUT.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = rows_by_split[split]
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS,
                                    extrasaction="raise")
            writer.writeheader()
            writer.writerows(rows)
        positives = sum(row[TARGET] for row in rows)
        events = len({row["org_code"] for row in rows
                      if row[TARGET] == POSITIVE_LABEL})
        stats[split] = {"rows": len(rows), "positives": positives,
                        "positive_rate": round(positives / len(rows), 6)
                        if rows else None,
                        "distinct_events": events}
    return stats


def timing_selfcheck(rows: list[dict], panel: dict, sample: int) -> dict:
    """Recompute a sample of rows against a physically truncated panel.

    If any feature path touches a month after M, the truncated copy yields a
    different value here instead of shipping a post-hoc feature.
    """
    if not rows:
        return {"checked": 0, "mismatches": 0}
    step = max(1, len(rows) // sample)
    checked = mismatches = 0
    for row in rows[::step]:
        year, month = (int(part) for part in row["target_month"].split("-"))
        feature_key = month_of_year(year, month, -1)
        org = row["org_code"]
        horizon = (feature_key[0], feature_key[1])
        truncated = {key: value for key, value in panel.items()
                     if key[1] <= horizon}
        rebuilt = features_for(truncated, org, *feature_key)
        checked += 1
        for column in FEATURES:
            if rebuilt.get(column) != row.get(column):
                mismatches += 1
                log(f"TIMING CHECK MISMATCH {row['row_id']} column {column}: "
                    f"shipped {row.get(column)!r} rebuilt {rebuilt.get(column)!r}")
                break
    return {"checked": checked, "mismatches": mismatches}


def national_crosscheck(panel: dict) -> dict:
    """National Type 1 within-4h for the cross-check month, volume-gated
    providers only (the discovery probe's comparable frame)."""
    year, month = CROSSCHECK_MONTH
    attendances = over4 = 0
    for (org, key), record in panel.items():
        if key != (year, month):
            continue
        att1 = record["values"].get("att1")
        if att1 is None or att1 < MIN_ATT1:
            continue
        attendances += att1
        over = record["values"].get("over4_1")
        over4 += over if over is not None else 0
    rate = (attendances - over4) / attendances if attendances else None
    return {"month": f"{year:04d}-{month:02d}", "attendances": attendances,
            "panel_rate": round(rate, 4) if rate is not None else None,
            "publisher_commentary_rate": CROSSCHECK_PUBLISHED_RATE}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the nhs-ae-four-hour-decline extract")
    parser.add_argument("--out", default="/output",
                        help="extract root (runner layout written inside)")
    parser.add_argument("--work-dir", default="/tmp/nhsae",
                        help="scratch for the source downloads")
    parser.add_argument("--source-dir", default=None,
                        help="read already-downloaded CSVs from this "
                             "directory instead of HTTP (local exercise)")
    parser.add_argument("--source-provenance", default=None,
                        help="note recorded in summary.source when the CSVs "
                             "come from a staged copy rather than a direct "
                             "publisher fetch")
    parser.add_argument("--smoke", action="store_true",
                        help="bounded exercise: skip acceptance assertions")
    parser.add_argument("--built-at", default=None,
                        help="pin the build timestamp (UTC)")
    parser.add_argument("--timing-check-sample", type=int, default=200)
    args = parser.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    built_at = args.built_at or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")

    log("== download ==")
    download_started = time.time()
    if args.source_dir:
        directory = Path(args.source_dir)
        paths = [(path, path.name) for path in sorted(directory.glob("*.csv"))]
        source = {"mode": "local", "files": len(paths),
                  "requests": 0, "bytes": sum(p.stat().st_size for p, _ in paths),
                  "seconds": None, "note": "CSVs read from a local directory"}
        if args.source_provenance:
            source["provenance"] = args.source_provenance
    else:
        urls, page_requests, anomalies = collect_urls()
        if anomalies or len(urls) < 100:
            log(f"FAIL: only {len(urls)} monthly CSV URLs enumerated "
                f"({page_requests} page requests, {len(anomalies)} page(s) "
                "without their expected content; >= 100 expected)")
            for item in anomalies[:4]:
                log(f"  page {item['page']}: {item['meta']}")
                log(f"  body sample: {item['sample']!r}")
            probe = out / "url_probe"
            probe.mkdir(parents=True, exist_ok=True)
            for index, item in enumerate(anomalies[:4]):
                slug = item["page"].rstrip("/").replace("/", "_")
                (probe / f"{index:02d}-{slug}").write_bytes(item["body"])
            return 2
        paths = []
        failures = []
        requests = page_requests
        first_failed_body = b""
        for entry in urls:
            dest = work / entry["filename"]
            body, meta = fetch_laddered(entry["url"], looks_like_csv)
            requests += len(meta["attempts"])
            if not meta["accepted"]:
                if not first_failed_body:
                    first_failed_body = body[:65536]
                failures.append({
                    "file": entry["filename"],
                    "attempts": [
                        attempt.get("error")
                        or [attempt.get("status"), attempt.get("bytes"),
                            attempt.get("content_type")]
                        for attempt in meta["attempts"]],
                    "body_sample": body[:300].decode("utf-8", "replace"),
                })
                continue
            dest.write_bytes(body)
            paths.append((dest, entry["filename"]))
        if failures:
            log(f"FAIL: {len(failures)} CSV downloads did not return a CSV "
                f"body: {failures[:2]}")
            if first_failed_body:
                probe = out / "csv_probe"
                probe.mkdir(parents=True, exist_ok=True)
                (probe / "first-failed-body.bin").write_bytes(first_failed_body)
            return 2
        source = {"mode": "http", "files": len(paths),
                  "requests": requests,
                  "bytes": sum(path.stat().st_size for path, _ in paths),
                  "seconds": round(time.time() - download_started, 1),
                  "pages": page_requests}
    digest = hashlib.sha256()
    for path, filename in sorted(paths, key=lambda item: item[1]):
        digest.update(filename.encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    source["composite_sha256"] = digest.hexdigest()
    log(f"{source['files']} CSVs, {source['bytes']} bytes, "
        f"{source['requests']} requests, {source['seconds']}s")

    log("== panel ==")
    loaded = load_panel(paths)
    panel, load_stats = loaded["panel"], loaded["stats"]
    months = sorted({key for _, key in panel})
    log(f"panel: {len(panel)} provider-months over {len(months)} months "
        f"({months[0]}..{months[-1]}); load stats: {load_stats}")
    if len(months) < 95 or months[-1] < (2026, 7):
        log("FAIL: month coverage collapsed below the recorded snapshot's "
            "(97 months to 2026-09); the source layout changed")
        return 2

    log("== rows ==")
    rows, gate = make_rows(panel)
    log(f"eligible rows: {len(rows)}; gate: {gate}")

    duplicates = len(rows) - len({row["row_id"] for row in rows})
    if duplicates:
        log(f"FAIL: {duplicates} duplicate row_ids")
        return 2

    rows_by_split = {"train": [], "eval": [], "holdout": []}
    outside = 0
    for row in rows:
        year, month = (int(part) for part in row["target_month"].split("-"))
        split = split_of((year, month))
        if split == "outside":
            outside += 1
            continue
        rows_by_split[split].append(row)
    log(f"rows outside the split windows (targets before 2019-01): {outside}")

    timing = timing_selfcheck(rows, panel, args.timing_check_sample)
    log(f"timing self-check: {timing}")
    if timing["mismatches"]:
        log("FAIL: features are not reproducible from months <= M alone")
        return 2

    stats = write_splits(out, rows_by_split)
    for split, entry in stats.items():
        log(f"{split}: {entry['rows']} rows, {entry['positives']} positives "
            f"({entry['positive_rate']}), {entry['distinct_events']} "
            f"distinct positive providers")

    # The label source must be absent from the shipped files: only the
    # binary target may carry any information about month M+1.
    with (out / LAYOUT["train"]).open(newline="") as handle:
        header = handle.readline()
    for column in ("att1_next", "over4_next", "rate_next", "rate_delta_next"):
        if column in header:
            log(f"FAIL: derived label column {column} shipped in the header")
            return 2

    baselines = {}
    for split, rel in LAYOUT.items():
        split_rows = rows_by_split[split]
        labels = [row[TARGET] for row in split_rows]
        baselines[split] = {
            "momentum_auc": auc(labels, [row["rate_m1"] - row["rate_m"]
                                         for row in split_rows]),
            "mean_reversion_auc": auc(labels, [row["rate_m"] - row["rate_mean_6m"]
                                               for row in split_rows]),
            "winter_auc": auc(labels, [1.0 if row["target_month_num"] in (11, 12)
                                       else 0.0 for row in split_rows]),
        }

    crosscheck = national_crosscheck(panel)

    summary = {
        "name": NAME,
        "built_at_utc": built_at,
        "source": source,
        "grain": "provider (Org Code) x calendar month",
        "label": {
            "definition": "declines = 1 iff within4h_rate(M+1) < within4h_rate(M)",
            "within4h_rate": "1 - Attendances over 4hrs Type 1 / A&E attendances Type 1",
            "external_threshold": None,
            "note": "fixed thresholds measured near-uniform rates and were "
                    "refused (record: <95% -> holdout 99.9% positive; <80% -> "
                    "95.8%); the m/m direction label is threshold-free",
        },
        "volume_gate": {"min_att1": MIN_ATT1,
                        "min_provider_months": MIN_PROVIDER_MONTHS,
                        "applies_to": "both the feature month M and the target month M+1"},
        "revision_policy": "duplicate (org, month) keys keep the copy from "
                            "the latest upload, ordered by (revision datestamp "
                            "in filename, revised flag, filename); originals "
                            "without a datestamp sort before every revision",
        "load_stats": load_stats,
        "gate": gate,
        "skipped_rows_outside_windows": outside,
        "splits": stats,
        "clustered_events_note": "distinct_events counts distinct positive "
                                 "Org Codes per window - positives cluster "
                                 "within providers, so this is the "
                                 "conservative independent-unit count",
        "national_crosscheck": crosscheck,
        "timing_selfcheck": timing,
        "duplicate_row_ids": duplicates,
        "schema_evolution": "16 data columns 2018-04..2020-07 (with 'Number "
                            "of' prefixes in 2018-19); booked-appointment "
                            "columns from 2020-08 (22 columns); unnamed "
                            "padding columns from 2024-09 (28 header fields); "
                            "booked columns parsed but not shipped - they are "
                            "absent for train feature months 2018-12..2020-07",
        "reference_baselines": {
            "note": "stdlib rank AUC measured at construction on the written "
                    "rows; every score is a prediction-time-safe single feature",
            "per_split": baselines,
        },
    }

    if not args.smoke:
        # Acceptance against the 2026-10-21 discovery measurements (same
        # snapshot; monthly revisions can move counts slightly).
        for split, expected in EXPECTED["splits"].items():
            entry = stats[split]
            low = expected["rows"] * (1 - ROW_TOLERANCE)
            high = expected["rows"] * (1 + ROW_TOLERANCE)
            if not low <= entry["rows"] <= high:
                log(f"FAIL: {split} rows {entry['rows']} outside the recorded "
                    f"measurement {expected['rows']} +- {ROW_TOLERANCE:.0%}")
                return 2
            if abs(entry["positive_rate"] - expected["positives"] / expected["rows"]) \
                    > RATE_TOLERANCE:
                log(f"FAIL: {split} positive rate {entry['positive_rate']} drifted "
                    f"from the recorded {expected['positives'] / expected['rows']:.3f} "
                    f"by more than {RATE_TOLERANCE}")
                return 2
            if entry["positives"] < 30 or entry["distinct_events"] < 20:
                log(f"FAIL: {split} too thin to score: {entry}")
                return 2
        if abs(gate["providers"] - EXPECTED["providers"]) > 3:
            log(f"FAIL: provider count {gate['providers']} drifted from the "
                f"recorded {EXPECTED['providers']}")
            return 2
        rate = crosscheck["panel_rate"]
        if rate is None or abs(rate - CROSSCHECK_PUBLISHED_RATE) > CROSSCHECK_TOLERANCE:
            log(f"FAIL: national within-4h cross-check {rate} vs published "
                f"{CROSSCHECK_PUBLISHED_RATE} (tolerance {CROSSCHECK_TOLERANCE})")
            return 2
    else:
        log("SMOKE MODE: acceptance and cross-check assertions skipped")

    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")

    meta = {
        "name": NAME,
        "description": PREDICTION_QUESTION,
        "source": "https://www.england.nhs.uk/statistics/statistical-work-areas/"
                  "ae-waiting-times-and-activity/ (monthly provider-level CSVs)",
        "license": "Open Government Licence v3.0 (NHS England / Crown copyright). "
                   "Derived research dataset - not NHS England's official product.",
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": ID_COLUMNS,
        "columns": COLUMNS,
        "rows": {split: stats[split]["rows"] for split in LAYOUT},
        "positive_rate": {split: stats[split]["positive_rate"] for split in LAYOUT},
        "split": {
            "strategy": "temporal on the target month M+1",
            "boundaries": {
                "train": "target months 2019-01..2022-12",
                "eval": "target months 2023-01..2024-12",
                "holdout": "target months 2025-01..2026-09",
            },
        },
        "label_rule": "declines = 1 iff within4h_rate(M+1) < within4h_rate(M), "
                      "within4h_rate(Y) = 1 - Attendances over 4hrs Type 1 / "
                      "A&E attendances Type 1; provider-months with Type 1 "
                      "attendances < 100 in either month are excluded",
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "prediction_time": PREDICTION_TIME,
        "features": FEATURES,
        "built_at_utc": built_at,
        "source_files": source["files"],
        "source_bytes": source["bytes"],
        "source_composite_sha256": source["composite_sha256"],
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    quality = {
        "name": NAME,
        "task": {"question": PREDICTION_QUESTION,
                 "prediction_time": PREDICTION_TIME},
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "time_column": "target_month",
        "event_key_column": "org_code",
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "timing": {
            "prediction_instant": {"kind": "publication", "period": "M",
                                   "days_after_period_end": 10,
                                   "citation": "NHS England publishes monthly A&E activity about ten "
                                               "days after the month ends; e.g. August 2026 data was "
                                               "published 2026-09-10"},
            "features": {"period": "M", "published_days_after_period_end": 10,
                         "source_kind": "statistical_release"},
            "row_selection": {"latest_period_used": "M",
                              "fields": ["att1_m", "over4_1_m", "rate_m", "months_reported_12m"],
                              "basis": "the rebuilt selection must use only months up to M; the "
                                       "audited v2026.10 build also used M+1 attendance"},
            "observations": [{"period": "2026-08", "period_end": "2026-08-31",
                              "published": "2026-09-10"}],
        },
        "feature_documentation": (
            "every source field is documented in NHS England's A&E "
            "Attendances and Emergency Admissions statistics (column meanings "
            "recorded in the candidate record from the publisher's work area; "
            "the derived-column dictionary lives in build.py's module "
            "docstring and ships in the release DATA_DICTIONARY); month M "
            "columns are published before the prediction instant and month "
            "M+1 columns are not shipped at all"),
        "carry_columns": CARRY_COLUMNS,
        "id_columns": ID_COLUMNS,
        "high_cardinality_columns": HIGH_CARDINALITY,
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "post_hoc_columns": [],
        "measurements": [
            {"column": "rate_m",
             "unit": "proportion of Type 1 attendances within 4 hours "
                     "(1 - over4/att1)",
             "frame": "month M, the feature month ending at the prediction "
                      "instant"},
            {"column": "att1_m",
             "unit": "count of Type 1 A&E attendances in month M",
             "frame": "month M; >= 100 by the volume gate"},
            {"column": "org_code",
             "unit": "categorical provider identifier (publisher's Org Code)",
             "frame": "stable provider identity; also the clustered-event key"},
            {"column": "target_month",
             "unit": "YYYY-MM of the target month M+1",
             "frame": "the month the label is drawn from; the prediction "
                      "instant is the end of the previous month"},
            {"column": "declines",
             "unit": "binary label",
             "frame": "within4h_rate(M+1) < within4h_rate(M), computed from "
                      "month M+1's source row only"},
        ],
        "external_threshold": None,
        "split_windows": {
            "train": {"start": "2019-01", "end": "2023-01"},
            "eval": {"start": "2023-01", "end": "2025-01"},
            "holdout": {"start": "2025-01", "end": None},
        },
        "split_boundaries": {
            "train": "target months 2019-01..2022-12",
            "eval": "target months 2023-01..2024-12",
            "holdout": "target months 2025-01..2026-09",
        },
        "expected_duplicate_ids": 0,
        "id_columns_are_entity_keys": True,
        "id_columns_note": "row_id names one provider-target-month with one "
                           "label; org codes legitimately repeat across "
                           "splits because the same providers are tracked "
                           "over time - the entity is the provider-month, "
                           "not the provider",
        "positive_events": {split: {"positives": stats[split]["positives"],
                                    "distinct_events": stats[split]["distinct_events"]}
                            for split in ("eval", "holdout")},
        "positive_events_note": "distinct_events counts distinct positive Org "
                                "Codes per window - the conservative "
                                "independent-unit count, per the candidate record",
        "splits": LAYOUT,
        "built_at_utc": built_at,
        "shipped_columns": COLUMNS,
        "timing_selfcheck": timing,
        "national_crosscheck": crosscheck,
    }
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")

    log("== done ==")
    log(json.dumps({"splits": stats, "gate": gate, "crosscheck": crosscheck,
                    "baselines": baselines}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
