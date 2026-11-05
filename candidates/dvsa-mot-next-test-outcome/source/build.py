#!/usr/bin/env python3
"""DVSA/DfT anonymised MOT next-test-outcome construction (job dvsa-mot-build-001).

Candidate: dvsa-mot-next-test-outcome. This script ONLY constructs the runner-layout
artifact plus the diagnostics the qualification gate recomputes. NO performance
metric is computed anywhere here - no AUC, no accuracy, no rate presented as a
finding; the reference stage (score.py) runs only after the gate passes on the
full artifact and --accept re-verifies the exact bytes (run.sh enforces the order).

Task: at the completion instant of a vehicle's previous completed class-4 MOT test
(an administrative record written at the event), using only the vehicle's static
attributes as recorded on that prior test plus its prior-test history, predict
whether the vehicle's NEXT completed class-4 test ends in an initial failure
(test_result F or PRS, the publisher's documented "initial failure" definition)
rather than a clean pass (P). The next test's own fields (result, mileage, date,
defect items) are the label source and never ship.

Source (measured, anonymous, OGL v3.0 - see the candidate record):
  * 2005-2016  test_result_YYYY.txt.gz   at data.dft.gov.uk/anonymised-mot-test/test_data/
  * 2017-2022  dft_test_result_YYYY.zip  at data.dft.gov.uk/anonymised-mot-test/test_data/
  * 2023       dft_test_result_2023.zip  at the DVSA S3 origin (also mirrored at DfT)
  * 2024       "MOT testing data results (2024).zip" at the DVSA S3 origin
  The 2024 zip is pinned byte-exactly to the 2026-10-19 measurement
  (1,531,265,132 bytes, 12 members test_result_202401..202412.csv); a different
  vintage refuses the build. Older files were never fetched before, so the build
  RECORDS their sha256 as the construction vintage pin (a rebuild must match it).
  data.dft.gov.uk ignores Range headers (measured 2026-11-05) - all bulk transfer
  happens on the worker, never through the coordinator.

Population (pre-registered in the candidate record 2026-11-05, before any score):
  * class 4 (passenger cars) only, both sides of every pair; the publisher's own
    headline product (DVSA/MOT/01) is class-specific, which keeps the cross-check
    comparable. Tests with other class ids are skipped and counted.
  * vehicles deterministically hash-sampled: md5(vehicle_id) as int, mod 1000 == 0
    (~0.1%, fixed before any split/label look; outcome-independent, reproducible).
  * completed tests only: test_result in {P, F, PRS}. ABR/ABA rows (<0.6% measured)
    are excluded from both sides of every pair and counted.
  * pair (t_prev, t_next) = consecutive completed class-4 tests of one vehicle in
    (test_date, completed_date, file order). The row exists iff the PRIOR test's
    date lies in [2009-01-01, 2023-12-01); priors after 2023-11-30 are excluded so
    that no row needs a next test beyond the 2024-12 data end (right-censoring
    rule; it never reads the label). Tests 2005-2008 are history priming only.
  * splits are temporal on the PRIOR test's year (the prediction instant, the
    latest shipped knowable date): train priors 2009-2018, eval 2019-2021,
    holdout 2022-2023.11. The record's original next-test-year windows cannot be
    checked by the gate: the next test's date is label-side timing information
    and cannot ship. Recorded in the candidate record before launch.
  * label: next test result F or PRS -> 1, P -> 0. The label source column
    (next test_result) is not shipped; its absence from the shipped columns is
    asserted.

Shipped columns (runner contract: every non-target column is model input):
  row_key (id; vehicle_id + pair ordinal - unique by construction),
  vehicle_id (the publisher's pseudonym; declared high-cardinality; the cluster
    key for every uncertainty interval), prior_test_date (the prediction
    instant; time column), make, model, colour, fuel_type, cylinder_capacity,
  postcode_area (static attributes as recorded on the prior test's own row),
  vehicle_age_days, prior_initial_fail, prior_test_type, prior_days_since_last,
  prior_mileage, prior_mileage_delta, mileage_per_day_last, n_prior_tests,
  prior_fail_count, prior_fail_rate, days_since_first_test (history features
  computed only from tests at or before the prior test), next_initial_fail.

Timing posture (current-vintage retrospective): only the CURRENT files exist -
the publisher revised the 2017 file in June 2022 and publishes no historical
vintages - so every shipped feature is the current-vintage value of an
administrative record of an event at or before the prediction instant. No as-of
availability is claimed anywhere. Retrospective research only.

Stdlib only. No credentials in the container.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import sys
import threading
import time
import urllib.request
import zipfile
from datetime import date, timedelta
from pathlib import Path

NAME = "dvsa-mot-next-test-outcome"
TARGET = "next_initial_fail"
POSITIVE_LABEL = 1
ID_COLUMN = "row_key"
TIME_COLUMN = "prior_test_date"
EVENT_KEY_COLUMN = "vehicle_id"

CLASS_ID = "4"
SAMPLE_MODULUS = 1000
COMPLETED_RESULTS = {"P": 0, "F": 1, "PRS": 1}
EXCLUDED_RESULTS = ("ABR", "ABA")
ALLOWED_RESULTS = set(COMPLETED_RESULTS) | set(EXCLUDED_RESULTS)

WINDOW_START = date(2009, 1, 1)
WINDOW_END = date(2023, 12, 1)          # exclusive; priors on/after this are censored out
TRAIN_END = date(2019, 1, 1)
EVAL_END = date(2022, 1, 1)

# 2024 zip vintage pin, measured by ranged reads 2026-10-19 (candidate record).
ZIP_2024_BYTES = 1_531_265_132
ZIP_2024_MEMBERS = [f"test_result_2024{month:02d}.csv" for month in range(1, 13)]
ZIP_2024_HEADER = ("test_id,vehicle_id,test_date,test_class_id,test_type,test_result,"
                   "test_mileage,postcode_area,make,model,colour,fuel_type,"
                   "cylinder_capacity,first_use_date,completed_date")

DFT_BASE = "https://data.dft.gov.uk/anonymised-mot-test/test_data/"
S3_BASE = "https://edh-dvsa-data-gov-uk-files-prod.s3.eu-west-1.amazonaws.com/"
SOURCE_FILES = {}
for year in range(2005, 2017):
    SOURCE_FILES[year] = DFT_BASE + f"test_result_{year}.txt.gz"
for year in range(2017, 2023):
    SOURCE_FILES[year] = DFT_BASE + f"dft_test_result_{year}.zip"
SOURCE_FILES[2023] = S3_BASE + "dft_test_result_2023.zip"
SOURCE_FILES[2024] = S3_BASE + "MOT+testing+data+results+(2024).zip"

# Required source fields. completed_date is optional (believed absent pre-2017);
# static fields are optional only for history priming years but required on any
# row that can serve as a PRIOR (>=2009), asserted per-file at parse time.
FIELD_ALIASES = {
    "test_id": ("test_id", "testid"),
    "vehicle_id": ("vehicle_id", "vehicleid"),
    "test_date": ("test_date", "testdate"),
    "test_class_id": ("test_class_id", "test_class", "class_id", "class"),
    "test_type": ("test_type", "testtype"),
    "test_result": ("test_result", "result", "testresult"),
    "test_mileage": ("test_mileage", "mileage", "testmileage"),
    "postcode_area": ("postcode_area", "postcode"),
    "make": ("make",),
    "model": ("model",),
    "colour": ("colour", "color"),
    "fuel_type": ("fuel_type", "fueltype"),
    "cylinder_capacity": ("cylinder_capacity", "cylinders_cc", "cc"),
    "first_use_date": ("first_use_date", "firstusedate"),
    "completed_date": ("completed_date", "completeddate"),
}
POSITIONAL_14 = ("test_id", "vehicle_id", "test_date", "test_class_id", "test_type",
                "test_result", "test_mileage", "postcode_area", "make", "model",
                "colour", "fuel_type", "cylinder_capacity", "first_use_date")
POSITIONAL_15 = POSITIONAL_14 + ("completed_date",)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

COLUMNS = [ID_COLUMN, EVENT_KEY_COLUMN, TIME_COLUMN,
           "make", "model", "colour", "fuel_type", "cylinder_capacity",
           "postcode_area", "vehicle_age_days", "prior_initial_fail",
           "prior_test_type", "prior_days_since_last", "prior_mileage",
           "prior_mileage_delta", "mileage_per_day_last", "n_prior_tests",
           "prior_fail_count", "prior_fail_rate", "days_since_first_test",
           TARGET]

HIGH_CARDINALITY_COLUMNS = [EVENT_KEY_COLUMN, TIME_COLUMN]
LABEL_SOURCE_COLUMNS = ["next_test_result"]          # never shipped; asserted absent
FEATURES = [column for column in COLUMNS if column not in (ID_COLUMN, TARGET)]

DOWNLOAD_CHUNK = 8 * 1024 * 1024
PREFETCH_DEPTH = 2


class BuildError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise BuildError(message)


def sample_keep(vehicle_id: str) -> bool:
    digest = hashlib.md5(vehicle_id.encode("utf-8")).hexdigest()
    return int(digest, 16) % SAMPLE_MODULUS == 0


def split_of(prior_day: date) -> str | None:
    if prior_day < WINDOW_START or prior_day >= WINDOW_END:
        return None
    if prior_day < TRAIN_END:
        return "train"
    if prior_day < EVAL_END:
        return "eval"
    return "holdout"


def parse_day(value: str) -> date | None:
    value = (value or "").strip()
    if not DATE_RE.match(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def parse_mileage(value: str) -> float | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return number


# ---------------------------------------------------------------------------
# Source acquisition: stream to disk, hash while writing, delete after parsing.
# A small prefetch thread overlaps the next download with the current parse.
# ---------------------------------------------------------------------------

def download(url: str, destination: Path) -> dict:
    started = time.time()
    digest = hashlib.sha256()
    bytes_written = 0
    request = urllib.request.Request(url)
    request.add_header("User-Agent", "dataset-factory-construction/1.0")
    with urllib.request.urlopen(request, timeout=300) as response, \
            destination.open("wb") as handle:
        while True:
            block = response.read(DOWNLOAD_CHUNK)
            if not block:
                break
            handle.write(block)
            digest.update(block)
            bytes_written += len(block)
    return {"url": url, "bytes": bytes_written, "sha256": digest.hexdigest(),
            "seconds": round(time.time() - started, 1)}


class Prefetcher:
    """Downloads up to PREFETCH_DEPTH upcoming files while the parser works."""

    def __init__(self, years: list[int], work_dir: Path):
        self.years = years
        self.work_dir = work_dir
        self.queue: dict[int, Path] = {}
        self.receipts: dict[int, dict] = {}
        self.errors: dict[int, str] = {}
        self.cursor = 0
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _paths(self, year: int) -> Path:
        suffix = ".zip" if year >= 2017 else ".txt.gz"
        return self.work_dir / f"source_{year}{suffix}"

    def _run(self):
        while True:
            with self.lock:
                if self.cursor >= len(self.years):
                    return
                if len(self.queue) >= PREFETCH_DEPTH:
                    time.sleep(0.5)
                    continue
                year = self.years[self.cursor]
                self.cursor += 1
            try:
                self.receipts[year] = download(SOURCE_FILES[year], self._paths(year))
                with self.lock:
                    self.queue[year] = self._paths(year)
            except Exception as exc:  # noqa: BLE001 - reported, never silent
                with self.lock:
                    self.errors[year] = f"{type(exc).__name__}: {exc}"

    def take(self, year: int) -> Path:
        while True:
            with self.lock:
                if year in self.queue:
                    return self.queue.pop(year)
                if year in self.errors:
                    fail(f"download failed for {year}: {self.errors[year]}")
            time.sleep(0.5)


# ---------------------------------------------------------------------------
# Row parsing across the three file eras.
# ---------------------------------------------------------------------------

class RowParser:
    """Maps one source file's rows onto the internal field tuple."""

    def __init__(self, year: int, header_line: str, source_name: str):
        self.year = year
        self.source_name = source_name
        counts = {"|": header_line.count("|"), "\t": header_line.count("\t"),
                  ",": header_line.count(",")}
        self.delimiter = max(counts, key=counts.get)
        self.header = [field.strip().strip('"').lower() for field in
                      header_line.split(self.delimiter)]
        self.mapping = self._map_by_name() or self._map_by_position()
        if not self.mapping:
            fail(f"{source_name}: cannot map columns; header was {header_line[:400]!r}")
        self.first_line = header_line

    def _map_by_name(self) -> dict | None:
        mapping = {}
        for canonical, aliases in FIELD_ALIASES.items():
            for index, field in enumerate(self.header):
                if field in aliases:
                    mapping[canonical] = index
                    break
        required = ("vehicle_id", "test_date", "test_class_id", "test_type",
                    "test_result")
        if not all(name in mapping for name in required):
            return None
        return mapping

    def _map_by_position(self) -> dict | None:
        order = POSITIONAL_15 if len(self.header) >= 15 else POSITIONAL_14
        if len(self.header) < len(POSITIONAL_14):
            return None
        return {name: index for index, name in enumerate(order[:len(self.header)])}

    def fields(self, line: str) -> dict | None:
        parts = line.split(self.delimiter)
        if len(parts) < len(self.mapping):
            return None
        get = lambda name: parts[self.mapping[name]].strip().strip('"') \
            if name in self.mapping else ""
        return {name: get(name) for name in FIELD_ALIASES}

    def describe(self) -> dict:
        return {"year": self.year, "source": self.source_name,
                "delimiter": repr(self.delimiter),
                "header": self.first_line[:400]}


