#!/usr/bin/env python3
"""Per-row diagnostic for the accepted ipo-trademark-registration-outcome artifact.

The runner contract (train.py/validate.py) prints only the aggregate eval AUC, so
job ipo-tm-baseline-001 could not put an interval around model-vs-reference. This
job preserves the per-row model scores and computes, on the SAME 97,274 eval rows:

  * the model's per-row predict_proba (validate.py's exact call: the target
    column is removed before the call), and its AUC/Brier;
  * the construction references recomputed from the shipped artifact bytes by a
    second implementation (this file reads the CSVs with pandas and re-derives
    every rate table from the recorded definitions, not by running score.py) -
    a replication check against job ipo-tm-004's figures;
  * paired row-level bootstrap intervals, model vs mark_type_rate (the dominant
    simple reference and the cheapest comparator a model must beat), model vs
    nice_class_rate (the required comparator) and model vs calendar_month_rate
    (the calendar control): 150 resamples, seed 31, the construction
    references' own protocol, so the intervals are mutually comparable;
  * per-filing-year model AUC/Brier beside the references, against the
    measured cohort prevalence.

Rows are single applications keyed by a unique tm_number; no owner or series
identity is shipped, so no dependence cluster is measurable from the shipped
columns. Intervals are therefore row-level only and that limitation is
recorded here rather than papered over with a pseudo-cluster.

Nothing is re-tuned: the label, threshold, splits and the runner template's own
model configuration are frozen. The holdout is never read. No number is
computed before run.sh has re-accepted the fetched bytes against the gate's
report.

Usage: diag.py <extract-dir> <workdir> <output-dir> [runner_files.json]
"""
from __future__ import annotations

import csv
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
TARGET = "registered"
POSITIVE = "1"
CLASS_COLUMNS = [f"class{i}" for i in range(1, 46)]
# Figures recorded by earlier jobs on this same artifact (record.json and the
# collected references json): ipo-tm-004 (construction references,
# post-acceptance) and ipo-tm-baseline-001 (runner-contract baseline). Carried
# here as labelled constants so the replication checks are explicit, never
# silently assumed. The model AUC is the contract's own 4-decimal print.
RECORDED = {
    "nice_class_rate_auc": {"value": 0.542050096312312, "job": "ipo-tm-004"},
    "mark_type_rate_auc": {"value": 0.5649860521366877, "job": "ipo-tm-004"},
    "owner_country_rate_auc": {"value": 0.5190639759221086, "job": "ipo-tm-004"},
    "calendar_month_rate_auc": {"value": 0.49717530762266227, "job": "ipo-tm-004"},
    "category_rate_auc": {"value": 0.5030650964271485, "job": "ipo-tm-004"},
    "series_flag_rate_auc": {"value": 0.5212537612864133, "job": "ipo-tm-004"},
    "majority_class_accuracy": {"value": 0.8398852725291445, "job": "ipo-tm-004"},
    "full_model_eval_auc": {"value": 0.6224, "job": "ipo-tm-baseline-001",
                            "tolerance": 5e-4,
                            "note": "the runner contract prints 4 decimals; the "
                                    "baseline job's dependency-versions.txt pins "
                                    "the exact package versions"},
    "nice_class_per_year_auc": {"2013": 0.5412071590589789, "2014": 0.5428658105024148,
                                "job": "ipo-tm-004"},
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
    the tied neg). Cross-checked against sklearn in tests/test_ipo_tm_diag.py.
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


