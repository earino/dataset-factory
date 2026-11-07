# data.gov.ma reopen-condition re-census: dataset count vs 697 baseline + publisher orgs
import json, urllib.request
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research-probe"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.status, r.read()
try:
    st, body = get("https://www.data.gov.ma/data/api/3/action/package_search?rows=0")
    d = json.loads(body)
    print("HTTP", st, "count:", d["result"]["count"])
except Exception as e:
    print("package_search failed:", repr(e))
# top organisations by package count
try:
    st, body = get("https://www.data.gov.ma/data/api/3/action/package_search?rows=0&facet.field=[%22organization%22]")
    d = json.loads(body)
    orgs = d["result"]["search_facets"].get("organization", {}).get("items", [])
    for o in sorted(orgs, key=lambda x: -x.get("count", 0))[:15]:
        print("org:", o.get("name"), o.get("count"))
except Exception as e:
    print("facet query failed:", repr(e))
