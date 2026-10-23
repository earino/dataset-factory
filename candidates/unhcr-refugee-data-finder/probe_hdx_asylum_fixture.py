#!/usr/bin/env python3
"""Probe 7: known-event fixture rows (verified 2026-10-23).

Fixtures the record carries, all on the sum-all G/P corridor-year panel:
  1. SYR->DEU 2014->2015: 41,100 -> 162,510  x2 label TRUE  (2015 Syrian surge into Germany)
  2. AFG->USA 2021->2022: 533 -> 25,082      x2 label TRUE  (post-Aug-2021 Taliban takeover,
                                                           Afghan asylum filings in the US)
  3. AFG->DEU 2021->2022: 37,245 -> 48,602   x2 label FALSE (large growth, sub-doubling)
  4. UKR->POL 2021->2022: 458 -> 1,593       below eligibility (458 < 500): Ukrainians in the
                                                           EU mostly registered temporary
                                                           protection, not asylum applications -
                                                           the task measures application surges.

Data source: see probe_hdx_asylum.py header.
Usage: python3 probe_hdx_asylum_fixture.py [--csv path]
"""
import argparse
import csv
from collections import defaultdict

DEFAULT_CSV = "/opt/data/cache/scratch/hdx/asylum_applications_residing_world.csv"

FIXTURES = [
    # (origin, host, yearD, expected label, expected valueD, expected valueD1)
    ("SYR", "DEU", 2014, True, 41100, 162510),
    ("AFG", "USA", 2021, True, 533, 25082),
    ("AFG", "DEU", 2021, False, 37245, 48602),
]
ELIGIBILITY = 500


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=DEFAULT_CSV)
    args = ap.parse_args()
    with open(args.csv, newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f)
                if r["Procedure Type"] == "G" and r["Application Data Type"] == "P"]
    vals = defaultdict(int)
    for r in rows:
        cy = (int(r["Year"]), r["Country of Origin Code"], r["Country of Asylum Code"])
        vals[cy] += int(float(r["Number of Applications"]))

    failures = 0
    for o, a, y, want_label, want_v0, want_v1 in FIXTURES:
        v0 = vals.get((y, o, a), 0)
        v1 = vals.get((y + 1, o, a), 0)
        got_label = v1 >= 2 * v0 if v0 >= ELIGIBILITY else "below-eligibility"
        ok = (v0 == want_v0 and v1 == want_v1 and got_label == want_label)
        failures += not ok
        print(f"{o}->{a} {y}->{y+1}: {v0:,} -> {v1:,} | label={got_label} "
              f"expected={want_label} | {'OK' if ok else 'MISMATCH'}")

    v0, v1 = vals.get((2021, "UKR", "POL"), 0), vals.get((2022, "UKR", "POL"), 0)
    print(f"UKR->POL 2021->2022: {v0:,} -> {v1:,} | eligible={v0 >= ELIGIBILITY} "
          f"(temporary-protection registrations are not in the applications stream; "
          f"a 3.5x corridor jump that the task correctly excludes at D=500 eligibility)")

    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
