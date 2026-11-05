#!/usr/bin/env python3
"""Simple references for the accepted `afdb-project-cancellation` artifact.

Runs ONLY after the qualification gate has passed on the full artifact and
--accept has re-verified the report against these exact bytes (run.sh enforces
the order). It reads the written CSVs, never rewrites them, and computes every
reference on the SAME eval rows.

The task is a one-shot operation-outcome question at the board-approval instant,
so the pre-registered baseline triad (candidate record, 2026-11-05, written
BEFORE any construction or score) takes this shape - each reference estimated
ONLY from training-era rows, evaluated against THIS split's labels:

  * global_rate - the constant train cancellation rate. No ranking
    information; its AUC is degenerate by construction and reported as null,
    never as zero.
  * trailing_country_rate - train-estimated cancellation rate per
    country_or_region (identity prior), global train rate as fallback.
  * trailing_sector_decade_rate - train-estimated rate per
    (sector_code x approval decade) cell, falling back to the sector's train
    rate, then the global rate. Tests whether sector-and-era rate tables carry
    the signal.

Supplementary references (reported, never part of the deciding set):
  * persistence_country_last - the label of the country_or_region's latest
    earlier TRAIN operation by approval_date (majority as fallback). The
    one-shot task has no within-row history, so a country's last observed
    terminal status IS the persistence analogue.
  * majority_class - the constant label fitted on train, measured against this
    split's labels (accuracy, not AUC).

DECIDING CHECK (pre-registered, runs in the baseline job where the full model
exists): headroom is demonstrated ONLY if the full model beats EVERY triad
member with a cluster-aware paired bootstrap 95% CI excluding zero in the
model's favour, the cluster being the declared event_key (country-or-region x
approval year). Triad dominance -> the candidate DROPS (the third measured
instance of the WB at-approval family defect), with the evidence preserved.
No re-tuning of threshold, window, label or features after any score.

Eval-only: the holdout is sealed until the design is frozen and the runner
evaluates it once. Per-approval-year reporting is mandatory - prevalence moves
across five decades, so a pooled number hides structure.

Uncertainty: cluster-aware paired bootstrap differences (1000 resamples, fixed
seed) on identical eval rows - never overlapping marginal intervals. An
interval containing zero is an inconclusive difference, not parity.

Stdlib only. No credentials.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

NAME = "afdb-project-cancellation"
TARGET = "cancelled"
POSITIVE = "1"
BOOTSTRAP = 1000
SEED = 20261105
DECIDING_MEMBERS = ("global_rate", "trailing_country_rate",
                    "trailing_sector_decade_rate")


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


def triad_score_vectors(train_rows: list[dict], eval_rows: list[dict],
                        train_rate: float) -> dict[str, list[float]]:
    """The three pre-registered triad members as per-row eval scores.

    Every table is estimated ONLY from train rows; eval rows never contribute
    to their own reference. Identical definitions are reused by the baseline
    job for the deciding model-vs-triad comparison.
    """
    train_labels = labels_of(train_rows)

    country_table = _rate_table(train_rows, train_labels,
                                lambda r: r["country_or_region"])
    country_scores = [_cell_rate(country_table, row["country_or_region"],
                                 train_rate) for row in eval_rows]

    sector_table = _rate_table(train_rows, train_labels,
                               lambda r: r["sector_code"])
    sector_decade_table = _rate_table(
        train_rows, train_labels,
        lambda r: (r["sector_code"], r["era"]))
    sector_decade_scores = []
    for row in eval_rows:
        cell = (row["sector_code"], row["era"])
        if cell in sector_decade_table:
            sector_decade_scores.append(_cell_rate(sector_decade_table, cell,
                                                   train_rate))
        else:
            # unseen (sector, decade) cell: sector prior, then global rate
            sector_decade_scores.append(_cell_rate(sector_table, row["sector_code"],
                                                   train_rate))
    return {
        "global_rate": [train_rate] * len(eval_rows),
        "trailing_country_rate": country_scores,
        "trailing_sector_decade_rate": sector_decade_scores,
    }


def persistence_scores(train_rows: list[dict], eval_rows: list[dict],
                       majority: int) -> tuple[list[float], int]:
    """Label of the country_or_region's latest earlier train operation."""
    last_date: dict[str, str] = {}
    last_label: dict[str, int] = {}
    train_labels = labels_of(train_rows)
    for row, label in zip(train_rows, train_labels):
        day = row["approval_date"]
        group = row["country_or_region"]
        if group not in last_date or day > last_date[group]:
            last_date[group] = day
            last_label[group] = label
    scores = [float(last_label.get(row["country_or_region"], majority))
              for row in eval_rows]
    covered = sum(1 for row in eval_rows if row["country_or_region"] in last_label)
    return scores, covered


