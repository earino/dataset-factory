# Aggregate probe over the unified Saber 11 table (kgxf-xxbe) on datos.gov.co.
# Server-side aggregates only: rows per periodo, punt_global availability, calendar mix.
# Usage: python3 probe_period_coverage.py
import csv
import io
import json
import sys
import urllib.parse
import urllib.request

BASE = "https://www.datos.gov.co/resource/kgxf-xxbe.json"
UA = {"User-Agent": "dataset-factory-discovery-probe"}


def soql(params):
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def main():
    out = {}

    # 1. rows per periodo
    rows = soql({
        "$select": "periodo,count(*) as n",
        "$group": "periodo",
        "$order": "periodo",
        "$limit": "100",
    })
    out["rows_per_periodo"] = rows
    print("rows per periodo:")
    for r in rows:
        print("  ", r)

    # 2. punt_global availability per periodo (non-null count, and parseable as number)
    rows = soql({
        "$select": "periodo,count(*) as n,count(punt_global) as n_score",
        "$where": "punt_global IS NOT NULL",
        "$group": "periodo",
        "$order": "periodo",
        "$limit": "100",
    })
    out["punt_global_per_periodo"] = rows
    print("punt_global non-null per periodo:")
    for r in rows:
        print("  ", r)

    # 3. calendar mix per periodo among rows with a score
    rows = soql({
        "$select": "periodo,cole_calendario,count(*) as n",
        "$where": "punt_global IS NOT NULL",
        "$group": "periodo,cole_calendario",
        "$order": "periodo",
        "$limit": "300",
    })
    out["calendar_mix_per_periodo"] = rows
    print("calendar mix among scored rows:")
    for r in rows:
        print("  ", r)

    json.dump(out, open("period_coverage.json", "w"), indent=1)
    print("wrote period_coverage.json")


if __name__ == "__main__":
    main()
