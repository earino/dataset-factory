#!/usr/bin/env python3
"""Simple references for the accepted `chilecompra-tender-outcome` artifact.

Runs ONLY after the qualification gate has passed and `--accept` has
re-verified the report against these exact bytes. It reads the written CSVs,
never rewrites them, and computes every reference on the SAME eval rows.

What is measured, and why in this shape
---------------------------------------
This task is cross-sectional: each tender appears once, so there is no
per-entity series and the usual "persistence = last observed value" reference
is INAPPLICABLE. That is recorded here rather than replaced by a lookalike.
What replaces it is the family a persistence reference would otherwise stand in
for - conditional rates fitted on TRAIN only and applied to eval rows:

  * global_rate      - the train positive rate as a constant score. A constant
                       has no ranking information, so its AUC is reported as
                       null (not 0.5, which would imply a measured tie).
  * majority_class   - majority = int(train_positive_rate >= 0.5); accuracy is
                       measured against THIS split's labels, per the
                       qualification skill, never the training prevalence.
  * procedure_only   - positive rate per procedure_code, fitted on train.
  * region_only      - positive rate per buyer_region, fitted on train.
  * unspsc_only      - positive rate per UNSPSC segment, fitted on train.
  * calendar_only    - positive rate per (buyer_region, pub_month), fitted on
                       train: identity plus a seasonal prior from the training
                       era, which is what a calendar/identity control means
                       here.
  * value_procedure  - positive rate per (procedure_code, value band), fitted on
                       train, where the value band is a train quantile split.

Unseen levels fall back to the training global rate (recorded per reference as
the share of eval rows that fell back). The holdout is NOT scored here: it stays
outside every reference computation until the design is frozen and the runner
evaluates it once.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

TARGET = "deserted"
POSITIVE = "1"


def read_split(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def auc(labels: list[int], scores: list[float]) -> float | None:
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        return None
    pairs = sorted(zip(scores, labels), key=lambda pair: pair[0])
    ranks = [0.0] * len(pairs)
    index = 0
    while index < len(pairs):
        stop = index
        while stop < len(pairs) and pairs[stop][0] == pairs[index][0]:
            stop += 1
        rank = (index + stop + 1) / 2.0
        for pos in range(index, stop):
            ranks[pos] = rank
        index = stop
    rank_sum = sum(rank for rank, (_, label) in zip(ranks, pairs) if label == 1)
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def rate_table(rows: list[dict[str, str]], key) -> tuple[dict, float]:
    counts: dict = defaultdict(lambda: [0, 0])
    for row in rows:
        level = key(row)
        counts[level][0] += 1
        counts[level][1] += int(row[TARGET] == POSITIVE)
    rates = {level: hits / n for level, (n, hits) in counts.items() if n}
    return rates, len(rows)


def evaluate(rows: list[dict[str, str]], rates: dict, key, prior: float) -> dict:
    labels = [int(row[TARGET] == POSITIVE) for row in rows]
    scores = []
    fallback = 0
    for row in rows:
        level = key(row)
        if level in rates:
            scores.append(rates[level])
        else:
            scores.append(prior)
            fallback += 1
    return {"auc": None if auc(labels, scores) is None else round(auc(labels, scores), 4),
            "rows": len(rows), "positives": sum(labels),
            "fallback_rows": fallback,
            "fallback_share": round(fallback / len(rows), 4) if rows else None,
            "levels_used": sum(1 for level in rates if level in {key(r) for r in rows})}


def value_band(thresholds: list[float]):
    def band(row: dict[str, str]) -> str:
        raw = row.get("estimated_value_clp", "")
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return "missing"
        low = -1.0
        for index, edge in enumerate(thresholds):
            if value <= edge:
                return f"q{index}"
            low = edge
        return f"q{len(thresholds)}"
    return band


def quantiles(values: list[float], parts: int = 3) -> list[float]:
    ordered = sorted(values)
    if not ordered:
        return []
    return [ordered[min(len(ordered) - 1, int(len(ordered) * (i + 1) / parts) - 1)]
            for i in range(parts - 1)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    root = Path(args.data)
    train = read_split(root / "public/train.csv")
    evaluation = read_split(root / "public/eval.csv")
    if not train or not evaluation:
        raise SystemExit("train or eval split is empty; nothing to reference")

    train_pos = sum(1 for row in train if row[TARGET] == POSITIVE)
    train_rate = train_pos / len(train)
    majority = int(train_rate >= 0.5)
    eval_labels = [int(row[TARGET] == POSITIVE) for row in evaluation]
    majority_accuracy = sum(1 for label in eval_labels if label == majority) / len(eval_labels)

    values = []
    for row in train:
        try:
            values.append(float(row.get("estimated_value_clp", "")))
        except (TypeError, ValueError):
            continue
    thresholds = quantiles(values, 3)

    references = {
        "global_rate": {"value": round(train_rate, 6), "auc": None,
                        "note": "constant score fitted on train; a constant has no "
                                "ranking information, so AUC is unmeasured, not 0.5"},
        "majority_class": {
            "majority": majority,
            "train_positive_rate": round(train_rate, 6),
            "eval_accuracy": round(majority_accuracy, 6),
            "eval_rows": len(eval_labels),
            "note": "majority fitted on train, accuracy measured against eval labels"},
        "persistence": {
            "applicable": False,
            "note": "each tender appears once (no per-entity series), so a "
                    "last-observed-value reference does not exist for this task; the "
                    "conditional-rate references below play that role and are measured "
                    "on identical eval rows"},
    }

    keys = {
        "procedure_only": lambda row: row.get("procedure_code", ""),
        "region_only": lambda row: row.get("buyer_region", ""),
        "unspsc_only": lambda row: row.get("unspsc_segment", ""),
        "calendar_only": lambda row: (row.get("buyer_region", ""), row.get("pub_month", "")),
        "value_procedure": lambda row: (row.get("procedure_code", ""),
                                        value_band(thresholds)(row)),
    }
    for name, key in keys.items():
        rates, _ = rate_table(train, key)
        references[name] = evaluate(evaluation, rates, key, train_rate)
        references[name]["fitted_on"] = "train only"

    by_month = {}
    for month in sorted({row.get("pub_month", "") for row in evaluation}):
        subset = [row for row in evaluation if row.get("pub_month", "") == month]
        labels = [int(row[TARGET] == POSITIVE) for row in subset]
        by_month[month] = {"rows": len(subset), "positives": sum(labels),
                           "positive_rate": round(sum(labels) / len(subset), 6)}
    references["eval_by_publication_month"] = by_month
    references["eval_positive_rate"] = round(sum(eval_labels) / len(eval_labels), 6)
    references["train_positive_rate"] = round(train_rate, 6)
    references["value_band_thresholds_clp"] = thresholds

    report = {
        "artifact": "chilecompra-tender-outcome",
        "scope": "eval split only (public/eval.csv); the holdout is untouched by "
                 "this script",
        "note": "every reference is fitted on train rows and scored on the same eval "
                "rows, with unseen levels falling back to the train global rate. No "
                "model has been fitted here; the runner's full-model baseline is a "
                "separate stage.",
        "references": references,
    }
    Path(args.report).write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
