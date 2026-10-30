#!/usr/bin/env python3
"""Probe 2b: piecewise range-fetch + incremental inflate of reports.txt.
4 MiB requests feed one decompressobj; retries a failed piece once."""
import json, struct, urllib.request, zlib
from collections import Counter

ZIP_URL = "https://open.canada.ca/data/dataset/9cbaef00-b52c-4a70-9fed-d9aa8263ab74/resource/2e736909-ef1f-4d60-bfb6-f15b3be3b1fa/download/extract_extrait.zip"
DATA_START = 280_690_987
CSIZE = 32_884_931          # reports.txt compressed size
USIZE = 422_306_974
PIECE = 4 * 1024 * 1024
TARGET_OUT = 100 * 1024 * 1024   # stop inflating at ~100 MiB of text

def fetch(start, length):
    req = urllib.request.Request(ZIP_URL, headers={"Range": f"bytes={start}-{start+length-1}",
                                                   "User-Agent": "dataset-factory-discovery/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        st, data = r.status, r.read()
    if st != 206:
        raise RuntimeError(f"status {st}")
    if len(data) != length:
        raise RuntimeError(f"short read {len(data)} != {length}")
    return data

d = zlib.decompressobj(-15)
buf = bytearray()
consumed = 0
fetched = 0
requests = 0
pieces_failed = []
while consumed < CSIZE and len(buf) < TARGET_OUT:
    want = min(PIECE, CSIZE - consumed)
    try:
        data = fetch(DATA_START + consumed, want)
        requests += 1
    except Exception as e:
        pieces_failed.append((consumed, str(e)))
        try:
            data = fetch(DATA_START + consumed, want)
            requests += 1
        except Exception as e2:
            pieces_failed.append((consumed, str(e2)))
            break
    fetched += len(data)
    try:
        out = d.decompress(data, TARGET_OUT - len(buf))
        buf.extend(out)
    except zlib.error as ze:
        pieces_failed.append((consumed, f"zlib: {ze}"))
        break
    consumed += len(data)
print(f"requests={requests} fetched={fetched:,} inflated={len(buf):,} consumed_of_stream={consumed:,}", flush=True)
print("failures:", pieces_failed, flush=True)

rows = bytes(buf).split(b"\n")
recs = []
bad = 0
for ln in rows:
    if not ln.strip():
        continue
    fs = [f.decode("utf-8", "replace").strip('"') for f in ln.split(b'$')]
    if len(fs) < 30:
        bad += 1
        continue
    recs.append(fs)
print(f"parsed records: {len(recs):,}  bad/short: {bad}", flush=True)
print("field count distribution:", Counter(len(r) for r in recs).most_common(5), flush=True)

per_rep = Counter(r[0] for r in recs)
n_rep = len(per_rep)
multi = {k: v for k, v in per_rep.items() if v > 1}
print(f"distinct REPORT_ID in sample: {n_rep:,}; with >1 row: {len(multi):,} ({100*len(multi)/n_rep:.3f}%)", flush=True)
print("rows-per-REPORT_ID:", Counter(per_rep.values()).most_common(15), flush=True)
print("VERSION_NO distribution:", Counter(r[2] for r in recs).most_common(15), flush=True)

# adjacency check: are a report's version rows adjacent in the file?
order = [r[0] for r in recs]
nonadj = sum(1 for i in range(len(order)-1) if order[i] == order[i+1])
first_multi = sorted(multi, key=lambda x: int(x))[:5]
print("sample of multi-row report ids:", first_multi, flush=True)
for rid in first_multi[:3]:
    idx = [i for i, r in enumerate(recs) if r[0] == rid]
    print(f"  rid={rid} at row idx {idx[:6]}:", [(recs[i][2], recs[i][3], recs[i][4], recs[i][25], recs[i][26]) for i in idx[:6]], flush=True)

# consecutive-pair ordering
ids = [int(r[0]) for r in recs]
inc = sum(1 for a, b in zip(ids, ids[1:]) if b == a + 1)
dec = sum(1 for a, b in zip(ids, ids[1:]) if b < a)
print(f"first ID {ids[0]:,} last ID {ids[-1]:,}; +1 pairs {inc:,}; decreasing pairs {dec:,}", flush=True)
print("first row DATRECEIVED/DATINTRECEIVED:", recs[0][3], recs[0][4], "| last row:", recs[-1][3], recs[-1][4], flush=True)
json.dump({"requests": requests, "fetched": fetched, "inflated": len(buf),
           "n_records": len(recs), "n_distinct": n_rep, "n_multi": len(multi),
           "version_dist": Counter(r[2] for r in recs).most_common(15),
           "rows_per_rep": Counter(per_rep.values()).most_common(15),
           "failures": [(a, b) for a, b in pieces_failed]},
          open("/opt/data/cache/scratch/vig_probe2_out.json", "w"), indent=1)
print("saved vig_probe2_out.json", flush=True)
