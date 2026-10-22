#!/usr/bin/env python3
"""Follow-up probes on the IEG ratings CSV + projects API join.

1. Identify the duplicated project_id and its rows.
2. FCS-status vintage: does country_fcs_status differ WITHIN (country, approval_fy)?
   If yes the column is row-specific (as-of-eval?), i.e. NOT knowable at approval.
3. Projects API join: sample project_ids, check approval-time fields exist, and
   measure max page size / CSV support for a bulk-pull cost estimate.
Stdlib only (urllib). Prints compact output.
"""
import csv
import json
import sys
import urllib.request
from collections import defaultdict, Counter

PATH = sys.argv[1] if len(sys.argv) > 1 else "ieg_test.csv"
rows = list(csv.DictReader(open(PATH, newline="", encoding="utf-8")))

# 1. duplicated project_id
byid = defaultdict(list)
for r in rows:
    byid[r["project_id"]].append(r)
dups = {k: v for k, v in byid.items() if len(v) > 1}
print("duplicated project_ids:", list(dups))
for k, v in dups.items():
    for r in v:
        print(" ", k, r["project_name"][:40], "| eval_fy", r["evaluation_fy"],
              "| type", r["evaluation_type"], "| outcome", r["outcome"],
              "| approval_fy", r["approval_fy"])

# 2. FCS vintage within (country, approval_fy)
cy = defaultdict(set)
for r in rows:
    a = int(r["approval_fy"]) if r["approval_fy"] else None
    if a:
        cy[(r["country"], a)].add(r["country_fcs_status"])
multi = {k: v for k, v in cy.items() if len(v) > 1}
print(f"(country,approval_fy) cells: {len(cy)}, cells with >1 distinct fcs_status: {len(multi)}")
for k, v in list(multi.items())[:5]:
    print("  ", k, sorted(v))

# does fcs_status correlate with evaluation_fy within same country-year? take one cell
if multi:
    k = next(iter(multi))
    same = [r for r in rows if (r["country"], int(r["approval_fy"])) == k]
    for r in same:
        print("  cell detail:", r["project_id"], "eval_fy", r["evaluation_fy"], "fcs", r["country_fcs_status"])

# 3. projects API join on three sampled ids (one modern DPF, one old ICRR, one PPAR)
def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "scout-probe/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read(), resp.status

samples = [r["project_id"] for r in rows if r["lending_instrument_type"] == "DPF" and int(r["approval_fy"]) > 2015][:1] \
    + [r["project_id"] for r in rows if r["evaluation_type"] == "PPAR" and int(r["approval_fy"]) > 2010][:1] \
    + [r["project_id"] for r in rows if r["evaluation_type"] == "ICRR" and int(r["approval_fy"]) < 1990][:1]
url = ("https://search.worldbank.org/api/v2/projects?format=json&id="
       + ";".join(samples) + "&fl=project_name;approvalfy;approvaldate;closingdate;"
       "lendprojectcost;borrower;countryshortname;sector1;sector2;impagency;"
       "prodline;status;projectfinancialtype;grantamt;ibrdcommamt;idacommamt;boardapprovaldt")
body, status = fetch(url)
data = json.loads(body)
print(f"projects API id-lookup: HTTP {status}, ids requested {samples}, returned {len(data.get('projects', {}))}")
for pid, p in data.get("projects", {}).items():
    keep = {k: p.get(k) for k in ("project_name", "approvalfy", "boardapprovaldt", "closingdate",
                                   "lendprojectcost", "borrower", "countryshortname",
                                   "sector1", "prodline", "projectfinancialtype")}
    print(f"  {pid}: {json.dumps(keep)[:300]}")

# page size support
body, status = fetch("https://search.worldbank.org/api/v2/projects?format=json&rows=10000&fl=id")
data = json.loads(body)
print(f"rows=10000 attempt: HTTP {status}, page_size_returned={data.get('rows')}, total={data.get('total')}")
body, status = fetch("https://search.worldbank.org/api/v2/projects?format=json&rows=10000&os=10000&fl=id")
data = json.loads(body)
print(f"os=10000 attempt: HTTP {status}, page_size_returned={data.get('rows')}, os={data.get('os')}")
