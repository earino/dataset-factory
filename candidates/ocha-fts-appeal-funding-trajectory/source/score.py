#!/usr/bin/env python3
"""Simple references for the accepted ocha-fts-appeal-funding-trajectory artifact.

Runs ONLY after the qualification gate has passed and --accept has re-verified
the report against these exact bytes (run.sh enforces that order; this file
re-checks the accepted report and the artifact digests before its first metric,
so an accidental early invocation refuses to score). It reads the written CSVs,
never rewrites them, and computes every reference on the SAME eval rows. The
holdout is NEVER opened - it is the final test surface and stays sealed.

The task is an appeal-coverage question at the launch instant, so the reference
set takes this shape (every rate table is estimated ONLY from training rows,
2000-2016; scored on eval rows, plan years 2017-2020):

  * persistence_last_coverage - THE HEADROOM REFERENCE the candidate record
    names first: the country's most recent strictly-earlier plan-year's label
    as the score (0.5 for the -1 no-prior sentinel) - the funding-persistence
    form the full model must beat.
  * prior_mean_rate - the shipped country_prior_covered_rate feature as a
    continuous score (mean over ALL prior plan-years; global train rate for the
    sentinel) - the broader persistence family.
  * country_hist_rate - train-estimated covered rate of the row's country
    (identity reference; global train rate for countries unseen in train).
  * plan_type_rate - train-estimated rate by plan type (launch-attribute base
    rate), global fallback.
  * ask_size_rate - train-estimated rate by orig-requirements tercile, bins cut
    on TRAIN values only (does the size of the ask alone rank coverage?).
  * year_rate - train-estimated rate by plan year; eval years 2017-2020 are
    outside the train range, so every eval row falls back to the global rate:
    a CONSTANT score, degenerate by construction. Recorded as such - at annual
    grain the calendar prior cannot be estimated outside the training era, and
    the skill's calendar control collapses exactly like pins' did.
  * global_rate - constant train rate (degenerate: no ranking information).
  * majority_class - fitted on train, measured against THIS split's labels.

The full model is NOT computed here: the benchmark runner's baseline job
trains and evaluates it on these same rows, and its figure is quoted beside
these references when it exists. Nothing in this file may run before
acceptance.

Per-plan-year eval reporting is mandatory: prevalence drifts across eras
(68.3% -> 42.5% measured at discovery), so a pooled eval number hides
year-level structure.

Uncertainty: paired bootstrap differences (150 resamples, fixed seed) on
identical eval rows - never overlapping marginal intervals. An interval
containing zero is an inconclusive difference, not parity.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

NAME = "ocha-fts-appeal-funding-trajectory"
TARGET = "reached_half"
POSITIVE = "1"
BOOTSTRAP = 150
SEED = 43


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def labels_of(rows: list[dict]) -> list[int]:
    return [1 if row[TARGET] == POSITIVE else 0 for row in rows]


def auc(labels: list[int], scores: list[float]) -> float | None:
    """Mann-Whitney AUC with tie handling."""
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--accepted-report", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    data = Path(args.data)

    # ---- acceptance re-check: no metric exists before this passes -------------
    report = json.loads(Path(args.accepted_report).read_text())
    failed = report.get("failed_checks") or []
    if failed:
        raise SystemExit("refusing to score: the qualification report carries "
                         f"failed checks: {failed}")
    if report.get("ok") is not True:
        raise SystemExit("refusing to score: the qualification report did not pass")
    digest_claim = ((report.get("artifact") or {}).get("artifact_version") or {}).get("digest")
    if not digest_claim:
        raise SystemExit("refusing to score: the accepted report carries no artifact digest")
    components = ((report.get("artifact") or {}).get("artifact_version") or {}).get("components") or []
    actual = {}
    for split_rel in ("public/train.csv", "public/eval.csv", "meta.json", "quality.json"):
        p = data / split_rel
        actual[split_rel] = hashlib.sha256(p.read_bytes()).hexdigest()
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

    def scores_from(rows, fn):
        return [fn(r) for r in rows]

    # persistence: the country's most recent strictly-earlier plan-year's label
    persistence = scores_from(evald, lambda r: 0.5 if r["country_last_prior_covered"] == "-1"
                              else float(r["country_last_prior_covered"]))

    # broader persistence family: mean covered rate over all prior plan-years
    prior_mean = scores_from(evald, lambda r: train_rate
                            if r["country_prior_covered_rate"] == "-1.000000"
                            else float(r["country_prior_covered_rate"]))

    # identity: train-estimated per-country covered rate
    country_table, country_global = rate_table(train, ["country_iso3"])
    country_hist = scores_from(evald, lambda r: country_table.get((r["country_iso3"],),
                                          country_global))

    # launch-attribute base rates
    type_table, type_global = rate_table(train, ["plan_type"])
    plan_type = scores_from(evald, lambda r: type_table.get((r["plan_type"],), type_global))

    # ask size: terciles cut on TRAIN values only
    train_orig = sorted(float(r["orig_requirements_usd"]) for r in train)
    t1, t2 = train_orig[len(train_orig) // 3], train_orig[2 * len(train_orig) // 3]

    def size_bin(row):
        value = float(row["orig_requirements_usd"])
        return 0 if value < t1 else (1 if value < t2 else 2)

    size_stats = defaultdict(lambda: [0, 0])
    for row, y in zip(train, y_train):
        size_stats[size_bin(row)][y] += 1
    size_table = {k: v[1] / (v[0] + v[1]) for k, v in size_stats.items() if (v[0] + v[1])}
    ask_size = scores_from(evald, lambda r: size_table.get(size_bin(r), train_rate))

    # calendar: train years cannot cover eval years, so this is degenerate here
    year_table, year_global = rate_table(train, ["plan_year"])
    year_only = scores_from(evald, lambda r: year_table.get((r["plan_year"],), year_global))

    majority = int(train_rate >= 0.5)
    majority_accuracy = sum(1 for y in y_eval if y == majority) / len(y_eval)

    references = {
        "persistence_last_coverage": {"eval_auc": auc(y_eval, persistence),
                                      "brier": brier(y_eval, persistence)},
        "prior_mean_rate": {"eval_auc": auc(y_eval, prior_mean),
                            "brier": brier(y_eval, prior_mean)},
        "country_hist_rate": {"eval_auc": auc(y_eval, country_hist),
                              "brier": brier(y_eval, country_hist)},
        "plan_type_rate": {"eval_auc": auc(y_eval, plan_type),
                           "brier": brier(y_eval, plan_type)},
        "ask_size_rate": {"eval_auc": auc(y_eval, ask_size),
                          "brier": brier(y_eval, ask_size)},
        "year_rate": {"eval_auc": auc(y_eval, year_only),
                      "brier": brier(y_eval, year_only),
                      "note": ("degenerate by construction: eval plan years "
                               "2017-2020 are outside the train range 2000-2016, "
                               "so every eval row falls back to the constant "
                               "global train rate - no ranking information; the "
                               "calendar prior cannot be estimated outside the "
                               "training era at annual grain")},
        "global_rate": {"eval_auc": None, "brier": brier(y_eval, [train_rate] * n_eval),
                        "note": "constant score, no ranking information; degenerate control"},
        "majority_class": {"accuracy_this_split": majority_accuracy,
                           "note": "majority fitted on train, measured against this split's labels"},
    }

    # per-plan-year eval reporting (mandatory: prevalence drifts across eras)
    per_year = {}
    for year in sorted({r["plan_year"] for r in evald}):
        idx = [i for i, r in enumerate(evald) if r["plan_year"] == year]
        ys = [y_eval[i] for i in idx]
        entry = {"rows": len(idx), "positives": sum(ys)}
        for name, vector in (("persistence_last_coverage", persistence),
                             ("prior_mean_rate", prior_mean),
                             ("country_hist_rate", country_hist),
                             ("plan_type_rate", plan_type),
                             ("ask_size_rate", ask_size)):
            entry[f"{name}_auc"] = auc(ys, [vector[i] for i in idx])
        per_year[year] = entry

    # ---- paired bootstrap: reference vs reference on identical rows ------------
    rng = random.Random(SEED)
    pairs = {"persistence_vs_country_hist": (persistence, country_hist),
             "persistence_vs_prior_mean": (persistence, prior_mean),
             "persistence_vs_plan_type": (persistence, plan_type),
             "persistence_vs_ask_size": (persistence, ask_size)}
    paired = {}
    for name, (a, b) in pairs.items():
        observed_a, observed_b = auc(y_eval, a), auc(y_eval, b)
        observed = (observed_a - observed_b) if (observed_a is not None
                                                 and observed_b is not None) else None
        diffs = []
        for _ in range(BOOTSTRAP):
            drawn = [rng.randrange(n_eval) for _ in range(n_eval)]
            labels_drawn = [y_eval[i] for i in drawn]  # one labels list, shared
            sa = [a[i] for i in drawn]
            sb = [b[i] for i in drawn]
            va, vb = auc(labels_drawn, sa), auc(labels_drawn, sb)
            if va is None or vb is None:
                continue
            diffs.append(va - vb)
        diffs.sort()
        if diffs:
            lo, hi = diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs)) - 1]
        else:
            lo = hi = None
        paired[name] = {"observed_difference": observed,
                        "ci95_low": lo, "ci95_high": hi,
                        "resamples": len(diffs)}

    out = {
        "name": NAME,
        "rows": {"eval": n_eval, "eval_positives": n_pos,
                 "train": len(train), "train_positive_rate": round(train_rate, 6)},
        "references": references,
        "per_eval_year": per_year,
        "paired_bootstrap": paired,
        "notes": [
            "every rate table is estimated ONLY from train plan-years 2000-2016",
            "the holdout was never opened by this stage",
            "the full model comes from the benchmark runner's baseline job on the "
            "same eval rows; its figure is quoted beside these references",
            "an interval containing zero is an inconclusive difference, not parity",
        ],
    }
    Path(args.report).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n",
                                encoding="utf-8")
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
