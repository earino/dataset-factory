#!/usr/bin/env python3
"""Fixture + anomaly probe over DG COMP merger open data.

Fixtures (externally verified facts, sources in candidate notes):
  M.877   Boeing/McDonnell Douglas: notif 1997-02-18, Art. 8(2) w/ conditions 1997-07-30 (Reg 4064/89)
  M.10188 Illumina/GRAIL: Art. 8(3) prohibition 2022-09-06 (Reg 139/2004)
  M.4731  Google/DoubleClick: cleared 2008-03-11 (press IP/08/458) - check what register says
Anomalies:
  - cases with no notification date: count, decision-type mix
  - cases with notification but a decision dated BEFORE notification
Read-only. Usage: python3 probe_merger_fixtures.py <case-data-M.json>"""
import json, sys, collections

d = json.load(open(sys.argv[1]))

def first(m, k):
    v = m.get(k, [])
    return v[0] if v else None

def dec_lines(c):
    out = []
    for dec in c.get("decisions", []):
        md = dec.get("metadata", {})
        types = []
        for raw in md.get("decisionTypes", []):
            try: types.append(json.loads(raw).get("label", ""))
            except Exception: types.append(raw)
        out.append((first(md, "decisionAdoptionDate"), types))
    return out

print("fixture records:")
for cid in ["M.877", "M.10188", "M.4731"]:
    c = d.get(cid)
    if not c:
        print(f"  {cid}: NOT PRESENT"); continue
    m = c["metadata"]
    print(f"  {cid}: title={first(m,'caseTitle')!r}")
    print(f"     notif={first(m,'caseNotificationDate')} initiation={first(m,'caseInitiationDate')} "
          f"reg={first(m,'caseRegulation')} simplified={first(m,'caseSimplified')}")
    for dt, types in dec_lines(c):
        print(f"     decision {dt}: {types}")

no_notif_types = collections.Counter()
no_notif = 0
pre_dec = []
for cid, c in d.items():
    m = c["metadata"]
    nd = first(m, "caseNotificationDate")
    dates = [dt for dt, _ in dec_lines(c) if dt]
    if not nd:
        no_notif += 1
        for _, types in dec_lines(c):
            for t in types: no_notif_types[t] += 1
    else:
        early = [dt for dt in dates if dt < nd]
        if early:
            pre_dec.append((cid, nd, sorted(set(early))[:3]))
print(f"\ncases with no notification date: {no_notif}")
print("their decision-type mix (top 12):")
for k, v in no_notif_types.most_common(12): print(f"  {v:5d}  {k}")
print(f"\ncases with notification but decision(s) dated BEFORE it: {len(pre_dec)} (first 8):")
for x in pre_dec[:8]: print("  ", x)
