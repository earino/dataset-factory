#!/usr/bin/env python3
"""Dated-example fixture probe for case 483/2024/PVV (European Ombudsman).

Fetches the case's published documents (bounded) to pin the opening-summary
publication date vs dateOpened, and the decision date vs dateClosed.
Evidence for candidates/eu-ombudsman-inquiry-outcome (discovery 2026-10-31).
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
    # caseId goes in with '/' replaced by '_' (setCaseId in the app bundle)
    d = search({"caseId": "483_2024_PVV"})
    print("countDtos:", d.get("countDtos"))
    for rec in d.get("listDtos", []):
        vc = rec.get("docVersionContent", {})
        print(rec.get("documentClass"),
              "|", rec.get("documentDate"),
              "|", (vc.get("title") or "")[:80])


if __name__ == "__main__":
    main()
