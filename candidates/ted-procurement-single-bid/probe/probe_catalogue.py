#!/usr/bin/env python3
"""Reproduce the data.europa.eu catalogue evidence for the TED CSV subset
recorded in candidates/ted-procurement-single-bid/record.json (2026-10-27):
dataset records (publisher, distributions), the ted-csv description, and the
zip sizes via ranged GET (HEAD is refused with 401). Run from anywhere.
"""
import json
import urllib.request

UA = {
    "User-Agent": "scout-dataset-factory/1.0 (dataset discovery)",
    "Accept": "application/json",
    "From": "scout@nousresearch.com",
}


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)["result"]


def main():
    for ds_id in ("ted-1", "ted-csv"):
        d = get_json(f"https://data.europa.eu/api/hub/search/datasets/{ds_id}")
        print(f"== {ds_id}: {(d.get('title') or {}).get('en')}")
        print("   publisher:", (d.get("publisher") or {}).get("name"))
        print("   access_right:", (d.get("access_right") or {}).get("label"))
        print("   issued:", d.get("issued"), "modified:", d.get("modified"))
        if ds_id == "ted-csv":
            print("   description:", (d.get("description") or {}).get("en", "")[:1200])
        for dist in d.get("distributions", [])[:60]:
            t = (dist.get("title") or {}).get("en") or ""
            if any(y in t for y in
                   ("2022", "2023", "2018-2023", "deprecated")) or "VEAT" in t:
                print("   dist:", json.dumps({
                    "title": t[:70],
                    "format": (dist.get("format") or {}).get("id"),
                    "url": (dist.get("access_url") or [None])[0],
                    "licence": dist.get("licence"),
                }, ensure_ascii=False)[:240])

    print("\n== zip sizes via ranged GET (HEAD -> 401)")
    for fn in ("ted-contract-notices-2023.zip",
               "ted-contract-award-notices-2023.zip",
               "ted-contract-award-notices-2022.zip"):
        url = f"https://data.europa.eu/api/hub/store/data/{fn}"
        req = urllib.request.Request(url, headers={**UA, "Range": "bytes=0-0"})
        with urllib.request.urlopen(req, timeout=40) as r:
            print(f"   {fn}: total={r.headers.get('Content-Range', '?').split('/')[-1]}"
                  f" bytes (HTTP {r.status})")


if __name__ == "__main__":
    main()
