# Africa tick 2026-11-04: batch 11 - diagnose datastore JSON shape + registry via compat API
import json, urllib.request, urllib.error, re

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research-data-probe/1.0"}
results = {}

def get(name, url, maxbytes=300000, timeout=45):
    out = {"url": url}
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(maxbytes)
            out["status"] = r.status
            out["final_url"] = r.geturl()
            out["ct"] = r.headers.get("Content-Type", "")
            out["n"] = len(body)
            out["text"] = body.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        out["status"] = e.code
        try:
            out["text"] = e.read(3000).decode("utf-8", "replace")
        except Exception:
            out["text"] = ""
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    results[name] = out
    print(f"[{name}] {out.get('status')} err={out.get('error','')} n={out.get('n','')}")
    return out

# A. datastore: dump the raw JSON of 3 completed activities, find where iati-identifier lives
ds = get("ds_completed", "https://datastore.codeforiati.org/api/1/access/activity/?reporting-org=XM-DAC-46002&activity-status=3&limit=3", maxbytes=300000)
ids = []
if ds.get("text"):
    ids = re.findall(r'(46002-P-[A-Z0-9-]+)', ds["text"])
    print("46002-P ids found:", sorted(set(ids))[:10])
    # show a window around the first occurrence
    i = ds["text"].find("46002-P-")
    print("\nCONTEXT around first id:\n", ds["text"][max(0,i-600):i+200])

# B. registry via CKAN compat API
for nm, u in [
    ("reg_show", "https://iatiregistry.org/api/3/action/package_show?id=afdb-saotome"),
    ("reg_show_http", "http://iatiregistry.org/api/3/action/package_show?id=afdb-saotome"),
]:
    r = get(nm, u)
    if r.get("text"):
        print(" body:", r["text"][:600])

json.dump(results, open("africa_tick_b11.json", "w"), indent=1)
