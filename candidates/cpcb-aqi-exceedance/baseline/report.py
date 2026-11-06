#!/usr/bin/env python3
"""Runner-contract baseline evidence + the PRE-REGISTERED deciding check for
cpcb-aqi-exceedance.

Part 1 reads the run's own logs and files; nothing is restated by hand: the
accepted artifact version, both eval AUCs the runner contract prints, the
runner files' digests, dependency versions.

Part 2 computes the deciding check the candidate record pre-registered BEFORE
any score existed: headroom is demonstrated ONLY if the full model beats EVERY
triad member (station_persistence, state_season_climatology, global_rate) on
the IDENTICAL eval rows with a station-clustered paired bootstrap 95% CI
excluding zero in the model's favour, AND the model's own cluster-bootstrap AUC
CI lies entirely above 0.5 (the degenerate constant member). Triad definitions
are imported from the bundled score.py - the same code that measured the
construction-time references, never reimplemented here. Triad dominance ->
recorded defect; drop or re-target per the pre-registered rule; no re-tuning of
threshold, window, label or features.

The model's per-row eval scores come from the SAME code path the runner's own
validate.py uses (runpy over train.py, then predict_proba on the eval frame
with the target column removed) - the runner itself is not modified.

Usage: report.py <extract-dir> <output-dir> [runner_files.json]
"""
import hashlib
import json
import os
import platform
import re
import runpy
import sys
from pathlib import Path

sys.path.insert(0, "/workspace")
import score  # noqa: E402  (bundled; the construction-time reference definitions)

RUNNER_FILES = ("train.py", "validate.py", "validate.sh")
ARTIFACT_KEYS = ("name", "target", "positive_label", "id_columns", "rows",
                "positive_rate", "split_description")
