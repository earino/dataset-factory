#!/usr/bin/env python3
"""Probe 5: application-type coexistence within G/P corridor-years.

The panel rule under test is sum-all-rows = 'total asylum applications'.
That is only double-counting if a corridor-year carries overlapping type
rows (e.g. N 'New' together with NR 'New and repeat', or N together with V).
Measured here: which type-code combinations coexist within a corridor-year,
how often, and how much a cleaner rule (V-wins, else N+R+A+J+others) would
differ from naive sum-all on eligible cells.

Data source: see probe_hdx_asylum.py header.
Usage: python3 probe_hdx_asylum_coexist.py [--csv path] [--min 500]
"""
import argparse
import csv
from collections import Counter, defaultdict

DEFAULT_CSV = "/opt/data/cache/scratch/hdx/asylum_applications_residing_world.csv"


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=DEFAULT_CSV)
    ap.add_argument("--min", type=int, default=500)
    args = ap.parse_args()
    rows = load(args.csv)
    gp = [r for r in rows if r["Procedure Type"] == "G" and r["Application Data Type"] == "P"]

    types = defaultdict(Counter)
    for r in gp:
        cy = (int(r["Year"]), r["Country of Origin Code"], r["Country of Asylum Code"])
        types[cy][r["Application Type Code"]] += int(float(r["Number of Applications"]))

    combos = Counter()
    for cy, t in types.items():
        combos[tuple(sorted(t))] += 1
    print("type-code combinations within G/P corridor-years (top 20):")
    for combo, n in combos.most_common(20):
        print(f"  {combo}: {n}")

    overlap_pairs = Counter()
    for cy, t in types.items():
        ks = set(t)
        for a in ("N", "V"):
            for b in ("NR", "NA", "FA", "RA", "A", "R", "J", "SP"):
                if a in ks and b in ks:
                    overlap_pairs[(a, b)] += 1
    print("overlap pairs (possible double-count if summed):", dict(overlap_pairs))

    # N and R coexist legitimately (new + repeat are disjoint). Check N+R+A sums vs V
    # for the small set of hosts that switched models over time (DEU 2000 vs 2022).
    # Difference between naive sum-all and 'sum disjoint types only' rule:
    disjoint = {"N", "R", "A", "J", "SP"}
    diff_cells = 0
    diff_elig = 0
    for cy, t in types.items():
        naive = sum(t.values())
        # rule: if V exists take V; if NR exists take NR + A + J; else sum disjoint types
        if "V" in t:
            rule = t["V"] + sum(v for k, v in t.items() if k in ("A", "J"))
        elif "NR" in t:
            rule = t["NR"] + sum(v for k, v in t.items() if k in ("A", "J"))
        else:
            rule = sum(v for k, v in t.items() if k in disjoint)
        if naive != rule:
            diff_cells += 1
            if max(naive, rule) >= args.min:
                diff_elig += 1
    print(f"cells where sum-all != V/NR-preferring rule: {diff_cells} of {len(types)} "
          f"(eligible: {diff_elig})")


if __name__ == "__main__":
    main()
