#!/usr/bin/env python3
"""Derived evidence for pins-planning-appeal-outcome: model-vs-reference intervals.

NOT the runner. The verbatim benchmark contract ran first (run.sh: train.py +
validate.sh, unmodified, their AUCs in the logs). This file is a clearly
labelled derived step that exists to measure the decisive comparison the
candidate record requires: paired intervals of the full model against the
simple references on the SAME eval rows.

It reimplements the two decisive references independently (pandas groupby,
not the build job's rate-table code), so the reference figures quoted in any
verdict are computed by a second implementation from the accepted bytes:

  * lpa_hist_rate  - train-estimated historical allow rate of the row's LPA
    (global fallback for LPAs unseen in train). The headroom reference the
    candidate record names.
  * procedure_type_rate - train-estimated rate by (procedure, casework type)
    with marginal and global fallbacks. The strongest simple reference
    measured post-acceptance (0.5551 eval AUC in the build job).
  * shipped_rate_feature - the artifact's own lpa_allow_rate_prior column as
    the score (-1 sentinel to 0.5): a cross-check that the shipped feature
    and the recomputed reference agree.

The model is the SAME configuration as the verbatim train.py baseline
(XGBClassifier n_estimators=30, max_depth=6, lr=0.1, hist, seed 42, string
columns with <=1000 levels categorical, higher-cardinality strings dropped),
retrained here only so per-row eval scores exist for the paired bootstrap.
Its eval AUC must reproduce the contract run's figure; a divergence is
recorded as a defect, never averaged away.

Uncertainty: paired bootstrap differences (150 resamples, fixed seed) on
identical rows - row-level and LPA-clustered. Never overlapping marginal
intervals. An interval containing zero is an inconclusive difference, not
parity. The holdout is never opened.

Usage: model_intervals.py <extract-dir> <out-dir>
"""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score

TARGET = "allowed"
POSITIVE = 1
BOOTSTRAP = 150
SEED = 43