def paired_row_bootstrap(labels, scores_a, scores_b) -> dict:
    """Paired bootstrap of AUC(A)-AUC(B) on identical eval rows.

    Protocol identical to the construction score.py: 150 resamples, seed 31,
    fresh generator per comparison, row-level resampling with replacement,
    tie-aware AUC over the weighted resample, percentile interval read the
    same way (low at int(0.025*n), high at int(0.975*n)-1).
    """
    y = np.asarray(labels, dtype=float)
    n = len(y)
    if not n:
        return {"note": "no rows"}
    rng = random.Random(SEED)
    differences = []
    for _ in range(BOOTSTRAP):
        idx = np.asarray([rng.randrange(n) for _ in range(n)])
        # counts[i] = number of times row i was drawn; the drawn row carries ITS
        # OWN label (y[i]), never the label of the draw position. Positional
        # alignment (weights=y over draw positions) was the defect of the first
        # implementation: it scrambles which label belongs to which drawn row and
        # collapses every AUC difference to noise - caught by reading the printed
        # mean against the observed gap, and pinned by
        # tests/test_ipo_tm_diag.py::test_bootstrap_weights_align_labels_with_drawn_rows.
        counts = np.bincount(idx, minlength=n).astype(float)
        w_pos = counts * y
        w_neg = counts * (1.0 - y)
        auc_a = auc_midrank(scores_a, w_pos, w_neg)
        auc_b = auc_midrank(scores_b, w_pos, w_neg)
        if auc_a is not None and auc_b is not None:
            differences.append(auc_a - auc_b)
    if not differences:
        return {"note": "degenerate resamples (a split lost one class)"}
    differences.sort()
    low = differences[int(0.025 * len(differences))]
    high = differences[int(0.975 * len(differences)) - 1]
    return {"resamples": len(differences),
            "mean_difference": round(sum(differences) / len(differences), 6),
            "ci95_low": round(low, 6),
            "ci95_high": round(high, 6),
            "interval_excludes_zero": bool(low > 0 or high < 0),
            "note": "paired row-level bootstrap on identical eval rows "
                    "(150 resamples, seed 31, the construction references' "
                    "protocol); an interval containing zero is inconclusive, "
                    "not parity"}


def rate_scores(train_keys, train_y, eval_keys) -> tuple[list, dict]:
    """Train-fit positive rate per level with global-rate backoff.

    train_keys/eval_keys are per-row level keys (built from the frame columns).
    Second implementation of the construction score.py's RateTable, from the
    recorded definitions.
    """
    totals: dict = {}
    positives: dict = {}
    for key, y in zip(train_keys, train_y):
        totals[key] = totals.get(key, 0) + 1
        if y:
            positives[key] = positives.get(key, 0) + 1
    global_rate = float(train_y.mean())
    table = {key: positives.get(key, 0) / total for key, total in totals.items()}
    scores = [table.get(key, global_rate) for key in eval_keys]
    return scores, {"levels": len(table)}


