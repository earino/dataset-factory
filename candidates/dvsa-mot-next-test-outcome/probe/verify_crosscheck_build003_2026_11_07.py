#!/usr/bin/env python3
"""Deterministic cross-check for dvsa-mot-build-003 (required acceptance step).

The build-003 summary.json per-year parse receipts for 2005-2014 must
reproduce build-001's collected container.log EXACTLY (10/10 years, as
build-002 already did), 2015-2016 must reproduce build-002's collected
container.log EXACTLY (the two years build-002 parsed with the ABRVE repair
before dying at the 2017 Deflate64 zip: 2015 37,490,736/35,445,915/35,591;
2016 37,693,380/35,637,088/35,626), and this script prints the 2017-2024
per-year receipts and non-completed inventories that no previous build ever
observed (the zip era).

Run AFTER the bounded diagnostics fetch:
  python3 candidates/dvsa-mot-next-test-outcome/probe/fetch_diagnostics_build003_2026_11_07.py
  python3 candidates/dvsa-mot-next-test-outcome/probe/verify_crosscheck_build003_2026_11_07.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
LOG_001 = ROOT / ".factory" / "dvsa-mot-build-001" / "staged-file-0001-part-0000"
LOG_002 = ROOT / ".factory" / "dvsa-mot-build-002" / "staged-container.log"
NEW_SUMMARY = ROOT / ".factory" / "dvsa-mot-build-003" / "staged-summary.json"

LINE_RE = re.compile(
    r"^(\d{4}): rows_seen=(\d+) class4=(\d+) sampled=(\d+) results=")


def log_receipts(path: Path) -> dict:
    recorded = {}
    for line in path.read_text().splitlines():
        match = LINE_RE.match(line)
        if match:
            year, rows, class4, sampled = match.groups()
            recorded[year] = (int(rows), int(class4), int(sampled))
    return recorded


def main() -> int:
    receipts_001 = log_receipts(LOG_001)
    receipts_002 = log_receipts(LOG_002)
    print(f"build-001 container.log receipts: {len(receipts_001)} years "
          f"({min(receipts_001)}..{max(receipts_001)})")
    print(f"build-002 container.log receipts: {len(receipts_002)} years "
          f"({min(receipts_002)}..{max(receipts_002)})")
    summary = json.loads(NEW_SUMMARY.read_text())
    assert summary["job"] == "dvsa-mot-build-003", "wrong job in summary.json"
    per_year = summary["population"]["per_year"]

    mismatches = []
    for year in sorted(set(receipts_002), key=int):
        rows, class4, sampled = receipts_002[year]
        new = per_year.get(year, {})
        got = (new.get("rows_seen"), new.get("class4_rows"),
               new.get("sampled_rows"))
        status = "EXACT" if got == (rows, class4, sampled) else "MISMATCH"
        if status == "MISMATCH":
            mismatches.append((year, (rows, class4, sampled), got))
        chain = ""
        if year in receipts_001:
            r1 = receipts_001[year]
            chain = (" (== build-001 " if r1 == (rows, class4, sampled)
                     else " (build-001 DISAGREES ")
            chain += f"{r1[0]}/{r1[1]}/{r1[2]})"
        print(f"  {year}: build-002 {rows}/{class4}/{sampled} "
              f"got {got[0]}/{got[1]}/{got[2]} -> {status}{chain}")

    print("\nzip-era (2017-2024) receipts + non-completed inventories "
          "(new evidence; no previous build parsed these years):")
    for year in sorted(per_year, key=int):
        if int(year) < 2017:
            continue
        entry = per_year[year]
        print(f"  {year}: rows_seen={entry.get('rows_seen', 0)} "
              f"class4={entry.get('class4_rows', 0)} "
              f"sampled={entry.get('sampled_rows', 0)} "
              f"non_completed_rows={entry.get('non_completed_rows', 0)} "
              f"values={sorted(entry.get('non_completed_values', []))}")

    if mismatches:
        print(f"\nCROSS-CHECK FAILED: {len(mismatches)} mismatched year(s)")
        return 1
    print("\nCROSS-CHECK PASSED: 2005-2016 receipts reproduce the recorded "
          "values EXACTLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
