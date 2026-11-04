# Africa tick 2026-11-04: batch 6 - MapAfrica API anonymous probe (bounded: 10 rows)
import json, urllib.request, urllib.error

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research-data-probe/1.0",
      "Accept": "application/json"}

def get(name, url, maxbytes=200000, timeout=40):
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
    print(f"[{name}] {out.get('status')} err={out.get('error','')} ct={out.get('ct','')[:40]} n={out.get('n','')}")
    return out

# activities page 1, 10 rows, as the SPA itself calls it
a = get("activities", "https://mapafrica.afdb.org/api/v15/activities?lang=en&per_page=10&page=1&ascending=false&order_by=activity_date_planned_start&currency=xdr")
json.dump(a, open("africa_tick_b6_activities.json", "w"), indent=1)
if a.get("text"):
    try:
        d = json.loads(a["text"])
        print("top-level keys:", list(d.keys())[:20])
        for k in d:
            v = d[k]
            if isinstance(v, list):
                print(f"  {k}: list len={len(v)}")
                if v and isinstance(v[0], dict):
                    print("  first-row keys:")
                    for kk in sorted(v[0].keys()):
                        print(f"    {kk}: {json.dumps(v[0][kk])[:90]}")
            elif isinstance(v, dict):
                print(f"  {k}: dict {json.dumps(v)[:200]}")
            else:
                print(f"  {k}: {json.dumps(v)[:120]}")
    except Exception as e:
        print("parse error:", e, a["text"][:400])

# codelists (bounded) - may carry status vocabulary
c = get("codelists", "https://mapafrica.afdb.org/api/v15/codelists?lang=en", maxbytes=120000)
if c.get("text"):
    try:
        d = json.loads(c["text"])
        json.dump(d, open("africa_tick_b6_codelists.json", "w"), indent=1)
        def walk(o, p=""):
            if isinstance(o, dict):
                for k in o: walk(o[k], p + "/" + str(k))
            elif isinstance(o, list):
                print(f"list {p}: len={len(o)} first={json.dumps(o[0])[:100]}" if o else f"list {p}: empty")
        # print only the top-level shape
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, list):
                    print(f"codelist {k}: n={len(v)} sample={json.dumps(v[:3])[:220]}")
                else:
                    print(f"codelist {k}: {json.dumps(v)[:150]}")
    except Exception as e:
        print("codelists parse error:", e, c["text"][:300])
