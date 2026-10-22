"""Bounded head-sample probe of the TSB RODS OCCURRENCE CSV (2026-10-22).

Answers concrete construction questions only, with a 2 MB ranged GET:
- exact value spellings: InjuriesIND, injury totals, OccClassID_DisplayEng,
  ActivityTypeID_DisplayEng, SubdOwner abbrevs, TimeZone values
- missing-value markers in the shipped candidate feature columns
"""
import csv
import io
import urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-CA,en;q=0.9",
    "Referer": "https://www.tsb.gc.ca/",
}
url = "https://www.tsb.gc.ca/sites/default/files/stats/RODSdb_MDOTW_VW_OCCURRENCE_PUBLIC.csv"
req = urllib.request.Request(url, headers={**HEADERS, "Range": "bytes=0-2097151"})
with urllib.request.urlopen(req, timeout=120) as r:
    data = r.read()
print("fetched", len(data), "bytes; status", r.status)

text = data.decode("cp1252", errors="replace")
# drop possibly-truncated last line
lines = text.splitlines()
reader = csv.DictReader(io.StringIO("\n".join(lines[:-1])))
rows = list(reader)
print("header cols:", len(reader.fieldnames))
print("sample rows:", len(rows))

from collections import Counter

def dist(col, n=18):
    c = Counter((row.get(col) or "<empty>") for row in rows)
    return c.most_common(n)

for col in ["OccClassID_DisplayEng", "ActivityTypeID_DisplayEng",
            "SUBD_OWNER_ABBREV_ENG", "SubdOwnerID_DisplayEng",
            "TimeZoneID_DisplayEng", "ProvinceID_DisplayEng",
            "RegionOfOccurrence_DisplayEng", "InjuriesIND",
            "OccurrenceTypeID_DisplayEng", "AccIncTypeID_DisplayEng"]:
    print(f"-- {col}:", dist(col))

# injury columns on a few rows
for col in ["TotalFatalInjuries", "TotalSeriousInjuries", "TotalMinorInjuries",
            "OccTime", "OccDate", "OccID", "OccNo", "SubdMileage",
            "Latitude", "Longitude", "NearLocation", "SubdNameID_DisplayEng"]:
    vals = [(row.get(col) or "<empty>") for row in rows[:8]]
    print(f"-- {col} sample:", vals)

# check label-vs-totals agreement in the sample
both = disagree_ind_only = disagree_totals_only = 0
for row in rows:
    ind = (row.get("InjuriesIND") or "").strip() == "1"
    totals = 0
    for c in ("TotalFatalInjuries", "TotalSeriousInjuries", "TotalMinorInjuries"):
        try:
            totals += int(float(row.get(c) or "0"))
        except ValueError:
            pass
    if ind and totals > 0:
        both += 1
    elif ind:
        disagree_ind_only += 1
    elif totals > 0:
        disagree_totals_only += 1
print("label agreement in sample: both", both, "ind_only", disagree_ind_only,
      "totals_only", disagree_totals_only)
