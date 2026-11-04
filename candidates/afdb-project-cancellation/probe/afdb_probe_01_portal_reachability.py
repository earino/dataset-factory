# Africa tick 2026-11-04: batch 1 - reopen triggers + named-publisher reachability (anonymous GETs only)
import json, urllib.request, urllib.error, socket, ssl, sys

results = {}
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research-data-probe/1.0"}

def probe(name, url, maxbytes=200000, timeout=25):
    out = {"url": url}
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(maxbytes)
            out["status"] = r.status
            out["final_url"] = r.geturl()
            out["ct"] = r.headers.get("Content-Type", "")
            out["bytes_read"] = len(body)
            out["head"] = body[:4000].decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        out["status"] = e.code
        try:
            out["head"] = e.read(2000).decode("utf-8", "replace")
        except Exception:
            out["head"] = ""
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    results[name] = out
    print(f"[{name}] status={out.get('status')} err={out.get('error','')} ct={out.get('ct','')[:40]} bytes={out.get('bytes_read','')}")
    return out

# 1. Morocco CKAN portal count (recorded reopen trigger: > 697 datasets or new org)
probe("ma_ckan_count", "https://data.gov.ma/data/api/3/action/package_search?rows=0")

# 2. SAPS copyright page re-read (evidence dated 2026-10-21)
probe("saps_copyright", "https://www.saps.gov.za/copyright.php")
probe("saps_crimepage", "https://www.saps.gov.za/services/crimestatistics.php", maxbytes=60000)

# 3. AfDB open data platform
probe("afdb_main", "https://data.afdb.org/", maxbytes=60000)

# 4. UNECA statistical portals
probe("uneca_main", "https://www.uneca.org/", maxbytes=40000)
probe("uneca_castats", "https://ecastats.uneca.org/", maxbytes=60000)

# 5. South African national open data portal
probe("datagovza", "https://data.gov.za/", maxbytes=80000)

json.dump(results, open("africa_tick_b1.json", "w"), indent=1)
print("\nsaved africa_tick_b1.json")
