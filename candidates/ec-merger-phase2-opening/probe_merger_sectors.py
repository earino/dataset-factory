#!/usr/bin/env python3
"""Feature probe: caseSectors coverage and coding eras; sector-conditional
Phase II base rates (learnability evidence); pending-case censoring count.
Read-only. Usage: python3 probe_merger_sectors.py <case-data-M.json>"""
import json, sys, collections

d = json.load(open(sys.argv[1]))

def first(m, k):
    v = m.get(k, [])
    return v[0] if v else None

def dec_types(c):
    t = set()
    for dec in c.get("decisions", []):
        for raw in dec.get("metadata", {}).get("decisionTypes", []):
            try: t.add(json.loads(raw).get("label", ""))
            except Exception: t.add(raw)
    return t

n_no_sect = 0
sect_missing_years = collections.Counter()
style_by_year = collections.Counter()
p2_by_topsect = collections.Counter()
n_by_topsect = collections.Counter()
pending = 0
n = 0
for cid, c in d.items():
    m = c["metadata"]
    if "MergerCaseType1" not in (first(m, "caseType") or ""): continue
    nd = first(m, "caseNotificationDate")
    if not nd: continue
    n += 1
    ny = nd[:4]
    types = dec_types(c)
    if "Art. 6(1)(c)" in types: is_p2 = True
    else: is_p2 = False
    if first(m, "caseInvestigationPhase"): pending += 1
    raw = m.get("caseSectors", [])
    if not raw:
        n_no_sect += 1
        sect_missing_years[ny] += 1
        continue
    for s in raw[:2]:
        try:
            obj = json.loads(s)
            code = obj.get("code", "")
            style = code.split("_")[0] if code else "?"
            style_by_year[(ny, style)] += 1
            # top-level division = first 2 chars of the code suffix
            div = code.rsplit("_", 1)[-1].split(".")[0]
            n_by_topsect[div] += 1
            if is_p2: p2_by_topsect[div] += 1
        except Exception:
            pass

print(f"eligible (notified, caseType Merger): {n}; missing caseSectors: {n_no_sect} "
      f"({100.0*n_no_sect/n:.2f}%)")
print("missing-sector cases by notification year (top 8):", sect_missing_years.most_common(8))
print("\ncode-style by year (sample of years):")
for y in ["1990", "1997", "2001", "2004", "2007", "2010", "2013", "2016", "2019", "2022", "2025"]:
    row = {st: c for (yy, st), c in style_by_year.items() if yy == y}
    print(f"  {y}: {row}")
print("\ntop-10 sector divisions by notified-case count (rate = phase2 share):")
for div, cnt in n_by_topsect.most_common(12):
    p = p2_by_topsect.get(div, 0)
    print(f"  {div}: n={cnt:5d}  p2={p:4d}  rate={100.0*p/cnt:.2f}%")
print(f"\ncases currently carrying a live investigation phase: {pending}")
print("\nM.877 caseSectors (Boeing/McDonnell Douglas, notified 1997):")
print("  ", d["M.877"]["metadata"].get("caseSectors"))
print("M.10188 caseSectors (Illumina/GRAIL, notified 2021):")
print("  ", d["M.10188"]["metadata"].get("caseSectors"))
