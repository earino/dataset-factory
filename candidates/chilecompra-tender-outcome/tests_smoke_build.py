#!/usr/bin/env python3
"""Synthetic-fixture smoke for the rebuilt chilecompra-tender-outcome build.

Runs the REAL build over synthetic member documents (fabricated data; nothing
here is quotable), then the REAL gate, --accept and score.py over the fixture
output, and asserts the rebuilt label rule behaves as designed:

  * terminal-state-within-180d: boundary at exactly pub+180d (in) vs +181d (out)
  * last-terminal-release-wins: active->cancelled = revoked, unsuccessful->active
    = adjudicated, pending->active = adjudicated, active->pending = adjudicated
  * censored buckets: pending-only, no award, award beyond horizon,
    compiled-only awards
  * membership buckets: publication_state_not_evidenced, publication month
    outside cohort, no tender release, duplicate ocid
  * quality.json: derived cohort months (no stale 2016/2021-01 prose), horizon
    180, honest outcome accounting whose identity closes over the buckets
  * score.py --previous-eval: identical-row overlap, label disagreements

Usage:  python3 tests_smoke_build.py   (from the candidate directory)
"""
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD = HERE / "source" / "build.py"
SCORE = HERE / "source" / "score.py"
GATE = HERE.parent.parent / "skills" / "dataset-qualification" / "scripts" / "qualify_dataset.py"

COHORTS = {"train": [(2019, 5), (2019, 6)],
           "eval": [(2020, 5), (2020, 6)],
           "holdout": [(2021, 5), (2021, 6)]}
REGIONS = ["REGION-A", "REGION-B", "REGION-C", "REGION-D"]
CODES = ["(L1) Licitacion Publica", "(LE) Licitacion Estatica",
         "(LP) Licitacion Privada", "(LQ) Obras"]
SEGMENTS = ["43", "44", "45", "46", "47", "48"]
CURRENCIES = ["CLP", "CLP", "CLP", "USD"]


def h(ocid, salt=""):
    return int(hashlib.sha256((ocid + salt).encode()).hexdigest()[:8], 16)


def award_entry(status, rel_date, details=""):
    entry = {"id": "aw1", "status": status, "date": rel_date}
    if details:
        entry["statusDetails"] = details
    return entry


def make_record(ocid, pub_day, *, award_rels=None, first_status="active",
                compiled_tender_status=None, compiled_awards=None):
    """award_rels: list of (release_date, [entries], tags)."""
    tender = {
        "status": first_status,
        "title": f"Fixture tender {ocid}",
        "description": "synthetic fixture description " + "x" * (h(ocid, "d") % 40),
        "procurementMethod": "open",
        "procurementMethodDetails": CODES[h(ocid, "p") % len(CODES)],
        "value": {"amount": 500000 + (h(ocid, "v") % 900) * 1000,
                  "currency": CURRENCIES[h(ocid, "c") % len(CURRENCIES)]},
        "tenderPeriod": {"startDate": f"{pub_day}T00:00:00Z",
                         "endDate": f"{pub_day}T00:00:00Z",
                         "durationInDays": 15 + h(ocid, "t") % 40},
        "items": [{"id": str(i), "quantity": 1 + (h(ocid, f"q{i}") % 9),
                   "classification": {"id": SEGMENTS[h(ocid, f"s{i}") % len(SEGMENTS)]
                                      + "000000", "scheme": "UNSPSC"}}
                  for i in range(1 + h(ocid, "i") % 4)],
    }
    releases = [{"ocid": ocid, "id": f"{ocid}-t1", "date": f"{pub_day}T12:00:00Z",
                 "tag": ["tender"], "tender": tender,
                 "buyer": {"id": "CL-RUT-1", "name": "Fixture Buyer"},
                 "parties": [{"id": "CL-RUT-1", "name": "Fixture Buyer",
                              "roles": ["buyer"],
                              "address": {"region": REGIONS[h(ocid, "r") % len(REGIONS)]}}]}]
    for index, (rel_date, entries, tags) in enumerate(award_rels or []):
        releases.append({"ocid": ocid, "id": f"{ocid}-a{index}",
                         "date": rel_date, "tag": tags or ["award"],
                         "awards": entries})
    record = {"ocid": ocid, "releases": releases}
    compiled = {}
    if compiled_tender_status is not None:
        compiled["tender"] = {"status": compiled_tender_status}
    if compiled_awards is not None:
        compiled["awards"] = compiled_awards
    if compiled:
        record["compiledRelease"] = compiled
    return {"records": [record]}


