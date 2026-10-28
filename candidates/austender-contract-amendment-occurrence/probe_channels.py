#!/usr/bin/env python3
"""Channel + licence probe for austender-contract-amendment-occurrence.

Reproduces the channel map and licence quotes recorded 2026-10-28:
- AusTender Terms of Use clauses 5.1/5.4/6.1 (licence + attribution)
- data.gov.au catalogue records (historic FY archive; licence id)
- weekly export HEAD (retention + size)
- amendments-report window download (one bounded week, format + stats block)
- OCDS registry per-year HEADs (sizes; the endpoint family that carries no
  amendment events - see probe_cohort_rate.py for the OCDS negative)

Run: python3 probe_channels.py   (bounded: <10 requests, a few MB)
"""
import json
import re
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
DGA = "https://data.gov.au/data/api/3/action/"


def fetch(url, headers=None, method="GET"):
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.headers, r.read()


def textify(html):
    t = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t)


# 1. Licence: AusTender Terms of Use
_, b = fetch("https://www.tenders.gov.au/infolinks/termsofuse")
t = textify(b.decode("utf-8", "replace"))
m = re.search(r"5\.1 With the exception of the Commonwealth Coat of Arms.*?CC BY 3\.0 AU\)\.", t)
print("ToU 5.1:", (m.group(0)[:200] + "...") if m else "NOT FOUND")
m = re.search(r"6\.1 Except where otherwise noted.*?www\.tenders\.gov\.au \.", t)
print("ToU 6.1:", (m.group(0)[:200] + "...") if m else "NOT FOUND")

# 2. data.gov.au historical dataset + licence id
d = json.loads(fetch(DGA + "package_show?id=historical-australian-government-contract-data")[1])
print("dataset:", d["result"]["title"], "| license_id:", d["result"].get("license_id"),
      "| resources:", len(d["result"]["resources"]))
for r in d["result"]["resources"][:6]:
    print("   RES:", r.get("name"), "|", r.get("format"), "|", r.get("size_human") or r.get("size"))

# 3. weekly export (HEAD only here)
hdrs, _ = fetch("https://www.tenders.gov.au/Reports/CnWeeklyExportDownload/"
                "c8dc039a-82ed-4e36-b185-519fbe6cf009", method="HEAD")
print("weekly export:", hdrs.get("Content-Length"), "bytes |", hdrs.get("Content-Disposition"))

# 4. amendments report: one bounded week
u = ("https://www.tenders.gov.au/Reports/CnAndAmendmentsDownload?AgencyStatus=0"
     "&DateType=Publish%20Date&DateStart=01-Sep-2023&DateEnd=07-Sep-2023")
hdrs, b = fetch(u, headers={"Referer": "https://www.tenders.gov.au/Reports/CnAndAmendmentsForm"})
print("amendments report week:", len(b), "bytes |", hdrs.get("Content-Type"))

# 5. OCDS registry sizes (HEAD)
for name in ["2018.jsonl.gz", "2023.csv.tar.gz", "2026.jsonl.gz"]:
    try:
        hdrs, _ = fetch("https://data.open-contracting.org/en/publication/19/download?name=" + name,
                        method="HEAD")
        print("OCDS", name, "->", hdrs.get("Content-Length"), "bytes")
    except Exception as e:  # noqa: BLE001
        print("OCDS", name, "ERROR:", e)
