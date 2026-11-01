#!/usr/bin/env python3
"""Decompose the A44 (108(2) opening) matches: case docs vs decision docs,
per year, to get the true case-level positive counts."""
import json
import os
import subprocess
import tempfile

URL = ("https://webgate.ec.europa.eu/es/search-api/rest/search"
       "?text=*&pageNumber=1&pageSize=20&apiKey=CS_PROD_ODSE_PROD")


def post(query):
    with tempfile.TemporaryDirectory() as td:
        qf = os.path.join(td, "query.json")
        sf = os.path.join(td, "sort.json")
        dff = os.path.join(td, "displayFields.json")
        open(qf, "w").write(json.dumps(query))
        open(sf, "w").write('[{"field":"caseLastDecisionDate","order":"DESC"}]')
        open(dff, "w").write('["metadataReference","caseNumber","caseInitiationDate","decisionTypes"]')
        args = ["curl", "-s", "--max-time", "60", "-X", "POST", URL,
                "-H", "Origin: https://competition-cases.ec.europa.eu",
                "-H", "Referer: https://competition-cases.ec.europa.eu/",
                "-F", f"query=@{qf};filename=blob;type=application/json",
                "-F", f"sort=@{sf};filename=blob;type=application/json",
                "-F", f"displayFields=@{dff};filename=blob;type=application/json"]
        out = subprocess.run(args, capture_output=True, text=True).stdout
        d = json.loads(out)
        return d


def q(year, mtype=None):
    must = [
        {"exists": {"field": "caseNumber"}},
        {"term": {"caseInstrument": "SA"}},
        {"terms": {"decisionTypes": ["DecisionTypeA44"]}},
        {"range": {"caseInitiationDate": {
            "gte": f"{year}-01-01T00:00:00.000Z",
            "lt": f"{year + 1}-01-01T00:00:00.000Z"}}}]
    if mtype:
        must.append({"term": {"metadataType": mtype}})
    return {"bool": {"must": must}}


if __name__ == "__main__":
    for y in (2004, 2011, 2019, 2021):
        anydoc = post(q(y))
        cases = post(q(y, "METADATA_CASE"))
        decs = post(q(y, "METADATA_DECISION"))
        sample = [r.get("reference") for r in (anydoc.get("results") or [])[:3]]
        print(y, "any:", anydoc.get("totalResults"),
              "case-docs:", cases.get("totalResults"),
              "decision-docs:", decs.get("totalResults"),
              "sample refs:", sample)
    # also 1993-2026 whole-period case-docs count
    whole = {"bool": {"must": [
        {"exists": {"field": "caseNumber"}},
        {"term": {"caseInstrument": "SA"}},
        {"terms": {"decisionTypes": ["DecisionTypeA44"]}},
        {"term": {"metadataType": "METADATA_CASE"}}]}}
    print("whole-period case-docs with A44:", post(whole).get("totalResults"))
    whole_dec = {"bool": {"must": [
        {"exists": {"field": "caseNumber"}},
        {"term": {"caseInstrument": "SA"}},
        {"terms": {"decisionTypes": ["DecisionTypeA44"]}},
        {"term": {"metadataType": "METADATA_DECISION"}}]}}
    print("whole-period decision-docs with A44:", post(whole_dec).get("totalResults"))
