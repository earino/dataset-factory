#!/usr/bin/env python3
"""Bounded probe of the EC infringement register (Themis) public JSON API.

POST /implementing-eu-law/search-infringement-decisions/api/decisions
Captured from the publisher's own search app (browser, 2026-10-31).
Usage: probe_api_decisions.py [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--size N]
                              [--category X] [--active true|false] [--out FILE]
"""
import argparse
import json
import sys
import urllib.request

URL = ("https://ec.europa.eu/implementing-eu-law/"
       "search-infringement-decisions/api/decisions")


def query(payload):
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="dfrom", default=None)
    ap.add_argument("--to", dest="dto", default=None)
    ap.add_argument("--size", type=int, default=3)
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--category", default=None,
                    help="decisionCategory value")
    ap.add_argument("--active", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    payload = {
        "refId": None, "relatedPetition": None, "petition": None,
        "decisionDateFrom": args.dfrom, "decisionDateTo": args.dto,
        "langCode": "EN", "memberState": None,
        "decisionCategory": args.category, "infringementType": None,
        "activeCase": args.active, "pressRelease": None,
        "page": args.page, "size": args.size, "title": None,
        "legalBasis": None, "dg": None, "policyArea": None,
        "courtFinancialSanctions": None,
        "order": "desc", "sortColumns": "decisionDate",
    }
    d = query(payload)
    out = json.dumps(d, indent=1, sort_keys=True)
    if args.out:
        with open(args.out, "w") as f:
            f.write(out)
    print(out[:4000])


if __name__ == "__main__":
    sys.exit(main())
