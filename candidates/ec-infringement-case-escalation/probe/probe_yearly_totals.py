#!/usr/bin/env python3
"""Aggregate probe of the EC infringement register (Themis) API.

Reads ONLY totalRows counts (bounded, no row transfer) for:
- earliest / latest decision date
- per-year totals (all categories)
- per-year totals for the procedural-stage categories LFN, RO, RTC, CLOSURES

Evidence for candidates/ec-infringement-case-escalation (discovery 2026-10-31).
"""
import json
import time
import urllib.request

URL = ("https://ec.europa.eu/implementing-eu-law/"
       "search-infringement-decisions/api/decisions")


def total(dfrom, dto, category=None, order="desc"):
    payload = {
        "refId": None, "relatedPetition": None, "petition": None,
        "decisionDateFrom": dfrom, "decisionDateTo": dto,
        "langCode": "EN", "memberState": None,
        "decisionCategory": category, "infringementType": None,
        "activeCase": None, "pressRelease": None,
        "page": 0, "size": 1, "title": None,
        "legalBasis": None, "dg": None, "policyArea": None,
        "courtFinancialSanctions": None,
        "order": order, "sortColumns": "decisionDate",
    }
    req = urllib.request.Request(
        URL, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    return d.get("totalRows"), d.get("records", [])


def main():
    # date-range sanity: does the From/To filter change the total?
    t_all, recs_desc = total(None, None)
    print(f"total (no filter): {t_all}")
    newest = recs_desc[0]["decisionDate"] if recs_desc else None
    _, recs_asc = total(None, None, order="asc")
    oldest = recs_asc[0]["decisionDate"] if recs_asc else None
    print(f"newest decision: {newest}   oldest decision: {oldest}")

    t_2025, _ = total("01/01/2025", "31/12/2025")
    print(f"total 2025 (DD/MM/YYYY format): {t_2025}")
    assert t_2025 != t_all, "date filter did not filter"

    fmt = "DD/MM/YYYY"
    print(f"date-filter format that works: {fmt}")

    results = {}
    for year in range(1996, 2027):
        row = {"year": year}
        for cat in [None, "LFN", "RO", "RTC", "CLOSURES"]:
            if fmt == "YYYY-MM-DD":
                df, dt = f"{year}-01-01", f"{year}-12-31"
            elif fmt == "DD/MM/YYYY":
                df, dt = f"01/01/{year}", f"31/12/{year}"
            else:
                break
            t, _ = total(df, dt, category=cat)
            row["ALL" if cat is None else cat] = t
            time.sleep(0.3)
        results[year] = row
        print(json.dumps(row))
        if fmt == "UNFILTERED":
            break

    with open("/opt/data/cache/scratch/iec_yearly_totals.json", "w") as f:
        json.dump(results, f, indent=1)
    print("saved /opt/data/cache/scratch/iec_yearly_totals.json")


if __name__ == "__main__":
    main()
