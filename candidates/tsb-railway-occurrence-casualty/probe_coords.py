"""Bounded coordinate-format probe (2026-10-22): 2 MB window at offset 8,000,000
of the OCCURRENCE CSV (file is newest-first; ~2021-2022 era, where tsb-003's
frame assertion failed). Tests the two encodings against the Canadian envelope
and against known town positions for rows the earlier head sample carried.
"""
import csv
import io
import urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA,
           "Accept": "*/*", "Accept-Language": "en-CA,en;q=0.9",
           "Referer": "https://www.tsb.gc.ca/"}
url = "https://www.tsb.gc.ca/sites/default/files/stats/RODSdb_MDOTW_VW_OCCURRENCE_PUBLIC.csv"
req = urllib.request.Request(url, headers={**HEADERS, "Range": "bytes=0-65535"})
with urllib.request.urlopen(req, timeout=120) as r:
    header_line = r.read().decode("utf-8", errors="replace").splitlines()[0]

req = urllib.request.Request(url, headers={**HEADERS, "Range": "bytes=8000000-10097151"})
with urllib.request.urlopen(req, timeout=120) as r:
    data = r.read()
text = data.decode("utf-8", errors="replace")
lines = text.splitlines()
reader = csv.DictReader(io.StringIO(header_line + "\n" + "\n".join(lines[1:-1])))
rows = list(reader)
years = {}
for row in rows:
    years[row.get("OccDate", "?")[:4]] = years.get(row.get("OccDate", "?")[:4], 0) + 1
print("window rows:", len(rows), "by year:", years)

def decode(v, is_lat):
    """Candidate decodes; return (label, value) for the unique one that is
    internally valid AND inside the Canadian envelope."""
    lo, hi = (41, 72) if is_lat else (52, 145)
    found = []
    if v >= 10_000_000:
        found.append(("x1e6", v / 1e6))
    if 10_000 <= v < 10_000_000:
        deg = v // 10_000
        minutes = (v % 10_000) / 100.0
        if minutes < 60:
            found.append(("ddmm.ff", deg + minutes / 60.0))
        found.append(("x1e3", v / 1e3))
    if v < 10_000:
        found.append(("plain", float(v)))
    ok = [(label, val) for label, val in found if lo <= val <= hi]
    return ok

both_ok = dms_ok = k3_ok = neither = both_lat = 0
examples = []
counts = {}
for row in rows:
    for col, is_lat in (("Latitude", True), ("Longitude", False)):
        raw = (row.get(col) or "").strip()
        if not raw:
            continue
        try:
            v = int(float(raw))
        except ValueError:
            continue
        ok = decode(v, is_lat)
        if len(ok) == 1:
            label, val = ok[0]
            counts[label] = counts.get(label, 0) + 1
        elif len(ok) > 1:
            both_ok += 1
            if len(examples) < 6:
                examples.append((col, raw, ok))
        else:
            neither += 1
            if len(examples) < 12:
                examples.append((col, raw, "NO VALID DECODE"))
print("decode counts:", counts, " ambiguous:", both_ok, " undecodable:", neither)
for e in examples:
    print("  ", e)

# spot-check a few rows' NearLocation against the two decodes
spots = [(row.get("NearLocation"), row.get("Latitude"), row.get("Longitude"))
         for row in rows[:400:40]]
for town, lat, lon in spots:
    print("town:", town, "raw lat/lon:", lat, lon)
