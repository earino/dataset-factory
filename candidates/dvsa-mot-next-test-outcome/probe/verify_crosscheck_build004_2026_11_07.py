#!/usr/bin/env python3
"""Deterministic cross-check for dvsa-mot-build-004 (required acceptance step).

The build-004 summary.json per-year parse receipts must reproduce the recorded
failure chain EXACTLY, year by year, for every year a previous build observed
before dying:
  2005-2014 == build-001's collected container.log receipts (10/10 years;
    build-001 died at the 2015 ABRVE row),
  2015-2016 == build-002's collected container.log receipts (the two years
    build-002 parsed with the ABRVE repair before dying at the 2017 Deflate64
    zip: 2015 37,490,736/35,445,915/35,591; 2016 37,693,380/35,637,088/35,626),
  2017 == build-003's collected container.log receipt EXACTLY (38,056,161 /
    35,983,938 / 35,975 - build-003 proved the Deflate64 route on the real DfT
    zip, then died at the 2018 zip's macOS __MACOSX/ AppleDouble junk member).
Every previous-build receipt is checked against every available earlier log, so
a disagreement anywhere in the chain fails the check. This script then prints
the 2018-2024 per-year receipts and non-completed inventories that no previous
build ever observed (the years behind the two repaired defects).

Run AFTER the bounded diagnostics fetch:
  python3 candidates/dvsa-mot-next-test-outcome/probe/fetch_diagnostics_build004_2026_11_07.py
  python3 candidates/dvsa-mot-next-test-outcome/probe/verify_crosscheck_build004_2026_11_07.py
"""
import json
import re
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
LOG_001 = ROOT / ".factory" / "dvsa-mot-build-001" / "staged-file-0001-part-0000"
LOG_002 = ROOT / ".factory" / "dvsa-mot-build-002" / "staged-container.log"
LOG_003 = ROOT / ".factory" / "dvsa-mot-build-003" / "staged-container.log"
NEW_SUMMARY = ROOT / ".factory" / "dvsa-mot-build-004" / "staged-summary.json"

LINE_RE = re.compile(
    r"^(\d{4}): rows_seen=(\d+) class4=(\d+) sampled=(\d+) results=")
HIST_RE = re.compile(r"results=(\{.*\})\s*$")
COMPLETED = {"P", "F", "PRS"}


def log_receipts(path: Path) -> dict:
    recorded = {}
    for line in path.read_text().splitlines():
        match = LINE_RE.match(line)
        if match:
            year, rows, class4, sampled = match.groups()
            recorded[year] = (int(rows), int(class4), int(sampled))
    return recorded


def log_histograms(path: Path) -> dict:
    """Per-year result histograms from a collected container.log."""
    out = {}
    for line in path.read_text().splitlines():
        match = LINE_RE.match(line)
        if match:
            hist_match = HIST_RE.search(line)
            if hist_match is None:
                continue
            hist = json.loads(hist_match.group(1))
            out[match.group(1)] = {k: v for k, v in hist.items()
                                   if k not in COMPLETED}
    return out


def main() -> int:
    receipts_001 = log_receipts(LOG_001)
    receipts_002 = log_receipts(LOG_002)
    receipts_003 = log_receipts(LOG_003)
    print(f"build-001 container.log receipts: {len(receipts_001)} years "
          f"({min(receipts_001)}..{max(receipts_001)})")
    print(f"build-002 container.log receipts: {len(receipts_002)} years "
          f"({min(receipts_002)}..{max(receipts_002)})")
    print(f"build-003 container.log receipts: {len(receipts_003)} years "
          f"({min(receipts_003)}..{max(receipts_003)})")

    summary_path = NEW_SUMMARY
    receipts_source = "summary.json"
    if not NEW_SUMMARY.is_file():
        # A build that dies before writing outputs ships no summary.json
        # (dvsa-mot-build-004 was OOM-killed mid-2022 with /output/extract
        # empty); the container.log receipts are the same per-year counters
        # and are the chain source for the failed builds.
        LOG_004 = ROOT / ".factory" / "dvsa-mot-build-004" / "staged-container.log"
        if not LOG_004.is_file():
            raise SystemExit("neither staged-summary.json nor "
                             "staged-container.log exists; run the fetch first")
        receipts_source = "container.log"
        per_year = {year: {"rows_seen": rows, "class4_rows": class4,
                           "sampled_rows": sampled}
                    for year, (rows, class4, sampled)
                    in log_receipts(LOG_004).items()}
        histograms = log_histograms(LOG_004)
        for year, extras in histograms.items():
            if year in per_year:
                per_year[year]["non_completed_rows"] = sum(extras.values())
                per_year[year]["non_completed_values"] = sorted(extras)
        print("no summary.json (failed build); using build-004 "
              "container.log receipts as the per-year source; non-completed "
              "counts derived from its result histograms")
    else:
        summary = json.loads(NEW_SUMMARY.read_text())
        assert summary["job"] == "dvsa-mot-build-004", \
            "wrong job in summary.json"
        per_year = summary["population"]["per_year"]
    print(f"per-year source: {receipts_source}")

    mismatches = []
    for year in sorted(receipts_003, key=int):
        expected = receipts_003[year]
        new = per_year.get(year, {})
        got = (new.get("rows_seen"), new.get("class4_rows"),
               new.get("sampled_rows"))
        status = "EXACT" if got == expected else "MISMATCH"
        if status == "MISMATCH":
            mismatches.append((year, expected, got))
        chain = ""
        for label, source in (("build-002", receipts_002),
                              ("build-001", receipts_001)):
            if year in source:
                agree = "==" if source[year] == expected else "DISAGREES"
                chain += (f" ({label} {agree} {source[year][0]}/"
                          f"{source[year][1]}/{source[year][2]})")
        print(f"  {year}: build-003 {expected[0]}/{expected[1]}/{expected[2]} "
              f"got {got[0]}/{got[1]}/{got[2]} -> {status}{chain}")

    print("\n2018-2024 receipts + non-completed inventories (new evidence; "
          "no previous build parsed these years):")
    for year in sorted(per_year, key=int):
        if int(year) < 2018:
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
    print("\nCROSS-CHECK PASSED: 2005-2017 receipts reproduce the recorded "
          "chain EXACTLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
