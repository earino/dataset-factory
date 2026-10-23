#!/usr/bin/env python3
"""Probe 4: duplicate resolution rule, decided by cross-check against totals.

For key hosts (DEU, AUS, USA, CHE, GBR, FRA) and years 2000-2024, compute the
G/P (Government, Persons) annual total under three duplicate rules and print
them side by side so they can be compared against the publisher's own
published host-level totals (UNHCR Global Trends / Statistical Yearbook,
BAMF, etc.). Also: ratio distribution between conflicting duplicate values,
and how many eligible corridor-years are affected by conflicts at all.

Data source: see probe_hdx_asylum.py header.
Usage: python3 probe_hdx_asylum_rule.py [--csv path]
"""
import argparse
import csv
import os
from collections import defaultdict

DEFAULT_CSV = "/opt/data/cache/scratch/hdx/asylum_applications_residing_world.csv"


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=DEFAULT_CSV)
    args = ap.parse_args()
    rows = load(args.csv)

    gp = [r for r in rows
          if r["Procedure Type"] == "G" and r["Application Data Type"] == "P"]
    cells = defaultdict(list)
    for r in gp:
        cy = (int(r["Year"]), r["Country of Origin Code"], r["Country of Asylum Code"])
        cells[cy].append(int(float(r["Number of Applications"])))

    n_conf = sum(1 for v in cells.values() if len(v) > 1)
    multi = [v for v in cells.values() if len(v) > 1]
    ratios = sorted(max(v) / min(v) for v in multi if min(v) > 0)
    print(f"G/P cells: {len(cells)}; with duplicate rows: {n_conf} "
          f"({n_conf/len(cells):.1%})")
    if ratios:
        mid = len(ratios) // 2
        print(f"dup ratio max/min: min={ratios[0]:.3f} median={ratios[mid]:.3f} "
              f"p90={ratios[int(0.9*len(ratios))]:.3f} max={ratios[-1]:.1f}")
        near = sum(1 for x in ratios if x <= 1.1)
        print(f"ratios <=1.1: {near} ({near/len(ratios):.1%}); "
              f">1.5: {sum(1 for x in ratios if x > 1.5)}")

    # host-level totals under three rules
    def host_total(host, year, rule):
        tot = 0
        for (y, o, a), v in cells.items():
            if a == host and y == year:
                if rule == "sum-all":
                    tot += sum(v)
                elif rule == "max":
                    tot += max(v)
                elif rule == "min":
                    tot += min(v)
        return tot

    hosts_years = [("DEU", 2000), ("DEU", 2015), ("DEU", 2016), ("DEU", 2022),
                   ("AUS", 2000), ("USA", 2000), ("USA", 2022), ("CHE", 2015),
                   ("GBR", 2016), ("FRA", 2019), ("SWE", 2015), ("DEU", 2010)]
    print("\nhost-year G/P totals by duplicate rule (compare with publisher totals):")
    for h, y in hosts_years:
        s = host_total(h, y, "sum-all")
        mx = host_total(h, y, "max")
        mn = host_total(h, y, "min")
        print(f"  {h} {y}: sum-all={s:,} max={mx:,} min={mn:,} (conflicts "
              f"affect {sum(1 for (yy,o,a),v in cells.items() if a==h and yy==y and len(v)>1)} origins)")

    # affected share of ELIGIBLE corridor-years (>=500 apps), max rule
    affected = 0
    eligible = 0
    for (y, o, a), v in cells.items():
        vv = max(v)
        if vv >= 500:
            eligible += 1
            if len(v) > 1:
                affected += 1
    print(f"\neligible cells (>=500, max rule): {eligible}; affected by duplicates: "
          f"{affected} ({affected/eligible:.1%})")


if __name__ == "__main__":
    main()
