# Africa tick 2026-11-04: batch 7 - MapAfrica download URL plain-client test + IATI registry AfDB
import json, urllib.request, urllib.error, re

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research-data-probe/1.0"}
results = {}

def get(name, url, maxbytes=300000, timeout=45, head=False):
    out = {"url": url}
    try:
        req = urllib.request.Request(url, headers=UA, method=("HEAD" if head else "GET"))
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = b"" if head else r.read(maxbytes)
            out["status"] = r.status
            out["final_url"] = r.geturl()
            out["ct"] = r.headers.get("Content-Type", "")
            out["cd"] = r.headers.get("Content-Disposition", "")
            out["cl"] = r.headers.get("Content-Length")
            out["n"] = len(body)
            if body:
                out["head_bytes"] = body[:400].decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        out["status"] = e.code
        try:
            out["head_bytes"] = e.read(300).decode("utf-8", "replace")
        except Exception:
            pass
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    results[name] = out
    print(f"[{name}] {out.get('status')} err={out.get('error','')} ct={out.get('ct','')[:50]} cd={out.get('cd','')[:60]} cl={out.get('cl')}")
    return out

# 1. the download UUID URL from our own browser click (tests plain-client bypass)
get("dl_uuid", "https://mapafrica.afdb.org/api/v15/downloads/download/6c9dc4f2-adb3-4afb-9f4b-e0b3d8d2880b")

# 2. the download request endpoint directly from Python (does POST-free GET work?)
get("dl_req", "https://mapafrica.afdb.org/api/v15/downloads/download?data_format=csv&lang=en&currency=xdr")

# 3. IATI registry: AfDB publisher page (registry is CKAN, plain HTTP friendly)
get("iati_reg_afdb", "https://iatiregistry.org/publisher/afdb", maxbytes=100000)
get("iati_reg_search", "https://iatiregistry.org/api/3/action/package_search?q=African+Development+Bank&rows=10", maxbytes=60000)

# 4. d-portal query for AfDB activities (plain HTTP, aggregates)
get("dportal_afdb", "https://d-portal.org/ctrack.html?reporting_ref=XM-DAC-46002&year=2026#", maxbytes=40000)

json.dump(results, open("africa_tick_b7.json", "w"), indent=1)
print("\n--- iati registry search body ---")
b = results.get("iati_reg_search", {}).get("head_bytes", "")
print(b[:2000] if b else "none")
