#!/usr/bin/env python3
"""Pre-registered reference triad for ab-wildfire-ia-escape (post-acceptance only).

run.sh runs this AFTER the qualification gate passes and the exact bytes are
accepted. It reads public/train.csv and public/eval.csv and NEVER opens
private/holdout.csv - the holdout stays sealed.

References, fixed before any score was seen (no re-tuning after results):

1. majority-class accuracy: the constant train-majority label, agreement with
   the evaluated split's labels. A constant score has no ranking information.
2. persistence analogue (in-instant state): score = assessment_hectares, the
   fire's own observed size at the prediction instant. Event-grain data has no
   per-entity history to persist, so the closest honest reading of "the most
   recent observed value" is the observed state of the quantity the label
   thresholds (final area burned >= 100 ha).
3. calendar/identity-only: smoothed P(escape | month, forest_area) estimated
   from TRAIN rows only, with fallback to month, then to the global train rate.
   Tests that particular seasonal/geographic reference.
4. full-feature simple model: L2-regularized logistic regression on every
   shipped feature (one-hot categoricals, rare levels pooled, numerics
   median-imputed from train with missing indicators, standardized by train
   statistics), fit on train only. A simple linear reference, not a tuned
   model; the benchmark's evaluated agents build their own.

Uncertainty: paired differences on identical eval rows with a day-cluster
bootstrap (cluster = assessment_date, the declared independence scale),
500 resamples, percentile intervals. An interval containing zero is reported
as an inconclusive difference, never as parity.

Outputs /output/references-<name>.json with every measured figure, the
provenance of the accepted artifact, and explicit degenerate-control notes.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

NAME = "ab-wildfire-ia-escape"
TARGET = "escape"
ID_COLUMN = "fire_id"
TIME_COLUMN = "assessment_ts"
CLUSTER_COLUMN = "assessment_date"
CATEGORICAL = ["day_of_week", "month", "forest_area", "fire_type", "fire_position_on_slope",
               "weather_conditions_over_fire", "wind_direction", "fuel_type",
               "detection_agent_type"]
NUMERIC = ["assessment_hectares", "fire_spread_rate", "temperature", "relative_humidity",
           "wind_speed", "latitude", "longitude", "hours_report_to_assessment",
           "hours_discovery_to_assessment", "hours_start_to_assessment", "doy_sin", "doy_cos"]
MISSING_POSSIBLE = ["fire_spread_rate", "temperature", "relative_humidity", "wind_speed",
                    "hours_discovery_to_assessment", "hours_start_to_assessment"]
POOL_MIN = 30          # one-hot levels below this train support pool into OTHER
EPOCHS = 220
LEARNING_RATE = 0.3
L2_PENALTY = 1e-4
BOOTSTRAP_RESAMPLES = 500


def read_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def auc(labels, scores):
    """Rank AUC with average ranks for ties."""
    pairs = sorted(zip(scores, labels), key=lambda p: p[0])
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    rank_sum = 0.0
    index = 0
    while index < len(pairs):
        stop = index
        while stop + 1 < len(pairs) and pairs[stop + 1][0] == pairs[index][0]:
            stop += 1
        average = (index + stop) / 2.0 + 1.0      # average of ranks index+1 .. stop+1
        positives = sum(1 for k in range(index, stop + 1) if pairs[k][1])
        rank_sum += positives * average
        index = stop + 1
    return (rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def brier(labels, scores):
    if not labels:
        return None
    return sum((s - y) ** 2 for s, y in zip(scores, labels)) / len(labels)


def fnum_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fit_calendar(train_rows):
    """Smoothed P(escape | month, forest_area) with fallbacks, from train only."""
    cell = defaultdict(lambda: [0, 0])       # (month, area) -> [positives, rows]
    month = defaultdict(lambda: [0, 0])
    total = [0, 0]
    for row in train_rows:
        label = int(row[TARGET] == "1")
        cell[(row["month"], row["forest_area"])][0] += label
        cell[(row["month"], row["forest_area"])][1] += 1
        month[row["month"]][0] += label
        month[row["month"]][1] += 1
        total[0] += label
        total[1] += 1
    base = total[0] / total[1]
    prior_strength = 20.0

    def smoothed(entry):
        return (entry[0] + prior_strength * base) / (entry[1] + prior_strength)

    def score_row(row):
        entry = cell.get((row["month"], row["forest_area"]))
        if entry and entry[1] >= 10:
            return smoothed(entry)
        entry = month.get(row["month"])
        if entry and entry[1] >= 10:
            return smoothed(entry)
        return base

    return score_row


def design_matrix(rows, levels, medians, means, stds):
    """One-hot (pooled rare levels) + standardized numerics + missing indicators."""
    matrix = []
    for row in rows:
        features = []
        for column in CATEGORICAL:
            value = row[column]
            for level in levels[column]:
                features.append(1.0 if value == level else 0.0)
        for column in NUMERIC:
            value = fnum_or_none(row[column])
            if value is None:
                features.append((medians[column] - means[column]) / stds[column])
            else:
                features.append((value - means[column]) / stds[column])
        for column in MISSING_POSSIBLE:
            features.append(0.0 if fnum_or_none(row[column]) is not None else 1.0)
        features.append(1.0)                       # intercept
        matrix.append(features)
    return matrix


def fit_logistic(matrix, labels, epochs=EPOCHS, lr=LEARNING_RATE, l2=L2_PENALTY):
    weights = [0.0] * len(matrix[0])
    for _ in range(epochs):
        gradient = [l2 * w for w in weights]
        gradient[-1] = 0.0                          # no penalty on the intercept
        for features, label in zip(matrix, labels):
            z = sum(w * x for w, x in zip(weights, features))
            if z >= 0:
                p = 1.0 / (1.0 + math.exp(-z)) if z < 35 else 1.0
            else:
                ez = math.exp(z) if z > -35 else 0.0
                p = ez / (1.0 + ez)
            error = p - label
            for index, x in enumerate(features):
                gradient[index] += error * x
        scale = lr / len(labels)
        weights = [w - scale * g for w, g in zip(weights, gradient)]
    return weights


def predict(weights, matrix):
    scores = []
    for features in matrix:
        z = sum(w * x for w, x in zip(weights, features))
        scores.append(1.0 / (1.0 + math.exp(-z)) if -35 < z < 35 else (1.0 if z >= 35 else 0.0))
    return scores


def bootstrap_diff(labels, score_a, score_b, clusters, resamples=BOOTSTRAP_RESAMPLES):
    """Day-cluster bootstrap of paired AUC differences (a - b), percentile CI.

    Deterministic: a fixed-seed LCG chooses clusters with replacement, so the
    reported interval is reproducible from the artifact alone.
    """
    by_cluster = defaultdict(list)
    for label, a, b, cluster in zip(labels, score_a, score_b, clusters):
        by_cluster[cluster].append((label, a, b))
    keys = sorted(by_cluster)
    diffs = []
    seed = 12345
    for _ in range(resamples):
        seed = (seed * 1103515245 + 12345) % (2 ** 31)
        sampled = []
        for _ in range(len(keys)):
            seed = (seed * 1103515245 + 12345) % (2 ** 31)
            sampled.extend(by_cluster[keys[seed % len(keys)]])
        rows = sampled
        lab = [r[0] for r in rows]
        auc_a = auc(lab, [r[1] for r in rows])
        auc_b = auc(lab, [r[2] for r in rows])
        if auc_a is None or auc_b is None:
            continue
        diffs.append(auc_a - auc_b)
    if not diffs:
        return None
    diffs.sort()
    low = diffs[min(int(0.025 * len(diffs)), len(diffs) - 1)]
    high = diffs[min(int(0.975 * len(diffs)), len(diffs) - 1)]
    median = diffs[len(diffs) // 2]
    return {"resamples": len(diffs), "ci_low": round(low, 4), "ci_high": round(high, 4),
            "median": round(median, 4)}


def main() -> int:
    parser = argparse.ArgumentParser(description="reference triad, post-acceptance only")
    parser.add_argument("--data", required=True)
    parser.add_argument("--accepted-report", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    data = Path(args.data)
    report_path = Path(args.accepted_report)
    accepted = json.loads(report_path.read_text())
    if not accepted.get("ok", not accepted.get("failed_checks")):
        print(json.dumps({"ok": False, "error": "accepted report did not pass"}))
        return 1

    # Re-verify the artifact identity from the bytes on disk, exactly as the gate does.
    quality = json.loads((data / "quality.json").read_text())
    components = {}
    for split, relative in quality["splits"].items():
        path = data / relative
        components[split] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ("meta.json", "quality.json"):
        components[name] = hashlib.sha256((data / name).read_bytes()).hexdigest()
    digest = hashlib.sha256("".join(sorted(f"{k}:{v}" for k, v in components.items()))
                            .encode()).hexdigest()
    expected = accepted["artifact"]["artifact_version"]["digest"]
    if digest != expected:
        print(json.dumps({"ok": False, "error": f"artifact digest {digest} != accepted {expected}"}))
        return 1

    train_rows = read_rows(data / "public" / "train.csv")
    eval_rows = read_rows(data / "public" / "eval.csv")
    holdout_path = data / "private" / "holdout.csv"
    if holdout_path.exists():
        print(json.dumps({"ok": True, "note": "holdout exists and was NOT opened by this stage"}))

    train_labels = [int(r[TARGET] == "1") for r in train_rows]
    eval_labels = [int(r[TARGET] == "1") for r in eval_rows]
    train_rate = sum(train_labels) / len(train_labels)
    eval_rate = sum(eval_labels) / len(eval_labels)

    # 1. majority-class accuracy (train-fit constant, agreement with eval labels)
    majority = int(train_rate >= 0.5)
    majority_accuracy = sum(1 for y in eval_labels if y == majority) / len(eval_labels)

    # 2. persistence analogue: observed size at the instant
    persistence_scores = [fnum_or_none(r["assessment_hectares"]) for r in eval_rows]

    # 3. calendar/identity-only prior from train
    calendar_scorer = fit_calendar(train_rows)
    calendar_scores = [calendar_scorer(r) for r in eval_rows]

    # 4. full-feature logistic reference
    levels = {}
    for column in CATEGORICAL:
        counts = Counter(r[column] for r in train_rows)
        levels[column] = sorted(level for level, n in counts.most_common() if n >= POOL_MIN)
    medians, means, stds = {}, {}, {}
    for column in NUMERIC:
        values = [v for v in (fnum_or_none(r[column]) for r in train_rows) if v is not None]
        values.sort()
        medians[column] = values[len(values) // 2] if values else 0.0
        means[column] = sum(values) / len(values) if values else 0.0
        stds[column] = (sum((v - means[column]) ** 2 for v in values) / len(values)) ** 0.5 \
            if values else 1.0
        if stds[column] == 0.0:
            stds[column] = 1.0
    train_matrix = design_matrix(train_rows, levels, medians, means, stds)
    weights = fit_logistic(train_matrix, train_labels)
    eval_matrix = design_matrix(eval_rows, levels, medians, means, stds)
    full_scores = predict(weights, eval_matrix)

    results = {}
    for name, scores in (("majority_constant", [float(majority)] * len(eval_labels)),
                         ("persistence_assessment_hectares", persistence_scores),
                         ("calendar_identity_only", calendar_scores),
                         ("full_feature_logistic", full_scores)):
        probabilistic = name != "persistence_assessment_hectares"
        entry = {"auc": auc(eval_labels, scores),
                 "brier": brier(eval_labels, scores) if probabilistic else None}
        if not probabilistic:
            entry["brier_note"] = ("not reported: the persistence analogue is a raw size in "
                                   "hectares, not a probability; Brier is undefined for it")
        if name == "majority_constant":
            entry["accuracy_on_eval"] = majority_accuracy
            entry["note"] = ("constant score: no ranking information; the AUC is the "
                             "coin-flip null 0.5 by construction")
        results[name] = entry

    # paired differences with day-cluster bootstrap
    pairs = {
        "full_minus_persistence": (full_scores, persistence_scores),
        "full_minus_calendar": (full_scores, calendar_scores),
        "persistence_minus_calendar": (persistence_scores, calendar_scores),
    }
    clusters = [r[CLUSTER_COLUMN] for r in eval_rows]
    for name, (a, b) in pairs.items():
        observed = None
        auc_a, auc_b = auc(eval_labels, a), auc(eval_labels, b)
        if auc_a is not None and auc_b is not None:
            observed = round(auc_a - auc_b, 4)
        interval = bootstrap_diff(eval_labels, a, b, clusters)
        results[name] = {"observed_auc_difference": observed,
                         "day_cluster_bootstrap": interval,
                         "note": "identical eval rows; an interval containing zero is an "
                                 "inconclusive difference, not parity"}

    # per-year breakdown inside the eval window (structural-shift visibility)
    per_year = {}
    for year in (2016, 2017, 2018, 2019, 2020):
        rows = [r for r in eval_rows if r[TIME_COLUMN].startswith(str(year))]
        labels = [int(r[TARGET] == "1") for r in rows]
        per_year[str(year)] = {
            "rows": len(rows), "positives": sum(labels),
            "positive_rate": round(sum(labels) / len(labels), 4) if rows else None,
            "auc": {"persistence": auc(labels, [fnum_or_none(r["assessment_hectares"])
                                                for r in rows]),
                    "calendar": auc(labels, [calendar_scorer(r) for r in rows]),
                    "full": None},
        }
    # full model per year (score once per row, then slice)
    for year in per_year:
        rows = [r for r in eval_rows if r[TIME_COLUMN].startswith(year)]
        matrix = design_matrix(rows, levels, medians, means, stds)
        per_year[year]["auc"]["full"] = auc([int(r[TARGET] == "1") for r in rows],
                                            predict(weights, matrix))

    report = {
        "ok": True,
        "stage": "references",
        "candidate": NAME,
        "artifact_version": digest,
        "gate_version": accepted.get("gate_version"),
        "accepted_report": str(report_path),
        "protocol": "pre-registered: metrics (rank AUC, Brier), references (majority "
                    "constant, persistence analogue = assessment_hectares, calendar/identity "
                    "prior from train, full-feature L2 logistic), eval window 2016-2020, "
                    "day-cluster bootstrap 500 resamples - all fixed before any score was "
                    "seen; holdout never opened",
        "eval_rows": len(eval_rows),
        "train_rows": len(train_rows),
        "train_positive_rate": round(train_rate, 6),
        "eval_positive_rate": round(eval_rate, 6),
        "references": results,
        "eval_per_year": per_year,
        "full_model_note": "a simple L2 logistic reference over all shipped features "
                           "(rare levels pooled at 30 train rows, median imputation with "
                           "missing indicators, standardized by train statistics), not a "
                           "tuned model; benchmark agents build their own",
    }
    Path(args.report).write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"ok": True, "stage": "references", "artifact_version": digest,
                      "references": {k: v.get("auc") for k, v in results.items()
                                      if "auc" in v}}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
