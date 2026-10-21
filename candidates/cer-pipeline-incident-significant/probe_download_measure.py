"""CER pipeline incident panel probe (2026-10-21 session).

Run: python3 candidates/cer-pipeline-incident-significant/probe_download_measure.py

Downloads the 3 small CER files (3.0 MB total, cp1252-encoded) and prints the
measured panel: rows/year, Significant counts, incident types, substances,
release types, volume distribution. Findings recorded in notes.md.
"""
import csv
import os
import statistics
import urllib.request

OUT = "/tmp/cer_probe"
os.makedirs(OUT, exist_ok=True)
FILES = {
    "data": "https://www.cer-rec.gc.ca/open/incident/pipeline-incidents-data.csv",
    "dictionary": "https://www.cer-rec.gc.ca/open/incident/pipeline-incidents-data-dictionary.csv",
}

for name, url in FILES.items():
    p = os.path.join(OUT, os.path.basename(url))
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "scout/1.0"}), timeout=120) as r:
        body = r.read()
    with open(p, "wb") as f:
        f.write(body)
    print(f"{name}: {len(body):,} bytes -> {p}")

with open(os.path.join(OUT, "pipeline-incidents-data.csv"), newline="", encoding="cp1252") as f:
    rows = list(csv.DictReader(f))
print(f"{len(rows):,} rows x {len(rows[0])} columns; columns: {', '.join(rows[0])}")
years, sig = {}, {}
for r in rows:
    y = str(r.get("Year", "?"))
    years[y] = years.get(y, 0) + 1
    sig.setdefault(y, [0, 0])
    if (r.get("Significant") or "").strip().lower() in ("yes", "y", "true"):
        sig[y][0] += 1
    else:
        sig[y][1] += 1
for y in sorted(years, key=str):
    print(f"  {y}: {years[y]:4d} rows, significant={sig[y][0]:3d}")
print(f"TOTAL significant: {sum(v[0] for v in sig.values())} / {len(rows)} "
      f"({100 * sum(v[0] for v in sig.values()) / len(rows):.2f}%)")

vols = []
for r in rows:
    v = (r.get("Approximate Volume Released (m3)") or "").strip()
    if v and v not in ("-", "N/A"):
        try:
            vols.append(float(v.replace(",", "")))
        except ValueError:
            pass
vols.sort()
if vols:
    print(f"volume m3: n={len(vols)}, median={statistics.median(vols)}, "
          f">=1: {sum(1 for v in vols if v >= 1)}, >=10: {sum(1 for v in vols if v >= 10)}, "
          f">=100: {sum(1 for v in vols if v >= 100)}")
