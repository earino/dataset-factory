#!/usr/bin/env python3
"""Simple references for the accepted `ipo-trademark-registration-outcome` artifact.

Runs ONLY after the qualification gate has passed and --accept has re-verified
the report against these exact bytes. It reads the written CSVs, never rewrites
them, and computes every reference on the SAME eval rows.

The task is a per-application outcome question at the filing instant, so the
reference set takes this shape (every rate table is estimated ONLY from
training-cohort rows, 2010-2012 filings; scored on eval rows, 2013-2014):

  * nice_class_rate - THE REQUIRED COMPARATOR: the mean train positive rate
    over the application's assigned Nice classes (global train rate when a
    class is unseen in train or no class is assigned). A useful model must
    beat this: it tests whether anything beyond class-conditional sector
    difficulty adds signal.
  * mark_type_rate - train rate per mark type (Word/Figurative/...).
  * owner_country_rate - train rate per owner country.
  * calendar_month_rate - train rate per filing calendar month.
  * category_rate - train rate per category of mark.
  * series_flag_rate - train rate per series flag.
  * majority_class - majority fitted on train, measured against THIS split's
    labels; global_rate - constant train rate (no ranking information; AUC
    degenerate by construction, reported as such).
  * persistence - NOT APPLICABLE, recorded as a degenerate control: every
    scored row is a new application with no prior observation of the same
    entity, so "most recent observed value" does not exist for this task.
    Recorded explicitly instead of silently omitted.

The full model is NOT computed here: the harness runner's baseline job
trains and evaluates it on these same rows, and its figure is quoted beside
these references when it exists. Nothing in this file may run before
acceptance.

Eval-only: the holdout is sealed until the design is frozen and the runner
evaluates it once. Per-filing-year reporting is mandatory - cohort prevalence
drifts (negatives 13.4% train / 16.0% eval / 13.7% holdout) and the label
window length varies by cohort.

Uncertainty: paired bootstrap differences (150 resamples, fixed seed) on
identical eval rows - never overlapping marginal intervals. An interval
containing zero is an inconclusive difference, not parity.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

NAME = "ipo-trademark-registration-outcome"
TARGET = "registered"
POSITIVE = "1"
CLASS_COLUMNS = [f"class{i}" for i in range(1, 46)]
BOOTSTRAP = 150
SEED = 31
COMPARATORS = ["mark_type_rate", "owner_country_rate", "calendar_month_rate",
               "category_rate", "series_flag_rate"]


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def labels_of(rows: list[dict]) -> list[int]:
    return [1 if row[TARGET] == POSITIVE else 0 for row in rows]


def auc(labels: list[int], scores: list[float]) -> float | None:
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        return None
    if len(set(scores)) == 1:
        return None  # constant scores carry no ranking information
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    rank_sum = 0.0
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        average = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            if labels[order[k]]:
                rank_sum += average
        i = j + 1
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def brier(labels: list[int], probabilities: list[float]) -> float | None:
    if not labels:
        return None
    return sum((p - y) ** 2 for y, p in zip(labels, probabilities)) / len(labels)


def accuracy(labels: list[int], probabilities: list[float],
             threshold: float = 0.5) -> float | None:
    if not labels:
        return None
    return sum((p >= threshold) == bool(y) for y, p in
               zip(labels, probabilities)) / len(labels)


class RateTable:
    """Train-fit positive rate per level with global-rate backoff."""

    def __init__(self, name: str, key_fn, rows: list[dict], labels: list[int]):
        self.name = name
        self.key_fn = key_fn
        totals: dict[str, int] = defaultdict(int)
        positives: dict[str, int] = defaultdict(int)
        for row, label in zip(rows, labels):
            key = key_fn(row)
            totals[key] += 1
            if label:
                positives[key] += 1
        self.global_rate = sum(labels) / len(labels)
        self.table = {key: positives[key] / total for key, total in totals.items()}
        self.backoff_share = 1.0 - sum(
            1 for row in rows if self.key_fn(row) in self.table) / len(rows)
        self.levels = len(self.table)

    def score(self, row: dict) -> float:
        key = self.key_fn(row)
        return self.table.get(key, self.global_rate)


class ClassRateTable:
    """Required comparator: mean train rate over the row's assigned classes."""

    def __init__(self, rows: list[dict], labels: list[int]):
        totals = defaultdict(int)
        positives = defaultdict(int)
        for row, label in zip(rows, labels):
            for column in CLASS_COLUMNS:
                if row[column] == "1":
                    totals[column] += 1
                    if label:
                        positives[column] += 1
        self.global_rate = sum(labels) / len(labels)
        self.table = {column: positives[column] / totals[column]
                      for column in totals}
        self.classes_seen = len(self.table)
        self.no_class_rows = sum(1 for row in rows
                                 if not any(row[c] == "1" for c in CLASS_COLUMNS))

    def score(self, row: dict) -> float:
        assigned = [column for column in CLASS_COLUMNS if row[column] == "1"]
        if not assigned:
            return self.global_rate
        values = [self.table.get(column) for column in assigned]
        known = [value for value in values if value is not None]
        if not known:
            return self.global_rate
        return sum(known) / len(known)


