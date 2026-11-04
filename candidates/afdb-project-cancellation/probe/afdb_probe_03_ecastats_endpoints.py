# Africa tick 2026-11-04: batch 3 - ecastats API discovery, AfDB bulk check, KE portal, SAPS
import json, urllib.request, urllib.error, re

results = {}
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"}

def get(name, url, maxbytes=400000, timeout=40, binary=False):
    out = {"url": url}
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(maxbytes)
            out["status"] = r.status
            out["ct"] = r.headers.get("Content-Type", "")
            out["n"] = len(body)
            if binary:
                out["path"] = f"b3_{name}.bin"
                open(out["path"], "wb").write(body)
            else:
                out["body"] = body.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        out["status"] = e.code
        try:
            out["body"] = e.read(3000).decode("utf-8", "replace")
        except Exception:
            out["body"] = ""
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    results[name] = out
    print(f"[{name}] status={out.get('status')} err={out.get('error','')} ct={out.get('ct','')[:40]} n={out.get('n','')}")
    return out

# 1. ecastats JS bundle -> find API endpoints
js = get("ecastats_js", "https://ecastats.uneca.org/data/assets/index-B9a3nMaS.js")
if js.get("body"):
    b = js["body"]
    urls = sorted(set(re.findall(r'https?://[a-zA-Z0-9._/-]+', b)))
    apiish = sorted(set(re.findall(r'["\'](/[a-zA-Z0-9_./-]*api[a-zA-Z0-9_./-]*)["\']', b)))
    paths = sorted(set(re.findall(r'["\'](/data/[a-zA-Z0-9_./?=-]{2,60})["\']', b)))[:40]
    results["ecastats_urls"] = urls[:40]
    results["ecastats_apiish"] = apiish[:40]
    results["ecastats_paths"] = paths
    print("URLS:", len(urls), "APIISH:", len(apiish), "PATHS:", len(paths))
    for u in urls[:25]: print("  u:", u)
    for a_ in apiish[:25]: print("  a:", a_)
    for p in paths[:25]: print("  p:", p)

# 2. AfDB projects-and-operations page: bulk data / API signals
af = get("afdb_po", "https://www.afdb.org/en/projects-and-operations")
if af.get("body"):
    b = af["body"]
    hits = sorted(set(re.findall(r'href="([^"]*(?:download|api|csv|json|data)[^"]*)"', b, re.I)))
    results["afdb_links"] = hits[:30]
    for h in hits[:20]: print("  af:", h)

# 3. Kenya open data portal (Socrata-era opendata.go.ke) reachability
get("ke_opendata", "https://opendata.go.ke/", maxbytes=20000)

# 4. SAPS copyright page via plain curl-like fetch with relaxed context? NO - record the cert failure honestly.
# Instead try http (no TLS) which the 2026-10-21 evidence may also have used
get("saps_http", "http://www.saps.gov.za/copyright.php", maxbytes=30000)

json.dump(results, open("africa_tick_b3.json", "w"), indent=1)
print("\nsaved africa_tick_b3.json")
