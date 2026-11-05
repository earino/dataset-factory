#!/usr/bin/env python3
"""Simple references for the accepted ibama-auto-infracao-recidivism artifact.

Runs ONLY after the qualification gate has passed and --accept has re-verified
the report against these exact bytes (run.sh enforces that order; this file
re-checks the accepted report and the on-disk digests before its first
metric, so an accidental early invocation refuses to score). It reads the
written CSVs, never rewrites them, and computes every reference on the SAME
eval rows. The private holdout is NEVER opened - it is the final test surface
and stays sealed (its declared meta.json positive rate is quoted as the
recorded drift, not measured here).

Reference set (every rate table is estimated ONLY from train lavratura years
2005-2015; scored on eval years 2016-2019). The candidate record pre-registered
these reference families before any score existed:

  * persistence_recency - score = -days_since_prev_auto (the entity's most
    recent enforcement contact; first-ever rows score lowest). The
    persistence-of-the-instant reading: recency of the last observed event.
  * persistence_count_365d - score = n_prior_autos_365d, the record's
    "entity's prior 12-month re-autuacao signal" named as the persistence
    reference.
  * persistence_count_rate - train-estimated positive rate by prior-12-month
    count bucket (0 / 1 / 2 / 3+), the smoothed persistence prior.
  * identity_entity_history - train-era positive rate per entity_id, global
    fallback; the record's "identity (entity auto-count history)" family: an
    infractor's own history names its propensity. Coverage against eval rows
    is recorded (entities unseen in train take the global rate).
  * identity_count_history - train-estimated rate by total prior-autos bin
    (first-time / 2 / 3-5 / 6-20 / 21+, the discovery probe's bins; measured
    2023: first-time 18.0% vs repeat 49.4%).
  * calendar_month_rate - train-estimated rate by lavratura month (the
    seasonal prior; cyclical encoding is shipped as month_sin/month_cos).
  * calendar_identity - mean of identity_entity_history and
    calendar_month_rate; the skill's calendar-identity control (entity
    identity + seasonal prior estimated from training-era rows).
  * global_rate - constant train rate (degenerate, no ranking information).
  * majority_class - fitted on train, measured against THIS split's labels.

DECIDING CHECK (pre-registered in the candidate record BEFORE this launch):
the full runner-contract model (a separate baseline job) must beat EVERY one
of these references on these identical eval rows for a headroom claim; if any
reference matches or beats the model with a cluster-aware paired bootstrap 95%
interval excluding zero on the deficit side, the verdict is "no demonstrated
headroom under this protocol" and the wb-loan/unhcr-corridor precedent applies
(drop, negative finding preserved). An interval containing zero is an
inconclusive difference, not parity. This file computes the references and
the reference-vs-reference diagnostics; the model comparison is quoted beside
them when the baseline job exists.

Positives cluster by entity (serial infrangers), so all intervals are CLUSTER
bootstrap intervals: distinct entity_id keys among eval rows are resampled
with replacement (all rows of a drawn entity travel together), 150 resamples,
fixed seed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

NAME = "ibama-auto-infracao-recidivism"
TARGET = "reautuacao_12m"
POSITIVE = "1"
SEED = 20261105
BOOTSTRAP = 150
COUNT_BUCKETS = ("0", "1", "2", "3+")


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def labels_of(rows: list[dict]) -> list[int]:
    return [1 if row[TARGET] == POSITIVE else 0 for row in rows]


def auc(labels: list[int], scores: list[float]) -> float | None:
    """Mann-Whitney AUC with tie handling; None for constant or single-class."""
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
        avg = (i + j) / 2 + 1  # 1-indexed average rank of the tie block
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    rank_sum = sum(ranks[i] for i in range(len(labels)) if labels[i])
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def brier(labels: list[int], scores: list[float]) -> float | None:
    if not labels:
        return None
    return sum((s - y) ** 2 for y, s in zip(labels, scores)) / len(labels)


def rate_table(rows: list[dict], keys: list[str]) -> tuple[dict, float]:
    stats: dict = defaultdict(lambda: [0, 0])
    for row, y in zip(rows, labels_of(rows)):
        stats[tuple(row.get(k, "") for k in keys)][y] += 1
    global_pos = sum(v[1] for v in stats.values())
    global_n = sum(v[0] + v[1] for v in stats.values())
    table = {k: v[1] / (v[0] + v[1]) for k, v in stats.items() if (v[0] + v[1])}
    return table, (global_pos / global_n if global_n else 0.5)


def count_bucket(row: dict) -> str:
    n = int(row["n_prior_autos_365d"])
    if n >= 3:
        return COUNT_BUCKETS[3]
    return COUNT_BUCKETS[n]


def history_bin(row: dict) -> str:
    n = int(row["n_prior_autos"])
    if n == 0:
        return "first_time"
    if n == 1:
        return "2nd"
    if n <= 5:
        return "3-5"
    if n <= 20:
        return "6-20"
    return "21+"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--accepted-report", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    data = Path(args.data)

    # ---- acceptance re-check: no metric exists before this passes -----------
    report = json.loads(Path(args.accepted_report).read_text())
    failed = report.get("failed_checks") or []
    if failed:
        raise SystemExit(f"refusing to score: the qualification report carries "
                         f"failed checks: {failed}")
    if report.get("ok") is not True:
        raise SystemExit("refusing to score: the qualification report did not pass")
    digest_claim = ((report.get("artifact") or {}).get("artifact_version") or {}).get("digest")
    if not digest_claim:
        raise SystemExit("refusing to score: the accepted report carries no artifact digest")
    components = ((report.get("artifact") or {}).get("artifact_version") or {}).get("components") or []
    actual = {}
    for split_rel in ("public/train.csv", "public/eval.csv", "meta.json", "quality.json"):
        actual[split_rel] = hashlib.sha256((data / split_rel).read_bytes()).hexdigest()
    claimed = {((report.get("artifact") or {}).get(k) or {}).get("sha256"): k
               for k in components
               if isinstance((report.get("artifact") or {}).get(k), dict)}
    missing = [rel for rel, dig in actual.items() if claimed.get(dig) is None]
    if missing:
        raise SystemExit(f"refusing to score: on-disk files do not match the "
                         f"accepted artifact: {missing}")

    train = read_rows(data / "public" / "train.csv")
    evald = read_rows(data / "public" / "eval.csv")
    y_eval = labels_of(evald)
    y_train = labels_of(train)
    n_eval, n_pos = len(evald), sum(y_eval)
    train_rate = sum(y_train) / len(y_train)

    # train-estimated tables (train rows only)
    entity_table, entity_global = rate_table(train, ["entity_id"])
    month_stats: dict = defaultdict(lambda: [0, 0])
    for row, y in zip(train, y_train):
        month_stats[row["lavratura_date"][:7]][y] += 1
    month_table = {k: v[1] / (v[0] + v[1]) for k, v in month_stats.items() if v[0] + v[1]}
    month_global = train_rate
    bucket_stats: dict = defaultdict(lambda: [0, 0])
    for row, y in zip(train, y_train):
        bucket_stats[count_bucket(row)][y] += 1
    bucket_table = {k: v[1] / (v[0] + v[1]) for k, v in bucket_stats.items() if v[0] + v[1]}
    bin_stats: dict = defaultdict(lambda: [0, 0])
    for row, y in zip(train, y_train):
        bin_stats[history_bin(row)][y] += 1
    bin_table = {k: v[1] / (v[0] + v[1]) for k, v in bin_stats.items() if v[0] + v[1]}

    # reference vectors over the identical eval rows
    persistence_recency = [-float(r["days_since_prev_auto"])
                           if int(r["days_since_prev_auto"]) >= 0 else -1e9
                           for r in evald]
    persistence_count = [float(r["n_prior_autos_365d"]) for r in evald]
    persistence_count_rate = [bucket_table.get(count_bucket(r), train_rate)
                              for r in evald]
    identity_entity = [entity_table.get((r["entity_id"],), entity_global)
                       for r in evald]
    identity_count = [bin_table.get(history_bin(r), train_rate) for r in evald]
    calendar_month = [month_table.get(r["lavratura_date"][:7], month_global)
                      for r in evald]
    calendar_identity = [(a + b) / 2 for a, b in zip(identity_entity, calendar_month)]

    identity_coverage = sum(1 for r in evald
                           if (r["entity_id"],) in entity_table) / len(evald)

    majority = int(train_rate >= 0.5)
    majority_accuracy = sum(1 for y in y_eval if y == majority) / len(y_eval)

    references = {
        "persistence_recency": {
            "eval_auc": auc(y_eval, persistence_recency),
            "brier": brier(y_eval, [min(max(s, 0.0), 1.0) for s in persistence_recency]),
            "note": ("score = -days_since_prev_auto (first-ever rows score "
                     "lowest); the recency-of-last-enforcement-contact "
                     "persistence reading"),
        },
        "persistence_count_365d": {
            "eval_auc": auc(y_eval, persistence_count),
            "brier": brier(y_eval, persistence_count),
            "note": ("score = n_prior_autos_365d, the record's named "
                     "persistence reference (the entity's prior 12-month "
                     "re-autuacao signal)"),
        },
        "persistence_count_rate": {
            "eval_auc": auc(y_eval, persistence_count_rate),
            "brier": brier(y_eval, persistence_count_rate),
            "note": (f"train-estimated rate by prior-12-month count bucket "
                     f"{COUNT_BUCKETS}; the smoothed persistence prior"),
        },
        "identity_entity_history": {
            "eval_auc": auc(y_eval, identity_entity),
            "brier": brier(y_eval, identity_entity),
            "eval_entity_coverage": round(identity_coverage, 6),
            "note": ("train-era positive rate per entity_id with global "
                     "fallback; the record's identity family (an infractor's "
                     "own history names its propensity)"),
        },
        "identity_count_history": {
            "eval_auc": auc(y_eval, identity_count),
            "brier": brier(y_eval, identity_count),
            "note": ("train-estimated rate by total prior-autos bin "
                     "(first_time/2nd/3-5/6-20/21+); the record's "
                     "'entity auto-count history' reference"),
        },
        "calendar_month_rate": {
            "eval_auc": auc(y_eval, calendar_month),
            "brier": brier(y_eval, calendar_month),
            "note": ("train-estimated rate by lavratura month; the seasonal "
                     "prior of the calendar-identity control"),
        },
        "calendar_identity": {
            "eval_auc": auc(y_eval, calendar_identity),
            "brier": brier(y_eval, calendar_identity),
            "note": ("mean of identity_entity_history and calendar_month_rate; "
                     "the skill's calendar-identity control (entity identity "
                     "plus seasonal prior, train-estimated only)"),
        },
        "global_rate": {
            "eval_auc": None, "brier": brier(y_eval, [train_rate] * n_eval),
            "note": "constant score, no ranking information; degenerate control",
        },
        "majority_class": {
            "accuracy_this_split": majority_accuracy,
            "note": "majority fitted on train, measured against this split's labels",
        },
    }

    # per-eval-year reporting (the structural-break check: four lavratura
    # years, one regime boundary inside eval at the 2019->2020 dip)
    per_year = {}
    for year in sorted({r["lavratura_date"][:4] for r in evald}):
        idx = [i for i, r in enumerate(evald) if r["lavratura_date"][:4] == year]
        ys = [y_eval[i] for i in idx]
        entry: dict = {"rows": len(idx), "positives": sum(ys),
                       "positive_rate": round(sum(ys) / len(ys), 6)}
        for name, vector in (("persistence_count_365d", persistence_count),
                             ("identity_entity_history", identity_entity),
                             ("calendar_identity", calendar_identity)):
            entry[f"{name}_auc"] = auc(ys, [vector[i] for i in idx])
        per_year[year] = entry

    # clusters: positives cluster by entity (serial infringers)
    clusters: dict = defaultdict(list)
    for i, row in enumerate(evald):
        clusters[row["entity_id"]].append(i)
    positive_clusters = sorted({row["entity_id"]
                                for row, y in zip(evald, y_eval) if y})

    # ---- cluster-aware paired bootstrap on identical rows ------------------
    rng = random.Random(SEED)
    cluster_keys = sorted(clusters)

    def cluster_auc_pair(vector_a, vector_b):
        a_val, b_val = auc(y_eval, vector_a), auc(y_eval, vector_b)
        observed = (a_val - b_val) if (a_val is not None and b_val is not None) else None
        diffs = []
        for _ in range(BOOTSTRAP):
            drawn = [cluster_keys[rng.randrange(len(cluster_keys))]
                     for _ in range(len(cluster_keys))]
            idx = [i for key in drawn for i in clusters[key]]
            ys = [y_eval[i] for i in idx]
            va = auc(ys, [vector_a[i] for i in idx])
            vb = auc(ys, [vector_b[i] for i in idx])
            if va is None or vb is None:
                continue
            diffs.append(va - vb)
        diffs.sort()
        if diffs:
            lo = diffs[int(0.025 * len(diffs))]
            hi = diffs[int(0.975 * len(diffs)) - 1]
        else:
            lo = hi = None
        return {"observed_difference": observed,
                "ci95_low": lo, "ci95_high": hi, "resamples": len(diffs)}

    pairs = {
        "persistence_count_vs_identity_entity": (persistence_count, identity_entity),
        "persistence_count_vs_calendar_identity": (persistence_count, calendar_identity),
        "calendar_identity_vs_identity_entity": (calendar_identity, identity_entity),
        "identity_count_vs_identity_entity": (identity_count, identity_entity),
    }
    paired = {name: cluster_auc_pair(a, b) for name, (a, b) in pairs.items()}

    # prevalence drift: eval measured here; holdout rate quoted from the
    # artifact's declared meta.json (the holdout rows are never opened)
    meta = json.loads((data / "meta.json").read_text())
    drift = {
        "train_positive_rate": round(train_rate, 6),
        "eval_positive_rate": round(n_pos / n_eval, 6),
        "holdout_positive_rate_declared": meta.get("positive_rate", {}).get("holdout"),
        "note": ("base-rate drift across eras is a measured phenomenon "
                 "property (the record's reference vintage measured 17.8% -> "
                 "27.7% -> 28.4%); the holdout figure is the declared "
                 "meta.json rate, not a measurement on opened rows"),
    }

    out = {
        "name": NAME,
        "rows": {"eval": n_eval, "eval_positives": n_pos,
                 "train": len(train), "train_positive_rate": round(train_rate, 6),
                 "eval_distinct_positive_entities": len(positive_clusters),
                 "eval_identity_coverage": round(identity_coverage, 6)},
        "references": references,
        "per_eval_year": per_year,
        "dependence": {
            "distinct_positive_clusters": len(positive_clusters),
            "note": ("positives cluster by entity (serial infrangers); all "
                     "intervals are CLUSTER bootstrap resamples of entity_id "
                     "keys"),
            "cluster_count": len(clusters),
        },
        "prevalence_shift": drift,
        "paired_cluster_bootstrap": paired,
        "deciding_check": {
            "pre_registered_rule": ("written into the candidate record BEFORE "
                                    "construction scores existed: the full "
                                    "runner-contract model (separate baseline "
                                    "job, identical eval rows) must beat "
                                    "EVERY reference here for a headroom "
                                    "claim; any reference matching or beating "
                                    "the model with a cluster-aware paired "
                                    "bootstrap 95% interval excluding zero on "
                                    "the deficit side is 'no demonstrated "
                                    "headroom under this protocol' and the "
                                    "wb-loan/unhcr-corridor precedent applies "
                                    "(drop, negative finding preserved); an "
                                    "interval containing zero is inconclusive, "
                                    "not parity"),
            "model_status": "pending_baseline_job",
        },
        "notes": [
            "every rate table is estimated ONLY from train lavratura years 2005-2015",
            "the holdout was never opened by this stage; the full model comes "
            "from the benchmark runner's baseline job on the same eval rows "
            "and is quoted beside these references when it exists",
            "the artifact is retrospective current-vintage with a declared "
            "isolated_rows protocol; the model comparison must honor "
            "row-isolated prediction (no cross-row joins)",
            "an interval containing zero is an inconclusive difference, not parity",
        ],
    }
    Path(args.report).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n",
                                encoding="utf-8")
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
