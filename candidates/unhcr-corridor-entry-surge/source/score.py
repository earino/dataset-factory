#!/usr/bin/env python3
"""Simple references for the accepted unhcr-corridor-entry-surge artifact.

Runs ONLY after the qualification gate has passed and --accept has
re-verified the report against these exact bytes (run.sh enforces that
order; this file re-checks the accepted report and the artifact digests
before its first metric, so an accidental early invocation refuses to
score). It reads the written CSVs, never rewrites them, and computes every
reference on the SAME eval rows. The holdout is NEVER opened - it is the
final test surface and stays sealed (its declared meta.json positive rate
is quoted as the recorded drift, not measured here).

The task is a one-shot first-crossing question (one row per corridor), so
the reference set takes this shape (every rate table is estimated ONLY from
train entry years, 2000-2014; scored on eval entry years, 2015-2020):

  * identity_only_origin / identity_only_host - train-estimated cum2 rate
    per origin / per host country, global-rate fallback. The corridor
    itself NEVER recurs (one row per corridor), so - unlike panel tasks -
    identity cannot name the row; an origin/host cell table would have
    zero eval coverage and is NOT computed (recorded as degenerate). These
    two are pure country priors.
  * identity_combined - the mean of the origin and host rate estimates;
    the calendar-identity control for this task. The seasonal component of
    the skill's calendar control is DEGENERATE at annual grain: all
    outcomes are two-year calendar windows and eval entry years never
    appear in train, so there is no seasonal prior to estimate. Recorded
    as inapplicable rather than faked.
  * momentum_raw - score = log_growth_into_entry, the naive into-entry
    momentum the candidate record names as the reference model. This is
    ALSO the persistence-of-change reading of the skill's persistence
    reference: the most recent observed change of the corridor's own
    series. Prior-instant LABEL persistence (the last observed label) is
    structurally absent in a one-shot task and is recorded as such, not
    pretended.
  * momentum_bucket_rate - train-estimated cum2 rate by into-entry growth
    bucket (<1.5x / 1.5-3x / >3x, the discovery probe's buckets). This is
    the smoothed momentum prior; the discovery measurement found the cum2
    association is NOT monotone (42.0% / 45.6% / 37.5%), so the bucket
    table can express what a raw monotone score cannot.
  * persistence_state_rate - train-estimated rate by surged_into_entry
    (the corridor's most recent observed doubling state).
  * persistence_last_value - score = apps_t0, the most recent observed
    magnitude. Note the mechanical direction: the label's bar is 2 x T0,
    so larger baselines make doubling harder; a low AUC here is the
    magnitude mean-reversion property, not a bug.
  * global_rate - constant train rate (degenerate: no ranking
    information).
  * majority_class - fitted on train, measured against THIS split's
    labels.

DECIDING CHECK (pre-registered in the candidate record BEFORE any score
existed): the task has demonstrated reference-level headroom over
identity-only priors only if a pre-specified momentum reference beats the
identity reference with a cluster-aware paired bootstrap 95% interval
excluding zero. The pre-specified pairs are (momentum_raw vs
identity_combined) and (momentum_bucket_rate vs identity_combined). If
neither pair clears its interval, the finding is "no demonstrated
headroom over identity-only priors under this protocol" - an inconclusive
interval is NOT parity, and the negative finding is preserved exactly as
measured. If identity dominates, the wb-loan-disbursement-completion
precedent applies (drop for no headroom).

The full model is NOT computed here: the benchmark runner's baseline job
trains and evaluates it on these same rows, and its figure is quoted
beside these references when it exists. Nothing in this file may run
before acceptance.

Positives cluster by (origin, entry-year) displacement events, so all
intervals are CLUSTER bootstrap intervals: distinct surge_cluster keys are
resampled with replacement (all rows of a drawn cluster travel together),
150 resamples, fixed seed. An interval containing zero is an inconclusive
difference, not parity.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

NAME = "unhcr-corridor-entry-surge"
TARGET = "cum2_2x"
POSITIVE = "1"
SEED = 20261105
BOOTSTRAP = 150
GROWTH_BUCKETS = ("lt_1.5x", "1.5x_to_3x", "gt_3x")


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
    """Train-estimated positive rate per key tuple; global rate as the fallback."""
    stats = defaultdict(lambda: [0, 0])
    for row, y in zip(rows, labels_of(rows)):
        stats[tuple(row.get(k, "") for k in keys)][y] += 1
    global_pos = sum(v[1] for v in stats.values())
    global_n = sum(v[0] + v[1] for v in stats.values())
    table = {k: v[1] / (v[0] + v[1]) for k, v in stats.items() if (v[0] + v[1])}
    return table, (global_pos / global_n if global_n else 0.5)


def growth_bucket(row: dict) -> str:
    ratio = float(row["apps_t0"]) / float(row["apps_t0m1"])
    if ratio > 3:
        return GROWTH_BUCKETS[2]
    if ratio >= 1.5:
        return GROWTH_BUCKETS[1]
    return GROWTH_BUCKETS[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--accepted-report", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    data = Path(args.data)

    # ---- acceptance re-check: no metric exists before this passes -------------
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

    # identity and momentum tables from train only
    origin_table, origin_global = rate_table(train, ["origin"])
    host_table, host_global = rate_table(train, ["asylum"])
    # growth buckets are computed, not shipped: build the key inline
    stats = defaultdict(lambda: [0, 0])
    for row, y in zip(train, y_train):
        stats[growth_bucket(row)][y] += 1
    bucket_table = {k: v[1] / (v[0] + v[1]) for k, v in stats.items() if v[0] + v[1]}
    bucket_global = train_rate
    state_stats = defaultdict(lambda: [0, 0])
    for row, y in zip(train, y_train):
        state_stats[row["surged_into_entry"]][y] += 1
    state_table = {k: v[1] / (v[0] + v[1]) for k, v in state_stats.items() if v[0] + v[1]}

    identity_origin = [origin_table.get((r["origin"],), origin_global) for r in evald]
    identity_host = [host_table.get((r["asylum"],), host_global) for r in evald]
    identity_combined = [(a + b) / 2 for a, b in zip(identity_origin, identity_host)]
    momentum_raw = [float(r["log_growth_into_entry"]) for r in evald]
    momentum_bucket = [bucket_table.get(growth_bucket(r), bucket_global) for r in evald]
    persistence_state = [state_table.get(r["surged_into_entry"], train_rate) for r in evald]
    persistence_last_value = [float(r["apps_t0"]) for r in evald]

    majority = int(train_rate >= 0.5)
    majority_accuracy = sum(1 for y in y_eval if y == majority) / len(y_eval)

    references = {
        "identity_only_origin": {"eval_auc": auc(y_eval, identity_origin),
                                 "brier": brier(y_eval, identity_origin)},
        "identity_only_host": {"eval_auc": auc(y_eval, identity_host),
                               "brier": brier(y_eval, identity_host)},
        "identity_combined": {
            "eval_auc": auc(y_eval, identity_combined),
            "brier": brier(y_eval, identity_combined),
            "note": ("mean of the origin-rate and host-rate train estimates; "
                     "the seasonal component of the calendar-identity "
                     "control is DEGENERATE at annual grain (eval entry "
                     "years never appear in train), recorded as "
                     "inapplicable; an origin x host cell table has zero "
                     "eval coverage (one row per corridor) and is not "
                     "computed")},
        "momentum_raw": {
            "eval_auc": auc(y_eval, momentum_raw),
            "brier": brier(y_eval, momentum_raw),
            "note": ("score = log_growth_into_entry, the naive into-entry "
                     "momentum (the record's reference model); also the "
                     "persistence-of-change reading - the corridor's most "
                     "recent observed change. Prior-instant LABEL "
                     "persistence is structurally absent in a one-shot "
                     "task (no earlier instant of the same corridor "
                     "exists) and is recorded as inapplicable, not faked")},
        "momentum_bucket_rate": {
            "eval_auc": auc(y_eval, momentum_bucket),
            "brier": brier(y_eval, momentum_bucket),
            "note": ("train-estimated cum2 rate by into-entry growth bucket "
                     f"{GROWTH_BUCKETS}; the discovery association is NOT "
                     "monotone (42.0% / 45.6% / 37.5%), so the bucket prior "
                     "expresses what a raw monotone score cannot")},
        "persistence_state_rate": {
            "eval_auc": auc(y_eval, persistence_state),
            "brier": brier(y_eval, persistence_state),
            "note": ("train-estimated rate by surged_into_entry, the "
                     "corridor's most recent observed doubling state")},
        "persistence_last_value": {
            "eval_auc": auc(y_eval, persistence_last_value),
            "brier": brier(y_eval, persistence_last_value),
            "note": ("score = apps_t0, the most recent observed magnitude; "
                     "the label's bar is 2 x T0, so a low AUC is the "
                     "magnitude mean-reversion property, not a defect")},
        "global_rate": {"eval_auc": None, "brier": brier(y_eval, [train_rate] * n_eval),
                        "note": "constant score, no ranking information; degenerate control"},
        "majority_class": {"accuracy_this_split": majority_accuracy,
                           "note": "majority fitted on train, measured against this split's labels"},
    }

    # per-entry-year eval reporting (the structural-break check: six entry
    # years, including the 2020 COVID collapse year inside outcomes)
    per_entry_year = {}
    for year in sorted({r["entry_year"] for r in evald}):
        idx = [i for i, r in enumerate(evald) if r["entry_year"] == year]
        ys = [y_eval[i] for i in idx]
        entry: dict = {"rows": len(idx), "positives": sum(ys)}
        for name, vector in (("momentum_raw", momentum_raw),
                             ("identity_combined", identity_combined),
                             ("momentum_bucket_rate", momentum_bucket)):
            entry[f"{name}_auc"] = auc(ys, [vector[i] for i in idx])
        per_entry_year[year] = entry

    # cluster structure: positives cluster by (origin, entry-year) events
    clusters = defaultdict(list)
    for i, row in enumerate(evald):
        clusters[row["surge_cluster"]].append(i)
    positive_clusters = sorted({row["surge_cluster"]
                                for row, y in zip(evald, y_eval) if y})

    # ---- cluster-aware paired bootstrap on identical rows --------------------
    rng = random.Random(SEED)
    cluster_keys = sorted(clusters)

    def cluster_auc_pair(vector_a, vector_b):
        a_val, b_val = auc(y_eval, vector_a), auc(y_eval, vector_b)
        observed = (a_val - b_val) if (a_val is not None and b_val is not None) else None
        diffs = []
        for _ in range(BOOTSTRAP):
            drawn_keys = [cluster_keys[rng.randrange(len(cluster_keys))]
                          for _ in range(len(cluster_keys))]
            idx = [i for key in drawn_keys for i in clusters[key]]
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
        "momentum_raw_vs_identity_combined": (momentum_raw, identity_combined),
        "momentum_bucket_rate_vs_identity_combined": (momentum_bucket, identity_combined),
        "momentum_raw_vs_identity_only_origin": (momentum_raw, identity_origin),
        "momentum_raw_vs_identity_only_host": (momentum_raw, identity_host),
        "momentum_raw_vs_persistence_last_value": (momentum_raw, persistence_last_value),
    }
    paired = {name: cluster_auc_pair(a, b) for name, (a, b) in pairs.items()}

    # ---- the pre-registered deciding check ------------------------------------
    deciding_pairs = ("momentum_raw_vs_identity_combined",
                      "momentum_bucket_rate_vs_identity_combined")
    clears = []
    for name in deciding_pairs:
        entry = paired[name]
        if (entry["observed_difference"] is not None
                and entry["observed_difference"] > 0
                and entry["ci95_low"] is not None and entry["ci95_low"] > 0):
            clears.append(name)
    momentum_vals = [references["momentum_raw"]["eval_auc"],
                     references["momentum_bucket_rate"]["eval_auc"]]
    identity_val = references["identity_combined"]["eval_auc"]
    identity_dominates = (identity_val is not None
                         and all(v is not None and identity_val > v
                                 for v in momentum_vals))
    if clears:
        verdict = "headroom_demonstrated_at_reference_level"
    elif identity_dominates:
        verdict = "identity_prior_dominates_no_headroom"
    else:
        verdict = "no_demonstrated_headroom_inconclusive"
    deciding = {
        "pre_registered_rule": (
            "written into the candidate record BEFORE construction scores "
            "existed: the task demonstrates reference-level headroom over "
            "identity-only priors only if a pre-specified momentum "
            "reference beats identity_combined with a cluster-aware paired "
            "bootstrap 95% interval excluding zero in its favor; an "
            "interval containing zero is an inconclusive difference, not "
            "parity; if identity dominates, the "
            "wb-loan-disbursement-completion precedent applies (drop for "
            "no headroom)"),
        "deciding_pairs": list(deciding_pairs),
        "pairs_clearing": clears,
        "identity_dominates": identity_dominates,
        "verdict": verdict,
    }

    # prevalence drift: eval measured here; holdout rate quoted from the
    # artifact's declared meta.json (the holdout rows are never opened)
    meta = json.loads((data / "meta.json").read_text())
    drift = {
        "train_positive_rate": round(train_rate, 6),
        "eval_positive_rate": round(n_pos / n_eval, 6),
        "holdout_positive_rate_declared": meta.get("positive_rate", {}).get("holdout"),
        "note": ("prevalence drift is a recorded phenomenon property of the "
                 "period (discovery measured 32.8% -> 44.8% -> 42.9% on "
                 "the full population); the holdout figure is the declared "
                 "meta.json rate, not a measurement on opened rows"),
    }

    out = {
        "name": NAME,
        "rows": {"eval": n_eval, "eval_positives": n_pos,
                 "train": len(train), "train_positive_rate": round(train_rate, 6),
                 "eval_distinct_positive_clusters": len(positive_clusters)},
        "references": references,
        "per_eval_entry_year": per_entry_year,
        "dependence": {
            "distinct_positive_clusters": len(positive_clusters),
            "note": ("positives cluster by (origin, entry-year) displacement "
                     "events; all intervals are CLUSTER bootstrap "
                     "resamples of surge_cluster keys"),
            "cluster_count": len(clusters),
        },
        "prevalence_shift": drift,
        "paired_cluster_bootstrap": paired,
        "deciding_check": deciding,
        "notes": [
            "every rate table is estimated ONLY from train entry years (2000-2014)",
            "the holdout was never opened by this stage; the full model "
            "comes from the benchmark runner's baseline job on the same "
            "eval rows and is quoted beside these references when it exists",
            "prior-instant label persistence is structurally absent (one "
            "row per corridor); the persistence readings here are the "
            "most recent observed change (momentum_raw), doubling state "
            "(persistence_state_rate) and magnitude "
            "(persistence_last_value), all from shipped at-instant columns",
            "an interval containing zero is an inconclusive difference, not parity",
        ],
    }
    Path(args.report).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n",
                                 encoding="utf-8")
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
