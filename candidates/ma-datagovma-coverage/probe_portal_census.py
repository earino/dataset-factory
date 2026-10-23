#!/usr/bin/env python3
"""Repro: Morocco data.gov.ma portal census + AMMC granularity check (ma-datagovma-coverage).
Anonymous CKAN reads; bounded AMMC file download. Run from anywhere."""
import io
import json
import re
import urllib.request
import zipfile

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research-probe/1.0"}
API = "https://www.data.gov.ma/data/api/3/action/"

def jget(path, timeout=30):
    req = urllib.request.Request(API + path, headers={**UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read(600_000))
            return d if isinstance(d, dict) else {"__non_dict__": d}
    except Exception as e:
        return {"__err__": str(e)}

d = jget("package_search?rows=0&facet.field=[\"organization\",\"res_format\",\"license_id\"]")
res = d.get("result", {})
print("total datasets:", res.get("count"))
print("license facet:", res.get("facets", {}).get("license_id"))
print("format facet:", res.get("facets", {}).get("res_format"))
print("top orgs:", sorted(res.get("facets", {}).get("organization", {}).items(),
                         key=lambda kv: -kv[1])[:15])

print("\nAMMC weekly OPCVM: check granularity (expect category-level, not per-fund)")
d = jget("package_show?id=stat-hebdo-opcvm-2025")
for r0 in d.get("result", {}).get("resources", []):
    url = r0.get("url", "")
    if url.endswith(".xlsx"):
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read(8_000_000)
        print(f"downloaded {url[-40:]}: {len(body)} bytes")
        z = zipfile.ZipFile(io.BytesIO(body))
        wb = z.read("xl/workbook.xml").decode("utf-8", "replace")
        print("  sheets:", re.findall(r'name="([^"]+)"', wb)[:5])
        ss = z.read("xl/sharedStrings.xml").decode("utf-8", "replace")[:2500]
        print("  first strings:", re.findall(r"<t[^>]*>([^<]{2,40})</t>", ss)[:12])
        break
