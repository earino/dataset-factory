#!/usr/bin/env python3
"""Aggregate the CQC weekly directory CSV: service-type mix (care homes) and region counts."""
import csv
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(HERE, "cqc_dl", "csv", "28_October_2026_CQC_directory.csv")

svc = Counter()
regions = Counter()
ch_by_type = Counter()
n = 0
carehome_rows = 0
with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
    r = csv.reader(f)
    for i, row in enumerate(r):
        if i < 5 or not row or not row[0]:
            continue
        n += 1
        types = row[6] or "(blank)"
        regions[row[11] or "(blank)"] += 1
        # a location may carry multiple service types separated by |
        parts = [p.strip() for p in types.split("|") if p.strip()]
        for p in parts:
            svc[p] += 1
        if any("care home" in p.lower() for p in parts):
            carehome_rows += 1
            ch_by_type[types] += 1

print(f"active locations: {n}")
print(f"locations with a 'care home' service type: {carehome_rows}")
print("\nservice types (top 30):")
for k, v in svc.most_common(30):
    print(f"  {v:6d}  {k}")
print("\ncare home type combos (top 10):")
for k, v in ch_by_type.most_common(10):
    print(f"  {v:6d}  {k}")
print("\nregions:")
for k, v in regions.most_common():
    print(f"  {v:6d}  {k}")
