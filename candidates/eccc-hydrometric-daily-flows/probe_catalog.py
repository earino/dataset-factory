"""ECCC hydrometric catalogue probe (2026-10-21 session).

Run: python3 candidates/eccc-hydrometric-daily-flows/probe_catalog.py

The mirror verdict does not rest on access cost; this probe records the
open.canada.ca identity + licence of the ECCC hydrometric records.
"""
import json
import urllib.parse
import urllib.request

URL = ("https://open.canada.ca/data/en/api/3/action/package_search?q="
       + urllib.parse.quote("hydrometric") + "&rows=10")
with urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "scout/1.0"}), timeout=60) as r:
    data = json.loads(r.read())
print(f"HTTP {r.status}, count={data['result']['count']}")
for res in data["result"]["results"]:
    org = (res.get("organization") or {}).get("title", "?")
    print(f"  [{org}] {res.get('title_en')} | id={res.get('id')} | lic={res.get('license_id')}")
