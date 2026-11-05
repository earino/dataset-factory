#!/usr/bin/env python3
"""UNECA ecastats API discovery (bounded, anonymous): find the API surface behind the
Vue SPA - swagger doc, indicator/dataset listing, licence/terms pages. <= 12 requests."""
import gzip
import json
import re
import time
import urllib.error
import urllib.request
import zlib

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
BASE = "https://ecastats.uneca.org"
paths = [
    "/ecastats.api/api",
    "/ecastats.api/api/",
    "/ecastats.api/swagger/index.html",
    "/ecastats.api/swagger/v1/swagger.json",
    "/ecastats.api/api/docs",
    "/ecastats.api/api/indicator",
    "/ecastats.api/api/indicators",
    "/ecastats.api/api/dataset",
    "/ecastats.api/api/datasets",
    "/ecastats.api/api/countries",
    "/ecastats.api/api/GetIndicators",
    "/data/about",
    "/data/terms",
]
out = {"probes": []}
for p in paths:
    rec = {"url": BASE + p, "t0": time.time()}
    req = urllib.request.Request(rec["url"], headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read(400_000)
            enc = (r.headers.get("Content-Encoding") or "").lower()
            if enc == "gzip":
                body = gzip.decompress(body)
            elif enc == "deflate":
                body = zlib.decompress(body)
            text = body.decode("utf-8", "replace")
            rec.update({"status": r.status, "content_type": r.headers.get("Content-Type"),
                        "bytes": len(body),
                        "head": re.sub(r"\s+", " ", text[:500])})
            if "json" in (r.headers.get("Content-Type") or "") or text[:1] in "{[":
                try:
                    j = json.loads(text)
                    rec["json_keys"] = (list(j.keys())[:12] if isinstance(j, dict)
                                        else f"list[{len(j)}]")
                    rec["json_sample"] = json.dumps(j, ensure_ascii=False)[:700]
                except Exception:
                    pass
    except urllib.error.HTTPError as e:
        rec.update({"status": e.code, "head": e.read()[:200].decode("utf-8", "replace")})
    except Exception as e:
        rec.update({"status": None, "error": f"{type(e).__name__}: {e}"})
    rec["elapsed_s"] = round(time.time() - rec["t0"], 2)
    out["probes"].append(rec)
    print(f"{p:45s} status={rec.get('status')} ct={rec.get('content_type')} "
          f"keys={rec.get('json_keys')} head={(rec.get('head') or rec.get('error') or '')[:140]!r}")
with open("/opt/data/cache/scratch/uneca_api_probe.json", "w") as fh:
    json.dump(out, fh, indent=1)