def auc(labels, scores):
    labels = np.asarray(labels)
    scores = np.asarray(scores, dtype=float)
    if len(set(scores.tolist())) == 1:
        return None
    if labels.sum() in (0, len(labels)):
        return None
    return float(roc_auc_score(labels, scores))


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: model_intervals.py <extract-dir> <out-dir>")
    extract, out = Path(sys.argv[1]), Path(sys.argv[2])
    train = pd.read_csv(extract / "public" / "train.csv")
    evald = pd.read_csv(extract / "public" / "eval.csv")

    # ---- the model: same configuration as the verbatim train.py baseline ----
    id_cols = ["row_id"]
    feature_cols = [c for c in train.columns if c not in id_cols + [TARGET]]
    obj_cols = [c for c in feature_cols
                if pd.api.types.is_object_dtype(train[c])
                or pd.api.types.is_string_dtype(train[c])]
    cat_cols = [c for c in obj_cols if train[c].nunique() <= 1000]
    feature_cols = [c for c in feature_cols if c not in obj_cols or c in cat_cols]
    cat_levels = {c: pd.Index(sorted(train[c].dropna().unique())) for c in cat_cols}

    def prepare(df: pd.DataFrame) -> pd.DataFrame:
        X = df[feature_cols].copy()
        for c in cat_cols:
            X[c] = pd.Categorical(X[c], categories=cat_levels[c])
        return X

    model = xgb.XGBClassifier(n_estimators=30, max_depth=6, learning_rate=0.1,
                              tree_method="hist", enable_categorical=True,
                              random_state=42, n_jobs=4)
    model.fit(prepare(train), (train[TARGET] == POSITIVE).astype(int))
    model_scores = model.predict_proba(prepare(evald))[:, 1]
    y_eval = (evald[TARGET] == POSITIVE).astype(int).to_numpy()
    model_auc = auc(y_eval, model_scores)

    # ---- references, second implementation (pandas groupby) -----------------
    train_lab = (train[TARGET] == POSITIVE).astype(int)
    lpa_rate = train_lab.groupby(train["lpa_name"]).mean()
    global_rate = float(train_lab.mean())
    lpa_hist = [float(lpa_rate.get(l, global_rate)) for l in evald["lpa_name"]]

    pt = train_lab.groupby([train["procedure"], train["casework_type"]]).mean()
    p_marg = train_lab.groupby(train["procedure"]).mean()
    t_marg = train_lab.groupby(train["casework_type"]).mean()

    def proc_score(row):
        key = (row["procedure"], row["casework_type"])
        if key in pt.index:
            return float(pt.loc[key])
        p, t = key
        if p in p_marg.index and t in t_marg.index:
            return 0.5 * (float(p_marg.loc[p]) + float(t_marg.loc[t]))
        if p in p_marg.index:
            return float(p_marg.loc[p])
        if t in t_marg.index:
            return float(t_marg.loc[t])
        return global_rate

    procedure_type = [proc_score(r) for _, r in evald.iterrows()]
    shipped_rate = [0.5 if v == -1.0 else float(v) for v in evald["lpa_allow_rate_prior"]]

    n = len(evald)
    references = {
        "lpa_hist_rate": auc(y_eval, lpa_hist),
        "procedure_type_rate": auc(y_eval, procedure_type),
        "shipped_rate_feature": auc(y_eval, shipped_rate),
    }

    # ---- paired bootstrap, row level and LPA-clustered ------------------------
    rng = random.Random(SEED)
    vectors = {"lpa_hist_rate": lpa_hist, "procedure_type_rate": procedure_type,
               "shipped_rate_feature": shipped_rate}
    paired = {}
    for name, ref in vectors.items():
        diffs = []
        for _ in range(BOOTSTRAP):
            drawn = [rng.randrange(n) for _ in range(n)]
            ys = [int(y_eval[i]) for i in drawn]
            vm = auc(ys, [model_scores[i] for i in drawn])
            vr = auc(ys, [ref[i] for i in drawn])
            if vm is None or vr is None:
                continue
            diffs.append(vm - vr)
        diffs.sort()
        paired[name] = {
            "model_auc": model_auc, "reference_auc": references[name],
            "observed_diff": (model_auc - references[name])
            if (model_auc is not None and references[name] is not None) else None,
            "ci95": [diffs[int(0.025 * len(diffs))],
                     diffs[int(0.975 * len(diffs)) - 1]] if len(diffs) > 1 else None,
            "resamples": len(diffs),
        }

    cluster_map = defaultdict(list)
    for i, l in enumerate(evald["lpa_name"]):
        cluster_map[l].append(i)
    clusters = [v for v in cluster_map.values() if v]
    clustered = {}
    for name, ref in vectors.items():
        diffs = []
        for _ in range(BOOTSTRAP):
            drawn = [clusters[rng.randrange(len(clusters))] for _ in range(len(clusters))]
            idx = [i for c in drawn for i in c]
            ys = [int(y_eval[i]) for i in idx]
            vm = auc(ys, [model_scores[i] for i in idx])
            vr = auc(ys, [ref[i] for i in idx])
            if vm is None or vr is None:
                continue
            diffs.append(vm - vr)
        diffs.sort()
        clustered[name] = {
            "ci95": [diffs[int(0.025 * len(diffs))],
                     diffs[int(0.975 * len(diffs)) - 1]] if len(diffs) > 1 else None,
            "resamples": len(diffs),
            "unit": "LPA cluster",
        }

    result = {
        "purpose": "derived evidence, not the runner: paired model-vs-reference "
                   "intervals on identical eval rows after the verbatim contract run",
        "model": "XGBClassifier n_estimators=30 max_depth=6 lr=0.1 hist seed 42 - "
                 "identical to the verbatim train.py baseline; string columns with "
                 ">1000 levels dropped exactly as the baseline drops them",
        "scope": f"eval rows only ({n} rows, validation instants 2020-2021); "
                 "the holdout was never opened",
        "model_eval_auc": model_auc,
        "references_eval_auc": references,
        "paired_row_level": paired,
        "paired_lpa_clustered": clustered,
        "notes": [
            "the references are reimplemented here independently (pandas groupby), "
            "not imported from the build job's score.py",
            "shipped_rate_feature scores the artifact's own lpa_allow_rate_prior column; "
            "its agreement with lpa_hist_rate cross-checks the reference",
            "intervals containing zero are inconclusive differences, not parity",
        ],
    }
    (out / "model-vs-references.json").write_text(json.dumps(result, indent=1) + "\n")
    print(f"MODEL eval AUC {model_auc}")
    for k, v in references.items():
        print(f"  reference {k}: {v}")
    for k, v in paired.items():
        print(f"  paired vs {k}: obs={v['observed_diff']} ci95={v['ci95']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
