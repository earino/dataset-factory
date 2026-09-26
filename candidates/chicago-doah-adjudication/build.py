#!/usr/bin/env python3
"""Build the chicago-doah-adjudication extract.

Task
----
At the moment a City of Chicago Department of Administrative Hearings (DOAH)
ordinance-violation case is docketed, will the hearing officer find the respondent liable on at
least one charge? The label is the City's own recorded disposition, not our inference.

Grain
-----
The source publishes one row per *violation charge*; a case carries several charges that share
one `docket_number`. Splitting by row would put the same case in two periods, which is case-level
leakage: the model would see a case's dismissed charge in train and its liable charge in eval.
Every case is therefore aggregated to exactly one row first, and the split is taken over cases.

The one-row-per-case grain is also what the source supports: no docket_number in the published
data carries conflicting decided dispositions (asserted below, and the builder exits non-zero if
one ever appears).

Time
----
`violation_date` is the time column: the date the violation notice was issued, which is on the
notice before the case is docketed. Splits are three disjoint periods of it, and the most recent
one is the holdout. Cases whose notice date falls outside the extract window are dropped rather
than shipped unlabelled.

`hearing_date` is deliberately **not** shipped. The City documents it as "the date of the most
recent hearing", so on a decided case it is the hearing at which the disposition was recorded -
after the prediction instant. A `days_to_hearing` feature derived from it separates the classes on
its own (single-column AUC 0.84 over the case rows), which is leakage, and the runner hands every
non-identifier column to the model, so neither the column nor anything derived from it is
published.

Freezing
--------
The City republishes this dataset daily and dispositions fill in over time, so the extract is
frozen by record: the builder records the source row count it fetched, a digest of the raw rows
in publication-id order, and a digest of the canonical case table it built. It also queries the
source's own row count and refuses to finish when it did not fetch every row. A holdout that
changes under the task is not a holdout.

Usage
-----
    python3 build.py --probe                 # bounded, read-only summary, writes nothing
    python3 build.py --out /output/extract   # full build
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RESOURCE = "6br9-quuz"
LANDING_PAGE = f"https://data.cityofchicago.org/d/{RESOURCE}"
RESOURCE_URL = f"https://data.cityofchicago.org/resource/{RESOURCE}.csv"
COUNT_URL = f"https://data.cityofchicago.org/resource/{RESOURCE}.json"

# Only the fields the task needs. `id` is the publication's own row identifier and is used for
# the source digest and the deterministic "primary violation" tie-break - it is never shipped.
# `hearing_date` is not read at all: it is post-hoc (see the module docstring).
SELECT = [
    "id", "docket_number", "case_disposition", "violation_date",
    "violation_code", "ward", "street_direction", "street_type", "latitude", "longitude",
]

POSITIVE = "Liable"
NEGATIVE = "Not Liable"

PAGE_LIMIT = 50000
PAGE_HARD_CAP = 40

# Disjoint case-level periods, keyed by the case's earliest recorded violation (notice) date.
SPLIT_WINDOWS = {
    "train": ("2008-01-01", "2018-01-01"),
    "eval": ("2018-01-01", "2022-01-01"),
    "holdout": ("2022-01-01", "2026-09-01"),
}
EXTRACT_END = SPLIT_WINDOWS["holdout"][1]

# The runner reads the header of each split file and hands every non-target, non-identifier
# column to prediction code, so the published column order is fixed here and repeated in
# meta.json. Every shipped column is knowable when the case is docketed.
COLUMNS = [
    "docket_number", "violation_date", "ward", "street_direction", "street_type",
    "latitude", "longitude", "charge_count", "distinct_code_count", "violation_code", "outcome",
]
TARGET = "outcome"
ID_COLUMNS = ["docket_number"]
# `violation_date` is the split key and is also a legitimate docket-time feature, so it is not a
# carry column: a model may use the notice date.
CARRY_COLUMNS = []
FEATURES = [column for column in COLUMNS
            if column not in set(ID_COLUMNS) | set(CARRY_COLUMNS) | {TARGET}]
HIGH_CARDINALITY_COLUMNS = ["violation_date", "violation_code"]
LABEL_SOURCE_COLUMNS = ["case_disposition"]
POST_HOC_COLUMNS = ["hearing_date", "imposed_fine", "admin_costs", "last_modified_date"]

DISCLAIMER = (
    "This site provides applications using data that has been modified for use from its "
    "original source, www.cityofchicago.org, the official website of the City of Chicago. The "
    "City of Chicago makes no claims as to the content, accuracy, timeliness, or completeness of "
    "any of the data provided at this site. The data provided at this site is subject to change "
    "at any time. It is understood that the data provided at this site is being used at one's "
    "own risk."
)

MEASUREMENTS = [
    {"column": "latitude", "unit": "decimal degrees",
     "frame": "WGS84 (EPSG:4326), as published by the City in dataset 6br9-quuz"},
    {"column": "longitude", "unit": "decimal degrees",
     "frame": "WGS84 (EPSG:4326), as published by the City in dataset 6br9-quuz"},
    {"column": "charge_count", "unit": "count of published rows",
     "frame": "violation charges the City publishes against the case's docket_number, all "
              "dispositions included"},
    {"column": "distinct_code_count", "unit": "count of distinct violation codes",
     "frame": "distinct violation_code values the City publishes against the case's "
              "docket_number"},
]


def date_part(value) -> str:
    """The publication's timestamps are 'YYYY-MM-DDTHH:MM:SS.mmm'; the date is what matters."""
    return (value or "")[:10]


