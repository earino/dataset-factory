#!/usr/bin/env python3
"""Per-row diagnostic for the accepted ns-bwa-advisory-lift-duration artifact.

The runner contract (train.py/validate.py) prints only the aggregate eval AUC, so
job ns-bwa-baseline-001 could not put an interval around model-vs-persistence.
This job preserves the per-row model scores and computes, on the SAME eval rows:

  * the model's per-row predict_proba (validate.py's exact call: the target
    column is removed before the call), and its AUC/Brier;
  * the persistence and calendar references recomputed from the shipped
    artifact bytes by a second implementation (this file reads the CSVs with
    pandas and re-derives the scores from the recorded definitions, not by
    running score.py) - a replication check against job ns-bwa-001's figures;
  * paired row-level bootstrap intervals, model vs persistence and model vs
    calendar (1000 resamples, seed 23, the same resampler the construction
    references used, so the intervals are mutually comparable);
  * a site-clustered paired bootstrap for model vs persistence, because rows
    cluster by site (2.4x repeat advisories per site; 286 distinct sites over
    372 eval rows) and the persistence feature is a site-level statistic;
  * per-issue-year model AUC/Brier beside persistence, against the measured
    2018-2020 prevalence shift (0.744 -> 0.415).

Nothing is re-tuned: the label, threshold, splits and the runner template's own
model configuration are frozen. The holdout is never read. No number is computed
before run.sh has re-accepted the fetched bytes against the gate's report.

Usage: diag.py <extract-dir> <workdir> <output-dir> [runner_files.json]
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import random
import re
import runpy
import sys
from collections import defaultdict
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd
from sklearn.metrics import roc_auc_score

BOOTSTRAP = 1000
SEED = 23
TARGET = "lift30"
POSITIVE = 1
# Figures recorded by earlier jobs on this same artifact (record.json):
# ns-bwa-001 (construction references, post-acceptance) and
# ns-bwa-baseline-001 (runner-contract baseline). Carried here as labelled
# constants so the replication checks are explicit, never silently assumed.
RECORDED = {
    "persistence_site_prior_auc": {"value": 0.6124, "job": "ns-bwa-001"},
    "calendar_county_month_auc": {"value": 0.5075, "job": "ns-bwa-001"},
    "reason_prior_auc": {"value": 0.4307, "job": "ns-bwa-001"},
    "majority_class_accuracy": {"value": 0.6048, "job": "ns-bwa-001"},
    "full_model_eval_auc": {"value": 0.5086, "job": "ns-bwa-baseline-001"},
    "persistence_per_year_auc": {"2018": 0.6084, "2019": 0.6203, "2020": 0.5991},
}


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


def auc(labels: list[int], scores: list[float]) -> float | None:
    """Tie-aware AUC, the same construction score.py uses (midrank form)."""
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        return None
    if len(set(scores)) == 1:
        return None  # constant scores carry no ranking information
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    ranks = [0.0] * len(order)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        average = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = average
        i = j + 1
    rank_sum = sum(ranks[k] for k in range(len(labels)) if labels[k])
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def brier(labels: list[int], probabilities: list[float]) -> float | None:
    if not labels:
        return None
    return sum((p - y) ** 2 for y, p in zip(labels, probabilities)) / len(labels)


def paired_row_bootstrap(labels, scores_a, scores_b) -> dict:
    """Paired bootstrap of AUC(A)-AUC(B); identical resampler to score.py."""
    rng = random.Random(SEED)
    differences = []
    for _ in range(BOOTSTRAP):
        sample = [rng.randrange(len(labels)) for _ in range(len(labels))]
        boot_labels = [labels[i] for i in sample]
        auc_a = auc(boot_labels, [scores_a[i] for i in sample])
        auc_b = auc(boot_labels, [scores_b[i] for i in sample])
        if auc_a is not None and auc_b is not None:
            differences.append(auc_a - auc_b)
    if not differences:
        return {"note": "degenerate resamples (a split lost one class)"}
    differences.sort()
    return {
        "unit": "row",
        "resamples": len(differences),
        "mean": round(sum(differences) / len(differences), 6),
        "ci95_low": round(differences[int(0.025 * len(differences))], 6),
        "ci95_high": round(differences[int(0.975 * len(differences))], 6),
        "note": "paired bootstrap on identical rows; an interval containing "
                "zero is inconclusive, not parity",
    }


def paired_cluster_bootstrap(labels, scores_a, scores_b, cluster_keys) -> dict:
    """Paired bootstrap resampling SITE CLUSTERS (dependence-aware).

    Advisories repeat within a site and the persistence reference is itself a
    site-level statistic, so i.i.d. row resampling understates the variance of
    any site-level comparison. Each resample draws len(clusters) sites with
    replacement and takes every row of each drawn site, keeping the pairing.
    """
    clusters = defaultdict(list)
    for index, key in enumerate(cluster_keys):
        clusters[key].append(index)
    names = sorted(clusters)
    rng = random.Random(SEED)
    differences = []
    for _ in range(BOOTSTRAP):
        picked = [names[rng.randrange(len(names))] for _ in range(len(names))]
        rows = [i for name in picked for i in clusters[name]]
        boot_labels = [labels[i] for i in rows]
        auc_a = auc(boot_labels, [scores_a[i] for i in rows])
        auc_b = auc(boot_labels, [scores_b[i] for i in rows])
        if auc_a is not None and auc_b is not None:
            differences.append(auc_a - auc_b)
    if not differences:
        return {"note": "degenerate resamples (a split lost one class)"}
    differences.sort()
    return {
        "unit": "site_cluster",
        "clusters": len(names),
        "resamples": len(differences),
        "mean": round(sum(differences) / len(differences), 6),
        "ci95_low": round(differences[int(0.025 * len(differences))], 6),
        "ci95_high": round(differences[int(0.975 * len(differences))], 6),
        "note": "paired site-cluster bootstrap (rows of a resampled site stay "
                "together); an interval containing zero is inconclusive, "
                "not parity",
    }


def agrees(recomputed, recorded) -> bool:
    return recomputed is not None and abs(recomputed - recorded) < 5e-5


def main() -> int:
    extract, workdir, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    runner_json = Path(sys.argv[4]) if len(sys.argv) > 4 else None

    task = json.loads((workdir / "task.json").read_text())
    if task["target"] != TARGET or task["positive_label"] != POSITIVE:
        print("unexpected task contract", file=sys.stderr)
        return 1
    train = pd.read_csv(workdir / "data" / "train.csv")
    evald = pd.read_csv(workdir / "data" / "eval.csv")
    train_y = (train[TARGET] == POSITIVE).astype(int)
    eval_y = (evald[TARGET] == POSITIVE).astype(int).tolist()
    train_rate = float(train_y.mean())

    # ---- the model, fit by the benchmark's own train.py (verbatim) --------
    os.chdir(workdir)
    captured = io.StringIO()
    with redirect_stdout(captured):
        ns = runpy.run_path("train.py", run_name="__train__")
    train_print = captured.getvalue()
    printed = re.findall(r"Eval AUC:\s*([0-9.]+)", train_print)
    predict_proba = ns.get("predict_proba")
    if not callable(predict_proba):
        print("train.py defined no callable predict_proba", file=sys.stderr)
        return 2
    model_scores = [float(v) for v in predict_proba(evald.drop(columns=[TARGET]))]
    if len(model_scores) != len(evald):
        print("predict_proba returned the wrong number of rows", file=sys.stderr)
        return 2
    if any(not (0.0 <= p <= 1.0) for p in model_scores):
        print("predict_proba returned values outside [0,1]", file=sys.stderr)
        return 2

    model_auc_sklearn = float(roc_auc_score(eval_y, model_scores))
    model_auc_midrank = auc(eval_y, model_scores)

    # ---- references, recomputed from the shipped bytes -------------------
    persistence_scores = []
    for value in evald["site_prior_lift30_rate"]:
        persistence_scores.append(float(value) if float(value) >= 0 else train_rate)
    covered = int((evald["site_prior_lift30_rate"] >= 0).sum())

    county_month, county_rate = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    for row, label in zip(train.to_dict("records"), train_y):
        key = (row["county"], row["issue_month"])
        county_month[key][0] += label
        county_month[key][1] += 1
        county_rate[row["county"]][0] += label
        county_rate[row["county"]][1] += 1

    def calendar_score(row) -> float:
        key = (row["county"], row["issue_month"])
        if key in county_month and county_month[key][1] >= 5:
            return county_month[key][0] / county_month[key][1]
        if row["county"] in county_rate:
            return county_rate[row["county"]][0] / county_rate[row["county"]][1]
        return train_rate

    calendar_scores = [calendar_score(r) for r in evald.to_dict("records")]

    reason_rate = defaultdict(lambda: [0, 0])
    for row, label in zip(train.to_dict("records"), train_y):
        reason_rate[row["reason"]][0] += label
        reason_rate[row["reason"]][1] += 1
    reason_scores = [
        reason_rate[r["reason"]][0] / reason_rate[r["reason"]][1]
        if r["reason"] in reason_rate else train_rate
        for r in evald.to_dict("records")]

    majority = 1 if train_rate >= 0.5 else 0
    majority_accuracy = sum(y == majority for y in eval_y) / len(eval_y)

    persistence_auc = auc(eval_y, persistence_scores)
    calendar_auc = auc(eval_y, calendar_scores)
    reason_auc = auc(eval_y, reason_scores)

    # ---- the comparisons the aggregate-only contract could not carry -----
    differences = {
        "model_vs_persistence_row": paired_row_bootstrap(
            eval_y, model_scores, persistence_scores),
        "model_vs_calendar_row": paired_row_bootstrap(
            eval_y, model_scores, calendar_scores),
        "model_vs_persistence_site_cluster": paired_cluster_bootstrap(
            eval_y, model_scores, persistence_scores,
            evald["site_name"].tolist()),
    }
    observed_gaps = {
        "model_minus_persistence": (round(model_auc_midrank - persistence_auc, 6)
                                    if model_auc_midrank is not None and persistence_auc is not None
                                    else None),
        "model_minus_calendar": (round(model_auc_midrank - calendar_auc, 6)
                                 if model_auc_midrank is not None and calendar_auc is not None
                                 else None),
    }

    # ---- per-issue-year, mandatory beside any pooled figure --------------
    years = evald["issue_date"].astype(str).str[:4].tolist()
    per_year = {}
    by_year = defaultdict(list)
    for index, year in enumerate(years):
        by_year[year].append(index)
    for year, indexes in sorted(by_year.items()):
        labels = [eval_y[i] for i in indexes]
        per_year[year] = {
            "rows": len(indexes),
            "positives": sum(labels),
            "positive_rate": round(sum(labels) / len(labels), 4),
            "model_auc": auc(labels, [model_scores[i] for i in indexes]),
            "model_brier": brier(labels, [model_scores[i] for i in indexes]),
            "persistence_auc": auc(labels, [persistence_scores[i] for i in indexes]),
            "persistence_brier": brier(labels, [persistence_scores[i] for i in indexes]),
            "calendar_auc": auc(labels, [calendar_scores[i] for i in indexes]),
        }

    # ---- runner-file and acceptance evidence -----------------------------
    declared = json.loads(runner_json.read_text()) if runner_json and runner_json.is_file() else {}
    actual = {name: sha256_of(workdir / name) for name in ("train.py", "validate.py", "validate.sh")
              if (workdir / name).is_file()}
    accept_log = (out / "accept.log").read_text() if (out / "accept.log").is_file() else ""
    accepted = re.search(r"matches the qualified artifact ([0-9a-f]{16,64})", accept_log)
    validate_log = (out / "validate.log").read_text() if (out / "validate.log").is_file() else ""
    validate_auc = re.findall(r"eval AUC via predict_proba \(target column removed\):\s*([0-9.]+)", validate_log)

    per_row = {
        "advisory_id": evald["advisory_id"].tolist(),
        "issue_year": years,
        "site_name": evald["site_name"].tolist(),
        "label": eval_y,
        "model_score": model_scores,
        "persistence_score": persistence_scores,
        "calendar_score": calendar_scores,
    }

    result = {
        "job": (Path("/workspace/job_id.txt").read_text().strip()
                if Path("/workspace/job_id.txt").is_file() else None),
        "purpose": "per-row model scores and the model-vs-reference comparison "
                   "the aggregate-only runner contract could not carry",
        "artifact": {"name": task["name"], "target": task["target"],
                     "positive_label": task["positive_label"],
                     "id_columns": task["id_columns"], "rows": task["rows"]},
        "qualification_report": {
            "accepted_before_scoring": accepted is not None,
            "accepted_artifact_version": accepted.group(1) if accepted else None,
            "bundled_report_sha256": sha256_of(Path("/workspace/qualification.json"))
            if Path("/workspace/qualification.json").is_file() else None,
        },
        "runner_files": {"bundled_sha256": actual, "expected_sha256": declared,
                         "unmodified": bool(declared) and all(
                             declared.get(nm) == value for nm, value in actual.items())},
        "dependencies": versions(),
        "rows": {"eval": len(evald), "train": len(train)},
        "train_positive_rate": round(train_rate, 6),
        "eval_positive_rate": round(sum(eval_y) / len(eval_y), 6),
        "model": {
            "configuration": "benchmark template XGBClassifier n_estimators=30 "
                              "max_depth=6 lr=0.1 seed 42, refit here by the bundled "
                              "train.py; nothing re-tuned",
            "eval_auc_sklearn": round(model_auc_sklearn, 6),
            "eval_auc_midrank": model_auc_midrank,
            "eval_auc_printed_by_train_py": float(printed[-1]) if printed else None,
            "eval_auc_from_validate_log": float(validate_auc[-1]) if validate_auc else None,
            "eval_brier": brier(eval_y, model_scores),
        },
        "references_recomputed": {
            "persistence_site_prior": {
                "covered_rows": covered,
                "coverage": round(covered / len(evald), 4),
                "auc": persistence_auc,
                "brier": brier(eval_y, persistence_scores)},
            "calendar_county_month": {"auc": calendar_auc,
                                      "brier": brier(eval_y, calendar_scores)},
            "reason_prior": {"auc": reason_auc, "brier": brier(eval_y, reason_scores)},
            "majority_class": {"prediction": majority, "accuracy": majority_accuracy},
        },
        "replication_against_recorded": {
            "recorded_values": RECORDED,
            "recomputed_matches_recorded": {
                "persistence_auc": agrees(persistence_auc, RECORDED["persistence_site_prior_auc"]["value"]),
                "calendar_auc": agrees(calendar_auc, RECORDED["calendar_county_month_auc"]["value"]),
                "reason_auc": agrees(reason_auc, RECORDED["reason_prior_auc"]["value"]),
                "majority_accuracy": agrees(majority_accuracy, RECORDED["majority_class_accuracy"]["value"]),
                "model_auc": agrees(model_auc_midrank, RECORDED["full_model_eval_auc"]["value"]),
            },
            "note": "constants are figures recorded by jobs ns-bwa-001 and "
                    "ns-bwa-baseline-001 on this same artifact; agreement is "
                    "measured here, not assumed",
        },
        "observed_gaps": observed_gaps,
        "paired_differences": differences,
        "per_issue_year": per_year,
        "per_row_scores": per_row,
        "scope": "diagnostic only: eval split, one model configuration, no "
                 "re-tuning, no agent loop; the holdout was never read and "
                 "stays sealed",
    }
    (out / "diag_result.json").write_text(json.dumps(result, indent=1) + "\n")

    print(f"model AUC: sklearn={model_auc_sklearn:.4f} midrank={model_auc_midrank:.4f} "
          f"train.py printed={printed[-1] if printed else None}")
    print(f"persistence AUC {persistence_auc:.4f} (covered {covered}/{len(evald)}), "
          f"calendar {calendar_auc:.4f}, reason {reason_auc:.4f}, "
          f"majority accuracy {majority_accuracy:.4f}")
    for name, interval in differences.items():
        print(f"{name}: mean {interval.get('mean')} ci95 "
              f"[{interval.get('ci95_low')}, {interval.get('ci95_high')}]")
    for year, figures in per_year.items():
        print(f"{year}: rate {figures['positive_rate']} model AUC {figures['model_auc']} "
              f"persistence AUC {figures['persistence_auc']}")
    clean = (result["runner_files"]["unmodified"]
             and result["qualification_report"]["accepted_before_scoring"]
             and model_auc_midrank is not None)
    return 0 if clean else 5


if __name__ == "__main__":
    raise SystemExit(main())
