#!/usr/bin/env python3
"""Simple references for the accepted `acnc-charity-ais-deadline-compliance` artifact.

Runs ONLY after the qualification gate has passed and --accept has re-verified
the report against these exact bytes (run.sh enforces that order; this file
re-checks the accepted report and the artifact digest before its first
metric, so an accidental early invocation refuses to score). It reads the
written CSVs, never rewrites them, and computes every reference on the SAME
eval rows. The holdout is never opened.

The task is a per-charity-year deadline-compliance question at the per-charity
instant T = recorded due date - 90 days, so the reference set takes this shape
(every rate table is estimated ONLY from training target years 2020-2021;
scored on eval rows, target years 2022-2023):

  * persistence_momentum - THE FIRST MEASURED REFERENCE (the candidate record
    names prior-lateness as the required first measurement): the prior row's
    signed lateness in days as the score. A previously-late charity is more
    likely to fail again.
  * persistence_flag - the binary form (prior_lateness_positive).
  * calendar_size_rate - calendar/identity control: train-estimated positive
    rate by (prior period-end month, charity size), with marginal and global
    fallbacks. Tests that the task is not just FY-structure/size composition.
  * identity_history_rate - train-estimated per-charity historical failure
    rate (the cross-year identity signal), global rate for charities unseen
    in train.
  * global_rate - constant train rate (degenerate: no ranking information,
    AUC undefined by construction, reported as such).
  * majority_class - fitted on train, measured against THIS split's labels.
  * persistence applicability: every scored row is a NEW target year, but the
    same charity recurs across years, so persistence is the prior-year
    outcome - measured, not recorded not-applicable.

The full model is NOT computed here: the harness runner's baseline job
trains and evaluates it on these same rows, and its figure is quoted beside
these references when it exists. Nothing in this file may run before
acceptance.

Eval-only: the holdout is sealed until the design is frozen and the runner
evaluates it once. Per-target-year reporting is mandatory - prevalence drifts
across years (measured 30.0% -> 25.9% train -> eval before this build's
frame) and history depth grows with the file window.

Uncertainty: paired bootstrap differences (150 resamples, fixed seed) on
identical eval rows - never overlapping marginal intervals. The resampler
draws row indices once per resample and both scores read the same drawn rows
and the same drawn labels (one labels list), so the pairing invariant holds
by construction and is asserted (resampler_alignment_ok).
An interval containing zero is an inconclusive difference, not parity.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

NAME = "acnc-charity-ais-deadline-compliance"
TARGET = "failed_by_due"
POSITIVE = "1"
BOOTSTRAP = 150
SEED = 31


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
    ranks = [0.0] * len(scores)
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
        raise SystemExit("refusing to score: the qualification report carries failed checks")
    digest_claim = ((report.get("artifact") or {}).get("artifact_version") or {}).get("digest")
    if not digest_claim:
        raise SystemExit("refusing to score: the accepted report carries no artifact digest")
    components = ((report.get("artifact") or {}).get("artifact_version") or {}).get("components") or []
    actual = {}
    for split_rel in ("public/train.csv", "public/eval.csv", "private/holdout.csv", "meta.json", "quality.json"):
        p = data / split_rel
        actual[split_rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    claimed = {((report.get("artifact") or {}).get(k) or {}).get("sha256"): k for k in components
               if isinstance((report.get("artifact") or {}).get(k), dict)}
    missing = [rel for rel, dig in actual.items() if claimed.get(dig) is None]
    if missing:
        raise SystemExit(f"refusing to score: on-disk files do not match the accepted artifact: {missing}")

    train = read_rows(data / "public" / "train.csv")
    evald = read_rows(data / "public" / "eval.csv")
    y_eval = labels_of(evald)
    y_train = labels_of(train)
    n_eval, n_pos = len(evald), sum(y_eval)
    train_rate = sum(y_train) / len(y_train)

    def scores_from(rows, fn):
        return [fn(r) for r in rows]

    # persistence (measured first: the candidate record requires it)
    momentum = scores_from(evald, lambda r: float(r["prior_lateness_days"]))
    flag = scores_from(evald, lambda r: float(r["prior_lateness_positive"]))

    # calendar/identity: train-estimated (prior period-end month, charity size) rate
    cal_table, _ = rate_table(train, ["prior_period_end_month", "charity_size_code"])
    _, cal_global = rate_table(train, ["prior_period_end_month"])
    month_table, _ = rate_table(train, ["prior_period_end_month"])
    size_table, _ = rate_table(train, ["charity_size_code"])

    def cal_score(row):
        key = (row.get("prior_period_end_month", ""), row.get("charity_size_code", ""))
        if key in cal_table:
            return cal_table[key]
        m, s = key[0], key[1]
        if s in size_table and m in month_table:
            return 0.5 * (month_table[m] + size_table[s])
        if m in month_table:
            return month_table[m]
        if s in size_table:
            return size_table[s]
        return cal_global

    calendar = scores_from(evald, cal_score)

    # identity/history: train per-charity failure rate
    ident_table, ident_global = rate_table(train, ["abn"])
    identity = scores_from(evald, lambda r: ident_table.get((r["abn"],), ident_global))

    majority = int(train_rate >= 0.5)
    majority_accuracy = sum(1 for y in y_eval if y == majority) / len(y_eval)

    references = {
        "persistence_momentum": {"eval_auc": auc(y_eval, momentum), "brier": brier(y_eval, momentum)},
        "persistence_flag": {"eval_auc": auc(y_eval, flag), "brier": brier(y_eval, flag)},
        "calendar_size_rate": {"eval_auc": auc(y_eval, calendar), "brier": brier(y_eval, calendar)},
        "identity_history_rate": {"eval_auc": auc(y_eval, identity), "brier": brier(y_eval, identity)},
        "global_rate": {"eval_auc": None, "brier": brier(y_eval, [train_rate] * n_eval),
                        "note": "constant score, no ranking information; degenerate control"},
        "majority_class": {"accuracy_this_split": majority_accuracy,
                           "note": "majority fitted on train, measured against this split's labels"},
    }

    # per-target-year reporting (mandatory: prevalence and history depth drift by year)
    per_year = {}
    for year in sorted({r["target_year"] for r in evald}):
        idx = [i for i, r in enumerate(evald) if r["target_year"] == year]
        ys = [y_eval[i] for i in idx]
        per_year[year] = {
            "rows": len(idx), "positives": sum(ys),
            "persistence_momentum_auc": auc(ys, [momentum[i] for i in idx]),
            "persistence_flag_auc": auc(ys, [flag[i] for i in idx]),
            "calendar_size_rate_auc": auc(ys, [calendar[i] for i in idx]),
            "identity_history_rate_auc": auc(ys, [identity[i] for i in idx]),
        }

    # ---- paired bootstrap: reference vs reference on identical rows ------------
    rng = random.Random(SEED)
    pairs = {"persistence_flag_vs_calendar": (flag, calendar),
             "persistence_momentum_vs_calendar": (momentum, calendar),
             "persistence_flag_vs_identity": (flag, identity)}
    paired = {}
    for name, (a, b) in pairs.items():
        observed_a, observed_b = auc(y_eval, a), auc(y_eval, b)
        observed = (observed_a - observed_b) if (observed_a is not None and observed_b is not None) else None
        diffs = []
        aligned = True
        for _ in range(BOOTSTRAP):
            drawn = [rng.randrange(n_eval) for _ in range(n_eval)]
            labels_drawn = [y_eval[i] for i in drawn]  # one labels list, shared by both scores
            sa = [a[i] for i in drawn]
            sb = [b[i] for i in drawn]
            if len(sa) != len(sb) or len(sa) != len(labels_drawn):
                aligned = False
                break
            va, vb = auc(labels_drawn, sa), auc(labels_drawn, sb)
            if va is None or vb is None:
                continue
            diffs.append(va - vb)
        diffs.sort()
        if aligned and diffs:
            lo = diffs[int(0.025 * len(diffs))]
            hi = diffs[int(0.975 * len(diffs)) - 1] if len(diffs) > 1 else diffs[-1]
            paired[name] = {"observed_diff": observed,
                            "ci95": [lo, hi], "resamples": len(diffs),
                            "resampler_alignment_ok": aligned}
        else:
            paired[name] = {"observed_diff": observed,
                            "ci95": None, "resamples": len(diffs),
                            "resampler_alignment_ok": aligned}

    out = {
        "name": NAME,
        "accepted_artifact": digest_claim,
        "scope": "eval rows only (target years 2022-2023); the holdout was never opened",
        "rows": n_eval,
        "positives": n_pos,
        "train_positive_rate": train_rate,
        "references": references,
        "per_target_year": per_year,
        "paired_differences": paired,
        "notes": [
            "the full model is NOT computed here; the harness runner's baseline job trains it on these same rows and its figure is quoted beside these references when it exists",
            "persistence is the prior-year outcome measured, not recorded not-applicable: the scored rows are new target years of recurring charities",
            "intervals containing zero are inconclusive differences, not parity",
        ],
    }
    Path(args.report).write_text(json.dumps(out, indent=1) + "\n")
    print(f"REFERENCES rows={n_eval} positives={n_pos}")
    for k, v in references.items():
        print(f"  {k}: {v}")
    for k, v in paired.items():
        print(f"  paired {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
