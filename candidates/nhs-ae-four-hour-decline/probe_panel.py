#!/usr/bin/env python3
"""Probe: NHS England A&E panel - base rates, split windows, clustered counts."""
import csv
import os
import re
from collections import defaultdict
from datetime import datetime

OUT = "/opt/data/cache/scratch/ae_csvs"

MONTHS = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"])}


def period_to_date(period):
    # e.g. MSitAE-SEPTEMBER-2026 or MSitAE-Feb-19
    m = re.search(r"([A-Za-z]+)-(\d{4})$", period.strip())
    if m:
        name, year = m.group(1).lower(), int(m.group(2))
        if name.lower() in MONTHS:
            return (year, MONTHS[name.lower()])
    return None


rows = []
n_files = 0
for fn in sorted(os.listdir(OUT)):
    if not fn.endswith(".csv"):
        continue
    with open(os.path.join(OUT, fn), newline="", encoding="utf-8", errors="replace") as f:
        r = csv.DictReader(f)
        cols = [c.strip() for c in r.fieldnames]
        remap = {c: c.strip() for c in r.fieldnames}
        for d in r:
            d = {remap[k]: v for k, v in d.items() if k in remap}
            rows.append(d)
    n_files += 1

panel = {}  # (org, y, m) -> dict
n_bad_period = 0
for d in rows:
    p = period_to_date(d.get("Period", ""))
    if not p:
        n_bad_period += 1
        continue
    org = d.get("Org Code", "").strip()
    if not org:
        continue
    def num(col):
        try:
            return float(d.get(col, "") or 0)
        except ValueError:
            return 0.0
    att1 = num("A&E attendances Type 1")
    over1 = num("Attendances over 4hrs Type 1")
    key = (org, p[0], p[1])
    if key in panel:  # revised files: keep max attendances copy
        if att1 >= panel[key]["att1"]:
            panel[key] = {"att1": att1, "over1": over1,
                          "name": d.get("Org name", "").strip()}
    else:
        panel[key] = {"att1": att1, "over1": over1, "name": d.get("Org name", "").strip()}

print(f"files={n_files} rows={len(rows)} bad_period={n_bad_period} panel={len(panel)}")

months = sorted({(k[1], k[2]) for k in panel})
print("month coverage:", months[0], "->", months[-1], f"({len(months)} months)")

# providers with meaningful type-1 volume
prov_months = defaultdict(list)
for (org, y, m), v in panel.items():
    if v["att1"] >= 100:
        prov_months[org].append((y, m, v["att1"], v["over1"]))

big = {o: lst for o, lst in prov_months.items() if len(lst) >= 24}
print(f"providers att1>=100 in >=24 months: {len(big)}; "
      f"provider-months: {sum(len(l) for l in big.values())}")

# national type-1 within-4h by year (cross-check candidate)
for y in range(2018, 2027):
    att = sum(v[2] for lst in big.values() for v in lst if v[0] == y)
    over = sum(v[3] for lst in big.values() for v in lst if v[0] == y)
    if att:
        print(f"national {y}: within4h type1 = {100*(att-over)/att:.1f}%  (att={att:,.0f})")

# label options per provider-month with next month present
def rate(v):
    return (v[2] - v[3]) / v[2]

def next_month(m):
    return (m[0] + 1, 1) if m[1] == 12 else (m[0], m[1] + 1)

WINDOWS = {"train": (2019, 1, 2022, 12), "eval": (2023, 1, 2024, 12),
           "holdout": (2025, 1, 2026, 9)}

for label_name, fn in [
    ("below95", lambda r: r < 0.95),
    ("below80", lambda r: r < 0.80),
    ("below74", lambda r: r < 0.74),
    ("mm_decline", lambda r, prev: r < prev),
]:
    stats = {w: [0, 0, set()] for w in WINDOWS}  # pos, neg, distinct providers pos
    for org, lst in big.items():
        lst.sort()
        for i in range(len(lst) - 1):
            y, m, att, over = lst[i]
            ny, nm, natt, nover = lst[i + 1]
            if (ny, nm) != next_month((y, m)):
                continue
            w = None
            for wn, (y0, m0, y1, m1) in WINDOWS.items():
                if y0 <= ny <= y1 and (ny > y0 or nm >= m0) and (ny < y1 or nm <= m1):
                    w = wn
            if w is None:
                continue
            r_next = rate((ny, nm, natt, nover))
            if label_name == "mm_decline":
                pos = fn(r_next, rate((y, m, att, over)))
            else:
                pos = fn(r_next)
            if pos:
                stats[w][0] += 1
                stats[w][2].add(org)
            else:
                stats[w][1] += 1
    print(f"label {label_name}:")
    for w, (p, n, orgs) in stats.items():
        tot = p + n
        print(f"  {w:8s} pos={p:6d} neg={n:6d} rate={p/tot*100:5.1f}% "
              f"distinct-prov-pos={len(orgs)}")
