#!/usr/bin/env python3
"""Aggregate measurement probe: European Ombudsman inquiries (REST API).

Bounded: reads countDtos only (page 1); never fetches the full corpus.
Phases:
  1. all-time counts by doc type (EODECISION, EOOPENINGSUMMARY, ...)
  2. per-year EODECISION and EOOPENINGSUMMARY counts 1998-2026
  3. settlement mix on EODECISION (all time)
  4. grouped outcome counts in 5-year windows (maladministration group,
     no-finding group, resolved-with-action group, other/withdrawn group)
Evidence for the eu-ombudsman-inquiry-outcome candidate, 2026-10-31.
"""
import json
import time
import urllib.request

BASE = "https://www.ombudsman.europa.eu/rest/legal-documents/search/en?page=1"

DOC_TYPES = ["EODECISION", "EOOPENINGSUMMARY", "EOSOLUTION",
             "EODRAFTRECOMMENDATION", "EOSPECIALREPORT", "EOCASEDESCRIPTION"]

SETTLEMENTS = {
    "nmf": 1, "dbc": 2, "sbi": 3, "frs": 4, "crr": 5, "drai": 6, "oth": 7,
    "casr": 8, "drpai": 9, "nfij": 10, "dwc": 11, "sai": 12, "spai": 13,
    "rpai": 14, "sa": 16, "spa": 17, "ma": 18, "rai": 19,
    "solution-rejected": 20, "recommendation-rejected": 21,
    "suggestion-rejected": 22,
}

GROUPS = {
    "maladministration_established(ma+crr+recRej)": "18,5,21",
    "no_maladministration(nmf+nfij)": "1,10",
    "resolved_with_action(sa+spa+sai+spai+sbi+frs+drai+drpai+rai+rpai)":
        "16,17,12,13,3,4,6,9,19,14",
    "withdrawn_or_court(dbc+dwc+oth+casr+solRej+sugRej)": "2,11,7,8,20,22",
}


def search(body):
    req = urllib.request.Request(
        BASE, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def count(body):
    return search(body).get("countDtos")


def main():
    out = {}

    print("== phase 1: all-time counts by doc type ==")
    out["by_doctype"] = {}
    for dt in DOC_TYPES:
        c = count({"docTypes": dt})
        out["by_doctype"][dt] = c
        print(f"  {dt}: {c}")
        time.sleep(0.3)

    print("== phase 2: per-year EODECISION / EOOPENINGSUMMARY ==")
    out["per_year"] = {}
    for year in range(1998, 2027):
        dmin, dmax = f"01_01_{year}", f"31_12_{year}"
        dec = count({"docTypes": "EODECISION", "dateMin": dmin, "dateMax": dmax})
        op = count({"docTypes": "EOOPENINGSUMMARY", "dateMin": dmin,
                    "dateMax": dmax})
        out["per_year"][year] = {"decisions": dec, "opened": op}
        print(f"  {year}: decisions={dec} opened={op}")
        time.sleep(0.3)

    print("== phase 3: settlement mix on EODECISION (all time) ==")
    out["settlement_mix_alltime"] = {}
    for key, tech in SETTLEMENTS.items():
        c = count({"docTypes": "EODECISION", "settlementIds": str(tech)})
        out["settlement_mix_alltime"][key] = c
        print(f"  {key}: {c}")
        time.sleep(0.3)

    print("== phase 4: grouped outcomes in 5-year windows (EODECISION) ==")
    out["group_windows"] = {}
    windows = [(1998, 2002), (2003, 2007), (2008, 2012), (2013, 2017),
               (2018, 2022), (2023, 2026)]
    for gname, ids in GROUPS.items():
        out["group_windows"][gname] = {}
        for lo, hi in windows:
            c = count({"docTypes": "EODECISION", "settlementIds": ids,
                       "dateMin": f"01_01_{lo}", "dateMax": f"31_12_{hi}"})
            out["group_windows"][gname][f"{lo}-{hi}"] = c
            print(f"  {gname} {lo}-{hi}: {c}")
            time.sleep(0.3)

    with open("/opt/data/cache/scratch/eo_measures.json", "w") as f:
        json.dump(out, f, indent=1)
    print("saved /opt/data/cache/scratch/eo_measures.json")


if __name__ == "__main__":
    main()
