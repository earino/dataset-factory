#!/usr/bin/env python3
"""Label probe v4: Phase II label = presence of an 'Art. 6(1)(c)' decision
(Phase II opener under both Reg 4064/89 and 139/2004).

Measures:
  - distinct cases with Art. 6(1)(c) by notification year (label base rates)
  - timing: lag notification -> first Art. 6(1)(c) decision; any opener BEFORE notification?
  - overlap between no-notification cases and decision-before-notification cases
  - decision-type mix of pre-notification decisions
  - post-hoc withdrawals of Art. 6(1)(c)/Art. 8 decisions (label caveat)
  - Phase I remedies ('Art. 6(1)(b) with conditions & obligations') count for context
Read-only. Usage: python3 probe_merger_label.py <case-data-M.json>"""
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
        dt = first(md, "decisionAdoptionDate")
        out.append((dt, types))
    return out

p2_year = collections.Counter(); notif_year = collections.Counter()
opener_before_notif = 0; opener_lags = collections.Counter()
p2_with_later_withdrawal = 0
remedy_p1 = 0
pre_notif_types = collections.Counter()
no_notif_ids, pre_dec_ids = set(), set()
n_notif = 0

for cid, c in d.items():
    m = c["metadata"]
    nd = first(m, "caseNotificationDate")
    decs = dec_list(c)
    types_all = set().union(*[t for _, t in decs]) if decs else set()
    if not nd:
        no_notif_ids.add(cid)
    else:
        n_notif += 1
        ny = nd[:4]; notif_year[ny] += 1
        openers = [dt for dt, t in decs if "Art. 6(1)(c)" in t and dt]
        early = [dt for dt in openers if dt < nd]
        if early: opener_before_notif += 1
        for _, t in decs:
            if "Art. 6(1)(c)" in t or "Art. 8" in " ".join(t):
                pass
        if openers:
            p2_year[ny] += 1
            first_op = min(openers)
            y0, m0 = int(nd[:4]), int(nd[5:7]); y1, m1 = int(first_op[:4]), int(first_op[5:7])
            opener_lags[(y1-y0)*12 + (m1-m0)] += 1
            if any("Withdrawal of Art. 6(1)(c)" in " ".join(t) for _, t in decs):
                p2_with_later_withdrawal += 1
        pre = [t for dt, t in decs if nd and dt and dt < nd]
        if pre:
            pre_dec_ids.add(cid)
            for t in pre:
                for x in t: pre_notif_types[x] += 1
        if any("Art. 6(1)(b) with conditions & obligations" in t for _, t in decs):
            remedy_p1 += 1

tot_p2 = sum(p2_year.values())
print(f"cases with notification date: {n_notif}; Phase II (Art. 6(1)(c) present): {tot_p2} "
      f"({100.0*tot_p2/n_notif:.2f}% of notified)")
print(f"openers dated BEFORE notification: {opener_before_notif}")
print(f"Phase II cases whose opener was later withdrawn: {p2_with_later_withdrawal}")
print(f"Phase I remedies (6(1)(b) w/ cond): {remedy_p1} ({100.0*remedy_p1/n_notif:.2f}%)")
print(f"\nno-notification cases {len(no_notif_ids)}, decision-before-notification cases {len(pre_dec_ids)}, "
      f"overlap {len(no_notif_ids & pre_dec_ids)}")
print("decision-type mix of pre-notification decisions (top 10):")
for k, v in pre_notif_types.most_common(10): print(f"  {v:5d}  {k}")
print("\nlag notification -> first Phase II opener (months):")
for k in sorted(opener_lags)[:12]: print(f"  {k} mo: {opener_lags[k]}")
print("\nyear: notified | phaseII")
for y in sorted(notif_year): print(f"  {y}: {notif_year[y]:5d} | {p2_year[y]:4d}")
print("\nsplit sketch on phaseII label:")
def w(a, b, ctr): return sum(v for k, v in ctr.items() if a <= int(k) <= b)
for name, a, b in [("train 1990-2013", 1990, 2013), ("eval 2014-2018", 2014, 2018),
                   ("holdout 2019-2026", 2019, 2026),
                   ("post-reform train 2005-2015", 2005, 2015), ("eval 2016-2020", 2016, 2020),
                   ("holdout 2021-2026", 2021, 2026)]:
    print(f"  {name}: {w(a,b,notif_year)} | {w(a,b,p2_year)}")
