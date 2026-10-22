#!/usr/bin/env python3
"""Probe: DATA.GOV.HK CKAN enumeration + keyword sweep + terms (2026-10-22)."""
import json
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (scout-research; dataset-factory)"}
API = "https://data.gov.hk/en-data/api/3/action/"

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

names = get(API + "package_list")["result"]
print("total packages:", len(names))
from collections import Counter
prov = Counter("-".join(n.split("-")[:2]) for n in names)
for k, v in prov.most_common(10):
    print(f"  {v:4d}  {k}")
for kw in ("accident", "incident", "burst", "prosecut", "reservoir", "cyclone"):
    hits = [n for n in names if kw in n]
    print(f"kw {kw!r}: {len(hits)}", hits[:6])