def open_text_lines(path: Path, year: int):
    """Yields (member_name, line) for a txt.gz or a zip of CSV members."""
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                yield path.name, line
        return
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            with archive.open(info, "r") as member:
                text = io.TextIOWrapper(member, encoding="utf-8",
                                        errors="replace")
                for line in text:
                    yield info.filename, line


def stream_tests(path: Path, year: int, stats: dict) -> list:
    """Parse one source file into slim internal test tuples (sampled class-4 only).

    A slim tuple: (vehicle_id, test_date, completed_date, test_type, test_result,
    mileage, make, model, colour, fuel_type, cylinder_capacity, first_use_date,
    postcode_area, file_seq). Memory stays flat because only sampled vehicles'
    rows are retained (~0.1%).
    """
    rows: list = []
    parser = None
    member_name = ""
    seq = 0

    def process(fields: dict) -> None:
        nonlocal seq
        stats["rows_seen"] = stats.get("rows_seen", 0) + 1
        result = fields["test_result"]
        if result not in ALLOWED_RESULTS:
            fail(f"{path.name}: unexpected test_result {result!r} at seq {seq}; "
                 f"row {fields!r}")
        stats["result_histogram"] = stats.get("result_histogram", {})
        stats["result_histogram"][result] = stats["result_histogram"].get(result, 0) + 1
        if fields["test_class_id"] != CLASS_ID:
            stats["other_class_rows"] = stats.get("other_class_rows", 0) + 1
            return
        stats["class4_rows"] = stats.get("class4_rows", 0) + 1
        if not sample_keep(fields["vehicle_id"]):
            return
        day = parse_day(fields["test_date"])
        if day is None:
            stats["bad_date_rows"] = stats.get("bad_date_rows", 0) + 1
            return
        if day.year != year:
            # Monthly members and annual files can carry boundary rows; keep the
            # row (it is a real test) but count the mismatch for the record.
            stats["off_year_rows"] = stats.get("off_year_rows", 0) + 1
        mileage = parse_mileage(fields["test_mileage"])
        seq += 1
        rows.append((fields["vehicle_id"], day.isoformat(),
                     fields["completed_date"][:10], fields["test_type"], result,
                     mileage, fields["make"] or "UNKNOWN", fields["model"] or "UNKNOWN",
                     fields["colour"] or "UNKNOWN", fields["fuel_type"] or "UNKNOWN",
                     fields["cylinder_capacity"], fields["first_use_date"],
                     fields["postcode_area"] or "UNKNOWN", seq))
        stats["sampled_rows"] = stats.get("sampled_rows", 0) + 1

    def looks_like_data(line: str, active: RowParser) -> bool:
        """True when the 'header' line is actually a data row (headerless era)."""
        parts = line.split(active.delimiter)
        if len(parts) < len(active.mapping):
            return False
        day = parse_day(parts[active.mapping["test_date"]].strip().strip('"'))
        result = parts[active.mapping["test_result"]].strip().strip('"')
        return day is not None and result in ALLOWED_RESULTS

    for name, line in open_text_lines(path, year):
        line = line.rstrip("\n").rstrip("\r")
        if not line:
            continue
        if parser is None or name != member_name:
            member_name = name
            stats.setdefault("members", []).append(name)
            if year == 2024 and line != ZIP_2024_HEADER:
                fail(f"2024 zip member {name}: header drift. expected "
                     f"{ZIP_2024_HEADER!r}, got {line[:400]!r}")
            parser = RowParser(year, line, f"{path.name}#{name}")
            stats.setdefault("file_schemas", []).append(parser.describe())
            if looks_like_data(line, parser):
                # Headerless era file: the first line is a data row; keep it.
                stats["headerless_members"] = stats.get("headerless_members", 0) + 1
                fields = parser.fields(line)
                if fields is not None:
                    process(fields)
            continue
        fields = parser.fields(line)
        if fields is None:
            stats["malformed_rows"] = stats.get("malformed_rows", 0) + 1
            continue
        process(fields)
    return rows


