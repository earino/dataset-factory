# Africa tick 2026-11-04: batch 8 - IATI datastore coverage queries for AfDB (XM-DAC-46002)
import json, urllib.request, urllib.error

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research-data-probe/1.0"}
results = {}

def get(name, url, maxbytes=200000, timeout=45):
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

# community datastore rebuild
get("ds_count", "https://datastore.codeforiati.org/api/1/access/activity/?reporting-org=XM-DAC-46002&limit=1")
get("ds_by_year", "https://datastore.codeforiati.org/api/1/access/activity/by_year/?reporting-org=XM-DAC-46002&limit=80")
get("ds_by_status", "https://datastore.codeforiati.org/api/1/access/activity/by_activity_status/?reporting-org=XM-DAC-46002&limit=20")
# registry publisher page slugs to try
for slug in ["african-development-bank", "afdb", "XM-DAC-46002"]:
    get(f"reg_{slug}", f"https://iatiregistry.org/publisher/{slug}", maxbytes=60000)

json.dump(results, open("africa_tick_b8.json", "w"), indent=1)
for k in ("ds_count", "ds_by_year", "ds_by_status"):
    t = results.get(k, {}).get("text", "")
    print(f"\n--- {k} ---")
    print(t[:2500])
