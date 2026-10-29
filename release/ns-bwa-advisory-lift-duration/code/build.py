#!/usr/bin/env python3
"""Construction for the `ns-bwa-advisory-lift-duration` prediction task.

One row per issued boil water advisory in the Nova Scotia advisory register.
The question: at the moment a boil water advisory is issued for a public
registered or municipal drinking water supply in Nova Scotia - known then:
site name, county, facility type, reason for the report, calendar season, and
the prior advisory history of the same site/county computed only from earlier
advisories - will the advisory be lifted within 30 days?

This file ONLY constructs the artifact and its gate diagnostics:
public/train.csv, public/eval.csv, private/holdout.csv, meta.json,
quality.json, summary.json. No performance metric (AUC, accuracy, any model
score) is computed anywhere in it; references run in score.py after the gate
passed and --accept re-verified the exact bytes.

Design frozen per the candidate record (construction_handoff):
  * source: the Socrata full-CSV export of data.novascotia.ca dataset
    7t68-9xmm, one anonymous GET (~284 KB), pinned by sha256; quarterly
    updates are expected, so the fetch re-measures every count and base rate
    against the numbers recorded at discovery and records the comparison;
  * population: advisories with a parseable issue date inside a scored
    window (train 2008-2017, eval 2018-2020, holdout 2021-2024, by issue
    year) and issue date <= register vintage minus 30 days (every scored
    row's 30-day target window closes before the vintage; the rule does not
    bind inside the windows but is asserted anyway);
  * label: lift30 = 1 iff (removal date - issue date) <= 30 days, inclusive;
    recomputed from the two date columns, never from the register's own
    'Length of Advisory in Days' (which is label source, not shipped);
  * censoring: rows with a blank removal date are advisories still in
    effect at the vintage (publisher-documented semantics) - excluded from
    scored sets and counted per window, never treated as observed non-lifts;
  * invalid outcomes: rows whose removal date precedes the issue date
    (negative duration - the register contradicting itself) are excluded as
    unverified outcomes and counted; the three rows measured at discovery
    are asserted by site and issue date when the vintage is unchanged;
  * features: issuance attributes (site, county, facility type, reason with
    variant normalisation, calendar month/day-of-week) plus as-of site and
    county history computed ONLY from register rows with a strictly earlier
    issue date; a prior advisory's lift30 outcome enters a history rate only
    when its removal date is also strictly earlier than the scored row's
    issue date (resolved before the instant);
  * messy identity: site/county keys are lowercased with collapsed
    whitespace; history events are de-duplicated per (key, issue date) with
    a stated representative rule; blank-county rows never enter any county
    history and carry sentinel history features.

Licence: Open Government Licence - Nova Scotia v1.1 (class A in the
candidate record). The OGL-NS attribution statement carries to any release.
Derived research dataset - never an official Government of Nova Scotia
product.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

NAME = "ns-bwa-advisory-lift-duration"
URL = ("https://data.novascotia.ca/api/views/7t68-9xmm/rows.csv"
       "?accessType=DOWNLOAD")
UA = ("Scout-factory-build/1.0 (dataset-factory worker construction; "
      "Nova Scotia open data register)")

TARGET = "lift30"
POSITIVE_LABEL = 1
THRESHOLD_DAYS = 30
SENTINEL = -1

ID_COLUMNS = ["advisory_id"]
CARRY_COLUMNS = ["issue_date"]
FEATURES = [
    "site_name",
    "county",
    "facility_type",
    "reason",
    "issue_month",
    "issue_dow",
    "site_prior_advisories",
    "site_days_since_last",
    "site_prior_resolved",
    "site_prior_lift30_rate",
    "site_active_prior",
    "county_prior_advisories",
    "county_days_since_last",
    "county_prior_resolved",
    "county_prior_lift30_rate",
    "county_active_prior",
]
HIGH_CARDINALITY = ["site_name", "issue_date"]
COLUMNS = ID_COLUMNS + CARRY_COLUMNS + FEATURES + [TARGET]
LAYOUT = {"train": "public/train.csv",
          "eval": "public/eval.csv",
          "holdout": "private/holdout.csv"}

# The label source and every post-instant field. None of these may appear in
# the written files; the build asserts their absence after writing.
LABEL_SOURCE_COLUMNS = [
    "date_advisory_removed", "length_of_advisory_in_days", "lift14",
]
POST_HOC_COLUMNS = LABEL_SOURCE_COLUMNS  # the only post-instant fields exist

# Split windows on the issue date (start inclusive, end exclusive).
WINDOWS = {
    "train": (date(2008, 1, 1), date(2018, 1, 1)),
    "eval": (date(2018, 1, 1), date(2021, 1, 1)),
    "holdout": (date(2021, 1, 1), date(2025, 1, 1)),
}

# Numbers recorded at discovery (probe_ns_csv_verify_out.json, register
# sha256 60f77ac4..., vintage 2026-06-16). The build re-measures everything
# and compares; a changed vintage is recorded, not silently absorbed.
RECORDED_SHA256 = ("60f77ac4945ca824700f5bcd3eaf564f4e5c5d4ec3f08496e8"
                   "dd796e7184a30a")
RECORDED = {
    "rows": 2649,
    "labeled": {"train": 1069, "eval": 372, "holdout": 886, "other": 249},
    "censored": {"train": 2, "eval": 1, "holdout": 10, "other": 30},
    "lift30": {"train": 0.6688, "eval": 0.6048, "holdout": 0.5824},
    "negative_duration_rows": 3,
    "zero_duration_rows": 5,
    "no_issue_year_rows": 30,
    "missing_reason": 5,
    "missing_facility_type": 57,
}

# The three negative-duration rows measured at discovery (site, issue date).
KNOWN_NEGATIVE = {
    ("mcintyre's h. cottages (baddeck)", date(2021, 9, 10)),
    ("pid 50323732", date(2023, 10, 13)),
    ("naugler's ultramar - italy cross", date(2025, 3, 21)),
}

EXPECTED_HEADERS = {
    "site name", "county", "date advisory issued", "date advisory removed",
    "facility type", "length of advisory in days", "reason for the report",
}

DATE_FORMATS = ("%B %d %Y", "%b %d %Y", "%B %d, %Y", "%b %d, %Y")


def log(message: str) -> None:
    print(message, flush=True)


def normalize(text: str | None) -> str:
    """Lowercase, strip and collapse whitespace - the stated identity rule."""
    return " ".join((text or "").split()).strip().lower()


def normalize_reason(text: str | None) -> str:
    value = normalize(text)
    if not value:
        return "unknown"
    if value in ("e.coli present", "e coli present"):
        value = "e. coli present"  # measured publisher spelling variants
    return value


def parse_date(text: str | None):
    value = normalize(text)
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def fetch(source: str, work: Path) -> tuple[bytes, dict]:
    if source.startswith("http"):
        last_error = None
        for attempt in range(3):
            try:
                request = urllib.request.Request(source, headers={"User-Agent": UA})
                with urllib.request.urlopen(request, timeout=120) as response:
                    data = response.read()
                    modified = response.headers.get("Last-Modified")
                sha = hashlib.sha256(data).hexdigest()
                vintage = None
                if modified:
                    try:
                        vintage = parsedate_to_datetime(modified).date()
                    except (TypeError, ValueError):
                        vintage = None
                info = {"url": source, "bytes": len(data), "sha256": sha,
                        "last_modified_header": modified, "vintage_date": (
                            vintage.isoformat() if vintage else None),
                        "fetch_attempts": attempt + 1}
                return data, info
            except Exception as exc:  # noqa: BLE001 - retried network fetch
                last_error = exc
                log(f"fetch attempt {attempt + 1} failed: {exc}; retrying")
                time.sleep(5 * (attempt + 1))
        raise SystemExit(f"fetch failed after 3 attempts: {last_error}")
    path = Path(source)
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    return data, {"url": f"file:{path}", "bytes": len(data), "sha256": sha,
                  "last_modified_header": None, "vintage_date": None,
                  "fetch_attempts": 0, "note": "local source (smoke test)"}


def parse_register(data: bytes) -> tuple[list[dict], dict]:
    text = data.decode("utf-8-sig", "replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = {normalize(name) for name in reader.fieldnames or []}
    if headers != EXPECTED_HEADERS:
        raise SystemExit(f"register schema changed: headers={sorted(headers)}")
    rows = []
    hazards = {
        "unparseable_issue_values": Counter(),
        "unparseable_removal_values": Counter(),
        "negative_duration": [],
        "zero_duration": 0,
        "length_column_disagreements": 0,
        "missing_county": 0,
        "missing_facility_type": 0,
        "missing_reason": 0,
    }
    for index, raw in enumerate(reader, start=1):
        issue = parse_date(raw.get("Date Advisory Issued"))
        removal_text = (raw.get("Date Advisory Removed") or "").strip()
        removal = parse_date(removal_text)
        if raw.get("Date Advisory Issued") and issue is None:
            hazards["unparseable_issue_values"][
                normalize(raw.get("Date Advisory Issued"))] += 1
        if removal_text and removal is None:
            hazards["unparseable_removal_values"][normalize(removal_text)] += 1
        length = None
        try:
            length = int(str(raw.get("Length of Advisory in Days")).strip())
        except (TypeError, ValueError):
            pass
        duration = (removal - issue).days if (issue and removal) else None
        if duration is not None and duration < 0:
            hazards["negative_duration"].append(
                {"site": normalize(raw.get("Site Name")),
                 "issue": issue.isoformat(), "removal": removal.isoformat(),
                 "duration": duration})
        if duration == 0:
            hazards["zero_duration"] += 1
        if duration is not None and length is not None and duration != length:
            hazards["length_column_disagreements"] += 1
        if not normalize(raw.get("County")):
            hazards["missing_county"] += 1
        if not normalize(raw.get("Facility Type")):
            hazards["missing_facility_type"] += 1
        if not normalize(raw.get("Reason for the Report")):
            hazards["missing_reason"] += 1
        rows.append({
            "advisory_id": f"ns{index:06d}",
            "site": normalize(raw.get("Site Name")),
            "county": normalize(raw.get("County")),
            "facility": normalize(raw.get("Facility Type")) or "unknown",
            "reason": normalize_reason(raw.get("Reason for the Report")),
            "issue": issue,
            "removal": removal,
            "removal_blank": not removal_text,
            "duration": duration,
        })
    return rows, hazards


def check_fixtures(rows: list[dict]) -> list[dict]:
    """The two in-file fixtures pin parsing, duration arithmetic, inclusivity.

    Maple Meadows Campground Inc (issued 2024-08-31, removed 2025-07-04,
    307 days) must land in the holdout window with lift30 = 0. Canning
    (issued 2025-10-02, removed 2025-10-03) is out of every scored window by
    the frozen design; it is asserted on the fetched register to pin the
    one-day positive, not as a scored row.
    """
    maple = [row for row in rows
             if row["site"].startswith("maple meadows")
             and row["issue"] == date(2024, 8, 31)]
    if len(maple) != 1:
        raise SystemExit(f"Maple Meadows fixture matched {len(maple)} rows")
    row = maple[0]
    if row["removal"] != date(2025, 7, 4) or row["duration"] != 307:
        raise SystemExit(f"Maple Meadows fixture changed: removal="
                         f"{row['removal']} duration={row['duration']}")
    canning = [row for row in rows
               if row["issue"] == date(2025, 10, 2)
               and row["removal"] == date(2025, 10, 3)]
    if len(canning) != 1:
        raise SystemExit(f"Canning fixture matched {len(canning)} rows")
    if canning[0]["duration"] != 1:
        raise SystemExit("Canning fixture duration is not 1 day")
    fixtures = [
        {"name": "maple meadows campground inc 2024-08-31",
         "expected": "307 days -> lift30 = 0 (holdout window)",
         "observed": f"duration={row['duration']} label="
                     f"{int(row['duration'] <= THRESHOLD_DAYS)}",
         "split": "holdout"},
        {"name": "canning 2025-10-02 (out of scored windows)",
         "expected": "1 day -> lift30 = 1 on the register",
         "observed": f"duration={canning[0]['duration']} label="
                     f"{int(canning[0]['duration'] <= THRESHOLD_DAYS)}",
         "split": "not scored (issue year 2025)"},
    ]
    return fixtures


def check_recorded(rows: list[dict], fetch_info: dict, hazards: dict) -> dict:
    """Re-measure the discovery numbers; a changed vintage is recorded.

    Only the register-identity comparison is skipped for synthetic smoke
    input (--skip-vintage-checks); the named fixtures always run.
    """
    same_vintage = fetch_info["sha256"] == RECORDED_SHA256
    # Reproduce the discovery probe's per-window counts on this register:
    # issued (parseable issue date in window), labeled (removal present),
    # censored (blank removal), lift30 rate over labeled rows.
    reproduction = {}
    for row in rows:
        if row["issue"] is None:
            continue
        split = window_of(row["issue"])
        key = split if split else "other"
        entry = reproduction.setdefault(key, {"issued": 0, "labeled": 0,
                                              "censored": 0,
                                              "labeled_positives": 0})
        entry["issued"] += 1
        if row["removal_blank"]:
            entry["censored"] += 1
        if row["removal"] is not None:
            entry["labeled"] += 1
            if row["duration"] is not None and row["duration"] <= THRESHOLD_DAYS:
                entry["labeled_positives"] += 1
    comparison = {"sha256_same_as_discovery": same_vintage,
                  "recorded_sha256": RECORDED_SHA256,
                  "fresh_sha256": fetch_info["sha256"]}
    window_table = {}
    for key, entry in sorted(reproduction.items()):
        rate = (round(entry["labeled_positives"] / entry["labeled"], 4)
                if entry["labeled"] else None)
        recorded_label = RECORDED["labeled"].get(key)
        recorded_rate = RECORDED["lift30"].get(key)
        window_table[key] = {
            "issued": entry["issued"],
            "labeled": entry["labeled"],
            "recorded_labeled": recorded_label,
            "labeled_delta": (entry["labeled"] - recorded_label
                              if recorded_label is not None else None),
            "censored": entry["censored"],
            "recorded_censored": RECORDED["censored"].get(key),
            "lift30_rate_labeled": rate,
            "recorded_lift30_rate": recorded_rate,
        }
    comparison["windows"] = window_table
    if same_vintage:
        if len(rows) != RECORDED["rows"]:
            raise SystemExit(
                f"register sha256 matches discovery but rows differ: "
                f"{len(rows)} vs {RECORDED['rows']}")
        for key, recorded_label in RECORDED["labeled"].items():
            fresh = reproduction.get(key, {}).get("labeled", 0)
            if fresh != recorded_label:
                raise SystemExit(
                    f"register sha256 matches discovery but {key} labeled "
                    f"count differs: {fresh} vs {recorded_label}")
        for key, recorded_rate in RECORDED["lift30"].items():
            fresh = window_table.get(key, {}).get("lift30_rate_labeled")
            if fresh is not None and abs(fresh - recorded_rate) > 0.005:
                raise SystemExit(
                    f"register sha256 matches discovery but {key} lift30 "
                    f"rate differs: {fresh} vs {recorded_rate}")
        if len(hazards["negative_duration"]) != RECORDED["negative_duration_rows"]:
            raise SystemExit("negative-duration count changed at the same sha")
        neg_sites = {(entry["site"], date.fromisoformat(entry["issue"]))
                     for entry in hazards["negative_duration"]}
        if neg_sites != KNOWN_NEGATIVE:
            raise SystemExit(f"negative-duration rows changed at the same sha: "
                             f"{sorted(neg_sites)}")
    else:
        if len(rows) < RECORDED["rows"] * 0.9:
            raise SystemExit(f"fresh register has only {len(rows)} rows "
                             f"(recorded {RECORDED['rows']}); review before build")
        log(f"NOTE: register vintage changed (sha256 differs); "
            f"re-measuring and recording against the recorded numbers")
    comparison["rows"] = {"fresh": len(rows), "recorded": RECORDED["rows"]}
    comparison["negative_duration_rows"] = {
        "fresh": len(hazards["negative_duration"]),
        "recorded": RECORDED["negative_duration_rows"]}
    return comparison


def window_of(issue: date) -> str | None:
    for split, (start, end) in WINDOWS.items():
        if start <= issue < end:
            return split
    return None


def build_rows_v2(rows: list[dict], eligibility_cutoff: date):
    """Scored rows with as-of history features, plus full exclusion counts.

    History pools are keyed by site and by county separately: one event per
    (pool key, issue date), representative row chosen by the stated rule.
    """
    dated = [row for row in rows if row["issue"] is not None]
    dated.sort(key=lambda row: (row["issue"], row["advisory_id"]))

    def representative(group: list[dict]) -> dict:
        chosen = next((row for row in group
                       if row["removal"] is not None and row["duration"] >= 0),
                      None)
        if chosen is None:
            chosen = next((row for row in group if row["removal_blank"]),
                          group[0])
        return chosen

    by_site_date: dict[tuple, list[dict]] = defaultdict(list)
    by_county_date: dict[tuple, list[dict]] = defaultdict(list)
    same_date_groups = Counter()
    for row in dated:
        by_site_date[(row["site"], row["issue"])].append(row)
        if row["county"]:
            by_county_date[(row["county"], row["issue"])].append(row)
    for group in by_site_date.values():
        same_date_groups[len(group)] += 1

    site_events: dict[str, list[dict]] = defaultdict(list)
    county_events: dict[str, list[dict]] = defaultdict(list)
    exclusions = {split: Counter() for split in list(WINDOWS) + ["other"]}
    out_rows: dict[str, list[dict]] = {split: [] for split in WINDOWS}
    per_year_scored: dict[str, Counter] = {split: Counter()
                                           for split in WINDOWS}
    out_of_window: Counter = Counter()
    boundary = Counter()
    valid_valid_pairs = 0
    for group in by_site_date.values():
        valid = [row for row in group
                 if row["removal"] is not None and row["duration"] >= 0]
        if len(valid) > 1:
            valid_valid_pairs += 1

    def history(events: list[dict], instant: date) -> dict:
        n_events = len(events)
        days_since = (instant - events[-1]["issue"]).days if events else SENTINEL
        resolved = [event for event in events
                    if event["removal"] is not None
                    and event["removal"] < instant
                    and event["duration"] >= 0]
        active = any(event["removal"] is None or event["removal"] >= instant
                     for event in events)
        rate = (sum(1 for event in resolved
                    if event["duration"] <= THRESHOLD_DAYS) / len(resolved)
                if resolved else SENTINEL)
        return {"n": n_events, "days": days_since,
                "resolved": len(resolved), "rate": round(rate, 4),
                "active": int(active)}

    EMPTY = {"n": 0, "days": SENTINEL, "resolved": 0, "rate": SENTINEL,
             "active": 0}
    buckets: dict[date, list[dict]] = defaultdict(list)
    for row in dated:
        buckets[row["issue"]].append(row)
    for day in sorted(buckets):
        for row in buckets[day]:
            split = window_of(day)
            bucket = "other" if split is None else split
            if day > eligibility_cutoff:
                exclusions[bucket]["after_eligibility_cutoff"] += 1
                if split is None:
                    out_of_window[day.year] += 1
                continue
            if split is None:
                out_of_window[day.year] += 1
                exclusions["other"]["out_of_window"] += 1
                continue
            if row["removal_blank"]:
                exclusions[split]["censored_active_at_vintage"] += 1
                continue
            if row["removal"] is None:
                exclusions[split]["unparseable_removal"] += 1
                continue
            if row["duration"] < 0:
                exclusions[split]["negative_duration_invalid"] += 1
                continue
            site_hist = history(site_events.get(row["site"], []), day)
            county_hist = (history(county_events.get(row["county"], []), day)
                           if row["county"] else dict(EMPTY))
            out_rows[split].append({
                "advisory_id": row["advisory_id"],
                "issue_date": day.isoformat(),
                "site_name": row["site"],
                "county": row["county"] or "unknown",
                "facility_type": row["facility"],
                "reason": row["reason"],
                "issue_month": day.month,
                "issue_dow": day.weekday(),
                "site_prior_advisories": site_hist["n"],
                "site_days_since_last": site_hist["days"],
                "site_prior_resolved": site_hist["resolved"],
                "site_prior_lift30_rate": site_hist["rate"],
                "site_active_prior": site_hist["active"],
                "county_prior_advisories": county_hist["n"],
                "county_days_since_last": county_hist["days"],
                "county_prior_resolved": county_hist["resolved"],
                "county_prior_lift30_rate": county_hist["rate"],
                "county_active_prior": county_hist["active"],
                TARGET: int(row["duration"] <= THRESHOLD_DAYS),
            })
            per_year_scored[split][day.year] += 1
            if row["duration"] in (THRESHOLD_DAYS - 1, THRESHOLD_DAYS,
                                   THRESHOLD_DAYS + 1):
                boundary[row["duration"]] += 1
        # One event per (key, date) enters the pools after the date is
        # scored, so rows sharing an issue date never see each other.
        seen_keys: set[tuple] = set()
        for row in buckets[day]:
            if (row["site"], day) not in seen_keys:
                seen_keys.add((row["site"], day))
                site_events[row["site"]].append(representative(
                    by_site_date[(row["site"], day)]))
            if row["county"] and (row["county"], day) not in seen_keys:
                seen_keys.add((row["county"], day))
                county_events[row["county"]].append(representative(
                    by_county_date[(row["county"], day)]))
    diag = {"exclusions": exclusions, "out_of_window_per_year": out_of_window,
            "boundary_durations": dict(boundary),
            "same_date_row_groups": dict(same_date_groups),
            "valid_valid_same_date_pairs": valid_valid_pairs,
            "per_issue_year_scored": {split: dict(sorted(years.items()))
                                      for split, years in
                                      per_year_scored.items()}}
    return out_rows, diag


def write_splits(out: Path, out_rows: dict[str, list[dict]]) -> dict:
    stats = {}
    for split, relative in LAYOUT.items():
        destination = out / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        rows = out_rows[split]
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS,
                                    lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        positives = sum(row[TARGET] for row in rows)
        sites = {row["site_name"] for row in rows}
        positive_sites = {row["site_name"] for row in rows if row[TARGET]}
        positive_dates = {row["issue_date"] for row in rows if row[TARGET]}
        stats[split] = {
            "rows": len(rows),
            "positives": positives,
            "positive_rate": round(positives / len(rows), 6) if rows else 0.0,
            "distinct_sites": len(sites),
            "distinct_positive_sites": len(positive_sites),
            "distinct_positive_issue_dates": len(positive_dates),
        }
        log(f"{split}: {stats[split]['rows']} rows, {positives} positives, "
            f"{len(positive_sites)} positive sites, "
            f"{len(positive_dates)} positive issue dates")
    return stats


def assert_label_sources_absent(out: Path) -> None:
    for relative in LAYOUT.values():
        with (out / relative).open(newline="", encoding="utf-8") as handle:
            header = next(csv.reader(handle))
        forbidden = sorted(set(header) & set(LABEL_SOURCE_COLUMNS))
        if forbidden:
            raise SystemExit(f"{relative} ships label-source columns: "
                             f"{forbidden}")
        missing = [column for column in COLUMNS if column not in header]
        if missing:
            raise SystemExit(f"{relative} misses declared columns: {missing}")


PREDICTION_QUESTION = (
    "At the moment a boil water advisory is issued for a public registered "
    "or municipal drinking water supply in Nova Scotia - known then: site "
    "name, county, facility type, reason for the report, calendar season, "
    "and the prior advisory history of the same site/county computed only "
    "from earlier advisories - will the advisory be lifted within 30 days?")
PREDICTION_TIME = (
    "The advisory issue date (register column 'Date Advisory Issued', a "
    "calendar day in the America/Halifax nominal local calendar; the "
    "register stores dates without times). Every shipped feature is a value "
    "fixed at or before that day: the issuing row's own site name, county, "
    "facility type, reason for the report, and derived calendar features; "
    "site/county history features read only register rows with a strictly "
    "earlier issue date, and a prior advisory's lift30 outcome enters a "
    "history rate only when its removal date is also strictly earlier than "
    "the scored row's issue date. The label window is the 30 days that "
    "follow the issue date; no part of the target window precedes the "
    "instant. The register is a single current vintage (full refresh), so "
    "all feature values are construction-time vintage values of "
    "issuance-time attributes - the same documented posture as "
    "wb-loan-disbursement-completion; no historical point-in-time "
    "availability is claimed.")


def quality_document(out: Path, stats: dict, fetch_info: dict, diag: dict,
                     vintage: date | None, eligibility_cutoff: date,
                     fixtures: list, comparison: dict, built_at: str) -> None:
    positive_events = {split: {
        "positives": stats[split]["positives"],
        "distinct_events": stats[split]["distinct_positive_issue_dates"]}
        for split in LAYOUT}
    vintage_text = vintage.isoformat() if vintage else "unparsed (Last-Modified header absent)"
    rate_note = ", ".join(f"{split} {stats[split]['positive_rate']}"
                          for split in LAYOUT)
    quality = {
        "name": NAME,
        "task": {"question": PREDICTION_QUESTION,
                 "prediction_time": PREDICTION_TIME},
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "time_column": "issue_date",
        "event_key_column": "issue_date",
        "event_key_note": (
            "the gate's clustered event count is distinct positive issue "
            "dates (same-day positives are read as not independent - a "
            "conservative regional-incident clustering). The site-repeat "
            "clustering the candidate record measured (distinct sites and "
            "distinct positive sites per window) is recorded beside it in "
            "summary.json split_stats"),
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "feature_documentation": (
            "every shipped feature is fixed at issuance: site_name, county, "
            "facility_type and reason are the register's own fields for the "
            "issuing advisory (normalised: lowercase, collapsed whitespace, "
            "'E.Coli Present' merged into 'e. coli present', blanks become "
            "the explicit 'unknown' level); issue_month and issue_dow are "
            "calendar arithmetic on the instant; the ten history features "
            "read only register rows with a strictly earlier issue date - "
            "counts and recurrences per normalised site/county key with "
            "events de-duplicated per (key, issue date), and lift30 rates "
            "over prior advisories whose removal date is also strictly "
            "earlier than the scored row's issue date, so no history value "
            "reads an outcome that was unresolved at the instant. Not "
            "shipped, with reasons: 'Date Advisory Removed' and 'Length of "
            "Advisory in Days' (the label source and its publisher "
            "derivation); lift14 (a second label derived from the same "
            "removal date; its discovery-measured base rates are recorded "
            "in summary.json as an alternative that is not shipped)"),
        "carry_columns": CARRY_COLUMNS,
        "id_columns": ID_COLUMNS,
        "high_cardinality_columns": HIGH_CARDINALITY,
        "high_cardinality_note": (
            "site_name has ~1.1k levels over ~2.3k scored rows (the source "
            "grain: many sites advise once or twice; repeat sites are the "
            "point of the history features); issue_date is a free event "
            "date with mostly <5 rows per level. Both are declared rather "
            "than scored by the single-column AUC check. The runner's "
            "id_columns exclude advisory_id from default model input; "
            "site_name stays a model input by design - site identity and "
            "its repeat structure are genuine issuance-time signal, and no "
            "cross-split site join can recover another row's label because "
            "each row's label is its own advisory's removal, never repeated "
            "in any other row's shipped columns"),
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "post_hoc_columns": POST_HOC_COLUMNS,
        "measurements": [
            {"column": "advisory_id",
             "unit": "constructed row identifier ns<NNNNNN>",
             "frame": "the register row's 1-based position in the pinned "
                      "CSV (stable per vintage); one advisory record"},
            {"column": "issue_date", "unit": "ISO calendar date",
             "frame": "the prediction instant itself (carry column, split "
                      "time column and clustered-event key)"},
            {"column": "site_name", "unit": "register free text (normalised)",
             "frame": "the supply's name as recorded for the issuing "
                      "advisory; the history pool key for site features"},
            {"column": "county", "unit": "register Nova Scotia county name "
              "(normalised; 'unknown' when blank)",
             "frame": "the county recorded for the issuing advisory"},
            {"column": "facility_type",
             "unit": "register level: registered / municipal / unknown",
             "frame": "the facility classification recorded for the issuing "
                      "advisory (57 rows blank at discovery, shipped as "
                      "'unknown')"},
            {"column": "reason", "unit": "register category (normalised; "
              "'unknown' when blank)",
             "frame": "the reason for the report recorded at issuance "
                      "(measured variants include 'E. Coli Present' and "
                      "'E.Coli Present', merged)"},
            {"column": "issue_month", "unit": "calendar month 1-12",
             "frame": "the month of the instant"},
            {"column": "issue_dow", "unit": "day of week 0=Monday..6=Sunday",
             "frame": "the weekday of the instant"},
            {"column": "site_prior_advisories", "unit": "count of advisories",
             "frame": "distinct earlier issue dates at the same normalised "
                      "site, strictly before the instant"},
            {"column": "site_days_since_last", "unit": "days (integer)",
             "frame": "instant minus the most recent earlier same-site "
                      "issue date; -1 when the site has no earlier "
                      "advisory"},
            {"column": "site_prior_resolved", "unit": "count of advisories",
             "frame": "earlier same-site advisories whose removal date is "
                      "strictly before the instant and whose duration is "
                      "non-negative"},
            {"column": "site_prior_lift30_rate", "unit": "mean binary label "
              "in [0,1]",
             "frame": "lift30 rate over those resolved priors; -1 when "
                      "site_prior_resolved is 0"},
            {"column": "site_active_prior", "unit": "binary 0/1",
             "frame": "1 iff an earlier same-site advisory was still in "
                      "effect at the instant (blank removal at the vintage, "
                      "or removal on/after the instant)"},
            {"column": "county_prior_advisories", "unit": "count of advisories",
             "frame": "distinct earlier issue dates in the same county, "
                      "strictly before the instant; 0 for rows with blank "
                      "county (never pooled)"},
            {"column": "county_days_since_last", "unit": "days (integer)",
             "frame": "instant minus the most recent earlier same-county "
                      "issue date; -1 when none"},
            {"column": "county_prior_resolved", "unit": "count of advisories",
             "frame": "earlier same-county advisories resolved strictly "
                      "before the instant"},
            {"column": "county_prior_lift30_rate", "unit": "mean binary label "
              "in [0,1]",
             "frame": "lift30 rate over those resolved priors; -1 when "
                      "none"},
            {"column": "county_active_prior", "unit": "binary 0/1",
             "frame": "1 iff an earlier same-county advisory was still in "
                      "effect at the instant; 0 for blank-county rows"},
            {"column": TARGET, "unit": "binary 0/1",
             "frame": f"1 iff (removal date - issue date) <= "
                      f"{THRESHOLD_DAYS} days, inclusive, recomputed from "
                      "the two register date columns; measured only on rows "
                      "with an observed removal; blank removal = advisory "
                      "still in effect at the vintage (publisher-documented), "
                      "excluded from scored sets and counted per window; "
                      "negative-duration rows are excluded as unverified "
                      "outcomes"},
        ],
        "external_threshold": False,
        "known_event": {
            "name": "in-file register fixtures (Maple Meadows Campground Inc "
                    "2024-08-31; Canning 2025-10-02)",
            "expected_verdict": "exceeds",
            "detail": (
                "two named register rows asserted against the fetched bytes: "
                "Maple Meadows Campground Inc (Inverness County, Registered, "
                "Total Coliform Present) issued 2024-08-31, removed "
                "2025-07-04, 307 days -> lift30 = 0, scored in the holdout "
                "window; and a Municipal Total Coliform advisory issued "
                "2025-10-02, removed 2025-10-03, 1 day -> lift30 = 1 on the "
                "register (issue year 2025 is outside every scored window by "
                "the frozen design, so this fixture pins parsing and "
                "one-day-positive semantics rather than a scored row). The "
                "30-day window is internal to the task, so the fixture set "
                "pins date parsing, duration arithmetic and inclusivity "
                "rather than an external standard; rows at duration exactly "
                "30 (label 1) and 31 (label 0) are counted in summary.json"),
            "source": "the fetched register CSV itself (values cross-checked "
                      "at discovery against the publisher's dataset page)",
        },
        "timing": {
            "prediction_instant": {
                "kind": "event_time",
                "period": "day",
                "days_after_period_end": 0,
                "citation": (
                    "register column 'Date Advisory Issued' is the advisory's "
                    "issue date - the event time documented on the publisher's "
                    "dataset page (data.novascotia.ca/datasets/7t68-9xmm, "
                    "'Date Boil Advisory Issued ... from 2006 - current'); "
                    "the prediction question is resolved at issuance, and the "
                    "register is an administrative record written at/after "
                    "the event"),
            },
            "features": {
                "period": "day",
                "published_days_after_period_end": 0,
                "source_kind": "administrative_record",
            },
            "row_selection": {
                "latest_period_used": "2024-12-31 (scored windows end "
                                      "2024-12-31 by issue date)",
                "fields": ["Date Advisory Issued (issue date, window "
                           "membership, eligibility cutoff)"],
                "basis": (
                    "membership reads only the issue date: a row is scored "
                    "iff its issue date falls inside one of the three "
                    "windows (2008-2017 / 2018-2020 / 2021-2024, by issue "
                    "year) and on or before the eligibility cutoff (register "
                    "vintage minus 30 days, so every scored row's 30-day "
                    "target window closes before the vintage). Censoring "
                    "excludes rows whose removal date is blank - the "
                    "publisher documents blank as 'advisories currently in "
                    "effect' - which is outcome-OBSERVABILITY conditioning, "
                    "never a label-value condition, bounded and counted per "
                    "window in summary.json. Negative-duration rows (removal "
                    "before issue, the register contradicting itself) are "
                    "excluded as unverified outcomes and counted. The label "
                    "is computed only after membership is fixed"),
            },
            "observations": [],
        },
        "split_windows": {
            "train": {"start": "2008-01-01", "end": "2018-01-01"},
            "eval": {"start": "2018-01-01", "end": "2021-01-01"},
            "holdout": {"start": "2021-01-01", "end": "2025-01-01"},
        },
        "split_boundaries": {
            "train": "advisory issue years 2008-2017 (window end exclusive)",
            "eval": "advisory issue years 2018-2020 (window end exclusive)",
            "holdout": "advisory issue years 2021-2024 (window end exclusive; "
                       "issue years 2025-2026 exist in the register with "
                       "mostly observed outcomes and are held as an "
                       "unscored reserve outside the frozen design)",
        },
        "positive_events": positive_events,
        "positive_events_note": (
            "positives and distinct positive issue dates per split, "
            "recomputed from the written rows; the gate re-verifies. "
            "Distinct positive sites per split are recorded in summary.json "
            "split_stats as the site-repeat clustering the candidate record "
            f"measured. Positive rates: {rate_note}"),
        "expected_duplicate_ids": 0,
        "id_columns_are_entity_keys": True,
        "id_columns_note": (
            "advisory_id names one register advisory record with one "
            "observed outcome; it is constructed from the pinned CSV row "
            "position and is unique across the artifact, so no identifier "
            "spans two splits. site_name repeats within and across splits by "
            "the source's grain (repeat advisories at one supply) and stays "
            "a declared high-cardinality feature, not an entity key"),
        "splits": LAYOUT,
        "evaluation_contract": {
            "use": "retrospective_research",
            "access": "isolated_rows",
            "training_label_timing": "unverified",
            "scope_note": (
                "each row is one issued advisory whose features are "
                "issuance-time register attributes plus strictly-earlier "
                "site/county history; the intended protocol predicts "
                "row-wise from the shipped columns (the shipped benchmark "
                "validator passes the whole table to the predictor, so "
                "isolated_rows is the design intent of this artifact's "
                "row-per-advisory contract, not a runtime-enforced "
                "protocol). Labeled eval is development/validation; the "
                "holdout is the final test and stays outside evaluated "
                "agents' workspaces. Training-label timing is UNVERIFIED: "
                "the register publishes no historical vintages, so no "
                "full-row availability ledger can be constructed and no "
                "historical as-of availability is claimed - retrospective "
                "research only, never a certified historical forecasting "
                "setup"),
            "feature_evidence": {
                "advisory_id": {
                    "source": "constructed: 1-based row position in the "
                              "pinned register CSV",
                    "availability": "assigned by construction at build time",
                    "status": "verified"},
                "issue_date": {
                    "source": "register column 'Date Advisory Issued'",
                    "availability": "the prediction instant itself",
                    "status": "verified"},
                "site_name": {
                    "source": "register column 'Site Name' (normalised)",
                    "availability": "the supply named on the issuing "
                                    "advisory record",
                    "status": "assumed",
                    "assumption": "current-vintage register value of an "
                                  "issuance-time attribute; no as-of "
                                  "reconstruction performed"},
                "county": {
                    "source": "register column 'County' (normalised; "
                              "'unknown' when blank)",
                    "availability": "the county recorded on the issuing "
                                    "advisory",
                    "status": "assumed",
                    "assumption": "current-vintage register value of an "
                                  "issuance-time attribute"},
                "facility_type": {
                    "source": "register column 'Facility Type' (normalised)",
                    "availability": "the facility classification recorded "
                                    "at issuance",
                    "status": "assumed",
                    "assumption": "current-vintage register value of an "
                                  "issuance-time attribute"},
                "reason": {
                    "source": "register column 'Reason for the Report' "
                              "(normalised, variants merged)",
                    "availability": "the reason recorded at issuance",
                    "status": "assumed",
                    "assumption": "current-vintage register value of an "
                                  "issuance-time attribute"},
                "issue_month": {
                    "source": "calendar arithmetic on issue_date",
                    "availability": "determined by the instant",
                    "status": "verified"},
                "issue_dow": {
                    "source": "calendar arithmetic on issue_date "
                              "(0=Monday)",
                    "availability": "determined by the instant",
                    "status": "verified"},
                "site_prior_advisories": {
                    "source": "count of register rows at the same normalised "
                              "site with strictly earlier issue dates, "
                              "de-duplicated per issue date",
                    "availability": "advisory issue events dated before "
                                    "the instant",
                    "status": "assumed",
                    "assumption": "computed from current-vintage register "
                                  "rows; the event ordering is enforced "
                                  "as-of, the values are single-vintage"},
                "site_days_since_last": {
                    "source": "instant minus the most recent earlier "
                              "same-site issue date",
                    "availability": "date arithmetic on earlier events",
                    "status": "assumed",
                    "assumption": "single-vintage register values"},
                "site_prior_resolved": {
                    "source": "count of earlier same-site advisories with "
                              "removal strictly before the instant and "
                              "non-negative duration",
                    "availability": "removal events dated before the "
                                    "instant",
                    "status": "assumed",
                    "assumption": "single-vintage register values; the "
                                  "strict as-of rule keeps unresolved "
                                  "priors out"},
                "site_prior_lift30_rate": {
                    "source": "mean lift30 over those resolved priors; -1 "
                              "when none",
                    "availability": "prior outcomes fully observed before "
                                    "the instant",
                    "status": "assumed",
                    "assumption": "single-vintage register values"},
                "site_active_prior": {
                    "source": "1 iff an earlier same-site advisory is "
                              "unresolved at the instant (blank removal or "
                              "removal on/after the instant)",
                    "availability": "state of earlier advisories at the "
                                    "instant",
                    "status": "assumed",
                    "assumption": "blank removal at the vintage implies in "
                                  "effect at every earlier instant; "
                                  "single-vintage register values"},
                "county_prior_advisories": {
                    "source": "count of register rows in the same county "
                              "with strictly earlier issue dates, "
                              "de-duplicated per issue date; blank-county "
                              "rows never pool (sentinel 0)",
                    "availability": "advisory issue events dated before "
                                    "the instant",
                    "status": "assumed",
                    "assumption": "single-vintage register values"},
                "county_days_since_last": {
                    "source": "instant minus the most recent earlier "
                              "same-county issue date",
                    "availability": "date arithmetic on earlier events",
                    "status": "assumed",
                    "assumption": "single-vintage register values"},
                "county_prior_resolved": {
                    "source": "count of earlier same-county advisories "
                              "resolved strictly before the instant",
                    "availability": "removal events dated before the "
                                    "instant",
                    "status": "assumed",
                    "assumption": "single-vintage register values"},
                "county_prior_lift30_rate": {
                    "source": "mean lift30 over those resolved priors; -1 "
                              "when none",
                    "availability": "prior outcomes fully observed before "
                                    "the instant",
                    "status": "assumed",
                    "assumption": "single-vintage register values"},
                "county_active_prior": {
                    "source": "1 iff an earlier same-county advisory is "
                              "unresolved at the instant",
                    "availability": "state of earlier advisories at the "
                                    "instant",
                    "status": "assumed",
                    "assumption": "single-vintage register values"},
            },
            "vintage": {
                "kind": "current_snapshot",
                "evidence": (
                    "the register is one in-place full-refresh vintage "
                    f"(register sha256 {fetch_info['sha256'][:16]}..., "
                    f"Last-Modified {fetch_info.get('last_modified_header')}"
                    f", vintage date {vintage_text}); the publisher's "
                    "changelog at discovery recorded a full refresh on "
                    "2026-06-16 ('Inserted 2649 rows, Deleted 0') and the "
                    "dataset page documents quarterly updates with no "
                    "historical vintages. Every shipped feature is a "
                    "construction-time vintage value of an issuance-time "
                    "attribute; history features enforce event ordering "
                    "as-of but read single-vintage values. No historical "
                    "point-in-time availability is claimed"),
            },
            "selection": {
                "kind": "prediction_time",
                "evidence": (
                    "membership is fixed by the issue date alone (window "
                    "membership and the eligibility cutoff = vintage minus "
                    "30 days); blank-removal censoring excludes rows whose "
                    "outcome is unobserved at the vintage and never reads "
                    "the label value; negative-duration rows are excluded "
                    "as unverified outcomes (the register contradicting "
                    "itself) - both bounded, counted per window in "
                    "summary.json and decided before any scoring; rows with "
                    "unparseable issue dates cannot be placed on the "
                    "timeline and are excluded and counted"),
            },
            "limitations": [
                "single current vintage; no historical as-of reconstruction "
                "of any feature value; retrospective research only",
                "the register's own 'Length of Advisory in Days' disagrees "
                "with the recomputed duration on a counted subset of rows "
                "(measured in summary.json); the label always uses the two "
                "date columns",
                "site identity is free text; the normalised exact-match "
                "rule can both split one physical supply across name "
                "variants and merge same-named supplies",
                "advisory duration has a measured regime shift straddling "
                "the holdout window (mean duration 218 days in 2020 vs "
                "47-65 days in 2009-2018); per-year reporting is mandatory",
                "issue years 2025-2026 exist in the register with mostly "
                "observed outcomes but sit outside the frozen scored "
                "windows; they are counted as an unscored reserve",
                "eval window n=372 scored rows is the smallest split; "
                "uncertainty intervals are correspondingly wide",
            ],
            "cross_row_audit": {
                "probes": [
                    {"entity_columns": ["site_name"],
                     "time_column": "issue_date",
                     "lag_days_column": "site_days_since_last",
                     "left": "site_prior_lift30_rate",
                     "operation": "copy"},
                    {"entity_columns": ["county"],
                     "time_column": "issue_date",
                     "lag_days_column": "county_days_since_last",
                     "left": "county_prior_lift30_rate",
                     "operation": "copy"},
                ],
                "rationale": (
                    "the plausible cross-row exposure is reverse-history: a "
                    "later advisory at the same site/county carries the "
                    "prior advisory's lift30 outcome inside its history "
                    "rate, exact when that prior is its only resolved "
                    "prior. The two probes measure that exposure on the "
                    "full artifact (donor = a later row whose "
                    "days_since_last points exactly back to the earlier "
                    "row's issue date, voting its prior lift30 rate); "
                    "covered rows require the isolated_rows access this "
                    "descriptor declares. The forward direction is closed "
                    "by construction: no shipped column reads any row "
                    "issued on or after the scored row's issue date"),
                "auxiliary_files_review": (
                    "the artifact ships public/train.csv, public/eval.csv, "
                    "private/holdout.csv, meta.json, quality.json and "
                    "summary.json. summary.json carries construction "
                    "diagnostics including per-split aggregate rates and "
                    "exclusion counts; it carries no per-row labels. No "
                    "joint label matrix or other solver-visible file "
                    "exists in the artifact"),
            },
        },
    }
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--source", default=URL,
                        help="register source: the URL (default) or a local "
                             "CSV path for synthetic smoke runs")
    parser.add_argument("--built-at", default="1970-01-01T00:00:00Z",
                        help="pinned construction instant for "
                             "byte-reproducible rebuilds")
    parser.add_argument("--skip-vintage-checks", action="store_true",
                        help="smoke input only: skip the register-identity "
                             "comparison (the named fixtures still run)")
    args = parser.parse_args(argv)
    out = Path(args.out)
    work = Path(args.work_dir)
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)

    log("== fetch (anonymous Socrata full-CSV export, pinned by sha256) ==")
    data, fetch_info = fetch(args.source, work)
    log(f"sha256={fetch_info['sha256']} bytes={fetch_info['bytes']} "
        f"last_modified={fetch_info.get('last_modified_header')}")

    log("== parse register ==")
    rows, hazards = parse_register(data)
    log(f"register rows: {len(rows)}; hazards: "
        f"negative_duration={len(hazards['negative_duration'])} "
        f"zero_duration={hazards['zero_duration']} "
        f"unparseable_issue={sum(hazards['unparseable_issue_values'].values())} "
        f"unparseable_removal={sum(hazards['unparseable_removal_values'].values())}")

    log("== fixtures (asserted on the fetched bytes) ==")
    fixtures = check_fixtures(rows)
    log(f"fixtures: {len(fixtures)} asserted OK")

    comparison = {"skipped": True} if args.skip_vintage_checks else \
        check_recorded(rows, fetch_info, hazards)
    if not args.skip_vintage_checks:
        log(f"recorded-count comparison: sha_same="
            f"{comparison['sha256_same_as_discovery']}")

    vintage = (date.fromisoformat(fetch_info["vintage_date"])
               if fetch_info.get("vintage_date") else None)
    if vintage is None and args.skip_vintage_checks:
        # synthetic smoke input only: a file source has no Last-Modified
        # header; pin the discovery vintage so the cutoff logic runs
        vintage = date(2026, 6, 16)
        log("smoke: pinned synthetic vintage 2026-06-16")
    if vintage is None:
        raise SystemExit("register Last-Modified header missing/unparseable; "
                         "the vintage date is required for the eligibility "
                         "cutoff")
    eligibility_cutoff = vintage - timedelta(days=30)
    log(f"vintage={vintage.isoformat()} "
        f"eligibility_cutoff={eligibility_cutoff.isoformat()}")

    log("== build scored rows with as-of history features ==")
    out_rows, diag = build_rows_v2(rows, eligibility_cutoff)
    for split in ("train", "eval", "holdout"):
        excluded = sum(diag["exclusions"][split].values())
        log(f"{split}: {len(out_rows[split])} scored rows, "
            f"{excluded} excluded ({dict(diag['exclusions'][split])})")

    log("== write ==")
    stats = write_splits(out, out_rows)
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
        "positive_rate": {split: stats[split]["positive_rate"]
                          for split in LAYOUT},
        "split": ("temporal on advisory issue year: train 2008-2017, "
                  "eval 2018-2020, holdout 2021-2024"),
        "split_description": (
            "temporal on advisory issue year: train 2008-2017, eval "
            "2018-2020, holdout 2021-2024; population is advisories with a "
            "parseable issue date inside a window, issue date on or before "
            "the register vintage minus 30 days, and an observed "
            "non-negative duration at the pinned vintage; blank removal "
            "(still in effect) and negative-duration rows are excluded and "
            "counted per window"),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    quality_document(out, stats, fetch_info, diag, vintage,
                     eligibility_cutoff, fixtures, comparison, args.built_at)

    reason_levels = Counter(row["reason"] for row in rows)
    summary = {
        "name": NAME,
        "stage": "construction (no performance metric computed anywhere here)",
        "built_at_utc": args.built_at,
        "fetch": fetch_info,
        "vintage": {
            "vintage_date": vintage.isoformat(),
            "eligibility_cutoff": eligibility_cutoff.isoformat(),
            "cutoff_rule": "register vintage minus 30 days, so every scored "
                           "row's 30-day target window closes before the "
                           "vintage",
        },
        "register_comparison_with_discovery": comparison,
        "register_totals": {
            "rows": len(rows),
            "parseable_issue_dates": sum(1 for row in rows if row["issue"]),
            "resolved_removal_present": sum(
                1 for row in rows if row["removal"] is not None),
            "blank_removal_active_at_vintage": sum(
                1 for row in rows if row["removal_blank"]),
            "distinct_sites": len({row["site"] for row in rows}),
            "reason_levels": dict(sorted(reason_levels.items(),
                                          key=lambda kv: -kv[1])),
        },
        "hazards": {
            "negative_duration_rows": hazards["negative_duration"],
            "zero_duration_rows": hazards["zero_duration"],
            "unparseable_issue_date_values": dict(
                hazards["unparseable_issue_values"]),
            "unparseable_removal_date_values": dict(
                hazards["unparseable_removal_values"]),
            "missing_county": hazards["missing_county"],
            "missing_facility_type": hazards["missing_facility_type"],
            "missing_reason": hazards["missing_reason"],
            "length_column_disagreements":
                hazards["length_column_disagreements"],
            "same_site_issue_date_row_groups":
                diag["same_date_row_groups"],
            "valid_valid_same_date_pairs":
                diag["valid_valid_same_date_pairs"],
        },
        "boundary_durations": diag["boundary_durations"],
        "boundary_note": (
            "rows at duration exactly 30 carry label 1 (inclusive window) "
            "and exactly 31 carry label 0; counts recorded from the scored "
            "rows plus the flanking days"),
        "exclusions": {split: dict(counts) for split, counts
                       in diag["exclusions"].items()},
        "out_of_window_per_year": dict(sorted(
            diag["out_of_window_per_year"].items())),
        "out_of_window_note": (
            "issue years outside the frozen scored windows (2006-2007 if "
            "any, 2025-2026), counted per year and never scored; the "
            "eligibility cutoff excludes post-cutoff rows the same way"),
        "split_stats": stats,
        "per_issue_year_scored": diag["per_issue_year_scored"],
        "fixtures": fixtures,
        "label_threshold": {
            "primary": "lift30: removal date - issue date <= 30 days, "
                       "inclusive (shipped)",
            "alternative_measured_not_shipped": (
                "lift14 (within 14 days); discovery-measured base rates "
                "train 0.4509 / eval 0.3952 / holdout 0.3995 - recorded "
                "from probe_ns_aggregates_out.json, not recomputed here"),
        },
        "shipped_rows": total_rows,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    log(f"== done: {total_rows} scored rows written to {out} ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
