#!/usr/bin/env python3
"""Repro: KNBS National Statistical Repository probes (kenya-opendata-knbs, 2026-10-23 update).
Anonymous DSpace 10 REST reads; verifies the CC BY-NC 4.0 statement first-hand. Run from anywhere."""
import json
import re
import urllib.error
import urllib.request

BASE = "https://repository.knbs.or.ke"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research-probe/1.0"}

def get(url, timeout=25, accept="application/json", max_read=500_000):
    req = urllib.request.Request(url, headers={**UA, "Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(max_read)
    except urllib.error.HTTPError as e:
        return e.code, str(e).encode()
    except Exception as e:
        return None, str(e).encode()

st, body = get(f"{BASE}/server/api")
print("API root:", st, "(live DSpace" , json.loads(body).get("dspaceVersion", "?") if st == 200 else "UNREACHABLE", ")")

st, body = get(f"{BASE}/server/api/core/communities?size=100")
comms = json.loads(body).get("_embedded", {}).get("communities", [])
print(f"top-level communities: {len(comms)}")
for c in comms[:8]:
    print("  -", c.get("name"))

st, body = get(f"{BASE}/server/api/discover/search/objects?size=10")
d = json.loads(body)
sr = d.get("_embedded", {}).get("searchResult", {})
print("\ndiscover total objects:", sr.get("page", {}).get("totalElements"))
for obj in sr.get("_embedded", {}).get("objects", [])[:6]:
    it = obj.get("_embedded", {}).get("indexableObject", {})
    md = it.get("metadata", {})
    t = (md.get("dc.title") or [{}])[0].get("value", "")
    dt = (md.get("dc.date.issued") or [{}])[0].get("value", "")
    print(f"  - [{it.get('type')}] {t[:80]} | {dt[:12]}")

print("\nitem-level access (expect 401 / 404 for anonymous):")
print("  /core/items ->", get(f"{BASE}/server/api/core/items?size=1")[0])
print("  /core/collections/<crime-uuid>/items ->",
      get(f"{BASE}/server/api/core/collections/a9ddef49-ba98-4895-903e-efe4e44a5176/items?size=5")[0])

st, body = get(f"{BASE}/info/accessibility", accept="text/html")
txt = body.decode("utf-8", "replace")
plain = re.sub(r"<script.*?</script>|<style.*?</style>", " ", txt, flags=re.S)
plain = re.sub(r"<[^>]+>", " ", plain)
plain = re.sub(r"\s+", " ", plain)
m = re.search(r"(Unless stated otherwise[^.]*\.)", plain)
print("\nlicence statement (repository's own accessibility page):")
print("  status:", st)
print("  QUOTE:", m.group(1) if m else "NOT FOUND - re-read before relying on the record")