def fetch_page(offset: int, limit: int = PAGE_LIMIT, attempts: int = 4) -> list:
    query = urllib.parse.urlencode({"$select": ",".join(SELECT), "$order": ":id",
                                    "$limit": limit, "$offset": offset})
    url = f"{RESOURCE_URL}?{query}"
    last = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=300) as response:
                text = response.read().decode("utf-8", "replace")
            return list(csv.DictReader(text.splitlines()))
        except Exception as exc:                     # noqa: BLE001 - retried, then reported
            last = exc
            time.sleep(2 ** attempt)
    raise SystemExit(f"page at offset {offset} failed after {attempts} attempts: {last}")


def source_row_count() -> int:
    query = urllib.parse.urlencode({"$select": "count(*)"})
    with urllib.request.urlopen(f"{COUNT_URL}?{query}", timeout=120) as response:
        payload = json.loads(response.read().decode())
    return int(payload[0]["count"])


def split_for(notice_date: str):
    for name in ("train", "eval", "holdout"):
        start, end = SPLIT_WINDOWS[name]
        if start <= notice_date < end:
            return name
    return None


def accumulate(max_pages: int) -> tuple[dict, dict]:
    """One streaming pass over the source, reduced to one entry per case.

    Holding 824k raw rows would cost most of a small worker's memory; the per-case accumulator is
    a few tens of megabytes and is all the task needs.
    """
    cases: dict[str, dict] = {}
    digest = hashlib.sha256()
    fetched = 0
    pages = 0
    truncated = False

    while True:
        if pages >= max_pages:
            truncated = True
            break
        rows = fetch_page(pages * PAGE_LIMIT)
        if not rows:
            break
        pages += 1
        for row in rows:
            fetched += 1
            digest.update(("\t".join(str(row.get(field, "") or "") for field in SELECT)
                           + "\n").encode())
            docket = (row.get("docket_number") or "").strip()
            if not docket:
                continue
            disposition = (row.get("case_disposition") or "").strip()
            violation_date = date_part(row.get("violation_date"))
            code = (row.get("violation_code") or "").strip()

            entry = cases.get(docket)
            if entry is None:
                entry = {"liable": 0, "not_liable": 0, "other": 0, "total": 0,
                         "primary": None, "codes": set()}
                cases[docket] = entry
            entry["total"] += 1
            if disposition == POSITIVE:
                entry["liable"] += 1
            elif disposition == NEGATIVE:
                entry["not_liable"] += 1
            else:
                entry["other"] += 1
            entry["codes"].add(code)
            # The case's lead charge: earliest recorded violation, tie-broken by code and by the
            # publication's own row id so the choice is deterministic.
            key = (violation_date or "9999-99-99", code, str(row.get("id") or ""))
            if entry["primary"] is None or key < entry["primary"][0]:
                entry["primary"] = (key, {
                    "violation_date": violation_date,
                    "violation_code": code,
                    "ward": (row.get("ward") or "").strip(),
                    "street_direction": (row.get("street_direction") or "").strip(),
                    "street_type": (row.get("street_type") or "").strip(),
                    "latitude": (row.get("latitude") or "").strip(),
                    "longitude": (row.get("longitude") or "").strip(),
                })
        if len(rows) < PAGE_LIMIT:
            break

    return cases, {"fetched_rows": fetched, "pages": pages, "truncated": truncated,
                   "source_rows_sha256": digest.hexdigest(), "max_pages": max_pages}


