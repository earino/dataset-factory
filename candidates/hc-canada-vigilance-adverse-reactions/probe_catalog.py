"""Health Canada Canada Vigilance catalogue probe (2026-10-21 session).

Run: python3 candidates/hc-canada-vigilance-adverse-reactions/probe_catalog.py

Established: the Vigilance packages list HTML (query-form) resources only, and
the 'Data on cannabis adverse reactions' package lists PDF annual reports only.
No CSV/API/bulk resource exists on any of the three records.
"""
import json
import urllib.request

API = "https://open.canada.ca/data/en/api/3/action/package_show?id="
for pid in ("98cad9a3-5b61-4c1e-965d-531804542560",  # Canada Vigilance online database
            "4468c43f-54a1-428c-a34f-5a2e90e35a2b",  # Instructions
            "371d84b2-e439-4c39-a4ef-8817d65a1485"):  # cannabis ADR 'data'
    with urllib.request.urlopen(urllib.request.Request(API + pid, headers={"User-Agent": "scout/1.0"}), timeout=60) as r:
        rec = json.loads(r.read())["result"]
    fmts = sorted({(res.get("format") or "?").upper() for res in rec.get("resources", [])})
    print(f"{pid}: lic={rec.get('license_id')}, resource formats={fmts}, n={len(rec.get('resources', []))}")
