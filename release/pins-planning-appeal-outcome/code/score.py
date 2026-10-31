#!/usr/bin/env python3
"""Simple references for the accepted pins-planning-appeal-outcome artifact.

Runs ONLY after the qualification gate has passed and --accept has re-verified
the report against these exact bytes (run.sh enforces that order; this file
re-checks the accepted report and the artifact digests before its first
metric, so an accidental early invocation refuses to score). It reads the
written CSVs, never rewrites them, and computes every reference on the SAME
eval rows. The holdout is never opened.

The task is an appeal-outcome question at the validation instant, so the
reference set takes this shape (every rate table is estimated ONLY from
training rows; scored on eval rows, validation instants 2020-2021):

  * lpa_hist_rate - THE HEADROOM REFERENCE the candidate record names first:
    the train-estimated historical allow rate of the row's LPA (global train
    rate for LPAs unseen in train). This is the LPA-persistence family.
  * persistence_last_outcome - the persistence form: the row's own
    lpa_last_outcome feature as the score (0.5 for the -1 no-prior sentinel),
    i.e. the most recent same-LPA prior decision.
  * procedure_type_rate - train-estimated rate by (procedure, casework type)
    with marginal and global fallbacks.
  * calendar_identity - train-estimated rate by (LPA, validation year) with
    LPA, year and global fallbacks: the calendar/identity control.
  * year_rate - train-estimated rate by validation year alone.
  * global_rate - constant train rate (degenerate: no ranking information,
    AUC undefined, reported as such).
  * majority_class - fitted on train, measured against THIS split's labels.

The full model is NOT computed here: the harness runner's baseline job
trains and evaluates it on these same rows, and its figure is quoted beside
these references when it exists. Nothing in this file may run before
acceptance.

Eval-only: the holdout is sealed until the design is frozen and the runner
evaluates it once. Per-validation-year reporting is mandatory (prevalence is
stable ~30% across years, but the composition of the panel shifts).

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

NAME = "pins-planning-appeal-outcome"
TARGET = "allowed"
POSITIVE = "1"
BOOTSTRAP = 150
SEED = 41


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
        raise SystemExit("refusing to score: the qualification report carries failed checks")
    digest_claim = ((report.get("artifact") or {}).get("artifact_version") or {}).get("digest")
    if not digest_claim:
        raise SystemExit("refusing to score: the accepted report carries no artifact digest")
    components = ((report.get("artifact") or {}).get("artifact_version") or {}).get("components") or []
    actual = {}
    for split_rel in ("public/train.csv", "public/eval.csv", "private/holdout.csv",
                      "meta.json", "quality.json"):
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

    # the headroom reference: LPA historical allow rate, train-estimated
    lpa_table, lpa_global = rate_table(train, ["lpa_name"])
    lpa_hist = scores_from(evald, lambda r: lpa_table.get((r["lpa_name"],), lpa_global))

    # persistence: the row's own last-outcome feature (0.5 for the -1 sentinel)
    persistence = scores_from(evald, lambda r: 0.5 if r["lpa_last_outcome"] == "-1"
                              else float(r["lpa_last_outcome"]))

    # procedure/casework-type base rates
    proc_table, _ = rate_table(train, ["procedure", "casework_type"])
    proc_marginal, proc_global = rate_table(train, ["procedure"])
    type_marginal, _ = rate_table(train, ["casework_type"])

    def proc_score(row):
        key = (row.get("procedure", ""), row.get("casework_type", ""))
        if key in proc_table:
            return proc_table[key]
        p, t = key
        if p in proc_marginal and t in type_marginal:
            return 0.5 * (proc_marginal[p] + type_marginal[t])
        if p in proc_marginal:
            return proc_marginal[p]
        if t in type_marginal:
            return type_marginal[t]
        return proc_global

    procedure_type = scores_from(evald, proc_score)

    # calendar/identity: (LPA, validation year) with fallbacks
    cal_table, _ = rate_table(train, ["lpa_name", "valid_year"])
    year_table, cal_global = rate_table(train, ["valid_year"])

    def cal_score(row):
        key = (row["lpa_name"], row["valid_year"])
        if key in cal_table:
            return cal_table[key]
        if (row["lpa_name"],) in lpa_table:
            return lpa_table[(row["lpa_name"],)]
        if (row["valid_year"],) in year_table:
            return year_table[(row["valid_year"],)]
        return cal_global

    calendar = scores_from(evald, cal_score)
    year_only = scores_from(evald, lambda r: year_table.get((r["valid_year"],), cal_global))

    majority = int(train_rate >= 0.5)
    majority_accuracy = sum(1 for y in y_eval if y == majority) / len(y_eval)

    references = {
        "lpa_hist_rate": {"eval_auc": auc(y_eval, lpa_hist), "brier": brier(y_eval, lpa_hist)},
        "persistence_last_outcome": {"eval_auc": auc(y_eval, persistence),
                                      "brier": brier(y_eval, persistence)},
        "procedure_type_rate": {"eval_auc": auc(y_eval, procedure_type),
                                "brier": brier(y_eval, procedure_type)},
        "calendar_identity": {"eval_auc": auc(y_eval, calendar),
                              "brier": brier(y_eval, calendar)},
        "year_rate": {"eval_auc": auc(y_eval, year_only),
                      "brier": brier(y_eval, year_only)},
        "global_rate": {"eval_auc": None, "brier": brier(y_eval, [train_rate] * n_eval),
                        "note": "constant score, no ranking information; degenerate control"},
        "majority_class": {"accuracy_this_split": majority_accuracy,
                           "note": "majority fitted on train, measured against this split's labels"},
    }

    # per-validation-year reporting (mandatory: panel composition shifts by year)
    per_year = {}
    for year in sorted({r["valid_year"] for r in evald}):
        idx = [i for i, r in enumerate(evald) if r["valid_year"] == year]
        ys = [y_eval[i] for i in idx]
        entry: dict = {"rows": len(idx), "positives": sum(ys)}
        for name, vector in (("lpa_hist_rate", lpa_hist),
                             ("persistence_last_outcome", persistence),
                             ("procedure_type_rate", procedure_type),
                             ("calendar_identity", calendar)):
            entry[f"{name}_auc"] = auc(ys, [vector[i] for i in idx])
        per_year[year] = entry

    # ---- paired bootstrap: reference vs reference on identical rows ------------
    rng = random.Random(SEED)
    pairs = {"lpa_hist_vs_calendar": (lpa_hist, calendar),
             "lpa_hist_vs_procedure_type": (lpa_hist, procedure_type),
             "persistence_vs_lpa_hist": (persistence, lpa_hist)}
    paired = {}
    for name, (a, b) in pairs.items():
        observed_a, observed_b = auc(y_eval, a), auc(y_eval, b)
        observed = (observed_a - observed_b) if (observed_a is not None
                                                 and observed_b is not None) else None
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

    # LPA-clustered bootstrap for the headroom reference's own AUC (dependence:
    # positives cluster by LPA beyond the row count)
    cluster_map = defaultdict(list)
    for i, row in enumerate(evald):
        cluster_map[row["lpa_name"]].append(i)
    clusters = [v for v in cluster_map.values() if v]
    cluster_aucs = []
    for _ in range(BOOTSTRAP):
        drawn_clusters = [clusters[rng.randrange(len(clusters))] for _ in range(len(clusters))]
        idx = [i for c in drawn_clusters for i in c]
        ys = [y_eval[i] for i in idx]
        va = auc(ys, [lpa_hist[i] for i in idx])
        vb = auc(ys, [persistence[i] for i in idx])
        if va is None or vb is None:
            continue
        cluster_aucs.append(va - vb)
    cluster_aucs.sort()
    hist_auc = auc(y_eval, lpa_hist)
    pers_auc = auc(y_eval, persistence)
    hist_vs_pers = (hist_auc - pers_auc) if (hist_auc is not None
                                             and pers_auc is not None) else None
    if len(cluster_aucs) > 1:
        ci95 = [cluster_aucs[int(0.025 * len(cluster_aucs))],
                cluster_aucs[int(0.975 * len(cluster_aucs)) - 1]]
    else:
        ci95 = None
    lpa_cluster = {
        "unit": "LPA (appeal outcomes of one planning authority are correlated)",
        "lpa_hist_vs_persistence_diff": hist_vs_pers,
        "ci95": ci95,
        "resamples": len(cluster_aucs),
    }

    out = {
        "name": NAME,
        "accepted_artifact": digest_claim,
        "scope": "eval rows only (validation instants 2020-2021); the holdout was never opened",
        "rows": n_eval,
        "positives": n_pos,
        "train_positive_rate": train_rate,
        "references": references,
        "per_validation_year": per_year,
        "paired_differences": paired,
        "lpa_clustered_bootstrap": lpa_cluster,
        "notes": [
            "the full model is NOT computed here; the harness runner's baseline job trains it "
            "on these same rows and its figure is quoted beside these references when it exists",
            "lpa_hist_rate is the headroom reference named in the candidate record: a model must "
            "demonstrate headroom over it under this protocol for a positive verdict",
            "persistence is measured, not declared not-applicable: every eval row's LPA has a "
            "train-era decided-case history for 92%+ of rows (the -1 sentinel marks the rest)",
            "intervals containing zero are inconclusive differences, not parity",
        ],
    }
    Path(args.report).write_text(json.dumps(out, indent=1) + "\n")
    print(f"REFERENCES rows={n_eval} positives={n_pos}")
    for k, v in references.items():
        print(f"  {k}: {v}")
    for k, v in paired.items():
        print(f"  paired {k}: {v}")
    print(f"  lpa_clustered lpa_hist_vs_persistence: {lpa_cluster}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
