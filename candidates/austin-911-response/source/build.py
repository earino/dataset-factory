#!/usr/bin/env python3
"""Construction script for the `austin-911-response` candidate.

Builds the train / eval / holdout extracts for the task "will a dispatched Austin police
911 call be answered on scene more than T minutes after the call was dispatched?".

Where this runs
---------------
**On a temporary worker, not on the coordinator.** The full series is ~1,050,000 rows and
the coordinator has 1.9 GiB of RAM and ~6 GB of disk. Use `--limit` for a bounded local
exercise that proves the script works without pulling the whole series.

The script is stdlib-only, mirroring the rest of the factory code.

Method
------
1. Freeze the threshold T from the **training window alone**, by binary-searching the
   Socrata aggregate so the training positive rate is as close as possible to
   `--target-rate` (default 0.40). Only COUNT queries are used, so no rows are fetched.
2. Page the series in `incident_number` order (unique, so paging is stable) and write each
   row to the split its `response_datetime` belongs to.
3. Record per-file SHA-256 checksums, row counts, the positive rate per split, and a
   simple category-rate baseline with its AUC.

Leakage discipline, from the candidate notes
--------------------------------------------
Features are dispatch-time only. `priority_level` (assigned at the officer's arrival) and
`mental_health_flag` (settable from the final problem description and the call disposition)
are post-hoc and are excluded, together with every arrival, closing, disposition, unit,
injury and final-classification field. The target uses the portal's own `response_time`
column, which begins when the call was *answered* - earlier than `response_datetime` - so it
can never be recomputed from the timestamps in the row.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATASET = "e687-fx2y"
BASE = "https://datahub.austintexas.gov"
USER_AGENT = {"User-Agent": "scout-dataset-factory/0.1 (construction)"}

# Dispatch-time features. `response_day_of_week` and `response_hour` are the portal's own
# derivations of `response_datetime`; nothing here is known only after the response.
FEATURES = [
    "incident_type",
    "sector",
    "council_district",
    "geoid",
    "blkgpnm",
    "response_day_of_week",
    "response_hour",
    "initial_problem_description",
    "initial_problem_category",
]

# Columns deliberately excluded, recorded so the exclusion is auditable rather than implied.
EXCLUDED_POST_HOC = [
    "priority_level",
    "mental_health_flag",
    "first_unit_arrived_datetime",
    "call_closed_datetime",
    "final_problem_description",
    "final_problem_category",
    "call_disposition_description",
    "number_of_units_arrived",
    "unit_time_on_scene",
    "report_written_flag",
    "officer_injured_killed_count",
    "subject_injured_killed_count",
    "other_injured_killed_count",
]

# `response_time` is the label source and `incident_number` is an identifier: carried in
# the file for scoring and reconciliation, never features.
CARRY_COLUMNS = ["incident_number", "response_datetime", "response_time"]

SPLITS = [
    ("train", "response_datetime < '2025-01-01T00:00:00.000'"),
    ("eval", "response_datetime >= '2025-01-01T00:00:00.000' AND "
             "response_datetime < '2026-01-01T00:00:00.000'"),
    ("holdout", "response_datetime >= '2026-01-01T00:00:00.000'"),
]

TRAIN_WHERE = SPLITS[0][1]
ELIGIBLE = "response_time IS NOT NULL"


def get_json(url: str, attempts: int = 4, timeout: int = 180):
    last = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers=USER_AGENT)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:160]}"
        except Exception as exc:  # noqa: BLE001
            last = repr(exc)
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"request failed after {attempts} attempts: {last}")


def resource_url(params: dict) -> str:
    return f"{BASE}/resource/{DATASET}.json?" + urllib.parse.urlencode(params)


def count(where: str) -> int:
    rows = get_json(resource_url({"$select": "count(*) AS n", "$where": where}))
    return int(rows[0]["n"]) if rows else 0


def freeze_threshold(target_rate: float, lo: int = 0, hi: int = 21600) -> dict:
    """Binary-search T so P(response_time > T) in the TRAINING WINDOW is near target_rate.

    Aggregate COUNT queries only, so this costs no row downloads. The returned T is the
    largest tested value whose training rate is still at or above the target, which keeps
    the choice monotone and reproducible.
    """
    base = count(f"{ELIGIBLE} AND {TRAIN_WHERE}")
    if not base:
        raise RuntimeError("training window is empty; check the split boundaries")

    probes = []

    def rate_at(threshold: int) -> float:
        n = count(f"{ELIGIBLE} AND {TRAIN_WHERE} AND response_time > {threshold}")
        probes.append({"threshold_seconds": threshold, "n_above": n, "rate": n / base})
        return n / base

    low, high = lo, hi
    while high - low > 60:
        mid = ((low + high) // 2 // 60) * 60
        if mid <= low:
            break
        if rate_at(mid) >= target_rate:
            low = mid
        else:
            high = mid

    chosen = low
    # Snap to the nearest whole minute and re-measure both sides for the record.
    chosen = int(round(chosen / 60.0)) * 60
    chosen_rate = rate_at(chosen)
    return {
        "threshold_seconds": chosen,
        "threshold_minutes": chosen // 60,
        "training_rows": base,
        "training_rate_at_threshold": round(chosen_rate, 6),
        "target_rate": target_rate,
        "probes": probes,
        "rule": "binary search on the training-window aggregate so P(response_time > T) "
                "is just at or above the target rate; frozen before any row is scored",
    }


def stream_rows(where: str, select: str, page_size: int, limit: int | None = None,
                order: str = "incident_number"):
    """Yield rows in a stable order. Ordering by the unique incident number prevents
    paging from skipping rows that share a response_datetime."""
    offset = 0
    seen = 0
    while True:
        want = page_size if limit is None else min(page_size, limit - seen)
        if want <= 0:
            return
        params = {"$select": select, "$where": where, "$order": order,
                  "$limit": str(want), "$offset": str(offset)}
        rows = get_json(resource_url(params))
        if not rows:
            return
        for row in rows:
            yield row
        seen += len(rows)
        offset += len(rows)
        if len(rows) < want:
            return


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_iso(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def auc_from_scores(labels: list[int], scores: list[float]) -> float | None:
    """Rank-based ROC AUC, ties averaged. Pure stdlib so the worker needs no ML stack."""
    if len(labels) != len(scores):
        raise ValueError("labels and scores must align")
    pairs = sorted(zip(scores, labels), key=lambda pair: pair[0])
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    rank_sum = 0.0
    index = 0
    while index < len(pairs):
        end = index
        while end + 1 < len(pairs) and pairs[end + 1][0] == pairs[index][0]:
            end += 1
        average_rank = (index + end) / 2.0 + 1.0
        for position in range(index, end + 1):
            if pairs[position][1] == 1:
                rank_sum += average_rank
        index = end + 1
    return (rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def category_rate_baseline(train_rows: list[dict], scored_rows: list[dict],
                           column: str = "initial_problem_category") -> dict:
    """A one-rule baseline: score a row by its category's training-window positive rate."""
    positives: dict[str, int] = {}
    totals: dict[str, int] = {}
    for row in train_rows:
        key = row.get(column) or "(missing)"
        totals[key] = totals.get(key, 0) + 1
        positives[key] = positives.get(key, 0) + int(row["_label"])
    base_rate = (sum(positives.values()) / len(train_rows)) if train_rows else 0.0
    rates = {key: positives.get(key, 0) / totals[key] for key in totals}

    labels = [int(row["_label"]) for row in scored_rows]
    scores = [rates.get(row.get(column) or "(missing)", base_rate) for row in scored_rows]
    auc = auc_from_scores(labels, scores)
    positive = sum(labels)
    majority_accuracy = (max(positive, len(labels) - positive) / len(labels)) if labels else None
    return {
        "column": column,
        "categories_in_train": len(rates),
        "training_base_rate": round(base_rate, 6),
        "rows_scored": len(scored_rows),
        "positives": positive,
        "auc": round(auc, 6) if auc is not None else None,
        "majority_class_accuracy": round(majority_accuracy, 6) if majority_accuracy else None,
        "note": "single-feature baseline; a competent model must beat this AUC",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the austin-911-response extracts")
    parser.add_argument("--out", default="/output",
                        help="output directory for the extracts (default: /output on a worker)")
    parser.add_argument("--target-rate", type=float, default=0.40,
                        help="training-window positive rate the threshold T is frozen at")
    parser.add_argument("--page-size", type=int, default=20000)
    parser.add_argument("--limit", type=int, default=None,
                        help="cap rows PER SPLIT; for a bounded coordinator exercise only")
    parser.add_argument("--skip-baseline", action="store_true")
    args = parser.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"dataset {DATASET}: total rows {count('1=1')}")
    print("freezing threshold T from the training window only")
    threshold = freeze_threshold(args.target_rate)
    print(f"  T = {threshold['threshold_seconds']}s "
          f"({threshold['threshold_minutes']} min), training rate "
          f"{threshold['training_rate_at_threshold']:.4f} "
          f"against a target of {threshold['target_rate']:.2f}")

    select = ", ".join(CARRY_COLUMNS + FEATURES)
    manifest = {
        "candidate": "austin-911-response",
        "dataset": DATASET,
        "endpoint": f"{BASE}/resource/{DATASET}.json",
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "threshold": threshold,
        "features": FEATURES,
        "excluded_post_hoc": EXCLUDED_POST_HOC,
        "carry_columns": CARRY_COLUMNS,
        "label_column": "late",
        "label_rule": f"late = 1 if response_time > {threshold['threshold_seconds']} else 0",
        "splits": [],
        "limit_per_split": args.limit,
    }

    fieldnames = CARRY_COLUMNS + FEATURES + ["late"]
    retained: list[dict] = []

    for name, where in SPLITS:
        path = out / f"{name}.csv"
        rows_written = 0
        positives = 0
        nulls = 0
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in stream_rows(f"{ELIGIBLE} AND {where}", select,
                                   args.page_size, args.limit):
                response_time = row.get("response_time")
                if response_time in (None, ""):
                    nulls += 1
                    continue
                label = 1 if float(response_time) > threshold["threshold_seconds"] else 0
                record = {column: row.get(column, "") for column in CARRY_COLUMNS + FEATURES}
                record["late"] = label
                writer.writerow(record)
                rows_written += 1
                positives += label
                if name == "train" and not args.skip_baseline:
                    kept = dict(record)
                    kept["_label"] = label
                    retained.append(kept)
        entry = {
            "name": name,
            "where": where,
            "file": path.name,
            "rows": rows_written,
            "positives": positives,
            "positive_rate": round(positives / rows_written, 6) if rows_written else None,
            "skipped_null_response_time": nulls,
            "sha256": sha256_of(path),
            "bytes": path.stat().st_size,
        }
        manifest["splits"].append(entry)
        print(f"  {name:<8} rows={rows_written:>8} positives={positives:>7} "
              f"rate={entry['positive_rate']} sha256={entry['sha256'][:16]}...")

        # Baseline is computed after the train and eval files are written.
        if name == "eval" and not args.skip_baseline and retained:
            with (out / "eval.csv").open(encoding="utf-8") as handle:
                eval_rows = []
                for row in csv.DictReader(handle):
                    row["_label"] = int(row["late"])
                    eval_rows.append(row)
            manifest["baseline"] = category_rate_baseline(retained, eval_rows)
            print(f"  baseline AUC on eval: {manifest['baseline']['auc']} "
                  f"(majority-class accuracy "
                  f"{manifest['baseline']['majority_class_accuracy']})")

    summary = {
        "candidate": "austin-911-response",
        "status": "extract-built",
        "threshold_seconds": threshold["threshold_seconds"],
        "splits": {entry["name"]: {"rows": entry["rows"],
                                  "positives": entry["positives"],
                                  "positive_rate": entry["positive_rate"]}
                   for entry in manifest["splits"]},
        "baseline_auc_eval": (manifest.get("baseline") or {}).get("auc"),
        "features": FEATURES,
        "note": "Measured extract. Not a scored result; no model comparison yet.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(f"\nwrote {out}/manifest.json and {out}/summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
