#!/usr/bin/env python3
"""Check whether the Themis register also exposes a case-level endpoint."""
import json
import urllib.request

BASE = ("https://ec.europa.eu/implementing-eu-law/"
        "search-infringement-decisions/api/")

BODY = {
    "refId": None, "relatedPetition": None, "petition": None,
    "decisionDateFrom": None, "decisionDateTo": None,
    "langCode": "EN", "memberState": None, "decisionCategory": None,
    "infringementType": None, "activeCase": None, "pressRelease": None,
    "page": 0, "size": 3, "title": None, "legalBasis": None, "dg": None,
    "policyArea": None, "courtFinancialSanctions": None,
    "order": "desc", "sortColumns": "decisionDate",
}


def probe(path, method="POST"):
    url = BASE + path
    try:
        if method == "POST":
            req = urllib.request.Request(
                url, data=json.dumps(BODY).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
        else:
            req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode(errors="replace")
            return r.status, body[:800]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:800]
    except Exception as e:
        return "ERR", str(e)[:300]


for path in ["cases", "case", "infringements"]:
    for method in ["POST", "GET"]:
        status, body = probe(path, method)
        print(f"{method} /api/{path} -> {status}\n{body}\n---")