# ---------------------------------------------------------------------------
# Pair construction and feature derivation.
# ---------------------------------------------------------------------------

def build_pairs(all_rows: list, counters: dict) -> dict:
    """Dedup, group by vehicle, order, drop abandoned codes, emit pairs."""
    # Exact-duplicate projected rows (measured 2026-10-19: the files carry them,
    # e.g. byte-identical first rows; test_id alone is NOT unique).
    unique_rows = []
    seen = set()
    duplicates = 0
    for row in all_rows:
        key = row[:13]
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        unique_rows.append(row)
    counters["duplicate_rows_dropped"] = duplicates
    unique_rows.sort(key=lambda row: (row[0], row[1], row[2], row[13]))
    vehicles: dict[str, list] = {}
    for row in unique_rows:
        vehicles.setdefault(row[0], []).append(row)

    split_rows: dict[str, list] = {"train": [], "eval": [], "holdout": []}
    abandoned = 0
    excluded_late_priors = 0
    excluded_early_priors = 0
    gap_days: list[int] = []
    for vehicle_id, rows in vehicles.items():
        tests = []
        for row in rows:
            if row[4] in EXCLUDED_RESULTS:
                abandoned += 1
                continue
            tests.append(row)
        for index in range(len(tests) - 1):
            prior, nxt = tests[index], tests[index + 1]
            prior_day = date.fromisoformat(prior[1])
            nxt_day = date.fromisoformat(nxt[1])
            gap = (nxt_day - prior_day).days
            if prior_day >= WINDOW_END:
                excluded_late_priors += 1
                continue
            if prior_day < WINDOW_START:
                excluded_early_priors += 1
                continue
            split = split_of(prior_day)
            gap_days.append(gap)
            history = tests[:index + 1]
            row = make_row(vehicle_id, index + 1, prior, nxt, prior_day, gap,
                           history)
            split_rows[split].append(row)
    counters["abandoned_rows"] = abandoned
    counters["excluded_late_priors"] = excluded_late_priors
    counters["excluded_early_priors"] = excluded_early_priors

    gap_days.sort()
    def percentile(fraction):
        if not gap_days:
            return None
        return gap_days[min(len(gap_days) - 1, int(fraction * len(gap_days)))]
    counters["gap_days"] = {"p50": percentile(0.50), "p95": percentile(0.95),
                            "p99": percentile(0.99), "p995": percentile(0.995),
                            "max": gap_days[-1] if gap_days else None}
    return split_rows


