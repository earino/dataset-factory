# Africa tick 2026-11-04: batch 9 - datastore coverage/status probes + registry licence + d-portal completed sample
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

BASE = "https://datastore.codeforiati.org/api/1/access/activity/"
RO = "reporting-org=XM-DAC-46002"

# A1. deep history: activities with planned/actual start before 1985
for nm, q in [
    ("ds_pre1985_start_lt", f"?{RO}&start-date__lt=1985-01-01&limit=1"),
    ("ds_pre2000_start_lt", f"?{RO}&start-date__lt=2000-01-01&limit=1"),
    ("ds_2010_2020", f"?{RO}&start-date__gt=2010-01-01&start-date__lt=2020-01-01&limit=1"),
]:
    r = get(nm, BASE + q)
    if r.get("text"):
        m = re.search(r'"total-count": (\d+)', r["text"])
        print("   total-count:", m.group(1) if m else "parse-fail")

# A2. status filter syntax attempts (cancelled = 5, completed = 3)
for nm, q in [
    ("ds_status5", f"?{RO}&activity-status=5&limit=1"),
    ("ds_status3", f"?{RO}&activity-status=3&limit=1"),
]:
    r = get(nm, BASE + q)
    if r.get("text"):
        m = re.search(r'"total-count": (\d+)', r["text"])
        print("   total-count:", m.group(1) if m else ("parse-fail: " + r["text"][:120]))

# B. registry publisher page via d-portal activity page link
dp = get("dp_activity", "https://d-portal.org/q.html?aid=46002-P-ST-K00-013", maxbytes=120000)
if dp.get("text"):
    links = sorted(set(re.findall(r'href="(https?://iatiregistry\.org[^"]*)"', dp["text"])))
    results["dp_registry_links"] = links
    print("registry links on d-portal page:", links[:10])

json.dump(results, open("africa_tick_b9.json", "w"), indent=1)
