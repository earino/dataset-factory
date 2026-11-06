#!/usr/bin/env python3
"""Pre-registered simple references for the accepted `cpcb-aqi-exceedance` artifact.

Runs ONLY after the qualification gate has passed on the full artifact and
--accept re-verified the report against these exact bytes (run.sh enforces the
order). Reads the written CSVs, never rewrites them, and computes every
reference on the SAME eval rows.

Task: at 23:59 IST on day D, predict whether the station's D+1 calendar-day
24-hour mean PM2.5 exceeds 90 ug/m3 (the CPCB National AQI Poor-band lower
edge). The pre-registered triad (candidate notes.md, 2026-11-05, written BEFORE
any score; no score/gate/acceptance had ever existed for this candidate):

  * station_persistence - the station's most recent observed daily value, i.e.
    the shipped `pm25_mean` of day D itself, used as the score for tomorrow's
    exceedance. The direct analogue of "it was bad today, so it will be bad
    tomorrow": a model that cannot beat today's level has not learned a
    forecast. Supplementary (never deciding): the binary agreement of
    [pm25_mean > 90] with the label, reported as accuracy.
  * state_season_climatology - train-estimated exceedance rate per
    (state_name x season of the TARGET day D+1), falling back to the state's
    train rate, then the global train rate. Tests whether the calendar and the
    station's coarse geography carry the signal.
  * global_rate - the constant train exceedance rate. No ranking information;
    its AUC is degenerate by construction and reported as null, never zero.

Supplementary references (reported, never part of the deciding set):
  * station_train_rate - train-estimated rate per station_id (identity
    memorisation), global train rate as fallback.
  * majority_class - the constant label fitted on train, measured against this
    split's labels (accuracy, not AUC).

DECIDING CHECK (pre-registered, applied in the baseline job where the full
model exists): headroom is demonstrated ONLY if the full model beats EVERY
triad member on identical eval rows with a station-clustered paired bootstrap
95% CI excluding zero in the model's favour AND the model's own
cluster-bootstrap AUC CI lies entirely above 0.5 (the degenerate constant
member). Triad dominance -> recorded defect; drop or re-target. No re-tuning of
threshold, window, label or features after any score.

Eval-only: the holdout is sealed and never read here. Positives are winter-
clustered, so the clustered event count (distinct positive days) is the
independent evidence, not the row count; per-season and per-prediction-month
tables are mandatory - a pooled AUC hides the monsoon/winter structure.

Uncertainty: cluster-aware paired bootstrap differences (1000 resamples, fixed
seed), cluster = station_id, on identical eval rows - never overlapping
marginal intervals. An interval containing zero is an inconclusive difference,
not parity.

Stdlib only. No credentials.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

NAME = "cpcb-aqi-exceedance"
TARGET = "exceeds"
POSITIVE = "1"
THRESHOLD = 90.0
BOOTSTRAP = 1000
SEED = 20261105
DECIDING_MEMBERS = ("station_persistence", "state_season_climatology", "global_rate")
SEASON_OF_MONTH = {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM",
                   6: "JJAS", 7: "JJAS", 8: "JJAS", 9: "JJAS", 10: "ON", 11: "ON"}


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def labels_of(rows: list[dict]) -> list[int]:
    return [1 if row[TARGET] == POSITIVE else 0 for row in rows]


def auc(labels: list[int], scores: list[float]) -> float | None:
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        return None
    if len(set(scores)) == 1:
        return None  # constant scores carry no ranking information
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    ranks = [0.0] * len(scores)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        average = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = average
        i = j + 1
    rank_sum = sum(ranks[k] for k in range(len(labels)) if labels[k])
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def brier(labels: list[int], probabilities: list[float]) -> float | None:
    if not labels:
        return None
    return sum((p - y) ** 2 for y, p in zip(labels, probabilities)) / len(labels)


def accuracy(labels: list[int], predictions: list[int]) -> float | None:
    if not labels:
        return None
    return sum(y == p for y, p in zip(labels, predictions)) / len(labels)


def _cell_rate(table: dict, key, fallback: float) -> float:
    stats = table.get(key)
    return stats[0] / stats[1] if stats else fallback


def _rate_table(rows: list[dict], labels: list[int], key_fn) -> dict:
    table: dict = {}
    for row, label in zip(rows, labels):
        stats = table.setdefault(key_fn(row), [0, 0])
        stats[0] += label
        stats[1] += 1
    return table


def target_season(row: dict) -> str:
    """Season of the TARGET day D+1 (calendar arithmetic from the shipped date)."""
    target_day = date.fromisoformat(row["date"]) + timedelta(days=1)
    return SEASON_OF_MONTH[target_day.month]


def triad_score_vectors(train_rows: list[dict], eval_rows: list[dict],
                        train_rate: float) -> dict[str, list[float]]:
    """The three pre-registered triad members as per-row eval scores.

    Every table is estimated ONLY from train rows; eval rows never contribute
    to their own reference. The identical definitions are reused by the
    baseline job for the deciding model-vs-triad comparison.
    """
    train_labels = labels_of(train_rows)

    state_table = _rate_table(train_rows, train_labels, lambda r: r["state_name"])
    state_season_table = _rate_table(
        train_rows, train_labels, lambda r: (r["state_name"], target_season(r)))
    state_season_scores = []
    for row in eval_rows:
        cell = (row["state_name"], target_season(row))
        if cell in state_season_table:
            state_season_scores.append(
                _cell_rate(state_season_table, cell, train_rate))
        else:
            # unseen (state, season) cell: the state prior, then the global rate
            state_season_scores.append(
                _cell_rate(state_table, row["state_name"], train_rate))

    persistence_scores = [float(row["pm25_mean"]) for row in eval_rows]

    return {
        "station_persistence": persistence_scores,
        "state_season_climatology": state_season_scores,
        "global_rate": [train_rate] * len(eval_rows),
    }


def station_rate_scores(train_rows: list[dict], eval_rows: list[dict],
                        train_rate: float) -> list[float]:
    """Supplementary identity prior: train-estimated rate per station_id."""
    table = _rate_table(train_rows, labels_of(train_rows), lambda r: r["station_id"])
    return [_cell_rate(table, row["station_id"], train_rate) for row in eval_rows]


def clustered_paired_bootstrap(labels: list[int], scores_a: list[float],
                               scores_b: list[float], cluster_keys: list[str],
                               resamples: int = BOOTSTRAP,
                               seed: int = SEED) -> dict:
    """Cluster-aware paired bootstrap of AUC(A) - AUC(B) on identical rows.

    Clusters (station_id) are resampled with replacement, so a station's whole
    eval history moves together; positives arrive winter-clustered by day and
    station, and independent-row resampling would overstate precision.
    """
    if not labels or not cluster_keys:
        return {"note": "no rows or no cluster keys"}
    by_cluster: dict[str, list[int]] = defaultdict(list)
    for index, key in enumerate(cluster_keys):
        by_cluster[key].append(index)
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
                 "clusters = station_id; an interval containing zero is "
                 "inconclusive, not parity"),
    }


def cluster_bootstrap_auc(labels: list[int], scores: list[float],
                          cluster_keys: list[str], resamples: int = BOOTSTRAP,
                          seed: int = SEED) -> dict:
    """One-sample cluster-aware bootstrap CI of AUC(scores) itself.

    Used for the degenerate constant member (global_rate), which carries no
    ranking information: "beating" it means the model's own cluster-bootstrap
    AUC CI lies entirely above 0.5.
    """
    if not labels or not cluster_keys:
        return {"note": "no rows or no cluster keys"}
    by_cluster: dict[str, list[int]] = defaultdict(list)
    for index, key in enumerate(cluster_keys):
        by_cluster[key].append(index)
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
        "note": ("one-sample cluster-aware bootstrap of AUC, clusters = "
                 "station_id"),
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
    # Build the (state, target-season) train table ONCE for the coverage counter.
    # (Pre-launch review defect in attempt -002's bundle: this was rebuilt inside a
    # per-eval-row generator, i.e. 154k x 340k operations - a hang, not a score.)
    state_season_train = _rate_table(train_rows, train_labels,
                                     lambda r: (r["state_name"], target_season(r)))
    station_prior = station_rate_scores(train_rows, eval_rows, train_rate)
    cluster_keys = [row["station_id"] for row in eval_rows]

    persistence_binary = [1 if float(row["pm25_mean"]) > THRESHOLD else 0
                          for row in eval_rows]

    references = {
        "station_persistence": {
            "definition": ("the station's most recent observed daily value: the "
                           "shipped pm25_mean of day D scored directly as the "
                           "probability-like ranking for D+1 exceedance "
                           "(full coverage by construction - every scored row "
                           "carries a complete day D)"),
            "auc": auc(eval_labels, vectors["station_persistence"]),
            "brier": brier(eval_labels, [s / 100.0 for s in
                                         vectors["station_persistence"]]),
            "supplementary_binary_agreement": {
                "rule": "predict exceedance iff pm25_mean > 90 ug/m3",
                "accuracy": accuracy(eval_labels, persistence_binary),
                "predicted_positive_rate": round(
                    sum(persistence_binary) / len(persistence_binary), 6),
            },
        },
        "state_season_climatology": {
            "definition": ("train-estimated exceedance rate per (state_name x "
                           "season of the TARGET day D+1); the state's train "
                           "rate then the global train rate are the fallbacks"),
            "unseen_cell_rows": sum(
                1 for row in eval_rows
                if (row["state_name"], target_season(row)) not in
                state_season_train),
            "auc": auc(eval_labels, vectors["state_season_climatology"]),
            "brier": brier(eval_labels, vectors["state_season_climatology"]),
        },
        "global_rate": {
            "definition": ("constant train exceedance rate; no ranking "
                           "information, AUC degenerate by construction"),
            "rate": round(train_rate, 6),
            "brier": brier(eval_labels, vectors["global_rate"]),
            "auc": None,
        },
        "station_train_rate": {
            "definition": ("supplementary identity prior: train-estimated "
                           "exceedance rate per station_id, global rate as "
                           "fallback (reported, never a deciding member)"),
            "auc": auc(eval_labels, station_prior),
            "brier": brier(eval_labels, station_prior),
        },
        "majority_class": {
            "definition": ("majority label fitted on train, measured against "
                           "this split's labels"),
            "prediction": majority,
            "accuracy": accuracy(eval_labels, [majority] * len(eval_rows)),
        },
    }

    differences = {}
    pairs = (("station_persistence", "state_season_climatology"),
             ("station_persistence", "global_rate"),
             ("state_season_climatology", "global_rate"))
    for left, right in pairs:
        differences[f"{left}_vs_{right}"] = clustered_paired_bootstrap(
            eval_labels, vectors[left], vectors[right], cluster_keys)

    per_month = {}
    by_month = defaultdict(list)
    for index, row in enumerate(eval_rows):
        by_month[row["date"][:7]].append(index)
    for month, indexes in sorted(by_month.items()):
        labels = [eval_labels[i] for i in indexes]
        entry = {
            "rows": len(indexes),
            "positives": sum(labels),
            "positive_rate": round(sum(labels) / len(labels), 6),
        }
        for name in DECIDING_MEMBERS:
            entry[f"{name}_auc"] = auc(labels, [vectors[name][i] for i in indexes])
        per_month[month] = entry

    per_season = {}
    by_season = defaultdict(list)
    for index, row in enumerate(eval_rows):
        by_season[SEASON_OF_MONTH[int(row["date"][5:7])]].append(index)
    for season, indexes in sorted(by_season.items()):
        labels = [eval_labels[i] for i in indexes]
        per_season[season] = {
            "rows": len(indexes),
            "positives": sum(labels),
            "positive_rate": round(sum(labels) / len(labels), 6),
            "station_persistence_auc": auc(
                labels, [vectors["station_persistence"][i] for i in indexes]),
            "state_season_climatology_auc": auc(
                labels, [vectors["state_season_climatology"][i] for i in indexes]),
        }

    output = {
        "name": NAME,
        "stage": ("pre-registered reference triad on identical eval rows "
                  "(post-acceptance)"),
        "accepted_report": Path(args.accepted_report).name,
        "artifact_version": (report.get("artifact") or {}).get(
            "artifact_version", {}).get("digest"),
        "deciding_rule": ("headroom is demonstrated ONLY if the full model beats "
                          "EVERY member of (" + ", ".join(DECIDING_MEMBERS) +
                          ") with a station-clustered paired bootstrap 95% CI "
                          "excluding zero in the model's favour AND the model's "
                          "own cluster-bootstrap AUC CI lies entirely above 0.5 "
                          "(degenerate constant member); triad dominance -> "
                          "recorded defect (drop or re-target); no re-tuning of "
                          "threshold, window, label or features after any score"),
        "rows": {"train": len(train_rows), "eval": len(eval_rows)},
        "train_positive_rate": round(train_rate, 6),
        "eval_positive_rate": round(sum(eval_labels) / len(eval_labels), 6),
        "eval_distinct_positive_days": len({row["date"] for row, label
                                            in zip(eval_rows, eval_labels)
                                            if label == 1}),
        "references": references,
        "clustered_paired_differences": differences,
        "per_prediction_month": per_month,
        "per_season": per_season,
        "prevalence_shift": {
            "train": round(train_rate, 6),
            "eval": round(sum(eval_labels) / len(eval_labels), 6),
            "note": ("train (2019-2022) is the higher-prevalence early era; the "
                     "eval (2023) shift is an out-of-distribution property of "
                     "the temporal split, reported rather than adjusted"),
        },
        "notes": [
            "global_rate carries no ranking information; its AUC is reported "
            "null, not zero",
            "every rate table is estimated ONLY from train rows",
            "the full model (harness runner baseline) is quoted beside these "
            "references in the baseline job; the deciding comparison runs there",
            "the holdout is sealed: no reference in this file reads "
            "private/holdout.csv",
            "positives are winter-clustered; the distinct-positive-days count "
            "is the independent evidence, not the row count",
        ],
    }
    Path(args.report).write_text(json.dumps(output, indent=1) + "\n")
    for name, ref in references.items():
        print(f"{name}: auc={ref.get('auc')} brier={ref.get('brier')} "
              f"accuracy={ref.get('accuracy')}")
    print(f"eval positive_rate={output['eval_positive_rate']} "
          f"distinct_positive_days={output['eval_distinct_positive_days']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
