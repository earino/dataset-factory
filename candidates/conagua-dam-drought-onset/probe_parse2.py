#!/usr/bin/env python3
"""Robust parse: repeated header blocks, column order varies per file/block.

Splits each dam CSV into blocks at 'Estacion,' header lines, maps VolumenAlm
by column name, merges, and recomputes coverage + drought-onset events.
"""
import csv, glob, os, sys
from datetime import datetime

def parse_file(path):
    lines = open(path, "rb").read().decode("utf-8", "replace").splitlines()
    blocks = []
    cur = None
    for l in lines:
        if l.startswith("Estacion,"):
            if cur: blocks.append(cur)
            cur = {"header": next(csv.reader([l])), "rows": []}
        elif cur is not None:
            if l.strip():
                cur["rows"].append(l)
    if cur: blocks.append(cur)
    out = {}
    for b in blocks:
        h = b["header"]
        try:
            vi = h.index("VolumenAlm(Mm3)")
        except ValueError:
            continue
        for r in csv.reader(b["rows"]):
            if len(r) != len(h) or not r[1]:
                continue
            try:
                d = datetime.strptime(r[1][:10], "%Y-%m-%d").date()
                v = float(r[vi])
            except ValueError:
                continue
            out[d] = v
    return out

print(f"{'clave':12s} {'station':38s} {'n_vol':>7s} {'first':10s} {'last':10s} {'vmax':>8s} {'vmin':>7s} ev25 ev40 yrs25")
allsum = {}
for path in sorted(glob.glob("/opt/data/cache/scratch/dam_*.csv")):
    clave = os.path.basename(path)[4:-4]
    vol = parse_file(path)
    if not vol:
        print(clave, "EMPTY"); continue
    days = sorted(vol)
    vmax = max(vol.values()); thr25, thr40 = 0.25*vmax, 0.40*vmax
    ev25, ev40 = {}, {}
    prev25 = prev40 = False
    for d in days:
        v = vol[d]
        b25 = v < thr25; b40 = v < thr40
        if b25 and not prev25: ev25[d.year] = ev25.get(d.year, 0) + 1
        if b40 and not prev40: ev40[d.year] = ev40.get(d.year, 0) + 1
        prev25, prev40 = b25, b40
    allsum[clave] = dict(n=len(days), first=str(days[0]), last=str(days[-1]),
                         vmax=round(vmax,1), vmin=round(min(vol.values()),1),
                         ev25=ev25, ev40=ev40,
                         n_ev25=sum(ev25.values()), n_ev40=sum(ev40.values()))
    print(f"{clave:12s} {'':38s} {len(days):7d} {str(days[0]):10s} {str(days[-1]):10s} {vmax:8.1f} {min(vol.values()):7.1f} {sum(ev25.values()):4d} {sum(ev40.values()):4d} {sorted(ev25)[:3]}...")
# ALRBN too
vol = parse_file("/opt/data/cache/scratch/probe_ALRBN.csv")
print("ALRBN robust:", len(vol), min(vol), max(vol))
import json
json.dump(allsum, open("/opt/data/cache/scratch/conagua_sample_summary2.json","w"), indent=1)
