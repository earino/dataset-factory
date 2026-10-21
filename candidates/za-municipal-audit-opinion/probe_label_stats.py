#!/usr/bin/env python3
"""Measured label stats for the za-municipal-audit-opinion candidate:
binary base rates per year, persistence (last-opinion) accuracy, split windows."""
import csv
import sys
from collections import Counter, defaultdict

path = sys.argv[1] if len(sys.argv) > 1 else ".factory/audit_opinions.csv"
rows = []
with open(path, newline="", encoding="utf-8") as f:
    r = csv.reader(f)
    next(r)
    for x in r:
        rows.append({"muni": x[0], "year": int(x[2]), "code": x[3]})

# binary label: qualified or worse (qualified/disclaimer/adverse) vs clean-ish
BAD = {"qualified", "disclaimer", "adverse"}


def label(code):
    if code == "outstanding":
        return None
    return 1 if code in BAD else 0


by_muni_year = defaultdict(dict)
for row in rows:
    lab = label(row["code"])
    if lab is not None:
        by_muni_year[row["muni"]][row["year"]] = lab

years = sorted({row["year"] for row in rows})
print("label years:", years)
print("\nper-year binary 'qualified-or-worse' rate (excluding outstanding audits):")
per_year = {}
for y in years:
    labs = [by_muni_year[m][y] for m in by_muni_year if y in by_muni_year[m]]
    pos = sum(labs)
    per_year[y] = (len(labs), pos)
    print(f"   {y}: {pos}/{len(labs)} = {pos/len(labs):.2%}")

# persistence baseline: last observed opinion predicts this year's
for window_name, window in [
    ("train 2011-2017", range(2011, 2018)),
    ("eval 2018-2020", range(2018, 2021)),
    ("holdout 2021-2024", range(2021, 2025)),
]:
    labs = [by_muni_year[m][y] for m in by_muni_year for y in window if y in by_muni_year[m]]
    pos = sum(labs)
    print(f"\n{window_name}: rows={len(labs)} positives={pos} ({pos/len(labs):.2%})")

# persistence accuracy on eval years 2018-2020
correct = tot = 0
changes = Counter()
for m, d in by_muni_year.items():
    ys = sorted(d)
    for i in range(1, len(ys)):
        if 2018 <= ys[i] <= 2020:
            tot += 1
            correct += d[ys[i]] == d[ys[i - 1]]
            if d[ys[i]] != d[ys[i - 1]]:
                changes[(d[ys[i - 1]], d[ys[i]])] += 1
print(f"\npersistence accuracy 2018-2020: {correct}/{tot} = {correct/tot:.2%}")
print("opinion transitions 2018-2020 (prev->next):", dict(changes))
