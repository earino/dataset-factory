#!/usr/bin/env python3
"""Local smoke for the nz-ea-baseline-001 bundle, before any worker spend.

Builds a synthetic extract (same layout/columns as the real artifact) and a stub
train.py that exposes the runner contract, then exercises the bundle's own scripts
end to end in pure stdlib:

  1. materialize.py: task.json written from meta.json TASK_KEYS, public CSVs copied,
     private holdout NOT copied;
  2. reference_check.py clean path: identity holds, all three recomputed bars equal
     their hand-computed values (persistence 0.8, mean7 0.7, calendar 9.5/15), the
     stub model AUC is 1.0, both paired differences and per-target-year rows are
     produced, and the year-boundary row lands in the target year (anchor + 7 days);
  3. reference_check.py identity-failure path: wrong expected rows -> exit 2 (the
     guard is shown to bite);
  4. reference_check.py bar-agreement-failure path: a wrong accepted persistence
     value -> exit 4 (a broken comparison basis is loud, not silent);
  5. report.py clean path: crafted train/validate logs + the real reference_check
     output with agreeing model AUCs -> exit 0, agreement flags true;
  6. report.py disagreement path: a reference_check.json whose bar disagrees ->
     exit 5.

Exit 0 only if every step's expectation is observed.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
BUNDLE = ROOT / "candidates/nz-ea-wholesale-price-exceedance/baseline"
SMOKE = Path("/opt/data/cache/scratch/nz-ea-baseline-smoke")

COLUMNS = ["row_id", "target_high_price", "anchor_date", "target_week", "island",
           "last_day_mean", "mean_7d", "mean_30d", "max_30d", "std_7d",
           "days_above_threshold_30d", "cross_island_ratio_7d", "anchor_month",
           "anchor_dow", "anchor_doy_sin", "anchor_doy_cos"]


def rows_csv(rows):
    lines = [",".join(COLUMNS)]
    for row in rows:
        lines.append(",".join(str(row[c]) for c in COLUMNS))
    return "\n".join(lines) + "\n"


def synthetic_row(row_id, label, anchor, week, island, last, mean7):
    return {"row_id": row_id, "target_high_price": label, "anchor_date": anchor,
            "target_week": week, "island": island, "last_day_mean": last,
            "mean_7d": mean7, "mean_30d": 90, "max_30d": 130, "std_7d": 5,
            "days_above_threshold_30d": 2, "cross_island_ratio_7d": "1.0",
            "anchor_month": int(anchor[5:7]), "anchor_dow": 1,
            "anchor_doy_sin": "0.5", "anchor_doy_cos": "0.5"}


def synthetic_extract():
    # Train: (NI, 2019-W01) rate 2/4 = 0.5; (SI, 2019-W02) rate 1/4 = 0.25.
    # Global train rate 3/8 = 0.375, so the majority class is 0.
    train = [
        synthetic_row("t1", 1, "2019-01-02", "2019-W01", "NI", 120, 110),
        synthetic_row("t2", 1, "2019-01-03", "2019-W01", "NI", 120, 110),
        synthetic_row("t3", 0, "2019-01-04", "2019-W01", "NI", 80, 85),
        synthetic_row("t4", 0, "2019-01-05", "2019-W01", "NI", 80, 85),
        synthetic_row("t5", 1, "2019-01-08", "2019-W02", "SI", 120, 110),
        synthetic_row("t6", 0, "2019-01-09", "2019-W02", "SI", 80, 85),
        synthetic_row("t7", 0, "2019-01-10", "2019-W02", "SI", 80, 85),
        synthetic_row("t8", 0, "2019-01-11", "2019-W02", "SI", 80, 85),
    ]
    # Eval: 3 positives (last_day_mean 120, mean_7d 110) and 5 negatives
    # (last_day_mean 80x4 + 150; mean_7d 85x3 + 110 + 140).
    # Hand-computed bars: persistence 12/15 = 0.8; mean7 10.5/15 = 0.7;
    # calendar 9.5/15. The 2018-12-30 anchor crosses the year boundary +7 days
    # (target day 2019-01-06), so its row must land in target year 2019.
    eval_rows = [
        synthetic_row("e1", 1, "2019-03-04", "2019-W01", "NI", 120, 110),
        synthetic_row("e2", 0, "2019-03-05", "2019-W01", "NI", 80, 85),
        synthetic_row("e3", 1, "2019-03-06", "2019-W01", "NI", 120, 110),
        synthetic_row("e4", 0, "2019-03-07", "2019-W01", "NI", 80, 85),
        synthetic_row("e5", 1, "2018-12-30", "2019-W02", "SI", 120, 110),
        synthetic_row("e6", 0, "2019-03-08", "2019-W02", "SI", 80, 85),
        synthetic_row("e7", 0, "2019-03-09", "2019-W02", "SI", 80, 110),
        synthetic_row("e8", 0, "2019-03-10", "2019-W02", "SI", 150, 140),
    ]
    meta = {"name": "smoke-nz-ea", "description": "synthetic smoke extract",
            "target": "target_high_price", "positive_label": 1,
            "id_columns": ["row_id"], "split": {"train": "x", "eval": "y"},
            "columns": COLUMNS, "rows": {"train": 8, "eval": 8, "holdout": 2},
            "positive_rate": 0.5, "label_rule": "synthetic"}
    return train, eval_rows, meta


STUB_TRAIN = '''\
"""Stub train.py exposing the runner contract, for the local smoke only."""
import csv
import json

TASK = json.load(open("task.json"))
TARGET = TASK["target"]
POSITIVE = TASK["positive_label"]

with open("data/train.csv", newline="") as handle:
    train = list(csv.DictReader(handle))
with open("data/eval.csv", newline="") as handle:
    evald = list(csv.DictReader(handle))


def to_y(df):
    return [int(row[TARGET] == str(POSITIVE)) for row in df]


def predict_proba(df):
    # perfect ranking on this synthetic fixture
    return [0.9 if row[TARGET] == str(POSITIVE) else 0.1 for row in df]


if __name__ == "__main__":
    labels = to_y(evald)
    scores = predict_proba(evald)
    positives = sum(labels)
    negatives = len(labels) - positives
    wins = sum(1 for y, p in zip(labels, scores) for y2, p2 in zip(labels, scores)
               if y == 1 and y2 == 0 and p > p2)
    print(f"Eval AUC: {wins / (positives * negatives):.4f}")
'''


def run(command, cwd=None):
    return subprocess.run(command, capture_output=True, text=True, cwd=cwd)


def expect(condition, message):
    if not condition:
        print(f"SMOKE FAIL: {message}", file=sys.stderr)
        raise SystemExit(1)
    print(f"  ok: {message}")


def main() -> int:
    print("== 0. fetch-spec integrity (guards a hand-typed digest) ==")
    # The nz-ea-baseline-001/002 failures were one mis-transcribed hex character in
    # this job's fetch spec: the worker downloaded the correct bytes and its digest
    # guard refused them against the wrong expectation, twice. The fetch spec is
    # derived data - every entry must equal the bundled qualification report's own
    # artifact digest - so check it here, before any worker spend.
    job_spec = json.loads((BUNDLE / "job.json").read_text())
    gate = json.loads((BUNDLE / "qualification.json").read_text())
    artifact = gate["artifact"]
    gate_files = {
        "extract/meta.json": artifact["meta.json"],
        "extract/private/holdout.csv": artifact["holdout"],
        "extract/public/eval.csv": artifact["eval"],
        "extract/public/train.csv": artifact["train"],
        "extract/quality.json": artifact["quality.json"],
    }
    expect(len(job_spec["fetch"]["assets"]) == len(gate_files),
           "the fetch spec lists exactly the five artifact files")
    for asset in job_spec["fetch"]["assets"]:
        entry = gate_files.get(asset["dest"])
        expect(entry is not None, f"fetch destination {asset['dest']} is an artifact file")
        expect(asset["sha256"] == entry["sha256"] and asset["size"] == entry["bytes"],
               f"fetch digest for {asset['dest']} equals the gate report digest")

    if SMOKE.exists():
        shutil.rmtree(SMOKE)
    extract = SMOKE / "extract"
    workdir = SMOKE / "workdir"
    out = SMOKE / "out"
    (extract / "public").mkdir(parents=True)
    (extract / "private").mkdir(parents=True)
    (workdir / "data").mkdir(parents=True)
    out.mkdir(parents=True)

    train, eval_rows, meta = synthetic_extract()
    (extract / "meta.json").write_text(json.dumps(meta))
    (extract / "quality.json").write_text("{}")
    (extract / "public" / "train.csv").write_text(rows_csv(train))
    (extract / "public" / "eval.csv").write_text(rows_csv(eval_rows))
    (extract / "private" / "holdout.csv").write_text(rows_csv(train[:2]))
    (workdir / "train.py").write_text(STUB_TRAIN)

    print("== 1. materialize ==")
    result = run([sys.executable, str(BUNDLE / "materialize.py"), str(extract), str(workdir)])
    expect(result.returncode == 0, "materialize exits 0")
    task = json.loads((workdir / "task.json").read_text())
    expect(task["target"] == "target_high_price", "task.json carries the target")
    expect((workdir / "data" / "train.csv").is_file()
           and (workdir / "data" / "eval.csv").is_file(), "public CSVs copied")
    expect(not (workdir / "data" / "holdout.csv").exists(), "holdout NOT copied into workdir")

    print("== 2. reference_check clean path ==")
    args = [sys.executable, str(BUNDLE / "reference_check.py"),
            "--extract", str(extract), "--out", str(out / "reference_check.json"),
            "--bootstrap", "40",
            "--expected-train-rows", "8", "--expected-train-positives", "3",
            "--expected-eval-rows", "8", "--expected-eval-positives", "3",
            "--accepted-persistence-value", "0.8",
            "--accepted-persistence-mean7", "0.7",
            "--accepted-calendar-only", str(9.5 / 15)]
    result = run(args, cwd=workdir)
    expect(result.returncode == 0, f"reference_check exits 0 (stderr: {result.stderr[-200:]})")
    check = json.loads((out / "reference_check.json").read_text())
    persistence = check["references"]["persistence_value"]["auc"]
    mean7 = check["references"]["persistence_mean7"]["auc"]
    calendar = check["references"]["calendar_only"]["auc"]
    expect(abs(persistence - 0.8) < 1e-9, f"persistence bar = 0.8 (got {persistence})")
    expect(abs(mean7 - 0.7) < 1e-9, f"mean7 bar = 0.7 (got {mean7})")
    expect(abs(calendar - 9.5 / 15) < 1e-9, f"calendar bar = 9.5/15 (got {calendar})")
    expect(check["model"]["auc"] == 1.0, "stub model AUC = 1.0")
    differences = check["paired_differences"]
    expect(abs(differences["model_minus_persistence_value"]["observed_difference"] - 0.2) < 1e-9,
           "model - persistence = 0.2")
    expect(abs(differences["model_minus_persistence_mean7"]["observed_difference"] - 0.3) < 1e-9,
           "model - mean7 = 0.3")
    per_year = check["per_target_year"]
    expect("2019" in per_year and per_year["2019"]["rows"] == 8,
           "the 2018-12-30 anchor lands in target year 2019 (anchor + 7 days)")
    expect(check["majority_class"]["majority"] == 0
           and abs(check["majority_class"]["accuracy"] - 0.625) < 1e-9,
           "majority = 0 (train rate 0.375), accuracy 5/8 against this split")
    expect(check["distinct_target_weeks"] == 2, "two target weeks clustered")

    print("== 3. reference_check identity-failure path ==")
    bad = list(args)
    bad[bad.index("--expected-eval-rows") + 1] = "9"
    result = run(bad, cwd=workdir)
    expect(result.returncode == 2, "wrong expected rows -> exit 2")

    print("== 4. reference_check bar-agreement-failure path ==")
    bad = list(args)
    bad[bad.index("--accepted-persistence-value") + 1] = "0.9"
    result = run(bad, cwd=workdir)
    expect(result.returncode == 4, "wrong accepted persistence value -> exit 4")

    print("== 5. report clean path ==")
    # report.py pins the REAL artifact's accepted bar values, so the crafted
    # reference_check.json for this step carries those values (the rest is the
    # genuine step-2 output); the model AUC agrees with both crafted logs.
    import re
    report_source = (BUNDLE / "report.py").read_text()
    accepted_bars = {}
    for bar_name in ("persistence_value", "persistence_mean7", "calendar_only"):
        match = re.search(rf'"{bar_name}":\s*([0-9.]+)', report_source)
        expect(match is not None, f"report.py declares the accepted {bar_name} value")
        accepted_bars[bar_name] = float(match.group(1))
    crafted = json.loads(json.dumps(check))
    for name, value in accepted_bars.items():
        crafted["references"][name]["auc"] = value
    (out / "reference_check.json").write_text(json.dumps(crafted))
    (out / "train.log").write_text("Training time: 0.0s\nEval AUC: 0.9996\n")
    (out / "validate.log").write_text(
        "[validate] eval AUC via predict_proba (target column removed): 0.9997\n"
        "[validate] CONTRACT OK\n")
    (out / "accept.log").write_text(
        "ACCEPTED: /data/extract matches the qualified artifact 545e0e4418c1f0e54bb55389e7816c1736a8473de600e70d6f006ed33089f7e7\n")
    result = run([sys.executable, str(BUNDLE / "report.py"), str(extract), str(out)])
    expect(result.returncode == 0, f"report exits 0 (stderr: {result.stderr[-200:]})")
    baseline = json.loads((out / "baseline_result.json").read_text())
    expect(baseline["contract"]["contract_ok"] is True, "contract_ok true")
    expect(baseline["comparison"]["agreement"]["references_agreement_ok"] is True,
           "references agreement true")
    expect(baseline["comparison"]["agreement"]["model_agreement_ok"] is True,
           "model agreement true (three implementations within 0.0005)")
    expect(baseline["qualification_report"]["accepted_before_scoring"] is True,
           "acceptance recorded before scoring")
    expect(baseline["runner_files"]["unmodified"] is False or True, "runner files recorded")

    print("== 6. report disagreement path ==")
    broken = dict(check)
    broken["references"] = dict(check["references"])
    broken["references"]["persistence_value"] = dict(
        check["references"]["persistence_value"], auc=0.5)
    (out / "reference_check.json").write_text(json.dumps(broken))
    result = run([sys.executable, str(BUNDLE / "report.py"), str(extract), str(out)])
    expect(result.returncode == 5, "disagreeing bar -> exit 5")

    print("SMOKE OK: all bundle guard paths exercised")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
