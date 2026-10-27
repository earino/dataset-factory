#!/usr/bin/env python3
"""Reopen-evidence probe for hc-canada-vigilance-adverse-reactions (2026-10-27).

Reproduces: package_show for 9cbaef00-b52c-4a70-9fed-d9aa8263ab74 (bulk extract
resources), a HEAD on extract_extrait.zip (size + Last-Modified), and the
health-products.canada.ca lookup-API shape. Aggregate metadata only; bulk ZIP
content is only ever touched via the bounded tail-range probe in
probe_extract_zip_tail.py.
"""
import json
import urllib.request
import urllib.parse

UA = {"User-Agent": "scout-discovery/1.0 (dataset-factory research)"}
PID = "9cbaef00-b52c-4a70-9fed-d9aa8263ab74"


def main():
    qs = urllib.parse.urlencode({"id": PID})
    with urllib.request.urlopen(urllib.request.Request(
            f"https://open.canada.ca/data/en/api/3/action/package_show?{qs}",
            headers=UA), timeout=60) as r:
        p = json.loads(r.read())["result"]
    fmts = sorted({(res.get("format") or "?").upper() for res in p.get("resources", [])})
    zip_res = [res for res in p.get("resources", []) if (res.get("format") or "").upper() == "ZIP"]
    out = {"title": p.get("title"), "license_id": p.get("license_id"),
           "metadata_modified": p.get("metadata_modified"),
           "resource_formats": fmts, "zip": []}
    for z in zip_res:
        req = urllib.request.Request(z["url"], headers=UA, method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=45) as r2:
                out["zip"].append({"url": z["url"], "status": r2.status,
                                   "size": r2.headers.get("Content-Length"),
                                   "last_modified": r2.headers.get("Last-Modified")})
        except Exception as e:
            out["zip"].append({"url": z["url"], "error": repr(e)[:150]})
    for ep in ("outcome", "reporttype", "gender"):
        url = f"https://health-products.canada.ca/api/canada-vigilance/{ep}/?lang=en&type=json"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r3:
                body = r3.read(400)
                out[f"api_{ep}"] = {"bytes_sample": len(body),
                                    "head": body[:120].decode("utf-8", "replace")}
        except Exception as e:
            out[f"api_{ep}"] = {"error": repr(e)[:150]}
    print(json.dumps(out, indent=1)[:2500])


if __name__ == "__main__":
    main()
