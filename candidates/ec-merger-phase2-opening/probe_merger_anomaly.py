#!/usr/bin/env python3
"""Identify the single case whose Phase II opener predates its notification,
plus label-union stats and eligibility-relevant counts.
Read-only. Usage: python3 probe_merger_anomaly.py <case-data-M.json>"""
import json, sys, collections

d = json.load(open(sys.argv[1]))

def first(m, k):
    v = m.get(k, [])
    return v[0] if v else None

def dec_list(c):
    out = []
    for dec in c.get("decisions", []):
        md = dec.get("metadata", {})
        types = set()
        for raw in md.get("decisionTypes", []):
            try: types.add(json.loads(raw).get("label", ""))
            except Exception: types.add(raw)
        out.append((first(md, "decisionAdoptionDate"), types))
    return out

p2, rem, both = set(), set(), set()
notified_merger = set()
for cid, c in d.items():
    m = c["metadata"]
    if first(m, "caseType") and "MergerCaseType1" not in (first(m, "caseType") or ""):
        continue
    nd = first(m, "caseNotificationDate")
    if not nd: continue
    notified_merger.add(cid)
    types = set().union(*[t for _, t in dec_list(c)])
    if "Art. 6(1)(c)" in types: p2.add(cid)
    if "Art. 6(1)(b) with conditions & obligations" in types: rem.add(cid)
print("notified Merger-caseType cases:", len(notified_merger))
print("phaseII:", len(p2), "| phase1-remedies:", len(rem), "| union any-intervention:", len(p2 | rem),
      f"({100.0*len(p2|rem)/len(notified_merger):.2f}%)")

for cid, c in d.items():
    m = c["metadata"]
    nd = first(m, "caseNotificationDate")
    if not nd: continue
    for dt, t in dec_list(c):
        if "Art. 6(1)(c)" in t and dt and dt < nd:
            print("\nanomaly case:", cid, first(m, "caseTitle"), "notif", nd, "opener", dt,
                  "caseLinks", first(m, "caseLinks"), "renotif", first(m, "caseRenotificationDate"))
