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
text = data.decode("utf-8", errors="replace")
lines = text.splitlines()
reader = csv.DictReader(io.StringIO("\n".join(lines[:-1])))
rows = list(reader)

dups = [r for r in rows if (r.get("OccNo") or "") == "R26D0003"]
print("rows with OccNo R26D0003:", len(dups))
cols = ["OccNo", "OccID", "OccDate", "OccTime", "OccurrenceTypeID_DisplayEng",
        "AccIncTypeID_DisplayEng", "ProvinceID_DisplayEng", "SubdNameID_DisplayEng",
        "NearLocation", "InjuriesIND", "ActivityTypeID_DisplayEng", "Summary"]
for r in dups:
    print("---")
    for c in cols:
        print(f"  {c}: {r.get(c)!r}")

# also: count rows where the two R26D0003 rows differ at all
if len(dups) == 2:
    diff_cols = [c for c in reader.fieldnames if (dups[0].get(c) or "") != (dups[1].get(c) or "")]
    print("columns differing between the two rows:", diff_cols)
