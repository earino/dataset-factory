#!/usr/bin/env python3
"""Simple references for the accepted `nz-ea-wholesale-price-exceedance` artifact.

Runs ONLY after the qualification gate has passed and `--accept` has
re-verified the report against these exact bytes. It reads the written CSVs,
never rewrites them, and computes every reference on the SAME eval rows.

What is measured, and why in this shape
---------------------------------------
The task is a 7-day-ahead exceedance forecast from published price history, so
the baseline triad's first two members are directly implementable:

  * persistence_value - the most recent published island daily mean (day D,
                       the last feature day) as a continuous score.
  * persistence_mean7 - the published 7-day trailing mean as the score.
  * calendar_only    - island identity plus cyclical week-of-year with a
                       seasonal prior estimated ONLY from training-era rows:
                       the train positive rate per (island, target ISO week),
                       falling back to the train global rate on unseen weeks.
  * majority_class   - majority = int(train_positive_rate >= 0.5); accuracy is
                       measured against THIS split's labels, never the
                       training prevalence.
  * global_rate      - constant train positive rate; AUC reported null because
                       a constant carries no ranking information.

The full model is NOT computed here: the harness runner's baseline job trains
and evaluates it on these same rows, and its figure is quoted next to these
references when it exists. Nothing in this file may run before acceptance.

Uncertainty: paired bootstrap differences (1000 resamples, fixed seed) on the
identical eval rows - never overlapping marginal intervals. An interval
containing zero is reported as an inconclusive difference, not parity.

Per-year reporting is mandatory for this artifact: the eval window spans
2016-2022 and the holdout sits in the post-2022-11 real-time pricing regime,
so pooled numbers hide structural change. Eval-only here; the holdout is
sealed until the design is frozen and the runner evaluates it once.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

NAME = "nz-ea-wholesale-price-exceedance"
TARGET = "target_high_price"
POSITIVE = "1"
THRESHOLD = 100.0
BOOTSTRAP = 1000
SEED = 13


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
    pairs = sorted(zip(scores, labels), key=lambda pair: pair[0])
    ranks = [0.0] * len(pairs)
    i = 0
    while i < len(pairs):
        j = i
        while j + 1 < len(pairs) and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        average = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[k] = average
        i = j + 1
    positive_rank_sum = sum(rank for rank, (_score, label) in zip(ranks, pairs) if label)
    return (positive_rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def brier(labels: list[int], probabilities: list[float]) -> float | None:
    if not labels:
        return None
    return sum((p - y) ** 2 for y, p in zip(labels, probabilities)) / len(labels)


def accuracy(labels: list[int], predictions: list[int]) -> float | None:
    if not labels:
        return None
    return sum(1 for y, p in zip(labels, predictions) if y == p) / len(labels)


def paired_bootstrap_difference(labels: list[int], scores_a: list[float],
                                scores_b: list[float]) -> dict:
    """Bootstrap the AUC difference (a - b) on identical rows, resampling rows."""
    auc_a = auc(labels, scores_a)
    auc_b = auc(labels, scores_b)
    if auc_a is None or auc_b is None:
        return {"observed_difference": None, "auc_a": auc_a, "auc_b": auc_b,
                "ci95": None, "note": "one reference has a single class on this split"}
    difference = auc_a - auc_b
    rng = random.Random(SEED)
    n = len(labels)
    samples = []
    for _ in range(BOOTSTRAP):
        indices = [rng.randrange(n) for _ in range(n)]
        boot_labels = [labels[i] for i in indices]
        value = (auc(boot_labels, [scores_a[i] for i in indices])
                 - auc(boot_labels, [scores_b[i] for i in indices]))
        if value is not None:
            samples.append(value)
    samples.sort()
    if len(samples) < 100:
        return {"observed_difference": round(difference, 6), "auc_a": round(auc_a, 6),
                "auc_b": round(auc_b, 6), "ci95": None,
                "note": "too few bootstrap samples with both classes"}
    low = samples[int(0.025 * len(samples))]
    high = samples[int(0.975 * len(samples)) - 1]
    return {"observed_difference": round(difference, 6), "auc_a": round(auc_a, 6),
            "auc_b": round(auc_b, 6), "ci95": [round(low, 6), round(high, 6)],
            "bootstrap_samples": len(samples),
            "note": "paired row bootstrap on identical eval rows; an interval containing "
                    "zero is an inconclusive difference, not parity"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--accepted-report", default=None,
                        help="qualification report whose artifact digest this evidence binds to")
    args = parser.parse_args()

    data = Path(args.data)
    train = read_rows(data / "public" / "train.csv")
    eval_rows = read_rows(data / "public" / "eval.csv")
    train_labels = labels_of(train)
    eval_labels = labels_of(eval_rows)
    train_rate = sum(train_labels) / len(train_labels) if train_labels else 0.0

    # calendar/identity prior fitted on TRAIN only: positive rate per (island, ISO week)
    buckets: dict[tuple, list] = defaultdict(list)
    for row, label in zip(train, train_labels):
        buckets[(row["island"], row["target_week"])].append(label)
    week_rate = {key: sum(values) / len(values) for key, values in buckets.items()}
    global_rate = train_rate

    def calendar_score(row: dict) -> float:
        key = (row["island"], row["target_week"])
        return week_rate.get(key, global_rate)

    persistence_scores = [float(row["last_day_mean"]) for row in eval_rows]
    persistence7_scores = [float(row["mean_7d"]) for row in eval_rows]
    calendar_scores = [calendar_score(row) for row in eval_rows]

    references = {
        "name": NAME,
        "stage": "post-acceptance simple references (eval only, train-fitted)",
        "rows": len(eval_rows),
        "positives": sum(eval_labels),
        "train_positive_rate": round(train_rate, 6),
        "references": {
            "persistence_value": {
                "definition": "score = last_day_mean, the most recent published island "
                              "daily mean (day D)",
                "auc": auc(eval_labels, persistence_scores),
                "brier_binary": brier(eval_labels,
                                      [1.0 if s > THRESHOLD else 0.0
                                       for s in persistence_scores]),
                "accuracy_binary": accuracy(eval_labels,
                                            [1 if s > THRESHOLD else 0
                                             for s in persistence_scores]),
            },
            "persistence_mean7": {
                "definition": "score = mean_7d, the published 7-day trailing mean",
                "auc": auc(eval_labels, persistence7_scores),
                "brier_binary": brier(eval_labels,
                                      [1.0 if s > THRESHOLD else 0.0
                                       for s in persistence7_scores]),
            },
            "calendar_only": {
                "definition": "train-fitted positive rate per (island, target ISO week), "
                              "global train rate fallback - identity plus seasonal prior, "
                              "no price information",
                "auc": auc(eval_labels, calendar_scores),
                "brier": brier(eval_labels, calendar_scores),
            },
            "majority_class": {
                "definition": "majority = int(train_positive_rate >= 0.5), measured "
                              "against THIS split's labels",
                "accuracy": accuracy(eval_labels,
                                     [1 if train_rate >= 0.5 else 0] * len(eval_labels)),
            },
            "global_rate": {
                "definition": "constant train positive rate; no ranking information",
                "auc": None,
                "brier": brier(eval_labels, [train_rate] * len(eval_labels)),
            },
        },
        "full_model": ("NOT computed at this stage: the harness runner's baseline job "
                       "trains and evaluates the full model on these same eval rows; "
                       "quote its figure beside these references when it exists"),
        "paired_differences": {
            "persistence_value_minus_calendar_only":
                paired_bootstrap_difference(eval_labels, persistence_scores, calendar_scores),
            "persistence_value_minus_persistence_mean7":
                paired_bootstrap_difference(eval_labels, persistence_scores, persistence7_scores),
        },
    }

    # per-year reporting (mandatory: the eval window spans structural change)
    per_year: dict[str, dict] = defaultdict(lambda: {"rows": 0, "positives": 0})
    for row, label, score, cal in zip(eval_rows, eval_labels, persistence_scores,
                                     calendar_scores):
        target_year = (date.fromisoformat(row["anchor_date"])
                       + timedelta(days=7)).year
        entry = per_year[str(target_year)]
        entry["rows"] += 1
        entry["positives"] += label
        entry.setdefault("labels", []).append(label)
        entry.setdefault("persistence_scores", []).append(score)
        entry.setdefault("calendar_scores", []).append(cal)
    for year, entry in sorted(per_year.items()):
        references.setdefault("per_year", {})[year] = {
            "rows": entry["rows"],
            "positives": entry["positives"],
            "positive_rate": round(entry["positives"] / entry["rows"], 6),
            "persistence_value_auc": auc(entry["labels"], entry["persistence_scores"]),
            "calendar_only_auc": auc(entry["labels"], entry["calendar_scores"]),
        }

    if args.accepted_report:
        accepted = json.loads(Path(args.accepted_report).read_text())
        references["accepted_artifact_version"] = accepted.get("artifact_version", {}).get("digest")
        references["gate_version_of_accepted_report"] = accepted.get("gate_version")

    Path(args.report).write_text(json.dumps(references, indent=1) + "\n")
    print(json.dumps(references, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
