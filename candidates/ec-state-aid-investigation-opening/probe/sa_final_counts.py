#!/usr/bin/env python3
"""Final population + split-window measurement for the state-aid candidate.

Population: SA cases with a recorded caseNotificationDate (excludes ex-officio
cases, which have no notification instant). Per year 1995-2026:
- cases_notified (with notification date, initiated that year)
- opening_cases_notified (distinct cases with an A44 decision AND a
  notification date, initiated that year)
Split windows: train 2000-2008, eval 2009-2011, holdout 2012-2014.
"""
import json
import os
import subprocess
import tempfile

URL = ("https://webgate.ec.europa.eu/es/search-api/rest/search"
       "?text=*&pageNumber={page}&pageSize=100&apiKey=CS_PROD_ODSE_PROD")


def post(query, page=1, tries=4):
    for a in range(tries):
        with tempfile.TemporaryDirectory() as td:
            qf = os.path.join(td, "query.json")
            sf = os.path.join(td, "sort.json")
            dff = os.path.join(td, "displayFields.json")
            open(qf, "w").write(json.dumps(query))
            open(sf, "w").write('[{"field":"metadataReference","order":"ASC"}]')
            open(dff, "w").write('["caseNumber"]')
            args = ["curl", "-s", "--max-time", "60", "-X", "POST",
                    URL.format(page=page),
                    "-H", "Origin: https://competition-cases.ec.europa.eu",
                    "-H", "Referer: https://competition-cases.ec.europa.eu/",
                    "-F", f"query=@{qf};filename=blob;type=application/json",
                    "-F", f"sort=@{sf};filename=blob;type=application/json",
                    "-F", f"displayFields=@{dff};filename=blob;type=application/json"]
            out = subprocess.run(args, capture_output=True, text=True).stdout
            try:
                return json.loads(out)
            except json.JSONDecodeError:
                continue
    return {}


def cases_notified(year):
    return {"bool": {"must": [
        {"exists": {"field": "caseNumber"}},
        {"term": {"caseInstrument": "SA"}},
        {"term": {"metadataType": "METADATA_CASE"}},
        {"exists": {"field": "caseNotificationDate"}},
        {"range": {"caseInitiationDate": {
            "gte": f"{year}-01-01T00:00:00.000Z",
            "lt": f"{year + 1}-01-01T00:00:00.000Z"}}}]}}


def opening_refs_query(year, page):
    q = {"bool": {"must": [
        {"exists": {"field": "caseNumber"}},
        {"term": {"caseInstrument": "SA"}},
        {"terms": {"decisionTypes": ["DecisionTypeA44"]}},
        {"term": {"metadataType": "METADATA_DECISION"}},
        {"exists": {"field": "caseNotificationDate"}},
        {"range": {"caseInitiationDate": {
            "gte": f"{year}-01-01T00:00:00.000Z",
            "lt": f"{year + 1}-01-01T00:00:00.000Z"}}}]}}
    return q


def opening_cases(year):
    cases = set()
    page = 1
    while page <= 20:
        d = post(opening_refs_query(year, page), page=page)
        if "totalResults" not in d:
            return None
        for r in d.get("results", []):
            ref = r.get("reference") or ""
            if "-DEC" in ref:
                cases.add(ref.split("-DEC")[0])
        if page * 100 >= d["totalResults"]:
            break
        page += 1
    return len(cases)

if __name__ == "__main__":
    rows = []
    for y in range(1995, 2027):
        n = post(cases_notified(y)).get("totalResults")
        o = opening_cases(y)
        rows.append({"year": y, "notified_cases": n, "opening_cases": o})
        print(y, "notified:", n, "openings:", o, flush=True)
    with open("sa_notified_split_counts.json", "w") as f:
        json.dump(rows, f, indent=1)

    def agg(a, b, key):
        return sum((r[key] or 0) for r in rows if a <= r["year"] <= b)
    for name, a, b in (("train 2000-2008", 2000, 2008),
                        ("eval 2009-2011", 2009, 2011),
                        ("holdout 2012-2014", 2012, 2014)):
        c, o = agg(a, b, "notified_cases"), agg(a, b, "opening_cases")
        print(f"{name}: notified cases {c}, openings {o} "
              f"({100.0 * o / max(c, 1):.2f}%)")
