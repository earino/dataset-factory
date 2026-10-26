#!/usr/bin/env python3
"""Simple references for the accepted `ec-merger-phase2-opening` artifact.

Runs ONLY after the qualification gate has passed and --accept has
re-verified the report against these exact bytes. It reads the written CSVs,
never rewrites them, and computes every reference on the SAME eval rows.

What is measured, and why in this shape
---------------------------------------
The task is a case-level classification: each row is a newly notified merger
case and every feature is fixed at its notification, so the baseline triad's
first member has no direct analogue:

  * persistence - RECORDED INAPPLICABLE. There is no prior observation of the
    same entity at the instant: a newly notified case has no history. The
    nearest regime-drift analogue is carried instead as `recent_rate` (the
    train positive rate over the last three train years). An inapplicable
    reference is recorded as such, never faked with a renamed constant.
  * sector_division_rate - THE REQUIRED COMPARATOR (the candidate record
    pins the sector-conditional rate as the reference a model must beat):
    train-fitted positive rate per NACE division, averaged over the case's
    divisions, global train rate fallback for NONE/unseen. Divisions are
    derived from the shipped sector_divisions column (the corrected grouping;
    the discovery probe grouped on the register code's last component).
  * sector_combo_rate - train rate per exact sector combination string,
    global fallback; the raw categorical prior.
  * calendar_identity - train rate per (regulation, notification month):
    the era-identity plus seasonal prior estimated only from training rows.
  * title_text - train rate per party-name token (lowercased alphanumeric
    tokens of length >= 3 seen in >= 5 train rows), averaged, global fallback:
    the repeat-acquirer signal the record names as a further baseline.
  * majority_class - majority fitted on train, measured against THIS split's
    labels; global_rate - constant train rate, AUC null (no ranking
    information).

The full model is NOT computed here: the harness runner's baseline job
trains and evaluates it on these same rows, and its figure is quoted beside
these references when it exists. Nothing in this file may run before
acceptance.

Uncertainty: paired bootstrap differences (1000 resamples, fixed seed) on
identical eval rows - never overlapping marginal intervals. An interval
containing zero is an inconclusive difference, not parity.

Per-year reporting is mandatory: the eval window spans 2014-2018 and the
holdout sits in a different enforcement era with maturing recent procedures,
so pooled numbers hide structural change. Eval-only here; the holdout is
sealed until the design is frozen and the runner evaluates it once.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

NAME = "ec-merger-phase2-opening"
TARGET = "phase2_opened"
POSITIVE = "1"
BOOTSTRAP = 1000
SEED = 17
MIN_TOKEN_ROWS = 5


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
    pairs = sorted(zip(scores, labels), key=lambda pair: pair[0])
    ranks = [0.0] * len(pairs)
    i = 0
    while i < len(pairs):
        j = i
        while j + 1 < len(pairs) and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        average = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[k] = average
        i = j + 1
    positive_rank_sum = sum(rank for rank, (_score, label) in zip(ranks, pairs) if label)
    return (positive_rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def brier(labels: list[int], probabilities: list[float]) -> float | None:
    if not labels:
        return None
    return sum((p - y) ** 2 for y, p in zip(labels, probabilities)) / len(labels)


def accuracy(labels: list[int], predictions: list[int]) -> float | None:
    if not labels:
        return None
    return sum(1 for y, p in zip(labels, predictions) if y == p) / len(labels)


def paired_bootstrap_difference(labels: list[int], scores_a: list[float],
                                scores_b: list[float]) -> dict:
    auc_a = auc(labels, scores_a)
    auc_b = auc(labels, scores_b)
    if auc_a is None or auc_b is None:
        return {"observed_difference": None, "auc_a": auc_a, "auc_b": auc_b,
                "ci95": None, "note": "one reference has a single class on this split"}
    difference = auc_a - auc_b
    rng = random.Random(SEED)
    n = len(labels)

    def boot_difference(indices: list[int]) -> float | None:
        boot_labels = [labels[i] for i in indices]
        left = auc(boot_labels, [scores_a[i] for i in indices])
        right = auc(boot_labels, [scores_b[i] for i in indices])
        if left is None or right is None:
            return None
        return left - right

    samples = []
    for _ in range(BOOTSTRAP):
        indices = [rng.randrange(n) for _ in range(n)]
        value = boot_difference(indices)
        if value is not None:
            samples.append(value)
    samples.sort()
    if len(samples) < 100:
        return {"observed_difference": round(difference, 6), "auc_a": round(auc_a, 6),
                "auc_b": round(auc_b, 6), "ci95": None,
                "note": "too few bootstrap samples with both classes"}
    low = samples[int(0.025 * len(samples))]
    high = samples[int(0.975 * len(samples)) - 1]
    return {"observed_difference": round(difference, 6), "auc_a": round(auc_a, 6),
            "auc_b": round(auc_b, 6), "ci95": [round(low, 6), round(high, 6)],
            "bootstrap_samples": len(samples),
            "note": "paired row bootstrap on identical eval rows; an interval "
                    "containing zero is an inconclusive difference, not parity"}


def tokens_of(title: str) -> set[str]:
    import re
    return {token.lower() for token in re.findall(r"[A-Za-z0-9]{3,}", title)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--accepted-report", required=True,
                        help="qualification report whose artifact digest this evidence binds to")
    args = parser.parse_args()

    accepted = json.loads(Path(args.accepted_report).read_text())
    if not accepted.get("ok"):
        print("REFUSING TO SCORE: the accepted report did not pass")
        return 1

    data = Path(args.data)
    train = read_rows(data / "public" / "train.csv")
    eval_rows = read_rows(data / "public" / "eval.csv")
    train_labels = labels_of(train)
    eval_labels = labels_of(eval_rows)
    train_rate = sum(train_labels) / len(train_labels) if train_labels else 0.0

    # ---- train-fitted priors (training rows only) -------------------------
    division_stats: dict[str, list] = defaultdict(lambda: [0, 0])
    combo_stats: dict[str, list] = defaultdict(lambda: [0, 0])
    cal_stats: dict[tuple, list] = defaultdict(lambda: [0, 0])
    token_stats: dict[str, list] = defaultdict(lambda: [0, 0])
    for row, label in zip(train, train_labels):
        for division in row["sector_divisions"].split("|"):
            entry = division_stats[division]
            entry[0] += label
            entry[1] += 1
        entry = combo_stats[row["sector_divisions"]]
        entry[0] += label
        entry[1] += 1
        entry = cal_stats[(row["regulation"], row["notification_month"])]
        entry[0] += label
        entry[1] += 1
        for token in tokens_of(row["case_title"]):
            entry = token_stats[token]
            entry[0] += label
            entry[1] += 1
    division_rate = {k: v[0] / v[1] for k, v in division_stats.items() if v[1]}
    combo_rate = {k: v[0] / v[1] for k, v in combo_stats.items() if v[1]}
    cal_rate = {k: v[0] / v[1] for k, v in cal_stats.items() if v[1]}
    token_rate = {k: v[0] / v[1] for k, v in token_stats.items()
                  if v[1] >= MIN_TOKEN_ROWS}

    def sector_score(row: dict) -> float:
        divisions = [d for d in row["sector_divisions"].split("|")
                     if d in division_rate]
        if not divisions:
            return train_rate
        return sum(division_rate[d] for d in divisions) / len(divisions)

    def combo_score(row: dict) -> float:
        return combo_rate.get(row["sector_divisions"], train_rate)

    def calendar_score(row: dict) -> float:
        return cal_rate.get((row["regulation"], row["notification_month"]), train_rate)

    def title_score(row: dict) -> float:
        known = [token_rate[t] for t in tokens_of(row["case_title"]) if t in token_rate]
        if not known:
            return train_rate
        return sum(known) / len(known)

    sector_scores = [sector_score(row) for row in eval_rows]
    combo_scores = [combo_score(row) for row in eval_rows]
    calendar_scores = [calendar_score(row) for row in eval_rows]
    title_scores = [title_score(row) for row in eval_rows]

    # recent-era constant: train rate over the last three train years
    train_years = sorted({int(row["notification_year"]) for row in train})
    recent_years = set(train_years[-3:])
    recent_labels = [label for row, label in zip(train, train_labels)
                     if int(row["notification_year"]) in recent_years]
    recent_rate = (sum(recent_labels) / len(recent_labels)) if recent_labels else train_rate

    references = {
        "name": NAME,
        "stage": "post-acceptance simple references (eval only, train-fitted)",
        "rows": len(eval_rows),
        "positives": sum(eval_labels),
        "train_positive_rate": round(train_rate, 6),
        "recent_train_years": sorted(recent_years),
        "references": {
            "persistence": {
                "applicable": False,
                "definition": "inapplicable: each row is a newly notified case "
                              "with no prior observation of the same entity at "
                              "the instant; the nearest analogue is recent_rate",
                "auc": None,
            },
            "recent_rate": {
                "definition": f"constant train positive rate over the last three "
                              f"train years {sorted(recent_years)} "
                              f"({round(recent_rate, 6)}); regime-drift probe",
                "auc": auc(eval_labels, [recent_rate] * len(eval_labels)),
                "brier": brier(eval_labels, [recent_rate] * len(eval_labels)),
            },
            "sector_division_rate": {
                "definition": "REQUIRED COMPARATOR: train-fitted positive rate per "
                              "NACE division (corrected grouping), averaged over "
                              "the case's divisions, global train rate fallback",
                "auc": auc(eval_labels, sector_scores),
                "brier": brier(eval_labels, sector_scores),
            },
            "sector_combo_rate": {
                "definition": "train rate per exact sector_divisions string, "
                              "global fallback",
                "auc": auc(eval_labels, combo_scores),
                "brier": brier(eval_labels, combo_scores),
            },
            "calendar_identity": {
                "definition": "train rate per (regulation, notification month): "
                              "era identity plus seasonal prior, training rows only",
                "auc": auc(eval_labels, calendar_scores),
                "brier": brier(eval_labels, calendar_scores),
            },
            "title_text": {
                "definition": "train rate per party-name token (>=3 alphanumeric "
                              f"chars, >= {MIN_TOKEN_ROWS} train rows), averaged, "
                              "global fallback",
                "auc": auc(eval_labels, title_scores),
                "brier": brier(eval_labels, title_scores),
            },
            "majority_class": {
                "definition": "majority = int(train_positive_rate >= 0.5), measured "
                              "against THIS split's labels",
                "accuracy": accuracy(eval_labels,
                                     [1 if train_rate >= 0.5 else 0] * len(eval_labels)),
            },
            "global_rate": {
                "definition": "constant train positive rate; no ranking information",
                "auc": None,
                "brier": brier(eval_labels, [train_rate] * len(eval_labels)),
            },
        },
        "full_model": ("NOT computed at this stage: the harness runner's baseline "
                       "job trains and evaluates the full model on these same eval "
                       "rows; quote its figure beside these references when it "
                       "exists"),
        "prevalence_shift": {
            "note": "train 1990-2013 vs eval 2014-2018 vs holdout 2019-snapshot "
                    "base rates, read from meta.json (gate-verified); a shift is "
                    "an out-of-distribution property to report, not a construction "
                    "fault",
            "rates": (json.loads((data / "meta.json").read_text()))["positive_rate"],
        },
        "paired_differences": {
            "sector_vs_global":
                paired_bootstrap_difference(eval_labels, sector_scores,
                                            [train_rate] * len(eval_rows)),
            "sector_vs_calendar_identity":
                paired_bootstrap_difference(eval_labels, sector_scores, calendar_scores),
            "title_text_vs_sector":
                paired_bootstrap_difference(eval_labels, title_scores, sector_scores),
        },
    }

    # per-year reporting (mandatory: structural change across the window)
    per_year: dict[str, dict] = defaultdict(lambda: {"rows": 0, "positives": 0})
    for row, label, sector, cal, title in zip(eval_rows, eval_labels, sector_scores,
                                              calendar_scores, title_scores):
        year = row["notification_year"]
        entry = per_year[str(year)]
        entry["rows"] += 1
        entry["positives"] += label
        entry.setdefault("labels", []).append(label)
        entry.setdefault("sector_scores", []).append(sector)
        entry.setdefault("calendar_scores", []).append(cal)
        entry.setdefault("title_scores", []).append(title)
    for year, entry in sorted(per_year.items()):
        references.setdefault("per_year", {})[year] = {
            "rows": entry["rows"],
            "positives": entry["positives"],
            "positive_rate": round(entry["positives"] / entry["rows"], 6),
            "sector_division_rate_auc": auc(entry["labels"], entry["sector_scores"]),
            "calendar_identity_auc": auc(entry["labels"], entry["calendar_scores"]),
            "title_text_auc": auc(entry["labels"], entry["title_scores"]),
        }

    references["accepted_artifact_version"] = (accepted.get("artifact_version", {})
                                                .get("digest"))
    references["gate_version_of_accepted_report"] = accepted.get("gate_version")

    Path(args.report).write_text(json.dumps(references, indent=1) + "\n")
    print(json.dumps(references, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