def class_rate_scores(train_frame, train_y, eval_frame, train_rate):
    """Required comparator: mean train rate over the row's assigned Nice classes.

    Second implementation of the construction score.py's ClassRateTable:
    backoff to the global train rate when a class is unseen in train or no
    class is assigned.
    """
    totals: dict = {}
    positives: dict = {}
    for column in CLASS_COLUMNS:
        mask = (train_frame[column] == "1").to_numpy()
        total = int(mask.sum())
        if total:
            totals[column] = total
            positives[column] = int((mask & (train_y == 1)).sum())
    table = {column: positives[column] / totals[column] for column in totals}
    rates = np.array([table.get(column, np.nan) for column in CLASS_COLUMNS])
    assigned = (eval_frame[CLASS_COLUMNS].to_numpy() == "1")
    values = np.where(assigned, np.broadcast_to(rates, assigned.shape), np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        scores = np.nanmean(values, axis=1)
    scores = np.where(np.isnan(scores), train_rate, scores)
    no_class_rows = int((~assigned.any(axis=1)).sum())
    return scores.tolist(), {"classes_seen": len(table), "eval_no_class_rows": no_class_rows}


def agrees(recomputed, recorded, tolerance=5e-5) -> bool:
    return recomputed is not None and abs(recomputed - recorded) < tolerance


def main() -> int:
    extract, workdir, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    runner_json = Path(sys.argv[4]) if len(sys.argv) > 4 else None

    task = json.loads((workdir / "task.json").read_text())
    if task["target"] != TARGET or str(task["positive_label"]) != POSITIVE:
        print("unexpected task contract", file=sys.stderr)
        return 1

    # ---- the shipped bytes, read as strings the way the gate's rows read ----
    train_s = pd.read_csv(extract / "public" / "train.csv", dtype=str, keep_default_na=False)
    eval_s = pd.read_csv(extract / "public" / "eval.csv", dtype=str, keep_default_na=False)
    for frame, name in ((train_s, "train"), (eval_s, "eval")):
        values = set(frame[TARGET].tolist())
        if not values <= {"0", "1"}:
            print(f"unexpected {TARGET} values in {name}: {sorted(values)[:5]}", file=sys.stderr)
            return 1
    train_y = (train_s[TARGET] == POSITIVE).to_numpy()
    eval_y = (eval_s[TARGET] == POSITIVE).to_numpy()
    train_rate = float(train_y.mean())

    # ---- references, recomputed from the shipped bytes ---------------------
    nice_scores, class_meta = class_rate_scores(train_s, train_y, eval_s, train_rate)
    month_key = lambda frame: frame["filed_date"].str[5:7].tolist()
    mark_scores, mark_meta = rate_scores(
        train_s["mark_type"].tolist(), train_y, eval_s["mark_type"].tolist())
    country_scores, country_meta = rate_scores(
        train_s["owner_country"].tolist(), train_y, eval_s["owner_country"].tolist())
    calendar_scores, calendar_meta = rate_scores(
        month_key(train_s), train_y, month_key(eval_s))
    category_scores, category_meta = rate_scores(
        train_s["category"].tolist(), train_y, eval_s["category"].tolist())
    series_scores, series_meta = rate_scores(
        train_s["series_flag"].tolist(), train_y, eval_s["series_flag"].tolist())
    majority = 1 if train_rate >= 0.5 else 0
    majority_accuracy = float((eval_y == majority).mean())

    years = eval_s["filed_date"].str[:4].tolist()
    del train_s

    # ---- the model, fit by the benchmark's own train.py (verbatim) --------
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
    if len(model_scores) != len(eval_y):
        print("predict_proba returned the wrong number of rows", file=sys.stderr)
        return 2
    if not np.isfinite(model_scores).all() or model_scores.min() < 0 or model_scores.max() > 1:
        print("predict_proba returned values outside [0,1]", file=sys.stderr)
        return 2

    model_auc_sklearn = float(roc_auc_score(eval_y, model_scores))
    model_auc_midrank = plain_auc(eval_y, model_scores)

    # ---- the comparisons the aggregate-only contract could not carry -------
    differences = {
        "model_vs_mark_type_rate": paired_row_bootstrap(
            eval_y, model_scores, mark_scores),
        "model_vs_nice_class_rate": paired_row_bootstrap(
            eval_y, model_scores, nice_scores),
        "model_vs_calendar_month_rate": paired_row_bootstrap(
            eval_y, model_scores, calendar_scores),
    }
    observed_gaps = {
        "model_minus_mark_type_rate": (round(model_auc_midrank - plain_auc(eval_y, mark_scores), 6)
                                       if model_auc_midrank is not None else None),
        "model_minus_nice_class_rate": (round(model_auc_midrank - plain_auc(eval_y, nice_scores), 6)
                                        if model_auc_midrank is not None else None),
        "model_minus_calendar_month_rate": (round(model_auc_midrank - plain_auc(eval_y, calendar_scores), 6)
                                            if model_auc_midrank is not None else None),
    }
    gap_for = {"model_vs_mark_type_rate": "model_minus_mark_type_rate",
               "model_vs_nice_class_rate": "model_minus_nice_class_rate",
               "model_vs_calendar_month_rate": "model_minus_calendar_month_rate"}
    # A bootstrap mean centers on the observed statistic (up to small bias). A
    # mean that collapses toward zero while the observed gap is large is the
    # signature of a resampler that scrambled label-row alignment - the exact
    # defect of ipo-tm-diag-001, where every mean read ~1e-4 against observed
    # gaps of ~5.7e-2. Refuse to record intervals that fail this invariant.
    resampler_aligned = all(
        interval.get("mean_difference") is not None and gap is not None
        and abs(interval["mean_difference"] - gap) < 0.05
        for name, interval in differences.items()
        if (gap := observed_gaps.get(gap_for.get(name, ""))) is not None
    ) if differences else False

    # ---- per-filing-year, mandatory beside any pooled figure --------------
    per_year = {}
    for year in sorted(set(years)):
        indexes = [i for i, y in enumerate(years) if y == year]
        labels = eval_y[indexes]
        per_year[year] = {
            "rows": len(indexes),
            "positives": int(labels.sum()),
            "positive_rate": round(float(labels.mean()), 6),
            "model_auc": plain_auc(labels, model_scores[indexes]),
            "model_brier": brier(labels, model_scores[indexes]),
            "nice_class_rate_auc": plain_auc(labels, np.asarray(nice_scores)[indexes]),
            "mark_type_rate_auc": plain_auc(labels, np.asarray(mark_scores)[indexes]),
            "calendar_month_rate_auc": plain_auc(labels, np.asarray(calendar_scores)[indexes]),
        }

    # ---- per-row scores, preserved for any later analysis -----------------
    with (out / "per_row_scores.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["tm_number", "filed_year", "label", "model_score",
                         "nice_class_score", "mark_type_score", "calendar_month_score"])
        nice_arr, mark_arr, cal_arr = (np.asarray(nice_scores), np.asarray(mark_scores),
                                        np.asarray(calendar_scores))
        for i, tm in enumerate(eval_s["tm_number"].tolist()):
            writer.writerow([tm, years[i], int(eval_y[i]), f"{model_scores[i]:.6f}",
                             f"{nice_arr[i]:.6f}", f"{mark_arr[i]:.6f}", f"{cal_arr[i]:.6f}"])
    del eval_s

    # ---- runner-file and acceptance evidence ------------------------------
    declared = json.loads(runner_json.read_text()) if runner_json and runner_json.is_file() else {}
    actual = {name: sha256_of(workdir / name) for name in ("train.py", "validate.py", "validate.sh")
              if (workdir / name).is_file()}
    accept_log = (out / "accept.log").read_text() if (out / "accept.log").is_file() else ""
    accepted = re.search(r"matches the qualified artifact ([0-9a-f]{16,64})", accept_log)
    validate_log = (out / "validate.log").read_text() if (out / "validate.log").is_file() else ""
    validate_auc = re.findall(
        r"eval AUC via predict_proba \(target column removed\):\s*([0-9.]+)", validate_log)

    model_record = RECORDED["full_model_eval_auc"]
    replication = {
        "nice_class_rate_auc": agrees(plain_auc(eval_y, nice_scores),
                                      RECORDED["nice_class_rate_auc"]["value"]),
        "mark_type_rate_auc": agrees(plain_auc(eval_y, mark_scores),
                                     RECORDED["mark_type_rate_auc"]["value"]),
        "owner_country_rate_auc": agrees(plain_auc(eval_y, country_scores),
                                         RECORDED["owner_country_rate_auc"]["value"]),
        "calendar_month_rate_auc": agrees(plain_auc(eval_y, calendar_scores),
                                          RECORDED["calendar_month_rate_auc"]["value"]),
        "category_rate_auc": agrees(plain_auc(eval_y, category_scores),
                                    RECORDED["category_rate_auc"]["value"]),
        "series_flag_rate_auc": agrees(plain_auc(eval_y, series_scores),
                                       RECORDED["series_flag_rate_auc"]["value"]),
        "majority_class_accuracy": agrees(majority_accuracy,
                                          RECORDED["majority_class_accuracy"]["value"]),
        "full_model_eval_auc": agrees(model_auc_midrank, model_record["value"],
                                      model_record.get("tolerance", 5e-5)),
        "nice_class_rate_auc_2013": agrees(per_year.get("2013", {}).get("nice_class_rate_auc"),
                                           RECORDED["nice_class_per_year_auc"]["2013"]),
        "nice_class_rate_auc_2014": agrees(per_year.get("2014", {}).get("nice_class_rate_auc"),
                                           RECORDED["nice_class_per_year_auc"]["2014"]),
    }

    result = {
        "job": (Path("/workspace/job_id.txt").read_text().strip()
                if Path("/workspace/job_id.txt").is_file() else None),
        "purpose": "per-row model scores and the model-vs-reference comparison "
                   "the aggregate-only runner contract could not carry",
        "artifact": {"name": task["name"], "target": task["target"],
                     "positive_label": task["positive_label"],
                     "id_columns": task["id_columns"], "rows": task["rows"]},
        "qualification_report": {
            "accepted_before_scoring": accepted is not None,
            "accepted_artifact_version": accepted.group(1) if accepted else None,
            "bundled_report_sha256": sha256_of(Path("/workspace/qualification.json"))
            if Path("/workspace/qualification.json").is_file() else None,
        },
        "runner_files": {"bundled_sha256": actual, "expected_sha256": declared,
                         "unmodified": bool(declared) and all(
                             declared.get(nm) == value for nm, value in actual.items())},
        "dependencies": versions(),
        "rows": {"eval": len(eval_y), "train": int(train_y.shape[0])},
        "train_positive_rate": round(train_rate, 6),
        "eval_positive_rate": round(float(eval_y.mean()), 6),
        "model": {
            "configuration": "benchmark template XGBClassifier n_estimators=30 "
                             "max_depth=6 lr=0.1 seed 42, refit here by the bundled "
                             "train.py; nothing re-tuned",
            "eval_auc_sklearn": round(model_auc_sklearn, 6),
            "eval_auc_midrank": model_auc_midrank,
            "eval_auc_printed_by_train_py": float(printed[-1]) if printed else None,
            "eval_auc_from_validate_log": float(validate_auc[-1]) if validate_auc else None,
            "eval_brier": brier(eval_y, model_scores),
        },
        "references_recomputed": {
            "nice_class_rate": {"auc": plain_auc(eval_y, nice_scores),
                                "brier": brier(eval_y, nice_scores), **class_meta},
            "mark_type_rate": {"auc": plain_auc(eval_y, mark_scores),
                               "brier": brier(eval_y, mark_scores), **mark_meta},
            "owner_country_rate": {"auc": plain_auc(eval_y, country_scores),
                                   "brier": brier(eval_y, country_scores), **country_meta},
            "calendar_month_rate": {"auc": plain_auc(eval_y, calendar_scores),
                                    "brier": brier(eval_y, calendar_scores), **calendar_meta},
            "category_rate": {"auc": plain_auc(eval_y, category_scores),
                              "brier": brier(eval_y, category_scores), **category_meta},
            "series_flag_rate": {"auc": plain_auc(eval_y, series_scores),
                                 "brier": brier(eval_y, series_scores), **series_meta},
            "majority_class": {"prediction": majority, "accuracy": majority_accuracy,
                               "note": "constant prediction: accuracy measured against "
                                       "this split's labels; AUC carries no ranking "
                                       "information"},
        },
        "replication_against_recorded": {
            "recorded_values": RECORDED,
            "recomputed_matches_recorded": replication,
            "all_match": all(replication.values()),
            "note": "constants are figures recorded by jobs ipo-tm-004 and "
                    "ipo-tm-baseline-001 on this same artifact; agreement is "
                    "measured here, not assumed",
        },
        "observed_gaps": observed_gaps,
        "paired_differences": differences,
        "resampler_alignment_ok": resampler_aligned,
        "resampler_alignment_note": "a bootstrap mean must center on its "
                                    "observed gap; a mean near zero against a "
                                    "large gap is the label-alignment defect "
                                    "of ipo-tm-diag-001, and fails the job",
        "per_filing_year": per_year,
        "clustering": "no dependence cluster is measurable from the shipped "
                      "columns: tm_number is unique per row and no owner or "
                      "series identity ships, so intervals are row-level only - "
                      "recorded as a limitation, not as independence",
        "per_row_scores": "per_row_scores.csv (tm_number, filed_year, label, "
                          "model_score, nice_class_score, mark_type_score, "
                          "calendar_month_score)",
        "scope": "diagnostic only: eval split, one model configuration, no "
                 "re-tuning, no agent loop; the holdout was never read and "
                 "stays sealed",
    }
    (out / "diag_result.json").write_text(json.dumps(result, indent=1) + "\n")

    print(f"model AUC: sklearn={model_auc_sklearn:.4f} midrank={model_auc_midrank:.4f} "
          f"train.py printed={printed[-1] if printed else None}")
    print(f"nice_class {plain_auc(eval_y, nice_scores):.4f} mark_type "
          f"{plain_auc(eval_y, mark_scores):.4f} calendar "
          f"{plain_auc(eval_y, calendar_scores):.4f} majority accuracy "
          f"{majority_accuracy:.4f}")
    gap_for_key = gap_for  # defined beside observed_gaps, before the alignment invariant
    for name, interval in differences.items():
        gap = observed_gaps.get(gap_for_key.get(name, ""))
        print(f"{name}: observed {gap} | bootstrap mean {interval.get('mean_difference')} ci95 "
              f"[{interval.get('ci95_low')}, {interval.get('ci95_high')}] "
              f"excludes_zero={interval.get('interval_excludes_zero')}")
    for year, figures in per_year.items():
        print(f"{year}: rate {figures['positive_rate']} model AUC {figures['model_auc']} "
              f"nice_class AUC {figures['nice_class_rate_auc']}")
    print(f"replication: {sum(replication.values())}/{len(replication)} match")
    print(f"resampler alignment ok: {resampler_aligned}")
    clean = (result["runner_files"]["unmodified"]
             and result["qualification_report"]["accepted_before_scoring"]
             and model_auc_midrank is not None
             and result["replication_against_recorded"]["all_match"]
             and result["resampler_alignment_ok"])
    return 0 if clean else 5


if __name__ == "__main__":
    raise SystemExit(main())
