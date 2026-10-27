#!/usr/bin/env python3
"""Reproduce the data.europa.eu catalogue evidence for the RASFF dataset
recorded in candidates/rasff-notification-risk-decision/record.json
(2026-10-27): the official DG SANTE 'Food and Feed Alert Notifications'
record (restored_rasff) and the catalogue sweep that found no official
machine-readable EC infringement-register dataset. Run from anywhere.
"""
import json
import urllib.parse
import urllib.request

UA = {
    "User-Agent": "scout-dataset-factory/1.0 (dataset discovery)",
    "Accept": "application/json",
}


def search(q, limit=8):
    url = ("https://data.europa.eu/api/hub/search/search"
           f"?q={urllib.parse.quote(q)}&limit={limit}")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r).get("result", {}).get("results", [])


def main():
    d = json.load(urllib.request.urlopen(urllib.request.Request(
        "https://data.europa.eu/api/hub/search/datasets/restored_rasff",
        headers=UA), timeout=40))["result"]
    print("== restored_rasff:", (d.get("title") or {}).get("en"))
    print("   publisher:", (d.get("publisher") or {}).get("name"))
    print("   issued:", d.get("issued"), "modified:", d.get("modified"))
    for dist in d.get("distributions", []):
        print("   dist:", json.dumps({
            "title": (dist.get("title") or {}).get("en"),
            "format": (dist.get("format") or {}).get("id"),
            "url": (dist.get("access_url") or [None])[0],
            "licence": dist.get("licence"),
        }, ensure_ascii=False)[:300])

    print("\n== catalogue sweep: no official machine-readable EC infringement register")
    for q in ("infringement procedure member states register decisions",
              "infringement decisions Commission reasoned opinion",
              "infringements of Union law dataset"):
        res = search(q)
        print(f"   '{q}': {len(res)} hits, top titles:")
        for it in res[:4]:
            t = it.get("title", {})
            print("     -", (t.get("en") or next(iter(t.values()), "?"))[:80],
                  "| pub:", str((it.get("publisher") or {}).get("name"))[:40])


if __name__ == "__main__":
    main()
