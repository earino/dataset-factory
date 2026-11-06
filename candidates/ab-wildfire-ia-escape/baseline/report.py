#!/usr/bin/env python3
"""Runner-contract baseline evidence + the PRE-REGISTERED deciding check for
ab-wildfire-ia-escape.

Part 1 reads the run's own logs and files; nothing is restated by hand: the
accepted artifact version, both eval AUCs the runner contract prints, the
runner files' digests, dependency versions.

Part 2 computes the deciding check the candidate record pre-registered BEFORE
any score existed: headroom is demonstrated ONLY if the runner-contract model
beats EVERY non-degenerate triad member (persistence_assessment_hectares,
calendar_identity_only) on the IDENTICAL eval rows with a day-clustered paired
bootstrap 95% CI excluding zero in the model's favour, AND the model's own
cluster-bootstrap AUC CI lies entirely above 0.5 (the degenerate majority
constant member). Triad dominance -> recorded defect; drop or re-target per the
pre-registered rule; no re-tuning of threshold, window, label or features.

Triad definitions are imported from the bundled score.py - the same code that
measured the construction-time references, never reimplemented here. The
construction-time full-feature logistic reference is recorded as a
SUPPLEMENTARY comparison (both are models; the pre-registered rule compares
the model against baselines, not against another model).

The model's per-row eval scores come from the SAME code path the runner's own
validate.py uses (runpy over train.py, then predict_proba on the eval frame
with the target column removed) - the runner itself is not modified.

Day-cluster bootstrap: cluster = assessment_date (score.CLUSTER_COLUMN), the
declared independence scale (the extreme fire-weather day). The paired
intervals reuse score.bootstrap_diff's fixed-seed LCG so they are reproducible;
the single-vector AUC CI mirrors that same deterministic pattern.

Usage: report.py <extract-dir> <output-dir> [runner_files.json]
"""
import hashlib
import json
import os
import platform
import re
import runpy
import sys
from collections import defaultdict
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
DECIDING_MEMBERS = ("persistence_assessment_hectares", "calendar_identity_only")
BOOTSTRAP_RESAMPLES = 500


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


def cluster_bootstrap_auc(labels, scores, clusters, resamples=BOOTSTRAP_RESAMPLES):
    """Day-cluster bootstrap of a single score vector's AUC.

    Mirrors score.bootstrap_diff's fixed-seed LCG (seed 12345) so the interval
    is deterministic and reproducible from the artifact alone.
    """
    by_cluster = defaultdict(list)
    for label, value, cluster in zip(labels, scores, clusters):
        by_cluster[cluster].append((label, value))
    keys = sorted(by_cluster)
    aucs = []
    seed = 12345
    for _ in range(resamples):
        seed = (seed * 1103515245 + 12345) % (2 ** 31)
        sampled = []
        for _ in range(len(keys)):
            seed = (seed * 1103515245 + 12345) % (2 ** 31)
            sampled.extend(by_cluster[keys[seed % len(keys)]])
        value = score.auc([r[0] for r in sampled], [r[1] for r in sampled])
        if value is not None:
            aucs.append(value)
    if not aucs:
        return None
    aucs.sort()
    return {"resamples": len(aucs),
            "auc_ci95_low": round(aucs[min(int(0.025 * len(aucs)), len(aucs) - 1)], 4),
            "auc_ci95_high": round(aucs[min(int(0.975 * len(aucs)), len(aucs) - 1)], 4)}


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
        train_labels = [int(r[score.TARGET] == "1") for r in train_rows]
        eval_labels = [int(r[score.TARGET] == "1") for r in eval_rows]

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

        # triad vectors, from the same bundled score.py definitions
        persistence_scores = [score.fnum_or_none(r["assessment_hectares"])
                              for r in eval_rows]
        calendar_scorer = score.fit_calendar(train_rows)
        calendar_scores = [calendar_scorer(r) for r in eval_rows]
        vectors = {"persistence_assessment_hectares": persistence_scores,
                   "calendar_identity_only": calendar_scores}
        cluster_keys = [r[score.CLUSTER_COLUMN] for r in eval_rows]

        member_results = {}
        for name in DECIDING_MEMBERS:
            boot = score.bootstrap_diff(eval_labels, model_scores, vectors[name],
                                         cluster_keys)
            member_results[name] = {
                "member_auc": score.auc(eval_labels, vectors[name]),
                "model_minus_member_ci": boot,
                "beaten": (boot is not None and boot.get("ci_low") is not None
                           and boot["ci_low"] > 0.0),
            }
        # the degenerate majority constant: a constant score carries no ranking
        # information; the comparison is the model's own cluster-bootstrap AUC
        # CI lying entirely above 0.5 (recorded, not silently skipped)
        boot_auc = cluster_bootstrap_auc(eval_labels, model_scores, cluster_keys)
        member_results["majority_constant"] = {
            "member_auc": 0.5,
            "treatment": ("constant member, no ranking information; beaten iff "
                          "the model's day-cluster-bootstrap AUC CI lies "
                          "entirely above 0.5"),
            "model_auc_ci": boot_auc,
            "beaten": (boot_auc is not None and boot_auc["auc_ci95_low"] > 0.5),
        }
        all_beaten = all(entry["beaten"] for entry in member_results.values())

        # supplementary: the runner model vs the construction-time simple
        # logistic reference (both are models; NOT a deciding member)
        refs = json.loads((out / "references-ab-wildfire-ia-escape.json").read_text())
        logistic_auc = refs["references"]["full_feature_logistic"]["auc"]
        supplementary = {
            "construction_full_feature_logistic_auc": logistic_auc,
            "model_minus_logistic_observed": (round(model_auc - logistic_auc, 4)
                                              if model_auc is not None else None),
            "note": ("supplementary only: both are models, so this is not a "
                     "deciding member; the pre-registered rule compares the "
                     "model against the baselines above"),
        }

        deciding = {
            "rule": ("headroom is demonstrated ONLY if the runner-contract "
                     "model beats EVERY triad member (persistence analogue = "
                     "assessment_hectares, calendar/identity prior) with a "
                     "day-clustered paired bootstrap 95% CI excluding zero in "
                     "the model's favour, and its own AUC CI lies entirely "
                     "above 0.5 for the degenerate constant member; triad "
                     "dominance -> recorded defect, drop or re-target; no "
                     "re-tuning after any score"),
            "eval_rows": len(eval_rows),
            "eval_distinct_positive_days": len(
                {row[score.CLUSTER_COLUMN] for row, label in zip(eval_rows, eval_labels)
                 if label == 1}),
            "model_eval_auc": model_auc,
            "model_eval_auc_recomputed_by_validate": contract["eval_auc_from_validate_py"],
            "agreement": (model_auc is not None
                          and contract["eval_auc_from_validate_py"] is not None
                          and abs(model_auc - contract["eval_auc_from_validate_py"]) < 1e-9),
            "members": member_results,
            "supplementary_model_vs_logistic_reference": supplementary,
            "verdict": "headroom_demonstrated" if all_beaten else "triad_not_beaten",
            "scope": ("eval split only (assessment years 2016-2020); the sealed "
                      "holdout (2021-2025) was not evaluated and no holdout "
                      "figure exists or is implied"),
        }

    result = {
        "job": job_id,
        "purpose": ("one baseline through the runner's existing training and "
                    "validation contract on the accepted ab-wildfire-ia-escape "
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