def clustered_paired_bootstrap(labels: list[int], scores_a: list[float],
                               scores_b: list[float], cluster_keys: list[str],
                               resamples: int = BOOTSTRAP,
                               seed: int = SEED) -> dict:
    """Cluster-aware paired bootstrap of AUC(A) - AUC(B) on identical rows.

    Clusters (the declared event_key) are resampled with replacement, so rows
    sharing a country-year cell move together; positives arrive clustered and
    independent-row resampling would overstate precision.
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
                 "clusters = declared event_key cells; an interval containing "
                 "zero is inconclusive, not parity"),
    }


def cluster_bootstrap_auc(labels: list[int], scores: list[float],
                          cluster_keys: list[str], resamples: int = BOOTSTRAP,
                          seed: int = SEED) -> dict:
    """One-sample cluster-aware bootstrap CI of AUC(scores) itself.

    Used for the degenerate triad member (the constant global rate), which
    carries no ranking information: a paired difference against a constant is
    undefined, so the comparison is whether the model's own cluster-bootstrap
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
        "note": ("one-sample cluster-aware bootstrap of the model AUC, "
                 "clusters = declared event_key cells"),
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
    persist, persist_covered = persistence_scores(train_rows, eval_rows, majority)
    cluster_keys = [row["event_key"] for row in eval_rows]

    references = {
        "global_rate": {
            "definition": ("constant train cancellation rate; no ranking "
                           "information, AUC degenerate by construction"),
            "rate": round(train_rate, 6),
            "brier": brier(eval_labels, vectors["global_rate"]),
            "auc": None,
        },
        "trailing_country_rate": {
            "definition": ("train-estimated cancellation rate per "
                            "country_or_region (identity prior), global rate "
                            "fallback"),
            "unseen_country_rows": sum(1 for row in eval_rows
                                        if row["country_or_region"] not in
                                        {r["country_or_region"] for r in train_rows}),
            "auc": auc(eval_labels, vectors["trailing_country_rate"]),
            "brier": brier(eval_labels, vectors["trailing_country_rate"]),
        },
        "trailing_sector_decade_rate": {
            "definition": ("train-estimated rate per sector_code x approval "
                            "decade cell; sector rate then global rate as "
                            "fallbacks"),
            "auc": auc(eval_labels, vectors["trailing_sector_decade_rate"]),
            "brier": brier(eval_labels, vectors["trailing_sector_decade_rate"]),
        },
        "persistence_country_last": {
            "definition": ("label of the country_or_region's latest earlier "
                            "train operation by approval_date (supplementary "
                            "one-shot persistence analogue, not a deciding "
                            "triad member); majority fallback"),
            "covered_rows": persist_covered,
            "coverage": round(persist_covered / len(eval_rows), 4),
            "auc": auc(eval_labels, persist),
            "brier": brier(eval_labels, persist),
        },
        "majority_class": {
            "definition": ("majority label fitted on train, measured against "
                           "this split's labels"),
            "prediction": majority,
            "accuracy": accuracy(eval_labels, [majority] * len(eval_rows)),
        },
    }

    differences = {}
    pairs = (("trailing_country_rate", "trailing_sector_decade_rate"),
             ("trailing_country_rate", "global_rate"),
             ("trailing_sector_decade_rate", "global_rate"))
    for left, right in pairs:
        differences[f"{left}_vs_{right}"] = clustered_paired_bootstrap(
            eval_labels, vectors[left], vectors[right], cluster_keys)

    per_year = {}
    by_year = defaultdict(list)
    for index, row in enumerate(eval_rows):
        by_year[row["approval_date"][:4]].append(index)
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
                          "EVERY member of (" + ", ".join(DECIDING_MEMBERS) +
                          ") with a cluster-aware paired bootstrap 95% CI excluding "
                          "zero in the model's favour; triad dominance -> DROP; "
                          "no re-tuning of threshold, window, label or features "
                          "after any score"),
        "rows": {"train": len(train_rows), "eval": len(eval_rows)},
        "train_positive_rate": round(train_rate, 6),
        "eval_positive_rate": round(sum(eval_labels) / len(eval_labels), 6),
        "references": references,
        "clustered_paired_differences": differences,
        "per_approval_year": per_year,
        "prevalence_shift": {
            "train": round(train_rate, 6),
            "eval": round(sum(eval_labels) / len(eval_labels), 6),
            "note": ("train is the high-cancellation early era; eval prevalence "
                     "shift is an out-of-distribution property of the temporal "
                     "split, reported rather than adjusted"),
        },
        "notes": [
            "global_rate carries no ranking information; its AUC is reported "
            "null, not zero",
            "every rate table is estimated ONLY from train rows",
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