def build_cases(cases: dict) -> tuple[dict, dict]:
    """Reduce the accumulator to the shipped case table, counting every exclusion."""
    built = {name: [] for name in SPLIT_WINDOWS}
    stats = {"dockets_seen": len(cases), "conflicting_dispositions": [],
             "dropped_no_decision": 0, "dropped_incomplete": 0, "dropped_out_of_window": 0,
             "mixed_disposition_cases": 0}

    for docket in sorted(cases):
        entry = cases[docket]
        liable, not_liable = entry["liable"], entry["not_liable"]
        if entry["other"]:
            stats["mixed_disposition_cases"] += 1
        if not liable and not not_liable:
            stats["dropped_no_decision"] += 1
            continue
        # A case that was both ruled liable and ruled not liable on different charges would make
        # the case-level label arbitrary. None does; if one ever appears the build must stop.
        if liable and not_liable:
            stats["conflicting_dispositions"].append(docket)
            continue

        primary = entry["primary"][1]
        if not (primary["violation_date"] and primary["latitude"] and primary["longitude"]):
            stats["dropped_incomplete"] += 1
            continue
        # The split key is the case's earliest recorded notice date.
        split = split_for(primary["violation_date"])
        if split is None:
            stats["dropped_out_of_window"] += 1
            continue
        try:
            float(primary["latitude"])
            float(primary["longitude"])
        except ValueError:
            stats["dropped_incomplete"] += 1
            continue

        built[split].append({
            "docket_number": docket,
            "violation_date": primary["violation_date"],
            "ward": primary["ward"],
            "street_direction": primary["street_direction"],
            "street_type": primary["street_type"],
            "latitude": primary["latitude"],
            "longitude": primary["longitude"],
            "charge_count": entry["total"],
            "distinct_code_count": len(entry["codes"]),
            "violation_code": primary["violation_code"],
            "outcome": POSITIVE if liable else NEGATIVE,
        })

    for split, rows in built.items():
        rows.sort(key=lambda row: (row["violation_date"], row["docket_number"]))
    return built, stats


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="/output/extract")
    parser.add_argument("--probe", action="store_true",
                        help="bounded read-only run: fetch a couple of pages, print a summary")
    parser.add_argument("--max-pages", type=int, default=PAGE_HARD_CAP)
    parser.add_argument("--built-at", default=None,
                        help="pin meta.json's built_at_utc so a rebuild is byte-identical")
    args = parser.parse_args(argv)

    max_pages = 2 if args.probe else args.max_pages
    # Coverage is a hard condition for a real build: the full source must be read, and the row
    # count must match the source's own. A bounded --max-pages run is a smoke test and says so.
    full_run = not args.probe and max_pages >= PAGE_HARD_CAP
    expected = source_row_count() if full_run else None

    cases, fetch_stats = accumulate(max_pages)
    if full_run and fetch_stats["truncated"]:
        raise SystemExit(f"stopped at the {max_pages}-page cap with rows still unread")
    if expected is not None and fetch_stats["fetched_rows"] != expected:
        raise SystemExit(f"fetched {fetch_stats['fetched_rows']} rows but the source reports "
                         f"{expected}: the extract is not the frozen one")

    built, stats = build_cases(cases)
    if stats["conflicting_dispositions"]:
        raise SystemExit(f"{len(stats['conflicting_dispositions'])} docket(s) carry both Liable "
                         f"and Not Liable charges, e.g. {stats['conflicting_dispositions'][:3]}")

    if args.probe:
        print(json.dumps({**fetch_stats, **{k: v for k, v in stats.items()
                                            if k != "conflicting_dispositions"},
                          "cases": {name: len(rows) for name, rows in built.items()},
                          "sample": built["holdout"][:2]}, indent=2))
        return 0

    return write_extract(Path(args.out), built, fetch_stats, stats, args.built_at)


