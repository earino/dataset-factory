#!/usr/bin/env python3
"""Buenos Aires Data (CKAN) inventory probe for the Ecobici trip archive - the
access/licence measurement from 2026-10-23 (notes s1-3).

Prints the package licence, every Recorridos resource with HEAD Content-Length,
CDN Last-Modified, and (optionally, --sample 2015) parses one small year zip to
verify the trip schema. Anonymous; no auth.
"""
import csv
import io
import json
import sys
import time
import urllib.request
import zipfile

CKAN = ("https://data.buenosaires.gob.ar/api/3/action/"
        "package_show?id=bicicletas-publicas")
CDN = ("https://cdn.buenosaires.gob.ar/datosabiertos/datasets/"
       "transporte-y-obras-publicas/bicicletas-publicas/"
       "recorridos-realizados-{yr}{ext}")

req = urllib.request.Request(CKAN, headers={"User-Agent": "research-probe/1.0"})
pkg = json.loads(urllib.request.urlopen(req, timeout=90).read())["result"]
print("license:", pkg.get("license_id"),
      "| metadata_modified:", pkg.get("metadata_modified"))
for res in pkg["resources"]:
    if "ecorrido" in (res.get("url") or ""):
        print(" *", res.get("url"))

for yr in range(2010, 2027):
    req = urllib.request.Request(CDN.format(yr=yr, ext=".zip"),
                                 headers={"User-Agent": "research-probe/1.0"},
                                 method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            print(f"{yr}.zip: 200 len={resp.headers.get('Content-Length')} "
                  f"LM={resp.headers.get('Last-Modified')}")
    except Exception as exc:
        print(f"{yr}.zip: {exc}")
    time.sleep(0.3)

if "--sample" in sys.argv:
    yr = sys.argv[sys.argv.index("--sample") + 1]
    ext = ".zip" if int(yr) >= 2014 else ".csv"
    url = CDN.format(yr=yr, ext=ext)
    data = urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "research-probe/1.0"}),
        timeout=600).read()
    if url.endswith(".zip"):
        zf = zipfile.ZipFile(io.BytesIO(data))
        member = max(zf.namelist(),
                     key=lambda name: zf.getinfo(name).file_size)
        handle = io.TextIOWrapper(zf.open(member), "utf-8", "replace")
    else:
        handle = io.StringIO(data.decode("utf-8", "replace"))
    reader = csv.DictReader(handle)
    cols = reader.fieldnames
    nrows = sum(1 for _ in reader)
    print(f"sample {yr}: {nrows} rows, columns={cols}")
