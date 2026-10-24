#!/usr/bin/env python3
"""Aggregate probe v2 over DG COMP merger open data, with decision-type labels
parsed from their JSON wrappers. Labels:
  L1 phase2      = case has any Art. 8* decision (Phase II reached)
  L2 intervened  = any of Art. 6(1)(c), Art. 8(2)*, Art. 8(3)  (conditions/prohibition)
  L3 referral_out= any of Art. 4(4), Art. 4(5), Art. 9(3), Art. 22* referral
  W  withdrawn   = Withdrawn / Aborted
Also: notification->last-decision lag distribution, decisions-before-notification count,
known-event fixtures (M.1845, M.4731, M.10187), per-year counts for split design.
Read-only. Usage: python3 probe_merger_agg2.py <case-data-M.json>"""
import json, sys, collections, statistics

d = json.load(open(sys.argv[1]))

def first(m, k):
    v = m.get(k, [])
    return v[0] if v else None

def labels_of(c):
    labs = []
    for dec in c.get("decisions", []):
        for raw in dec.get("metadata", {}).get("decisionTypes", []):
            try:
                labs.append(json.loads(raw).get("label", ""))
            except Exception:
                labs.append(raw)
    return labs

def adoption_dates(c):
    out = []
    for dec in c.get("decisions", []):
        v = first(dec.get("metadata", {}), "decisionAdoptionDate")
        if v: out.append(v)
    return out

y_l1 = collections.Counter(); y_l2 = collections.Counter()
y_l3 = collections.Counter(); y_w = collections.Counter(); y_n = collections.Counter()
dec_before_notif = 0
lags = collections.Counter()
l1_lags = []
n = 0
for cid, c in d.items():
    n += 1
    m = c["metadata"]
    ny = (first(m, "caseNotificationDate") or "")[:4]
    labs = labels_of(c)
    dates = adoption_dates(c)
    if ny: y_n[ny] += 1
    nd = first(m, "caseNotificationDate")
    if nd:
        if any(x < nd for x in dates): dec_before_notif += 1
        if dates:
            mx = max(dates)
            y0, m0, dd0 = map(int, nd.split("-")); y1, m1, dd1 = map(int, mx.split("-"))
            lag = (y1-y0)*12 + (m1-m0)
            lags[lag] += 1
    if any(l.startswith("Art. 8") for l in labs):
        y_l1[ny] += 1
        if nd and dates: l1_lags.append(max(dates))
    if any(l.startswith("Art. 6(1)(c)") or l.startswith("Art. 8(2)") or l.startswith("Art. 8(3)") for l in labs):
        y_l2[ny] += 1
    if any(l.startswith("Art. 4(4)") or l.startswith("Art. 4(5)") or l.startswith("Art. 9(3)") or l.startswith("Art. 22") for l in labs):
        y_l3[ny] += 1
    if any(l.startswith("Withdrawn") or l.startswith("Aborted") for l in labs):
        y_w[ny] += 1

print(f"n_cases {n}, cases with a decision dated BEFORE notification: {dec_before_notif}")
tot_l1 = sum(v for k, v in y_l1.items() if k); tot_l2 = sum(y_l2.values()); tot_l3 = sum(y_l3.values()); tot_w = sum(y_w.values())
print(f"L1 phase2 cases {tot_l1} ({100.0*tot_l1/n:.2f}%) | L2 intervened {tot_l2} ({100.0*tot_l2/n:.2f}%) | "
      f"L3 referral_out {tot_l3} ({100.0*tot_l3/n:.2f}%) | withdrawn {tot_w} ({100.0*tot_w/n:.2f}%)")
print("\nyear: notified | phase2 | intervened | referral_out | withdrawn")
for y in sorted(set(list(y_n) + list(y_l1))):
    print(f"  {y}: {y_n[y]:5d} | {y_l1[y]:4d} | {y_l2[y]:4d} | {y_l3[y]:4d} | {y_w[y]:4d}")
print("\nnotification -> last decision lag (months, top 15):")
for k, v in sorted(lags.items())[:15]: print(f"  {k} mo: {v}")

print("\nknown-event fixtures:")
for cid, expect in [("M.1845", "Boeing/McDonnell Douglas 1997 Art. 8(2)"),
                    ("M.4731", "Google/DoubleClick 2008 Art. 6(1)(b) w/conditions"),
                    ("M.10187", "Illumina/GRAIL 2021 Art. 8(3) prohibition")]:
    c = d.get(cid)
    if not c:
        print(f"  {cid} ({expect}): NOT PRESENT"); continue
    m = c["metadata"]
    print(f"  {cid} ({expect}): title={first(m,'caseTitle')!r} notif={first(m,'caseNotificationDate')} "
          f"labels={sorted(set(labels_of(c)))[:6]} lastdec={first(m,'caseLastDecisionDate')}")

# window sketch: disjoint temporal thirds on notification year for L1 and L2
def window(a, b, ctr): return sum(v for k, v in ctr.items() if k and a <= int(k) <= b)
print("\nsplit-window sketch (notifications | L1 | L2):")
for name, a, b in [("train 1990-2013", 1990, 2013), ("eval 2014-2018", 2014, 2018),
                   ("holdout 2019-2026", 2019, 2026),
                   ("post-reform train 2005-2015", 2005, 2015), ("post-reform eval 2016-2020", 2016, 2020),
                   ("post-reform holdout 2021-2026", 2021, 2026)]:
    print(f"  {name}: {window(a,b,y_n)} | {window(a,b,y_l1)} | {window(a,b,y_l2)}")
