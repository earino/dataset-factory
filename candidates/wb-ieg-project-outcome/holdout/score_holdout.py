#!/usr/bin/env python3
"""Decisive holdout comparison for the accepted wb-ieg-project-outcome artifact.

This is the bounded follow-up the candidate record calls for: score the
runner-contract model AND the train-fitted simple references on the private
holdout rows (and, for the paired comparison, the eval rows), with paired
uncertainty. It also closes the three measured source-review findings that are
in scope for this stage:

  * ordering - run.sh re-accepts the fetched bytes through the qualification
    gate BEFORE this script runs; nothing here is executed unless --accept
    exited 0 (construct -> qualify -> accept -> score -> report);
  * majority-class accuracy - measured as a constant prediction evaluated on
    each split's own labels, never restated as the training prevalence;
  * the "calendar" control - the build's country x approval_fy table is shown
    empirically to fall back to country identity on 100% of eval/holdout rows
    (recorded, not assumed), and replaced by a genuine time-only reference:
    logistic regression on approval_fy + cyclical approval month, fitted on
    train rows only with fixed hyperparameters (no tuning);
  * information sets - every reference's scores are recomputed on a copy of
    the split in which every column OUTSIDE the rule's claimed inputs has been
    row-shuffled, and must be bit-identical: the metric names are verified,
    not trusted.

Everything is fitted on the train split only. The model leg runs the
benchmark's own train.py verbatim via runpy (exactly validate.py's mechanism)
and calls its module-level predict_proba, so the scored model is the runner's
own fitted artifact with no retraining choices. The private holdout is read
only by this scorer, never copied into an agent workdir.

Usage: score_holdout.py <extract-dir> <workdir> <output-dir> [runner_files.json]
"""
import hashlib
import io
import json
import os
import platform
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

TARGET = "msplus"
ID_COL = "project_id"
BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 20261023
SHUFFLE_SEED = 20261023
EXPECTED = {  # previously recorded numbers, recorded here as cross-checks, not assertions
    "model_eval_auc_wb_baseline_001": 0.5879,
    "identity_eval_auc_build_early_scoring": 0.6003,
    "identity_holdout_auc_build_early_scoring": 0.4909,
}
TRAIN_AUC_PRINT_RE = re.compile(r"Eval AUC:\s*([0-9.]+)")


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


