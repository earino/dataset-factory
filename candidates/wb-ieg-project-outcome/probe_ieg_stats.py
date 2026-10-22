#!/usr/bin/env python3
"""Probe the World Bank IEG World Bank Project Performance Ratings dataset.

Reads the CSV already fetched anonymously from
  https://datacatalogapi.worldbank.org/dexapps/fone/api/apiservice?datasetId=DS00053&resourceId=RS00055&top=20000&type=csv
(one request, 12,629 data rows, 3,340,648 bytes, measured 2026-10-22) and measures:
row/uniqueness, label distribution, split capacity by approval FY window,
approval->evaluation lag, categorical mixes, FCS-column vintage behaviour, missingness.

Stdlib only. Prints a compact summary; keeps no bulk data.
"""
import csv
import json
import sys
from collections import Counter, defaultdict

PATH = sys.argv[1] if len(sys.argv) > 1 else "ieg_test.csv"

POSITIVE = {"Highly Satisfactory", "Satisfactory", "Moderately Satisfactory"}

rows = list(csv.DictReader(open(PATH, newline="", encoding="utf-8")))
print(f"rows: {len(rows)}")
ids = [r["project_id"] for r in rows]
print(f"distinct project_id: {len(set(ids))}  duplicated_ids: {len(ids)-len(set(ids))}")

# label distribution
oc = Counter(r["outcome"] for r in rows)
print("outcome mix:", json.dumps(dict(oc.most_common())))
rated = [r for r in rows if r["outcome"] and r["outcome"] != "Not Rated"]
pos = sum(1 for r in rated if r["outcome"] in POSITIVE)
print(f"rated rows: {len(rated)}  MS+ share: {pos/len(rated):.4f}")

# evaluation type mix (two streams: ICRR validation vs PPAR full evaluation, latest kept)
et = Counter(r["evaluation_type"] for r in rows)
print("evaluation_type mix:", json.dumps(dict(et.most_common())))

# approval FY distribution and per-window class balance
def fy(r, key):
    try:
        return int(r[key])
    except (TypeError, ValueError):
        return None

af = Counter(fy(r, "approval_fy") for r in rows)
years = sorted(y for y in af if y is not None)
print(f"approval_fy range: {years[0]}..{years[-1]}  null: {len(rows)-len(years)}")
WINDOWS = [(1960, 1995), (1996, 2005), (2006, 2012), (2013, 2016), (2017, 2030)]
print("approval_fy window | n | MS+ rate | distinct countries")
rows_afy = [(r, fy(r, "approval_fy")) for r in rows]
for lo, hi in WINDOWS:
    w = [r for r, a in rows_afy if a is not None and lo <= a <= hi]
    p = sum(1 for r in w if r["outcome"] in POSITIVE)
    print(f"  {lo}-{hi}: n={len(w)} msplus={p/len(w):.4f} countries={len(set(r['country'] for r in w))}")

# approval -> evaluation lag (when does the label arrive?)
lags = Counter()
for r in rows:
    a, e = fy(r, "approval_fy"), fy(r, "evaluation_fy")
    if a and e:
        lags[e - a] += 1
ks = sorted(lags)
if ks:
    n = sum(lags.values())
    cum = 0
    med = None
    for k in ks:
        cum += lags[k]
        if med is None and cum >= n // 2:
            med = k
    print(f"approval->evaluation lag: min={ks[0]} median={med} max={ks[-1]} n={n}")
# labels available for which recent approval years?
recent = Counter(a for r, a in rows_afy if a is not None and a >= 2013)
print("rated rows by approval_fy 2013+:", json.dumps(dict(sorted(recent.items()))))

# FCS / lending-group column vintage: does any country carry >1 distinct status across rows?
fcs = defaultdict(set)
lg = defaultdict(set)
for r in rows:
    if r["country"]:
        fcs[r["country"]].add(r["country_fcs_status"])
        lg[r["country"]].add(r["country_lending_group"])
multi_fcs = sum(1 for v in fcs.values() if len(v) > 1)
multi_lg = sum(1 for v in lg.values() if len(v) > 1)
print(f"countries with >1 distinct fcs_status across rows: {multi_fcs}/{len(fcs)}; "
      f">1 lending_group: {multi_lg}/{len(lg)}")

# country column semantics: is it always a country?
region_names = {"Africa", "Europe", "Latin America", "Middle East", "Asia"}
cvals = Counter(r["country"] for r in rows)
print(f"distinct country values: {len(cvals)}; top: {json.dumps(dict(cvals.most_common(5)))}")
print(f"rows with region-like country value: {sum(v for k, v in cvals.items() if k in region_names)}")

# mixes of approval-time categoricals + missingness
for col in ("agreement_type", "lending_instrument_type", "global_practice", "practice_group", "wb_region"):
    cc = Counter(r[col] for r in rows)
    print(f"{col}: {len(cc)} levels; top: {json.dumps(dict(cc.most_common(4)))}")
for col in ("final_closing_fy", "global_practice", "country_lending_group", "country_fcs_status"):
    miss = sum(1 for r in rows if not r[col].strip())
    print(f"missing {col}: {miss} ({miss/len(rows):.3%})")

# clustered positives: country-year clusters (both classes must carry)
cy = defaultdict(list)
for r in rows:
    a = fy(r, "approval_fy")
    if a and r["outcome"]:
        cy[(r["country"], a)].append(r["outcome"] in POSITIVE)
cl_pos = sum(1 for v in cy.values() if any(v))
cl_all = len(cy)
print(f"country-approvalFY clusters: {cl_all}, with >=1 MS+ positive: {cl_pos}")
