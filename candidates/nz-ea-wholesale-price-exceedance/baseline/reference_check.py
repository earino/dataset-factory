#!/usr/bin/env python3
"""Independent recomputation of the decisive comparison for the NZ Electricity
Authority wholesale-price baseline.

This module is deliberately NOT the build's score.py. It is written from the runner
contract and the accepted quality.json alone, in pure standard-library Python (plus
the benchmark's own train.py, re-run through runpy to obtain the model's eval
scores), so the decisive numbers are computed twice by different code and their
agreement is checkable rather than asserted:

  * persistence_value - the most recent published island daily mean (the
    last_day_mean column) as a continuous score; the strongest simple reference
    the model must beat for any headroom claim;
  * persistence_mean7 - the published 7-day trailing mean (mean_7d) as the score;
  * calendar_only - island identity plus ISO-week seasonal prior fitted on the
    fetched train.csv only: positive rate per (island, target_week), falling back
    to the global train rate on unseen weeks;
  * the model's eval AUC: train.py's predict_proba re-applied to the eval rows,
    AUC by this module's own Mann-Whitney implementation, beside train.py's own
    sklearn print and validate.py's recompute;
  * paired differences (model - reference) on the identical eval rows with a
    target_week-clustered bootstrap (target_week is the gate's declared event key:
    rows in the same target week share market conditions) and a naive row bootstrap
    for comparison;
  * an identity assertion that the fetched eval rows are exactly the 4,992 rows /
    2,150 positives the accepted references were measured on, and an agreement
    assertion that every recomputed reference matches its accepted value (a
    mismatch means the comparison basis is broken and the job must stop);
  * per-target-year AUCs (model and persistence) because the eval window spans
    2016-2022 and pooled numbers hide structural change;
  * the majority-class accuracy measured against THIS split's labels.

Runs with the materialized workdir as its working directory (train.py needs
task.json and data/ beside it). Pure stdlib so it can be smoke-tested on the
coordinator against a stub train.py before any worker spend.

Usage: reference_check.py --extract <extract-dir> --out <json> [--bootstrap N]
"""
import argparse
import csv
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

# Identity of the rows the accepted simple references were measured on (gate-recomputed,
# qualification report splits.non_empty + the collected references report). A fetch that
# does not carry exactly these rows is not the artifact the references belong to.
EXPECTED_TRAIN_ROWS = 14004
EXPECTED_TRAIN_POSITIVES = 2789
EXPECTED_EVAL_ROWS = 4992
EXPECTED_EVAL_POSITIVES = 2150
TARGET = "target_high_price"
POSITIVE = "1"
PERSISTENCE_COLUMN = "last_day_mean"
MEAN7_COLUMN = "mean_7d"
ISLAND_COLUMN = "island"
WEEK_COLUMN = "target_week"    # the gate's declared event key (clustered independence unit)
ANCHOR_COLUMN = "anchor_date"  # the anchor trading day D; target day = D + 7
HORIZON_DAYS = 7
# The accepted references report (staging release 422246241, references asset
# 4b3496d38c6ab7c9...) measured these AUCs on those rows with the build's score.py.
ACCEPTED_PERSISTENCE_VALUE_AUC = 0.8820357429258793
ACCEPTED_PERSISTENCE_MEAN7_AUC = 0.884293406215734
ACCEPTED_CALENDAR_ONLY_AUC = 0.5010555946516537
BAR_TOLERANCE = 1e-6  # same rows, same definitions, different implementation: must agree


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


def calendar_prior(train_rows: list):
    """Positive rate per (island, target_week) fitted on train, plus the train global rate."""
    buckets = {}
    total = hits = 0
    for row in train_rows:
        key = (row[ISLAND_COLUMN], row[WEEK_COLUMN])
        positive = int(row[TARGET] == POSITIVE)
        bucket = buckets.setdefault(key, [0, 0])
        bucket[0] += 1
        bucket[1] += positive
        total += 1
        hits += positive
    rates = {key: pair[1] / pair[0] for key, pair in buckets.items() if pair[0]}
    return rates, (hits / total if total else 0.0)


