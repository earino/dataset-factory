#!/usr/bin/env python3
"""Simple references for the accepted `ns-bwa-advisory-lift-duration` artifact.

Runs ONLY after the qualification gate has passed and --accept has re-verified
the report against these exact bytes. It reads the written CSVs, never
rewrites them, and computes every reference on the SAME eval rows.

The task is a per-advisory outcome question at the issue instant, so the
reference triad takes this shape:

  * persistence_site_prior - the site's own history at the instant: the
    mean lift30 outcome of earlier same-site advisories whose removal
    resolved strictly before this row's issue date (information set:
    strictly-earlier same-site outcomes, train and eval era alike -
    exactly what was knowable at the instant; global train rate fallback
    when the site has no resolved prior). v2026.12: the artifact no longer
    ships this value (it was the P0 label-recovery channel of the
    2026-11-01 independent audit), so it is recomputed HERE as a
    reference only, from the register fetched again and asserted byte-
    identical (sha256) to the register the artifact was constructed
    from - the same computation as v2026.10's shipped
    site_prior_lift30_rate feature. A useful model must beat this: it is
    the reference that tests whether issuance attributes add anything
    beyond "this site's advisories usually clear quickly".
  * calendar_county_month - county identity plus calendar month, estimated
    ONLY from training-era rows with county-then-global backoff: the
    seasonal/identity control.
  * reason_prior - train-estimated positive rate per normalised reason: the
    strongest single issuance attribute.
  * facility_prior - train-estimated positive rate per facility type.
  * majority_class - majority fitted on train, measured against THIS split's
    labels; global_rate - constant train rate (no ranking information; AUC
    degenerate by construction, reported as such).

The full model is NOT computed here: the harness runner's baseline job
trains and evaluates it on these same rows, and its figure is quoted beside
these references when it exists. Nothing in this file may run before
acceptance.

Eval-only: the holdout is sealed until the design is frozen and the runner
evaluates it once. Per-issue-year reporting is mandatory - advisory duration
has a measured regime shift around 2020 (mean 218 days in 2020 vs 47-65 days
in 2009-2018) that a pooled number would hide.

Uncertainty: paired bootstrap differences (1000 resamples, fixed seed) on
identical eval rows - never overlapping marginal intervals. An interval
containing zero is an inconclusive difference, not parity.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

NAME = "ns-bwa-advisory-lift-duration"
TARGET = "lift30"
POSITIVE = "1"
BOOTSTRAP = 1000
SEED = 23

REGISTER_URL = ("https://data.novascotia.ca/api/views/7t68-9xmm/rows.csv"
                "?accessType=DOWNLOAD")
REGISTER_UA = ("Scout-factory-references/1.0 (dataset-factory worker; "
               "Nova Scotia open data register)")
THRESHOLD_DAYS = 30
DATE_FORMATS = ("%B %d %Y", "%b %d %Y", "%B %d, %Y", "%b %d, %Y")


def normalize(text: str | None) -> str:
    return " ".join((text or "").split()).strip().lower()


def parse_date(text: str | None):
    value = normalize(text)
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def fetch_register() -> bytes:
    last_error = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(REGISTER_URL,
                                             headers={"User-Agent": REGISTER_UA})
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except Exception as exc:  # noqa: BLE001 - retried network fetch
            last_error = exc
            time.sleep(5 * (attempt + 1))
    raise SystemExit(f"register fetch failed after 3 attempts: {last_error}")


def site_persistence_scores(eval_rows: list[dict], train_rate: float,
                            summary: dict) -> tuple[list[float], dict]:
    """v2026.12 persistence reference, recomputed from the register.

    Identical computation to v2026.10's shipped site_prior_lift30_rate:
    one event per (normalised site, issue date) - representative row = the
    first with an observed non-negative duration, else the first
    still-in-effect row, else the group's first - and the score is the mean
    lift30 over events with removal strictly before the instant and
    non-negative duration; train_rate fallback when none. The register is
    asserted byte-identical (sha256) to the one the artifact was built
    from, so this reads exactly the accepted artifact's own vintage.
    """
    expected_sha = (summary.get("fetch") or {}).get("sha256")
    if not expected_sha:
        raise SystemExit("summary.json carries no register sha256; the "
                         "persistence reference cannot be tied to the "
                         "artifact's vintage")
    data = fetch_register()
    sha = hashlib.sha256(data).hexdigest()
    if sha != expected_sha:
        raise SystemExit(
            f"register changed since construction (sha256 {sha[:16]}... vs "
            f"recorded {expected_sha[:16]}...); the persistence reference "
            "must be computed on the artifact's own vintage")
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig", "replace")))
    by_site_date: dict[tuple, list[dict]] = defaultdict(list)
    for raw in reader:
        issue = parse_date(raw.get("Date Advisory Issued"))
        if issue is None:
            continue
        removal = parse_date(raw.get("Date Advisory Removed"))
        duration = (removal - issue).days if removal else None
        by_site_date[(normalize(raw.get("Site Name")), issue)].append(
            {"removal": removal,
             "removal_blank": not (raw.get("Date Advisory Removed") or
                                   "").strip(),
             "duration": duration})
    events: dict[str, list[dict]] = defaultdict(list)
    for (site, day), group in by_site_date.items():
        chosen = next((row for row in group
                       if row["removal"] is not None
                       and row["duration"] >= 0), None)
        if chosen is None:
            chosen = next((row for row in group if row["removal_blank"]),
                          group[0])
        chosen = dict(chosen)
        chosen["date"] = day
        events[site].append(chosen)
    for group in events.values():
        group.sort(key=lambda row: row["date"])

    scores: list[float] = []
    covered = 0
    for row in eval_rows:
        instant = date.fromisoformat(row["issue_date"])
        site = normalize(row["site_name"])
        earlier = [event for event in events.get(site, [])
                   if event["date"] < instant]
        resolved = [event for event in earlier
                    if event["removal"] is not None
                    and event["removal"] < instant
                    and event["duration"] >= 0]
        if resolved:
            rate = (sum(1 for event in resolved
                        if event["duration"] <= THRESHOLD_DAYS)
                    / len(resolved))
            covered += 1
        else:
            rate = train_rate
        scores.append(round(rate, 4))
    info = {"register_sha256": sha,
            "matches_artifact_vintage": True,
            "covered_rows": covered,
            "scoring": "identical to v2026.10's shipped "
                       "site_prior_lift30_rate, recomputed register-side "
                       "as a reference only (v2026.12 ships no "
                       "outcome-derived column)"}
    return scores, info


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
    ranks = [0.0] * len(order)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        average = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = average
        i = j + 1
    rank_sum = sum(ranks[k] for k in range(len(labels)) if labels[k])
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def brier(labels: list[int], probabilities: list[float]) -> float | None:
    if not labels:
        return None
    return sum((p - y) ** 2 for y, p in zip(labels, probabilities)) / len(labels)


def accuracy(labels: list[int], predictions: list[int]) -> float | None:
    if not labels:
        return None
    return sum(y == p for y, p in zip(labels, predictions)) / len(labels)


def paired_bootstrap_difference(labels: list[int], scores_a: list[float],
                                scores_b: list[float]) -> dict:
    """Paired bootstrap of AUC(A) - AUC(B) on identical rows."""
    if not labels:
        return {"note": "no rows"}
    rng = random.Random(SEED)
    differences = []
    for _ in range(BOOTSTRAP):
        sample = [rng.randrange(len(labels)) for _ in range(len(labels))]
        boot_labels = [labels[i] for i in sample]
        auc_a = auc(boot_labels, [scores_a[i] for i in sample])
        auc_b = auc(boot_labels, [scores_b[i] for i in sample])
        if auc_a is not None and auc_b is not None:
            differences.append(auc_a - auc_b)
    if not differences:
        return {"note": "degenerate resamples (a split lost one class)"}
    differences.sort()
    return {
        "resamples": len(differences),
        "mean": round(sum(differences) / len(differences), 6),
        "ci95_low": round(differences[int(0.025 * len(differences))], 6),
        "ci95_high": round(differences[int(0.975 * len(differences))], 6),
        "note": "paired bootstrap on identical rows; an interval containing "
                "zero is inconclusive, not parity",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--accepted-report", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    data = Path(args.data)

    report = json.loads(Path(args.accepted_report).read_text())
    if not report.get("ok"):
        raise SystemExit("the qualification report did not pass; "
                         "scoring is refused")

    train_rows = read_rows(data / "public" / "train.csv")
    eval_rows = read_rows(data / "public" / "eval.csv")
    train_labels = labels_of(train_rows)
    eval_labels = labels_of(eval_rows)
    train_rate = sum(train_labels) / len(train_labels)
    majority = 1 if train_rate >= 0.5 else 0

    # ---- references estimated ONLY from train -------------------------
    county_month = defaultdict(lambda: [0, 0])
    county_rate = defaultdict(lambda: [0, 0])
    for row, label in zip(train_rows, train_labels):
        key = (row["county"], row["issue_month"])
        county_month[key][0] += label
        county_month[key][1] += 1
        county_rate[row["county"]][0] += label
        county_rate[row["county"]][1] += 1

    def calendar_score(row: dict) -> float:
        key = (row["county"], row["issue_month"])
        if key in county_month and county_month[key][1] >= 5:
            return county_month[key][0] / county_month[key][1]
        if row["county"] in county_rate:
            return county_rate[row["county"]][0] / county_rate[row["county"]][1]
        return train_rate

    calendar_scores = [calendar_score(row) for row in eval_rows]

    reason_rate = defaultdict(lambda: [0, 0])
    facility_rate = defaultdict(lambda: [0, 0])
    for row, label in zip(train_rows, train_labels):
        reason_rate[row["reason"]][0] += label
        reason_rate[row["reason"]][1] += 1
        facility_rate[row["facility_type"]][0] += label
        facility_rate[row["facility_type"]][1] += 1

    reason_scores = [
        (reason_rate[row["reason"]][0] / reason_rate[row["reason"]][1]
         if row["reason"] in reason_rate else train_rate)
        for row in eval_rows]
    facility_scores = [
        (facility_rate[row["facility_type"]][0]
         / facility_rate[row["facility_type"]][1]
         if row["facility_type"] in facility_rate else train_rate)
        for row in eval_rows]

    # persistence: the site's own as-of outcome history, recomputed from
    # the register (v2026.12 ships no outcome-derived column); the fetched
    # register is asserted byte-identical to the artifact's own vintage.
    summary = json.loads((data / "summary.json").read_text())
    persistence_scores, persistence_info = site_persistence_scores(
        eval_rows, train_rate, summary)
    persistence_covered = persistence_info["covered_rows"]

    references = {
        "majority_class": {
            "definition": "majority label fitted on train, measured against "
                          "this split's labels",
            "prediction": majority,
            "accuracy": accuracy(eval_labels, [majority] * len(eval_rows)),
        },
        "global_rate": {
            "definition": "constant train positive rate; no ranking "
                          "information, AUC degenerate by construction",
            "rate": round(train_rate, 6),
            "brier": brier(eval_labels, [train_rate] * len(eval_rows)),
            "auc": None,
        },
        "persistence_site_prior": {
            "definition": "the site's as-of lift30 rate over earlier "
                          "same-site advisories resolved strictly before the "
                          "instant, recomputed register-side after "
                          "acceptance (v2026.10 shipped this as "
                          "site_prior_lift30_rate; v2026.12 removed the "
                          "column and keeps the value as a reference only); "
                          "register asserted sha256-identical to the "
                          "artifact's vintage; global train rate fallback",
            "reference_info": persistence_info,
            "covered_rows": persistence_covered,
            "coverage": round(persistence_covered / len(eval_rows), 4),
            "auc": auc(eval_labels, persistence_scores),
            "brier": brier(eval_labels, persistence_scores),
        },
        "calendar_county_month": {
            "definition": "train-estimated (county, issue month) rate with "
                          ">=5 train rows, county rate then global train "
                          "rate backoff (identity + seasonal control)",
            "train_counties": len(county_rate),
            "unseen_county_rows": sum(1 for row in eval_rows
                                      if row["county"] not in county_rate),
            "auc": auc(eval_labels, calendar_scores),
            "brier": brier(eval_labels, calendar_scores),
        },
        "reason_prior": {
            "definition": "train-estimated positive rate per normalised "
                          "reason, global rate fallback",
            "train_reasons": sorted(reason_rate),
            "auc": auc(eval_labels, reason_scores),
            "brier": brier(eval_labels, reason_scores),
        },
        "facility_prior": {
            "definition": "train-estimated positive rate per facility type, "
                          "global rate fallback",
            "train_types": sorted(facility_rate),
            "auc": auc(eval_labels, facility_scores),
            "brier": brier(eval_labels, facility_scores),
        },
    }

    differences = {
        "persistence_vs_calendar": paired_bootstrap_difference(
            eval_labels, persistence_scores, calendar_scores),
        "calendar_vs_reason": paired_bootstrap_difference(
            eval_labels, calendar_scores, reason_scores),
        "persistence_vs_reason": paired_bootstrap_difference(
            eval_labels, persistence_scores, reason_scores),
    }

    per_year = {}
    by_year = defaultdict(list)
    for index, row in enumerate(eval_rows):
        by_year[row["issue_date"][:4]].append(index)
    for year, indexes in sorted(by_year.items()):
        labels = [eval_labels[i] for i in indexes]
        per_year[year] = {
            "rows": len(indexes),
            "positives": sum(labels),
            "positive_rate": round(sum(labels) / len(labels), 4),
            "persistence_auc": auc(labels, [persistence_scores[i]
                                            for i in indexes]),
            "calendar_auc": auc(labels, [calendar_scores[i]
                                         for i in indexes]),
            "reason_auc": auc(labels, [reason_scores[i] for i in indexes]),
            "persistence_brier": brier(labels, [persistence_scores[i]
                                                for i in indexes]),
        }

    output = {
        "name": NAME,
        "stage": "simple references on identical eval rows (post-acceptance)",
        "accepted_report": Path(args.accepted_report).name,
        "artifact_version": ((report.get("artifact") or {}).get(
            "artifact_version") or {}).get("digest"),
        "rows": {"train": len(train_rows), "eval": len(eval_rows)},
        "train_positive_rate": round(train_rate, 6),
        "eval_positive_rate": round(sum(eval_labels) / len(eval_labels), 6),
        "references": references,
        "paired_differences": differences,
        "per_issue_year": per_year,
        "notes": [
            "persistence is the site's own as-of outcome history; it may "
            "embed strictly-earlier eval-era outcomes, which is exactly its "
            "information set at the instant - unlike the train-only "
            "references. v2026.12 recomputes it register-side (the "
            "shipped column was removed after the 2026-11-01 audit "
            "recovered labels from it); the register is asserted "
            "sha256-identical to the artifact's vintage, so the reference "
            "reads no information the artifact's own construction did not",
            "calendar_county_month, reason_prior and facility_prior are "
            "estimated only from training-era rows",
            "constant global_rate scores carry no ranking information; its "
            "AUC is reported null, not zero",
            "the full model (harness runner baseline) is quoted beside these "
            "references when its job exists; it is not computed here",
            "the holdout is sealed: no reference or model in this file "
            "reads private/holdout.csv",
            "per-issue-year figures are mandatory reading beside the pooled "
            "ones: duration has a measured regime shift around 2020",
        ],
    }
    Path(args.report).write_text(json.dumps(output, indent=1) + "\n")
    for name, ref in references.items():
        print(f"{name}: auc={ref.get('auc')} brier={ref.get('brier')} "
              f"accuracy={ref.get('accuracy')}")
    print(f"eval positive_rate={output['eval_positive_rate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
