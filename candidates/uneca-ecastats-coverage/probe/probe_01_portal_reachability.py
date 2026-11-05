#!/usr/bin/env python3
"""Africa tick 2026-11-05 free probes (coordinator, anonymous, read-only):
1. Morocco data.gov.ma recorded re-census trigger: package_search count vs 697/699.
2. UNECA - never probed, no candidate record: ecastats.uneca.org structure,
   licence instrument, catalog grain. Bounded: <= 12 requests, no bulk download.
"""
import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.request
import zlib

OUT = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "probes": []}
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def fetch(url, max_bytes=900_000, timeout=25):
    rec = {"url": url, "t0": time.time()}
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(max_bytes)
            enc = (r.headers.get("Content-Encoding") or "").lower()
            if enc == "gzip":
                body = gzip.decompress(body)
            elif enc == "deflate":
                body = zlib.decompress(body)
            text = body.decode("utf-8", "replace")
            rec.update({"status": r.status, "final_url": r.geturl(),
                        "content_type": r.headers.get("Content-Type"),
                        "bytes": len(body), "elapsed_s": round(time.time() - rec["t0"], 2)})
            rec["text"] = text if len(text) < 400_000 else text[:400_000]
    except urllib.error.HTTPError as e:
        rec.update({"status": e.code, "error": f"HTTP {e.code}",
                    "head": e.read()[:200].decode("utf-8", "replace")})
    except Exception as e:
        rec.update({"status": None, "error": f"{type(e).__name__}: {e}"})
    OUT["probes"].append(rec)
    return rec


def title_of(text):
    m = re.search(r"<title[^>]*>(.*?)</title>", text or "", re.S | re.I)
    return re.sub(r"\s+", " ", m.group(1)).strip()[:160] if m else None


print("== 1. Morocco data.gov.ma re-census trigger ==")
ma = fetch("https://data.gov.ma/data/api/3/action/package_search?q=&rows=0")
if ma.get("text"):
    try:
        j = json.loads(ma["text"])
        count = j.get("result", {}).get("count")
        print(f"package_search count = {count}  (censused 697 on 2026-10-23; 699 on 2026-10-30)")
        OUT["morocco_count"] = count
    except Exception as e:
        print("parse error:", e, "| head:", (ma.get("text") or "")[:200])
else:
    print("fetch failed:", ma.get("error"), ma.get("status"))

print("\n== 2. UNECA ecastats (never probed) ==")
for url in ("https://ecastats.uneca.org/",
            "https://ecastats.uneca.org/data",
            "https://ecastats.uneca.org/data/",
            "https://www.uneca.org/data",
            "https://data.uneca.org/"):
    r = fetch(url)
    print(f"{url} -> status={r.get('status')} final={r.get('final_url')} title={title_of(r.get('text'))!r}")

# inspect the /data page for structure: API hints, dataset links, licence text
dpage = next((p for p in OUT["probes"] if p.get("final_url", "").endswith("/data") and p.get("text")), None)
if dpage:
    t = dpage["text"]
    links = re.findall(r'href="([^"]+)"', t)
    api_like = [l for l in links if any(k in l.lower() for k in ("api", "sdmx", "download", "export", "csv", "metadata"))]
    lic = [l for l in links if any(k in l.lower() for k in ("licence", "license", "terms", "disclaimer", "copyright", "about"))]
    print("api-like links (first 10):", api_like[:10])
    print("licence-ish links (first 10):", lic[:10])
    m = re.findall(r"(?:licen[cs]e|copyright|terms of use|disclaimer)[^<]{0,200}", t, re.I)
    print("licence-ish text snippets (first 5):", [x[:160] for x in m[:5]])
    # dataset/indicator product links
    prod = [l for l in links if re.search(r"/(data|dataset|indicator|series|browse)", l, re.I)]
    print("product links (first 15):", prod[:15])

print("\nJSON saved to afdb-region-probe out file")
with open("/opt/data/cache/scratch/africa_tick_2026_11_05_region_probes.json", "w") as fh:
    json.dump(OUT, fh, indent=1)
print(json.dumps({k: v for k, v in OUT.items() if k != "probes"}, indent=1))
