# Africa tick 2026-11-04: batch 10 - registry licence first-hand + completed-row actual-end check
import json, urllib.request, urllib.error, re

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research-data-probe/1.0"}
results = {}

def get(name, url, maxbytes=250000, timeout=45):
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
    print(f"[{name}] {out.get('status')} err={out.get('error','')} final={out.get('final_url','')[:70]} n={out.get('n','')}")
    return out

# A. registry dataset page (licence field)
reg = get("reg_dataset", "http://iatiregistry.org/dataset/afdb-saotome", maxbytes=150000)
if reg.get("text"):
    t = reg["text"]
    # licence mentions
    for pat in [r'licen[cs]e[^<>]{0,220}', r'CC[ -]BY[^<>]{0,120}', r'creativecommons[^"\'<> ]*']:
        hits = re.findall(pat, t, re.I)
        print(f"  pattern {pat!r}: {hits[:6]}")
    # count of datasets by this publisher on the page if visible
    m = re.findall(r'/dataset/afdb-[a-z-]+', t)
    print("  afdb-* dataset links on page:", len(set(m)), sorted(set(m))[:60])

# B. find completed activities and check actual end dates via datastore + d-portal csv
ds = get("ds_completed_sample", "https://datastore.codeforiati.org/api/1/access/activity/?reporting-org=XM-DAC-46002&activity-status=3&limit=6", maxbytes=250000)
ids = []
if ds.get("text"):
    ids = re.findall(r'"iati-identifier": \{"text": "(46002-P-[^"]+)"', ds["text"])
    print("completed sample ids:", ids[:6])
for aid in ids[:3]:
    csvr = get(f"dp_csv_{aid[-8:]}", f"https://d-portal.org/q.csv?aid={aid}", maxbytes=250000)
    if csvr.get("text"):
        rows = [l for l in csvr["text"].splitlines() if "/activity-date" in l]
        print(f"  {aid} activity-date rows:")
        for l in rows[:8]:
            print("   ", l[:150])

json.dump(results, open("africa_tick_b10.json", "w"), indent=1)
