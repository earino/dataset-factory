#!/usr/bin/env python3
"""Exact case-level positive counts: distinct case numbers with at least one
DecisionTypeA44 (108(2) formal investigation opening) decision, per case
initiation year, via the publisher's public search API.

Pages METADATA_DECISION docs per year (displayFields=[caseNumber]) and counts
DISTINCT case numbers. Bounded: <=~2 pages of 100 per year, tiny payloads.
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


def year_query(year):
    return {"bool": {"must": [
        {"exists": {"field": "caseNumber"}},
        {"term": {"caseInstrument": "SA"}},
        {"terms": {"decisionTypes": ["DecisionTypeA44"]}},
        {"term": {"metadataType": "METADATA_DECISION"}},
        {"range": {"caseInitiationDate": {
            "gte": f"{year}-01-01T00:00:00.000Z",
            "lt": f"{year + 1}-01-01T00:00:00.000Z"}}}]}}


def distinct_cases(year):
    cases = set()
    page = 1
    pages_seen = 0
    while page <= 40:
        d = post(year_query(year), page=page)
        if "totalResults" not in d:
            return None, 0
        for r in d.get("results", []):
            ref = r.get("reference") or ""
            if "-DEC" in ref:
                cases.add(ref.split("-DEC")[0])
        pages_seen += 1
        total = d["totalResults"]
        if page * 100 >= total:
            break
        page += 1
    return len(cases), pages_seen


if __name__ == "__main__":
    out_rows = []
    for y in range(1993, 2027):
        n, pages = distinct_cases(y)
        out_rows.append({"year": y, "opening_cases": n})
        print(y, "distinct opening cases:", n, f"({pages}p)", flush=True)
    with open("sa_opening_cases_exact.json", "w") as f:
        json.dump(out_rows, f, indent=1)
    tot = sum(r["opening_cases"] or 0 for r in out_rows)
    print("TOTAL distinct opening cases 1993-2026:", tot)
