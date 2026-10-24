#!/usr/bin/env python3
"""Probe DG COMP merger open data (case-data-M.json): schema and aggregate counts.

Discovery probe for candidate ec-merger-phase2-referral. Read-only; prints
bounded summaries. Usage: python3 probe_merger_schema.py <case-data-M.json>"""
import json, sys, collections, re

path = sys.argv[1]
d = json.load(open(path))
cases = list(d.values())
print("n_cases:", len(cases))

# --- schema: union of top-level keys and their types
keycount = collections.Counter()
for c in cases:
    for k in c: keycount[k] += 1
print("\ntop-level keys (count of cases having them):")
for k, v in keycount.most_common(40):
    print(f"  {k}: {v}")

# --- one example case, truncated
ex = d.get("M.12345") or cases[0]
print("\nexample case keys:", list(ex.keys()))
def show(o, indent=0, maxitems=6):
    if isinstance(o, dict):
        for k, v in list(o.items())[:maxitems]:
            print("  "*indent + f"{k}: {type(v).__name__}")
            if isinstance(v, (dict, list)) and indent < 3:
                show(v, indent+1, maxitems)
    elif isinstance(o, list) and o:
        print("  "*indent + f"[0] ({len(o)} items):")
        show(o[0], indent+1, maxitems)
print("\nexample structure (M.12345):")
show(ex)
