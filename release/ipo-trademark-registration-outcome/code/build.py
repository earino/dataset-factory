#!/usr/bin/env python3
"""Construction for the `ipo-trademark-registration-outcome` prediction task.

One row per UK domestic trade mark application (distinct mark number) in the
IPO's frozen 2018-02-13 open-data snapshot. The question: for a domestic trade
mark application filed 2010-2016, from filing-time attributes only - mark
text, Nice class coverage, category, mark type, series flag/count, owner
country/region/postcode area, filing date - will the mark reach registration
as resolved in the snapshot (Registered date non-empty)?

This file ONLY constructs the artifact and its gate diagnostics:
public/train.csv, public/eval.csv, private/holdout.csv, meta.json,
quality.json, summary.json. No performance metric (AUC, accuracy, any model
score) is computed anywhere in it; references run in score.py after the gate
passed and --accept re-verified the exact bytes.

Design frozen per the candidate record (construction_handoff, status ready,
discovery probes 2026-10-27 plus the 2026-10-30 dedup-key reconciliation
probe retained in the candidate's notes):
  * source: the IPO domestic open-data zip, one anonymous GET
    (63,238,846 B), pinned by sha256
    3b6063be...; member OpenDataDomestic.txt is UTF-16LE, pipe-separated,
    62 columns, \\r\\n line ends; header row carries a BOM;
  * parsing: right-anchored field recovery for the 94 rows with embedded
    pipes in Mark Text (field-count distribution 62/63/64/65 measured:
    1,188,910/76/15/3 over 1,189,004 data rows - asserted);
  * identity: one row per distinct mark number string (spaces stripped);
    multi-owner duplicate rows (16,909 under the string key: the discovery
    probe's 16,892 numeric-key dups plus 17 letter-suffixed series sub-marks
    with repeated owner rows) keep the FIRST occurrence; the file is
    number-sorted (3 sortedness violations measured, recorded not asserted
    as a rule); 22,812 rows carry letter-suffixed mark numbers
    (UK0000000052A/B series sub-marks) and stay distinct records;
  * eligibility: filed 2010-01-01..2016-12-31 (complete-population coverage
    documented from 2010-01-01; 2005-2009 measured registration-conditioned);
  * label: registered-by-snapshot - positive iff the Registered date is
    non-empty; negative iff Registered is empty AND status in
    {Refused, Withdrawn}; everything else is censored (unobserved outcome at
    the snapshot, e.g. still in examination/opposition), excluded from
    scoring and counted per cohort - never labelled negative. Eight
    eligible rows carry a negative status AND a Registered date; the label
    keys on the Registered date (asserted, per the discovery probe's ten
    rows on the wider post-2010 population);
  * splits: cohort split on filing year - train 2010-2012, eval 2013-2014,
    holdout 2015-2016 - with counts asserted exactly as re-derived by the
    corrected 2026-10-30 reconciliation probe
    (probe_reconcile_pipe_rows.py; RECONCILIATION CLOSED): the discovery
    probe's table under-counted cohorts 2013-2016 because it read the 94
    embedded-pipe rows at shifted positions - a probe-measurement error,
    corrected here, never tuned against build output:
    train 106,990 scored rows / 14,322 negatives, eval 97,274 / 15,575,
    holdout 115,172 / 15,787; censored 21 / 172 / 809;
  * features: filing-time attributes only (mark text, class booleans +
    class count, category, mark type, series flag/count, owner
    country/region/postcode area, filed date). Status, Published,
    Registered, Expired, Renewal Due Date are the label source and never
    shipped; Hyperlink (an Excel formula wrapping the mark number) and owner
    Name (free-text owner identity, excluded by the frozen handoff design)
    are not shipped either;
  * cross-check: the measured per-year distinct-mark cohorts 2012-2016 match
    the IPO's own facts-and-figures workbook "National UK applications"
    within +-1% (pinned published values recorded from the workbook at
    discovery);
  * vintage: one frozen snapshot for every row - a clearly-labelled
    RETROSPECTIVE task; no historical operational availability is claimed.

Licence: Open Government Licence v3.0 (class A in the candidate record).
Contains public sector information licensed under the Open Government
Licence v3.0. Derived research dataset - never an official IPO product.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
import urllib.request
import zlib
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

NAME = "ipo-trademark-registration-outcome"
URL = ("https://assets.publishing.service.gov.uk/media/"
       "5a82e5f4e5274a2e87dc387d/opendatadomestic.zip")
UA = ("Scout-factory-build/1.0 (dataset-factory worker construction; "
      "UK IPO trade mark open data snapshot)")
PINNED_SHA256 = ("3b6063bed36a78e8a04f10a5383f2881f4072a1be13e706a81ab09"
                 "7fb56ee571")
PINNED_BYTES = 63_238_846

TARGET = "registered"
POSITIVE_LABEL = 1

ID_COLUMNS = ["tm_number"]
CARRY_COLUMNS = ["filed_date"]
HIGH_CARDINALITY = ["mark_text", "owner_postcode_area"]
CLASS_COLUMNS = [f"class{i}" for i in range(1, 46)]
FEATURES = (["category", "mark_type", "series_flag", "series_marks_count",
             "nice_class_count", *CLASS_COLUMNS,
             "owner_country", "owner_region"])
COLUMNS = [*ID_COLUMNS, *FEATURES, *HIGH_CARDINALITY, *CARRY_COLUMNS,
           TARGET]

LABEL_SOURCE_COLUMNS = ["Status", "Published", "Registered", "Expired",
                        "Renewal Due Date"]
EXCLUDED_BY_DESIGN = ["Hyperlink", "Name"]

LAYOUT = {"train": "public/train.csv", "eval": "public/eval.csv",
          "holdout": "private/holdout.csv"}
SPLIT_WINDOWS = {
    "train": {"start": "2010-01-01", "end": "2013-01-01"},
    "eval": {"start": "2013-01-01", "end": "2015-01-01"},
    "holdout": {"start": "2015-01-01", "end": "2017-01-01"},
}

NEG_STATUSES = {"Refused", "Withdrawn"}
# Statuses implying the mark reached registration (label keys on the
# Registered date; recorded for the summary's status-level census only).
POS_LAPSED = {"Registered", "Merged", "Dead", "Removed", "Expired",
               "Cancelled", "Surrendered"}

# Field indices in the 62-column pipe-separated record.
F_TM, F_HYPERLINK, F_MARK, F_NAME = 0, 1, 2, 3
F_POSTCODE, F_REGION, F_COUNTRY, F_STATUS = 4, 5, 6, 7
F_CATEGORY, F_MARKTYPE, F_SERIES, F_NSERIES = 8, 9, 10, 11
F_FILED, F_PUBLISHED, F_REGISTERED, F_EXPIRED, F_RENEWAL = 12, 13, 14, 15, 16
F_CLASS_BASE = 17

# Expectations pinned from measured source metadata. The ORIGINAL frozen table
# (probe_aggregate.py 2026-10-27 plus the 2026-10-30 dedup-key probe) mis-read
# the 94 embedded-pipe rows at shifted positions (fields[7]/[12]/[14]
# left-anchored) and deduped late on the int key. The corrected table below is
# re-derived from the same sha256-pinned snapshot by
# probe_reconcile_pipe_rows.py (pass C == this build's pipeline, verified
# against the ipo-tm-002 worker's measured numbers; per-row attribution of
# every delta closed exactly; all 94 recovered rows verified against the
# publisher's own last-45-class column structure). The old table is preserved
# in git history and in ipo_tm_aggregates.json as a recorded probe-measurement
# error. The bytes are pinned, so every count below is deterministic and
# asserted.
EXPECTED = {
    "data_rows": 1_189_004,
    "field_count_distribution": {62: 1_188_910, 63: 76, 64: 15, 65: 3},
    "dup_rows_string_key": 16_909,
    "letter_suffix_rows": 22_812,
    "letter_suffix_dup_rows": 17,
    "blank_or_bad_filed_head": 34,   # rows whose (correct) Filed value fails
                                     # a 4-digit year check; the old 52
                                     # included 18 pipe rows whose SHIFTED
                                     # read ('No'/'Yes'/'Word'/'Figurative')
                                     # failed the check
    "unparseable_filed": 0,          # correct-column count; the old "3" was
                                     # the shifted read '3'/'5' of three pipe
                                     # rows whose recovered dates parse
    "neg_with_regdate_eligible": 8,
    "neg_with_regdate_post2010": 10,
    "per_year": {
        "2010": {"n": 30_372, "pos": 27_181, "neg": 3_187, "cens": 4},
        "2011": {"n": 36_364, "pos": 31_015, "neg": 5_338, "cens": 11},
        "2012": {"n": 40_275, "pos": 34_472, "neg": 5_797, "cens": 6},
        "2013": {"n": 46_362, "pos": 38_928, "neg": 7_365, "cens": 69},
        "2014": {"n": 51_084, "pos": 42_771, "neg": 8_210, "cens": 103},
        "2015": {"n": 54_300, "pos": 46_169, "neg": 7_953, "cens": 178},
        "2016": {"n": 61_681, "pos": 53_216, "neg": 7_834, "cens": 631},
    },
    "splits": {
        "train": {"rows": 106_990, "positives": 92_668, "censored": 21},
        "eval": {"rows": 97_274, "positives": 81_699, "censored": 172},
        "holdout": {"rows": 115_172, "positives": 99_385, "censored": 809},
    },
}

# IPO facts-and-figures workbook "Trade_marks_2016.xlsx", "Summary of trade
# mark activity", National UK applications column (read at discovery from
# https://assets.publishing.service.gov.uk/media/5a74c648e5274a3f93b48b43/
# Trade_marks_2016.xlsx; values pinned here so the worker fetches nothing
# beyond the data zip).
PUBLISHED_NATIONAL_APPLICATIONS = {2012: 40_238, 2013: 46_362, 2014: 51_016,
                                   2015: 54_320, 2016: 61_681}

PREDICTION_QUESTION = (
    "For a UK domestic trade mark application filed 2010-2016 - known at "
    "filing: mark text, Nice class coverage, category, mark type, series "
    "flag and series size, owner country/region/postcode area, filing date "
    "- will the mark reach registration as resolved in the IPO's frozen "
    "February-2018 open-data snapshot (Registered date recorded)? Unresolved "
    "applications at the snapshot (still in examination, opposition or "
    "appeal) are censored, never scored.")
PREDICTION_TIME = (
    "The application's filing date (Europe/London calendar day; register "
    "column 'Filed'). Every shipped feature is a filing-time attribute AS "
    "RECORDED IN the one frozen 2018-02-13 snapshot (sha256-pinned): mark "
    "text, category, mark type, series flag/count, Nice class booleans and "
    "count, owner country/region/postcode area. This is a clearly-labelled "
    "RETROSPECTIVE single-snapshot task: no historical operational "
    "availability is claimed, and no feature is derived from any other "
    "application's record. The outcome observation window is the snapshot "
    "itself (filed date .. 2018-02-13), so the target window never precedes "
    "the instant.")


def log(message: str) -> None:
    print(message, flush=True)


def fetch(url: str, work: Path) -> Path:
    """One anonymous GET of the pinned zip, verified by sha256 and size."""
    destination = work / "opendatadomestic.zip"
    digest = hashlib.sha256()
    total = 0
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=300) as response, \
            destination.open("wb") as handle:
        while True:
            block = response.read(1 << 20)
            if not block:
                break
            handle.write(block)
            digest.update(block)
            total += len(block)
    sha256 = digest.hexdigest()
    if total != PINNED_BYTES:
        raise SystemExit(f"download size {total} != pinned {PINNED_BYTES}")
    if sha256 != PINNED_SHA256:
        raise SystemExit(f"download sha256 {sha256} != pinned {PINNED_SHA256}")
    log(f"fetched {total} bytes, sha256={sha256} (pinned OK)")
    return destination


def iter_records(zip_path: Path, hazards: dict):
    """Stream UTF-16LE pipe-separated records out of the stored zip member.

    Right-anchored recovery: the 45 class columns are the LAST 45 fields;
    with k extra fields (k = len-62 >= 1, embedded pipes inside Mark Text -
    measured only there) the mark text absorbs fields 2..2+k.
    """
    import struct
    with zip_path.open("rb") as handle:
        pre = handle.read(30)
        if pre[:4] != b"PK\x03\x04":
            raise SystemExit("not a zip local-file record")
        nlen, elen = struct.unpack("<HH", pre[26:30])
        handle.read(nlen + elen)
        dec = zlib.decompressobj(-15)
        bytebuf = b""
        tail = ""
        header_seen = False
        while True:
            raw = handle.read(1 << 18)
            text_part = dec.decompress(raw, 0) if raw else dec.flush()
            if text_part:
                bytebuf += text_part
                usable = len(bytebuf) - (len(bytebuf) % 2)
                tail += bytebuf[:usable].decode("utf-16-le", "replace")
                bytebuf = bytebuf[usable:]
                lines = tail.split("\r")
                tail = lines[-1]
                for line in lines[:-1]:
                    line = line.strip("\n")
                    if not line.strip():
                        continue
                    if not header_seen:
                        header_seen = True
                        header = line.lstrip("\ufeff").split("|")
                        if len(header) != 62 or header[0].strip() != "Trade Mark" \
                                or header[7].strip() != "Status" \
                                or header[14].strip() != "Registered":
                            raise SystemExit(f"unexpected header: {header[:16]}")
                        continue
                    fields = line.split("|")
                    hazards["field_counts"][len(fields)] += 1
                    if len(fields) < 17:
                        hazards["short_rows"] += 1
                        continue
                    if len(fields) != 62:
                        extra = len(fields) - 62
                        classes = fields[-45:]
                        head = fields[:-45]
                        if len(head) != 17 + extra:
                            hazards["short_rows"] += 1
                            continue
                        mark_text = "|".join(head[2:3 + extra])
                        fields = [head[0], head[1], mark_text] + head[3 + extra:] + classes
                        hazards["pipe_recovered"] += 1
                    yield fields
            if not raw:
                break
        if tail.strip():
            hazards["trailing_partial_line"] += 1


def parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def new_hazards() -> dict:
    """The single hazards shape every iter_records caller must pass.

    check_fixtures once passed a bare Counter(), which made iter_records
    subscript the int a Counter returns for a missing key (ipo-tm-001,
    TypeError at line 253). Both call sites now share this constructor so
    the shape cannot drift between the fixture stage and the main build.
    """
    return {"field_counts": Counter(), "short_rows": 0,
            "pipe_recovered": 0, "trailing_partial_line": 0,
            "dup_rows": 0, "letter_suffix_rows": 0,
            "letter_suffix_dups": 0, "blank_or_bad_filed": 0,
            "unparseable_filed": 0, "class_value_anomalies": 0,
            "series_count_unparseable": 0}


def build_rows(zip_path: Path) -> tuple[dict, dict]:
    """Classify every distinct mark; return scored rows per split and diagnostics."""
    hazards = new_hazards()
    seen: set[str] = set()
    out_rows: dict[str, list[dict]] = {split: [] for split in LAYOUT}
    per_year: dict[str, Counter] = defaultdict(
        lambda: Counter({"n": 0, "pos": 0, "neg": 0, "cens": 0}))
    censored_statuses: Counter = Counter()
    neg_with_regdate = Counter({"eligible": 0, "post2010": 0})
    out_of_window: Counter = Counter()
    owner_stats = Counter()
    data_rows = 0

    for fields in iter_records(zip_path, hazards):
        data_rows += 1
        tm = fields[F_TM].strip().replace(" ", "")
        filed_raw = fields[F_FILED].strip()
        status = fields[F_STATUS].strip()
        regd = fields[F_REGISTERED].strip()

        numeric = True
        try:
            int(tm.replace("UK", "").lstrip("0") or "0")
        except ValueError:
            numeric = False
        letter_row = not numeric
        if letter_row:
            hazards["letter_suffix_rows"] += 1
        if tm in seen:
            hazards["dup_rows"] += 1
            if letter_row:
                hazards["letter_suffix_dups"] += 1
            continue
        seen.add(tm)

        if not filed_raw or not filed_raw[:4].isdigit():
            hazards["blank_or_bad_filed"] += 1
            continue
        filed = parse_date(filed_raw)
        if filed is None:
            hazards["unparseable_filed"] += 1
            continue

        # census over the wider post-2010 population the discovery probe measured
        if filed_raw[:4] >= "2010":
            if regd and status in NEG_STATUSES:
                neg_with_regdate["post2010"] += 1

        year = str(filed.year)
        if not (2010 <= filed.year <= 2016):
            out_of_window[year] += 1
            continue

        per_year[year]["n"] += 1
        if regd:
            label = 1
            per_year[year]["pos"] += 1
            if status in NEG_STATUSES:
                neg_with_regdate["eligible"] += 1
        elif status in NEG_STATUSES:
            label = 0
            per_year[year]["neg"] += 1
        else:
            per_year[year]["cens"] += 1
            censored_statuses[status or "(blank)"] += 1
            continue

        mark_text = " ".join(fields[F_MARK].split())
        category = " ".join(fields[F_CATEGORY].split()) or "unknown"
        mark_type = " ".join(fields[F_MARKTYPE].split()) or "unknown"
        series_flag = " ".join(fields[F_SERIES].split()) or "unknown"
        try:
            series_count = int(fields[F_NSERIES].strip() or "0")
        except ValueError:
            series_count = 0
            hazards["series_count_unparseable"] += 1
        classes = []
        nice_count = 0
        for offset in range(45):
            value = fields[F_CLASS_BASE + offset].strip()
            if value == "1":
                classes.append(1)
                nice_count += 1
            elif value in ("0", ""):
                classes.append(0)
            else:
                classes.append(1 if value else 0)
                hazards["class_value_anomalies"] += 1
        owner_country = " ".join(fields[F_COUNTRY].split()) or "unknown"
        owner_region = " ".join(fields[F_REGION].split()) or "unknown"
        owner_postcode = fields[F_POSTCODE].strip() or "unknown"
        owner_stats["uk_owners" if owner_country == "United Kingdom"
                   else "non_uk_owners"] += 1

        row = {
            "tm_number": tm,
            "mark_text": mark_text,
            "category": category,
            "mark_type": mark_type,
            "series_flag": series_flag,
            "series_marks_count": series_count,
            "nice_class_count": nice_count,
            "owner_country": owner_country,
            "owner_region": owner_region,
            "owner_postcode_area": owner_postcode,
            "filed_date": filed.isoformat(),
            TARGET: label,
        }
        for offset, value in enumerate(classes):
            row[CLASS_COLUMNS[offset]] = value

        if filed.year <= 2012:
            out_rows["train"].append(row)
        elif filed.year <= 2014:
            out_rows["eval"].append(row)
        else:
            out_rows["holdout"].append(row)

    diag = {
        "data_rows": data_rows,
        "distinct_marks": len(seen),
        "per_year": {y: dict(c) for y, c in sorted(per_year.items())},
        "censored_statuses": dict(censored_statuses.most_common()),
        "neg_with_regdate": dict(neg_with_regdate),
        "out_of_window": dict(sorted(out_of_window.items())),
        "owner_stats": dict(owner_stats),
        "hazards": {k: (dict(v) if isinstance(v, Counter) else v)
                    for k, v in hazards.items()},
    }
    return out_rows, diag


def check_fixtures(zip_path: Path) -> list[dict]:
    """The three recorded in-file fixtures, asserted against the fetched bytes."""
    fixtures = []
    seen = {}
    for fields in iter_records(zip_path, new_hazards()):
        tm = fields[F_TM].strip().replace(" ", "")
        if tm in ("UK00000000001", "UK00003171385", "UK00003041794"):
            seen[tm] = fields
    # 1. the first UK trade mark: identity/fidelity anchor.
    fields = seen.get("UK00000000001")
    if fields is None:
        raise SystemExit("fixture UK00000000001 (BASS) missing from snapshot")
    if " ".join(fields[F_MARK].split()) != "BASS & Co's PALE ALE":
        raise SystemExit(f"BASS mark text changed: {fields[F_MARK]!r}")
    if fields[F_STATUS].strip() != "Registered" or \
            fields[F_REGISTERED].strip() != "1876-01-01" or \
            fields[F_FILED].strip() != "1876-01-01":
        raise SystemExit("BASS fixture status/registered/filed changed")
    fixtures.append({"fixture": "UK00000000001 'BASS & Co's PALE ALE'",
                     "asserted": "in-file Registered with Registered date "
                                 "1876-01-01, filed 1876-01-01 (identity "
                                 "anchor; outside every scored cohort)",
                     "ok": True})
    # 2. 'Brexit' (2016): Appealed at snapshot, no Registered date -> censored.
    fields = seen.get("UK00003171385")
    if fields is None:
        raise SystemExit("fixture UK00003171385 (Brexit) missing")
    if " ".join(fields[F_MARK].split()) != "Brexit":
        raise SystemExit(f"Brexit mark text changed: {fields[F_MARK]!r}")
    if fields[F_FILED].strip() != "2016-06-25" or \
            fields[F_STATUS].strip() != "Appealed" or fields[F_REGISTERED].strip():
        raise SystemExit("Brexit fixture filed/status/registered changed")
    fixtures.append({"fixture": "UK00003171385 'Brexit' (filed 2016-06-25)",
                     "asserted": "status Appealed, Registered empty at the "
                                 "snapshot -> censored, excluded from the "
                                 "holdout cohort (the live register resolved "
                                 "it Refused later - outside this vintage)",
                     "ok": True})
    # 3. the long-examination tail: Application Published, never registered.
    fields = seen.get("UK00003041794")
    if fields is None:
        raise SystemExit("fixture UK00003041794 missing")
    if not " ".join(fields[F_MARK].split()).startswith("ALL NATURAL FRUITY V"):
        raise SystemExit(f"third fixture mark text changed: {fields[F_MARK]!r}")
    if fields[F_FILED].strip() != "2014-02-11" or \
            fields[F_STATUS].strip() != "Application Published" or \
            fields[F_REGISTERED].strip():
        raise SystemExit("third fixture filed/status/registered changed")
    fixtures.append({"fixture": "UK00003041794 (filed 2014-02-11)",
                     "asserted": "Application Published 2017-12-22 (34 months "
                                 "after filing), still unregistered at the "
                                 "snapshot -> censored: the long-examination "
                                 "tail must stay censored, never negative",
                     "ok": True})
    return fixtures


def assert_expectations(diag: dict, out_rows: dict) -> None:
    """Hard assertions against the discovery-measured record."""
    problems = []
    if diag["data_rows"] != EXPECTED["data_rows"]:
        problems.append(f"data_rows {diag['data_rows']} != {EXPECTED['data_rows']}")
    if dict(diag["hazards"]["field_counts"]) != EXPECTED["field_count_distribution"]:
        problems.append(f"field counts {dict(diag['hazards']['field_counts'])} "
                        f"!= {EXPECTED['field_count_distribution']}")
    if diag["hazards"]["dup_rows"] != EXPECTED["dup_rows_string_key"]:
        problems.append(f"dup rows {diag['hazards']['dup_rows']} "
                        f"!= {EXPECTED['dup_rows_string_key']}")
    if diag["hazards"]["letter_suffix_rows"] != EXPECTED["letter_suffix_rows"]:
        problems.append("letter-suffix row count changed")
    if diag["hazards"]["letter_suffix_dups"] != EXPECTED["letter_suffix_dup_rows"]:
        problems.append("letter-suffix dup count changed")
    if diag["hazards"]["blank_or_bad_filed"] != EXPECTED["blank_or_bad_filed_head"]:
        problems.append(f"blank/bad filed {diag['hazards']['blank_or_bad_filed']} "
                        f"!= {EXPECTED['blank_or_bad_filed_head']}")
    if diag["hazards"]["unparseable_filed"] != EXPECTED["unparseable_filed"]:
        problems.append(f"unparseable filed {diag['hazards']['unparseable_filed']} "
                        f"!= {EXPECTED['unparseable_filed']}")
    if diag["neg_with_regdate"]["eligible"] != EXPECTED["neg_with_regdate_eligible"]:
        problems.append(f"eligible neg-with-Registered-date rows "
                        f"{diag['neg_with_regdate']['eligible']} != "
                        f"{EXPECTED['neg_with_regdate_eligible']}")
    if diag["neg_with_regdate"]["post2010"] != EXPECTED["neg_with_regdate_post2010"]:
        problems.append(f"post-2010 neg-with-Registered-date rows "
                        f"{diag['neg_with_regdate']['post2010']} != "
                        f"{EXPECTED['neg_with_regdate_post2010']}")
    for year, expected in EXPECTED["per_year"].items():
        got = diag["per_year"].get(year)
        if got != expected:
            problems.append(f"cohort {year}: {got} != {expected}")
    for split, expected in EXPECTED["splits"].items():
        rows = out_rows[split]
        positives = sum(row[TARGET] for row in rows)
        negatives = len(rows) - positives
        if len(rows) != expected["rows"]:
            problems.append(f"{split}: {len(rows)} rows != {expected['rows']}")
        if positives != expected["positives"]:
            problems.append(f"{split}: {positives} positives != {expected['positives']}")
        if negatives != expected["rows"] - expected["positives"]:
            problems.append(f"{split}: {negatives} negatives != "
                           f"{expected['rows'] - expected['positives']}")
        censored = sum(diag["per_year"][str(y)]["cens"]
                       for y in SPLIT_YEARS[split])
        if censored != expected["censored"]:
            problems.append(f"{split}: {censored} censored != {expected['censored']}")
    # publisher cross-check: measured distinct-mark cohorts vs the workbook's
    # National UK applications, within +-1%.
    for year, published in PUBLISHED_NATIONAL_APPLICATIONS.items():
        measured = diag["per_year"][str(year)]["n"]
        rel = (measured - published) / published
        if abs(rel) > 0.01:
            problems.append(f"cross-check {year}: measured {measured} vs "
                            f"published {published} ({rel:+.2%}) exceeds +-1%")
    if problems:
        for problem in problems:
            print("ASSERTION FAILED:", problem, file=sys.stderr)
        raise SystemExit("construction does not reproduce the frozen record")


SPLIT_YEARS = {"train": range(2010, 2013), "eval": range(2013, 2015),
               "holdout": range(2015, 2017)}


def write_splits(out: Path, out_rows: dict) -> dict:
    stats = {}
    for split, relative in LAYOUT.items():
        destination = out / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        rows = out_rows[split]
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS,
                                    lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        positives = sum(row[TARGET] for row in rows)
        positive_dates = {row["filed_date"] for row in rows if row[TARGET]}
        negative_dates = {row["filed_date"] for row in rows if not row[TARGET]}
        stats[split] = {
            "rows": len(rows),
            "positives": positives,
            "negatives": len(rows) - positives,
            "positive_rate": round(positives / len(rows), 6) if rows else 0.0,
            "distinct_positive_filed_dates": len(positive_dates),
            "distinct_negative_filed_dates": len(negative_dates),
        }
        log(f"{split}: {stats[split]['rows']} rows, {positives} positives, "
            f"{len(positive_dates)} distinct positive filed dates")
    return stats


def assert_label_sources_absent(out: Path) -> None:
    for relative in LAYOUT.values():
        with (out / relative).open(newline="", encoding="utf-8") as handle:
            header = next(csv.reader(handle))
        forbidden = sorted(set(header) & set(LABEL_SOURCE_COLUMNS))
        if forbidden:
            raise SystemExit(f"{relative} ships label-source columns: {forbidden}")
        missing = [column for column in COLUMNS if column not in header]
        if missing:
            raise SystemExit(f"{relative} misses declared columns: {missing}")
        extra = [column for column in header if column not in COLUMNS]
        if extra:
            raise SystemExit(f"{relative} ships undeclared columns: {extra}")


def feature_measurement_entries() -> list[dict]:
    entries = [
        {"column": "tm_number",
         "unit": "register trade mark number (spaces stripped; letter-suffixed "
                 "series sub-marks stay distinct records)",
         "frame": "the application's own number as recorded in the snapshot; "
                  "id column, not a model input"},
        {"column": "mark_text", "unit": "register free text (whitespace collapsed)",
         "frame": "the mark as filed; declared high-cardinality (near-unique "
                  "per row), dropped by the runner's >1000-level rule"},
        {"column": "category", "unit": "register level, column 'Category of Mark' "
                                       "(blank -> 'unknown')",
         "frame": "the category recorded for the application (e.g. Standard)"},
        {"column": "mark_type", "unit": "register level, column 'Mark Type' "
                                        "(blank -> 'unknown')",
         "frame": "the mark's type recorded for the application "
                  "(e.g. Word, Figurative)"},
        {"column": "series_flag", "unit": "register level, column 'Series' "
                                          "(blank -> 'unknown')",
         "frame": "whether the application is part of a series"},
        {"column": "series_marks_count", "unit": "integer, column 'No of Marks "
                                                 "in Series' (0 when blank/unparseable)",
         "frame": "the number of marks in the series as recorded at filing"},
        {"column": "nice_class_count", "unit": "count of assigned Nice classes "
                                               "(0-45)",
         "frame": "sum of the row's class booleans as recorded in the snapshot"},
        {"column": "owner_country", "unit": "register text, column 'Country' "
                                            "(blank -> 'unknown')",
         "frame": "the owner's country as recorded in the snapshot"},
        {"column": "owner_region", "unit": "register text, column 'Region' "
                                           "(blank -> 'unknown')",
         "frame": "the owner's region as recorded in the snapshot (UK owners)"},
        {"column": "owner_postcode_area", "unit": "register text, column 'Postcode' "
                                                   "- the outward area code for UK "
                                                   "owners (blank -> 'unknown'); "
                                                   "declared high-cardinality",
         "frame": "the owner's postcode area as recorded in the snapshot; "
                  "blank for non-UK owners by the source's grain"},
        {"column": "filed_date", "unit": "ISO calendar date (Europe/London)",
         "frame": "the prediction instant itself (carry column, split time "
                  "column and clustered-event key)"},
        {"column": TARGET, "unit": "0/1 (1 = Registered date non-empty in the "
                                    "snapshot)",
         "frame": "the label: registered-by-snapshot"},
    ]
    for index, column in enumerate(CLASS_COLUMNS, start=1):
        entries.append({
            "column": column,
            "unit": f"0/1 - Nice class {index} assigned (snapshot value; "
                    f"non-{{0,1}} values counted as anomalies)",
            "frame": "the class coverage recorded for the application",
        })
    return entries


def quality_document(out: Path, stats: dict, diag: dict, built_at: str) -> None:
    positive_events = {split: {
        "positives": stats[split]["positives"],
        "distinct_events": stats[split]["distinct_positive_filed_dates"]}
        for split in LAYOUT}
    rate_note = ", ".join(f"{split} {stats[split]['positive_rate']}"
                          for split in LAYOUT)
    feature_evidence = {}
    for column in COLUMNS:
        if column == TARGET:
            continue
        if column == "tm_number":
            feature_evidence[column] = {
                "source": "register column 'Trade Mark' (spaces stripped)",
                "availability": "assigned to the application at filing; id column",
                "status": "verified"}
        elif column == "filed_date":
            feature_evidence[column] = {
                "source": "register column 'Filed'",
                "availability": "the prediction instant itself",
                "status": "verified"}
        elif column == "mark_text":
            feature_evidence[column] = {
                "source": "register column 'Mark Text' (whitespace collapsed)",
                "availability": "the mark as filed",
                "status": "assumed",
                "assumption": "snapshot-vintage value of a filing-time "
                              "attribute (mark text does not change "
                              "post-filing; embedded-pipe rows recovered "
                              "right-anchored, counted)"}
        elif column in ("category", "mark_type", "series_flag",
                        "series_marks_count", "nice_class_count"):
            feature_evidence[column] = {
                "source": f"register column for {column} (normalised)",
                "availability": "recorded for the application at filing",
                "status": "assumed",
                "assumption": "snapshot-vintage value of a filing-time "
                              "attribute"}
        elif column in CLASS_COLUMNS:
            feature_evidence[column] = {
                "source": f"register class column {column[5:].upper()}",
                "availability": "the class coverage recorded for the application",
                "status": "assumed",
                "assumption": "snapshot-vintage value: the publisher's guide "
                              "documents classes for the application; classes "
                              "can be narrowed post-filing, so the boolean is "
                              "the snapshot's view"}
        else:  # owner fields
            feature_evidence[column] = {
                "source": f"register owner column for {column} (normalised)",
                "availability": "the owner recorded for the application",
                "status": "assumed",
                "assumption": "snapshot-vintage value: ownership can move "
                              "after filing by assignment; the as-of policy is "
                              "uniform because there is exactly one vintage"}

    quality = {
        "name": NAME,
        "task": {"question": PREDICTION_QUESTION,
                 "prediction_time": PREDICTION_TIME},
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "time_column": "filed_date",
        "event_key_column": "filed_date",
        "event_key_note": (
            "the gate's clustered event count is distinct positive filing "
            "dates - a deliberately conservative same-day reading (marks "
            "filed the same day by different owners are in truth "
            "independent events; hundreds of distinct dates per split keep "
            "the count far above the gate minimum either way). The "
            "application-level event key is the trade mark number, unique "
            "per scored row"),
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "feature_documentation": (
            "every shipped feature is a filing-time attribute of the "
            "application itself: mark text, category, mark type, series "
            "flag/count, the 45 Nice class booleans and their count, owner "
            "country/region/postcode area, and the filing date. No shipped "
            "column is computed from any other application's record, and no "
            "history/aggregate feature exists. Not shipped, with reasons: "
            "Status, Published, Registered, Expired, Renewal Due Date (the "
            "label source and its post-filing companions); Hyperlink (an "
            "Excel formula wrapping the mark number); Name (free-text owner "
            "identity, excluded by the frozen handoff design - its removal "
            "also removes the trivial same-owner outcome-rate join a solver "
            "could otherwise build)"),
        "carry_columns": CARRY_COLUMNS,
        "id_columns": ID_COLUMNS,
        "high_cardinality_columns": HIGH_CARDINALITY,
        "high_cardinality_note": (
            "mark_text is near-unique per row and owner_postcode_area "
            "carries ~2k outward-code levels; both are declared rather than "
            "scored by the single-column AUC check, and the runner's "
            "baseline drops string columns over 1000 levels automatically. "
            "tm_number is the id column. No high-cardinality column "
            "encodes any other row's outcome"),
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "post_hoc_columns": ["Published", "Expired", "Renewal Due Date"],
        "measurements": feature_measurement_entries(),
        "known_event": {
            "name": "in-file snapshot fixtures (UK00000000001 'BASS & Co's "
                    "PALE ALE'; UK00003171385 'Brexit'; UK00003041794)",
            "expected_verdict": "as recorded in the frozen snapshot",
            "detail": (
                "three named rows asserted against the fetched bytes: the "
                "1876 BASS mark (Registered, Registered date 1876-01-01 - "
                "identity/fidelity anchor outside every scored cohort); "
                "'Brexit' UK00003171385 filed 2016-06-25, status Appealed "
                "and no Registered date at the snapshot -> censored, "
                "excluded from the holdout cohort (exercises the censoring "
                "rule); and UK00003041794 filed 2014-02-11, Application "
                "Published 2017-12-22 and still unregistered at the "
                "snapshot -> censored (the long-examination tail must stay "
                "censored, never negative). No external threshold is used "
                "by this task; the fixtures pin parsing, dedup and "
                "censoring semantics"),
            "source": "the fetched snapshot itself (values cross-checked at "
                      "discovery against the publisher's live register for "
                      "the Brexit mark)",
        },
        "timing": {
            "prediction_instant": {
                "kind": "event_time",
                "period": "day",
                "days_after_period_end": 0,
                "citation": (
                    "register column 'Filed' is the application's filing "
                    "date - the event time documented in the publisher's own "
                    "guide (ipo-data-explained-2016, section 5, and the "
                    "dataset landing page 'IPO trade mark data release', "
                    "last updated 13 Feb 2018); the question is resolved at "
                    "the filing event, and the snapshot is an administrative "
                    "record of applications"),
            },
            "features": {
                "period": "day",
                "published_days_after_period_end": 0,
                "source_kind": "administrative_record",
            },
            "row_selection": {
                "latest_period_used": "2016-12-31 (scored cohorts are "
                                      "filings 2010-01-01..2016-12-31; the "
                                      "2017-2018 cohorts exist in the "
                                      "snapshot and are excluded by "
                                      "eligibility, never by outcome)",
                "fields": ["Filed (filing date: cohort membership)"],
                "basis": (
                    "membership is fixed by the filing date alone. The "
                    "label rule runs after membership: a mark whose outcome "
                    "is unresolved at the frozen snapshot (still in "
                    "examination, opposition or appeal) is censored - "
                    "excluded from scoring and counted per cohort - which "
                    "is outcome-OBSERVABILITY conditioning recorded as a "
                    "limitation, never a label-value decision; censored "
                    "marks are not treated as negatives. Rows with blank or "
                    "unparseable filing dates cannot be placed on the "
                    "timeline and are excluded and counted"),
            },
            "observations": [],
        },
        "split_windows": SPLIT_WINDOWS,
        "split_boundaries": {
            "train": "filing years 2010-2012 (window end exclusive)",
            "eval": "filing years 2013-2014 (window end exclusive)",
            "holdout": "filing years 2015-2016 (window end exclusive; the "
                       "2017-2018 cohorts stay an unscored reserve outside "
                       "the frozen design)",
        },
        "positive_events": positive_events,
        "positive_events_note": (
            "positives and distinct positive filing dates per split, "
            "recomputed from the written rows; the gate re-verifies. "
            f"Positive rates: {rate_note}"),
        "expected_duplicate_ids": 0,
        "id_columns_are_entity_keys": True,
        "id_columns_note": (
            "tm_number names one application with one observed outcome in "
            "the snapshot; construction keeps one row per distinct mark "
            "number (multi-owner duplicate rows keep the first occurrence, "
            "16,909 rows removed and counted; the 22,812 letter-suffixed "
            "series sub-marks such as UK0000000052A/B are distinct records "
            "and stay). The identifier is unique across the artifact, so no "
            "id spans two splits"),
        "splits": LAYOUT,
        "evaluation_contract": {
            "use": "retrospective_research",
            "access": "isolated_rows",
            "training_label_timing": "unverified",
            "scope_note": (
                "each row is one application whose features are its own "
                "filing-time attributes as recorded in the single frozen "
                "2018-02-13 snapshot; the intended protocol predicts row-wise "
                "from the shipped columns (the shipped benchmark validator "
                "passes the whole table to the predictor, so isolated_rows is "
                "the design intent of this artifact's row-per-application "
                "contract, not a runtime-enforced protocol). Labeled eval is "
                "development/validation; the holdout is the final test and "
                "stays outside evaluated agents' workspaces. Training-label "
                "timing is UNVERIFIED: the publisher exposes one frozen "
                "snapshot and no historical vintages, so no full-row "
                "availability ledger can be constructed and no historical "
                "as-of availability is claimed - retrospective research "
                "only, never a certified historical forecasting setup"),
            "feature_evidence": feature_evidence,
            "vintage": {
                "kind": "as_of",
                "evidence": (
                    "exactly one frozen vintage for every row: the "
                    "publisher's 2018-02-13 open-data snapshot, fetched as a "
                    f"sha256-pinned 63,238,846-byte zip "
                    f"({PINNED_SHA256[:16]}..., Last-Modified 2018-02-13T13:"
                    "19:48Z); every shipped value is that snapshot's value "
                    "of a filing-time attribute. The publisher itself warns "
                    "the snapshot 'may not be directly comparable' with the "
                    "live register. No mixing of vintages occurs because no "
                    "other vintage exists"),
            },
            "selection": {
                "kind": "prediction_time",
                "evidence": (
                    "membership is fixed by filing date (cohorts 2010-2016); "
                    "eligibility never reads the label. Censoring excludes "
                    "1,002 eligible marks whose outcome is unresolved at the "
                    "snapshot (21/172/809 per split window, 0.31% of the "
                    "eligible population) and is outcome-observability "
                    "conditioning - counted per cohort and recorded as a "
                    "limitation; the 2017-2018 cohorts are excluded by the "
                    "frozen eligibility window (16,386 and 5,949 censored "
                    "there at discovery), not by outcome"),
            },
            "limitations": [
                "single frozen 2018-02-13 snapshot; no historical vintages "
                "exist, so no as-of reconstruction of any feature value and "
                "no operational-forecasting claim is possible",
                "owner fields are snapshot-vintage: assignment can move "
                "ownership after filing, so owner country/region/postcode "
                "may reflect a later owner; a robustness variant dropping "
                "owner fields is recorded as a future construction decision",
                "Nice class booleans are snapshot-vintage: classes can be "
                "narrowed post-filing, so coverage may overstate what was "
                "filed",
                "censoring conditions the scored population on outcomes "
                "resolvable within the snapshot: 1,002 eligible marks "
                "(0.31%; 631 of them in the 2016 cohort, 1.02%) remain "
                "unresolved and are excluded rather than labelled; their "
                "exclusion is a recorded selection bias, not a missing "
                "check",
                "the label window extends to the snapshot date (up to ~8 "
                "years for 2010 filings, ~13-25 months for 2016 filings), "
                "so 'registered-by-snapshot' mixes horizons across cohorts; "
                "per-year reporting is mandatory when quoting figures",
                "large repeat filers (one owner filing many marks) cluster "
                "outcomes statistically; owner Name is not shipped, so a "
                "same-owner join is not directly available to a solver, but "
                "dependence across one owner's marks remains a caveat for "
                "uncertainty estimates",
                "filing-year prevalence drifts (negatives 13.4% train / "
                "16.0% eval / 13.7% holdout): a prevalence shift between "
                "splits is a measured property of the cohorts",
            ],
            "cross_row_audit": {
                "probes": [
                    {"entity_columns": ["tm_number"],
                     "time_column": "filed_date",
                     "offset_days": 1,
                     "left": "class1",
                     "operation": "copy"},
                ],
                "rationale": (
                    "the plausible cross-row exposure family is "
                    "reverse-history: a later row at the same entity carrying "
                    "an earlier row's outcome inside a shipped feature. This "
                    "artifact cannot carry it: no shipped column is derived "
                    "from any other row (no history or aggregate features "
                    "exist), and each trade mark number appears exactly once "
                    "after construction dedup, so no donor row exists for "
                    "any scored row. The declared probe executes the "
                    "same-entity join on the full artifact and measures "
                    "exactly that: coverage is expected to be zero on every "
                    "split, and nonzero coverage would mean the dedup "
                    "failed. Coarser keys (owner country/region/postcode) "
                    "expose only other applications' own attributes, never "
                    "the scored row's outcome"),
                "auxiliary_files_review": (
                    "the artifact ships public/train.csv, public/eval.csv, "
                    "private/holdout.csv, meta.json, quality.json and "
                    "summary.json. summary.json carries construction "
                    "diagnostics only (per-cohort counts, hazard buckets, "
                    "fixture results, censored-status census) and no "
                    "per-row labels. No joint label matrix or other "
                    "solver-visible file exists in the artifact"),
            },
        },
    }
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")


def cross_check_measured(per_year: dict) -> dict:
    """Measured cohort sizes keyed to match the pinned published values.

    per_year is keyed by filing-year STRINGS ("2012"); the pinned workbook
    values in PUBLISHED_NATIONAL_APPLICATIONS are keyed by INT years. The
    ipo-tm-003 build crashed writing summary.json because the inline
    comprehension looked the int keys up in the string-keyed dict
    (KeyError: 2012) - AFTER every construction assertion had passed and
    all five artifact files were already written. Guarded by
    tests/test_ipo_tm_build.py (red on the pre-fix expression).
    """
    return {str(year): per_year[str(year)]["n"]
            for year in PUBLISHED_NATIONAL_APPLICATIONS}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--source", default=URL,
                        help="zip source: the URL (default) or a local zip "
                             "path for synthetic smoke runs")
    parser.add_argument("--built-at", default="1970-01-01T00:00:00Z",
                        help="pinned construction instant for "
                             "byte-reproducible rebuilds")
    args = parser.parse_args(argv)
    out = Path(args.out)
    work = Path(args.work_dir)
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)

    log("== fetch (pinned IPO snapshot zip, sha256-verified) ==")
    zip_path = Path(args.source) if args.source != URL else \
        fetch(args.source, work)

    log("== fixtures (asserted on the fetched bytes) ==")
    fixtures = check_fixtures(zip_path)
    for fixture in fixtures:
        log(f"fixture OK: {fixture['fixture']}")

    log("== parse + classify (streaming; dedup first occurrence) ==")
    out_rows, diag = build_rows(zip_path)
    log(f"data rows {diag['data_rows']}, distinct marks "
        f"{diag['distinct_marks']}, dup rows removed "
        f"{diag['hazards']['dup_rows']}, pipe-recovered "
        f"{diag['hazards']['pipe_recovered']}")
    for year, counts in diag["per_year"].items():
        log(f"cohort {year}: {counts}")

    log("== assertions against the frozen discovery record ==")
    assert_expectations(diag, out_rows)
    log("all assertions passed (cohorts, splits, fixtures, cross-check, hazards)")

    log("== write ==")
    stats = write_splits(out, out_rows)
    assert_label_sources_absent(out)
    log("label-source columns absent from all three files; column set exact")

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
        "split": ("cohort split on filing year: train 2010-2012, "
                  "eval 2013-2014, holdout 2015-2016"),
        "split_description": (
            "cohort split on filing year: train 2010-2012, eval 2013-2014, "
            "holdout 2015-2016; population is domestic applications with a "
            "parseable filing date inside a cohort window; marks whose "
            "outcome is unresolved at the frozen 2018-02-13 snapshot are "
            "censored - excluded and counted per cohort, never labelled "
            "negative"),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    quality_document(out, stats, diag, args.built_at)

    summary = {
        "name": NAME,
        "stage": "construction (no performance metric computed anywhere here)",
        "built_at_utc": args.built_at,
        "source": {"url": URL, "sha256": PINNED_SHA256,
                   "bytes": PINNED_BYTES,
                   "last_modified_header": "2018-02-13T13:19:48Z"},
        "classification": {
            "label_rule": "positive iff Registered date non-empty; negative "
                          "iff Registered empty AND status in {Refused, "
                          "Withdrawn}; everything else censored (excluded, "
                          "counted per cohort)",
            "neg_with_regdate": diag["neg_with_regdate"],
            "neg_with_regdate_note": (
                "the label keys on the Registered date: rows with a "
                "negative status AND a Registered date are positive (8 "
                "eligible rows; the discovery probe measured 10 on the "
                "wider post-2010 population, including the 2017-2018 "
                "cohorts)"),
            "censored_statuses_eligible": diag["censored_statuses"],
            "per_year": diag["per_year"],
            "out_of_window_per_year": diag["out_of_window"],
        },
        "identity": {
            "distinct_marks_total": diag["distinct_marks"],
            "dup_rows_removed": diag["hazards"]["dup_rows"],
            "letter_suffix_rows": diag["hazards"]["letter_suffix_rows"],
            "letter_suffix_dups": diag["hazards"]["letter_suffix_dups"],
            "dedup_rule": "first occurrence per stripped mark-number string; "
                          "letter-suffixed series sub-marks (e.g. "
                          "UK0000000052A) are distinct records",
        },
        "hazards": diag["hazards"],
        "owner_stats": diag["owner_stats"],
        "publisher_cross_check": {
            "workbook": "IPO facts-and-figures Trade_marks_2016.xlsx, "
                        "'Summary of trade mark activity', National UK "
                        "applications (values pinned from the discovery "
                        "read; +-1% asserted in-build)",
            "published": {str(k): v for k, v in
                          PUBLISHED_NATIONAL_APPLICATIONS.items()},
            "measured": cross_check_measured(diag["per_year"]),
        },
        "split_stats": stats,
        "fixtures": fixtures,
        "shipped_rows": total_rows,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    log(f"== done: {total_rows} scored rows written to {out} ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