def make_row(vehicle_id: str, pair_index: int, prior, nxt, prior_day, gap, history):
    """Derive every shipped field from tests at or before the prior test."""
    # Slim tuple layout (see stream_tests):
    # 0 vehicle_id, 1 test_date, 2 completed_date, 3 test_type, 4 result,
    # 5 mileage, 6 make, 7 model, 8 colour, 9 fuel_type, 10 cylinder_capacity,
    # 11 first_use_date, 12 postcode_area, 13 file_seq
    first_use = parse_day(prior[11])
    vehicle_age = (prior_day - first_use).days if first_use else -1

    prior_result = prior[4]
    prior_initial_fail = COMPLETED_RESULTS[prior_result]

    count = len(history)
    fail_count = sum(COMPLETED_RESULTS[test[4]] for test in history)
    first_test_day = date.fromisoformat(history[0][1])
    days_since_first = (prior_day - first_test_day).days

    if count >= 2:
        previous = history[-2]
        days_since_last = (prior_day - date.fromisoformat(previous[1])).days
        previous_mileage = previous[5]
        mileage_delta = (prior[5] - previous_mileage
                         if prior[5] is not None and previous_mileage is not None
                         else -1.0)
        per_day = mileage_delta / days_since_last if mileage_delta >= 0 and days_since_last > 0 else -1.0
    else:
        days_since_last = -1
        mileage_delta = -1.0
        per_day = -1.0

    return {
        ID_COLUMN: f"{vehicle_id}-{pair_index:04d}",
        EVENT_KEY_COLUMN: vehicle_id,
        TIME_COLUMN: prior_day.isoformat(),
        "make": prior[6], "model": prior[7], "colour": prior[8],
        "fuel_type": prior[9],
        "cylinder_capacity": int(prior[10]) if prior[10].strip().isdigit() else -1,
        "postcode_area": prior[12],
        "vehicle_age_days": vehicle_age,
        "prior_initial_fail": prior_initial_fail,
        "prior_test_type": prior[3] or "UNKNOWN",
        "prior_days_since_last": days_since_last,
        "prior_mileage": prior[5] if prior[5] is not None else -1.0,
        "prior_mileage_delta": mileage_delta,
        "mileage_per_day_last": per_day,
        "n_prior_tests": count,
        "prior_fail_count": fail_count,
        "prior_fail_rate": round(fail_count / count, 6),
        "days_since_first_test": days_since_first,
        TARGET: COMPLETED_RESULTS[nxt[4]],
    }


# ---------------------------------------------------------------------------
# Artifact writing and pre-registered anchors.
# ---------------------------------------------------------------------------

def positive_events_of(rows: list) -> dict:
    """Clustered positive-event count, mirroring the gate's own rule exactly:
    one distinct event per [:10] prefix of the event key among positive rows."""
    days = {row[EVENT_KEY_COLUMN][:10] for row in rows if row[TARGET] == POSITIVE_LABEL}
    return {"positives": sum(row[TARGET] for row in rows),
            "distinct_events": len(days)}


