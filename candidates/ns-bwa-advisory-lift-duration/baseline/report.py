#!/usr/bin/env python3
"""Compact evidence for the runner-contract baseline of ns-bwa-advisory-lift-duration.

Every number is read from the run's own logs and files; nothing is restated by hand:

  * the artifact actually read (meta.json facts, so the rows scored are identifiable);
  * the qualification report it was accepted against, by digest, and the artifact
    digest the gate's --accept line printed (scored bytes == qualified bytes);
  * whether the contract completed (train.py exit, validate.sh exit, CONTRACT OK);
  * both eval AUCs the contract itself prints - train.py's own `Eval AUC` and
    validate.py's independent predict_proba recompute - so their agreement is checkable;
  * the runner files' bundled vs expected digests, so "the runner, unmodified" is checkable.

This is a baseline scope only: no agent or harness comparison was run, and none is implied.
The holdout is not touched here.

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
                 "split_description")
TRAIN_AUC_RE = re.compile(r"^Eval AUC:\s*([0-9.]+)", re.M)
PROBA_AUC_RE = re.compile(r"eval AUC via predict_proba \(target column removed\):\s*([0-9.]+)")
ACCEPT_RE = re.compile(r"matches the qualified artifact ([0-9a-f]{16,64})")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def versions() -> dict:
    import importlib.metadata as metadata
    found = {"python": platform.python_version()}
    for package in ("pandas", "numpy", "xgboost", "scikit-learn"):
        try:
            found[package] = metadata.version(package)
        except Exception:
            found[package] = None
    return found


def read(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


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

    contract = {
        "contract_ok": "[validate] CONTRACT OK" in validate_log,
        "eval_auc_from_train_py": float(train_auc[-1]) if train_auc else None,
        "eval_auc_from_validate_py": float(proba_auc[-1]) if proba_auc else None,
    }
    gate = json.loads(report_path.read_text()) if report_path.is_file() else {}
    result = {
        "job": job_id,
        "purpose": "one baseline through the runner's existing training and validation "
                   "contract, on the accepted ns-bwa-advisory-lift-duration artifact",
        "artifact": {key: meta[key] for key in ARTIFACT_KEYS if key in meta},
        "qualification_report": {
            "bundled": "qualification.json",
            "sha256": sha256_of(report_path) if report_path.is_file() else None,
            "gate_version": gate.get("gate_version"),
            "gate_ok": gate.get("ok"),
            "gate_failed_checks": gate.get("failed_checks"),
            "accepted_before_scoring": accepted is not None,
            "accepted_artifact_version": accepted.group(1) if accepted else None,
            "qualified_artifact_version": (gate.get("artifact") or {}).get("artifact_version", {}).get("digest"),
        },
        "contract": contract,
        "runner_files": {
            "bundled_sha256": actual,
            "expected_sha256": declared,
            "unmodified": bool(declared) and all(declared.get(nm) == value
                                                 for nm, value in actual.items()),
        },
        "dependencies": versions(),
        "scope": "runner-contract baseline only; no agent loop, no holdout evaluation. "
                 "Holdout stays sealed until the design is frozen.",
    }
    (out / "baseline_result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(contract, indent=2))
    clean = (contract["contract_ok"]
             and contract["eval_auc_from_train_py"] is not None
             and result["qualification_report"]["accepted_before_scoring"])
    return 0 if clean else 5


if __name__ == "__main__":
    raise SystemExit(main())
