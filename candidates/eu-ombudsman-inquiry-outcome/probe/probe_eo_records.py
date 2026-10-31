#!/usr/bin/env python3
"""Fetch one EOOPENINGSUMMARY and one EODECISION record (bounded, 2 pages of 1-ish
results) to record what fields the publisher exposes at each document class.

Evidence for the eu-ombudsman-inquiry-outcome candidate, 2026-10-31.
"""
import json
import urllib.request

BASE = "https://www.ombudsman.europa.eu/rest/legal-documents/search/en?page=1"


def search(body):
    req = urllib.request.Request(
        BASE, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def main():
    for label, body in [
        ("EOOPENINGSUMMARY (2024)", {"docTypes": "EOOPENINGSUMMARY",
                                      "dateMin": "01_01_2024",
                                      "dateMax": "31_12_2024"}),
        ("EODECISION (2024)", {"docTypes": "EODECISION",
                               "dateMin": "01_01_2024",
                               "dateMax": "31_12_2024"}),
    ]:
        d = search(body)
        print(f"== {label}: countDtos={d.get('countDtos')} ==")
        if d.get("listDtos"):
            rec = d["listDtos"][0]
            print(json.dumps(rec, indent=1, sort_keys=True)[:3500])
        print()

    # settlement filter sanity: EODECISION with maladministration-found
    d = search({"docTypes": "EODECISION", "settlementIds": "18",
                "dateMin": "01_01_2023", "dateMax": "31_12_2023"})
    print("EODECISION 2023 settlement=ma:", d.get("countDtos"))
    d = search({"docTypes": "EODECISION", "settlementIds": "1",
                "dateMin": "01_01_2023", "dateMax": "31_12_2023"})
    print("EODECISION 2023 settlement=nmf:", d.get("countDtos"))


if __name__ == "__main__":
    main()
