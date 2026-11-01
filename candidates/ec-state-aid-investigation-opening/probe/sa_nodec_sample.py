#!/usr/bin/env python3
"""Label-reliability probe: sample 2011-initiated SA cases that have NO
caseLastDecisionDate in the register, list their numbers/categories, so they
can be checked against the live register / public record for formal
investigations the dump might have missed."""
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


def nodec_query(year):
    return {"bool": {
        "must": [
            {"exists": {"field": "caseNumber"}},
            {"term": {"caseInstrument": "SA"}},
            {"term": {"metadataType": "METADATA_CASE"}},
            {"range": {"caseInitiationDate": {
                "gte": f"{year}-01-01T00:00:00.000Z",
                "lt": f"{year + 1}-01-01T00:00:00.000Z"}}}],
        "must_not": [{"exists": {"field": "caseLastDecisionDate"}}]}}


if __name__ == "__main__":
    for year in (2011, 2004):
        d = post(nodec_query(year))
        refs = [r["reference"] for r in d.get("results", [])][:60]
        print(year, "no-decision cases totalResults:", d.get("totalResults"))
        print("  sample:", refs[:20])
