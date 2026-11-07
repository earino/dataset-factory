#!/usr/bin/env python3
"""Bounded Range sampling of MY rail OD CSV editions (2026-11-07).

Fetches ~6 x 256 KB chunks per file (header + spread offsets + tail), stdlib only.
Measures: columns, row format, date coverage, station-code inventory within samples,
pair density, and whether zero-ridership rows appear. No complete-file download.
"""
import csv
import io
import re
import urllib.request
from collections import Counter

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/131.0"}
CHUNK = 256 * 1024


def head_size(url):
    req = urllib.request.Request(url, headers=UA, method="HEAD")
    with urllib.request.urlopen(req, timeout=45) as r:
        return int(r.headers["Content-Length"])


def range_chunk(url, start, end):
    req = urllib.request.Request(url, headers={**UA, "Range": f"bytes={start}-{end}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def sample(url, n_chunks=6):
    size = head_size(url)
    print(f"### {url.split('/')[-1]}  total={size:,} bytes")
    # header + first data rows
    first = range_chunk(url, 0, CHUNK - 1)
    lines = first.decode("utf-8", "replace").splitlines()
    header = lines[0]
    print("header:", header)
    colnames = next(csv.reader([header]))
    body = "\n".join(lines[1:])
    dates = Counter()
    stations = Counter()
    stats = {"rows": 0, "zero": 0}
    ridership = []
    dcol = colnames.index("date")
    ocol = colnames.index("origin")
    dncol = colnames.index("destination")
    rcol = colnames.index("ridership")

    def eat(text):
        for rec in csv.reader(io.StringIO(text)):
            if len(rec) != len(colnames) or rec[dcol] == "date":
                continue
            stats["rows"] += 1
            dates[rec[dcol]] += 1
            stations[rec[ocol]] += 1
            stations[rec[dncol]] += 1
            v = int(rec[rcol])
            if v == 0:
                stats["zero"] += 1
            ridership.append(v)

    eat(body)
    offsets = [int(size * f) for f in (0.2, 0.4, 0.6, 0.8)] + [max(0, size - CHUNK)]
    seen_bounds = {0}
    for off in offsets:
        if off in seen_bounds:
            continue
        seen_bounds.add(off)
        blob = range_chunk(url, off, off + CHUNK - 1).decode("utf-8", "replace")
        # drop partial first/last lines
        nl = blob.find("\n")
        blob = blob[nl + 1:]
        eat(blob)
    print(f"sampled_rows={stats['rows']} (chunks={len(seen_bounds)}, ~{len(seen_bounds)*CHUNK/1024:.0f} KiB of {size/1e6:.0f} MB)")
    ds = sorted(dates)
    print(f"dates in sample: {ds[0]} .. {ds[-1]} | distinct={len(ds)} | rows at first date={dates[ds[0]]}")
    print(f"distinct station codes in sample: {len(stations)} | top:", stations.most_common(6))
    pre = Counter(s.split("-")[0].strip() if "-" in s else re.match(r"[A-Z]+", s).group(0) if re.match(r"[A-Z]+", s) else s for s in stations)
    print("station-code prefixes in sample:", dict(pre))
    if ridership:
        ridership.sort()
        n = len(ridership)
        print(f"ridership: min={ridership[0]} p50={ridership[n//2]} p90={ridership[int(n*0.9)]} max={ridership[-1]} | zero-rows={stats['zero']}")
    print()


for u in [
    "https://storage.data.gov.my/transportation/rail/rapidrail_2024_daily.csv",
    "https://storage.data.gov.my/transportation/ktmb/komuter_2024.csv",
]:
    sample(u)