def clustered_bootstrap(labels, model_scores, ref_scores, clusters, samples: int,
                        seed: int = 42) -> dict:
    """Paired bootstrap of AUC(model) - AUC(reference), resampling CLUSTERS.

    Clusters are target weeks (the gate's event key) by default; the smoke test also
    passes one-row clusters (the naive row bootstrap, reported for comparison only).
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
            for row_index in clusters[key]:
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
    # The identity and agreement defaults pin the worker to the accepted artifact's
    # own rows and the accepted references; the smoke test overrides them for its
    # synthetic fixture, and run.sh never passes them.
    parser.add_argument("--expected-train-rows", type=int, default=EXPECTED_TRAIN_ROWS)
    parser.add_argument("--expected-train-positives", type=int, default=EXPECTED_TRAIN_POSITIVES)
    parser.add_argument("--expected-eval-rows", type=int, default=EXPECTED_EVAL_ROWS)
    parser.add_argument("--expected-eval-positives", type=int, default=EXPECTED_EVAL_POSITIVES)
    parser.add_argument("--accepted-persistence-value", type=float,
                        default=ACCEPTED_PERSISTENCE_VALUE_AUC)
    parser.add_argument("--accepted-persistence-mean7", type=float,
                        default=ACCEPTED_PERSISTENCE_MEAN7_AUC)
    parser.add_argument("--accepted-calendar-only", type=float,
                        default=ACCEPTED_CALENDAR_ONLY_AUC)
    args = parser.parse_args()

    extract = Path(args.extract)
    train_rows = read_rows(extract / "public" / "train.csv")
    eval_rows = read_rows(extract / "public" / "eval.csv")

    # 1. Identity: the fetched rows must be exactly the rows the references were
    #    measured on.
    train_labels = [int(row[TARGET] == POSITIVE) for row in train_rows]
    eval_labels = [int(row[TARGET] == POSITIVE) for row in eval_rows]
    identity = {
        "train_rows": len(train_rows),
        "train_positives": sum(train_labels),
        "eval_rows": len(eval_rows),
        "eval_positives": sum(eval_labels),
        "expected": {"train_rows": args.expected_train_rows,
                     "train_positives": args.expected_train_positives,
                     "eval_rows": args.expected_eval_rows,
                     "eval_positives": args.expected_eval_positives},
    }
    if (len(train_rows) != args.expected_train_rows
            or sum(train_labels) != args.expected_train_positives
            or len(eval_rows) != args.expected_eval_rows
            or sum(eval_labels) != args.expected_eval_positives):
        print(json.dumps({"identity": identity, "ok": False}, indent=1))
        print("the fetched rows are not the identical rows the accepted references were "
              "measured on; refusing to compare", file=sys.stderr)
        return 2

    # 2. The three references, recomputed independently from the fetched bytes.
    persistence_scores = [float(row[PERSISTENCE_COLUMN]) for row in eval_rows]
    mean7_scores = [float(row[MEAN7_COLUMN]) for row in eval_rows]
    week_rates, train_rate = calendar_prior(train_rows)
    calendar_scores, calendar_fallback = [], 0
    for row in eval_rows:
        key = (row[ISLAND_COLUMN], row[WEEK_COLUMN])
        if key in week_rates:
            calendar_scores.append(week_rates[key])
        else:
            calendar_scores.append(train_rate)
            calendar_fallback += 1
    persistence_auc = mann_whitney_auc(eval_labels, persistence_scores)
    mean7_auc = mann_whitney_auc(eval_labels, mean7_scores)
    calendar_auc = mann_whitney_auc(eval_labels, calendar_scores)

    agreement = {
        "persistence_value": {
            "recomputed": persistence_auc,
            "accepted": args.accepted_persistence_value,
            "ok": persistence_auc is not None
                  and abs(persistence_auc - args.accepted_persistence_value) <= BAR_TOLERANCE,
        },
        "persistence_mean7": {
            "recomputed": mean7_auc,
            "accepted": args.accepted_persistence_mean7,
            "ok": mean7_auc is not None
                  and abs(mean7_auc - args.accepted_persistence_mean7) <= BAR_TOLERANCE,
        },
        "calendar_only": {
            "recomputed": calendar_auc,
            "accepted": args.accepted_calendar_only,
            "ok": calendar_auc is not None
                  and abs(calendar_auc - args.accepted_calendar_only) <= BAR_TOLERANCE,
        },
    }
    if not all(entry["ok"] for entry in agreement.values()):
        print(json.dumps({"agreement": agreement}, indent=1))
        print("a recomputed reference disagrees with its accepted value; the comparison "
              "basis is broken, refusing to proceed", file=sys.stderr)
        return 4

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

    # 4. Paired differences with a target_week-clustered bootstrap (primary,
    #    dependence-aware: target_week is the gate's independence unit) and a naive
    #    row bootstrap for comparison. The persistence references are the decisive
    #    comparators; the calendar difference is reported observed-only.
    week_clusters = {}
    for index, row in enumerate(eval_rows):
        week_clusters.setdefault(row[WEEK_COLUMN], []).append(index)
    row_clusters = {index: [index] for index in range(len(eval_rows))}

    differences = {}
    for name, ref_scores, ref_auc in (
            ("model_minus_persistence_value", persistence_scores, persistence_auc),
            ("model_minus_persistence_mean7", mean7_scores, mean7_auc)):
        differences[name] = {
            "observed_difference": (model_auc - ref_auc)
                if model_auc is not None and ref_auc is not None else None,
            "week_clustered_bootstrap": clustered_bootstrap(
                eval_labels, model_scores, ref_scores, week_clusters, args.bootstrap),
            "row_bootstrap": clustered_bootstrap(
                eval_labels, model_scores, ref_scores, row_clusters, args.bootstrap),
        }
    differences["model_minus_calendar_only"] = {
        "observed_difference": (model_auc - calendar_auc) if model_auc is not None
                               and calendar_auc is not None else None,
        "note": "observed difference only; the calendar reference is not the decisive "
                "comparator, so no interval is spent on it",
    }

    # 5. Per-target-year AUCs (mandatory: the eval window spans 2016-2022 and pooled
    #    numbers hide structural change). Target year = anchor day + 7 days, matching
    #    the build's score.py definition.
    per_year = {}
    for index, row in enumerate(eval_rows):
        target_year = (date.fromisoformat(row[ANCHOR_COLUMN])
                       + timedelta(days=HORIZON_DAYS)).year
        entry = per_year.setdefault(str(target_year),
                                    {"labels": [], "model": [], "persistence": []})
        entry["labels"].append(eval_labels[index])
        entry["model"].append(model_scores[index])
        entry["persistence"].append(persistence_scores[index])
    per_year_out = {}
    for year, entry in sorted(per_year.items()):
        per_year_out[year] = {
            "rows": len(entry["labels"]),
            "positives": sum(entry["labels"]),
            "model_auc": mann_whitney_auc(entry["labels"], entry["model"]),
            "persistence_value_auc": mann_whitney_auc(entry["labels"], entry["persistence"]),
        }

    majority = int(train_rate >= 0.5)
    result = {
        "purpose": "independent recomputation of the accepted references and the model "
                   "eval AUC from the fetched, re-accepted bytes; paired on the "
                   "identical rows",
        "identity": {**identity, "ok": True},
        "references": {
            "persistence_value": {
                "column": PERSISTENCE_COLUMN,
                "definition": "score = last_day_mean, the most recent published island "
                              "daily mean (day D)",
                "auc": persistence_auc,
            },
            "persistence_mean7": {
                "column": MEAN7_COLUMN,
                "definition": "score = mean_7d, the published 7-day trailing mean",
                "auc": mean7_auc,
            },
            "calendar_only": {
                "definition": "train-fitted positive rate per (island, target_week), "
                              "global train rate fallback",
                "auc": calendar_auc,
                "fallback_rows": calendar_fallback,
            },
        },
        "agreement_with_accepted": agreement,
        "model": {
            "auc": model_auc,
            "source": "benchmark train.py predict_proba on the eval rows, AUC by this "
                      "module's own implementation",
        },
        "paired_differences": differences,
        "majority_class": {
            "majority": majority,
            "definition": "majority = int(train_positive_rate >= 0.5); accuracy measured "
                          "against THIS split's labels",
            "accuracy": sum(1 for label in eval_labels if label == majority) / len(eval_labels),
        },
        "per_target_year": per_year_out,
        "train_positive_rate": train_rate,
        "eval_positive_rate": sum(eval_labels) / len(eval_labels),
        "bootstrap_samples": args.bootstrap,
        "distinct_target_weeks": len(week_clusters),
        "note": "the week-clustered interval is the primary dependence-aware measure "
                "(target_week is the gate's declared event key); the row bootstrap "
                "assumes independent rows and is reported for comparison only. An "
                "interval containing zero is an inconclusive difference, not parity.",
    }
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({"persistence_value_auc": persistence_auc,
                      "persistence_mean7_auc": mean7_auc,
                      "calendar_only_auc": calendar_auc,
                      "model_auc": model_auc,
                      "model_minus_persistence_mean7":
                          differences["model_minus_persistence_mean7"]["observed_difference"],
                      "week_clustered_ci": [differences["model_minus_persistence_mean7"]
                                            ["week_clustered_bootstrap"].get("ci_low"),
                                            differences["model_minus_persistence_mean7"]
                                            ["week_clustered_bootstrap"].get("ci_high")]},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
