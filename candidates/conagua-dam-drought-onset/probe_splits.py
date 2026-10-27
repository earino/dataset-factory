#!/usr/bin/env python3
"""Stratified ~30-dam sample: split-window onset counts (discovery evidence).

One dam per state where possible (26 states), then split-window counts of
30-day drought-onset events at 25% of per-dam observed max volume.
Clustered counts = distinct (dam, year) onsets.
"""
import csv, io, subprocess, time, json
from datetime import datetime

CAT = "/opt/data/cache/scratch/probe_0_Catalogo_de_presas.csv"
JAR = "/opt/data/cache/scratch/conagua_probe_jar.txt"
BASE = "https://sih.conagua.gob.mx/basedatos/Presas/"
ALREADY = {"ALRBN","CCHNL","CILAAMSMX","CILAFLCMX","INFMC","IALGJ","SLSGJ"}

# pick first clave per state from catalog
cat_rows = [r for r in csv.reader(io.StringIO(open(CAT,"rb").read().decode("latin-1"))) if r and r[0].strip().isdigit()]
per_state = {}
for r in cat_rows:
    clave, nom, edo = r[1].strip(), r[2], r[6].strip()
    per_state.setdefault(edo, clave)
picks = sorted(set(list(per_state.values())[:26]) )
picks = [p for p in picks if p not in ALREADY][:20]
print("sample picks:", picks, len(picks))

def fetch(clave):
    t0 = time.time()
    subprocess.run(["curl","-skL","--max-time","90","--max-redirs","8","-A","Mozilla/5.0",
                    "-c",JAR,"-b",JAR,"-o",f"/opt/data/cache/scratch/dam_{clave}.csv",
                    BASE+clave+".csv"], check=False)
    return time.time()-t0

def parse_file(path):
    lines = open(path,"rb").read().decode("utf-8","replace").splitlines()
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
                d = datetime.strptime(r[1][:10],"%Y-%m-%d").date(); v = float(r[vi])
            except ValueError: continue
            out[d] = v
    return out

total_t = 0.0
result = {}
for clave in picks:
    dt = fetch(clave)
    total_t += dt
    vol = parse_file(f"/opt/data/cache/scratch/dam_{clave}.csv")
    if not vol:
        result[clave] = {"n": 0}; print(f"{clave}: EMPTY"); continue
    days = sorted(vol); vmax = max(vol.values()); thr = 0.25*vmax
    onsets = []
    prev = None
    for d in days:
        below = vol[d] < thr
        if below and prev is False: onsets.append(str(d))
        prev = below
    # split windows
    w = {"train<=2010": [o for o in onsets if o <= "2010-12-31"],
         "eval 2011-2018": [o for o in onsets if "2011-01-01" <= o <= "2018-12-31"],
         "holdout 2019-2026": [o for o in onsets if o >= "2019-01-01"]}
    result[clave] = {"n_days": len(days), "first": str(days[0]), "last": str(days[-1]),
                     "vmax": round(vmax,1), "n_onsets25": len(onsets), "by_window": {k: len(v) for k,v in w.items()}}
    print(f"{clave}: n={len(days)} {days[0]}..{days[-1]} vmax={vmax:.0f} onsets25={len(onsets)} "
          f"train={len(w['train<=2010'])} eval={len(w['eval 2011-2018'])} hold={len(w['holdout 2019-2026'])}")

# aggregate over ALL fetched dam files (sample + earlier 7)
import glob, os
agg = {"dams_with_data":0, "dams_no_vol":0, "events":0, "train":0, "eval":0, "holdout":0,
       "clusters": set(), "fetches": 0, "bytes": 0, "secs": 0.0}
for path in sorted(glob.glob("/opt/data/cache/scratch/dam_*.csv")):
    clave = os.path.basename(path)[4:-4]
    agg["bytes"] += os.path.getsize(path)
    vol = parse_file(path)
    if not vol: agg["dams_no_vol"] += 1; continue
    agg["dams_with_data"] += 1
    days = sorted(vol); vmax = max(vol.values()); thr = 0.25*vmax
    prev = None
    for d in days:
        below = vol[d] < thr
        if below and prev is False:
            agg["events"] += 1
            agg["clusters"].add((clave, d.year))
            y = d.year
            if y <= 2010: agg["train"] += 1
            elif y <= 2018: agg["eval"] += 1
            else: agg["holdout"] += 1
        prev = below
agg["clusters"] = len(agg["clusters"])
print(f"\nAGGREGATE over {agg['dams_with_data']} dams with data ({agg['dams_no_vol']} without):")
print(f"  events@25%: {agg['events']}  train(<=2010)={agg['train']}  eval(2011-2018)={agg['eval']}  holdout(2019-2026)={agg['holdout']}")
print(f"  clusters(dam,year): {agg['clusters']}")
print(f"  bytes fetched: {agg['bytes']/1e6:.1f} MB")
json.dump({"per_dam": result, "aggregate": {k:(list(v) if isinstance(v,set) else v) for k,v in agg.items()}},
          open("/opt/data/cache/scratch/conagua_splits_sample.json","w"), indent=1)
print("saved conagua_splits_sample.json")
