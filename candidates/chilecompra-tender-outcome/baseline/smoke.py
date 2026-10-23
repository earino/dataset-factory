#!/usr/bin/env python3
"""Local smoke for the cl-tender-baseline-001 bundle, before any worker spend.

Builds a synthetic extract (same layout/columns as the real artifact) and a stub
train.py that exposes the runner contract, then exercises the bundle's own scripts
end to end in pure stdlib:

  1. materialize.py: task.json written from meta.json TASK_KEYS, public CSVs copied,
     private holdout NOT copied;
  2. reference_check.py clean path: identity holds, the bar AUC equals its
     hand-computed value (52/84), the stub model AUC is 1.0, both bootstrap
     intervals produced;
  3. reference_check.py identity-failure path: wrong expected rows -> exit 2
     (the guard is shown to bite);
  4. report.py clean path: logs + a crafted reference_check.json with bar 0.5707 and
     agreeing model AUCs -> exit 0;
  5. report.py disagreement path: bar 0.5 -> exit 5 (a broken comparison basis is
     loud, not silent).

Exit 0 only if every step's expectation is observed.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
BUNDLE = ROOT / "candidates/chilecompra-tender-outcome/baseline"
SMOKE = Path("/opt/data/cache/scratch/cl-baseline-smoke")

COLUMNS = ["tender_id", "deserted", "pub_date", "buyer_region", "unspsc_segment",
           "procedure_code", "estimated_value_clp"]


def rows_csv(rows):
    lines = [",".join(COLUMNS)]
    for row in rows:
        lines.append(",".join(str(row[c]) for c in COLUMNS))
    return "\n".join(lines) + "\n"


def synthetic_extract():
    train = []
    # segment A: 10 rows, 5 positives -> rate 0.5 ; segment B: 30 rows, 3 positives -> 0.1
    for index in range(10):
        train.append(dict(tender_id=f"t{index}", deserted=1 if index < 5 else 0,
                          pub_date=f"2019-05-{(index % 28) + 1:02d}", buyer_region="RM",
                          unspsc_segment="A", procedure_code="P1", estimated_value_clp=100))
    for index in range(30):
        train.append(dict(tender_id=f"u{index}", deserted=1 if index < 3 else 0,
                          pub_date=f"2019-06-{(index % 28) + 1:02d}", buyer_region="VL",
                          unspsc_segment="B", procedure_code="P2", estimated_value_clp=200))
    ev = []
    # 10 segment-A rows: 4 positive, 6 negative ; 10 segment-B rows: 2 positive, 8 negative
    for index in range(10):
        ev.append(dict(tender_id=f"e{index}", deserted=1 if index < 4 else 0,
                       pub_date=f"2020-05-{(index % 28) + 1:02d}", buyer_region="RM",
                       unspsc_segment="A", procedure_code="P1", estimated_value_clp=100))
    for index in range(10):
        ev.append(dict(tender_id=f"f{index}", deserted=1 if index < 2 else 0,
                       pub_date=f"2020-06-{(index % 28) + 1:02d}", buyer_region="VL",
                       unspsc_segment="B", procedure_code="P2", estimated_value_clp=200))
    extract = SMOKE / "extract"
    (extract / "public").mkdir(parents=True, exist_ok=True)
    (extract / "private").mkdir(parents=True, exist_ok=True)
    (extract / "public/train.csv").write_text(rows_csv(train))
    (extract / "public/eval.csv").write_text(rows_csv(ev))
    (extract / "private/holdout.csv").write_text(rows_csv(ev))
    meta = {"name": "chilecompra-smoke", "description": "synthetic",
            "target": "deserted", "positive_label": 1, "id_columns": ["tender_id"],
            "split": "temporal", "columns": COLUMNS,
            "rows": {"train": len(train), "eval": len(ev), "holdout": len(ev)},
            "positive_rate": {"train": 0.2}, "label_rule": "smoke"}
    (extract / "meta.json").write_text(json.dumps(meta) + "\n")
    quality = {"outcome_conditioning": {"eval": {"scored_rows": 20, "censored_rate": 0.05,
                                                 "revoked_rate": 0.04}}}
    (extract / "quality.json").write_text(json.dumps(quality) + "\n")
    return extract, len(train), len(ev), sum(int(r["deserted"]) for r in ev)


STUB_TRAIN = '''
import csv
evald = list(csv.DictReader(open("data/eval.csv")))
def to_y(df):
    return [int(row["deserted"] == "1") for row in df]
def predict_proba(df):
    return [0.9 if row["deserted"] == "1" else 0.1 for row in df]
'''


def run(command, cwd=None):
    return subprocess.run(command, capture_output=True, text=True, cwd=cwd)


def main() -> int:
    if SMOKE.exists():
        shutil.rmtree(SMOKE)
    failures = []

    extract, n_train, n_eval, n_pos = synthetic_extract()
    workdir = SMOKE / "workdir"
    workdir.mkdir(parents=True)
    (workdir / "train.py").write_text(STUB_TRAIN)

    # 1. materialize
    result = run([sys.executable, str(BUNDLE / "materialize.py"), str(extract), str(workdir)])
    ok = result.returncode == 0
    ok = ok and (workdir / "task.json").is_file() and (workdir / "data/train.csv").is_file() \
        and (workdir / "data/eval.csv").is_file() and not (workdir / "data/holdout.csv").exists()
    task = json.loads((workdir / "task.json").read_text())
    ok = ok and task["target"] == "deserted" and task["id_columns"] == ["tender_id"]
    print(f"1. materialize.py: {'PASS' if ok else 'FAIL'}")
    if not ok:
        print(result.stdout, result.stderr)
        failures.append("materialize")

    # 2. reference_check clean path (expected bar AUC = 52/84 = 0.619047..., model AUC = 1)
    check_out = SMOKE / "reference_check.json"
    result = run([sys.executable, str(BUNDLE / "reference_check.py"),
                  "--extract", str(extract), "--out", str(check_out), "--bootstrap", "60",
                  "--expected-train-rows", str(n_train),
                  "--expected-eval-rows", str(n_eval),
                  "--expected-eval-positives", str(n_pos)], cwd=workdir)
    check = json.loads(check_out.read_text()) if check_out.is_file() else {}
    bar_auc = (check.get("bar") or {}).get("auc")
    model_auc = (check.get("model") or {}).get("auc")
    clustered = check.get("paired_difference", {}).get("day_clustered_bootstrap", {})
    expected_bar = 52 / 84
    ok = (result.returncode == 0 and bar_auc is not None and abs(bar_auc - expected_bar) < 1e-9
          and model_auc == 1.0 and clustered.get("ci_low") is not None
          and check.get("identity", {}).get("ok") is True
          and check.get("outcome_conditioning") is not None)
    print(f"2. reference_check clean: {'PASS' if ok else 'FAIL'} "
          f"(bar={bar_auc} expected={expected_bar:.6f} model={model_auc} "
          f"ci=[{clustered.get('ci_low')}, {clustered.get('ci_high')}])")
    if not ok:
        print(result.stdout, result.stderr)
        failures.append("reference_check-clean")

    # 3. reference_check identity-failure path: wrong expected rows -> exit 2
    result = run([sys.executable, str(BUNDLE / "reference_check.py"),
                  "--extract", str(extract), "--out", str(SMOKE / "bad.json"),
                  "--expected-train-rows", "999"], cwd=workdir)
    ok = result.returncode == 2
    print(f"3. reference_check identity guard bites (exit 2): {'PASS' if ok else 'FAIL'}")
    if not ok:
        print(result.returncode, result.stdout[-500:], result.stderr[-500:])
        failures.append("reference_check-guard")

    # 4/5. report.py clean + disagreement paths
    logs = SMOKE / "logs"
    logs.mkdir()
    (logs / "train.log").write_text("Eval AUC: 0.6123\n")
    (logs / "validate.log").write_text(
        "[validate] eval AUC via predict_proba (target column removed): 0.6123\n"
        "[validate] CONTRACT OK\n")
    (logs / "accept.log").write_text(
        "ACCEPTED: /data/extract matches the qualified artifact 27e610ba65e13805c8\n")

    def craft_check(bar_value, model_value):
        template = json.loads(check_out.read_text())
        template["bar"]["auc"] = bar_value
        template["model"]["auc"] = model_value
        (logs / "reference_check.json").write_text(json.dumps(template) + "\n")

    craft_check(0.5707, 0.6123)
    result = run([sys.executable, str(BUNDLE / "report.py"), str(extract), str(logs)])
    clean_report = logs / "baseline_result.json"
    payload = json.loads(clean_report.read_text()) if clean_report.is_file() else {}
    ok = (result.returncode == 0
          and payload.get("contract", {}).get("eval_auc_from_train_py") == 0.6123
          and payload.get("comparison", {}).get("agreement", {}).get("bar_agreement_ok") is True
          and payload.get("outcome_conditioning") is not None
          and payload.get("qualification_report", {}).get("accepted_artifact_version",
                                                          "").startswith("27e610ba"))
    print(f"4. report.py clean path (exit 0, evidence recorded): {'PASS' if ok else 'FAIL'}")
    if not ok:
        print(result.stdout, result.stderr)
        failures.append("report-clean")

    craft_check(0.5000, 0.6123)
    result = run([sys.executable, str(BUNDLE / "report.py"), str(extract), str(logs)])
    ok = result.returncode == 5
    print(f"5. report.py disagreement path (bar != accepted 0.5707 -> exit 5): "
          f"{'PASS' if ok else 'FAIL'}")
    if not ok:
        print(result.returncode, result.stdout, result.stderr)
        failures.append("report-disagreement")

    if failures:
        print("SMOKE FAILED:", failures)
        return 1
    print("SMOKE OK - all five steps behaved as designed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
