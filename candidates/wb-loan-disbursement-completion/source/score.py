#!/usr/bin/env python3
"""Simple references for the accepted `wb-loan-disbursement-completion` artifact.

Runs ONLY after the qualification gate has passed and --accept has re-verified
the report against these exact bytes. It reads the written CSVs, never
rewrites them, and computes every reference on the SAME eval rows.

The task is a one-shot loan-outcome question at the approval instant, so the
baseline triad takes this shape (each reference estimated ONLY from
training-era rows, evaluated against THIS split's labels):

  * persistence_country_last - the most recent observed analogue: the label
    of the borrowing country's latest earlier matured TRAIN loan (by approval
    date), falling back to the global train rate. The one-shot task has no
    within-row history, so a country's last observed completion IS the
    persistence reference; a useful model must beat it.
  * country_prior - train-estimated positive rate per country (calendar /
    identity prior), falling back to the global train rate: tests whether
    country identity alone carries the signal.
  * loan_type_prior - train-estimated positive rate per approved instrument
    type: the strongest single approval-attribute prior.
  * majority_class - majority fitted on train, measured against THIS split's
    labels; global_rate - constant train rate (no ranking information; AUC
    degenerate by construction, reported as such).

The full model is NOT computed here: the harness runner's baseline job
trains and evaluates it on these same rows, and its figure is quoted beside
these references when it exists. Nothing in this file may run before
acceptance.

Eval-only: the holdout is sealed until the design is frozen and the runner
evaluates it once. Per-approval-year reporting is mandatory - the eval window
spans 2000-2009 and completion prevalence moves with era, so a pooled number
hides structure.

Uncertainty: paired bootstrap differences (1000 resamples, fixed seed) on
identical eval rows - never overlapping marginal intervals. An interval
containing zero is an inconclusive difference, not parity.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

NAME = "wb-loan-disbursement-completion"
TARGET = "completed90"
POSITIVE = "1"
BOOTSTRAP = 1000
SEED = 23
RATE = "positive_rate"


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


def paired_bootstrap_difference(labels: list[int], scores_a: list[float],
                                scores_b: list[float]) -> dict:
    """Paired bootstrap of AUC(A) - AUC(B) on identical rows."""
    if not labels:
        return {"note": "no rows"}
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
        "resamples": len(differences),
        "mean": round(sum(differences) / len(differences), 6),
        "ci95_low": round(differences[int(0.025 * len(differences))], 6),
        "ci95_high": round(differences[int(0.975 * len(differences))], 6),
        "note": "paired bootstrap on identical rows; an interval containing "
                "zero is inconclusive, not parity",
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

    # ---- references, each estimated only from train --------------------
    country_rate = {}
    country_count = defaultdict(int)
    for row, label in zip(train_rows, train_labels):
        country_count[row["country"]] += 1
        country_rate.setdefault(row["country"], [0, 0])
        country_rate[row["country"]][0] += label
        country_rate[row["country"]][1] += 1

    def prior(group: str) -> float:
        stats = country_rate.get(group)
        return stats[0] / stats[1] if stats else train_rate

    country_scores = [prior(row["country"]) for row in eval_rows]

    type_rate = defaultdict(lambda: [0, 0])
    for row, label in zip(train_rows, train_labels):
        type_rate[row["loan_type"]][0] += label
        type_rate[row["loan_type"]][1] += 1
    type_scores = [
        (type_rate[row["loan_type"]][0] / type_rate[row["loan_type"]][1]
         if row["loan_type"] in type_rate else train_rate)
        for row in eval_rows]

    # persistence: the country's latest earlier matured train loan's label
    last_label = {}
    last_date = {}
    for row, label in zip(train_rows, train_labels):
        day = row["board_approval_date"]
        if row["country"] not in last_date or day > last_date[row["country"]]:
            last_date[row["country"]] = day
            last_label[row["country"]] = label
    persistence_scores = [float(last_label.get(row["country"], majority))
                          for row in eval_rows]
    persistence_covered = sum(1 for row in eval_rows if row["country"] in last_label)

    references = {
        "majority_class": {
            "definition": "majority label fitted on train, measured against "
                          "this split's labels",
            "prediction": majority,
            "accuracy": accuracy(eval_labels, [majority] * len(eval_rows)),
        },
        "global_rate": {
            "definition": "constant train positive rate; no ranking "
                          "information, AUC degenerate by construction",
            "rate": round(train_rate, 6),
            "brier": brier(eval_labels, [train_rate] * len(eval_rows)),
            "auc": None,
        },
        "persistence_country_last": {
            "definition": "label of the borrowing country's latest earlier "
                          "matured train loan (by board approval date), "
                          "global train rate as fallback",
            "covered_rows": persistence_covered,
            "coverage": round(persistence_covered / len(eval_rows), 4),
            "auc": auc(eval_labels, persistence_scores),
            "brier": brier(eval_labels, persistence_scores),
        },
        "country_prior": {
            "definition": "train-estimated positive rate per country "
                          "(identity/calendar prior), global rate fallback",
            "train_countries": len(country_rate),
            "unseen_country_rows": sum(1 for row in eval_rows
                                       if row["country"] not in country_rate),
            "auc": auc(eval_labels, country_scores),
            "brier": brier(eval_labels, country_scores),
        },
        "loan_type_prior": {
            "definition": "train-estimated positive rate per approved "
                          "instrument type",
            "train_types": sorted(type_rate),
            "auc": auc(eval_labels, type_scores),
            "brier": brier(eval_labels, type_scores),
        },
    }

    differences = {
        "persistence_vs_country_prior": paired_bootstrap_difference(
            eval_labels, persistence_scores, country_scores),
        "country_prior_vs_loan_type_prior": paired_bootstrap_difference(
            eval_labels, country_scores, type_scores),
    }

    per_year = {}
    by_year = defaultdict(list)
    for index, row in enumerate(eval_rows):
        by_year[row["board_approval___calendar_year"]].append(index)
    for year, indexes in sorted(by_year.items()):
        labels = [eval_labels[i] for i in indexes]
        per_year[year] = {
            "rows": len(indexes),
            "positives": sum(labels),
            "positive_rate": round(sum(labels) / len(labels), 4),
            "country_prior_auc": auc(labels, [country_scores[i] for i in indexes]),
            "loan_type_prior_auc": auc(labels, [type_scores[i] for i in indexes]),
        }

    output = {
        "name": NAME,
        "stage": "simple references on identical eval rows (post-acceptance)",
        "accepted_report": Path(args.accepted_report).name,
        "artifact_version": (report.get("artifact") or {}).get("version"),
        "rows": {"train": len(train_rows), "eval": len(eval_rows)},
        "train_positive_rate": round(train_rate, 6),
        "eval_positive_rate": round(sum(eval_labels) / len(eval_labels), 6),
        "references": references,
        "paired_differences": differences,
        "per_approval_year": per_year,
        "notes": [
            "persistence here is the country's last observed completion - "
            "the one-shot task has no within-row history",
            "constant global_rate scores carry no ranking information; its "
            "AUC is reported null, not zero",
            "the full model (harness runner baseline) is quoted beside these "
            "references when its job exists; it is not computed here",
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
