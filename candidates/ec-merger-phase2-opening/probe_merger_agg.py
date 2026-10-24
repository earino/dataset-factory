#!/usr/bin/env python3
"""Aggregate probe over DG COMP merger open data: decision types, case types,
per-year notifications and Phase II (Art. 8* / Art. 6(2)) base rates.

Read-only. Usage: python3 probe_merger_agg.py <case-data-M.json>"""
import json, sys, collections, re

d = json.load(open(sys.argv[1]))
cases = d.values()

dectypes = collections.Counter()
casetypes = collections.Counter()
simplified = collections.Counter()
regulation = collections.Counter()
invphase = collections.Counter()
notif_year = collections.Counter()
p2_by_year = collections.Counter()      # Art. 8* decision reached (case's first Art. 8 decision)
p2_open_by_year = collections.Counter()  # Art. 6(2) opening decision
no_decisions = 0
no_notif = 0
no_sectors = 0
n = 0

def ymd(l):
    return l[0] if l else None

for c in cases:
    n += 1
    m = c["metadata"]
    def g(k):
        v = m.get(k, [])
        return v[0] if v else None
    ny = (g("caseNotificationDate") or "")[:4]
    if not ny:
        no_notif += 1
    else:
        notif_year[ny] += 1
    secs = m.get("caseSectors", [])
    if not secs:
        no_sectors += 1
    casetypes[g("caseType") or "?"] += 1
    simplified[g("caseSimplified") or "(none)"] += 1
    regulation[g("caseRegulation") or "?"] += 1
    invphase[g("caseInvestigationPhase") or "(none)"] += 1
    decs = c.get("decisions", [])
    if not decs:
        no_decisions += 1
    types_seen = set()
    art8 = False
    art62 = False
    for dec in decs:
        for dt in dec.get("metadata", {}).get("decisionTypes", []):
            lab = dt
            dectypes[dt] += 1
            types_seen.add(dt)
            if dt.startswith("Art. 8"):
                art8 = True
            if dt.startswith("Art. 6(2)"):
                art62 = True
    if art8: p2_by_year[ny] += 1
    if art62: p2_open_by_year[ny] += 1

print(f"n_cases {n}, no_notification_date {no_notif}, no_decisions {no_decisions}, no_sectors {no_sectors}")
print("\ndecision type labels (count across all decisions):")
for k, v in dectypes.most_common(60): print(f"  {v:7d}  {k}")
print("\ncase types:")
for k, v in casetypes.most_common(20): print(f"  {v:7d}  {k}")
print("\nsimplified track:")
for k, v in simplified.most_common(20): print(f"  {v:7d}  {k}")
print("\nregulation:")
for k, v in regulation.most_common(10): print(f"  {v:7d}  {k}")
print("\ninvestigation phase:")
for k, v in invphase.most_common(10): print(f"  {v:7d}  {k}")
print("\nyear: notifications | Art8-reached | Art6(2)-opened")
for y in sorted(set(list(notif_year) + list(p2_by_year) + list(p2_open_by_year))):
    print(f"  {y}: {notif_year[y]:6d} | {p2_by_year[y]:4d} | {p2_open_by_year[y]:4d}")
