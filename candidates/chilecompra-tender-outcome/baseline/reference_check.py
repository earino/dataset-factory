#!/usr/bin/env python3
"""Independent recomputation of the decisive comparison for the ChileCompra tender baseline.

This module is deliberately NOT the build's score.py. It is written from the runner
contract and the accepted quality.json alone, in pure standard-library Python (plus the
benchmark's own train.py, re-run through runpy to obtain the model's eval scores), so the
decisive numbers are computed twice by different code and their agreement is checkable
rather than asserted:

  * the unspsc_only bar: positive rate per UNSPSC segment fitted on the fetched train.csv
    (unseen segments fall back to the global train rate), scored on the fetched eval.csv,
    AUC by this module's own Mann-Whitney implementation (score.py has its own);
  * the model's eval AUC: train.py's predict_proba re-applied to the eval rows, AUC by
    the same implementation here, beside train.py's own sklearn print and validate.py's
    recompute;
  * the paired difference (model - bar) on the identical eval rows with TWO bootstrap
    intervals: a publication-day-clustered bootstrap (the day is the gate's declared
    independence unit: tenders published the same day share market conditions) and a
    naive row bootstrap for comparison;
  * an identity assertion that the fetched eval rows are exactly the 11,791 rows /
    1,959 positives the accepted references were measured on (a mismatch means the
    comparison is NOT on identical rows and the job must stop);
  * the outcome_conditioning rates read from the fetched quality.json, so they travel
    with the numbers (the accepted row_selection basis requires them to be quoted
    beside any score).

Runs with the materialized workdir as its working directory (train.py needs task.json
and data/ beside it). Pure stdlib so it can be smoke-tested on the coordinator against
a stub train.py before any worker spend.

Usage: reference_check.py --extract <extract-dir> --out <json> [--bootstrap N]
"""
import argparse
import csv
import json
import random
import sys
from pathlib import Path

# Identity of the rows the accepted simple references were measured on (gate-recomputed,
# record.json qualification.splits + the collected references report). A fetch that does
# not carry exactly these rows is not the artifact the bar belongs to.
EXPECTED_TRAIN_ROWS = 23188
EXPECTED_EVAL_ROWS = 11791
EXPECTED_EVAL_POSITIVES = 1959
TARGET = "deserted"
POSITIVE = "1"
BAR_COLUMN = "unspsc_segment"
DAY_COLUMN = "pub_date"  # event key; the gate reads its first 10 chars as the cluster unit


def read_rows(path: Path) -> list:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def mann_whitney_auc(labels: list, scores: list):
    """AUC from first principles: P(score(positive) > score(negative)) with ties at 0.5.

    Average ranks over tie groups (midranks), then the Mann-Whitney statistic
    normalized by pos*neg. Returns None when either class is absent.
    """
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return None
    ordered = sorted(zip(scores, labels), key=lambda pair: pair[0])
    ranks = [0.0] * len(ordered)
    index = 0
    while index < len(ordered):
        stop = index
        while stop < len(ordered) and ordered[stop][0] == ordered[index][0]:
            stop += 1
        midrank = (index + stop - 1) / 2.0 + 1.0
        for position in range(index, stop):
            ranks[position] = midrank
        index = stop
    rank_sum = sum(rank for rank, (_, label) in zip(ranks, ordered) if label == 1)
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def segment_rates(train_rows: list) -> tuple:
    """Positive rate per UNSPSC segment fitted on train, plus the train global rate."""
    counts = {}
    total = hits = 0
    for row in train_rows:
        level = row.get(BAR_COLUMN, "")
        positive = int(row[TARGET] == POSITIVE)
        bucket = counts.setdefault(level, [0, 0])
        bucket[0] += 1
        bucket[1] += positive
        total += 1
        hits += positive
    rates = {level: pair[1] / pair[0] for level, pair in counts.items() if pair[0]}
    return rates, (hits / total if total else 0.0), counts


def bar_scores(eval_rows: list, rates: dict, prior: float) -> tuple:
    scores = []
    fallback = 0
    for row in eval_rows:
        level = row.get(BAR_COLUMN, "")
        if level in rates:
            scores.append(rates[level])
        else:
            scores.append(prior)
            fallback += 1
    return scores, fallback


