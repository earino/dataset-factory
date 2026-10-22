#!/usr/bin/env python3
"""Probe NZ Electricity Authority EMI 'Final energy prices' end to end.

Re-runnable discovery probe for nz-ea-wholesale-price-exceedance. All access is the
publisher-documented anonymous Azure blob container (no key, no SAS):
  1. list the FinalEnergyPrices folder: file inventory, size distribution, and the
     publication lag (Last-Modified minus trade date) for daily files;
  2. fetch the latest NetworkSupplyPointsTable (POC -> Island / reporting region);
  3. download a bounded sample - four whole monthly files chosen for era and event
     coverage (199701, 200807, 202006, 202408) plus one daily file per recent month -
     and print per-day market mean prices and exceedance counts at candidate
     thresholds.

Usage: python3 candidates/nz-ea-wholesale-price-exceedance/probe_final_prices.py
"""
import csv
import io
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

CONTAINER = "https://emidatasets.blob.core.windows.net/publicdata"
PFX = "Datasets/Wholesale/DispatchAndPricing/FinalEnergyPrices/"


def fetch(url, timeout=180):
    req = urllib.request.Request(url, headers={"User-Agent": "scout-factory-probe/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


print(f"probe start {datetime.now(timezone.utc).isoformat()}")
reqs = 0
dbytes = 0
t0 = time.time()

listing = fetch(f"{CONTAINER}?restype=container&comp=list&prefix={PFX}&maxresults=5000")
reqs += 1
dbytes += len(listing)
root = ET.fromstring(listing)
monthly, daily = {}, {}
for b in root.iter("Blob"):
    name_el, props_el = b.find("Name"), b.find("Properties")
    if name_el is None or props_el is None:
        continue
    stem = name_el.text.split("/")[-1]
    key = stem.split("_")[0]
    (monthly if len(key) == 6 else daily if len(key) == 8 else {}).setdefault(key, name_el.text)
print(f"inventory: {len(monthly)} monthly files {sorted(monthly)[0]}..{sorted(monthly)[-1]}, "
      f"{len(daily)} daily files {sorted(daily)[0]}..{sorted(daily)[-1]}")

lags = []
for b in root.iter("Blob"):
    name_el, props_el = b.find("Name"), b.find("Properties")
    if name_el is None or props_el is None:
        continue
    stem = name_el.text.split("/")[-1]
    key = stem.split("_")[0]
    if len(key) != 8:
        continue
    td = datetime.strptime(key, "%Y%m%d").replace(tzinfo=timezone.utc)
    lm_el = props_el.find("Last-Modified")
    if lm_el is None or not lm_el.text:
        continue
    lmt = parsedate_to_datetime(lm_el.text).astimezone(timezone.utc)
    lags.append((lmt - td).total_seconds() / 86400.0)
lags.sort()
if lags:
    k = len(lags)
    print(f"daily-file lag days: n={k} min={lags[0]:.2f} p50={lags[k//2]:.2f} "
          f"p90={lags[int(k*0.9)]:.2f} max={lags[-1]:.2f}")

# --- mapping ---
mroot = ET.fromstring(fetch(f"{CONTAINER}?restype=container&comp=list&"
                            "prefix=Datasets/Wholesale/MappingsAndGeospatial/NetworkSupplyPointsTable/"))
mnames = sorted(n for n in (b.find("Name").text for b in mroot.iter("Blob")) if n)
mtext = fetch(f"{CONTAINER}/{mnames[-1]}").decode("utf-8", errors="replace")
reqs += 2
dbytes += len(mtext)
mrows = list(csv.DictReader(io.StringIO(mtext)))
cols = list(mrows[0].keys())
geo_cols = [c for c in cols if any(k in c.lower() for k in ("island", "region"))]
poc_col = next((c for c in cols if "poc" in c.lower()), None)
print(f"mapping {mnames[-1].split('/')[-1]}: {len(mrows)} rows; geo cols {geo_cols} on poc {poc_col!r}")
poc_geo = {}
for r in mrows:
    poc_geo[r[poc_col].strip().upper()] = {g: (r[g] or "").strip() for g in geo_cols}


def day_means(blob_name):
    global reqs, dbytes
    data = fetch(f"{CONTAINER}/{blob_name}")
    reqs += 1
    dbytes += len(data)
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8", errors="replace"))))
    acc = defaultdict(list)
    pocs = set()
    for r in rows:
        pocs.add(r["PointOfConnection"])
        v = r["DollarsPerMegawattHour"]
        if v.strip():
            acc[r["TradingDate"]].append(float(v))
    return len(rows), len(pocs), {d: sum(v) / len(v) for d, v in acc.items()}


def summarise(label, day_map, thresholds=(100, 150, 200, 300)):
    means = sorted(day_map.values())
    if not means:
        print(f"{label}: no data")
        return
    n = len(means)
    line = (f"{label}: days={n} market-mean $/MWh min={means[0]:.0f} p25={means[n//4]:.0f} "
            f"median={means[n//2]:.0f} p75={means[3*n//4]:.0f} max={means[-1]:.0f}")
    for t in thresholds:
        line += f" | >{t}: {sum(1 for m in means if m > t)}"
    print(line)


for key in ("199701", "200807", "202006", "202408"):
    nrows, npocs, dm = day_means(monthly[key])
    print(f"monthly file {key}: rows={nrows:,} pocs={npocs}")
    summarise(f"  {key}", dm)

by_month = defaultdict(list)
for k in daily:
    by_month[k[:6]].append(k)
recent = {}
for m in sorted(by_month):
    names = sorted(by_month[m])
    _, _, dm = day_means(daily[names[len(names) // 2]])
    recent.update(dm)
summarise("recent-era sampled days", recent)

secs = time.time() - t0
print(f"COST: requests={reqs} bytes={dbytes:,} ({dbytes/1e6:.1f} MB) secs={secs:.1f}")
print(f"probe end {datetime.now(timezone.utc).isoformat()}")
