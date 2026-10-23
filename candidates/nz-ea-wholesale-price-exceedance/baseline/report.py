#!/usr/bin/env python3
"""Compact evidence for the runner-contract baseline of the NZ Electricity Authority
wholesale-price-exceedance task.

Records which artifact was read (meta.json facts), the qualification report it was
accepted against (by digest, so the scored bytes are traceable to the gate), whether
the contract completed (train.py exit, validate.sh exit, the CONTRACT OK line), the
AUCs the contract itself printed (train.py's own Eval AUC and validate.py's
independent predict_proba recompute), and the independent comparison from
reference_check.py: the three recomputed references (persistence_value,
persistence_mean7, calendar_only), the model AUC, the paired differences with their
target_week-clustered bootstrap intervals, the per-target-year breakdown and the
majority-class accuracy - on the identical 4,992 eval rows.

The measured prevalence shift across splits is recorded in the same report as any
score (read from the gate's own accepted evidence, not recomputed from holdout
rows), so no reader can quote the eval AUC without the population shift it sits in.
Nothing here is computed from memory or restated by hand: every number is read from
the run's own logs and files.

The comparison verdict is NOT decided here - the job reports measured numbers and
agreement flags; the headroom decision is recorded by the coordinator session
against the pre-declared criterion in job.json.

Usage: report.py <extract-dir> <output-dir> [runner_files.json]
"""
import hashlib
import json
import platform
import re
import sys
from pathlib import Path

RUNNER_FILES = ("train.py", "validate.py", "validate.sh")
ARTIFACT_KEYS = ("name", "target", "positive_label", "id_columns", "rows", "positive_rate",
                 "label_rule")
TRAIN_AUC_RE = re.compile(r"^Eval AUC:\s*([0-9.]+)", re.M)
PROBA_AUC_RE = re.compile(r"eval AUC via predict_proba \(target column removed\):\s*([0-9.]+)")
ACCEPT_RE = re.compile(r"matches the qualified artifact ([0-9a-f]{16,64})")
MODEL_TOLERANCE = 0.0005  # 4-decimal rounding agreement between implementations
ACCEPTED_BARS = {
    "persistence_value": 0.8820357429258793,
    "persistence_mean7": 0.884293406215734,
    "calendar_only": 0.5010555946516537,
}
CRITERION = ("model eval AUC vs the stronger persistence reference (persistence_mean7) "
             "on the identical eval rows; headroom is demonstrated only if the model "
             "exceeds persistence_mean7 AND the week-clustered paired interval for "
             "(model - persistence_mean7) excludes zero (decided by the coordinator "
             "session, not by this job)")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def versions() -> dict:
    import importlib.metadata as metadata
    found: dict = {"python": platform.python_version()}
    for package in ("pandas", "numpy", "xgboost", "scikit-learn"):
        try:
            found[package] = metadata.version(package)
        except Exception:
            found[package] = None
    return found


