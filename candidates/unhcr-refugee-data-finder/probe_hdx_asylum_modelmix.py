#!/usr/bin/env python3
"""Probe 6: reporting-model mixture among eligible corridor-years.

Eligibility for the task is G-procedure persons total >= MIN in year D.
Two reporting models exist inside the G/P stream:
  - 'split'  : corridor-year reported via disjoint type codes (N/R/A/J/...)
  - 'V'       : corridor-year reported only as unsplit 'Various' rows
Duplicates inside V cells are (per BAMF cross-check 2000/2010/2015/2016)
disjoint components (e.g. first vs follow-up), summed to the total.
This probe counts the model mix among ELIGIBLE corridor-years, per split
window, so the task definition can record the mixture (skill: provenance mix
must be counted before deciding what a row means).

Data source: see probe_hdx_asylum.py header.
Usage: python3 probe_hdx_asylum_modelmix.py [--csv path] [--min 500]
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
    cells = defaultdict(list)
    for r in gp:
        cy = (int(r["Year"]), r["Country of Origin Code"], r["Country of Asylum Code"])
        cells[cy].append(r["Application Type Code"])

    host_years = defaultdict(set)
    for (y, o, a), _ in cells.items():
        host_years[a].add(y)

    # rebuild values with sum-all
    vals = defaultdict(int)
    for r in gp:
        cy = (int(r["Year"]), r["Country of Origin Code"], r["Country of Asylum Code"])
        vals[cy] += int(float(r["Number of Applications"]))

    splits = {
        "train (label-year<=2016)": lambda y: y + 1 <= 2016,
        "eval (2017-2021)": lambda y: 2017 <= y + 1 <= 2021,
        "holdout (>=2022)": lambda y: y + 1 >= 2022,
    }
    years = sorted({k[0] for k in vals})
    for name, infn in splits.items():
        mix = Counter()
        hosts_v = set()
        hosts_split = set()
        elig = 0
        for y in years:
            if not infn(y):
                continue
            for (yy, o, a), v in vals.items():
                if yy != y or v < args.min:
                    continue
                if (y + 1) not in host_years[a]:
                    continue  # censored: host reports nothing in D+1
                elig += 1
                types = set(cells[(yy, o, a)])
                if types == {"V"}:
                    mix["V-model"] += 1
                    hosts_v.add(a)
                else:
                    mix["split-model"] += 1
                    hosts_split.add(a)
        print(f"{name}: eligible={elig} mix={dict(mix)} "
              f"V-hosts={len(hosts_v)} split-hosts={len(hosts_split)}")

    # which hosts are V-model heavy among eligible rows, all years
    hv = Counter()
    hs = Counter()
    for (y, o, a), v in vals.items():
        if v < args.min:
            continue
        types = set(cells[(y, o, a)])
        if types == {"V"}:
            hv[a] += 1
        else:
            hs[a] += 1
    print("\ntop-15 V-model hosts among eligible corridor-years:")
    for h, n in hv.most_common(15):
        print(f"  {h}: {n} V-cells vs {hs.get(h,0)} split-cells")
    both = [h for h in hv if h in hs]
    print(f"hosts appearing in BOTH models among eligible cells: {len(both)}")


if __name__ == "__main__":
    main()