def clustered_bootstrap(labels, model_scores, ref_scores, clusters, samples: int,
                        seed: int = 42) -> dict:
    """Paired bootstrap of AUC(model) - AUC(bar), resampling CLUSTERS (publication days).

    A resample that ends up single-class cannot carry an AUC and is skipped (counted);
    a large skip share would make the interval unreliable and is reported.
    """
    rng = random.Random(seed)
    keys = sorted(clusters)
    deltas = []
    skipped = 0
    for _ in range(samples):
        pooled_labels, pooled_model, pooled_ref = [], [], []
        for _ in range(len(keys)):
            key = keys[rng.randrange(len(keys))]
            rows = clusters[key]
            for row_index in rows:
                pooled_labels.append(labels[row_index])
                pooled_model.append(model_scores[row_index])
                pooled_ref.append(ref_scores[row_index])
        auc_model = mann_whitney_auc(pooled_labels, pooled_model)
        auc_ref = mann_whitney_auc(pooled_labels, pooled_ref)
        if auc_model is None or auc_ref is None:
            skipped += 1
            continue
        deltas.append(auc_model - auc_ref)
    if len(deltas) < 2:
        return {"ci_low": None, "ci_high": None, "resamples": len(deltas),
                "skipped": skipped, "note": "too few usable resamples"}
    deltas.sort()
    def percentile(fraction):
        position = fraction * (len(deltas) - 1)
        low = int(position)
        weight = position - low
        if low + 1 < len(deltas):
            return deltas[low] * (1 - weight) + deltas[low + 1] * weight
        return deltas[low]
    return {"mean": sum(deltas) / len(deltas),
            "ci_low": percentile(0.025), "ci_high": percentile(0.975),
            "resamples": len(deltas), "skipped": skipped}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--bootstrap", type=int, default=1000)
    # The identity defaults are the accepted artifact's own row counts; the smoke test
    # overrides them for its synthetic fixture, and run.sh never passes them, so the
    # worker is pinned to the rows the accepted bar was measured on.
    parser.add_argument("--expected-train-rows", type=int, default=EXPECTED_TRAIN_ROWS)
    parser.add_argument("--expected-eval-rows", type=int, default=EXPECTED_EVAL_ROWS)
    parser.add_argument("--expected-eval-positives", type=int, default=EXPECTED_EVAL_POSITIVES)
    args = parser.parse_args()

    extract = Path(args.extract)
    train_rows = read_rows(extract / "public" / "train.csv")
    eval_rows = read_rows(extract / "public" / "eval.csv")
    quality = json.loads((extract / "quality.json").read_text())

    # 1. Identity: the fetched rows must be exactly the rows the bar was measured on.
    eval_labels = [int(row[TARGET] == POSITIVE) for row in eval_rows]
    identity = {
        "train_rows": len(train_rows),
        "eval_rows": len(eval_rows),
        "eval_positives": sum(eval_labels),
        "expected": {"train_rows": args.expected_train_rows,
                     "eval_rows": args.expected_eval_rows,
                     "eval_positives": args.expected_eval_positives},
    }
    if (len(train_rows) != args.expected_train_rows
            or len(eval_rows) != args.expected_eval_rows
            or sum(eval_labels) != args.expected_eval_positives):
        print(json.dumps({"identity": identity, "ok": False}, indent=1))
        print("the fetched rows are not the identical rows the accepted references were "
              "measured on; refusing to compare", file=sys.stderr)
        return 2
    if train_rows[0].get(TARGET) is None or eval_rows[0].get(TARGET) is None:
        print(f"target column {TARGET!r} missing from the CSVs", file=sys.stderr)
        return 2

    # 2. The bar, recomputed independently from the fetched bytes.
    rates, prior, level_counts = segment_rates(train_rows)
    ref_scores, fallback = bar_scores(eval_rows, rates, prior)
    bar_auc = mann_whitney_auc(eval_labels, ref_scores)

    # 3. The model's eval scores, from the benchmark's own train.py re-run here.
    import runpy
    from typing import Any
    namespace: Any = runpy.run_path("train.py", run_name="__reference_check__")
    predict_proba = namespace.get("predict_proba")
    to_y = namespace.get("to_y")
    eval_frame = namespace.get("evald")
    if not callable(predict_proba) or not callable(to_y) or eval_frame is None:
        print("train.py did not expose predict_proba/to_y/evald as the contract requires",
              file=sys.stderr)
        return 3
    model_scores = [float(value) for value in predict_proba(eval_frame)]
    model_labels = [int(value) for value in to_y(eval_frame)]
    if len(model_scores) != len(eval_rows) or len(model_labels) != len(eval_rows):
        print(f"predict_proba returned {len(model_scores)} values for {len(eval_rows)} rows",
              file=sys.stderr)
        return 3
    if model_labels != eval_labels:
        print("train.py's to_y() disagrees with the gate's target/positive_label reading",
              file=sys.stderr)
        return 3
    model_auc = mann_whitney_auc(eval_labels, model_scores)

    # 4. Paired difference with a publication-day-clustered bootstrap (primary,
    #    dependence-aware: the day is the gate's independence unit) and a naive row
    #    bootstrap for comparison.
    clusters = {}
    for index, row in enumerate(eval_rows):
        clusters.setdefault(row[DAY_COLUMN][:10], []).append(index)
    cluster_boot = clustered_bootstrap(eval_labels, model_scores, ref_scores,
                                       clusters, args.bootstrap)
    row_clusters = {index: [index] for index in range(len(eval_rows))}
    row_boot = clustered_bootstrap(eval_labels, model_scores, ref_scores,
                                   row_clusters, args.bootstrap)

    result = {
        "purpose": "independent recomputation of the unspsc_only bar and the model eval "
                    "AUC from the fetched, re-accepted bytes; paired on the identical rows",
        "identity": {**identity, "ok": True},
        "bar": {
            "column": BAR_COLUMN,
            "fitted_on": "train only; unseen segment falls back to the global train rate",
            "auc": bar_auc,
            "declared_from_accepted_references": 0.5707,
            "fallback_rows": fallback,
            "levels_used": sum(1 for level in rates if any(
                row.get(BAR_COLUMN, "") == level for row in eval_rows)),
        },
        "model": {
            "auc": model_auc,
            "source": "benchmark train.py predict_proba on the eval rows, AUC by this "
                      "module's own implementation",
        },
        "paired_difference": {
            "model_minus_bar": (model_auc - bar_auc) if bar_auc is not None else None,
            "day_clustered_bootstrap": cluster_boot,
            "row_bootstrap": row_boot,
            "note": "the day-clustered interval is the primary dependence-aware measure "
                    "(publication day is the gate's independence unit); the row bootstrap "
                    "assumes independent rows and is reported for comparison only",
        },
        "outcome_conditioning": quality.get("outcome_conditioning"),
        "train_positive_rate": prior,
        "eval_positive_rate": sum(eval_labels) / len(eval_labels),
        "bootstrap_samples": args.bootstrap,
        "distinct_days": len(clusters),
    }
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({"bar_auc": bar_auc, "model_auc": model_auc,
                      "model_minus_bar": result["paired_difference"]["model_minus_bar"],
                      "day_clustered_ci": [cluster_boot.get("ci_low"),
                                           cluster_boot.get("ci_high")]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