def rank_auc(labels: np.ndarray, scores: np.ndarray):
    """Tie-averaged Mann-Whitney AUC, the definition build.py used (independent
    of sklearn, so agreement between the two is a replication not a re-run)."""
    labels = np.asarray(labels)
    scores = np.asarray(scores, dtype=float)
    n_pos = int((labels == 1).sum())
    n_neg = len(labels) - n_pos
    if not n_pos or not n_neg:
        return None
    order = np.argsort(scores, kind="mergesort")
    sorted_scores = scores[order]
    ranks = np.empty(len(scores), dtype=float)
    i = 0
    while i < len(sorted_scores):
        j = i
        while j + 1 < len(sorted_scores) and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        ranks[i:j + 1] = (i + j + 2) / 2.0  # mean of 1-based ranks i+1 .. j+1
        i = j + 1
    restored = np.empty(len(scores), dtype=float)
    restored[order] = ranks
    return float((restored[labels == 1].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def auc_pair(labels, scores):
    """Both AUC implementations; they must agree to 1e-9 or the job fails."""
    labels = np.asarray(labels)
    scores = np.asarray(scores, dtype=float)
    mine = rank_auc(labels, scores)
    theirs = roc_auc_score(labels, scores) if mine is not None else None
    if mine is not None and theirs is not None and abs(mine - theirs) > 1e-9:
        raise SystemExit(f"AUC implementations disagree: rank={mine!r} sklearn={theirs!r}")
    return mine


def brier(labels, scores):
    labels = np.asarray(labels)
    scores = np.asarray(scores, dtype=float)
    return float(np.mean((scores - labels) ** 2))


def rate_table(keys, labels):
    table = {}
    for key, label in zip(keys, labels):
        entry = table.setdefault(key, [0, 0])
        entry[0] += int(label)
        entry[1] += 1
    return {key: pos / total for key, (pos, total) in table.items()}


def main() -> int:
    if len(sys.argv) not in (4, 5):
        raise SystemExit("usage: score_holdout.py <extract-dir> <workdir> <output-dir> [runner_files.json]")
    extract, workdir, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    runner_json = Path(sys.argv[4]) if len(sys.argv) == 5 else None
    out.mkdir(parents=True, exist_ok=True)
    workspace = Path("/workspace")
    job_id = (workspace / "job_id.txt").read_text().strip() if (workspace / "job_id.txt").is_file() else None

    meta = json.loads((extract / "meta.json").read_text())
    frames = {}
    for split, relative in (("train", "public/train.csv"), ("eval", "public/eval.csv"),
                            ("holdout", "private/holdout.csv")):
        frames[split] = pd.read_csv(extract / relative)
    for split, frame in frames.items():
        expected_rows = int(meta["rows"][split])
        if len(frame) != expected_rows:
            raise SystemExit(f"{split} has {len(frame)} rows, meta.json says {expected_rows}")
    labels = {split: (frame[TARGET] == 1).to_numpy().astype(int) for split, frame in frames.items()}
    train_rate = float(labels["train"].mean())
    majority_class = 1 if train_rate > 0.5 else 0

    # ---- the runner's own fitted model (no retraining choices) --------------
    os.chdir(workdir)
    captured = io.StringIO()
    with redirect_stdout(captured):
        import runpy
        namespace = runpy.run_path("train.py", run_name="__train__")
    printed = TRAIN_AUC_PRINT_RE.findall(captured.getvalue())
    predict_proba = namespace.get("predict_proba")
    if not callable(predict_proba):
        raise SystemExit("train.py did not define a callable predict_proba(df)")
    model_scores = {}
    for split in ("train", "eval", "holdout"):
        frame = frames[split].drop(columns=[TARGET])
        scores = np.asarray(predict_proba(frame), dtype=float).ravel()
        if len(scores) != len(frames[split]) or not np.all(np.isfinite(scores)):
            raise SystemExit(f"model scores malformed for {split}")
        model_scores[split] = scores
    model_eval_auc_own_print = float(printed[-1]) if printed else None

    # ---- train-fitted references -------------------------------------------
    train_frame = frames["train"]
    identity_table = rate_table(train_frame["country"].tolist(), labels["train"])

    def identity_scores(frame):
        return np.array([identity_table.get(country, train_rate)
                          for country in frame["country"]], dtype=float)

    degenerate_calendar_table = rate_table(
        zip(train_frame["country"].tolist(), train_frame["approval_fy"].tolist()), labels["train"])

    def degenerate_calendar_scores(frame):
        scores = []
        for country, fy in zip(frame["country"], frame["approval_fy"]):
            scores.append(degenerate_calendar_table.get((country, fy), identity_table.get(country, train_rate)))
        return np.array(scores, dtype=float)

    fy_mean = float(train_frame["approval_fy"].mean())
    fy_std = float(train_frame["approval_fy"].std()) or 1.0

    def calendar_features(frame):
        fy = (frame["approval_fy"].to_numpy(dtype=float) - fy_mean) / fy_std
        month = frame["approval_month_num"].to_numpy(dtype=float)
        angle = 2.0 * np.pi * (np.clip(month, 1, 12) - 1) / 12.0
        return np.column_stack([fy, np.sin(angle), np.cos(angle)])

    calendar_model = LogisticRegression(max_iter=1000)
    calendar_model.fit(calendar_features(train_frame), labels["train"])

    def calendar_scores(frame):
        return calendar_model.predict_proba(calendar_features(frame))[:, 1]

    def prior_share_scores(frame):
        counts = frame["prior_evals_count"].to_numpy()
        shares = frame["prior_msplus_share"].to_numpy(dtype=float)
        scores = np.where(counts > 0, shares, train_rate)
        return scores.astype(float), int((counts <= 0).sum())

    rules = {"identity_country": (identity_scores, ["country"]),
             "calendar_trend": (calendar_scores, ["approval_fy", "approval_month_num"]),
             "prior_share": (lambda f: prior_share_scores(f)[0],
                             ["prior_msplus_share", "prior_evals_count"])}
    all_scores = {"model": (model_scores, None)}
    prior_fallback_rows = {}
    for name, (scorer, claimed) in rules.items():
        all_scores[name] = ({split: scorer(frames[split])
                             for split in ("train", "eval", "holdout")}, claimed)
    if "prior_share" in rules:
        prior_fallback_rows = {split: prior_share_scores(frames[split])[1]
                              for split in ("train", "eval", "holdout")}

    # ---- verify each reference's information set by perturbation -------------
    rng = np.random.default_rng(SHUFFLE_SEED)
    information_sets = {}
    for name, (scores_by_split, claimed) in all_scores.items():
        if claimed is None:
            information_sets[name] = {"claimed_inputs": "all feature columns (the runner's own model)",
                                      "perturbation_check": "not applicable - the model may read everything"}
            continue
        perturbed = {}
        for split in ("eval", "holdout"):
            frame = frames[split].copy()
            other = [c for c in frame.columns if c not in claimed + [TARGET]]
            changed, constant = {}, {}
            for column in other:
                original = frame[column].copy()
                permutation = rng.permutation(len(frame))
                frame[column] = original.to_numpy()[permutation]
                if original.nunique(dropna=False) <= 1:
                    constant[column] = "constant in this split - carries no information, cannot change"
                else:
                    changed[column] = not frame[column].equals(original)
            recomputed = rules[name][0](frame)
            perturbed[split] = {
                "columns_shuffled": len(other),
                "nonconstant_columns_all_changed": all(changed.values()) and len(changed) > 0,
                "constant_columns": sorted(constant),
                "scores_identical_after_perturbation": bool(np.array_equal(recomputed, scores_by_split[split])),
            }
        information_sets[name] = {"claimed_inputs": claimed,
                                  "perturbation_check": perturbed}
        if not all(entry["scores_identical_after_perturbation"]
                   and entry["nonconstant_columns_all_changed"]
                   for entry in perturbed.values()):
            raise SystemExit(f"rule {name} reads columns beyond its claimed inputs")

    # ---- empirical check of the degenerate country x year table ------------
    degenerate = {}
    for split in ("eval", "holdout"):
        frame = frames[split]
        keys = list(zip(frame["country"], frame["approval_fy"]))
        hits = sum(1 for key in keys if key in degenerate_calendar_table)
        degenerate[split] = {
            "rows_with_train_country_fy_key": hits,
            "rows": len(frame),
            "fallback_fraction": round(1.0 - hits / len(frame), 6),
            "auc": auc_pair(labels[split], degenerate_calendar_scores(frame)),
            "scores_identical_to_identity_rule": bool(
                np.array_equal(degenerate_calendar_scores(frame), all_scores["identity_country"][0][split])),
        }

    # ---- per-split table ----------------------------------------------------
    def split_table(split):
        frame = frames[split]
        row = {"rows": len(frame),
               "positives": int(labels[split].sum()),
               "prevalence": round(float(labels[split].mean()), 6),
               "countries": int(frame["country"].nunique()),
               "countries_with_positive": int(frame.loc[labels[split] == 1, "country"].nunique()),
               "majority_class": majority_class,
               "majority_class_accuracy_measured": round(float((labels[split] == majority_class).mean()), 6),
               "majority_class_accuracy_is_training_prevalence": False}
        for name, (scores_by_split, _) in all_scores.items():
            scores = scores_by_split[split]
            auc = auc_pair(labels[split], scores)
            row[f"{name}_auc"] = None if auc is None else round(auc, 6)
            row[f"{name}_brier"] = round(brier(labels[split], scores), 6)
        return row

    splits = {split: split_table(split) for split in ("train", "eval", "holdout")}
    splits["train"]["note"] = ("train AUCs are in-sample for the references and the model; "
                               "they are recorded for diagnosis, never quoted as held-out results")
    # train leg for the references (in-sample, diagnostic only)
    train_diag = {}
    for name, (scorer, claimed) in rules.items():
        train_diag[name] = round(auc_pair(labels["train"], scorer(train_frame)), 6)
    splits["train"]["reference_in_sample_auc"] = train_diag

    # ---- per-year breakdown (structural check: no pooled-only number) ------
    per_year = {}
    for split in ("eval", "holdout"):
        frame = frames[split]
        per_year[split] = {}
        for year in sorted(frame["approval_fy"].unique()):
            mask = (frame["approval_fy"] == year).to_numpy()
            year_labels = labels[split][mask]
            entry = {"rows": int(mask.sum()), "positives": int(year_labels.sum()),
                     "prevalence": round(float(year_labels.mean()), 6)}
            for name, (scores_by_split, _) in all_scores.items():
                scores = scores_by_split[split][mask]
                entry[f"{name}_auc"] = None if (year_labels == 0).all() or (year_labels == 1).all() \
                    else round(auc_pair(year_labels, scores), 6)
                entry[f"{name}_brier"] = round(brier(year_labels, scores), 6)
            per_year[split][int(year)] = entry

    # ---- paired cluster bootstrap by country --------------------------------
    def cluster_bootstrap(split, rule):
        frame = frames[split]
        y = labels[split]
        model = all_scores["model"][0][split]
        other = all_scores[rule][0][split]
        groups = {country: np.flatnonzero((frame["country"] == country).to_numpy())
                  for country in frame["country"].unique()}
        names = sorted(groups)
        rng = np.random.default_rng(BOOTSTRAP_SEED)
        deltas, skipped = [], 0
        for _ in range(BOOTSTRAP_RESAMPLES):
            chosen = rng.integers(0, len(names), len(names))
            indices = np.concatenate([groups[names[i]] for i in chosen])
            resampled_labels = y[indices]
            if (resampled_labels == 0).all() or (resampled_labels == 1).all():
                skipped += 1
                continue
            auc_model = rank_auc(resampled_labels, model[indices])
            auc_other = rank_auc(resampled_labels, other[indices])
            if auc_model is None or auc_other is None:
                skipped += 1
                continue
            deltas.append(auc_model - auc_other)
        if not deltas:
            raise SystemExit(f"every bootstrap resample was degenerate for {split} {rule}")
        deltas = np.array(deltas)
        point_model = rank_auc(y, model)
        point_other = rank_auc(y, other)
        if point_model is None or point_other is None:
            raise SystemExit(f"point estimate undefined for {split} {rule}")
        return {"delta_auc_point_estimate": round(float(point_model - point_other), 6),
                "bootstrap_mean_delta_auc": round(float(deltas.mean()), 6),
                "ci95_low": round(float(np.percentile(deltas, 2.5)), 6),
                "ci95_high": round(float(np.percentile(deltas, 97.5)), 6),
                "resamples": BOOTSTRAP_RESAMPLES, "skipped_degenerate": skipped,
                "cluster": "country", "seed": BOOTSTRAP_SEED}

    uncertainty = {f"model_minus_{rule}": {split: cluster_bootstrap(split, rule)
                                            for split in ("eval", "holdout")}
                    for rule in ("identity_country", "calendar_trend", "prior_share")}

    # ---- assemble the report -------------------------------------------------
    artifact_files = {relative: {"sha256": sha256_of(extract / relative),
                                 "bytes": (extract / relative).stat().st_size}
                      for relative in ("public/train.csv", "public/eval.csv",
                                       "private/holdout.csv", "meta.json", "quality.json")}
    accept_log = (out / "accept.log")
    accept_tail = accept_log.read_text().strip().splitlines()[-1] if accept_log.is_file() else None
    runner_files = json.loads(runner_json.read_text()) if runner_json and runner_json.is_file() else {}
    report = {
        "job": job_id,
        "purpose": "decisive holdout comparison for the wb-ieg-project-outcome decision point: "
                   "runner-contract model vs train-fitted simple references on identical rows",
        "artifact": {"name": meta["name"],
                     "files": artifact_files,
                     "gate_accept_tail": accept_tail,
                     "runner_files": runner_files},
        "environment": versions(),
        "train_prevalence": round(train_rate, 6),
        "majority_class": majority_class,
        "splits": splits,
        "per_year": per_year,
        "degenerate_country_x_year_check": degenerate,
        "information_sets": information_sets,
        "prior_share_fallback_rows": prior_fallback_rows,
        "cross_checks": {
            "model_eval_auc_from_train_py_print": model_eval_auc_own_print,
            "model_eval_auc_recomputed_via_predict_proba": splits["eval"]["model_auc"],
            "previously_recorded_model_eval_auc": EXPECTED["model_eval_auc_wb_baseline_001"],
            "identity_eval_auc_previously_recorded": EXPECTED["identity_eval_auc_build_early_scoring"],
            "identity_holdout_auc_previously_recorded": EXPECTED["identity_holdout_auc_build_early_scoring"],
            "note": "previously recorded values are cross-checks; discrepancies are findings to "
                    "investigate, not values to overwrite",
        },
        "uncertainty": uncertainty,
        "prevalence_shift_note": "train %.3f -> eval %.3f -> holdout %.3f: the evaluation windows "
                                 "are out-of-distribution in prevalence as well as temporal; "
                                 "AUC is prevalence-robust, Brier is not" % (
                                     splits["train"]["prevalence"], splits["eval"]["prevalence"],
                                     splits["holdout"]["prevalence"]),
        "persistence_note": "no per-entity persistence leg exists at project grain (each project is "
                            "evaluated exactly once); the identity/prior-share rules play the "
                            "track-record role persistence plays in panel tasks",
        "design_frozen_before_holdout_scoring": True,
    }
    (out / "holdout-comparison.json").write_text(json.dumps(report, indent=1) + "\n")

    print("== decisive numbers ==")
    for split in ("eval", "holdout"):
        row = splits[split]
        print(f"{split}: rows={row['rows']} prevalence={row['prevalence']} "
              f"model_auc={row['model_auc']} identity={row['identity_country_auc']} "
              f"calendar={row['calendar_trend_auc']} prior_share={row['prior_share_auc']} "
              f"majority_acc={row['majority_class_accuracy_measured']}")
    for name, block in uncertainty.items():
        holdout = block["holdout"]
        print(f"holdout {name}: delta={holdout['delta_auc_point_estimate']} "
              f"ci95=[{holdout['ci95_low']}, {holdout['ci95_high']}] "
              f"(skipped {holdout['skipped_degenerate']}/{BOOTSTRAP_RESAMPLES})")
    print("degenerate country x year check:",
          json.dumps({s: {"fallback_fraction": degenerate[s]["fallback_fraction"],
                          "identical_to_identity": degenerate[s]["scores_identical_to_identity_rule"]}
                      for s in ("eval", "holdout")}))
    print("report written:", out / "holdout-comparison.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
