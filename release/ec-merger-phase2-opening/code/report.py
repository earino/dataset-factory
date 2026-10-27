#!/usr/bin/env python3
"""Compact evidence for the runner-contract baseline of the ec-merger task.

Records which artifact was read (meta.json facts), the qualification report it
was accepted against (by digest, so the scored bytes are traceable to the
gate), whether the contract completed (train.py exit, validate.sh exit, the
CONTRACT OK line), and the AUCs the contract itself printed - both train.py's
own Eval AUC and validate.py's independent predict_proba recompute, so
agreement is checkable.

Then the decisive comparison the candidate record pins: the FULL MODEL's
per-row scores (recomputed here through the runner's own predict_proba, never
retrained differently) against the simple references on the SAME eval rows -
sector_division_rate (the required comparator), calendar_identity, and the
recent-era constant - with paired row-bootstrap differences and 95% intervals.
Reference math (auc, brier, paired bootstrap, tokenization, label reading) is
imported from the bundled score.py so the definitions cannot drift from the
construction-stage references; the train-fitted priors are rebuilt here from
train.csv with the same fitting code, and the recomputed reference AUCs are
cross-checked against the bundled references.json from the accepted
construction run (same rows, same definitions -> must agree).

Nothing here runs before run.sh's acceptance step: this script is invoked only
after qualify_dataset.py --accept has re-verified the fetched bytes.

Usage: report.py <extract-dir> <workdir> <output-dir> [runner_files.json]
"""
from __future__ import annotations

import json
import os
import platform
import re
import runpy
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "/workspace")
import score  # the construction-stage reference implementation, bundled verbatim

TARGET = "phase2_opened"
TRAIN_AUC_RE = re.compile(r"^Eval AUC:\s*([0-9.]+)", re.M)
PROBA_AUC_RE = re.compile(r"eval AUC via predict_proba \(target column removed\):\s*([0-9.]+)")
ACCEPT_RE = re.compile(r"matches the qualified artifact ([0-9a-f]{16,64})")
RUNNER_FILES = ("train.py", "validate.py", "validate.sh")
MIN_TOKEN_ROWS = 5


def sha256_of(path: Path) -> str:
    import hashlib
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def fit_references(train_rows, train_labels, train_rate):
    """Train-fitted priors, verbatim semantics from score.py's main()."""
    division_stats = defaultdict(lambda: [0, 0])
    cal_stats = defaultdict(lambda: [0, 0])
    token_stats = defaultdict(lambda: [0, 0])
    for row, label in zip(train_rows, train_labels):
        for division in row["sector_divisions"].split("|"):
            entry = division_stats[division]
            entry[0] += label
            entry[1] += 1
        entry = cal_stats[(row["regulation"], row["notification_month"])]
        entry[0] += label
        entry[1] += 1
        for token in score.tokens_of(row["case_title"]):
            entry = token_stats[token]
            entry[0] += label
            entry[1] += 1
    division_rate = {k: v[0] / v[1] for k, v in division_stats.items() if v[1]}
    cal_rate = {k: v[0] / v[1] for k, v in cal_stats.items() if v[1]}
    token_rate = {k: v[0] / v[1] for k, v in token_stats.items()
                  if v[1] >= MIN_TOKEN_ROWS}

    def sector_score(row):
        divisions = [d for d in row["sector_divisions"].split("|")
                     if d in division_rate]
        if not divisions:
            return train_rate
        return sum(division_rate[d] for d in divisions) / len(divisions)

    def calendar_score(row):
        return cal_rate.get((row["regulation"], row["notification_month"]), train_rate)

    def title_score(row):
        known = [token_rate[t] for t in score.tokens_of(row["case_title"])
                 if t in token_rate]
        if not known:
            return train_rate
        return sum(known) / len(known)

    return sector_score, calendar_score, title_score


