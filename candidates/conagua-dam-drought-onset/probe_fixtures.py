#!/usr/bin/env python3
"""Extract fixture dates: minima and threshold-crossing days from the sample."""
import csv, glob, os
from datetime import datetime, timedelta

def parse_file(path):
    lines = open(path, "rb").read().decode("utf-8", "replace").splitlines()
    blocks, cur = [], None
    for l in lines:
        if l.startswith("Estacion,"):
            if cur: blocks.append(cur)
            cur = {"header": next(csv.reader([l])), "rows": []}
        elif cur is not None and l.strip():
            cur["rows"].append(l)
    if cur: blocks.append(cur)
    out = {}
    for b in blocks:
        h = b["header"]
        try: vi = h.index("VolumenAlm(Mm3)")
        except ValueError: continue
        for r in csv.reader(b["rows"]):
            if len(r) != len(h) or not r[1]: continue
            try:
                d = datetime.strptime(r[1][:10], "%Y-%m-%d").date(); v = float(r[vi])
            except ValueError: continue
            out[d] = v
    return out

names = {"CILAFLCMX":"Falcon", "CCHNL":"Cuchillo", "INFMC":"Infiernillo",
         "IALGJ":"Allende", "SLSGJ":"Solis", "CILAAMSMX":"La Amistad"}
for path in sorted(glob.glob("/opt/data/cache/scratch/dam_*.csv")):
    clave = os.path.basename(path)[4:-4]
    vol = parse_file(path); days = sorted(vol)
    vmin_day = min(days, key=lambda d: vol[d])
    vmax = max(vol.values())
    # onset days at 25% with the preceding above-run length
    thr = 0.25 * vmax
    onsets = []
    prev = None
    for d in days:
        below = vol[d] < thr
        if below and prev is False:
            onsets.append((d, round(vol[d],1)))
        prev = below
    print(f"{clave:11s} {names[clave]:11s} vmin={vol[vmin_day]:7.1f} on {vmin_day} | vmax={vmax:7.1f} | 25%={thr:7.1f} | onsets({len(onsets)}):", [f"{d}({v})" for d,v in onsets[:8]])
