# Africa tick 2026-11-04: batch 12 - registry resource URL + raw XML schema check (bounded 3MB)
import json, urllib.request, urllib.error, re

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research-data-probe/1.0"}
results = {}

def get(name, url, maxbytes=3000000, timeout=60):
    out = {"url": url}
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(maxbytes)
            out["status"] = r.status
            out["ct"] = r.headers.get("Content-Type", "")
            out["n"] = len(body)
            out["text"] = body.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        out["status"] = e.code
        try:
            out["text"] = e.read(2000).decode("utf-8", "replace")
        except Exception:
            out["text"] = ""
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    results[name] = out
    print(f"[{name}] {out.get('status')} err={out.get('error','')} ct={out.get('ct','')[:40]} n={out.get('n','')}")
    return out

# A. package_show full record -> resource URL + extras
ps = get("pkg_show", "https://iatiregistry.org/api/3/action/package_show?id=afdb-saotome", maxbytes=30000)
res_url = None
if ps.get("text"):
    d = json.loads(ps["text"])
    r0 = d["result"]
    print("license_id:", r0.get("license_id"))
    print("extras:", {e["key"]: e["value"] for e in r0.get("extras", [])})
    res = r0.get("resources", [])
    if res:
        res_url = res[0].get("url")
        print("resource url:", res_url)
        print("resource format:", res[0].get("format"), "last_modified:", res[0].get("last_modified"))

# B. fetch the XML (bounded) and inspect statuses + dates
if res_url:
    xml = get("xml_saotome", res_url, maxbytes=3000000)
    if xml.get("text"):
        t = xml["text"]
        statuses = re.findall(r'<activity-status code="(\d+)"', t)
        from collections import Counter
        print("activity-status mix:", Counter(statuses))
        # date types present: iati activity-date type 1 planned start, 2 actual start, 3 planned end, 4 actual end
        datetypes = Counter(re.findall(r'<activity-date[^>]*type="(\d+)"', t))
        print("activity-date type mix:", dict(datetypes))
        # per-activity pairing: show first two activities' date/status blocks compactly
        acts = re.findall(r'<iati-activity.*?</iati-activity>', t, re.S)
        print("activities parsed:", len(acts))
        for a in acts[:3]:
            aid = re.search(r'<iati-identifier>([^<]+)</iati-identifier>', a)
            st = re.search(r'<activity-status code="(\d+)"', a)
            dates = re.findall(r'<activity-date[^>]*type="(\d+)"[^>]*iso-date="([^"]+)"', a)
            print("  ", aid.group(1) if aid else "?", "status", st.group(1) if st else "?", "dates", dates)

# C. enumerate all afdb datasets (compat API fq attempt)
en = get("pkg_search_afdb", "https://iatiregistry.org/api/3/action/package_search?fq=organization:afdb&rows=100", maxbytes=200000)
if en.get("text"):
    try:
        d = json.loads(en["text"])
        if d.get("success"):
            print("count:", d["result"].get("count"))
            names = [r["name"] for r in d["result"].get("results", [])]
            print("datasets:", len(names), names[:60])
            lic = {r.get("license_id") for r in d["result"].get("results", [])}
            print("license_ids:", lic)
    except Exception as e:
        print("parse fail:", e, en["text"][:200])

json.dump(results, open("africa_tick_b12.json", "w"), indent=1)