def write_artifact(out: Path, split_rows: dict, counters: dict) -> dict:
    for key in ("train", "eval", "holdout"):
        if not split_rows[key]:
            fail(f"split {key} is empty; the population filter matched nothing")
        positives = sum(row[TARGET] for row in split_rows[key])
        if positives == 0 or positives == len(split_rows[key]):
            fail(f"split {key} is single-class ({positives} positives of "
                 f"{len(split_rows[key])} rows) - a uniform split cannot carry "
                 f"a score and usually means a unit or frame error")
    for key in ("eval", "holdout"):
        events = positive_events_of(split_rows[key])
        if events["positives"] < 30:
            fail(f"{key} carries {events['positives']} positives, below the "
                 f"gate's minimum of 30")
        if events["distinct_events"] < 20:
            fail(f"{key} carries {events['distinct_events']} distinct positive "
                 f"vehicles, below the gate's minimum of 20")
        if not 0.05 <= events["positives"] / len(split_rows[key]) <= 0.5:
            fail(f"{key} positive rate {events['positives'] / len(split_rows[key]):.4f} "
                 f"is outside the pre-registered 0.05..0.50 sanity band "
                 f"(DVSA/MOT/01 class 3&4 initial-fail is 27.51% FY2025-26; the "
                 f"August-2024 prefix measured 22.1%)")

    # Row keys unique; no identifier spans two splits; rows inside their windows.
    seen: dict[str, str] = {}
    for key in ("train", "eval", "holdout"):
        for row in split_rows[key]:
            value = row[ID_COLUMN]
            if value in seen:
                fail(f"row key {value!r} appears in {seen[value]} and {key}")
            seen[value] = key
    for key, start, end in (("train", WINDOW_START, TRAIN_END),
                            ("eval", TRAIN_END, EVAL_END),
                            ("holdout", EVAL_END, WINDOW_END)):
        days = sorted(row[TIME_COLUMN] for row in split_rows[key])
        if days[0] < start.isoformat() or days[-1] >= end.isoformat():
            fail(f"split {key} rows [{days[0]}..{days[-1]}] fall outside the "
                 f"declared window [{start}..{end})")

    paths = {"train": out / "public" / "train.csv",
             "eval": out / "public" / "eval.csv",
             "holdout": out / "private" / "holdout.csv"}
    for key, path in paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = sorted(split_rows[key], key=lambda r: (r[TIME_COLUMN], r[ID_COLUMN]))
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    counts = {key: positive_events_of(split_rows[key])
              for key in ("train", "eval", "holdout")}
    for key in counts:
        counts[key]["rows"] = len(split_rows[key])
        counts[key]["positive_rate"] = round(counts[key]["positives"]
                                              / counts[key]["rows"], 6)

    meta = {
        "name": NAME,
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": [ID_COLUMN],
        "columns": COLUMNS,
        "rows": {key: counts[key]["rows"] for key in counts},
        "positive_rate": {key: counts[key]["positive_rate"] for key in counts},
        "split_description": (
            "temporal split on the prediction instant (the prior completed class-4 "
            "test's date): train priors 2009-2018, eval 2019-2021, holdout "
            "2022-2023.11; population = deterministically hash-sampled vehicles "
            "(md5(vehicle_id) mod 1000 == 0, ~0.1%), consecutive completed class-4 "
            "test pairs, prior date in [2009-01-01, 2023-12-01) so no row needs a "
            "next test beyond the 2024-12 data end; tests 2005-2008 are prior-"
            "history priming only; ABR/ABA rows (<0.6% measured) are excluded and "
            "counted"),
        "target_definition": (
            "1 if the vehicle's next completed class-4 MOT test ended in an "
            "initial failure (test_result F or PRS, the DfT/DVSA documented "
            "'initial failure' definition), 0 if it was a clean pass (P)"),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    # The label source (the next test's own test_result) is structurally absent.
    assert not (set(LABEL_SOURCE_COLUMNS) & set(COLUMNS)), "label source shipped"

    quality = QUALITY_JSON.copy()
    quality["positive_events"] = counts
    quality["split_windows"] = {
        "train": {"start": WINDOW_START.isoformat(), "end": TRAIN_END.isoformat()},
        "eval": {"start": TRAIN_END.isoformat(), "end": EVAL_END.isoformat()},
        "holdout": {"start": EVAL_END.isoformat(), "end": WINDOW_END.isoformat()},
    }
    quality["evaluation_contract"]["feature_evidence"] = FE_EVIDENCE.copy()
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")
    return counts


QUALITY_JSON = {
 "name": NAME,
 "target": TARGET,
 "positive_label": POSITIVE_LABEL,
 "id_columns": [ID_COLUMN],
 "features": FEATURES,
 "high_cardinality_columns": HIGH_CARDINALITY_COLUMNS,
 "carry_columns": [],
 "splits": {
  "train": "public/train.csv",
  "eval": "public/eval.csv",
  "holdout": "private/holdout.csv"
 },
 "time_column": TIME_COLUMN,
 "event_key_column": EVENT_KEY_COLUMN,
 "expected_duplicate_ids": 0,
 "id_columns_are_entity_keys": True,
 "external_threshold": False,
 "features_documented_at": "prediction_time",
 "label_source_columns": LABEL_SOURCE_COLUMNS,
 "post_hoc_columns": [
  "next_test_result",
  "next_test_date",
  "next_test_mileage",
  "next_completed_date",
  "next_test_id",
  "next_test_type"
 ],
 "task": {
  "prediction_time": "the completion instant of the vehicle's previous completed class-4 MOT test (the prior test's test_date; completed_date timestamp where the era's file carries it). The test record is an administrative record written at the event; the user guide (MOT Testing Data User Guide v5.1, part of the same OGL dataset) documents the test regime and result codes",
  "target_definition": "1 if the vehicle's next completed class-4 test ended in an initial failure (test_result F or PRS), 0 if a clean pass (P); ABR/ABA outcomes are excluded from both sides of every pair",
  "description": "at the previous test's completion, using static vehicle attributes as recorded on that prior test plus the vehicle's prior-test history (results, test types, mileage and deltas, counts), predict whether the vehicle's next completed MOT test initially fails"
 },
 "measurements": [
  {"column": "cylinder_capacity", "unit": "cubic centimetres (engine cylinder capacity)",
   "frame": "the value recorded on the prior test's own row of the DVSA/DfT anonymised MOT files; -1 when the row carries no parseable value"},
  {"column": "vehicle_age_days", "unit": "days",
   "frame": "prior test_date minus first_use_date as recorded on the prior test's row; -1 when first_use_date is absent/unparseable"},
  {"column": "prior_days_since_last", "unit": "days",
   "frame": "prior test_date minus the vehicle's previous completed class-4 test date, both from the same source files; -1 when no earlier completed test exists"},
  {"column": "prior_mileage", "unit": "miles (odometer reading recorded at the prior test)",
   "frame": "test_mileage of the prior test's own row; -1.0 when absent"},
  {"column": "prior_mileage_delta", "unit": "miles",
   "frame": "prior test_mileage minus the previous completed test's test_mileage; -1.0 when either side is absent"},
  {"column": "mileage_per_day_last", "unit": "miles per day",
   "frame": "prior_mileage_delta divided by prior_days_since_last; -1.0 when either input is missing"},
  {"column": "n_prior_tests", "unit": "count of tests",
   "frame": "completed class-4 tests of the vehicle at or before the prior test, within the 2005-2024 current-snapshot files"},
  {"column": "days_since_first_test", "unit": "days",
   "frame": "prior test_date minus the vehicle's first completed class-4 test date in the 2005-2024 window"}
 ],
 "timing": {
  "prediction_instant": {
   "kind": "event_time",
   "period": "D",
   "days_after_period_end": 0,
   "citation": "the prior test's own row in the DVSA/DfT anonymised MOT test files (an administrative record written at the test; completed_date timestamps exist in the 2017+ era, day-precision test_date in 2005-2016). The 2024-era header and result codes were measured 2026-10-19 and the 2024 zip is pinned byte-exactly; per-file observed headers are recorded in summary.json by this build"
  },
  "features": {
   "period": "D",
   "published_days_after_period_end": 0,
   "source_kind": "administrative_record"
  },
  "row_selection": {
   "latest_period_used": "2023-11",
   "fields": [
    "prior_test_date",
    "vehicle_id",
    "make",
    "model",
    "colour",
    "fuel_type",
    "cylinder_capacity",
    "postcode_area",
    "prior_initial_fail",
    "prior_test_type",
    "prior_days_since_last",
    "prior_mileage",
    "prior_mileage_delta",
    "n_prior_tests",
    "prior_fail_count"
   ],
   "basis": "scored rows are consecutive completed class-4 test pairs of deterministically hash-sampled vehicles (md5(vehicle_id) mod 1000 == 0) whose PRIOR test completed in 2009-01..2023-11; a prior test on/after 2023-12-01 is excluded because its next test could fall beyond the 2024-12 data end (right-censoring rule that never reads the label; excluded pairs counted); tests 2005-2008 are history priming only; ABR/ABA rows are excluded and counted. Both label values are retained in every window"
  },
  "observations": []
 },
 "evaluation_contract": {
  "use": "retrospective_research",
  "access": "isolated_rows",
  "training_label_timing": "unverified",
  "scope_note": "each row is one vehicle's next-test prediction at its prior test's completion; features are precomputed at construction and the runner predicts row-wise from the shipped columns. Labeled eval is development/validation; the holdout is the final test and stays outside evaluated agents' workspaces. Training-label timing is UNVERIFIED: the publisher provides no historical vintages (the 2017 file was revised in June 2022 per the CKAN notes), so no full-row availability ledger can be constructed - retrospective research only, never a certified historical forecasting setup",
  "vintage": {
   "kind": "current_snapshot",
   "evidence": "only the CURRENT per-year DVSA/DfT files exist (data.dft.gov.uk 2005-2022, DVSA S3 2023-2024); the publisher publishes no historical vintages, and its CKAN notes record that the 2017 file was revised in June 2022. Every shipped feature is the current-vintage value of an administrative record of an event at or before the prior test; no as-of value is claimed. The 2024 zip is byte-pinned to the 2026-10-19 measurement; every file's sha256 measured by this build is recorded in summary.json as the construction vintage pin"
  },
  "selection": {
   "kind": "prediction_time",
   "evidence": "membership is fixed by the prior test's completion date (2009-01-01 <= prior date < 2023-12-01) plus the deterministic vehicle hash bucket - both decidable at the prediction instant and never reading the label. The right-censoring exclusion (priors on/after 2023-12-01, whose next test could postdate the 2024-12 data end) is an observability rule applied before any label look; excluded pairs are counted, and within the retained window the measured next-test gap distribution (p99 reported in summary.json) shows the annual cycle closes inside the data end for the retained population"
  },
  "limitations": [
   "current_snapshot vintage: features are current-vintage values of event-time administrative records; the publisher revised the 2017 file in June 2022 and keeps no historical vintages, so values corrected after the event cannot be distinguished",
   "right-censoring: pairs whose next test occurred after 2024-12-31 are absent because the data window ends; the 2023-11-30 prior cutoff removes the outcome-conditioned tail (short-gap retests surviving late priors) wholesale, and the retained-window gap distribution is reported",
   "class 4 (passenger cars) only; other test classes are excluded and counted; a vehicle's tests in other classes are invisible to its history",
   "ABR/ABA outcomes (<0.6% measured in the 2024-08 prefix) are excluded from both sides of every pair",
   "deterministic vehicle hash sampling (md5 mod 1000 == 0, ~0.1%) bounds the artifact; sampling is outcome-independent and fixed before any split or label, but it is a sample, not the full panel",
   "training_label_timing is unverified: no as-of ledger exists for when any test row first appeared in the published files",
   "positives cluster by vehicle; the independent positive evidence is the declared distinct-vehicle count, not the row count",
   "cross-row exposure: a later pair of the same vehicle carries this row's label as its prior_initial_fail feature (measured by the declared probe); access is isolated_rows and the exposure is recorded, not eliminated",
   "labeled eval is development/validation, never an untouched final test; the holdout is the final test and remains sealed until the design is frozen"
  ],
  "cross_row_audit": {
   "probes": [
    {
     "entity_columns": [EVENT_KEY_COLUMN],
     "time_column": TIME_COLUMN,
     "lag_days_column": "prior_days_since_last",
     "left": "prior_initial_fail",
     "operation": "copy",
     "purpose": "blind-join label recovery: a donor row of the same vehicle whose prior test is this row's next test donates prior_initial_fail, which equals this row's label by construction; coverage measures how many rows a same-vehicle join can answer outright"
    }
   ],
   "probes_note": "the panel's serial structure is real and is measured, not argued away: for pair (t_prev, t_next) the NEXT pair (t_next, t_after) ships prior_initial_fail = result(t_next), which is exactly this row's label. The probe measures that exposure on the full artifact; coverage is expected to be high, which is why access is isolated_rows and the artifact is restricted retrospective research",
   "rationale": "rows are per-vehicle consecutive-test predictions whose history features are precomputed at construction; the runner predicts row-wise from shipped columns. The label source (the next test's own result/date/mileage/type) is absent from the shipped columns (asserted), but the same vehicle's later row legitimately carries the prior outcome as a feature, so the cross-row join exposure is declared and measured rather than denied",
   "auxiliary_files_review": "the extract ships exactly the runner layout - public/train.csv, public/eval.csv, private/holdout.csv, meta.json, quality.json - plus summary.json, which carries per-file receipts (urls, sizes, sha256, observed headers), population counts, gap statistics and per-year tables; no row-level source data and no performance metric. The downloaded source files stay in the job's scratch directory outside /output and are deleted; they are never uploaded"
  }
 }
}

FE_EVIDENCE = {
 "row_key": {
  "source": "derived: vehicle_id + the pair's 1-based ordinal within the vehicle's consecutive-test sequence",
  "availability": "unique row identity assigned at construction; names one next-test event",
  "status": "verified"
 },
 "vehicle_id": {
  "source": "the publisher's pseudonym over registration+VIN in the DVSA/DfT anonymised MOT files (pseudonymised by the publisher; measured in the row sample 2026-10-19)",
  "availability": "the record's own identity, present on every test row of the vehicle including the prior test",
  "status": "verified"
 },
 "prior_test_date": {
  "source": "test_date of the prior test's own row (completed_date timestamp where the era's file carries it)",
  "availability": "the prediction instant itself",
  "status": "verified"
 },
 "make": {
  "source": "make recorded on the prior test's own row",
  "availability": "vehicle attribute recorded on the prior test's administrative record",
  "status": "assumed",
  "assumption": "current-vintage value of an event-time record; the publisher revises files (2017 revised June 2022) and keeps no historical vintages"
 },
 "model": {
  "source": "model recorded on the prior test's own row",
  "availability": "vehicle attribute recorded on the prior test's administrative record",
  "status": "assumed",
  "assumption": "current-vintage value of an event-time record"
 },
 "colour": {
  "source": "colour recorded on the prior test's own row",
  "availability": "vehicle attribute recorded on the prior test's administrative record",
  "status": "assumed",
  "assumption": "current-vintage value of an event-time record"
 },
 "fuel_type": {
  "source": "fuel_type recorded on the prior test's own row",
  "availability": "vehicle attribute recorded on the prior test's administrative record",
  "status": "assumed",
  "assumption": "current-vintage value of an event-time record"
 },
 "cylinder_capacity": {
  "source": "cylinder_capacity recorded on the prior test's own row",
  "availability": "vehicle attribute recorded on the prior test's administrative record",
  "status": "assumed",
  "assumption": "current-vintage value of an event-time record"
 },
 "postcode_area": {
  "source": "postcode_area recorded on the prior test's own row",
  "availability": "vehicle attribute recorded on the prior test's administrative record",
  "status": "assumed",
  "assumption": "current-vintage value of an event-time record"
 },
 "vehicle_age_days": {
  "source": "derived: prior test_date minus first_use_date as recorded on the prior test's row",
  "availability": "derivable at the prior test from that row's own fields",
  "status": "assumed",
  "assumption": "first_use_date is a registry fact as of the current vintage"
 },
 "prior_initial_fail": {
  "source": "the prior test's own test_result (F or PRS -> 1, P -> 0), the documented initial-failure definition",
  "availability": "the prior test's outcome, completed at or before the prediction instant",
  "status": "assumed",
  "assumption": "current-vintage value of the prior test's result; post-hoc corrections cannot be distinguished"
 },
 "prior_test_type": {
  "source": "test_type (NT normal / RT retest) of the prior test's own row",
  "availability": "recorded on the prior test's administrative record",
  "status": "assumed",
  "assumption": "current-vintage value of an event-time record"
 },
 "prior_days_since_last": {
  "source": "derived: prior test_date minus the vehicle's previous completed class-4 test date, both in the same files",
  "availability": "both events precede the prediction instant",
  "status": "assumed",
  "assumption": "requires the earlier test to be present in the current snapshot; absent earlier rows shift the value"
 },
 "prior_mileage": {
  "source": "test_mileage of the prior test's own row",
  "availability": "recorded at the prior test",
  "status": "assumed",
  "assumption": "current-vintage value of an event-time record"
 },
 "prior_mileage_delta": {
  "source": "derived: prior test_mileage minus the previous completed test's test_mileage",
  "availability": "both events precede the prediction instant",
  "status": "assumed",
  "assumption": "same vintage caveat as prior_mileage"
 },
 "mileage_per_day_last": {
  "source": "derived: prior_mileage_delta / prior_days_since_last",
  "availability": "derived from events at or before the prediction instant",
  "status": "assumed",
  "assumption": "same vintage caveat as its inputs"
 },
 "n_prior_tests": {
  "source": "derived: count of the vehicle's completed class-4 tests at or before the prior test within the 2005-2024 files",
  "availability": "counts only past events",
  "status": "assumed",
  "assumption": "the count depends on the current snapshot containing all past tests; rows added/removed by revision shift it"
 },
 "prior_fail_count": {
  "source": "derived: count of initial failures among those prior tests",
  "availability": "counts only past events",
  "status": "assumed",
  "assumption": "same snapshot dependence as n_prior_tests"
 },
 "prior_fail_rate": {
  "source": "derived: prior_fail_count / n_prior_tests",
  "availability": "derived from past events only",
  "status": "assumed",
  "assumption": "same snapshot dependence as its inputs"
 },
 "days_since_first_test": {
  "source": "derived: prior test_date minus the vehicle's first completed class-4 test date in the window",
  "availability": "both events precede the prediction instant",
  "status": "assumed",
  "assumption": "the observed first test is the true first test only if the snapshot contains it"
 }
}


def main() -> int:
    argument = argparse.ArgumentParser()
    argument.add_argument("--out", required=True)
    argument.add_argument("--work-dir", required=True)
    argument.add_argument("--source-dir",
                          help="test mode: read local source_<year> files "
                               "instead of downloading (dry-run only)")
    args = argument.parse_args()
    out = Path(args.out)
    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    years = sorted(SOURCE_FILES)
    test_mode = bool(args.source_dir)
    all_rows: list = []
    receipts: dict[int, dict] = {}
    per_year: dict[int, dict] = {}
    prefetcher = None
    local_paths = {}
    if test_mode:
        source_dir = Path(args.source_dir)
        for year in years:
            suffix = ".zip" if year >= 2017 else ".txt.gz"
            local_paths[year] = source_dir / f"source_{year}{suffix}"
    else:
        prefetcher = Prefetcher(years, work)

    for year in years:
        started = time.time()
        if test_mode:
            path = local_paths[year]
            if not path.is_file():
                fail(f"test-mode source missing: {path}")
        else:
            path = prefetcher.take(year)
            receipts[year] = dict(prefetcher.receipts[year])
            if year == 2024 and receipts[year]["bytes"] != ZIP_2024_BYTES:
                fail(f"2024 zip is {receipts[year]['bytes']} bytes; the vintage "
                     f"pin is {ZIP_2024_BYTES} (measured 2026-10-19). The "
                     f"publisher's file changed - re-pin deliberately, never "
                     f"silently")
        stats: dict = {"year": year}
        rows = stream_tests(path, year, stats)
        if year == 2024 and stats.get("members") != ZIP_2024_MEMBERS:
            fail(f"2024 zip members {stats.get('members')} do not match the "
                 f"pinned 12 monthly members {ZIP_2024_MEMBERS}")
        if stats.get("sampled_rows", 0) == 0:
            fail(f"{year}: the class-4 sampled filter matched nothing "
                 f"(rows_seen={stats.get('rows_seen', 0)}; a silent empty filter "
                 f"means the build processed the wrong population)")
        all_rows.extend(rows)
        per_year[year] = stats
        stats["parse_seconds"] = round(time.time() - started, 1)
        print(f"{year}: rows_seen={stats.get('rows_seen', 0)} "
              f"class4={stats.get('class4_rows', 0)} "
              f"sampled={stats.get('sampled_rows', 0)} "
              f"results={json.dumps(stats.get('result_histogram', {}))}",
              flush=True)
        if not test_mode:
            path.unlink()          # parsed; free the disk before the next year

    counters: dict = {}
    split_rows = build_pairs(all_rows, counters)
    all_rows = []
    counts = write_artifact(out, split_rows, counters)

    per_split_per_year = {}
    for key in ("train", "eval", "holdout"):
        table: dict[str, dict] = {}
        for row in split_rows[key]:
            bucket = table.setdefault(row[TIME_COLUMN][:4], {"rows": 0, "positives": 0})
            bucket["rows"] += 1
            bucket["positives"] += row[TARGET]
        per_split_per_year[key] = table

    summary = {
        "job": "dvsa-mot-build-001",
        "name": NAME,
        "source_vintage": {
            "files": len(receipts),
            "receipts": {str(year): receipts[year] for year in sorted(receipts)},
            "pin_note": ("the 2024 zip is asserted byte-equal to the 2026-10-19 "
                         "measurement (1,531,265,132 bytes, 12 monthly members, "
                         "header verified verbatim); every sha256 above is the "
                         "construction vintage pin a rebuild must match"),
            "range_note": ("data.dft.gov.uk ignores Range headers (measured "
                           "2026-11-05), so all DfT-era bulk transfer happens "
                           "on this worker; the DVSA S3 origin answers ranged "
                           "reads"),
        },
        "population": {"per_year": {str(year): per_year[year] for year in years}},
        "pairs": counters,
        "splits": counts,
        "per_split_per_year": per_split_per_year,
        "cross_check": {
            "publisher_product": ("DVSA/MOT/01 MOT test results by class of "
                                  "vehicle (gov.uk): FY2025-26 classes 3&4 "
                                  "initial fail 27.51% / final 22.30%; classes "
                                  "1&2 13.40%; class 7 34.00% (read 2026-10-19)"),
            "ours": {key: counts[key]["positive_rate"] for key in counts},
            "note": ("our rates are next-tests-with-prior-history for the "
                     "hash-sampled class-4 population, by prior-test year; same "
                     "magnitude expected, not an equality the build asserts"),
        },
        "no_metric_computed": ("no AUC, accuracy or rate-vs-label performance "
                               "number is computed anywhere in this build; "
                               "score.py runs only after the gate passes and "
                               "--accept re-verifies the exact bytes"),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({"splits": {key: {k: counts[key][k] for k in
                                       ("rows", "positives", "distinct_events")}
                                 for key in counts},
                      "pairs": {k: counters[k] for k in
                                ("duplicate_rows_dropped", "abandoned_rows",
                                 "excluded_late_priors", "excluded_early_priors")},
                      "gap_days": counters.get("gap_days"),
                      "files": {"train": "public/train.csv", "eval": "public/eval.csv",
                                "holdout": "private/holdout.csv"}}), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as error:
        print(f"BUILD FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)

