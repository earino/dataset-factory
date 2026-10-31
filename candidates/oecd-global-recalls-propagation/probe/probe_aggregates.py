#!/usr/bin/env python3
"""Probe recipe: OECD GlobalRecalls portal aggregate coverage (discovery 2026-10-31).

Reproduces the two anonymous read-only GETs that the portal's own public UI issues on
load (dashboard aggregates + one 4-row sample page with facet lists). Prints the total
notice count, the per-jurisdiction coverage mix, and the sample-record field names.
No bulk transfer: ~16.8 KB + ~246 KB in two requests.

Usage: python3 probe_aggregates.py
"""
import json
import urllib.request

BASE = "https://globalrecalls.oecd.org/ws"
UA = {"User-Agent": "dataset-factory-discovery-probe/1.0 (bounded aggregate read)"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main():
    dash = json.loads(get(f"{BASE}/mainDashboards.xqy?q=&lang=en"))
    search = json.loads(get(f"{BASE}/search.xqy?q=&start=1&end=5&lang=en&uiLang=en"))

    print("dashboards:", [a["id"] for a in dash.get("aggregations", [])])
    print("generated:", search.get("date"))
    print("TOTAL notices:", search.get("total"))
    print("copyright line served with data:", search.get("copyright"))

    facet = search["facets"]["country-were-recalled"]["facetValues"]
    total = search.get("total") or 0
    top5 = sum(v["count"] for v in facet[:5])
    print(f"jurisdictions in country facet: {len(facet)}")
    print(f"top-5 share: {top5}/{total} = {top5/total:.1%}")
    small = [v for v in facet if v["count"] < 100]
    print(f"jurisdictions with <100 lifetime notices: {len(small)}")
    print("mix:", [(v["name"], v["count"]) for v in facet])

    rows = search.get("results") or []
    print("sample rows returned:", len(rows))
    if rows:
        print("sample record fields:", sorted(rows[0].keys()))
        print("sample record date values:", [r.get("date") for r in rows])


if __name__ == "__main__":
    main()
