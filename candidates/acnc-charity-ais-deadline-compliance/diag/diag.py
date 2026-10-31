#!/usr/bin/env python3
"""Per-row diagnostic for the accepted acnc-charity-ais-deadline-compliance artifact.

The runner contract (train.py/validate.py) prints only the aggregate eval AUC, so
job acnc-baseline-001 could not put an interval around model-vs-reference. This
job preserves the per-row model scores and computes, on the SAME 80,298 eval rows:

  * the model's per-row predict_proba (validate.py's exact call: the target
    column is removed before the call), and its AUC/Brier - the AUC computed by
    sklearn (the contract's own metric) AND by the independent tie-aware midrank
    implementation below, so the decisive figure has two implementations;
  * the construction references recomputed from the shipped artifact bytes by a
    second implementation (this file reads the CSVs as strings and re-derives
    every score from the recorded definitions in source/score.py, never by
    running it) - a replication check against job acnc-002's figures;
  * paired row-level bootstrap intervals, model vs persistence_momentum (the
    dominant simple reference), model vs persistence_flag, model vs
    identity_history_rate and model vs calendar_size_rate: 150 resamples,
    seed 31, the construction references' own protocol (fresh generator per
    comparison), so the intervals are mutually comparable with the recorded
    reference-vs-reference intervals;
  * a charity-cluster bootstrap for the decisive model-vs-momentum comparison:
    eval rows cluster by charity (abn, a declared property - a charity may
    appear in multiple target years), so a dependence-aware interval resamples
    CHARITIES, not rows. Recorded beside the row-level interval, never instead
    of it;
  * a resampler canary: momentum_vs_calendar recomputed here and compared with
    the interval recorded by job acnc-002 (observed 0.13293, CI
    [0.12746, 0.13909]) - a large-gap pair whose interval is already known, so
    a resampler that collapses differences to noise cannot pass silently;
  * per-target-year model AUC/Brier beside the measured per-year references.

Rows are NOT independent (per-charity clustering is declared); the row-level
intervals are reported for protocol comparability and the cluster interval is
the dependence-aware one. Nothing is re-tuned: the label, threshold, splits and
the runner template's own model configuration are frozen. The holdout is never
read. No number is computed before run.sh has re-accepted the fetched bytes
against the gate's report.

Usage: diag.py <extract-dir> <workdir> <output-dir> [runner_files.json]
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import random
import re
import runpy
import sys
import warnings
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

BOOTSTRAP = 150
SEED = 31
TARGET = "failed_by_due"
POSITIVE = 1
# Figures recorded by earlier jobs on this same artifact (the collected
# references json of job acnc-002 and the collected baseline_result.json of job
# acnc-baseline-001). Carried here as labelled constants so the replication
# checks are explicit, never silently assumed.
RECORDED = {
    "persistence_momentum_auc": {"value": 0.7006129103762208, "job": "acnc-002"},
    "persistence_flag_auc": {"value": 0.6710197939061475, "job": "acnc-002"},
    "calendar_size_rate_auc": {"value": 0.5676793070279146, "job": "acnc-002"},
    "identity_history_rate_auc": {"value": 0.6890741926945402, "job": "acnc-002"},
    "majority_class_accuracy": {"value": 0.741799297616379, "job": "acnc-002"},
    "full_model_eval_auc": {"value": 0.6862, "job": "acnc-baseline-001",
                            "tolerance": 5e-4,
                            "note": "the runner contract prints 4 decimals; the "
                                    "baseline job's dependency-versions.txt pins "
                                    "the exact package versions"},
    "momentum_vs_calendar": {"observed_diff": 0.13293360334830617,
                             "ci95": [0.12745563094993873, 0.13908801844665497],
                             "job": "acnc-002"},
    "per_year_references": {
        "2022": {"rows": 39102, "positives": 10129,
                 "persistence_momentum_auc": 0.6926370627928814,
                 "persistence_flag_auc": 0.6680586441190355,
                 "calendar_size_rate_auc": 0.5713666310128627,
                 "identity_history_rate_auc": 0.7032869177817728},
        "2023": {"rows": 41196, "positives": 10604,
                 "persistence_momentum_auc": 0.7083189584824507,
                 "persistence_flag_auc": 0.6738255941548859,
                 "calendar_size_rate_auc": 0.5639611931369349,
                 "identity_history_rate_auc": 0.6746735474909602},
    },
}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def versions() -> dict:
    import importlib.metadata as metadata
    found = {"python": platform.python_version()}
    for package in ("pandas", "numpy", "xgboost", "scikit-learn"):
        try:
            found[package] = metadata.version(package)
        except Exception:
            found[package] = None
    return found


def auc_midrank(scores, w_pos, w_neg) -> float | None:
    """Tie-aware AUC over weighted rows (unit weights give the plain midrank AUC).

    Same arithmetic as the construction score.py's rank-sum form, written
    independently: U = sum over tie groups of pos_g * (neg ranked below + half
    the tied neg). The same implementation shipped in the ipo-tm diag, where it
    was cross-checked against sklearn in tests/test_ipo_tm_diag.py.
    """
    scores = np.asarray(scores, dtype=float)
    w_pos = np.asarray(w_pos, dtype=float)
    w_neg = np.asarray(w_neg, dtype=float)
    total_pos = float(w_pos.sum())
    total_neg = float(w_neg.sum())
    if total_pos <= 0 or total_neg <= 0:
        return None
    order = np.argsort(scores, kind="mergesort")
    s = scores[order]
    change = np.empty(len(s), dtype=bool)
    change[0] = True
    change[1:] = s[1:] != s[:-1]
    gid = np.cumsum(change) - 1
    g_pos = np.bincount(gid, weights=w_pos[order])
    g_neg = np.bincount(gid, weights=w_neg[order])
    cum_neg_before = np.cumsum(g_neg) - g_neg
    u = float((g_pos * (cum_neg_before + 0.5 * g_neg)).sum())
    return u / (total_pos * total_neg)


def plain_auc(labels, scores) -> float | None:
    labels = np.asarray(labels)
    scores = np.asarray(scores, dtype=float)
    if len(set(scores.tolist())) == 1:
        return None  # constant scores carry no ranking information
    return auc_midrank(scores, labels, 1.0 - labels)


def brier(labels, probabilities) -> float | None:
    labels = np.asarray(labels, dtype=float)
    probabilities = np.asarray(probabilities, dtype=float)
    if not len(labels):
        return None
    return float(((probabilities - labels) ** 2).mean())


def _interval(differences) -> dict:
    differences = sorted(differences)
    if not differences:
        return {"resamples": 0, "ci95": None}
    low = differences[int(0.025 * len(differences))]
    high = differences[int(0.975 * len(differences)) - 1] if len(differences) > 1 \
        else differences[-1]
    return {"resamples": len(differences),
            "mean_difference": round(sum(differences) / len(differences), 6),
            "ci95": [round(low, 6), round(high, 6)],
            "interval_excludes_zero": bool(low > 0 or high < 0)}


def paired_row_bootstrap(labels, scores_a, scores_b) -> dict:
    """Paired bootstrap of AUC(A)-AUC(B) on identical eval rows.

    Protocol identical to the construction score.py: 150 resamples, seed 31,
    fresh generator per comparison, row-level resampling with replacement,
    tie-aware AUC over the weighted resample, percentile interval read the
    same way (low at int(0.025*n), high at int(0.975*n)-1).

    counts[i] = number of times row i was drawn; the drawn row carries ITS
    OWN label (y[i]), never the label of the draw position. Positional
    alignment (weights=y over draw positions) was the defect of the ipo
    diag-001 resampler: it scrambles which label belongs to which drawn row
    and collapses every AUC difference to noise - pinned there by
    tests/test_ipo_tm_diag.py::test_bootstrap_weights_align_labels_with_drawn_rows
    and watched here by the momentum_vs_calendar canary against job
    acnc-002's recorded interval.
    """
    y = np.asarray(labels, dtype=float)
    n = len(y)
    if not n:
        return {"note": "no rows"}
    rng = random.Random(SEED)
    differences = []
    for _ in range(BOOTSTRAP):
        idx = np.asarray([rng.randrange(n) for _ in range(n)])
        counts = np.bincount(idx, minlength=n).astype(float)
        w_pos = counts * y
        w_neg = counts * (1.0 - y)
        auc_a = auc_midrank(scores_a, w_pos, w_neg)
        auc_b = auc_midrank(scores_b, w_pos, w_neg)
        if auc_a is not None and auc_b is not None:
            differences.append(auc_a - auc_b)
    result = _interval(differences)
    result["note"] = ("paired row-level bootstrap on identical eval rows "
                      "(150 resamples, seed 31, the construction references' "
                      "protocol); eval rows cluster by charity, so the "
                      "dependence-aware interval is the charity-cluster one "
                      "recorded beside this; an interval containing zero is "
                      "inconclusive, not parity")
    return result


def paired_cluster_bootstrap(labels, scores_a, scores_b, clusters) -> dict:
    """Paired bootstrap that resamples CHARITIES (dependence-aware).

    clusters[i] is the charity (abn) of row i. Each resample draws
    len(distinct charities) charities with replacement and every drawn
    charity carries ALL its eval rows, each such row weighted by the number of
    times its charity was drawn. Same seed protocol as the row-level variant.
    """
    y = np.asarray(labels, dtype=float)
    n = len(y)
    uniq = sorted(set(clusters))
    n_c = len(uniq)
    position = {c: i for i, c in enumerate(uniq)}
    rows_of = [[] for _ in uniq]
    for i, c in enumerate(clusters):
        rows_of[position[c]].append(i)
    sizes = np.asarray([len(r) for r in rows_of], dtype=np.int64)
    starts = np.concatenate([[0], np.cumsum(sizes)[:-1]])
    rows_sorted = np.asarray([r for group in rows_of for r in group], dtype=np.int64)

    rng = random.Random(SEED)
    differences = []
    for _ in range(BOOTSTRAP):
        drawn = np.asarray([rng.randrange(n_c) for _ in range(n_c)])
        rep = sizes[drawn]
        total = int(rep.sum())
        if not total:
            continue
        out_starts = np.repeat(starts[drawn], rep)
        group_offset = np.arange(total) - np.repeat(np.cumsum(rep) - rep, rep)
        rows = rows_sorted[out_starts + group_offset]
        counts = np.bincount(rows, minlength=n).astype(float)
        w_pos = counts * y
        w_neg = counts * (1.0 - y)
        auc_a = auc_midrank(scores_a, w_pos, w_neg)
        auc_b = auc_midrank(scores_b, w_pos, w_neg)
        if auc_a is not None and auc_b is not None:
            differences.append(auc_a - auc_b)
    result = _interval(differences)
    result["clusters"] = n_c
    result["rows_per_cluster"] = {"min": int(sizes.min()), "max": int(sizes.max()),
                                  "mean": round(float(sizes.mean()), 4)}
    result["note"] = ("paired charity-cluster bootstrap on identical eval rows "
                      "(150 resamples, seed 31, whole-charity resampling): the "
                      "dependence-aware interval for a panel whose rows "
                      "cluster by charity (declared property); an interval "
                      "containing zero is inconclusive, not parity")
    return result


def rate_table_second(train_keys, train_y):
    """Train-fit positive rate per key, plus the global rate - second implementation."""
    totals: dict = {}
    positives: dict = {}
    for key, y in zip(train_keys, train_y):
        totals[key] = totals.get(key, 0) + 1
        if y:
            positives[key] = positives.get(key, 0) + 1
    table = {key: positives.get(key, 0) / total for key, total in totals.items()}
    global_rate = float(np.asarray(train_y, dtype=float).mean())
    return table, global_rate


def calendar_size_scores(train_s, train_y, eval_s, global_rate):
    """Second implementation of score.py's cal_score: (month, size) rate with
    the recorded backoff blend -> month -> size -> global."""
    pair_table, _ = rate_table_second(
        list(zip(train_s["prior_period_end_month"], train_s["charity_size_code"])),
        train_y)
    month_table, _ = rate_table_second(train_s["prior_period_end_month"].tolist(), train_y)
    size_table, _ = rate_table_second(train_s["charity_size_code"].tolist(), train_y)

    def score(row):
        key = (row.get("prior_period_end_month", ""), row.get("charity_size_code", ""))
        if key in pair_table:
            return pair_table[key]
        m, s = key
        if s in size_table and m in month_table:
            return 0.5 * (month_table[m] + size_table[s])
        if m in month_table:
            return month_table[m]
        if s in size_table:
            return size_table[s]
        return global_rate

    return [score(row) for row in eval_s.to_dict("records")], {
        "pair_levels": len(pair_table), "month_levels": len(month_table),
        "size_levels": len(size_table)}


def agrees(recomputed, recorded, tolerance=5e-5) -> bool:
    return recomputed is not None and abs(recomputed - recorded) < tolerance


def main() -> int:
    extract, workdir, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    runner_json = Path(sys.argv[4]) if len(sys.argv) > 4 else None

    task = json.loads((workdir / "task.json").read_text())
    if task["target"] != TARGET or task["positive_label"] != POSITIVE:
        print("unexpected task contract", file=sys.stderr)
        return 1
    declared = json.loads(runner_json.read_text()) if runner_json and runner_json.is_file() else {}

    # ---- the shipped bytes, read as strings the way the gate's rows read ----
    train_s = pd.read_csv(extract / "public" / "train.csv", dtype=str, keep_default_na=False)
    eval_s = pd.read_csv(extract / "public" / "eval.csv", dtype=str, keep_default_na=False)
    for frame, name in ((train_s, "train"), (eval_s, "eval")):
        values = set(frame[TARGET].tolist())
        if not values <= {"0", "1"}:
            print(f"unexpected {TARGET} values in {name}: {sorted(values)[:5]}", file=sys.stderr)
            return 1
    train_y = (train_s[TARGET] == "1").to_numpy()
    eval_y = (eval_s[TARGET] == "1").to_numpy()
    train_rate = float(train_y.mean())
    n_eval = len(eval_y)

    # ---- references, recomputed from the shipped bytes ---------------------
    momentum = np.asarray(eval_s["prior_lateness_days"].astype(float))
    flag = np.asarray(eval_s["prior_lateness_positive"].astype(float))
    calendar, cal_meta = calendar_size_scores(train_s, train_y, eval_s, train_rate)
    calendar = np.asarray(calendar, dtype=float)
    ident_table, ident_global = rate_table_second(train_s["abn"].tolist(), train_y)
    identity = np.asarray(
        [ident_table.get((row["abn"],), ident_global) for row in eval_s.to_dict("records")],
        dtype=float)
    majority = 1 if train_rate >= 0.5 else 0
    majority_accuracy = float((eval_y == majority).mean())

    replication = {
        "persistence_momentum_auc": {"recomputed": plain_auc(eval_y, momentum),
                                      "recorded": RECORDED["persistence_momentum_auc"]["value"]},
        "persistence_flag_auc": {"recomputed": plain_auc(eval_y, flag),
                                  "recorded": RECORDED["persistence_flag_auc"]["value"]},
        "calendar_size_rate_auc": {"recomputed": plain_auc(eval_y, calendar),
                                    "recorded": RECORDED["calendar_size_rate_auc"]["value"]},
        "identity_history_rate_auc": {"recomputed": plain_auc(eval_y, identity),
                                       "recorded": RECORDED["identity_history_rate_auc"]["value"]},
        "majority_class_accuracy": {"recomputed": majority_accuracy,
                                     "recorded": RECORDED["majority_class_accuracy"]["value"]},
    }
    for entry in replication.values():
        entry["agrees"] = agrees(entry["recomputed"], entry["recorded"])

    years = eval_s["target_year"].tolist()
    per_year = {}
    for year in sorted(set(years)):
        idx = [i for i, y_ in enumerate(years) if y_ == year]
        ys = eval_y[idx]
        recorded_year = RECORDED["per_year_references"][year]
        entry = {
            "rows": len(idx), "positives": int(ys.sum()),
            "model_auc": None, "model_brier": None,
            "persistence_momentum_auc": plain_auc(ys, momentum[idx]),
            "persistence_flag_auc": plain_auc(ys, flag[idx]),
            "calendar_size_rate_auc": plain_auc(ys, calendar[idx]),
            "identity_history_rate_auc": plain_auc(ys, identity[idx]),
        }
        assert entry["rows"] == recorded_year["rows"], f"row count drift for {year}"
        assert entry["positives"] == recorded_year["positives"], f"positive drift for {year}"
        for key in ("persistence_momentum_auc", "persistence_flag_auc",
                    "calendar_size_rate_auc", "identity_history_rate_auc"):
            entry[key + "_agrees"] = agrees(entry[key], recorded_year[key])
        per_year[year] = entry
    del train_s

    # ---- the model, fit by the benchmark's own train.py (verbatim) ---------
    os.chdir(workdir)
    captured = io.StringIO()
    with redirect_stdout(captured):
        ns = runpy.run_path("train.py", run_name="__train__")
    train_print = captured.getvalue()
    printed = re.findall(r"Eval AUC:\s*([0-9.]+)", train_print)
    predict_proba = ns.get("predict_proba")
    if not callable(predict_proba):
        print("train.py defined no callable predict_proba", file=sys.stderr)
        return 2
    eval_model = pd.read_csv(workdir / "data" / "eval.csv")
    model_scores = np.asarray(predict_proba(eval_model.drop(columns=[TARGET])), dtype=float).ravel()
    del eval_model
    if len(model_scores) != n_eval:
        print("predict_proba returned the wrong number of rows", file=sys.stderr)
        return 2
    if not np.isfinite(model_scores).all() or model_scores.min() < 0 or model_scores.max() > 1:
        print("predict_proba returned values outside [0,1]", file=sys.stderr)
        return 2

    model_auc_sklearn = float(roc_auc_score(eval_y, model_scores))
    model_auc_midrank = plain_auc(eval_y, model_scores)
    model_brier_value = brier(eval_y, model_scores)
    for year, entry in per_year.items():
        idx = [i for i, y_ in enumerate(years) if y_ == year]
        entry["model_auc"] = float(roc_auc_score(eval_y[idx], model_scores[idx]))
        entry["model_brier"] = brier(eval_y[idx], model_scores[idx])

    # ---- per-row evidence ---------------------------------------------------
    with (out / "per_row_scores.csv").open("w", newline="") as handle:
        handle.write("row_id,abn,target_year,label,model_score,persistence_momentum,persistence_flag\n")
        for i in range(n_eval):
            handle.write(f"{eval_s['row_id'].iloc[i]},{eval_s['abn'].iloc[i]},"
                         f"{years[i]},{int(eval_y[i])},"
                         f"{model_scores[i]:.6f},{momentum[i]:.6f},{flag[i]:.6f}\n")

    # ---- paired intervals ---------------------------------------------------
    canary = paired_row_bootstrap(eval_y, momentum, calendar)
    canary_check = {
        "recomputed_mean": canary.get("mean_difference"),
        "recorded_observed": RECORDED["momentum_vs_calendar"]["observed_diff"],
        "recomputed_ci95": canary.get("ci95"),
        "recorded_ci95": RECORDED["momentum_vs_calendar"]["ci95"],
    }
    canary_check["mean_agrees"] = (
        canary_check["recomputed_mean"] is not None
        and abs(canary_check["recomputed_mean"] - canary_check["recorded_observed"]) < 0.01)
    canary_check["ci_agrees"] = (
        canary_check["recomputed_ci95"] is not None
        and abs(canary_check["recomputed_ci95"][0] - canary_check["recorded_ci95"][0]) < 0.02
        and abs(canary_check["recomputed_ci95"][1] - canary_check["recorded_ci95"][1]) < 0.02)

    comparisons = {}
    for name, ref in (("persistence_momentum", momentum),
                      ("persistence_flag", flag),
                      ("identity_history_rate", identity),
                      ("calendar_size_rate", calendar)):
        ref_auc = plain_auc(eval_y, ref)
        if ref_auc is None:
            print(f"reference {name} produced no ranking; refusing to compare", file=sys.stderr)
            return 3
        comparisons[f"model_vs_{name}"] = {
            "observed_model_auc": model_auc_sklearn,
            "observed_reference_auc": ref_auc,
            "observed_difference": round(model_auc_sklearn - ref_auc, 6),
            "row_level": paired_row_bootstrap(eval_y, model_scores, ref),
        }
    clusters = eval_s["abn"].tolist()
    comparisons["model_vs_persistence_momentum"]["charity_cluster"] = \
        paired_cluster_bootstrap(eval_y, model_scores, momentum, clusters)

    # ---- the runner files, provably unmodified ------------------------------
    actual = {name: sha256_of(workdir / name) for name in
              ("train.py", "validate.py", "validate.sh") if (workdir / name).is_file()}

    validate_log = (out / "validate.log").read_text() if (out / "validate.log").is_file() else ""
    contract_auc = re.findall(
        r"eval AUC via predict_proba \(target column removed\):\s*([0-9.]+)", validate_log)

    result = {
        "name": "acnc-charity-ais-deadline-compliance",
        "job": "acnc-diag-001",
        "purpose": "per-row model scores and model-vs-reference paired intervals on the "
                   "accepted artifact, completing the baseline triad measured by "
                   "acnc-baseline-001",
        "accepted_artifact": "70b7e7175ad45c8ad831c6246c3f33291e4874d0471094b4e183979ab295cabd",
        "scope": "eval rows only (target years 2022-2023); the holdout was never read",
        "rows": n_eval,
        "positives": int(eval_y.sum()),
        "model": {
            "eval_auc_sklearn": model_auc_sklearn,
            "eval_auc_midrank_second_implementation": model_auc_midrank,
            "eval_brier": model_brier_value,
            "train_py_printed_auc": float(printed[-1]) if printed else None,
            "validate_py_printed_auc": float(contract_auc[-1]) if contract_auc else None,
            "recorded_baseline_auc": RECORDED["full_model_eval_auc"]["value"],
            "agrees_with_baseline_print": abs(model_auc_sklearn
                                              - RECORDED["full_model_eval_auc"]["value"])
                                           < RECORDED["full_model_eval_auc"]["tolerance"],
            "two_implementations_agree": (model_auc_midrank is not None
                                          and abs(model_auc_sklearn - model_auc_midrank) < 1e-9),
        },
        "reference_replication": replication,
        "per_target_year": per_year,
        "resampler_canary_momentum_vs_calendar": canary_check,
        "comparisons": comparisons,
        "runner_files": {"bundled_sha256": actual, "expected_sha256": declared,
                         "unmodified": bool(declared)
                         and all(declared.get(nm) == value for nm, value in actual.items())},
        "dependencies": versions(),
        "clustering": "eval rows cluster by charity (abn, declared: a charity may appear "
                      "in multiple target years); the row-level intervals are recorded for "
                      "protocol comparability and the charity-cluster interval is the "
                      "dependence-aware one for the decisive comparison",
        "per_row_scores": "per_row_scores.csv (row_id, abn, target_year, label, model_score, "
                          "persistence_momentum, persistence_flag; eval rows only)",
        "holdout": "never read; no holdout figure exists in this job",
    }
    (out / "diag_result.json").write_text(json.dumps(result, indent=2) + "\n")

    checks = {
        "references_agree": all(entry["agrees"] for entry in replication.values()),
        "per_year_references_agree": all(
            entry.get(key + "_agrees")
            for entry in per_year.values()
            for key in ("persistence_momentum_auc", "persistence_flag_auc",
                        "calendar_size_rate_auc", "identity_history_rate_auc")),
        "model_matches_baseline": result["model"]["agrees_with_baseline_print"],
        "model_two_implementations_agree": result["model"]["two_implementations_agree"],
        "train_validate_prints_agree": (printed and contract_auc
                                        and abs(float(printed[-1]) - float(contract_auc[-1])) < 5e-4),
        "canary_mean_agrees": canary_check["mean_agrees"],
        "canary_ci_agrees": canary_check["ci_agrees"],
        "runner_unmodified": result["runner_files"]["unmodified"],
        "cluster_interval_computed": comparisons["model_vs_persistence_momentum"]
                                     .get("charity_cluster", {}).get("ci95") is not None,
    }
    print(json.dumps({"model_eval_auc": model_auc_sklearn,
                      "observed_model_vs_momentum":
                          comparisons["model_vs_persistence_momentum"]["observed_difference"],
                      "row_level_ci95":
                          comparisons["model_vs_persistence_momentum"]["row_level"]["ci95"],
                      "charity_cluster_ci95":
                          comparisons["model_vs_persistence_momentum"]["charity_cluster"]["ci95"],
                      "checks": checks}, indent=2))
    return 0 if all(checks.values()) else 5


if __name__ == "__main__":
    raise SystemExit(main())
