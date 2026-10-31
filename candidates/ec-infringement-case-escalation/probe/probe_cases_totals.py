#!/usr/bin/env python3
"""Measure case-level totals of the Themis register (/api/infringements).

Bounded: reads totalRows + a handful of full case records (no bulk transfer).
Evidence for candidates/ec-infringement-case-escalation (discovery 2026-10-31).
"""
import json
import urllib.request

URL = ("https://ec.europa.eu/implementing-eu-law/"
       "search-infringement-decisions/api/infringements")

BODY = {
    "refId": None, "relatedPetition": None, "petition": None,
    "decisionDateFrom": None, "decisionDateTo": None,
    "langCode": "EN", "memberState": None, "decisionCategory": None,
    "infringementType": None, "activeCase": None, "pressRelease": None,
    "page": 0, "size": 2, "title": None, "legalBasis": None, "dg": None,
    "policyArea": None, "courtFinancialSanctions": None,
    "order": "desc", "sortColumns": "decisionDate",
}


def query(body):
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def main():
    d = query(dict(BODY))
    print("case-level totalRows:", d.get("totalRows"),
          "pageNumber:", d.get("pageNumber"), "pageSize:", d.get("pageSize"))
    print("record keys:", sorted(d["records"][0].keys()))
    print(json.dumps(d["records"][0], indent=1, sort_keys=True)[:2500])

    # active-case count as a coverage cross-check
    b = dict(BODY)
    b["activeCase"] = "true"
    d2 = query(b)
    print("active cases:", d2.get("totalRows"))

    # decision-level 1995 coverage check (earliest case seen 18/10/1995)
    b3 = {
        "refId": None, "relatedPetition": None, "petition": None,
        "decisionDateFrom": "01/01/1995", "decisionDateTo": "31/12/1995",
        "langCode": "EN", "memberState": None, "decisionCategory": None,
        "infringementType": None, "activeCase": None, "pressRelease": None,
        "page": 0, "size": 1, "title": None, "legalBasis": None, "dg": None,
        "policyArea": None, "courtFinancialSanctions": None,
        "order": "desc", "sortColumns": "decisionDate",
    }
    d3 = query(b3)
    print("1995 case-level rows (decisions in 1995):", d3.get("totalRows"))


if __name__ == "__main__":
    main()
