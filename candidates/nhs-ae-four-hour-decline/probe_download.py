#!/usr/bin/env python3
"""Probe: download all NHS England monthly A&E CSVs and build the provider-month panel."""
import json
import os
import csv
import io
import time
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
OUT = "/opt/data/cache/scratch/ae_csvs"
os.makedirs(OUT, exist_ok=True)

with open("/opt/data/cache/scratch/ae_csv_urls.json") as f:
    pages = json.load(f)

urls = []
for page, v in pages.items():
    urls.extend(v.get("monthly", []))
print("urls:", len(urls))

t0 = time.time()
n_ok = n_fail = 0
fails = []
for u in urls:
    name = u.rsplit("/", 1)[-1]
    dest = os.path.join(OUT, name)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        n_ok += 1
        continue
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        with open(dest, "wb") as f:
            f.write(data)
        n_ok += 1
    except Exception as e:
        n_fail += 1
        fails.append((name, repr(e)))
print(f"downloaded {n_ok} ok, {n_fail} fail in {time.time()-t0:.1f}s, total bytes "
      f"{sum(os.path.getsize(os.path.join(OUT,x)) for x in os.listdir(OUT))}")
for f_ in fails[:5]:
    print("FAIL", f_)
