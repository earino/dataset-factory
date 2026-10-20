#!/usr/bin/env python3
"""Compact evidence for the all-config baseline run through the runner's contract.

Records, for every fetched config: which artifact it read (meta.json facts), the
qualification report it was accepted against (by digest, so the scored bytes are
traceable to the gate), whether the contract completed (train.py exit, validate.sh
exit, the CONTRACT OK line), and the AUCs the contract itself printed - both
train.py's own Eval AUC and validate.py's independent predict_proba recompute, so
agreement is checkable. Nothing here is computed from memory or restated by hand:
every number is read from the run's own logs and files.

Usage: report_all.py <data-root> <output-dir> [runner_files.json]
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
    data, out = Path(sys.argv[1]), Path(sys.argv[2])
    runner_json = Path(sys.argv[3]) if len(sys.argv) > 3 else None

    workspace = Path("/workspace")
    job_id = (workspace / "job_id.txt").read_text().strip() \
        if (workspace / "job_id.txt").is_file() else None
    declared = json.loads(runner_json.read_text()) if runner_json and runner_json.is_file() else {}
    actual = {name: sha256_of(workspace / name) for name in RUNNER_FILES
              if (workspace / name).is_file()}

    configs = {}
    for config_dir in sorted(path for path in data.iterdir() if path.is_dir()):
        name = config_dir.name
        meta = json.loads((config_dir / "meta.json").read_text())
        train_log = (out / f"train-{name}.log").read_text() \
            if (out / f"train-{name}.log").is_file() else ""
        validate_log = (out / f"validate-{name}.log").read_text() \
            if (out / f"validate-{name}.log").is_file() else ""
        accept_log = (out / f"accept-{name}.log").read_text() \
            if (out / f"accept-{name}.log").is_file() else ""
        train_auc = TRAIN_AUC_RE.findall(train_log)
        proba_auc = PROBA_AUC_RE.findall(validate_log)
        accepted = ACCEPT_RE.search(accept_log)
        report_path = workspace / "qualification-reports" / f"qualification-{name}.json"
        configs[name] = {
            "artifact": {key: meta[key] for key in ARTIFACT_KEYS if key in meta},
            "qualification_report": {
                "bundled": f"qualification-reports/qualification-{name}.json",
                "sha256": sha256_of(report_path) if report_path.is_file() else None,
                "accepted_before_scoring": accepted is not None,
                "accepted_artifact_version": accepted.group(1) if accepted else None,
            },
            "contract": {
                "contract_ok": "[validate] CONTRACT OK" in validate_log,
                "eval_auc_from_train_py": float(train_auc[-1]) if train_auc else None,
                "eval_auc_from_validate_py": float(proba_auc[-1]) if proba_auc else None,
            },
        }

    clean = [entry for entry in configs.values() if entry["contract"]["contract_ok"]]
    aucs = sorted(entry["contract"]["eval_auc_from_train_py"] for entry in clean
                  if entry["contract"]["eval_auc_from_train_py"] is not None)
    disagree = [name for name, entry in configs.items()
                if entry["contract"]["eval_auc_from_train_py"] is not None
                and entry["contract"]["eval_auc_from_validate_py"] is not None
                and entry["contract"]["eval_auc_from_train_py"]
                != entry["contract"]["eval_auc_from_validate_py"]]

    report = {
        "job": job_id,
        "purpose": "one baseline through the runner's existing training and validation "
                   "contract, on every one of the 40 per-code configs of the multi-label "
                   "suite, measured in one uniform run",
        "configs": configs,
        "summary": {
            "configs": len(configs),
            "contract_ok": len(clean),
            "accept_ok": sum(1 for entry in configs.values()
                             if entry["qualification_report"]["accepted_before_scoring"]),
            "train_validate_auc_disagreements": disagree,
            "eval_auc_min": aucs[0] if aucs else None,
            "eval_auc_median": aucs[len(aucs) // 2] if aucs else None,
            "eval_auc_max": aucs[-1] if aucs else None,
        },
        "runner_files": {
            "bundled_sha256": actual,
            "expected_sha256": declared,
            "unmodified": bool(declared) and all(declared.get(nm) == value
                                                 for nm, value in actual.items()),
        },
        "dependencies": versions(),
        "scope": "baselines only, through the runner's own contract. No agent or harness "
                 "comparison was run, and none is implied - that is outside this "
                 "publication milestone.",
    }
    (out / "baseline.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))
    print(json.dumps({name: entry["contract"] for name, entry in configs.items()}, indent=1))
    return 0 if len(clean) == len(configs) and not disagree else 5


if __name__ == "__main__":
    raise SystemExit(main())
