#!/usr/bin/env python3
"""Extract complete pair-year series from rapidrail_2024_daily.csv (fixed) 2026-11-07.

Sorted (origin, destination, date): binary search the pair block start, then read the
whole contiguous block. Bounded: ~30 range requests per pair.
"""
import json
import time
import urllib.request
from collections import Counter
from datetime import date

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/131.0"}
URL = "https://storage.data.gov.my/transportation/rail/rapidrail_2024_daily.csv"
SIZE = 375_944_306
REQS = {"n": 0, "bytes": 0}


def range_chunk(a, b):
    REQS["n"] += 1
    REQS["bytes"] += b - a + 1
    req = urllib.request.Request(URL, headers={**UA, "Range": f"bytes={a}-{b}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def line_rec(off):
    """(first complete line at/after off, its true start offset)"""
    blob = range_chunk(off, min(off + 4095, SIZE - 1))
    nl = blob.find("\n")
    if nl == -1:
        return blob, off
    start = off + nl + 1
    line = blob[start - off:].split("\n", 1)[0]
    return line, start


def block_for(pair_key):
    prefix = pair_key + ","
    lo, hi = 0, SIZE - 1
    for _ in range(28):
        mid = (lo + hi) // 2
        line, _ls = line_rec(mid)
        parts = line.split(",", 2)
        cur = (parts[0] + "," + parts[1] + ",") if len(parts) >= 3 else "\xff"
        if cur < prefix:
            lo = mid
        else:
            hi = mid
        if hi - lo < 2:
            break
    line, start = line_rec(hi)
    parts = line.split(",", 2)
    if len(parts) < 3 or parts[0] + "," + parts[1] + "," != prefix:
        return []
    rows = []
    off = start
    while True:
        blob = range_chunk(off, min(off + 31_743, SIZE - 1))
        lines = blob.split("\n")
        consumed = 0
        stop = False
        for ln in lines:
            consumed += len(ln) + 1
            if not ln:
                continue
            p = ln.split(",", 3)
            if len(p) < 4 or p[0] + "," + p[1] + "," != prefix:
                stop = True
                break
            rows.append((p[2][:10], int(p[3])))
        off += consumed
        if stop or off >= SIZE:
            break
    return rows


PAIRS = [
    "A0: All Stations,AG01: Sentul Timur",
    "KG16: Pasar Seni,KJ14: Pasar Seni",
    "KJ14: Pasar Seni,KG16: Pasar Seni",
    "SP31: Putra Heights,SP31: Putra Heights",
    "PYL33: Serdang Jaya,KG16: Pasar Seni",
]

t0 = time.time()
out = {}
for pk in PAIRS:
    rows = block_for(pk)
    if not rows:
        print(f"== {pk}: NOT FOUND")
        continue
    dates = [r[0] for r in rows]
    vals = [r[1] for r in rows]
    zeros = sum(1 for v in vals if v == 0)
    sv = sorted(vals)
    n = len(vals)
    dow, dow_sum = Counter(), Counter()
    for d, v in rows:
        w = date.fromisoformat(d).weekday()
        dow[w] += 1
        dow_sum[w] += v
    span = (date.fromisoformat(dates[-1]) - date.fromisoformat(dates[0])).days + 1
    print(f"== {pk}")
    print(f"   rows={n} dates {dates[0]}..{dates[-1]} (calendar span {span}, missing {span-n})")
    print(f"   zeros={zeros} ({zeros/n:.1%}) | p50={sv[n//2]} p90={sv[int(n*0.9)]} p99={sv[int(n*0.99)]} max={sv[-1]} mean={sum(vals)/n:.1f}")
    print("   dow means:", {k: round(dow_sum[k]/dow[k]) for k in sorted(dow)})
    print("   top:", sorted(rows, key=lambda r: -r[1])[:4])
    print("   low:", sorted(rows, key=lambda r: r[1])[:6])
    out[pk] = rows

print(f"\nrequests={REQS['n']} bytes={REQS['bytes']:,} wall={time.time()-t0:.1f}s")
json.dump(out, open("/opt/data/cache/scratch/pair_blocks_2024.json", "w"))
print("saved /opt/data/cache/scratch/pair_blocks_2024.json")
