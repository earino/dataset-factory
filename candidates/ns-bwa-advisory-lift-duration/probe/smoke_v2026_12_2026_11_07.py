#!/usr/bin/env python3
"""Coordinator smoke for the ns-bwa v2026.12 rebuild (2026-11-07).

Runs BEFORE any worker spend, exactly like the 2026-10-29 smoke for v2026.10:

  1. a synthetic register (the publisher's 7 columns, the two mandatory
     in-file fixtures included) exercises build.py end to end with
     --skip-vintage-checks;
  2. the written rows are asserted for the v2026.12 as-of semantics:
     strictly-earlier-only recency, same-(site, issue date) rows never
     seeing each other, blank-county rows never pooling (sentinel), the
     eight removed outcome-derived columns absent from every header, and
     the two fixtures landing with their documented labels;
  3. the real qualification gate runs two-phase on the synthetic artifact
     (qualify + exact-byte --accept) - the same gate, unmodified, that the
     worker will run on the real artifact;
  4. score.py's new register-derived persistence reference is unit-checked
     with fetch_register monkeypatched to the synthetic bytes (no network,
     no real-data scoring: every value here is synthetic construction).

No performance metric is computed on any real row: the real register is
never fetched by this smoke, and the AUC machinery of score.py never runs.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "source"
GATE = HERE.parents[2] / "skills" / "dataset-qualification" / "scripts" / \
    "qualify_dataset.py"
SCRATCH = Path("/opt/data/cache/scratch")

HEADERS = ["Site Name", "County", "Date Advisory Issued",
           "Date Advisory Removed", "Facility Type",
           "Length of Advisory in Days", "Reason for the Report"]

# (site, county, issue, removal, facility, length, reason)
# Windows: train 2008-2017, eval 2018-2020, holdout 2021-2024.
ROWS = [
    # the two mandatory in-file fixtures (always asserted by build.py)
    ("Maple Meadows Campground Inc", "Inverness County", "August 31 2024",
     "July 4 2025", "Registered", 307, "Total Coliform Present"),
    ("Canning Municipal Supply", "Kings County", "October 2 2025",
     "October 3 2025", "Municipal", 1, "Total Coliform Present"),
    # train window: recency chain, same-date blindness, blank county
    ("Alpha Lodge", "Halifax", "January 10 2010", "January 15 2010",
     "Registered", 5, "E. Coli Present"),
    ("Alpha Lodge", "Halifax", "March 1 2010", "April 10 2010",
     "Registered", 40, "Total Coliform Present"),
    ("Bravo Inn", "Kings", "May 5 2012", "May 8 2012",
     "Municipal", 3, "Total Coliform Present"),
    ("Bravo Inn", "Kings", "May 5 2012", "July 4 2012",
     "Municipal", 60, "Total Coliform Present"),
    ("Bravo Inn", "Kings", "June 4 2012", "June 6 2012",
     "Municipal", 2, "Total Coliform Present"),
    ("Charlie Camp", "", "July 1 2015", "July 20 2015",
     "Registered", 19, "E. Coli Present"),
    ("Delta Hall", "Kings", "June 1 2015", "July 1 2015",
     "Registered", 30, "Total Coliform Present"),
    ("Echo School", "Kings", "August 1 2015", "September 15 2015",
     "Municipal", 45, "Total Coliform Present"),
    # eval window: six rows, both classes, varied months/dows
    ("November Inn", "Yarmouth", "January 15 2018", "February 20 2018",
     "Registered", 36, "Total Coliform Present"),
    ("Osprey Lodge", "Halifax", "April 10 2018", "April 13 2018",
     "Municipal", 3, "E. Coli Present"),
    ("Petrel Camp", "Kings", "February 10 2019", "March 1 2019",
     "Registered", 19, "Total Coliform Present"),
    ("Quarry Hall", "Halifax", "July 7 2019", "August 15 2019",
     "Municipal", 39, "Total Coliform Present"),
    ("Raven Well", "Kings", "March 3 2020", "March 4 2020",
     "Registered", 1, "E. Coli Present"),
    ("Summit Pump", "Yarmouth", "September 12 2020", "October 25 2020",
     "Municipal", 43, "Total Coliform Present"),
    # holdout window: Maple fixture above plus four rows, both classes
    ("Tundra Station", "Halifax", "June 10 2021", "July 5 2021",
     "Registered", 25, "Total Coliform Present"),
    ("Umber Hall", "Kings", "September 9 2022", "October 20 2022",
     "Municipal", 41, "E. Coli Present"),
    ("Violet Camp", "Halifax", "May 13 2023", "May 14 2023",
     "Municipal", 1, "Total Coliform Present"),
    ("Willow Pump", "Kings", "April 7 2024", "May 12 2024",
     "Registered", 35, "Total Coliform Present"),
]

# Deterministic bulk so the synthetic splits clear the gate's count
# minimums (>=30 positives and >=20 distinct positive issue dates in eval
# and holdout) while keeping every categorical level small enough to be
# scored (levels <= rows/5) and label-mixed, and every numeric column
# non-separating. Unique generated sites leave the hand-written recency
# assertions untouched.
BULK = {
    "train": {"count": 30, "start": (2008, 2, 7), "step_days": 11},
    "eval": {"count": 56, "start": (2018, 1, 8), "step_days": 13},
    "holdout": {"count": 56, "start": (2021, 1, 6), "step_days": 13},
}
COUNTIES = ["Halifax", "Kings", "Yarmouth", "Inverness"]
FACILITIES = ["Registered", "Municipal"]
REASONS = ["Total Coliform Present", "E. Coli Present", "Other Reason"]


def bulk_rows() -> list[tuple]:
    from datetime import date as _date, timedelta as _timedelta
    rows = []
    serial = 0
    for split, spec in BULK.items():
        start = _date(*spec["start"])
        for j in range(spec["count"]):
            serial += 1
            issue = start + _timedelta(days=spec["step_days"] * j)
            label = 1 if (j % 7) < 4 else 0
            duration = 3 + (j % 20) if label else 35 + (j % 25)
            removal = issue + _timedelta(days=duration)
            rows.append((
                f"Gen Site {serial:03d}",
                COUNTIES[j % 4],
                f"{issue.strftime('%B')} {issue.day} {issue.year}",
                f"{removal.strftime('%B')} {removal.day} {removal.year}",
                FACILITIES[(j // 4) % 2],
                duration,
                REASONS[(j // 2) % 3],
            ))
    return rows

EXPECTED_COLUMNS = ["advisory_id", "issue_date", "site_name", "county",
                    "facility_type", "reason", "issue_month", "issue_dow",
                    "site_days_since_last", "county_days_since_last",
                    "lift30"]
REMOVED_COLUMNS = ["site_prior_advisories", "site_prior_resolved",
                   "site_prior_lift30_rate", "site_active_prior",
                   "county_prior_advisories", "county_prior_resolved",
                   "county_prior_lift30_rate", "county_active_prior"]


def die(message: str) -> None:
    print(f"SMOKE FAIL: {message}")
    raise SystemExit(1)


def read_csv(path: Path) -> list[dict]:
    import csv
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def expected_county_recency(county: str, instant: str) -> int:
    """Independent recomputation of the county recency rule.

    Reads the synthetic register rows (hand-written + bulk), normalises the
    county exactly like build.py, and returns instant minus the most recent
    strictly-earlier same-county issue date, or -1. Same-date duplicates do
    not change the max-date arithmetic; blank counties never pool.
    """
    from datetime import date as _date, datetime as _datetime
    instant_d = _date.fromisoformat(instant)
    key = " ".join((county or "").split()).strip().lower()
    if not key:
        return -1
    dates = []
    for row in ROWS + bulk_rows():
        candidate = " ".join((row[1] or "").split()).strip().lower()
        if candidate != key:
            continue
        dates.append(_datetime.strptime(row[2], "%B %d %Y").date())
    earlier = [d for d in dates if d < instant_d]
    return (instant_d - max(earlier)).days if earlier else -1


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="nsbwa-smoke-2026-11-07-",
                                 dir=SCRATCH))
    extract = work / "extract"
    register = work / "register.csv"
    import csv
    with register.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADERS)
        writer.writerows(ROWS)
        writer.writerows(bulk_rows())

    print("== build.py on the synthetic register ==")
    build = subprocess.run(
        [sys.executable, "-u", str(SOURCE / "build.py"),
         "--out", str(extract), "--work-dir", str(work / "tmpwork"),
         "--source", str(register), "--skip-vintage-checks",
         "--built-at", "2026-11-07T00:00:00Z"],
        capture_output=True, text=True)
    print(build.stdout[-1500:])
    if build.returncode != 0:
        print(build.stderr[-2000:])
        die(f"build.py exited {build.returncode}")

    train = read_csv(extract / "public" / "train.csv")
    eval_rows = read_csv(extract / "public" / "eval.csv")
    holdout = read_csv(extract / "private" / "holdout.csv")
    for name, rows in (("train", train), ("eval", eval_rows),
                       ("holdout", holdout)):
        header = list(rows[0].keys()) if rows else []
        if header != EXPECTED_COLUMNS:
            die(f"{name} header is {header}")
        forbidden = sorted(set(header) & set(REMOVED_COLUMNS))
        if forbidden:
            die(f"{name} still ships removed columns {forbidden}")

    by_site_issue = {(row["site_name"], row["issue_date"]): row
                     for rows in (train, eval_rows, holdout)
                     for row in rows}
    def field(site: str, issue: str, column: str):
        return by_site_issue[(site, issue)][column]

    print("== v2026.12 as-of recency semantics ==")
    checks = [
        ("alpha 2010-03-01 site recency is strictly-earlier (50)",
         field("alpha lodge", "2010-03-01", "site_days_since_last"), "50"),
        ("alpha 2010-01-10 first advisory is sentinel",
         field("alpha lodge", "2010-01-10", "site_days_since_last"), "-1"),
        ("bravo same-date pair never sees itself (row 1)",
         field("bravo inn", "2012-05-05", "site_days_since_last"), "-1"),
        ("bravo 2012-06-04 recency is 30",
         field("bravo inn", "2012-06-04", "site_days_since_last"), "30"),
        ("blank-county row never pools (sentinel)",
         field("charlie camp", "2015-07-01", "county_days_since_last"), "-1"),
        ("blank county ships as 'unknown'",
         field("charlie camp", "2015-07-01", "county"), "unknown"),
        ("echo county recency recomputed independently",
         field("echo school", "2015-08-01", "county_days_since_last"),
         str(expected_county_recency("Kings", "2015-08-01"))),
        ("maple fixture is holdout label 0",
         field("maple meadows campground inc", "2024-08-31", "lift30"), "0"),
        ("maple county recency recomputed independently",
         field("maple meadows campground inc", "2024-08-31",
               "county_days_since_last"),
         str(expected_county_recency("Inverness County", "2024-08-31"))),
        ("willow county recency recomputed independently",
         field("willow pump", "2024-04-07", "county_days_since_last"),
         str(expected_county_recency("Kings", "2024-04-07"))),
        ("same-date bravo rows carry their own labels (3d -> 1)",
         [field("bravo inn", "2012-05-05", "lift30")], None),
    ]
    for label, value, expected in checks[:-1]:
        if value != expected:
            die(f"{label}: got {value!r}, expected {expected!r}")
        print(f"  ok: {label}")
    same_date_labels = {row["lift30"] for row in train
                        if row["site_name"] == "bravo inn"
                        and row["issue_date"] == "2012-05-05"}
    if same_date_labels != {"0", "1"}:
        die(f"same-date bravo rows lost their distinct labels: "
            f"{same_date_labels}")
    print("  ok: same-date bravo rows keep distinct labels 0/1")
    for split, rows in (("train", train), ("eval", eval_rows),
                        ("holdout", holdout)):
        labels = {row["lift30"] for row in rows}
        if labels != {"0", "1"}:
            die(f"{split} does not carry both classes: {labels}")
    if len(train) != 38 or len(eval_rows) != 62 or len(holdout) != 61:
        die(f"split sizes changed: train {len(train)}, eval {len(eval_rows)},"
            f" holdout {len(holdout)}")
    print(f"  ok: splits train {len(train)} / eval {len(eval_rows)} / "
          f"holdout {len(holdout)}, both classes everywhere")
    for split, rows in (("eval", eval_rows), ("holdout", holdout)):
        positives = sum(1 for row in rows if row["lift30"] == "1")
        dates = {row["issue_date"] for row in rows if row["lift30"] == "1"}
        if positives < 30 or len(dates) < 20:
            die(f"{split} bulk too thin: {positives} positives over "
                f"{len(dates)} distinct dates (gate needs 30/20)")

    print("== pre-check with the gate's own scorer (no perfect columns) ==")
    gate_ns: dict = {}
    exec(compile(GATE.read_text(), str(GATE), "exec"), gate_ns)
    for split, rows in (("train", train), ("eval", eval_rows),
                        ("holdout", holdout)):
        labels = [1 if row["lift30"] == "1" else 0 for row in rows]
        for column in EXPECTED_COLUMNS[:-1]:
            values = [row[column] for row in rows]
            finding = gate_ns["column_leak_score"](values, labels)
            if finding["determines_label"]:
                die(f"synthetic {split}.{column} accidentally separates the "
                    f"label (auc={finding['auc']}); fix the fixture")
    print("  ok: no synthetic column separates the label in any split")

    print("== gate two-phase on the synthetic artifact ==")
    report_path = work / "qualification.json"
    qualify = subprocess.run(
        [sys.executable, str(GATE), str(extract), "--json",
         "--report", str(report_path)],
        capture_output=True, text=True)
    print(qualify.stdout[-1200:])
    if qualify.returncode != 0:
        print(qualify.stderr[-2000:])
        die(f"the gate refused the synthetic artifact (exit "
            f"{qualify.returncode})")
    accept = subprocess.run(
        [sys.executable, str(GATE), "--accept", str(report_path),
         str(extract)],
        capture_output=True, text=True)
    print(accept.stdout[-400:])
    if accept.returncode != 0:
        die(f"--accept refused the synthetic artifact (exit "
            f"{accept.returncode})")

    print("== score.py persistence helper (synthetic, no network) ==")
    spec = importlib.util.spec_from_file_location("nsbwa_score",
                                                  SOURCE / "score.py")
    assert spec is not None and spec.loader is not None
    score = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(score)
    setattr(score, "fetch_register", lambda: register.read_bytes())
    summary = {"fetch": {"sha256": __import__("hashlib").sha256(
        register.read_bytes()).hexdigest()}}
    synthetic_eval = [
        {"site_name": "alpha lodge", "issue_date": "2010-06-01"},
        {"site_name": "bravo inn", "issue_date": "2012-06-04"},
        {"site_name": "foxtrot clinic", "issue_date": "2019-01-01"},
    ]
    scores, info = score.site_persistence_scores(synthetic_eval, 0.4, summary)
    expected_persistence = [0.5, 1.0, 0.4]
    if scores != expected_persistence:
        die(f"persistence reference values {scores} != {expected_persistence}")
    if info["covered_rows"] != 2:
        die(f"persistence covered_rows {info['covered_rows']} != 2")
    print(f"  ok: persistence scores {scores} (covered 2/3, fallback 0.4)")

    shutil.rmtree(work)
    print("SMOKE PASS: build, as-of semantics, gate two-phase, accept and "
          "the persistence helper all behave as designed on synthetic data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
