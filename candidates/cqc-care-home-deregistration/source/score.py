#!/usr/bin/env python3
"""Simple references for the accepted cqc-care-home-deregistration artifact.

Runs ONLY after the qualification gate has passed and --accept has re-verified
the report against these exact bytes (run.sh enforces that order; this file
re-checks the accepted report and the artifact digests before its first
metric, so an accidental early invocation refuses to score). It reads the
written CSVs, never rewrites them, and computes every reference on the SAME
eval rows. The holdout is NEVER opened - it is the final test surface and
stays sealed.

The candidate record names this reference set (the simple-reference triad
this task's own next_action requires before any model figure): the priors a
commissioner or the BMJ/npj closure literature would compute first, every
rate table estimated ONLY from train rows (January vintages 2016-2022) and
scored on the eval rows (the January 2024 vintage):

  * global_rate - the train 12-month deregistration rate (constant; the
    degenerate control, no ranking information).
  * local_authority_rate - train-estimated rate of the row's local authority,
    global fallback.
  * last_rating_rate - train-estimated rate of the row's latest overall
    rating level (the CQC State of Care closure signal: Inadequate-rated homes
    deregister far more often).
  * beds_bucket_rate - train-estimated rate of the row's bed-size bucket
    (small homes dominate closures).
  * provider_sector_rate - train-estimated rate of the row's provider sector.
  * hsca_start_year_rate - train-estimated rate of the row's registration
    start year (registration age; the nearest shippable analogue of a
    persistence/history prior).
  * rating_x_beds_rate - the strongest two-way cell (rating x bed-size
    bucket), train-estimated with fallbacks.
  * majority_class - fitted on train, measured against THIS split's labels.

NO persistence reference exists, and that is a designed property, not an
omission: the location's own prior-instant outcome would be the natural
persistence score, but location identity ships as a per-instant pseudonym
(the missing-successor P0 design), so prior-instant labels are structurally
unlinkable over the shipped frame - for the scorer too. Any model figure must
be quoted beside ALL of these references, and the strongest one leads.

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

NAME = "cqc-care-home-deregistration"
TARGET = "deregistered_12m"
POSITIVE = "1"
SEED = 20261103
BOOTSTRAP = 150


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


def rate_table(rows: list[dict], keys: list[str]):
    """Train-estimated positive rate per key tuple; global rate as the fallback."""
    stats = defaultdict(lambda: [0, 0])
    for row, y in zip(rows, labels_of(rows)):
        stats[tuple(row.get(k, "") for k in keys)][y] += 1
    global_pos = sum(v[1] for v in stats.values())
    global_n = sum(v[0] + v[1] for v in stats.values())
    table = {k: v[1] / (v[0] + v[1]) for k, v in stats.items() if (v[0] + v[1])}
    return table, (global_pos / global_n if global_n else 0.5)


def score_with(table, fallback, keys, rows):
    return [table.get(tuple(r.get(k, "") for k in keys), fallback) for r in rows]


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
    artifact = report.get("artifact") or {}
    digest_claim = (artifact.get("artifact_version") or {}).get("digest")
    if not digest_claim:
        raise SystemExit("refusing to score: the accepted report carries no artifact digest")
    components = (artifact.get("artifact_version") or {}).get("components") or []
    actual = {}
    for split_rel in ("public/train.csv", "public/eval.csv", "meta.json", "quality.json"):
        actual[split_rel] = hashlib.sha256((data / split_rel).read_bytes()).hexdigest()
    claimed = {(artifact.get(k) or {}).get("sha256"): k
               for k in components if isinstance(artifact.get(k), dict)}
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

    la_table, g1 = rate_table(train, ["local_authority"])
    rating_table, g2 = rate_table(train, ["latest_overall_rating"])
    beds_table, g3 = rate_table(train, ["beds_bucket"])
    sector_table, g4 = rate_table(train, ["provider_sector"])
    start_table, g5 = rate_table(train, ["hsca_start_year"])
    cell_table, g6 = rate_table(train, ["latest_overall_rating", "beds_bucket"])

    vectors = {
        "local_authority_rate": score_with(la_table, g1, ["local_authority"], evald),
        "last_rating_rate": score_with(rating_table, g2, ["latest_overall_rating"], evald),
        "beds_bucket_rate": score_with(beds_table, g3, ["beds_bucket"], evald),
        "provider_sector_rate": score_with(sector_table, g4, ["provider_sector"], evald),
        "hsca_start_year_rate": score_with(start_table, g5, ["hsca_start_year"], evald),
    }
    rating_beds = []
    for row in evald:
        key = (row["latest_overall_rating"], row["beds_bucket"])
        rating_beds.append(cell_table.get(
            key, rating_table.get((row["latest_overall_rating"],),
                                  beds_table.get((row["beds_bucket"],), g6))))
    vectors["rating_x_beds_rate"] = rating_beds

    majority = int(train_rate >= 0.5)
    majority_accuracy = sum(1 for y in y_eval if y == majority) / len(y_eval)

    references = {}
    for name, vector in vectors.items():
        references[name] = {"eval_auc": auc(y_eval, vector),
                            "brier": brier(y_eval, vector)}
    references["global_rate"] = {
        "eval_auc": None, "brier": brier(y_eval, [train_rate] * n_eval),
        "note": "constant score, no ranking information; degenerate control"}
    references["majority_class"] = {
        "accuracy_this_split": majority_accuracy,
        "note": "majority fitted on train, measured against this split's labels"}

    # per-rating-level eval reporting (the CQC State of Care closure axis)
    per_rating = {}
    for level in sorted({r["latest_overall_rating"] for r in evald}):
        idx = [i for i, r in enumerate(evald)
               if r["latest_overall_rating"] == level]
        ys = [y_eval[i] for i in idx]
        per_rating[level] = {
            "rows": len(idx), "positives": sum(ys),
            "prevalence": (sum(ys) / len(idx)) if idx else None,
            "last_rating_rate_auc": auc(ys, [vectors["last_rating_rate"][i]
                                             for i in idx])}

    # ---- paired bootstrap: each reference vs the global control, and the
    # strongest plausible pair, on identical rows -------------------------------
    rng = random.Random(SEED)
    order = sorted((name for name, v in vectors.items()
                     if v and auc(y_eval, v) is not None),
                    key=lambda name: -(auc(y_eval, vectors[name]) or 0))
    pairs = {f"{name}_vs_global_constant": (vectors[name], [train_rate] * n_eval)
             for name in order[:3]}
    if len(order) >= 2:
        pairs[f"{order[0]}_vs_{order[1]}"] = (vectors[order[0]],
                                              vectors[order[1]])
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
        "reference_ranking": order,
        "per_eval_rating_level": per_rating,
        "paired_bootstrap": paired,
        "notes": [
            "every rate table is estimated ONLY from train rows (January "
            "vintages 2016-2022) and scored on the eval rows (the January "
            "2024 vintage); the holdout was never opened by this stage",
            "NO persistence reference exists BY DESIGN: the location's own "
            "prior-instant outcome is the natural persistence score, but "
            "location identity ships as a per-instant pseudonym (the "
            "missing-successor P0 design), so prior-instant labels are "
            "structurally unlinkable over the shipped frame - for this "
            "scorer too; hsca_start_year_rate is the nearest shippable "
            "history prior",
            "the full model comes from the benchmark runner's baseline job "
            "on the same eval rows; its figure must be quoted beside ALL of "
            "these references, and a model below the strongest one is a "
            "recorded defect, not an encouraging result",
            "an interval containing zero is an inconclusive difference, not "
            "parity",
        ],
    }
    Path(args.report).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n",
                                 encoding="utf-8")
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
