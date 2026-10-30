#!/usr/bin/env python3
"""Probe 3: full-stream aggregate pass over reports.txt (422 MiB uncompressed)
via bounded 4 MiB range requests; output is discarded except aggregate counters.
Decides: (a) any REPORT_ID with >1 row anywhere? (b) VERSION_NO distribution
(c) per-year DATINTRECEIVED/DATRECEIVED counts (d) follow-up (VERSION>=1) rate by year.
No data is retained beyond counters."""
import json, urllib.request, zlib
from collections import Counter

ZIP_URL = "https://open.canada.ca/data/dataset/9cbaef00-b52c-4a70-9fed-d9aa8263ab74/resource/2e736909-ef1f-4d60-bfb6-f15b3be3b1fa/download/extract_extrait.zip"
DATA_START = 280_690_987
CSIZE = 32_884_931
PIECE = 4 * 1024 * 1024

def fetch(start, length):
    req = urllib.request.Request(ZIP_URL, headers={"Range": f"bytes={start}-{start+length-1}",
                                                   "User-Agent": "dataset-factory-discovery/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        st, data = r.status, r.read()
    if st != 206 or len(data) != length:
        raise RuntimeError(f"status {st} len {len(data)} != {length}")
    return data

d = zlib.decompressobj(-15)
n_rows = 0
bad = 0
field_counts = Counter()
ver_dist = Counter()
year_int = Counter()      # DATINTRECEIVED year
year_rec = Counter()      # DATRECEIVED year
followup_by_year = Counter()   # reports with VERSION_NO >= 1, by DATINTRECEIVED year
tot_by_year = Counter()
serious_dist = Counter()
last_id = None
dup_id = 0
nonincr = 0
carry = b""
pieces = 0
tail = bytearray()          # keep last ~2 MiB of text for a final close look
consumed = 0
while consumed < CSIZE:
    want = min(PIECE, CSIZE - consumed)
    data = fetch(DATA_START + consumed, want)
    pieces += 1
    consumed += len(data)
    out = d.decompress(data)
    if consumed >= CSIZE:
        out += d.flush()
    buf = carry + out
    lines = buf.split(b"\n")
    carry = lines.pop()          # last partial line carries forward
    for ln in lines:
        if not ln.strip():
            continue
        fs = [f.strip(b'"') for f in ln.split(b'$')]
        if len(fs) < 30:
            bad += 1
            continue
        n_rows += 1
        field_counts[len(fs)] += 1
        rid = int(fs[0])
        ver = fs[2].decode("ascii", "replace")
        datint = fs[4].decode("ascii", "replace")   # DATINTRECEIVED (initial)
        datrec = fs[3].decode("ascii", "replace")   # DATRECEIVED (latest)
        ver_dist[ver] += 1
        serious_dist[fs[25].decode("ascii", "replace")] += 1
        y_int = datint[-2:] and (1900 + int(datint[-2:]) if int(datint[-2:]) <= 26 else 1900 + int(datint[-2:]))
        # safer: parse DD-MON-YY
        try:
            yy = int(datint.split("-")[2])
            year = 2000 + yy if yy <= 26 else 1900 + yy
        except Exception:
            year = None
        if year:
            tot_by_year[year] += 1
            if ver != "0":
                followup_by_year[year] += 1
        try:
            yy2 = int(datrec.split("-")[2])
            year2 = 2000 + yy2 if yy2 <= 26 else 1900 + yy2
            year_rec[year2] += 1
        except Exception:
            pass
        if last_id is not None:
            if rid == last_id:
                dup_id += 1
            elif rid < last_id:
                nonincr += 1
        last_id = rid
    tail.extend(out[-1_000_000:] if False else b"")  # placeholder (kept simple)
    del buf, lines, out

print(f"pieces={pieces} consumed={consumed:,}/{CSIZE:,} rows={n_rows:,} bad={bad}", flush=True)
print("field count distribution:", field_counts.most_common(5), flush=True)
print("duplicate-adjacent REPORT_ID rows:", dup_id, "| non-increasing ID transitions:", nonincr, flush=True)
print("VERSION_NO distribution (all):", sorted(ver_dist.items(), key=lambda kv: int(kv[0]))[:20], flush=True)
print("seriousness col25 distribution:", serious_dist.most_common(10), flush=True)
print("DATINTRECEIVED year -> total, follow-ups(VER>=1):", flush=True)
for y in sorted(tot_by_year):
    print(f"  {y}: {tot_by_year[y]:,} reports, {followup_by_year[y]:,} follow-up ({100*followup_by_year[y]/tot_by_year[y]:.1f}%)", flush=True)
print("DATRECEIVED (latest) year distribution:", sorted(year_rec.items())[-25:], flush=True)
res = {"pieces": pieces, "rows": n_rows, "bad": bad, "dup_adjacent": dup_id, "nonincr": nonincr,
       "ver_dist": sorted(ver_dist.items(), key=lambda kv: int(kv[0])),
       "by_year": {str(y): [tot_by_year[y], followup_by_year[y]] for y in sorted(tot_by_year)}}
json.dump(res, open("/opt/data/cache/scratch/vig_probe3_out.json", "w"), indent=1)
print("saved vig_probe3_out.json", flush=True)
