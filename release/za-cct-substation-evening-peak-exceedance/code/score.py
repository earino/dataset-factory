#!/usr/bin/env python3
"""Simple references for the accepted za-cct-substation-evening-peak-exceedance artifact.

Runs ONLY after the qualification gate has passed and --accept has re-verified
the report against these exact bytes (run.sh enforces that order; this file
re-checks the accepted report and the artifact digests before its first metric,
so an accidental early invocation refuses to score). It reads the written CSVs,
never rewrites them, and computes every reference on the SAME eval rows. The
holdout is NEVER opened - it is the final test surface and stays sealed.

The task is an evening-peak exceedance question at the 06:00 SAST instant, so
the reference set takes this shape (every rate table is estimated ONLY from
train target days, 2022; scored on eval target days, 2023):

  * persistence_prev_evening - THE HEADROOM REFERENCE the candidate record
    names first: the same station's previous evening's exceedance label as
    the score. The prior-evening outcome is knowable in the real world at
    06:00 (the previous evening closed 10 hours before the instant) but is
    UNSHIPPABLE under the operator's P0 standard (a prior label shipped as a
    feature is exactly the fts-appeal-003 / queue-audit cross-row recovery),
    so it is RECOMPUTED HERE from the label columns of strictly-earlier
    same-station rows in train.csv + eval.csv (never the holdout; an eval
    row's previous day is always a train or eval row). INFORMATION ASYMMETRY,
    disclosed: the full model is NOT given the previous outcome while this
    reference reads it - trailing this reference is expected; the comparison
    must always be quoted with this note.
  * calendar_identity (the skill's calendar-only control: identity plus a
    seasonal prior): train-estimated exceedance rate of the row's
    station x month cell, with station-rate and global-rate fallbacks.
  * identity_only: train-estimated per-station rate (identity without season).
  * month_only: train-estimated per-month rate (season without identity).
  * morning_ratio: the physics reference built only from shipped features -
    morning_max / hist_morningpeak_mean_90, "how high is this morning's draw
    relative to the station's recent morning regime". A model that cannot
    beat this one-line rule adds nothing to the telemetry it is given.
  * global_rate: constant train rate (degenerate: no ranking information).
  * majority_class: fitted on train, measured against THIS split's labels.

The full model is NOT computed here: the benchmark runner's baseline job
trains and evaluates it on these same rows, and its figure is quoted beside
these references when it exists. Nothing in this file may run before
acceptance.

Eval is a single year (2023), so per-month eval reporting replaces the pooled
per-year check: exceedance prevalence and reference quality are reported by
calendar month, and the station-day clustering (positives concentrated on
regime days) is recorded as the dependence structure that clustered intervals
must respect.

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

NAME = "za-cct-substation-evening-peak-exceedance"
TARGET = "exceeds"
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

    # ---- scorer-side persistence recompute ------------------------------------
    # The previous evening's label is real-world knowable at 06:00 but unshippable
    # under the P0 standard, so it is recomputed here from the LABELS of
    # strictly-earlier same-station rows in train.csv + eval.csv only. The holdout
    # is never opened, and an eval row's previous day (2022-12-31 at the earliest)
    # is always a train or eval row, never a holdout row.
    history = {}
    for rows in (train, evald):
        for row in rows:
            history[(row["station"], row["date"])] = 1 if row[TARGET] == POSITIVE else 0

    def previous_day(date: str) -> str:
        import datetime as _dt
        return (_dt.date.fromisoformat(date) - _dt.timedelta(days=1)).isoformat()

    persistence = []
    for row in evald:
        prior = history.get((row["station"], previous_day(row["date"])))
        persistence.append(0.5 if prior is None else float(prior))

    # identity and seasonal tables from train only
    station_table, station_global = rate_table(train, ["station"])
    month_table, month_global = rate_table(train, ["month"])
    cell_table, cell_global = rate_table(train, ["station", "month"])

    def calendar_identity(row):
        return cell_table.get((row["station"], row["month"]),
                              station_table.get((row["station"],), cell_global))

    identity_only = [station_table.get((r["station"],), station_global) for r in evald]
    month_only = [month_table.get((r["month"],), month_global) for r in evald]
    climatology = [calendar_identity(r) for r in evald]

    def ratio(row):
        hist = float(row["hist_morningpeak_mean_90"])
        if hist <= 0:
            return 0.0
        return float(row["morning_max"]) / hist

    morning_ratio = [ratio(r) for r in evald]

    majority = int(train_rate >= 0.5)
    majority_accuracy = sum(1 for y in y_eval if y == majority) / len(y_eval)

    references = {
        "persistence_prev_evening": {"eval_auc": auc(y_eval, persistence),
                                     "brier": brier(y_eval, persistence)},
        "calendar_identity": {"eval_auc": auc(y_eval, climatology),
                              "brier": brier(y_eval, climatology)},
        "identity_only": {"eval_auc": auc(y_eval, identity_only),
                          "brier": brier(y_eval, identity_only)},
        "month_only": {"eval_auc": auc(y_eval, month_only),
                       "brier": brier(y_eval, month_only)},
        "morning_ratio": {"eval_auc": auc(y_eval, morning_ratio),
                          "brier": brier(y_eval, morning_ratio)},
        "global_rate": {"eval_auc": None, "brier": brier(y_eval, [train_rate] * n_eval),
                        "note": "constant score, no ranking information; degenerate control"},
        "majority_class": {"accuracy_this_split": majority_accuracy,
                           "note": "majority fitted on train, measured against this split's labels"},
    }

    # per-month eval reporting (eval is one year; the month is the structural axis)
    per_month = {}
    for month in sorted({r["month"] for r in evald}):
        idx = [i for i, r in enumerate(evald) if r["month"] == month]
        ys = [y_eval[i] for i in idx]
        entry = {"rows": len(idx), "positives": sum(ys)}
        for name, vector in (("persistence_prev_evening", persistence),
                             ("calendar_identity", climatology),
                             ("morning_ratio", morning_ratio)):
            entry[f"{name}_auc"] = auc(ys, [vector[i] for i in idx])
        per_month[month] = entry

    # station-day clustering evidence (the dependence structure for intervals)
    positive_days = sorted({r["date"] for r, y in zip(evald, y_eval) if y})
    per_station = defaultdict(lambda: [0, 0])
    for row, y in zip(evald, y_eval):
        per_station[row["station"]][y] += 1

    # ---- paired bootstrap: reference vs reference on identical rows ------------
    rng = random.Random(SEED)
    pairs = {"persistence_vs_calendar_identity": (persistence, climatology),
             "persistence_vs_morning_ratio": (persistence, morning_ratio),
             "calendar_identity_vs_morning_ratio": (climatology, morning_ratio),
             "persistence_vs_identity_only": (persistence, identity_only)}
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
                 "train": len(train), "train_positive_rate": round(train_rate, 6),
                 "eval_distinct_positive_days": len(positive_days)},
        "references": references,
        "per_eval_month": per_month,
        "dependence": {
            "distinct_positive_days": len(positive_days),
            "note": ("positives cluster city-wide on regime days; station-days "
                     "within one day are dependent and clustered intervals "
                     "(station, day) must be used for inference"),
            "per_station": {station: {"positives": v[1], "rows": v[0] + v[1]}
                            for station, v in sorted(per_station.items())},
        },
        "paired_bootstrap": paired,
        "notes": [
            "every rate table is estimated ONLY from train target days (2022)",
            "persistence_prev_evening is recomputed scorer-side from the labels "
            "of strictly-earlier same-station rows (train.csv + eval.csv only, "
            "holdout never opened) because a shipped prior-evening label is "
            "exactly the P0 cross-row recovery the feature design excludes; the "
            "full model does NOT receive this information, so the "
            "model-vs-persistence comparison is information-asymmetric by "
            "design and must be quoted with this note",
            "eval is a single year (2023): per-month reporting replaces the "
            "pooled per-year structural check; prevalence drift across splits "
            "(11.20% -> 8.39% -> 9.21%) is recorded in quality.json limitations",
            "the holdout was never opened by this stage",
            "the full model comes from the benchmark runner's baseline job on "
            "the same eval rows; its figure is quoted beside these references",
            "an interval containing zero is an inconclusive difference, not parity",
        ],
    }
    Path(args.report).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n",
                                 encoding="utf-8")
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
