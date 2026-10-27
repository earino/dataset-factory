#!/usr/bin/env python3
"""Parse the CONAGUA presas catalog + sample station CSV (discovery probe 2)."""
import csv, io, sys
from datetime import date

# --- catalog ---
raw = open("/opt/data/cache/scratch/probe_0_Catalogo_de_presas.csv", "rb").read()
text = raw.decode("latin-1")
rows = list(csv.reader(io.StringIO(text)))
hdr = rows[0]
print("CATALOG columns:", [h.replace("\r"," ").replace("\n"," ").strip() for h in hdr])
data = [r for r in rows[1:] if r and r[0].strip()]
print("CATALOG dams:", len(data))
states = {}
for r in data:
    st = r[6].strip()
    states[st] = states.get(st, 0) + 1
print("CATALOG states:", len(states), sorted(states.items(), key=lambda x: -x[1])[:8])
print("CATALOG sample row:", data[3])

# --- station ALRBN ---
raw = open("/opt/data/cache/scratch/probe_ALRBN.csv", "rb").read().decode("utf-8", "replace")
lines = raw.splitlines()
# find header line starting with Estacion,
hdr_i = next(i for i, l in enumerate(lines) if l.startswith("Estacion,"))
srows = list(csv.reader(io.StringIO("\n".join(lines[hdr_i:]))))
sh = srows[0]
print("\nSTATION header:", sh)
sdata = [r for r in srows[1:] if len(r) == len(sh) and r[1]]
print("STATION ALRBN rows:", len(sdata))
print("first:", sdata[0], "\nlast: ", sdata[-1])
# parse dates + volume coverage by decade
import collections
vol_by_dec = collections.defaultdict(lambda: [0,0,None,None])  # n_rows, n_vol, min, max
for r in sdata:
    d = r[1][:10]
    dec = d[:3] + "0s"
    e = vol_by_dec[dec]
    e[0] += 1
    v = r[8].strip() if len(r) > 8 else ""
    if v:
        fv = float(v)
        e[1] += 1
        e[2] = fv if e[2] is None else min(e[2], fv)
        e[3] = fv if e[3] is None else max(e[3], fv)
for dec in sorted(vol_by_dec):
    n, nv, lo, hi = vol_by_dec[dec]
    print(f"  {dec}: rows={n} vol={nv} ({100*nv//max(n,1)}%) min={lo} max={hi}")