def reference_scores(tables: dict, rows: list[dict]) -> dict[str, list[float]]:
    return {name: [table.score(row) for row in rows]
            for name, table in tables.items()}


def weighted_auc(scores: list[float], order: list[int], groups: list[list[int]],
                 count_pos: list[int], count_neg: list[int]) -> float | None:
    """Tie-aware AUC over a weighted resample, O(n) given precomputed order."""
    total_pos = sum(count_pos)
    total_neg = sum(count_neg)
    if not total_pos or not total_neg:
        return None
    u = 0.0
    cum_neg = 0
    for group in groups:
        neg_in = sum(count_neg[i] for i in group)
        pos_in = sum(count_pos[i] for i in group)
        if pos_in:
            u += pos_in * (cum_neg + 0.5 * neg_in)
        cum_neg += neg_in
    value = u / (total_pos * total_neg)
    return value


def precompute(scores: list[float]):
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    groups: list[list[int]] = []
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        groups.append(order[i:j + 1])
        i = j + 1
    return order, groups


def paired_bootstrap(labels: list[int], scores_a: list[float],
                     scores_b: list[float]) -> dict:
    """Paired bootstrap of AUC(A) - AUC(B) on identical eval rows."""
    if not labels:
        return {"note": "no rows"}
    pre_a = precompute(scores_a)
    pre_b = precompute(scores_b)
    rng = random.Random(SEED)
    n = len(labels)
    differences = []
    for _ in range(BOOTSTRAP):
        count_pos = [0] * n
        count_neg = [0] * n
        for _ in range(n):
            index = rng.randrange(n)
            if labels[index]:
                count_pos[index] += 1
            else:
                count_neg[index] += 1
        auc_a = weighted_auc(scores_a, *pre_a, count_pos, count_neg)
        auc_b = weighted_auc(scores_b, *pre_b, count_pos, count_neg)
        if auc_a is not None and auc_b is not None:
            differences.append(auc_a - auc_b)
    if not differences:
        return {"note": "degenerate resamples (a split lost one class)"}
    differences.sort()
    low = differences[int(0.025 * len(differences))]
    high = differences[int(0.975 * len(differences)) - 1]
    return {"resamples": len(differences),
            "mean_difference": round(sum(differences) / len(differences), 6),
            "ci95_low": round(low, 6), "ci95_high": round(high, 6),
            "interval_excludes_zero": bool(low > 0 or high < 0)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="accepted extract dir")
    parser.add_argument("--accepted-report", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    data = Path(args.data)
    report_path = Path(args.report)

    accepted = json.loads(Path(args.accepted_report).read_text())
    if not accepted.get("ok"):
        raise SystemExit("the qualification report did not pass; refusing to score")

    train_rows = read_rows(data / "public" / "train.csv")
    eval_rows = read_rows(data / "public" / "eval.csv")
    train_labels = labels_of(train_rows)
    eval_labels = labels_of(eval_rows)
    train_rate = sum(train_labels) / len(train_labels)

    month_of = lambda row: row["filed_date"][5:7]
    class_table = ClassRateTable(train_rows, train_labels)
    tables: dict[str, object] = {
        "nice_class_rate": class_table,
        "mark_type_rate": RateTable("mark_type_rate",
                                    lambda r: r["mark_type"],
                                    train_rows, train_labels),
        "owner_country_rate": RateTable("owner_country_rate",
                                        lambda r: r["owner_country"],
                                        train_rows, train_labels),
        "calendar_month_rate": RateTable("calendar_month_rate", month_of,
                                         train_rows, train_labels),
        "category_rate": RateTable("category_rate", lambda r: r["category"],
                                   train_rows, train_labels),
        "series_flag_rate": RateTable("series_flag_rate",
                                      lambda r: r["series_flag"],
                                      train_rows, train_labels),
    }
    scores = reference_scores(tables, eval_rows)

    references = {}
    for name, score in scores.items():
        table = tables[name]
        references[name] = {
            "information_set": ("train-fit positive rate per assigned Nice "
                                "class, averaged over the row's classes"
                                if name == "nice_class_rate" else
                                f"train-fit positive rate per "
                                f"{name.removesuffix('_rate').replace('_', ' ')}"),
            "levels": getattr(table, "levels", None)
                      or getattr(table, "classes_seen", None),
            "backoff_share": getattr(table, "backoff_share", None),
            "auc_eval": auc(eval_labels, score),
            "brier_eval": brier(eval_labels, score),
            "accuracy_eval_at_0.5": accuracy(eval_labels, score),
        }
    references["nice_class_rate"]["no_class_train_rows"] = class_table.no_class_rows

    majority = int(train_rate >= 0.5)
    majority_accuracy = sum(label == majority for label in eval_labels) / len(eval_labels)
    references["majority_class"] = {
        "information_set": "constant majority label fitted on train",
        "majority_label": majority,
        "accuracy_eval": majority_accuracy,
        "auc_eval": None,
        "note": "constant prediction: accuracy measured against this split's "
                "labels; AUC carries no ranking information",
    }
    references["global_rate"] = {
        "information_set": "constant train positive rate (no ranking information)",
        "train_positive_rate": round(train_rate, 6),
        "auc_eval": None,
        "note": "degenerate by construction: a constant score has no ranking "
                "information; recorded so no later reader quotes a "
                "'global-rate AUC'",
    }
    references["persistence"] = {
        "information_set": "most recent observed value of the same entity",
        "status": "not_applicable",
        "note": "every scored row is a new application: no prior observation "
                "of the same entity exists at the filing instant, so the "
                "persistence control is undefined for this task - recorded "
                "explicitly as a degenerate control, not silently omitted",
    }

    per_year = {}
    for year in ("2013", "2014"):
        rows = [row for row in eval_rows if row["filed_date"].startswith(year)]
        labels = labels_of(rows)
        entry = {"rows": len(rows), "positives": sum(labels),
                 "positive_rate": round(sum(labels) / len(labels), 6) if rows else None}
        for name, score in scores.items():
            subset = [s for s, row in zip(scores[name], eval_rows)
                      if row["filed_date"].startswith(year)]
            entry[name] = {"auc": auc(labels, subset),
                           "brier": brier(labels, subset)}
        per_year[year] = entry

    prevalence = {}
    for split, relative in (("train", "public/train.csv"),
                            ("eval", "public/eval.csv"),
                            ("holdout", "private/holdout.csv")):
        meta = json.loads((data / "meta.json").read_text())
        prevalence[split] = {
            "rows": meta["rows"][split],
            "positive_rate": meta["positive_rate"][split],
            "note": "read from meta.json (construction-stage facts); "
                    "score.py reads eval labels only",
        }

    bootstrap = {}
    for other in COMPARATORS:
        bootstrap[f"nice_class_rate_vs_{other}"] = paired_bootstrap(
            eval_labels, scores["nice_class_rate"], scores[other])

    report = {
        "name": NAME,
        "stage": "references (post-acceptance only; eval rows only, holdout sealed)",
        "fit_rows": len(train_rows),
        "eval_rows": len(eval_rows),
        "references": references,
        "per_filing_year_eval": per_year,
        "prevalence": prevalence,
        "prevalence_note": (
            "cohort prevalence drifts between splits (negatives 13.4% train "
            "/ 16.0% eval / 13.7% holdout at construction); eval is an "
            "out-of-prevalence window as well as a temporal one - "
            "investigate calibration before interpreting gaps"),
        "bootstrap_paired_differences_nice_class_rate": bootstrap,
        "bootstrap_note": (
            "paired differences on identical eval rows, 150 resamples, seed "
            f"{SEED}; which simple reference dominates decides the cheapest "
            "comparator a model must beat"),
        "runner_model_eval_auc": None,
        "runner_model_note": (
            "the full model is NOT computed here: the harness runner's "
            "baseline job trains the benchmark's own train.py on "
            "public/train.csv and evaluates on these same eval rows; its "
            "figure is quoted beside these references when it exists, with "
            "the model-vs-nice_class_rate paired difference computed then"),
        "acceptance": {"report": str(args.accepted_report),
                       "gate_version": accepted.get("gate_version"),
                       "artifact_version": (accepted.get("artifact", {})
                                            .get("artifact_version", {})
                                            .get("digest"))},
    }
    report_path.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({name: values.get("auc_eval", values.get("accuracy_eval"))
                      for name, values in references.items()}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
