#!/usr/bin/env python3
"""Probe: national monthly type-1 within-4h series + Dec-2021 Omicron fixture numbers."""
import csv
import os
import re
from collections import defaultdict

OUT = "/opt/data/cache/scratch/ae_csvs"
MONTHS = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"])}

def period_to_date(period):
    m = re.search(r"([A-Za-z]+)-(\d{4})$", period.strip())
    if m and m.group(1).lower() in MONTHS:
        return (int(m.group(2)), MONTHS[m.group(1).lower()])
    return None

nat = defaultdict(lambda: [0.0, 0.0])
for fn in os.listdir(OUT):
    if not fn.endswith(".csv"):
        continue
    with open(os.path.join(OUT, fn), newline="", encoding="utf-8", errors="replace") as f:
        r = csv.DictReader(f)
        remap = {c: c.strip() for c in r.fieldnames}
        for d in r:
            d = {remap[k]: v for k, v in d.items() if k in remap}
            p = period_to_date(d.get("Period", ""))
            if not p:
                continue
            try:
                att1 = float(d.get("A&E attendances Type 1", "") or 0)
                over1 = float(d.get("Attendances over 4hrs Type 1", "") or 0)
            except ValueError:
                continue
            nat[p][0] += att1
            nat[p][1] += over1

months = sorted(nat)
print("national type-1 within-4h by month:")
prev = None
for y, m in months:
    att, over = nat[(y, m)]
    rate = (att - over) / att * 100 if att else float("nan")
    # NOTE: summing across duplicate revised files can double-count; this is a
    # quick fixture check only - the panel script dedupes properly.
    if (y, m) in [(2021, 10), (2021, 11), (2021, 12), (2022, 1)] or (y >= 2025 and m == 9) or (y, m) == (2026, 8):
        print(f"  {y}-{m:02d}: {rate:.1f}%")
