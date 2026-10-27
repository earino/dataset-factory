#!/usr/bin/env python3
"""Bounded multi-dam sample: coverage, volume ranges, drought-onset events.

Fetches 8 dam CSVs chosen from the catalog across drought-prone states,
records fetch cost, and computes onset-event counts at 25%/40% of each
dam's observed max volume (proxy capacity, documented assumption).
"""
import csv, io, subprocess, sys, time
from datetime import date, datetime

CAT = "/opt/data/cache/scratch/probe_0_Catalogo_de_presas.csv"
JAR = "/opt/data/cache/scratch/conagua_probe_jar.txt"
BASE = "https://sih.conagua.gob.mx/basedatos/Presas/"

# find claves by name fragment
cat = {}
for r in csv.reader(io.StringIO(open(CAT, "rb").read().decode("latin-1"))):
    if r and r[0].strip().isdigit():
        cat[r[1].strip()] = (r[2], r[6], r[7])
want = ["Cuchillo", "Boca", "Falc", "Amistad", "Angostura", "Chicoas", "Infiernillo", "Allende", "El Yeso", "Sol", "Palmito"]
picks = {}
for frag in want:
    for clave, (nom, edo, muni) in cat.items():
        if frag.lower() in nom.lower():
            picks[clave] = (frag, nom, edo)
            break
print("matched:", {k: v[1] for k, v in picks.items()})

def fetch(clave, out):
    t0 = time.time()
    url = BASE + clave + ".csv"
    subprocess.run(["curl", "-skL", "--max-time", "120", "--max-redirs", "8",
                    "-A", "Mozilla/5.0 (X11; Linux x86_64)",
                    "-c", JAR, "-b", JAR, "-o", out, "-w",
                    f"{clave} http=%{{http_code}} bytes=%{{size_download}} time=%{{time_total}}s\n", url],
                   check=False)

def parse(clave):
    raw = open(f"/opt/data/cache/scratch/dam_{clave}.csv", "rb").read().decode("utf-8", "replace")
    lines = raw.splitlines()
    try:
        hdr_i = next(i for i, l in enumerate(lines) if l.startswith("Estacion,"))
    except StopIteration:
        print(clave, "NO HEADER"); return None
    rows = list(csv.reader(io.StringIO("\n".join(lines[hdr_i:]))))
    out = []
    for r in rows[1:]:
        if len(r) >= 9 and r[1] and r[8].strip():
            try:
                v = float(r[8])
            except ValueError:
                continue
            try:
                d = datetime.strptime(r[1][:10], "%Y-%m-%d").date()
            except ValueError:
                continue
            out.append((d, v))
    return out

summary = {}
for clave in picks:
    fetch(clave, f"/opt/data/cache/scratch/dam_{clave}.csv")
    data = parse(clave)
    if not data:
        print(clave, "no data"); continue
    data.sort()
    vmax = max(v for _, v in data)
    by_year = {}
    for d, v in data:
        by_year.setdefault(d.year, []).append(v)
    yrs_cov = {y: len(vv) for y, vv in sorted(by_year.items())}
    # drought-onset events: day above 25% of vmax, then falls below within horizon
    events25, events40 = {}, {}
    n_below25_ever = 0
    data_sorted = data
    for pct, evs in ((0.25, events25), (0.40, events40)):
        thr = vmax * pct
        i = 0
        prev_below = False
        while i < len(data_sorted):
            d, v = data_sorted[i]
            below = v < thr
            if below and not prev_below:
                evs[d.year] = evs.get(d.year, 0) + 1
            prev_below = below
            i += 1
    summary[clave] = dict(n=len(data), vmax=round(vmax,1), first=min(d for d,_ in data), last=max(d for d,_ in data),
                          ev25=events25, ev40=events40)
    print(f"\n{clave} {picks[clave][1]} ({picks[clave][2]}): n_days_vol={len(data)} vmax={vmax:.0f} Mm3 "
          f"first={min(d for d,_ in data)} last={max(d for d,_ in data)}")
    print(f"  onset events @25%: total={sum(events25.values())} by_year={events25}")
    print(f"  onset events @40%: total={sum(events40.values())} by_year={events40}")
import json
json.dump({k: {kk: (str(vv) if isinstance(vv,date) else vv) for kk, vv in v.items()} for k, v in summary.items()},
          open("/opt/data/cache/scratch/conagua_sample_summary.json", "w"), indent=1, default=str)
print("\nsummary saved")
