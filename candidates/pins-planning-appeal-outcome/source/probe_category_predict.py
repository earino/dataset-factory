#!/usr/bin/env python3
"""Minimal worker-side probe: does the verbatim benchmark train.py predict path
accept category-dtype columns at predict time under the installed xgboost?

Why this exists
---------------
Job pins-planning-baseline-001 failed at the runner contract. The verbatim
train.py fits XGBClassifier(enable_categorical=True) on a frame whose string
columns (nunique <= 1000) its prepare() converts to pandas Categorical, then
evaluates with model.predict_proba(prepare(evald)) - which reaches
Booster.inplace_predict. xgboost 3.4.1 rejected that frame with

    ValueError: DataFrame.dtypes for data must be int, float, bool or category.
    When categorical type is supplied, the experimental DMatrix parameter
    `enable_categorical` must be set to `True`.
    Invalid columns:lpa_name: category, ... (nine columns), floor_space_sqm: object

even though enable_categorical=True WAS set at fit: the estimator's flag is not
applied on the inplace_predict path. Two defects were entangled there - the
object-dtype floor_space_sqm column (publisher prose in 6 eval rows) and the
nine category-dtype columns. The build fixes the object column unconditionally
(num() maps prose to missing); whether category dtypes ALONE also fail is what
this probe settles, on synthetic frames, before the build writes its artifact.

Two sub-tests, both mirroring the verbatim train.py's own idiom exactly
(pd.Categorical with train-sorted levels; the same estimator configuration):

  1. predict on a category-dtype frame whose levels were all seen at fit;
  2. predict on a category-dtype frame carrying one unseen level -> NaN
     (the real artifact can hold levels in eval/holdout that train never saw).

verdict "ok" requires BOTH to return finite probabilities; any exception or
malformed shape is "rejected", and the build then integer-codes the nine
categorical columns so the shipped frame is int/float/bool only.

This probe reads no dataset row and computes no performance metric. Output:
JSON {"predict_on_category_dtype": "ok"|"rejected", ...} with the installed
library versions and the exact failure text, so the writer's decision is
recorded evidence, never a guess.

Usage: probe_category_predict.py --out PATH
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import pandas as pd
import xgboost as xgb


def run_subtest(model, cat_levels, levels_for_frame, num_column):
    """Mirror train.py's prepare() + predict_proba on a synthetic frame."""
    frame = pd.DataFrame({
        "cat": levels_for_frame,
        "num": num_column,
    })
    X = frame[["cat", "num"]].copy()
    X["cat"] = pd.Categorical(X["cat"], categories=cat_levels)  # unseen levels -> NaN
    probabilities = model.predict_proba(X)
    array = np.asarray(probabilities, dtype=float)
    if array.shape != (len(frame), 2):
        raise ValueError(f"predict_proba returned shape {array.shape}")
    if not np.all(np.isfinite(array)) or array.min() < 0 or array.max() > 1:
        raise ValueError("predict_proba returned non-finite or out-of-range probabilities")
    return array


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rng = np.random.default_rng(7)
    levels = ["alpha", "beta", "gamma", "delta"]
    n = 240
    train = pd.DataFrame({
        "cat": rng.choice(levels, n),
        "num": rng.normal(size=n),
        "y": rng.integers(0, 2, n),
    })

    # the verbatim train.py's own idiom, copied exactly
    cat_levels = pd.Index(sorted(train["cat"].dropna().unique()))
    cat_cols = ["cat"]

    def prepare(df: pd.DataFrame) -> pd.DataFrame:
        X = df[[c for c in df.columns if c not in ("y",)]].copy()
        for c in cat_cols:
            X[c] = pd.Categorical(X[c], categories=cat_levels)  # unseen levels -> NaN
        return X

    model = xgb.XGBClassifier(
        n_estimators=10,
        max_depth=3,
        learning_rate=0.1,
        tree_method="hist",
        enable_categorical=True,
        random_state=42,
        n_jobs=2,
    )
    fit_detail = "fit ok"
    try:
        model.fit(prepare(train), train["y"].to_numpy())
    except Exception as exc:  # noqa: BLE001 - recorded, then the probe fails closed
        result = {
            "predict_on_category_dtype": "rejected",
            "subtests": {"fit": f"{type(exc).__name__}: {exc}"},
            "fit_detail": f"{type(exc).__name__}: {exc}",
            "note": "even the fit path rejected category dtypes; verdict rejected",
        }
        _write(args.out, result)
        print(json.dumps(result, indent=1))
        return 0

    subtests = {"fit": fit_detail}
    verdict = "ok"

    # sub-test 1: all levels seen at fit
    try:
        run_subtest(model, cat_levels,
                    rng.choice(levels, 60), rng.normal(size=60))
        subtests["predict_seen_levels"] = "ok"
    except Exception as exc:  # noqa: BLE001 - recorded verbatim as the rejection
        subtests["predict_seen_levels"] = f"{type(exc).__name__}: {exc}"
        verdict = "rejected"

    # sub-test 2: one unseen level -> NaN category (eval/holdout can hold
    # levels train never saw; the verbatim prepare() maps those to NaN)
    try:
        unseen = list(rng.choice(levels, 59)) + ["epsilon"]
        run_subtest(model, cat_levels, unseen, rng.normal(size=60))
        subtests["predict_unseen_level_nan"] = "ok"
    except Exception as exc:  # noqa: BLE001 - recorded verbatim as the rejection
        subtests["predict_unseen_level_nan"] = f"{type(exc).__name__}: {exc}"
        verdict = "rejected"

    result = {
        "predict_on_category_dtype": verdict,
        "purpose": ("does the verbatim benchmark train.py predict path accept "
                    "category-dtype columns at predict under the installed xgboost"),
        "subtests": subtests,
        "model_config": ("XGBClassifier n_estimators=10 max_depth=3 lr=0.1 hist "
                         "enable_categorical=True seed 42 - the verbatim train.py "
                         "configuration modulo tree size"),
        "versions": {
            "python": sys.version.split()[0],
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "xgboost": xgb.__version__,
        },
        "note": ("verdict rejected means build.py integer-codes the nine string-"
                 "categorical columns so the shipped frame is int/float/bool only; "
                 "no dataset row was read and no metric computed"),
    }
    _write(args.out, result)
    print(json.dumps(result, indent=1))
    return 0


def _write(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
        fh.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
