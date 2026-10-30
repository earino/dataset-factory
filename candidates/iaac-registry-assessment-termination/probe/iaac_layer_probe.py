#!/usr/bin/env python3
"""IAAC assessment_inventory probe (2026-10-30 Canada tick).

Reproduces every aggregate number in candidates/iaac-registry-assessment-termination/notes.md:
  1. MapServer liveness + per-layer counts + 8-record samples per layer
  2. Full attribute fetch of all 6,600 rows (no geometry) with cost measurement
  3. Start-year x state histogram, category mix, province mix

Anonymous ESRI REST; run from anywhere. ~10 requests, ~1 MB total.
"""
import json
import time
import urllib.parse
import urllib.request
from collections import Counter

BASE = ("https://maps-cartes.services.geo.ca/server_serveur/rest/services/"
        "IAAC/assessment_inventory_en/MapServer/{L}/{action}")

def get(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()

# --- 1. liveness, counts, schema ---
svc = json.loads(get(BASE.format(L="", action="?f=json")))
print("layers:", [(l["id"], l["name"]) for l in svc.get("layers", [])])
for L in (0, 1, 2):
    meta = json.loads(get(BASE.format(L=L, action="?f=json")))
    cnt = json.loads(get(BASE.format(L=L, action="query?where=1%3D1&returnCountOnly=true&f=json")))
    print(f"layer {L} ({meta.get('name')}): count={cnt.get('count')}")
    print("  fields:", [f["name"] for f in meta.get("fields", [])])

# --- 2. full attribute fetch with cost ---
t0, reqs, nbytes, rows = time.time(), 0, 0, []
for L in (0, 1, 2):
    offset = 0
    while True:
        q = urllib.parse.urlencode({
            "where": "1=1",
            "outFields": "project_id,project_cat_en,province_codes,start_date,project_state_en",
            "returnGeometry": "false", "resultRecordCount": 1000,
            "resultOffset": offset, "f": "json"})
        body = get(BASE.format(L=L, action="query?") + q)
        reqs += 1
        nbytes += len(body)
        fs = json.loads(body).get("features", [])
        rows.extend(f["attributes"] for f in fs)
        if len(fs) < 1000:
            break
        offset += 1000
print(json.dumps({"rows": len(rows), "requests": reqs, "bytes": nbytes,
                  "seconds": round(time.time() - t0, 2)}, indent=1))

# --- 3. histograms ---
hist = {}
for r in rows:
    y = (r["start_date"] or "")[:4] or "none"
    hist.setdefault(y, Counter())[r["project_state_en"]] += 1
for y in sorted(hist):
    c = hist[y]
    print(f"{y} {c.get('Completed', 0)}/{c.get('In progress', 0)}/{c.get('Terminated', 0)}")
print("categories:", Counter(r["project_cat_en"] for r in rows).most_common(12))
print("provinces:", Counter((r["province_codes"] or "?").split(";")[0] for r in rows).most_common(8))