def read(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def gate_split_rates(qualification: dict) -> dict:
    """Per-split positive rates exactly as the accepted gate report recorded them."""
    rates = {}
    for item in qualification.get("results", []):
        if isinstance(item, dict) and item.get("check") == "splits.non_empty":
            for split, evidence in (item.get("evidence") or {}).items():
                if isinstance(evidence, dict) and "positive_rate" in evidence:
                    rates[split] = evidence["positive_rate"]
    return rates


def main() -> int:
    extract, out = Path(sys.argv[1]), Path(sys.argv[2])
    runner_json = Path(sys.argv[3]) if len(sys.argv) > 3 else None

    workspace = Path("/workspace")
    job_id = (workspace / "job_id.txt").read_text().strip() \
        if (workspace / "job_id.txt").is_file() else None
    declared = json.loads(runner_json.read_text()) if runner_json and runner_json.is_file() else {}
    actual = {name: sha256_of(workspace / name) for name in RUNNER_FILES
              if (workspace / name).is_file()}

    meta = json.loads((extract / "meta.json").read_text())
    train_log = read(out / "train.log")
    validate_log = read(out / "validate.log")
    accept_log = read(out / "accept.log")
    train_auc = TRAIN_AUC_RE.findall(train_log)
    proba_auc = PROBA_AUC_RE.findall(validate_log)
    accepted = ACCEPT_RE.search(accept_log)
    report_path = workspace / "qualification.json"
    qualification = json.loads(report_path.read_text()) if report_path.is_file() else {}

    check_path = out / "reference_check.json"
    reference_check = json.loads(check_path.read_text()) if check_path.is_file() else None

    contract = {
        "contract_ok": "[validate] CONTRACT OK" in validate_log,
        "eval_auc_from_train_py": float(train_auc[-1]) if train_auc else None,
        "eval_auc_from_validate_py": float(proba_auc[-1]) if proba_auc else None,
    }
    contract: dict

    # Agreement between every implementation that measured the decisive numbers.
    agreement: dict = {"references_agreement_ok": None, "model_agreement_ok": None}
    decisive: dict = {}
    if reference_check is not None:
        recomputed = reference_check.get("references") or {}

        def bar_agrees(name: str, value: float) -> bool:
            bar_auc = (recomputed.get(name) or {}).get("auc")
            return bar_auc is not None and abs(bar_auc - value) <= 1e-6

        agreement["references_agreement_ok"] = all(
            bar_agrees(name, value) for name, value in ACCEPTED_BARS.items())
        printed = [value for value in
                   (contract["eval_auc_from_train_py"], contract["eval_auc_from_validate_py"],
                    (reference_check.get("model") or {}).get("auc")) if value is not None]
        agreement["model_agreement_ok"] = (
            len(printed) == 3 and max(printed) - min(printed) <= MODEL_TOLERANCE)
        paired_differences = reference_check.get("paired_differences") or {}
        mean7_difference = paired_differences.get("model_minus_persistence_mean7") or {}
        decisive = {
            "model_auc": (reference_check.get("model") or {}).get("auc"),
            "persistence_value_auc": (recomputed.get("persistence_value") or {}).get("auc"),
            "persistence_mean7_auc": (recomputed.get("persistence_mean7") or {}).get("auc"),
            "calendar_only_auc": (recomputed.get("calendar_only") or {}).get("auc"),
            "model_minus_persistence_mean7": mean7_difference.get("observed_difference"),
            "week_clustered_ci95": [mean7_difference.get("week_clustered_bootstrap", {})
                                    .get("ci_low"),
                                    mean7_difference.get("week_clustered_bootstrap", {})
                                    .get("ci_high")],
            "per_target_year": reference_check.get("per_target_year"),
            "majority_class": reference_check.get("majority_class"),
        }

    result = {
        "job": job_id,
        "purpose": "one baseline through the runner's existing training and validation "
                   "contract, on the accepted nz-ea-wholesale-price-exceedance artifact "
                   "545e0e4418c1f0e54bb55389e7816c1736a8473de600e70d6f006ed33089f7e7, "
                   "compared with the accepted references on identical eval rows",
        "artifact": {key: meta[key] for key in ARTIFACT_KEYS if key in meta},
        "qualification_report": {
            "bundled": "qualification.json",
            "sha256": sha256_of(report_path) if report_path.is_file() else None,
            "accepted_before_scoring": accepted is not None,
            "accepted_artifact_version": accepted.group(1) if accepted else None,
            "gate_version": qualification.get("gate_version"),
        },
        "contract": contract,
        "comparison": {
            "accepted_references": ACCEPTED_BARS,
            "criterion": CRITERION,
            "reference_check": reference_check,
            "decisive": decisive,
            "agreement": agreement,
        },
        "prevalence_shift": {
            "gate_recorded_positive_rates": gate_split_rates(qualification),
            "note": "train ~0.199 vs eval ~0.431 vs holdout ~0.544 as recorded by the "
                    "accepted gate report: the eval window is prevalence-shifted "
                    "relative to training and the holdout sits in the post-2022-11 "
                    "real-time pricing regime; any score is out-of-distribution as "
                    "much as temporal, and per-target-year reporting is mandatory",
        },
        "runner_files": {
            "bundled_sha256": actual,
            "expected_sha256": declared,
            "unmodified": bool(declared) and all(declared.get(nm) == value
                                                 for nm, value in actual.items()),
        },
        "dependencies": versions(),
        "scope": "baseline only, through the runner's own contract. No agent or harness "
                 "comparison was run, and none is implied. The private holdout was "
                 "fetched for gate re-acceptance only and never copied into the workdir "
                 "or scored; its positive rate is quoted from the accepted gate report, "
                 "not recomputed here.",
    }
    (out / "baseline_result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"contract": contract, "agreement": agreement,
                      "decisive": decisive}, indent=2))

    clean = (contract["contract_ok"]
             and contract["eval_auc_from_train_py"] is not None
             and reference_check is not None
             and agreement["references_agreement_ok"]
             and agreement["model_agreement_ok"])
    if not clean:
        print("the comparison basis did not verify end to end; the numbers above are "
              "recorded but the job exits nonzero", file=sys.stderr)
    return 0 if clean else 5


if __name__ == "__main__":
    raise SystemExit(main())
