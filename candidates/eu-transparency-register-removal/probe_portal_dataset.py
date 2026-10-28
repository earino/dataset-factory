#!/usr/bin/env python3
"""Fetch the EU Transparency Register dataset record from data.europa.eu
and enumerate all distributions (titles, formats, URLs, licence)."""
import json
import urllib.parse
import urllib.request

API = "https://data.europa.eu/api/hub/search/search"
DETAIL = "https://data.europa.eu/api/hub/search/datasets/"
UA = {"User-Agent": "scout-discovery/1.0"}


def langval(v):
    if isinstance(v, dict):
        for k in ("en", "de", "fr", "it", "es"):
            if k in v and isinstance(v[k], str):
                return v[k]
        return next((x for x in v.values() if isinstance(x, str)), "")
    if isinstance(v, list):
        return langval(v[0]) if v else ""
    return v if isinstance(v, str) else ""


url = API + "?" + urllib.parse.urlencode({"q": "Transparency Register", "limit": 30})
with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
    data = json.load(r)

target = None
for rset in data.get("result", {}).get("results", []):
    pub = (rset.get("publisher") or {}).get("name", "")
    title = langval(rset.get("title"))
    if "Secretariat" in pub and "Transparency" in title:
        target = rset["id"]
        print("FOUND:", title, "| publisher:", pub, "| id:", rset["id"])

if not target:
    print("no Secretariat-General transparency dataset in top 30; ids seen:")
    for rset in data.get("result", {}).get("results", [])[:30]:
        print(" -", langval(rset.get("title"))[:80], "|", (rset.get("publisher") or {}).get("name", "?"), "|", rset.get("id"))
    raise SystemExit(1)

with urllib.request.urlopen(urllib.request.Request(DETAIL + urllib.parse.quote(target, safe=""), headers=UA), timeout=30) as r:
    ds = json.load(r)

res = ds.get("result", {})
print("\ndataset title:", langval(res.get("title")))
print("publisher:", (res.get("publisher") or {}).get("name"), (res.get("publisher") or {}).get("resource"))
print("modified:", res.get("modified"))
print("description:", langval(res.get("description"))[:600])
print("access_right:", langval((res.get("access_right") or {}).get("label")))
print("accrual_periodicity:", langval((res.get("accrual_periodicity") or {}).get("label")))
print("provenance/other keys:", [k for k in res.keys()][:40])

dists = res.get("distributions", [])
print("\ndistribution count:", len(dists))
for d in dists:
    lic = d.get("license") or {}
    lic_url = lic.get("resource") if isinstance(lic, dict) else str(lic)
    print(" -", langval(d.get("title"))[:90], "| fmt:", langval((d.get("format") or {}).get("label")), "| issued:", str(d.get("issued"))[:10], "| modified:", str(d.get("modified"))[:10])
    print("    url:", langval(d.get("access_url")) or langval(d.get("download_url")))
    print("    licence:", lic_url)
