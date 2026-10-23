#!/usr/bin/env python3
"""Probe 3: duplicate-key structure and honest clustered counts.

Questions:
  1. What distinguishes duplicate rows with the same dimension key but
     different counts? (full-row dump for a few keys; duplicates by year)
  2. Does Application Type 'V' (Various) coexist with N/R/A rows in the same
     corridor-year, and if so does V ~= sum of the others (V is an unsplit
     total that must NOT be summed in) or is it an additive category?
  3. Distinct (origin, label-year) positive clusters for candidate splits,
     x2 label on the G/P stream with the V-handling rule decided above.

Data source: see probe_hdx_asylum.py header.
Usage: python3 probe_hdx_asylum_dupes.py [--csv path] [--min 500]
"""
import argparse
import csv
import os
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
    MIN = args.min
    rows = load(args.csv)

    keycols = ["Year", "Country of Origin Code", "Country of Asylum Code",
               "Procedure Type", "Application Type Code", "Application Data Type"]

    # 1. full-row dump of a few conflicting keys
    groups = defaultdict(list)
    for r in rows:
        groups[tuple(r[c] for c in keycols)].append(r)
    shown = 0
    for k, g in groups.items():
        counts = {x["Number of Applications"] for x in g}
        if len(g) > 1 and len(counts) > 1 and shown < 3:
            print("CONFLICT KEY:", k)
            for x in g:
                print("   ", {c: x[c] for c in x})
            shown += 1
    dup_by_year = Counter()
    for k, g in groups.items():
        if len(g) > 1:
            dup_by_year[k[0]] += 1
    print("conflicting groups by year:", dict(sorted(dup_by_year.items())))

    # 2. V coexistence in G/P corridor-years
    gp = [r for r in rows if r["Procedure Type"] == "G" and r["Application Data Type"] == "P"]
    cy_types = defaultdict(lambda: defaultdict(int))
    for r in gp:
        cy = (int(r["Year"]), r["Country of Origin Code"], r["Country of Asylum Code"])
        cy_types[cy][r["Application Type Code"]] += int(float(r["Number of Applications"]))
    both = [cy for cy, t in cy_types.items() if "V" in t and len(t) > 1]
    print(f"corridor-years with V plus other types: {len(both)} of {len(cy_types)}")
    agree = 0
    examples = []
    for cy in both[:100000]:
        t = cy_types[cy]
        others = sum(v for k, v in t.items() if k != "V")
        if abs(t["V"] - others) <= max(2, 0.02 * max(t["V"], others)):
            agree += 1
        elif len(examples) < 8:
            examples.append((cy, dict(t)))
    print(f"V ~= sum(others) within 2%: {agree}/{len(both)}")
    for cy, t in examples:
        print("  disagree:", cy, t)

    # 3. panel under two aggregation rules
    def build(rule):
        p = defaultdict(int)
        for r in gp:
            cy = (int(r["Year"]), r["Country of Origin Code"], r["Country of Asylum Code"])
            t = r["Application Type Code"]
            if rule == "V-exclusive" and t == "V" and len(cy_types[cy]) > 1:
                continue
            p[cy] += int(float(r["Number of Applications"]))
        return p

    for rule in ("sum-all", "V-exclusive"):
        panel = build(rule)
        years = sorted({k[0] for k in panel})
        host_years = defaultdict(set)
        for (y, o, a) in panel:
            host_years[a].add(y)
        splits = {
            "train": [y for y in years if y + 1 <= 2016],
            "eval": [y for y in years if 2017 <= y + 1 <= 2021],
            "holdout": [y for y in years if y + 1 >= 2022],
        }
        print(f"\nrule={rule}:")
        for name, ys in splits.items():
            n = pos = clusters = 0
            oy = set()
            for y in ys:
                corridors = {(o, a): v for (yy, o, a), v in panel.items() if yy == y and v >= MIN}
                for (o, a), v in corridors.items():
                    if (y + 1) not in host_years[a]:
                        continue
                    n += 1
                    if panel.get((y + 1, o, a), 0) >= 2 * v:
                        pos += 1
                        oy.add((o, y))
            print(f"  {name}: n={n} x2_pos={pos} distinct_(origin,labelyear)_clusters={len(oy)}")

    # 4. grand-total check under both rules vs UNHCR published totals flavour
    for rule in ("sum-all", "V-exclusive"):
        panel = build(rule)
        tot = defaultdict(int)
        for (y, o, a), v in panel.items():
            tot[y] += v
        s = ", ".join(f"{y}:{tot[y]:,}" for y in (2020, 2021, 2022, 2023, 2024, 2025))
        print(f"rule={rule} G/P annual totals -> {s}")


if __name__ == "__main__":
    main()
