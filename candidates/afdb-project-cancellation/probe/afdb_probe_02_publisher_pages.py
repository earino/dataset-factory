# Africa tick 2026-11-04: batch 2 - AfDB portals, UNECA ecastats/data, SAPS terms re-read
import json, urllib.request, urllib.error, ssl

results = {}
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
      "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8"}

def probe(name, url, maxbytes=120000, timeout=30):
    out = {"url": url}
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(maxbytes)
            out["status"] = r.status
            out["final_url"] = r.geturl()
            out["ct"] = r.headers.get("Content-Type", "")
            out["bytes_read"] = len(body)
            out["body"] = body.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        out["status"] = e.code
        try:
            out["body"] = e.read(4000).decode("utf-8", "replace")
        except Exception:
            out["body"] = ""
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    results[name] = out
    print(f"[{name}] status={out.get('status')} err={out.get('error','')} ct={out.get('ct','')[:40]} bytes={out.get('bytes_read','')}")
    return out

probe("afdb_projects", "https://projectsportal.afdb.org/")
probe("afdb_aih_dataportal", "https://dataportal.opendataforafrica.org/")
probe("africadata", "https://africadata.org/")
probe("uneca_data", "https://ecastats.uneca.org/data")
probe("saps_copyright_curl", "https://www.saps.gov.za/copyright.php", maxbytes=30000)

json.dump(results, open("africa_tick_b2.json", "w"), indent=1)
print("\nsaved africa_tick_b2.json")
