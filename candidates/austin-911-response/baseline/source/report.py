#!/usr/bin/env python3
"""Compact evidence for one baseline run through the runner's contract.

Records what ran, which artifact it read, which runner files were used (by hash, so "the
existing runner, unmodified" is checkable rather than asserted), the dependency versions, and
the AUC the contract itself printed. Everything here is read from the artifacts of the run -
nothing is computed from memory or restated by hand.

Usage: report.py <extract-dir> <output-dir> <train-exit> <validate-exit> [runner_files.json]
"""
import hashlib
import json
import platform
import re
import sys
from pathlib import Path

RUNNER_FILES = ("train.py", "validate.py", "validate.sh")


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


def main() -> int:
    extract, out = Path(sys.argv[1]), Path(sys.argv[2])
    train_exit, validate_exit = int(sys.argv[3]), int(sys.argv[4])
    runner_json = Path(sys.argv[5]) if len(sys.argv) > 5 else None

    workspace = Path("/workspace")
    job_id = (workspace / "job_id.txt").read_text().strip() if (workspace / "job_id.txt").is_file() else None
    declared = json.loads(runner_json.read_text()) if runner_json and runner_json.is_file() else {}
    actual = {name: sha256_of(workspace / name) for name in RUNNER_FILES if (workspace / name).is_file()}

    train_log = (out / "train.log").read_text() if (out / "train.log").is_file() else ""
    validate_log = (out / "validate.log").read_text() if (out / "validate.log").is_file() else ""
    train_auc = re.findall(r"^Eval AUC:\s*([0-9.]+)", train_log, re.M)
    proba_auc = re.findall(r"eval AUC via predict_proba \(target column removed\):\s*([0-9.]+)",
                           validate_log)
    meta = json.loads((extract / "meta.json").read_text())

    report = {
        "job": job_id,
        "purpose": "one baseline through the runner's existing training and validation contract",
        "contract": {
            "train_py_exit": train_exit,
            "validate_sh_exit": validate_exit,
            "contract_ok": "[validate] CONTRACT OK" in validate_log,
            "eval_auc_from_train_py": train_auc[-1] if train_auc else None,
            "eval_auc_from_validate_py": proba_auc[-1] if proba_auc else None,
        },
        "artifact": {
            "target": meta.get("target"),
            "positive_label": meta.get("positive_label"),
            "threshold_seconds": meta.get("threshold_seconds"),
            "rows": meta.get("rows"),
            "positive_rate": meta.get("positive_rate"),
        },
        "runner_files": {
            "bundled_sha256": actual,
            "expected_sha256": declared,
            "unmodified": bool(declared) and all(declared.get(name) == value
                                                 for name, value in actual.items()),
        },
        "dependencies": versions(),
        "scope": "one baseline only. No agent or harness comparison was run, and none is implied "
                 "- that is outside this publication milestone.",
    }
    (out / "baseline.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())