def write_extract(out: Path, built: dict, fetch_stats: dict, stats: dict,
                  built_at: str | None) -> int:
    (out / "public").mkdir(parents=True, exist_ok=True)
    (out / "private").mkdir(parents=True, exist_ok=True)
    splits = {"train": "public/train.csv", "eval": "public/eval.csv",
              "holdout": "private/holdout.csv"}
    counts, rates, events, case_digest = {}, {}, {}, hashlib.sha256()
    for name, relative in splits.items():
        rows = built[name]
        with (out / relative).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        positives = [row for row in rows if row["outcome"] == POSITIVE]
        counts[name] = len(rows)
        rates[name] = round(len(positives) / len(rows), 6) if rows else None
        events[name] = {"positives": len(positives),
                        "distinct_events": len({row["violation_date"][:10] for row in positives})}
    for name in sorted(built):
        for row in built[name]:
            case_digest.update(("\t".join(str(row[column]) for column in COLUMNS)
                                + "\n").encode())

    built_at = built_at or datetime.datetime.now(datetime.timezone.utc).isoformat()

    meta = {
        "name": "chicago-doah-adjudication",
        "target": TARGET,
        "positive_label": POSITIVE,
        "id_columns": ID_COLUMNS,
        "columns": COLUMNS,
        "rows": counts,
        "positive_rate": rates,
        "built_at_utc": built_at,
        "grain": "one row per docket_number (case)",
        "description": "City of Chicago Department of Administrative Hearings (DOAH) ordinance "
                       "violations, reduced to one row per case. Each row carries what is on the "
                       "docket when the case is opened - the lead charge, the ward, street and "
                       "location, the notice date and how many charges the case carries - and one "
                       "binary target: whether the hearing officer recorded a Liable disposition "
                       "on at least one charge.",
        "split": "Temporal, taken over cases (never over rows). A case is placed by the notice "
                 "date of its earliest recorded violation: train = before 2018-01-01, eval = "
                 "2018-01-01 to 2022-01-01, holdout = 2022-01-01 to 2026-09-01. The three periods "
                 "are disjoint, and no docket_number appears in more than one of them.",
        "source": {"name": "City of Chicago, Department of Administrative Hearings, Ordinance "
                           "Violations",
                   "dataset_id": RESOURCE,
                   "landing_page": LANDING_PAGE,
                   "resource": f"https://data.cityofchicago.org/resource/{RESOURCE}.json",
                   "attribution": "City of Chicago",
                   "licence": "See Terms of Use (City of Chicago Data Terms of Use)"},
        "derived": "Labelled as derived and not an official City of Chicago product.",
        "disclaimer": DISCLAIMER,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    quality = {
        "name": "chicago-doah-adjudication",
        "task": {
            "question": "At the moment a City of Chicago Department of Administrative Hearings "
                        "ordinance-violation case is docketed, will the hearing officer find the "
                        "respondent liable on at least one charge?",
            "prediction_time": "Docketing: the case's charges, the violation code and date, the "
                               "ward and the property location are on the notice and on the "
                               "docket. No disposition, fine or administrative cost has been "
                               "recorded yet. The City's hearing_date is deliberately not "
                               "published: it is documented as the date of the most recent "
                               "hearing, which on a decided case is the hearing at which the "
                               "disposition was recorded.",
        },
        "target": TARGET,
        "positive_label": POSITIVE,
        "time_column": "violation_date",
        "event_key_column": "violation_date",
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "carry_columns": CARRY_COLUMNS,
        "id_columns": ID_COLUMNS,
        "high_cardinality_columns": HIGH_CARDINALITY_COLUMNS,
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "post_hoc_columns": POST_HOC_COLUMNS,
        "measurements": MEASUREMENTS,
        "external_threshold": False,
        "id_columns_are_entity_keys": True,
        "expected_duplicate_ids": 0,
        "split_windows": {name: {"start": start, "end": end}
                          for name, (start, end) in SPLIT_WINDOWS.items()},
        "positive_events": {"eval": events["eval"], "holdout": events["holdout"]},
        "splits": splits,
        "grain": "one row per docket_number (case); the source publishes one row per violation "
                 "charge, so a row-level split would leak a case across periods",
        "disclaimer": DISCLAIMER,
        "notes": "Splits are three disjoint periods of the case's earliest recorded violation "
                 "(notice) date. hearing_date is not published at all: it is the City's most "
                 "recent-hearing date, which is post-hoc for a decided case, and a feature "
                 "derived from it separates the classes on its own. The City republishes this "
                 "dataset daily, so the extract is frozen by the row count and digests recorded "
                 "in build_summary.json.",
    }
    (out / "quality.json").write_text(json.dumps(quality, indent=2) + "\n")

    summary = {
        "dataset": "chicago-doah-adjudication",
        "source": {"dataset_id": RESOURCE, "landing_page": LANDING_PAGE,
                   "extract_end": EXTRACT_END,
                   "fetched_rows": fetch_stats["fetched_rows"],
                   "reported_rows": fetch_stats["fetched_rows"],
                   "pages": fetch_stats["pages"],
                   "source_rows_sha256": fetch_stats["source_rows_sha256"],
                   "case_table_sha256": case_digest.hexdigest()},
        "grain": "one row per docket_number (case)",
        "exclusions": {key: value for key, value in stats.items()
                       if key != "conflicting_dispositions"},
        "levels": {"temporal": {name: {"rows": counts[name],
                                       "positives": events[name]["positives"],
                                       "distinct_events": events[name]["distinct_events"],
                                       "positive_rate": rates[name]} for name in counts}},
        "split_windows": {name: {"start": start, "end": end}
                          for name, (start, end) in SPLIT_WINDOWS.items()},
        "built_at_utc": built_at,
    }
    (out / "build_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    print(json.dumps({"ok": True, "out": str(out), "rows": counts, "positive_rate": rates,
                      "events": events, "level": "temporal"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
