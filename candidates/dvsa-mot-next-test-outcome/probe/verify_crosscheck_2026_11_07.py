#!/usr/bin/env python3
"""Deterministic cross-check for dvsa-mot-build-002 (required acceptance step).

Compares the collected build-002 summary.json per-year parse receipts for
2005-2014 against the values recorded by dvsa-mot-build-001 (its collected
container.log), EXACT equality required, and prints the new 2015-2024
non-completed inventories that the failed build could never observe.

Run AFTER the bounded diagnostics fetch:
  python3 candidates/dvsa-mot-next-test-outcome/probe/verify_crosscheck_2026_11_07.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
OLD_LOG = ROOT / ".factory" / "dvsa-mot-build-001" / "staged-file-0001-part-0000"
NEW_SUMMARY = ROOT / ".factory" / "dvsa-mot-build-002" / "staged-summary.json"

LINE_RE = re.compile(
    r"^(\d{4}): rows_seen=(\d+) class4=(\d+) sampled=(\d+) results=")


def old_receipts() -> dict:
    recorded = {}
    for line in OLD_LOG.read_text().splitlines():
        match = LINE_RE.match(line)
        if match:
            year, rows, class4, sampled = match.groups()
            recorded[year] = (int(rows), int(class4), int(sampled))
    return recorded


def main() -> int:
    recorded = old_receipts()
    print(f"build-001 container.log receipts: {len(recorded)} years "
          f"({min(recorded)}..{max(recorded)})")
    summary = json.loads(NEW_SUMMARY.read_text())
    assert summary["job"] == "dvsa-mot-build-002", "wrong job in summary.json"
    per_year = summary["population"]["per_year"]

    mismatches = []
    for year in sorted(recorded, key=int):
        rows, class4, sampled = recorded[year]
        new = per_year.get(year, {})
        got = (new.get("rows_seen"), new.get("class4_rows"),
               new.get("sampled_rows"))
        status = "EXACT" if got == (rows, class4, sampled) else "MISMATCH"
        if status == "MISMATCH":
            mismatches.append((year, (rows, class4, sampled), got))
        print(f"  {year}: recorded {rows}/{class4}/{sampled} "
              f"got {got[0]}/{got[1]}/{got[2]} -> {status}")

    print("\nnon-completed inventories per year (new evidence; build-001 "
          "died at 2015 before any of this existed):")
    for year in sorted(per_year, key=int):
        entry = per_year[year]
        print(f"  {year}: non_completed_rows={entry.get('non_completed_rows', 0)} "
              f"values={sorted(entry.get('non_completed_values', []))}")

    splits = summary["splits"]
    print("\nsplits:", json.dumps(
        {k: {kk: splits[k][kk] for kk in ("rows", "positives",
                                          "distinct_events")}
         for k in splits}, indent=1))
    print("pairs counters:", json.dumps(
        {k: v for k, v in summary["pairs"].items() if k != "gap_days"},
        indent=1))
    print("gap_days:", json.dumps(summary["pairs"].get("gap_days")))
    out = {"crosscheck_years": len(recorded), "mismatches": mismatches}
    print(json.dumps(out))
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
