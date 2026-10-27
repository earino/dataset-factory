#!/usr/bin/env python3
"""Simple references for the accepted `unhcr-refugee-data-finder` artifact.

Runs ONLY after the qualification gate has passed and --accept has re-verified
the report against these exact bytes. It reads the written CSVs, never
rewrites them, and computes every reference on the SAME eval rows.

What is measured, and why in this shape
---------------------------------------
The task is a corridor-year doubling exceedance at an annual publication-lag
instant. The baseline triad's members, each estimated ONLY from training-era
rows and evaluated against THIS split's labels:

  * persistence (the most recent observed analogue) - the corridor's own
    momentum observed at the instant: log_growth_d as the ranking score
    (did the corridor already surge into year D?), plus its binary form
    surged_recently. A doubling-forecast model must improve on this.
  * calendar_identity - train-estimated positive rate per corridor
    (origin, asylum), falling back to per-origin, then to the global train
    rate: tests whether corridor identity alone carries the signal.
  * origin_year_prior - train-estimated rate per (origin, target-year
    decade-half)... superseded: target years in eval are unseen in train, so
    the honest calendar prior is per-origin recent-era rate (last three train
    label-years), carried as recent_rate.
  * majority_class - majority fitted on train, measured against THIS split's
    labels; global_rate - constant train rate (AUC null: no ranking
    information).

The full model is NOT computed here: the harness runner's baseline job trains
and evaluates it on these same rows, and its figure is quoted beside these
references when it exists. Nothing in this file may run before acceptance.

Eval-only: the holdout is sealed until the design is frozen and the runner
evaluates it once. Per-label-year reporting is mandatory - the eval window
spans 2017-2021 and surge years move prevalence, so a pooled number hides
structure.

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

NAME = "unhcr-refugee-data-finder"
TARGET = "doubled"
POSITIVE = "1"
BOOTSTRAP = 1000
SEED = 23


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
        left = auc(boot_labels, [scores_a[i] for i in indices])
        right = auc(boot_labels, [scores_b[i] for i in indices])
        if left is not None and right is not None:
            samples.append(left - right)
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
            "note": "paired row bootstrap on identical eval rows; an interval "
                    "containing zero is an inconclusive difference, not parity"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--accepted-report", required=True,
                        help="qualification report whose artifact digest this evidence binds to")
    args = parser.parse_args()

    accepted = json.loads(Path(args.accepted_report).read_text())
    if not accepted.get("ok"):
        print("REFUSING TO SCORE: the accepted report did not pass")
        return 1

    data = Path(args.data)
    train = read_rows(data / "public" / "train.csv")
    eval_rows = read_rows(data / "public" / "eval.csv")
    train_labels = labels_of(train)
    eval_labels = labels_of(eval_rows)
    train_rate = sum(train_labels) / len(train_labels) if train_labels else 0.0

    # ---- train-fitted priors (training rows only) -------------------------
    corridor_stats: dict[tuple, list] = defaultdict(lambda: [0, 0])
    origin_stats: dict[str, list] = defaultdict(lambda: [0, 0])
    for row, label in zip(train, train_labels):
        entry = corridor_stats[(row["origin"], row["asylum"])]
        entry[0] += label
        entry[1] += 1
        entry = origin_stats[row["origin"]]
        entry[0] += label
        entry[1] += 1
    corridor_rate = {k: v[0] / v[1] for k, v in corridor_stats.items() if v[1]}
    origin_rate = {k: v[0] / v[1] for k, v in origin_stats.items() if v[1]}

    def calendar_identity_score(row: dict) -> float:
        if (row["origin"], row["asylum"]) in corridor_rate:
            return corridor_rate[(row["origin"], row["asylum"])]
        if row["origin"] in origin_rate:
            return origin_rate[row["origin"]]
        return train_rate

    calendar_scores = [calendar_identity_score(row) for row in eval_rows]

    # recent-era constant: train rate over the last three train label-years
    train_years = sorted({int(row["target_year"]) for row in train})
    recent_years = set(train_years[-3:])
    recent_labels = [label for row, label in zip(train, train_labels)
                    if int(row["target_year"]) in recent_years]
    recent_rate = (sum(recent_labels) / len(recent_labels)) if recent_labels else train_rate

    # persistence: the corridor's own momentum observed at the instant
    momentum_scores = [float(row["log_growth_d"]) for row in eval_rows]
    surged_scores = [float(row["surged_recently"]) for row in eval_rows]
    constant_scores = [train_rate] * len(eval_rows)
    majority = 1 if train_rate >= 0.5 else 0

    momentum_auc = auc(eval_labels, momentum_scores)
    surged_auc = auc(eval_labels, surged_scores)
    calendar_auc = auc(eval_labels, calendar_scores)

    references = {
        "name": NAME,
        "stage": "post-acceptance simple references (eval only, train-fitted)",
        "artifact": {"accepted_report_ok": accepted.get("ok"),
                     "artifact_sha256": (accepted.get("artifact") or {}).get("sha256"),
                     "gate_version": accepted.get("gate_version")},
        "rows": len(eval_rows),
        "positives": sum(eval_labels),
        "train_positive_rate": round(train_rate, 6),
        "recent_train_label_years": sorted(recent_years),
        "references": {
            "persistence_momentum": {
                "applicable": True,
                "definition": "score = log_growth_d = ln(apps_d+1)-ln(apps_d1+1), "
                              "the corridor's own last-step growth observed at "
                              "the instant (the most recent observed analogue)",
                "auc": None if momentum_auc is None else round(momentum_auc, 6),
                "brier": None,
                "note": "rank reference; Brier needs calibrated probabilities "
                        "which a growth score is not"},
            "persistence_surge_flag": {
                "applicable": True,
                "definition": "score = surged_recently = apps_d >= 2 x apps_d1: "
                              "did the corridor already double into year D?",
                "auc": None if surged_auc is None else round(surged_auc, 6),
                "brier": round(brier(eval_labels, surged_scores) or 0.0, 6),
            },
            "calendar_identity": {
                "applicable": True,
                "definition": "train-estimated positive rate per (origin, asylum) "
                              "corridor, per-origin fallback, global train-rate "
                              "fallback; identity-only prior from training rows",
                "auc": None if calendar_auc is None else round(calendar_auc, 6),
                "brier": round(brier(eval_labels, calendar_scores) or 0.0, 6),
                "coverage": {
                    "corridor_known": sum(1 for row in eval_rows
                                          if (row["origin"], row["asylum"]) in corridor_rate),
                    "origin_fallback": sum(1 for row in eval_rows
                                            if (row["origin"], row["asylum"]) not in corridor_rate
                                            and row["origin"] in origin_rate),
                    "global_fallback": sum(1 for row in eval_rows
                                            if (row["origin"], row["asylum"]) not in corridor_rate
                                            and row["origin"] not in origin_rate),
                },
            },
            "recent_rate": {
                "applicable": True,
                "definition": f"constant train positive rate over the last three "
                              f"train label-years {sorted(recent_years)}: the "
                              "era-drift analogue for a task with no same-entity "
                              "persistence at a longer horizon",
                "rate": round(recent_rate, 6),
                "brier": round(brier(eval_labels, [recent_rate] * len(eval_rows)) or 0.0, 6),
                "note": "constant: AUC null (no ranking information)"},
            "majority_class": {
                "applicable": True,
                "definition": "majority label fitted on train, measured against "
                              "this split's labels",
                "prediction": majority,
                "accuracy": accuracy(eval_labels, [majority] * len(eval_rows)),
                "note": "constant: AUC null (no ranking information)"},
            "global_rate": {
                "applicable": True,
                "definition": "constant train positive rate",
                "rate": round(train_rate, 6),
                "brier": round(brier(eval_labels, constant_scores) or 0.0, 6),
                "note": "constant: AUC null (no ranking information)"},
        },
        "comparisons": {
            "momentum_vs_calendar_identity": paired_bootstrap_difference(
                eval_labels, momentum_scores, calendar_scores),
            "surge_flag_vs_calendar_identity": paired_bootstrap_difference(
                eval_labels, surged_scores, calendar_scores),
        },
        "per_label_year": {},
        "interpretation_note": (
            "one weak or strong reference does not establish the task's "
            "usefulness or impossibility; the full model is the harness "
            "runner's job and its figure is quoted beside these when it "
            "exists. The holdout is sealed until the design is frozen."),
    }

    # per-label-year texture: rows, positives, and each ranking reference's AUC
    by_year: dict[int, list] = defaultdict(list)
    for row, label in zip(eval_rows, eval_labels):
        by_year[int(row["target_year"])].append(label)
    for year in sorted(by_year):
        labels = by_year[year]
        mask = [i for i, row in enumerate(eval_rows) if int(row["target_year"]) == year]
        references["per_label_year"][year] = {
            "rows": len(labels),
            "positives": sum(labels),
            "positive_rate": round(sum(labels) / len(labels), 6) if labels else None,
            "momentum_auc": auc(labels, [momentum_scores[i] for i in mask]),
            "surge_flag_auc": auc(labels, [surged_scores[i] for i in mask]),
            "calendar_identity_auc": auc(labels, [calendar_scores[i] for i in mask]),
        }

    Path(args.report).write_text(json.dumps(references, indent=1) + "\n")
    print(json.dumps({
        "rows": references["rows"],
        "positives": references["positives"],
        "momentum_auc": references["references"]["persistence_momentum"]["auc"],
        "surge_flag_auc": references["references"]["persistence_surge_flag"]["auc"],
        "calendar_identity_auc": references["references"]["calendar_identity"]["auc"],
        "comparisons": references["comparisons"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
