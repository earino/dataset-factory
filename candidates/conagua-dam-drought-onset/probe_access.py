#!/usr/bin/env python3
"""CONAGUA SIH presas access probe (discovery, 2026-10-27).

Fetches the dam catalog and a bounded sample of per-dam CSVs, prints
schema, date ranges, row counts and fetch cost. No bulk download.
"""
import csv, io, sys, time, urllib.request

BASE = "https://sih.conagua.gob.mx/basedatos/Presas/"

def fetch(url, timeout=60):
    t0 = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (scout-discovery-probe)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    return data, time.time() - t0

def show_csv(raw, name, max_rows=8):
    for enc in ("utf-8-sig", "latin-1"):
        try:
            text = raw.decode(enc)
            used = enc
            break
        except UnicodeDecodeError:
            continue
    rows = list(csv.reader(io.StringIO(text)))
    print(f"--- {name}: {len(raw)} bytes, encoding {used}, {len(rows)} rows total")
    for r in rows[:max_rows]:
        print("   ", ",".join(str(c)[:28] for c in r))
    if len(rows) > max_rows:
        print("    ...")
        for r in rows[-2:]:
            print("   ", ",".join(str(c)[:28] for c in r))
    return rows

targets = ["0_Catalogo_de_presas.csv", "presas.csv", "ALRBN.csv", "CHLJL.csv"]
for t in targets:
    try:
        raw, dt = fetch(BASE + t)
        rows = show_csv(raw, t)
        # header + date column sniff for station files
        if len(rows) > 1 and t != "0_Catalogo_de_presas.csv":
            header = rows[0]
            print(f"    header: {header}")
            # find date-like column and report min/max
            import re
            pat = re.compile(r"\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}")
            ci = None
            for i, h in enumerate(header):
                if "fecha" in h.lower() or "date" in h.lower():
                    ci = i
                    break
            if ci is not None:
                vals = [r[ci] for r in rows[1:] if len(r) > ci and pat.match(r[ci])]
                if vals:
                    print(f"    dates: n={len(vals)} min={min(vals)} max={max(vals)}")
    except Exception as e:
        print(f"--- {t}: FAILED {type(e).__name__}: {e}")
