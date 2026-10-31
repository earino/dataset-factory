#!/usr/bin/env python3
"""Bounded probe of the European Ombudsman search REST API.

POST /rest/legal-documents/search/{lang}?page=N with the app's own body class
(captured from chunk_CqcAHzvI.js, 2026-10-31):
{text, languageISO, caseId, docTypes, dateMin "dd_mm_yyyy", dateMax,
 institutionIds, settlementIds, topics, keys1..3,5,7, countryId}

Evidence for the eu-ombudsman-inquiry-maladministration candidate (discovery).
"""
import json
import sys
import urllib.request

BASE = "https://www.ombudsman.europa.eu/rest"


def post_search(body, page=1, lang="en"):
    url = f"{BASE}/legal-documents/search/{lang}?page={page}"
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def get(path):
    with urllib.request.urlopen(f"{BASE}/{path}", timeout=60) as r:
        return json.load(r)


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"

    if what in ("all", "ref"):
        for name, path in [("documentTypes", "documentTypes"),
                           ("eo-settlements", "eo-settlements"),
                           ("institutions", "institutions")]:
            d = get(path)
            print(f"== {name} ({len(d) if isinstance(d, list) else '?'}) ==")
            print(json.dumps(d, indent=0)[:1500])
            print()

    if what in ("all", "search"):
        # empty-ish body: docTypes empty is defaulted to ALL by the app,
        # but the REST endpoint may need it; try minimal body first
        for body in [{}, {"docTypes": ""}]:
            try:
                d = post_search(body, 1)
                print("== search", body, "==")
                print("keys:", list(d.keys()) if isinstance(d, dict) else type(d))
                print(json.dumps(d, indent=1)[:2200])
                break
            except urllib.error.HTTPError as e:
                print(f"search {body} -> HTTP {e.code}:",
                      e.read().decode(errors="replace")[:200])

    if what in ("all", "count"):
        d = post_search({}, 1)
        print("total countDtos:", d.get("countDtos"))

    if what == "yearly":
        # per-year decision counts via dateMin/dateMax (dd_mm_yyyy)
        results = {}
        for year in range(1998, 2027):
            body = {"dateMin": f"01_01_{year}", "dateMax": f"31_12_{year}"}
            try:
                d = post_search(body, 1)
                results[year] = d.get("countDtos")
                print(year, d.get("countDtos"))
            except urllib.error.HTTPError as e:
                print(year, "HTTP", e.code)
                break
        with open("/opt/data/cache/scratch/eo_yearly.json", "w") as f:
            json.dump(results, f, indent=1)


if __name__ == "__main__":
    main()
