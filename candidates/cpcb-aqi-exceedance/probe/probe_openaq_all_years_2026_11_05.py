# Enumerate S3 year-dir coverage for ALL 937 CPCB pm25 locationids from the
# 2023-04-25 capture (bounded: one LIST per location, no file downloads).
# Output: per-year location counts + per-location year lists (compact JSON).
import urllib.request, urllib.parse, xml.etree.ElementTree as ET, json, time, sys

BUCKET = "https://openaq-data-archive.s3.amazonaws.com/"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
UA = {"User-Agent": "Mozilla/5.0 (dataset-factory-discovery/1.0)"}

def list_years(lid, tries=3):
    q = urllib.parse.urlencode({"list-type": "2", "prefix": f"records/csv.gz/locationid={lid}/",
                                "delimiter": "/", "max-keys": "1000"})
    url = BUCKET + "?" + q
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                root = ET.fromstring(r.read())
            return [p.findtext(NS + "Prefix") for p in root.findall(NS + "CommonPrefixes")]
        except Exception as e:
            if attempt == tries - 1:
                raise
            time.sleep(2)

ids = json.load(open("openaq_cpcb_pm25_ids_2023_04_25.json"))["pm25_cpcb_ids"]
print(f"enumerating {len(ids)} locationids...", flush=True)
t0 = time.time()
cov = {}
fails = []
for i, lid in enumerate(ids):
    try:
        yrs = sorted(p.split("year=")[1].rstrip("/") for p in list_years(lid))
        cov[str(lid)] = yrs
    except Exception as e:
        fails.append((lid, f"{type(e).__name__}: {str(e)[:80]}"))
    if (i + 1) % 100 == 0:
        print(f"  {i+1}/{len(ids)} done, {time.time()-t0:.0f}s, fails={len(fails)}", flush=True)

import collections
per_year = collections.Counter()
locs_with_any = 0
for yrs in cov.values():
    if yrs:
        locs_with_any += 1
    for y in yrs:
        per_year[y] += 1
print("locations with >=1 year dir:", locs_with_any, "of", len(ids))
print("per-year location counts:", dict(sorted(per_year.items())))
gap2324 = sum(1 for yrs in cov.values() if "2022" in yrs and "2023" not in yrs and "2025" in yrs)
full2324 = sum(1 for yrs in cov.values() if "2023" in yrs or "2024" in yrs)
print(f"2022->(gap)->2025 pattern: {gap2324}; locations with any 2023/2024 files: {full2324}")
json.dump({"measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "n_ids": len(ids), "per_year": dict(sorted(per_year.items())),
           "locs_with_any": locs_with_any, "fails": fails,
           "coverage": cov},
          open("openaq_cpcb_937_year_coverage.json", "w"))
print("wrote openaq_cpcb_937_year_coverage.json in", round(time.time()-t0,1), "s")