TRAIN_AUC_RE = re.compile(r"^Eval AUC:\s*([0-9.]+)", re.M)
PROBA_AUC_RE = re.compile(
    r"eval AUC via predict_proba \(target column removed\):\s*([0-9.]+)")
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
    gate = json.loads((workspace / "qualification.json").read_text()) \
        if (workspace / "qualification.json").is_file() else {}

    contract = {
        "contract_ok": "[validate] CONTRACT OK" in validate_log,
        "eval_auc_from_train_py": float(train_auc[-1]) if train_auc else None,
        "eval_auc_from_validate_py": float(proba_auc[-1]) if proba_auc else None,
    }

    # ---- the pre-registered deciding check -----------------------------------
    deciding = {"status": "not_computed"}
    workdir = Path("/tmp/workdir")
    if contract["contract_ok"] and (workdir / "train.py").is_file():
        import pandas as pd
        train_rows = score.read_rows(extract / "public" / "train.csv")
        eval_rows = score.read_rows(extract / "public" / "eval.csv")
        train_labels = score.labels_of(train_rows)
        eval_labels = score.labels_of(eval_rows)
        train_rate = sum(train_labels) / len(train_labels)

        previous_cwd = os.getcwd()
        os.chdir(workdir)
        try:
            namespace = runpy.run_path("train.py", run_name="__baseline_model__")
            predict = namespace.get("predict_proba")
            frame = pd.read_csv("data/eval.csv")
            model_scores = [float(v) for v in
                            predict(frame.drop(columns=[score.TARGET]))]
        finally:
            os.chdir(previous_cwd)
        model_auc = score.auc(eval_labels, model_scores)

        vectors = score.triad_score_vectors(train_rows, eval_rows, train_rate)
        cluster_keys = [row["station_id"] for row in eval_rows]

        member_results = {}
        for name in score.DECIDING_MEMBERS:
            if name == "global_rate":
                # a constant score carries no ranking information: the
                # comparison is the model's own cluster-bootstrap AUC CI
                # lying entirely above 0.5 (recorded, not silently skipped)
                boot = score.cluster_bootstrap_auc(eval_labels, model_scores,
                                                   cluster_keys)
                member_results[name] = {
                    "member_auc": None,
                    "treatment": ("constant member, no ranking information; "
                                  "beaten iff the model's cluster-bootstrap "
                                  "AUC CI lies entirely above 0.5"),
                    "model_auc_ci": boot,
                    "beaten": (boot.get("auc_ci95_low") is not None
                               and boot["auc_ci95_low"] > 0.5),
                }
            else:
                boot = score.clustered_paired_bootstrap(
                    eval_labels, model_scores, vectors[name], cluster_keys)
                member_results[name] = {
                    "member_auc": score.auc(eval_labels, vectors[name]),
                    "model_minus_member_ci": boot,
                    "beaten": (boot.get("ci95_low") is not None
                               and boot["ci95_low"] > 0.0),
                }
        all_beaten = all(entry["beaten"] for entry in member_results.values())
        deciding = {
            "rule": ("headroom is demonstrated ONLY if the full model beats "
                     "EVERY triad member with a station-clustered paired "
                     "bootstrap 95% CI excluding zero in the model's favour; "
                     "triad dominance -> recorded defect, drop or re-target; no "
                     "re-tuning after any score"),
            "eval_rows": len(eval_rows),
            "eval_distinct_positive_days": len(
                {row["date"] for row, label in zip(eval_rows, eval_labels)
                 if label == 1}),
            "model_eval_auc": model_auc,
            "model_eval_auc_recomputed_by_validate": contract["eval_auc_from_validate_py"],
            "agreement": (model_auc is not None
                          and contract["eval_auc_from_validate_py"] is not None
                          and abs(model_auc - contract["eval_auc_from_validate_py"]) < 1e-9),
            "members": member_results,
            "verdict": "headroom_demonstrated" if all_beaten else "triad_not_beaten",
            "scope": ("eval split only (2023 station-days); prevalence and the "
                      "seasonal structure are reported beside the number; the "
                      "sealed holdout (2024) was not evaluated and no holdout "
                      "figure exists or is implied"),
        }

    result = {
        "job": job_id,
        "purpose": ("one baseline through the runner's existing training and "
                    "validation contract on the accepted cpcb-aqi-exceedance "
                    "artifact, plus the pre-registered model-vs-triad deciding "
                    "check on identical eval rows"),
        "artifact": {key: meta[key] for key in ARTIFACT_KEYS if key in meta},
        "qualification_report": {
            "bundled": "qualification.json",
            "sha256": sha256_of(workspace / "qualification.json")
            if (workspace / "qualification.json").is_file() else None,
            "gate_version": gate.get("gate_version"),
            "gate_ok": gate.get("ok"),
            "gate_failed_checks": gate.get("failed_checks"),
            "accepted_before_scoring": accepted is not None,
            "accepted_artifact_version": accepted.group(1) if accepted else None,
            "qualified_artifact_version": (gate.get("artifact") or {}).get(
                "artifact_version", {}).get("digest"),
        },
        "contract": contract,
        "deciding_check": deciding,
        "runner_files": {
            "bundled_sha256": actual,
            "expected_sha256": declared,
            "unmodified": bool(declared) and all(declared.get(nm) == value
                                                 for nm, value in actual.items()),
        },
        "dependencies": versions(),
        "scope": ("runner-contract baseline + deciding check only; no agent "
                  "loop, no holdout evaluation. Holdout stays sealed until the "
                  "design is frozen."),
    }
    (out / "baseline_result.json").write_text(json.dumps(result, indent=2) + "\n")
    raw_members = deciding.get("members")
    members = raw_members if isinstance(raw_members, dict) else {}
    print(json.dumps({"contract": contract,
                      "deciding": {"model_eval_auc": deciding.get("model_eval_auc"),
                                   "verdict": deciding.get("verdict"),
                                   "members": {k: {"member_auc": v.get("member_auc"),
                                                   "beaten": v.get("beaten"),
                                                   "ci": v.get("model_minus_member_ci")
                                                   or v.get("model_auc_ci")}
                                               for k, v in members.items()}}},
                     indent=2))
    clean = (contract["contract_ok"]
             and contract["eval_auc_from_train_py"] is not None
             and result["qualification_report"]["accepted_before_scoring"]
             and deciding.get("verdict") in ("headroom_demonstrated",
                                             "triad_not_beaten"))
    return 0 if clean else 5


if __name__ == "__main__":
    raise SystemExit(main())
