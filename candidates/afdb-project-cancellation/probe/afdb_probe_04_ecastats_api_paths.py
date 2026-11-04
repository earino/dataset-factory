# Africa tick 2026-11-04: batch 4 - ecastats API discovery
import json, urllib.request, urllib.error, re

results = {}
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
      "Accept": "application/json, text/plain, */*", "Referer": "https://ecastats.uneca.org/data"}

def probe(name, url, maxbytes=80000, timeout=40, method="GET", data=None, ctype=None):
    out = {"url": url, "method": method}
    h = dict(UA)
    if ctype: h["Content-Type"] = ctype
    try:
        req = urllib.request.Request(url, headers=h, method=method,
                                     data=(json.dumps(data).encode() if (data is not None and method == "POST") else None))
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(maxbytes)
            out["status"] = r.status
            out["ct"] = r.headers.get("Content-Type", "")
            out["n"] = len(body)
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
    print(f"[{name}] {out.get('status')} err={out.get('error','')} ct={out.get('ct','')[:40]} n={out.get('n','')}")
    return out

base = "https://ecastats.uneca.org/ecastats.api/api"
probe("api_root", base + "/")
probe("api_docs", base + "/docs")
probe("api_swagger", base + "/swagger")
probe("api_swagger_json", base + "/swagger/index.html")
probe("api_openapi", base + "/openapi.json")
probe("api_meta", base + "/meta")
probe("api_v1", base + "/v1")
probe("api_datasets", base + "/datasets")
probe("api_indicators", base + "/indicators")
probe("api_countries", base + "/countries")
probe("api_series", base + "/series")
# the underlying server may expose swagger at the service root
probe("svc_root", "https://ecastats.uneca.org/ecastats.api/")
probe("svc_swagger", "https://ecastats.uneca.org/ecastats.api/swagger/index.html")

json.dump(results, open("africa_tick_b4.json", "w"), indent=1)
print("\n--- bodies of anything that answered ---")
for k, v in results.items():
    if v.get("status") and v.get("status") != 404 and v.get("body"):
        print(f"== {k} ({v['status']}) ==")
        print(v["body"][:1500])
        print()
