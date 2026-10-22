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

for enc in ("utf-8", "cp1252"):
    try:
        text = data.decode(enc)
        print(f"{enc}: clean decode")
    except UnicodeDecodeError as e:
        print(f"{enc}: decode error {e}")

text = data.decode("utf-8", errors="replace")
lines = text.splitlines()
reader = csv.DictReader(io.StringIO("\n".join(lines[:-1])))
rows = list(reader)

empty_occid = sum(1 for r in rows if not (r.get("OccID") or "").strip())
pop_occid = [r["OccID"] for r in rows if (r.get("OccID") or "").strip()]
print(f"empty OccID: {empty_occid}/{len(rows)}; populated sample: {pop_occid[:5]}")

occnos = [r.get("OccNo") for r in rows]
print("distinct OccNo:", len(set(occnos)), "of", len(occnos))
dups = [o for o in set(occnos) if occnos.count(o) > 1][:5]
print("dup OccNo sample:", dups)

# OccNo year prefix vs OccDate year
import re
mismatch = 0
for r in rows[:200]:
    m = re.match(r"R(\d\d)", r.get("OccNo") or "")
    if m and not r.get("OccDate", "").startswith("20" + m.group(1)):
        mismatch += 1
print("OccNo-year vs OccDate-year mismatch in first 200:", mismatch)

# AccIncType era-signature shares in this newest sample (should be ~0)
early = sum(1 for r in rows if "HISTORICAL" in (r.get("AccIncTypeID_DisplayEng") or "")
            or "DG LEAKER" in (r.get("AccIncTypeID_DisplayEng") or ""))
print("early-signature rows in newest sample:", early)

# missing shares in candidate feature columns
for col in ["OccTime", "SubdNameID_DisplayEng", "SUBD_OWNER_ABBREV_ENG",
            "NearLocation", "ProvinceID_DisplayEng", "RegionOfOccurrence_DisplayEng",
            "Latitude", "Longitude", "TimeZoneID_DisplayEng", "ActivityTypeID_DisplayEng",
            "SubdMileage"]:
    miss = sum(1 for r in rows if not (r.get(col) or "").strip()
               or (r.get(col) or "").strip() in ("N/A", "NULL"))
    print(f"{col}: missing/N-A {miss}/{len(rows)}")

# INJURIES table head sample: confirm the key columns
iurl = "https://www.tsb.gc.ca/sites/default/files/stats/RODSdb_MDOTW_VW_INJURIES_PUBLIC.csv"
ireq = urllib.request.Request(iurl, headers={**HEADERS, "Range": "bytes=0-65535"})
with urllib.request.urlopen(ireq, timeout=120) as r:
    idata = r.read()
itext = idata.decode("utf-8", errors="replace")
ilines = itext.splitlines()
ireader = csv.DictReader(io.StringIO("\n".join(ilines[:-1])))
irows = list(ireader)
print("INJURIES header:", ireader.fieldnames[:12])
print("INJURIES sample row:", {k: irows[0][k] for k in list(ireader.fieldnames)[:8]})