def lag_day(pub_day, days):
    return (date.fromisoformat(pub_day) + timedelta(days=days)).isoformat()


def volume_rows(split, month, count, positive):
    """count rows spread across the month, all terminal within the horizon."""
    year, mon = month
    sign = "pos" if positive else "neg"
    days = [date(year, mon, 1) + timedelta(days=i)
            for i in range((date(year + (mon == 12), (mon % 12) + 1, 1)
                            - date(year, mon, 1)).days)]
    out = []
    for i in range(count):
        pub = days[(i * 3 + 1) % len(days)].isoformat()
        ocid = f"ocds-fx-{split}-{sign}-{mon:02d}-{i:04d}"
        status = "unsuccessful" if positive else "active"
        details = "7-Desierta (o art. 3 ó 9 Ley 19.886)" if positive else "8-Adjudicada"
        rel = lag_day(pub, 30 + (h(ocid) % 60))
        out.append(make_record(ocid, pub,
                               award_rels=[(f"{rel}T10:00:00Z",
                                            [award_entry(status, rel, details)],
                                            ["award"])]))
    return out


def build_fixture_members():
    members = []
    # gate capacity minimums: >=30 positives over >=20 distinct positive days
    # in eval AND holdout; both classes everywhere.
    for split, months in COHORTS.items():
        for month in months:
            members += volume_rows(split, month, 18, positive=True)
            members += volume_rows(split, month, 18, positive=False)
    # label-rule fixtures (train months; asserted via buckets and row checks)
    pub = "2019-05-10"
    fixtures = {
        # terminal within horizon, straightforward
        "fx-active": ([(f"{lag_day(pub, 40)}T10:00:00Z",
                        [award_entry("active", lag_day(pub, 40))], ["award"])], 0),
        "fx-deserted": ([(f"{lag_day(pub, 45)}T10:00:00Z",
                          [award_entry("unsuccessful", lag_day(pub, 45))], ["award"])], 1),
        # horizon boundary: pub 2019-05-10T12:00Z + 180d = 2019-11-06T12:00Z
        # (exactly at the cutoff -> inside); +181d -> outside
        "fx-h180-in": ([(f"{lag_day(pub, 180)}T12:00:00Z",
                         [award_entry("unsuccessful", lag_day(pub, 180))], ["award"])], 1),
        "fx-h181-out": ([(f"{lag_day(pub, 181)}T00:00:00Z",
                          [award_entry("unsuccessful", lag_day(pub, 181))], ["award"])], None),
        # last terminal release wins
        "fx-active-then-cancelled": (
            [(f"{lag_day(pub, 40)}T10:00:00Z", [award_entry("active", lag_day(pub, 40))],
              ["award"]),
             (f"{lag_day(pub, 60)}T10:00:00Z",
              [award_entry("cancelled", lag_day(pub, 60))], ["awardUpdate"])], None),
        "fx-unsuccessful-then-active": (
            [(f"{lag_day(pub, 40)}T10:00:00Z",
              [award_entry("unsuccessful", lag_day(pub, 40))], ["award"]),
             (f"{lag_day(pub, 70)}T10:00:00Z", [award_entry("active", lag_day(pub, 70))],
              ["awardUpdate"])], 0),
        "fx-pending-then-active": (
            [(f"{lag_day(pub, 20)}T10:00:00Z", [award_entry("pending", lag_day(pub, 20))],
              ["award"]),
             (f"{lag_day(pub, 90)}T10:00:00Z", [award_entry("active", lag_day(pub, 90))],
              ["awardUpdate"])], 0),
        "fx-active-then-pending": (
            [(f"{lag_day(pub, 40)}T10:00:00Z", [award_entry("active", lag_day(pub, 40))],
              ["award"]),
             (f"{lag_day(pub, 100)}T10:00:00Z", [award_entry("pending", lag_day(pub, 100))],
              ["awardUpdate"])], 0),
        # censored shapes
        "fx-pending-only": ([(f"{lag_day(pub, 50)}T10:00:00Z",
                              [award_entry("pending", lag_day(pub, 50))], ["award"])], None),
        "fx-no-award": ([], None),
        "fx-compiled-only": ([], None),
        # mixed terminal inside one release (no active)
        "fx-mixed": ([(f"{lag_day(pub, 44)}T10:00:00Z",
                       [award_entry("unsuccessful", lag_day(pub, 44)),
                        award_entry("cancelled", lag_day(pub, 44))], ["award"])], None),
        # disagreement diagnostic: deserted but compiled tender status active
        "fx-disagree": ([(f"{lag_day(pub, 47)}T10:00:00Z",
                          [award_entry("unsuccessful", lag_day(pub, 47))], ["award"])], 1),
    }
    extras = {}
    for ocid, (rels, _label) in fixtures.items():
        kwargs = {}
        if ocid == "fx-compiled-only":
            kwargs["compiled_awards"] = [
                {"id": "c1", "status": "active", "date": lag_day(pub, 50)}]
        if ocid == "fx-disagree":
            kwargs["compiled_tender_status"] = "active"
        members.append(make_record(f"ocds-{ocid}", pub, award_rels=rels, **kwargs))
        extras[ocid] = rels
    # membership fixtures
    members.append(make_record("ocds-fx-not-evidenced", pub,
                               first_status="complete",
                               award_rels=[(f"{lag_day(pub, 40)}T10:00:00Z",
                                            [award_entry("active", lag_day(pub, 40))],
                                            ["award"])]))
    members.append(make_record("ocds-fx-outside-cohort", "2019-07-15",
                               award_rels=[(f"{lag_day('2019-07-15', 40)}T10:00:00Z",
                                            [award_entry("active",
                                                         lag_day("2019-07-15", 40))],
                                            ["award"])]))
    members.append({"records": [{"ocid": "ocds-fx-no-tender",
                                 "releases": [{"ocid": "ocds-fx-no-tender",
                                               "id": "x", "date": f"{pub}T12:00:00Z",
                                               "tag": ["award"],
                                               "awards": [award_entry("active", pub)]}]}]})
    # duplicate ocid: first scores, second is bucketed
    members.append(make_record("ocds-fx-dupe", "2019-06-05",
                               award_rels=[(f"{lag_day('2019-06-05', 30)}T10:00:00Z",
                                            [award_entry("active",
                                                         lag_day('2019-06-05', 30))],
                                            ["award"])]))
    members.append(make_record("ocds-fx-dupe", "2019-06-06",
                               award_rels=[(f"{lag_day('2019-06-06', 30)}T10:00:00Z",
                                            [award_entry("active",
                                                         lag_day('2019-06-06', 30))],
                                            ["award"])]))
    return members, extras


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="cl-smoke-", dir="/opt/data/cache/scratch"))
    members_dir = work / "members"
    members_dir.mkdir()
    members, _extras = build_fixture_members()
    for i, member in enumerate(members):
        (members_dir / f"m{i:04d}.json").write_text(json.dumps(member))
    print(f"[smoke] {len(members)} synthetic members in {members_dir}")

    out = work / "extract"
    run = subprocess.run([sys.executable, "-u", str(BUILD), "--out", str(out),
                          "--members-dir", str(members_dir), "--smoke",
                          "--built-at", "2026-10-23T00:00:00Z"],
                         capture_output=True, text=True)
    print(run.stdout[-4000:])
    if run.returncode != 0:
        print(run.stderr)
        raise SystemExit(f"SMOKE FAIL: build exit {run.returncode}")
    summary = json.loads((out / "summary.json").read_text())
    buckets = summary["buckets"]
    train = buckets["train"]

    def count(key):
        return train.get(key, 0)
    # targeted assertions: read the actual CSV rows for the fixture ocids
    rows = {}
    for split, rel in [("train", "public/train.csv"), ("eval", "public/eval.csv"),
                       ("holdout", "private/holdout.csv")]:
        with (out / rel).open() as handle:
            for row in csv.DictReader(handle):
                rows[row["tender_id"]] = row

    expectations = {
        "ocds-fx-active": "0", "ocds-fx-deserted": "1",
        "ocds-fx-h180-in": "1", "ocds-fx-unsuccessful-then-active": "0",
        "ocds-fx-pending-then-active": "0", "ocds-fx-active-then-pending": "0",
        "ocds-fx-disagree": "1", "ocds-fx-dupe": "0",
    }
    problems = []
    for ocid, label in expectations.items():
        got = rows.get(ocid, {}).get("deserted")
        if got != label:
            problems.append(f"{ocid}: expected deserted={label}, got {got!r}")
    for ocid in ("ocds-fx-h181-out", "ocds-fx-active-then-cancelled",
                 "ocds-fx-pending-only", "ocds-fx-no-award", "ocds-fx-compiled-only",
                 "ocds-fx-mixed", "ocds-fx-not-evidenced", "ocds-fx-outside-cohort",
                 "ocds-fx-no-tender"):
        if ocid in rows:
            problems.append(f"{ocid}: should not be scored, found in CSVs")

    for key, expected in [
            ("unobserved_target:award_beyond_horizon", 1),
            ("outcome:revoked", 1),
            ("unobserved_target:pending_within_horizon", 1),
            ("unobserved_target:no_award_within_horizon", 1),
            ("unobserved_target:compiled_only_awards", 1),
            ("outcome:mixed_terminal", 1),
            ("duplicate_ocid", 1)]:
        if count(key) != expected:
            problems.append(f"bucket {key}: expected {expected}, got {count(key)}")
    # membership-bucket expectations computed from the member list itself:
    # each member is processed once per (split, cohort month) iteration, so it
    # fails the month filter in every iteration but its own.
    from collections import Counter
    expected_membership = {split: Counter() for split in COHORTS}
    for member in members:
        record = member["records"][0]
        first = [r for r in record.get("releases", [])
                 if "tender" in (r.get("tag") or []) and r.get("date")]
        if not first:
            for split in COHORTS:
                expected_membership[split]["no_tender_release"] += len(COHORTS[split])
            continue
        first.sort(key=lambda r: r["date"])
        pub_month = first[0]["date"][:7]
        status = ((first[0].get("tender") or {}).get("status") or "").strip().lower()
        for split, months in COHORTS.items():
            for year, mon in months:
                if f"{year}-{mon:02d}" != pub_month:
                    expected_membership[split]["publication_month_outside_cohort"] += 1
                elif status != "active":
                    expected_membership[split]["publication_state_not_evidenced"] += 1
    for split in COHORTS:
        for key, want in expected_membership[split].items():
            got = buckets[split].get(key, 0)
            if got != want:
                problems.append(f"{split} bucket {key}: expected {want}, got {got}")

    if summary["tender_final_status_disagreements"].get("unsuccessful->active") != 1:
        problems.append("disagreement diagnostic missing")

    # accounting identity closes over the buckets
    for split, account in summary["outcome_accounting"].items():
        total = (account["scored_rows"] + account["revoked"] + account["mixed_terminal"]
                 + account["duplicate_ocid"] + account["censored"])
        if total != account["eligible_rows"]:
            problems.append(f"{split}: accounting identity {total} != "
                            f"{account['eligible_rows']}")
        if account["positives"] != summary["splits"][split]["positives"]:
            problems.append(f"{split}: positives mismatch")

    quality = json.loads((out / "quality.json").read_text())
    selection = quality["timing"]["row_selection"]["latest_period_used"]
    for stale in ("2016-05", "2021-01"):
        if stale in selection:
            problems.append(f"stale cohort {stale} still in row_selection")
    for fresh in ("2019-05", "2020-05", "2021-05", "2021-06"):
        if fresh not in selection:
            problems.append(f"derived cohort {fresh} missing from row_selection")
    if quality["horizon_days"] != 180:
        problems.append("horizon_days != 180")
    if "+" in selection:
        problems.append("row_selection latest_period_used contains '+'")
    if quality["outcome_conditioning"]["train"]["eligible_rows"] < 1:
        problems.append("outcome_conditioning empty")
    if quality["timing"]["observations"] != []:
        problems.append("fixture (members-dir) run should carry no observations")

    # terminal_outcome boundary unit checks, loading build.py without pycache
    namespace: dict = {"__name__": "build_under_test"}
    exec(compile(BUILD.read_text(), str(BUILD), "exec"), namespace)
    terminal_outcome = namespace["terminal_outcome"]  # type: ignore[assignment]
    vintage_observations = namespace["vintage_observations"]  # type: ignore[assignment]
    instant = datetime(2020, 6, 30, 12, 0, tzinfo=timezone.utc)
    rel_in = "2020-12-27T00:00:00Z"     # exactly pub+180d
    rel_out = "2020-12-28T00:00:00Z"    # pub+181d
    for rel_date, want_in in [(rel_in, True), (rel_out, False)]:
        record = make_record("ocds-unit", "2020-06-30",
                             award_rels=[(rel_date,
                                          [award_entry("unsuccessful", rel_date)],
                                          ["award"])])
        label, key, _details = terminal_outcome(record["records"][0], instant)
        if want_in and (label, key) != (1, "outcome:deserted"):
            problems.append(f"boundary {rel_date}: expected scored deserted, got {label},{key}")
        if not want_in and key != "unobserved_target:award_beyond_horizon":
            problems.append(f"boundary {rel_date}: expected beyond-horizon, got {label},{key}")
    fake_sources = {"201905": {"last_modified": "Wed, 13 Jan 2021 11:10:01 GMT"},
                    "201906": {"last_modified": "Wed, 13 Jan 2021 11:32:28 GMT"},
                    "202106": {"last_modified": "Fri, 31 Dec 2021 04:15:29 GMT"}}
    obs = vintage_observations(fake_sources)
    if len(obs) != 3 or obs[0] != {"period": "2019-05", "period_end": "2019-05-31",
                                   "published": "2021-01-13",
                                   "channel": obs[0]["channel"]}:
        problems.append(f"vintage_observations wrong: {obs}")

    if problems:
        for problem in problems:
            print("SMOKE FAIL:", problem)
        raise SystemExit(1)

    # gate on the fixture output, then accept, then score with --previous-eval
    report_path = work / "qual.json"
    gate = subprocess.run([sys.executable, str(GATE), str(out), "--json",
                           "--report", str(report_path)],
                          capture_output=True, text=True)
    if gate.returncode != 0:
        print(gate.stdout[-6000:], gate.stderr[-2000:])
        raise SystemExit("SMOKE FAIL: gate did not pass the fixture output")
    gate_report = json.loads(report_path.read_text())
    if not gate_report.get("ok") or gate_report.get("failed_checks"):
        raise SystemExit(f"SMOKE FAIL: gate report {gate_report.get('failed_checks')}")
    accept = subprocess.run([sys.executable, str(GATE), "--accept", str(report_path),
                             str(out)], capture_output=True, text=True)
    if accept.returncode != 0:
        print(accept.stdout[-3000:])
        raise SystemExit("SMOKE FAIL: --accept did not verify the fixture bytes")

    prev = work / "previous.txt"
    with prev.open("w") as handle:
        handle.write("tender_id,deserted\n")
        for row in csv.DictReader((out / "public/eval.csv").open()):
            handle.write(f"{row['tender_id']},{row['deserted']}\n")
        handle.write("ocds-fx-ghost-row,1\n")  # in previous, not in new
    score_report = work / "refs.json"
    score = subprocess.run([sys.executable, str(SCORE), "--data", str(out),
                           "--previous-eval", str(prev),
                           "--report", str(score_report)],
                          capture_output=True, text=True)
    if score.returncode != 0:
        print(score.stdout[-4000:], score.stderr[-2000:])
        raise SystemExit("SMOKE FAIL: score.py failed on the fixture")
    refs = json.loads(score_report.read_text())
    comparison = refs["references"]["previous_eval_comparison"]
    if comparison["old_only_rows"] != 1:
        problems.append(f"old_only_rows {comparison['old_only_rows']} != 1")
    if comparison["identical_rows"] != refs["references"]["unspsc_only"]["rows"]:
        problems.append("identical_rows != eval rows (fixture eval rows all overlap)")
    if problems:
        for problem in problems:
            print("SMOKE FAIL:", problem)
        raise SystemExit(1)

    print("[smoke] SMOKE OK: build, gate, accept and previous-eval comparison all "
          "behave as designed on the synthetic fixture")
    print(f"[smoke] fixture kept at {work}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
