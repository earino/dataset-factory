#!/usr/bin/env python3
"""Simple references for the accepted `dvsa-mot-next-test-outcome` artifact.

Runs ONLY after the qualification gate has passed on the full artifact and
--accept has re-verified the report against these exact bytes (run.sh enforces
the order). It reads the written CSVs, never rewrites them, and computes every
reference on the SAME eval rows. NO full model exists here - the model-vs-triad
deciding comparison runs in the baseline job where the runner's model is.

The task is a per-vehicle panel prediction at the prior test's completion, so the
pre-registered baseline triad (candidate record, 2026-11-05, written BEFORE any
construction or score) takes this shape - each reference estimated ONLY from
training-era rows, evaluated against THIS split's labels:

  * persistence_prior_result - the last observed outcome: the prior test's own
    initial-fail flag as the score. The reference the model must beat for the
    task to teach more than "cars that failed last time fail again".
  * calendar_make_week - train-estimated initial-fail rate per (make x ISO
    week-of-year of the prediction date), make's train rate then the global
    train rate as fallbacks. Tests the seasonal/coarse-identity reference.
  * vehicle_train_rate - train-estimated initial-fail rate per vehicle_id (the
    identity prior), global train rate as fallback. The panel analogue of the
    trailing-country reference; it uses ONLY train-era rows of the same vehicle.

Supplementary references (reported, never part of the deciding set):
  * global_rate - the constant train rate. No ranking information; its AUC is
    degenerate by construction and reported as null, never as zero.
  * majority_class - the constant label fitted on train, measured against this
    split's labels (accuracy, not AUC).

DECIDING CHECK (pre-registered, runs in the baseline job where the full model
exists): headroom is demonstrated ONLY if the full model beats EVERY member of
(persistence_prior_result, calendar_make_week, vehicle_train_rate) with a
cluster-aware paired bootstrap 95% CI excluding zero in the model's favour, the
cluster being the declared event_key (vehicle_id), AND the model's own
cluster-bootstrap AUC CI lies entirely above 0.5 (the degenerate global-rate
member carries no ranking information and cannot be differenced). Triad
dominance -> the candidate DROPS. No re-tuning of threshold, window, label or
features after any score.

Eval-only: the holdout is sealed until the design is frozen and the runner
evaluates it once. Per-prior-year reporting is mandatory - the 2018 MOT regime
change (May 2018) and the 2020-2021 pandemic test-extension period are
structural breaks a pooled number would hide.

Uncertainty: cluster-aware paired bootstrap differences (fixed seed) on
identical eval rows - never overlapping marginal intervals. An interval
containing zero is an inconclusive difference, not parity.

Stdlib only. No credentials.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from datetime import date
from pathlib import Path

NAME = "dvsa-mot-next-test-outcome"
TARGET = "next_initial_fail"
POSITIVE = "1"
ID_COLUMN = "row_key"
EVENT_KEY = "vehicle_id"
TIME_COLUMN = "prior_test_date"
BOOTSTRAP = 1000
SEED = 20261105
DECIDING_MEMBERS = ("persistence_prior_result", "calendar_make_week",
                    "vehicle_train_rate")


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def labels_of(rows: list[dict]) -> list[int]:
    return [1 if row[TARGET] == POSITIVE else 0 for row in rows]


def auc(labels: list[int], scores: list[float]) -> float | None:
    """Rank-based ROC AUC, tie-averaged. Sorts (score, label) tuples at C speed."""
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        return None
    pairs = sorted(zip(scores, labels))
    if pairs[0][0] == pairs[-1][0]:
        return None  # constant scores carry no ranking information
    rank_sum = 0.0
    index = 0
    while index < len(pairs):
        end = index
        while end + 1 < len(pairs) and pairs[end + 1][0] == pairs[index][0]:
            end += 1
        average = (index + end) / 2.0 + 1.0
        for position in range(index, end + 1):
            if pairs[position][1]:
                rank_sum += average
        index = end + 1
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def brier(labels: list[int], probabilities: list[float]) -> float | None:
    if not labels:
        return None
    return sum((p - y) ** 2 for y, p in zip(labels, probabilities)) / len(labels)


def accuracy(labels: list[int], predictions: list[int]) -> float | None:
    if not labels:
        return None
    return sum(y == p for y, p in zip(labels, predictions)) / len(labels)


def _rate_table(rows: list[dict], labels: list[int], key_fn) -> dict:
    table: dict = {}
    for row, label in zip(rows, labels):
        stats = table.setdefault(key_fn(row), [0, 0])
        stats[0] += label
        stats[1] += 1
    return table


def _cell_rate(table: dict, key, fallback: float) -> float:
    stats = table.get(key)
    return stats[0] / stats[1] if stats else fallback


def _week_of_year(day_text: str) -> int:
    return date.fromisoformat(day_text).isocalendar()[1]


def triad_score_vectors(train_rows: list[dict], eval_rows: list[dict],
                        train_rate: float) -> dict[str, list[float]]:
    """The pre-registered triad members as per-row eval scores.

    Every table is estimated ONLY from train rows; eval rows never contribute
    to their own reference. Identical definitions are reused by the baseline
    job for the deciding model-vs-triad comparison.
    """
    train_labels = labels_of(train_rows)

    persistence = [float(row["prior_initial_fail"]) for row in eval_rows]

    make_table = _rate_table(train_rows, train_labels, lambda r: r["make"])
    make_week_table = _rate_table(
        train_rows, train_labels,
        lambda r: (r["make"], _week_of_year(r[TIME_COLUMN])))
    calendar = []
    unseen_make_weeks = 0
    for row in eval_rows:
        cell = (row["make"], _week_of_year(row[TIME_COLUMN]))
        if cell in make_week_table:
            calendar.append(_cell_rate(make_week_table, cell, train_rate))
        else:
            unseen_make_weeks += 1
            calendar.append(_cell_rate(make_table, row["make"], train_rate))

    vehicle_table = _rate_table(train_rows, train_labels,
                                lambda r: r[EVENT_KEY])
    vehicle_scores = [_cell_rate(vehicle_table, row[EVENT_KEY], train_rate)
                     for row in eval_rows]
    unseen_vehicles = sum(1 for row in eval_rows
                          if row[EVENT_KEY] not in vehicle_table)
    covered = len(eval_rows) - unseen_vehicles

    return {
        "persistence_prior_result": persistence,
        "calendar_make_week": calendar,
        "vehicle_train_rate": vehicle_scores,
        "_diagnostics": {"unseen_make_week_cells": unseen_make_weeks,
                         "unseen_vehicle_rows": unseen_vehicles,
                         "vehicle_rate_covered_rows": covered},
    }


def cluster_indices(cluster_keys: list[str]) -> dict[str, list[int]]:
    by_cluster: dict[str, list[int]] = defaultdict(list)
    for index, key in enumerate(cluster_keys):
        by_cluster[key].append(index)
    return by_cluster


def clustered_paired_bootstrap(labels: list[int], scores_a: list[float],
                               scores_b: list[float], cluster_keys: list[str],
                               resamples: int = BOOTSTRAP,
                               seed: int = SEED) -> dict:
    """Cluster-aware paired bootstrap of AUC(A) - AUC(B) on identical rows.

    Clusters (the declared event_key: vehicle_id) are resampled with replacement,
    so rows of the same vehicle move together; per-vehicle persistence makes
    independent-row resampling overstate precision.
    """
    if not labels or not cluster_keys:
        return {"note": "no rows or no cluster keys"}
    by_cluster = cluster_indices(cluster_keys)
    clusters = sorted(by_cluster)
    if len(clusters) < 2:
        return {"note": "fewer than two clusters"}
    rng = random.Random(seed)
    differences = []
    for _ in range(resamples):
        sample: list[int] = []
        for _ in clusters:
            sample.extend(by_cluster[rng.choice(clusters)])
        boot_labels = [labels[i] for i in sample]
        auc_a = auc(boot_labels, [scores_a[i] for i in sample])
        auc_b = auc(boot_labels, [scores_b[i] for i in sample])
        if auc_a is not None and auc_b is not None:
            differences.append(auc_a - auc_b)
    if not differences:
        return {"note": "degenerate resamples (a split lost one class)"}
    differences.sort()
    return {
        "resamples": len(differences),
        "clusters": len(clusters),
        "mean": round(sum(differences) / len(differences), 6),
        "ci95_low": round(differences[int(0.025 * len(differences))], 6),
        "ci95_high": round(differences[int(0.975 * len(differences))], 6),
        "note": ("cluster-aware paired bootstrap on identical eval rows, "
                 "clusters = vehicle_id (the declared event_key); an interval "
                 "containing zero is inconclusive, not parity"),
    }


def cluster_bootstrap_auc(labels: list[int], scores: list[float],
                          cluster_keys: list[str], resamples: int = BOOTSTRAP,
                          seed: int = SEED) -> dict:
    """One-sample cluster-aware bootstrap CI of AUC(scores) itself.

    Used against the degenerate global-rate member: a paired difference against
    a constant is undefined, so the comparison is whether the reference's (or
    the model's, in the baseline job) own cluster-bootstrap AUC CI lies entirely
    above 0.5.
    """
    if not labels or not cluster_keys:
        return {"note": "no rows or no cluster keys"}
    by_cluster = cluster_indices(cluster_keys)
    clusters = sorted(by_cluster)
    if len(clusters) < 2:
        return {"note": "fewer than two clusters"}
    rng = random.Random(seed)
    values = []
    for _ in range(resamples):
        sample: list[int] = []
        for _ in clusters:
            sample.extend(by_cluster[rng.choice(clusters)])
        value = auc([labels[i] for i in sample], [scores[i] for i in sample])
        if value is not None:
            values.append(value)
    if not values:
        return {"note": "degenerate resamples (a split lost one class)"}
    values.sort()
    return {
        "resamples": len(values),
        "clusters": len(clusters),
        "auc_ci95_low": round(values[int(0.025 * len(values))], 6),
        "auc_ci95_high": round(values[int(0.975 * len(values))], 6),
        "note": "one-sample cluster-aware bootstrap of AUC, clusters = vehicle_id",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--accepted-report", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    data = Path(args.data)

    report = json.loads(Path(args.accepted_report).read_text())
    if not report.get("ok"):
        raise SystemExit("the qualification report did not pass; scoring is refused")

    train_rows = read_rows(data / "public" / "train.csv")
    eval_rows = read_rows(data / "public" / "eval.csv")
    train_labels = labels_of(train_rows)
    eval_labels = labels_of(eval_rows)
    train_rate = sum(train_labels) / len(train_labels)
    majority = 1 if train_rate >= 0.5 else 0

    vectors = triad_score_vectors(train_rows, eval_rows, train_rate)
    diagnostics = vectors.pop("_diagnostics")
    cluster_keys = [row[EVENT_KEY] for row in eval_rows]

    references = {
        "persistence_prior_result": {
            "definition": "the prior test's own initial-fail flag (the last "
                          "observed outcome); fitted on nothing, estimated from "
                          "no table",
            "auc": auc(eval_labels, vectors["persistence_prior_result"]),
            "brier": brier(eval_labels, vectors["persistence_prior_result"]),
        },
        "calendar_make_week": {
            "definition": "train-estimated initial-fail rate per (make x ISO "
                          "week-of-year of prior_test_date); make train rate, "
                          "then global train rate, as fallbacks",
            "unseen_make_week_cells": diagnostics["unseen_make_week_cells"],
            "auc": auc(eval_labels, vectors["calendar_make_week"]),
            "brier": brier(eval_labels, vectors["calendar_make_week"]),
        },
        "vehicle_train_rate": {
            "definition": "train-estimated initial-fail rate per vehicle_id "
                          "(identity prior); global train rate fallback",
            "covered_rows": diagnostics["vehicle_rate_covered_rows"],
            "coverage": round(diagnostics["vehicle_rate_covered_rows"]
                              / len(eval_rows), 4),
            "auc": auc(eval_labels, vectors["vehicle_train_rate"]),
            "brier": brier(eval_labels, vectors["vehicle_train_rate"]),
        },
        "global_rate": {
            "definition": "constant train initial-fail rate; no ranking "
                          "information, AUC degenerate by construction",
            "rate": round(train_rate, 6),
            "brier": brier(eval_labels, [train_rate] * len(eval_rows)),
            "auc": None,
        },
        "majority_class": {
            "definition": "majority label fitted on train, measured against "
                          "this split's labels",
            "prediction": majority,
            "accuracy": accuracy(eval_labels, [majority] * len(eval_rows)),
        },
    }

    differences = {}
    pairs = (("persistence_prior_result", "calendar_make_week"),
             ("persistence_prior_result", "vehicle_train_rate"),
             ("calendar_make_week", "vehicle_train_rate"),
             ("persistence_prior_result", "global_rate"),
             ("vehicle_train_rate", "global_rate"))
    for left, right in pairs:
        differences[f"{left}_vs_{right}"] = clustered_paired_bootstrap(
            eval_labels, vectors[left],
            [train_rate] * len(eval_rows) if right == "global_rate"
            else vectors[right], cluster_keys)
    differences["global_rate_auc_ci"] = None  # degenerate; see cluster_bootstrap_auc

    per_year = {}
    by_year = defaultdict(list)
    for index, row in enumerate(eval_rows):
        by_year[row[TIME_COLUMN][:4]].append(index)
    for year, indexes in sorted(by_year.items()):
        labels = [eval_labels[i] for i in indexes]
        entry = {
            "rows": len(indexes),
            "positives": sum(labels),
            "positive_rate": round(sum(labels) / len(labels), 4),
        }
        for name in DECIDING_MEMBERS:
            entry[f"{name}_auc"] = auc(labels, [vectors[name][i] for i in indexes])
        per_year[year] = entry

    output = {
        "name": NAME,
        "stage": "pre-registered reference triad on identical eval rows "
                 "(post-acceptance)",
        "accepted_report": Path(args.accepted_report).name,
        "artifact_version": (report.get("artifact") or {}).get("artifact_version",
                                                              {}).get("digest"),
        "deciding_rule": ("headroom is demonstrated ONLY if the full model beats "
                          "EVERY member of (" + ", ".join(DECIDING_MEMBERS) + ") "
                          "with a cluster-aware paired bootstrap 95% CI excluding "
                          "zero in the model's favour AND the model's own "
                          "cluster-bootstrap AUC CI lies entirely above 0.5 (the "
                          "constant global rate carries no ranking information); "
                          "triad dominance -> DROP; no re-tuning of threshold, "
                          "window, label or features after any score"),
        "rows": {"train": len(train_rows), "eval": len(eval_rows)},
        "train_positive_rate": round(train_rate, 6),
        "eval_positive_rate": round(sum(eval_labels) / len(eval_labels), 6),
        "references": references,
        "clustered_paired_differences": differences,
        "per_prior_year": per_year,
        "prevalence_shift": {
            "train": round(train_rate, 6),
            "eval": round(sum(eval_labels) / len(eval_labels), 6),
            "note": ("train priors are 2009-2018 (pre/partially post the May-2018 "
                     "regime change), eval priors are 2019-2021 (post-change, "
                     "including the 2020-21 pandemic test-extension period); any "
                     "prevalence shift is a property of the temporal split, "
                     "reported rather than adjusted"),
        },
        "notes": [
            "global_rate carries no ranking information; its AUC is reported "
            "null, not zero",
            "every rate table is estimated ONLY from train rows",
            "clusters are vehicle_id, the declared event_key; intervals are "
            "cluster-aware paired bootstraps on identical rows",
            "the full model (harness runner baseline) is quoted beside these "
            "references when its job exists; the deciding comparison runs there",
            "the holdout is sealed: no reference or model in this file reads "
            "private/holdout.csv",
        ],
    }
    Path(args.report).write_text(json.dumps(output, indent=1) + "\n")
    for name, ref in references.items():
        print(f"{name}: auc={ref.get('auc')} brier={ref.get('brier')} "
              f"accuracy={ref.get('accuracy')}")
    print(f"eval positive_rate={output['eval_positive_rate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
