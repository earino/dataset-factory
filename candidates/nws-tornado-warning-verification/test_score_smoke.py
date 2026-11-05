#!/usr/bin/env python3
"""Synthetic smoke test for score.py machinery (never touches real bytes).

Builds tiny synthetic train/eval CSVs with the shipped column layout, a fake
passing qualification report, and runs score.py end to end. Verifies the
persistence gap rule with hand-checked cases. This is a rehearsal only; no
real data is read and no real figure is produced.
"""
import csv
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
SMOKE = Path("/opt/data/cache/scratch/nws-score-smoke")
COLUMNS = ["row_id", "wfo", "fcster", "issue_doy", "issue_hour",
           "issue_weekday", "issue_month", "duration_min", "hail_tag_in",
           "wind_tag_mph", "svr_tornado_possible", "tor_in_svrtorpossible",
           "county_count", "county_area_km2", "polygon_area_km2", "perimeter",
           "shared_border_pct", "size_reduction_pct", "polygon_county_ratio",
           "lat0", "lon0", "issue_ts", "issue_date", "verified"]


def row(i, wfo, issue, dur, verified, fcster="SMITH"):
    dt = datetime(2019, 6, 1) + timedelta(hours=i * 37)
    if issue:
        dt = issue
    return {
        "row_id": f"2019-{wfo}-{i:04d}", "wfo": wfo, "fcster": fcster,
        "issue_doy": dt.timetuple().tm_yday, "issue_hour": dt.hour,
        "issue_weekday": dt.weekday(), "issue_month": dt.month,
        "duration_min": dur, "hail_tag_in": "", "wind_tag_mph": "",
        "svr_tornado_possible": 1, "tor_in_svrtorpossible": 0,
        "county_count": 2, "county_area_km2": 2000.0,
        "polygon_area_km2": 800.0, "perimeter": 120.0,
        "shared_border_pct": 40.0, "size_reduction_pct": 60.0,
        "polygon_county_ratio": 0.4, "lat0": 35.0, "lon0": -92.0,
        "issue_ts": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "issue_date": dt.date().isoformat(), "verified": verified,
    }


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    if SMOKE.exists():
        print("smoke dir exists; using fresh subdir")
        import time
        out = SMOKE / f"run-{int(time.time())}"
    else:
        out = SMOKE
    train = [row(i, "ABC", None, 45, i % 2) for i in range(120)]
    train += [row(i, "XYZ", None, 45, 1) for i in range(40)]
    # eval: the first row's WFO ABC has a prior train warning 30+ min earlier;
    # a same-instant prior (still live) must be skipped; WFO NEW has no prior.
    eval_rows = [
        row(0, "ABC", datetime(2019, 6, 2, 1), 45, 1),
        row(1, "XYZ", datetime(2019, 6, 2, 2), 45, 0),
        row(2, "NEW", datetime(2019, 6, 2, 3), 45, 1),
        row(3, "ABC", datetime(2019, 6, 2, 4), 45, 0),
    ]
    write(out / "public" / "train.csv", train)
    write(out / "public" / "eval.csv", eval_rows)
    write(out / "private" / "holdout.csv", [row(0, "ABC", None, 45, 1)])
    report = {"ok": True, "artifact": {"artifact_version": "smoke"}}
    (out / "qualification.json").write_text(json.dumps(report))
    rc = subprocess.run(
        [sys.executable, str(HERE / "source" / "score.py"),
         "--data", str(out), "--accepted-report", str(out / "qualification.json"),
         "--report", str(out / "references.json")],
        capture_output=True, text=True)
    print(rc.stdout)
    print(rc.stderr[-500:] if rc.stderr else "")
    if rc.returncode != 0:
        raise SystemExit(f"score.py smoke FAILED rc={rc.returncode}")
    refs = json.load(open(out / "references.json"))
    p = refs["references"]["persistence_same_wfo_30min"]
    c = refs["references"]["calendar_identity_wfo_doy_hour"]
    m = refs["references"]["majority_constant"]
    assert p["rows_with_prior_outcome"] + p["rows_fallback_wfo_prior"] \
        + p["rows_fallback_global_prior"] == 4, p
    assert p["rows_fallback_global_prior"] == 1, p  # WFO NEW
    assert m["train_majority"] == 1, m  # 100 positives of 160 train rows
    assert c["eval_auc"] is not None, c
    print("SMOKE OK:", json.dumps({
        "persistence": {k: p[k] for k in ("rows_with_prior_outcome",
                                         "rows_fallback_wfo_prior",
                                         "rows_fallback_global_prior")},
        "calendar_auc": c["eval_auc"],
        "majority_accuracy": m["eval_accuracy"],
        "bootstrap": refs["bootstrap"]["persistence_vs_calendar"]["ci95"]},
        indent=1))


if __name__ == "__main__":
    main()
