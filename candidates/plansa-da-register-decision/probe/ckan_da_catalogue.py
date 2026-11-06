#!/usr/bin/env python3
"""Catalogue probe for plansa-da-register-decision (2026-11-06).

Reproduces the data.gov.au / data.sa.gov.au catalogue sweep that found the SA
Development Application Public Register and its AU comparators. Anonymous
package_search only; prints licence metadata and resource URLs; fetches no
bulk data. package_show on data.gov.au 302s to HTML - use package_search.
"""
import json
import urllib.parse
import urllib.request

UA = {"User-Agent": "dataset-factory-discovery/1.0"}
AU_SEARCH = "https://data.gov.au/data/api/3/action/package_search"
SA_SHOW = "https://data.sa.gov.au/data/api/3/action/package_show?id="


def package_search(query, rows=8):
    url = AU_SEARCH + "?" + urllib.parse.urlencode({"q": query, "rows": rows})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)["result"]


def show(d):
    print(f"  {d.get('name')} | {d.get('license_id')} / {d.get('license_title')}")
    print(f"    org={(d.get('organization') or {}).get('title')}")
    print(f"    notes={(d.get('notes') or '')[:200]}")
    for res in d.get("resources", [])[:6]:
        print(f"    res: {res.get('name','?')[:50]} | fmt={res.get('format')} | {res.get('url','')[:110]}")


def main():
    print("== data.gov.au: DA / permit register sweep ==")
    for q in ["development applications", "resource consents", "building permit"]:
        print(f'## q="{q}" count={package_search(q, 0)["count"]}')
        for d in package_search(q)["results"]:
            if any(k in (d.get("name") or "") for k in
                   ("development", "permit", "pcc")):
                show(d)
    print("\n== data.sa.gov.au: the SA record ==")
    req = urllib.request.Request(SA_SHOW + "development-application-public-register", headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)["result"]
    print(f"  {d.get('title')} | {d.get('license_id')} / {d.get('license_title')}")
    for res in d.get("resources", []):
        print(f"    res: {res.get('name','?')[:60]} | {res.get('url','')}")


if __name__ == "__main__":
    main()
