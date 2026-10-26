#!/usr/bin/env python3
"""Pre-launch verification probe for the ec-merger build (coordinator scratch).

Exercises the SHIPPED build.py parsing and label rules against a fresh
register fetch WITHOUT constructing any artifact: no CSVs, no panel written,
no performance metric. Prints eligibility/label counts, split counts,
pending censoring, fixture verdicts and cross-check band results - the same
class of evidence the discovery probes (probe_merger_label.py et al.)
already recorded, used here to validate the build's assumptions before a
worker launch.

The fetched JSON is deleted by the caller after evidence extraction.

Usage: python3 probe_merger_buildcheck.py <case-data-M.json>
"""
from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "source" / "build.py"


def load_build():
    spec = importlib.util.spec_from_file_location("ec_build", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    build = load_build()
    loaded = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        print("FATAL: register top level is not a case-number-keyed object")
        return 3

    rows = []
    eligible = 0
    exclusions = Counter()
    pending_by_split = Counter()
    pending_by_year = Counter()
    pre_notif = []
    unmatched_regulation = 0
    art8_no_opener = []
    inventory = Counter()

    for number in sorted(loaded):
        case = loaded[number]
        metadata = case.get("metadata") or {}
        try:
            row = build.build_row(number, metadata)
        except build.BuildError as error:
            print(f"BUILD RULE FAILURE at {number}: {error}")
            return 4
        if row is None:
            type_label = str(build.first(metadata, "caseType") or "?")
            exclusions[type_label] += 1
            continue
        eligible += 1
        facts, all_labels = build.decision_facts(case)
        for label in sorted(all_labels):
            if label:
                inventory[label] += 1
        label, bucket, diag = build.label_of(number, facts, row["notification_date"])
        if bucket == "pending":
            split = ("train" if row["notification_year"] <= build.SPLIT_END_YEAR["train"]
                     else "eval" if row["notification_year"] <= build.SPLIT_END_YEAR["eval"]
                     else "holdout")
            pending_by_split[split] += 1
            pending_by_year[row["notification_year"]] += 1
            continue
        if diag.get("pre_notification_openers") or diag.get("openers_early_only"):
            pre_notif.append(number)
        if label == 0 and any("Art. 8(" in l for l in all_labels):
            art8_no_opener.append(number)
        row[build.TARGET] = label
        rows.append(row)

    split_stats = {}
    for split in ("train", "eval", "holdout"):
        split_rows = [r for r in rows
                      if (r["notification_year"] <= build.SPLIT_END_YEAR["train"] and split == "train")
                      or (build.SPLIT_START_YEAR["eval"] <= r["notification_year"] <= build.SPLIT_END_YEAR["eval"] and split == "eval")
                      or (r["notification_year"] >= build.SPLIT_START_YEAR["holdout"] and split == "holdout")]
        pos = sum(1 for r in split_rows if r[build.TARGET] == 1)
        dates = {r["notification_date"] for r in split_rows if r[build.TARGET] == 1}
        years = {r["notification_year"] for r in split_rows}
        pos_years = {r["notification_year"] for r in split_rows if r[build.TARGET] == 1}
        split_stats[split] = {"rows": len(split_rows), "positives": pos,
                              "distinct_positive_dates": len(dates),
                              "years": len(years),
                              "years_with_positives": len(pos_years)}

    positives = sum(1 for r in rows if r[build.TARGET] == 1)
    missing_sector = sum(1 for r in rows if r["has_sectors"] == 0)
    by_number = {r[build.ROW_ID]: r for r in rows}

    results = {
        "eligible_cases": eligible,
        "shipped_rows": len(rows),
        "phase2_positives": positives,
        "excluded": dict(sorted(exclusions.items())),
        "split_stats": split_stats,
        "pending_censored_by_split": dict(pending_by_split),
        "pending_censored_by_year": dict(sorted(pending_by_year.items())),
        "pre_notification_opener_cases": sorted(pre_notif),
        "art8_without_opener": art8_no_opener,
        "missing_sector_cases": missing_sector,
        "m3333": {k: by_number.get("M.3333", {}).get(k) for k in
                  (build.ROW_ID, build.TARGET, "notification_date", "regulation")},
        "fixture_checks": [],
        "band_checks": [],
        "decision_type_inventory": dict(sorted(inventory.items(), key=lambda kv: -kv[1])[:20]),
    }

    for fixture in build.FIXTURES:
        number = fixture["case"]
        row = by_number.get(number)
        sectors = set()
        for code, _ in build.sector_codes((loaded.get(number, {}) or {}).get("metadata") or {}):
            sectors.add(code)
        problems = []
        if row is None:
            problems.append("missing from rows")
        else:
            if row[build.TARGET] != fixture["label"]:
                problems.append(f"label={row[build.TARGET]}")
            if row["notification_date"] != fixture["notif"]:
                problems.append(f"notif={row['notification_date']}")
            if row["regulation"] != fixture["regulation"]:
                problems.append(f"regulation={row['regulation']}")
        if sectors != fixture["sectors"]:
            problems.append(f"sectors={sorted(sectors)}")
        results["fixture_checks"].append({"case": number,
                                          "ok": not problems,
                                          "problems": problems})

    for what, value, band in [
        ("eligible_cases", eligible, build.CROSS_CHECK["eligible_cases"]),
        ("pending_censored", sum(pending_by_split.values()),
         build.CROSS_CHECK["pending_censored"]),
        ("phase2_positives", positives, build.CROSS_CHECK["phase2_positives"]),
        ("missing_sector_cases", missing_sector, build.CROSS_CHECK["missing_sector_cases"]),
        ("train_positives", split_stats["train"]["positives"],
         build.CROSS_CHECK["split_positives"]["train"]),
        ("eval_positives", split_stats["eval"]["positives"],
         build.CROSS_CHECK["split_positives"]["eval"]),
        ("holdout_positives", split_stats["holdout"]["positives"],
         build.CROSS_CHECK["split_positives"]["holdout"]),
    ]:
        low, high = band
        results["band_checks"].append({"what": what, "value": value,
                                       "band": band,
                                       "ok": low <= value <= high})

    print(json.dumps(results, indent=1))
    failures = [c for c in results["band_checks"] if not c["ok"]]
    fixtures_failed = [c for c in results["fixture_checks"] if not c["ok"]]
    m3333_ok = (by_number.get("M.3333", {}).get(build.TARGET) == 1)
    if failures or fixtures_failed or sorted(pre_notif) != ["M.3333"] or not m3333_ok:
        print("PROBE VERDICT: FAIL", file=sys.stderr)
        return 5
    if split_stats["eval"]["distinct_positive_dates"] < 20 or \
       split_stats["holdout"]["distinct_positive_dates"] < 20:
        print("PROBE VERDICT: FAIL (clustered positive events below the gate minimum 20)",
              file=sys.stderr)
        return 5
    print("PROBE VERDICT: OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
