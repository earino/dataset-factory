#!/usr/bin/env python3
"""FY2017-18 panel measurement for austender-contract-amendment-occurrence.

Streams the data.gov.au FY2017-18 contract notice CSV (31.0 MB, one anonymous
GET, held in memory only) and reproduces the counts recorded 2026-10-28:
73,458 rows = 60,590 Parent + 12,868 Amendment; 110 agencies; procurement
method mix; parents published Jul-Dec 2017 and their in-file amendment
lower bounds (9.1% anywhere in file, 6.4% within 6 months).

Run: python3 probe_fy_panel.py
"""
import collections
import csv
import datetime
import io
import time
import urllib.request

URL = ("https://data.gov.au/data/dataset/5c7fa69b-b0e9-4553-b8df-2a022dd2e982/"
       "resource/bc2097b7-8116-4e9d-9953-98813635892a/download/17-18-fy-dataset.csv")

t0 = time.time()
req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (research probe)"})
with urllib.request.urlopen(req, timeout=300) as r:
    raw = r.read()
print(f"fetch: {len(raw)} bytes in {time.time()-t0:.1f}s")

rd = csv.DictReader(io.StringIO(raw.decode("utf-8", "replace")))
parents = {}
amends = collections.defaultdict(list)
n = 0
types = collections.Counter()
agencies = collections.Counter()
methods = collections.Counter()
for row in rd:
    n += 1
    typ = row["Contract Notice Type"]
    types[typ] += 1
    agencies[row["Agency Name"]] += 1
    methods[row["Procurement Method"]] += 1
    cid = row["Contract ID"] or ""
    if typ == "Parent":
        parents[cid] = row["Publish Date"]
    elif typ == "Amendment":
        pid = row["Parent Contract ID"] or (cid.rsplit("-A", 1)[0] if "-A" in cid else None)
        if pid:
            amends[pid].append(row["Amendment Date"] or row["Publish Date"])

print("rows:", n, "| types:", dict(types))
print("parents:", len(parents), "| with >=1 amendment in file:", len(amends))
print("agencies:", len(agencies), "| methods:", dict(methods))


def pd_(s):
    for f in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


eligible = amended6 = amend_any = 0
for cid, pdate in parents.items():
    d = pd_(pdate)
    if not (d and datetime.date(2017, 7, 1) <= d <= datetime.date(2017, 12, 31)):
        continue
    eligible += 1
    evs = [pd_(a) for a in amends.get(cid, [])]
    evs = [e for e in evs if e]
    if evs:
        amend_any += 1
    if any(0 <= (e - d).days <= 182 for e in evs):
        amended6 += 1
print(f"parents published Jul-Dec 2017: {eligible}")
print(f"  >=1 amendment row in file: {amend_any} ({amend_any/max(eligible,1):.1%})")
print(f"  amended within 6 months (lower bound): {amended6} ({amended6/max(eligible,1):.1%})")