def main() -> int:
    extract, workdir, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    runner_json = Path(sys.argv[4]) if len(sys.argv) > 4 else None

    workspace = Path("/workspace")
    job_id = (workspace / "job_id.txt").read_text().strip() \
        if (workspace / "job_id.txt").is_file() else None
    declared = json.loads(runner_json.read_text()) if runner_json and runner_json.is_file() else {}
    actual = {name: sha256_of(workspace / name) for name in RUNNER_FILES
              if (workspace / name).is_file()}

    meta = json.loads((extract / "meta.json").read_text())
    qualification = json.loads((workspace / "qualification.json").read_text())
    construction_refs = json.loads((workspace / "references.json").read_text())
    train_log = read(out / "train.log")
    validate_log = read(out / "validate.log")
    accept_log = read(out / "accept.log")
    train_auc = TRAIN_AUC_RE.findall(train_log)
    proba_auc = PROBA_AUC_RE.findall(validate_log)
    accepted = ACCEPT_RE.search(accept_log)

    contract = {
        "contract_ok": "[validate] CONTRACT OK" in validate_log,
        "eval_auc_from_train_py": float(train_auc[-1]) if train_auc else None,
        "eval_auc_from_validate_py": float(proba_auc[-1]) if proba_auc else None,
    }

    # ---- model scores through the runner's own predict_proba --------------
    import numpy as np
    import pandas as pd
    from sklearn.metrics import roc_auc_score

    os.chdir(workdir)
    ns = runpy.run_path("train.py", run_name="__baseline_report__")
    fn = ns.get("predict_proba")
    if not callable(fn):
        print("report: train.py defines no callable predict_proba", file=sys.stderr)
        return 1
    df = pd.read_csv("data/eval.csv")
    y = (df[TARGET] == meta["positive_label"]).astype(int).to_numpy()
    model_scores = np.asarray(fn(df.drop(columns=[TARGET])), dtype=float).ravel()
    model_auc_recomputed = float(roc_auc_score(y, model_scores))
    model_brier = float(np.mean((model_scores - y) ** 2))

    # ---- references on the same rows ---------------------------------------
    train_rows = score.read_rows(extract / "public" / "train.csv")
    eval_rows = score.read_rows(extract / "public" / "eval.csv")
    train_labels = score.labels_of(train_rows)
    eval_labels = score.labels_of(eval_rows)
    train_rate = sum(train_labels) / len(train_labels) if train_labels else 0.0
    sector_score, calendar_score, title_score = fit_references(
        train_rows, train_labels, train_rate)
    sector_scores = [sector_score(row) for row in eval_rows]
    calendar_scores = [calendar_score(row) for row in eval_rows]
    title_scores = [title_score(row) for row in eval_rows]

    train_years = sorted({int(row["notification_year"]) for row in train_rows})
    recent_years = set(train_years[-3:])
    recent_labels = [label for row, label in zip(train_rows, train_labels)
                     if int(row["notification_year"]) in recent_years]
    recent_rate = (sum(recent_labels) / len(recent_labels)) if recent_labels else train_rate
    recent_scores = [recent_rate] * len(eval_rows)

    majority = int(train_rate >= 0.5)
    majority_accuracy = score.accuracy(eval_labels, [majority] * len(eval_labels))

    auc = score.auc
    comparisons = {
        "sector_division_rate": {
            "auc": auc(eval_labels, sector_scores),
            "construction_run_auc": construction_refs["references"]
                                    ["sector_division_rate"]["auc"],
        },
        "calendar_identity": {
            "auc": auc(eval_labels, calendar_scores),
            "construction_run_auc": construction_refs["references"]
                                    ["calendar_identity"]["auc"],
        },
        "title_text": {
            "auc": auc(eval_labels, title_scores),
            "construction_run_auc": construction_refs["references"]["title_text"]["auc"],
        },
        "recent_rate": {
            "auc": auc(eval_labels, recent_scores),
            "construction_run_auc": construction_refs["references"]["recent_rate"]["auc"],
        },
    }
    for name, entry in comparisons.items():
        both = entry["auc"] is not None and entry["construction_run_auc"] is not None
        entry["agrees_with_construction_run"] = (both and abs(entry["auc"] -
            entry["construction_run_auc"]) < 1e-9) or (entry["auc"] is None and
            entry["construction_run_auc"] is None)

    paired = {}
    for name, ref_scores in (("sector_division_rate", sector_scores),
                             ("calendar_identity", calendar_scores),
                             ("title_text", title_scores),
                             ("recent_rate", recent_scores)):
        paired[f"full_model_vs_{name}"] = score.paired_bootstrap_difference(
            eval_labels, list(model_scores), ref_scores)

    per_year = {}
    for i, row in enumerate(eval_rows):
        year = str(row["notification_year"])
        entry = per_year.setdefault(year, {"rows": 0, "positives": 0,
                                          "labels": [], "model": [], "sector": []})
        entry["rows"] += 1
        entry["positives"] += eval_labels[i]
        entry["labels"].append(eval_labels[i])
        entry["model"].append(float(model_scores[i]))
        entry["sector"].append(sector_scores[i])
    per_year_out = {}
    for year, entry in sorted(per_year.items()):
        per_year_out[year] = {
            "rows": entry["rows"], "positives": entry["positives"],
            "positive_rate": round(entry["positives"] / entry["rows"], 6),
            "full_model_auc": auc(entry["labels"], entry["model"]),
            "sector_division_rate_auc": auc(entry["labels"], entry["sector"]),
        }

    result = {
        "job": job_id,
        "purpose": "one baseline through the runner's existing training and validation "
                   f"contract, on the accepted {meta.get('name', 'candidate')} artifact",
        "artifact": {
            "name": meta.get("name"),
            "target": meta.get("target"),
            "positive_label": meta.get("positive_label"),
            "id_columns": meta.get("id_columns"),
            "rows": meta.get("rows"),
            "positive_rate": meta.get("positive_rate"),
            "accepted_artifact_version": qualification.get("artifact", {})
                                              .get("artifact_version", {}).get("digest")
              or (accepted.group(1) if accepted else None),
            "gate_version_of_accepted_report": qualification.get("gate_version"),
        },
        "runner_files": {"declared": declared, "actual": actual,
                         "verbatim": all(declared.get(name) == actual.get(name)
                                         for name in RUNNER_FILES)
                         if declared else None},
        "contract": contract,
        "eval_rows": len(eval_labels),
        "eval_positives": sum(eval_labels),
        "full_model": {
            "eval_auc_recomputed_via_predict_proba": model_auc_recomputed,
            "eval_brier": model_brier,
        },
        "train_positive_rate": round(train_rate, 6),
        "majority_class": {
            "definition": "majority = int(train_positive_rate >= 0.5), "
                          "measured against THIS split's labels",
            "accuracy": majority_accuracy,
        },
        "references_recomputed_on_identical_rows": comparisons,
        "paired_differences_full_model_vs_references": paired,
        "per_year": per_year_out,
        "note": "persistence is recorded inapplicable for this task (each row is a newly "
                "notified case with no prior observation of the same entity); the nearest "
                "analogue, recent_rate, is carried instead. The holdout is sealed and was "
                "never copied into the workdir; nothing here touches it.",
    }
    (out / "baseline_result.json").write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
