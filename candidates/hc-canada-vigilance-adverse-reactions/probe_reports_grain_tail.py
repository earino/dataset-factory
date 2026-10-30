#!/usr/bin/env python3
"""Bounded probe: does reports.txt in the CVpOnline extract carry multiple
VERSION_NO rows per REPORT_ID? Range-fetches only; never holds >32 MiB.
Writes findings incrementally to /opt/data/cache/scratch/vig_probe_out.json."""
import json, struct, sys, urllib.request, zlib

ZIP_URL = "https://open.canada.ca/data/dataset/9cbaef00-b52c-4a70-9fed-d9aa8263ab74/resource/2e736909-ef1f-4d60-bfb6-f15b3be3b1fa/download/extract_extrait.zip"
OUT = "/opt/data/cache/scratch/vig_probe_out.json"
out = {"requests": 0, "bytes": 0}

def rng_fetch(start, length, label=""):
    req = urllib.request.Request(ZIP_URL, headers={"Range": f"bytes={start}-{start+length-1}",
                                                    "User-Agent": "dataset-factory-discovery/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    out["requests"] += 1
    out["bytes"] += len(data)
    if r.status not in (200, 206):
        raise SystemExit(f"unexpected status {r.status} on {label}")
    return data

# --- 1. HEAD ---
req = urllib.request.Request(ZIP_URL, method="HEAD",
                             headers={"User-Agent": "dataset-factory-discovery/1.0"})
with urllib.request.urlopen(req, timeout=60) as r:
    out["head"] = {"status": r.status, "size": r.headers.get("Content-Length"),
                   "last_modified": r.headers.get("Last-Modified"),
                   "accept_ranges": r.headers.get("Accept-Ranges")}
total = int(out["head"]["size"])
print("HEAD:", out["head"], flush=True)

# --- 2. central directory (last 128 KiB) ---
TAIL = 128 * 1024
tail = rng_fetch(total - TAIL, TAIL, "central-dir")
eocd_pos = tail.rfind(b"PK\x05\x06")  # EOCD, search from end
eocd = tail[eocd_pos:]
if len(eocd) < 22:
    raise SystemExit(f"truncated EOCD at {eocd_pos} of {len(tail)}")
n_members = struct.unpack("<H", eocd[10:12])[0]
cd_size = struct.unpack("<I", eocd[12:16])[0]
cd_ofs = struct.unpack("<I", eocd[16:20])[0]
print(f"EOCD at file offset ~{total - TAIL + eocd_pos:,}: n_members={n_members} cd_size={cd_size:,} cd_ofs={cd_ofs:,}", flush=True)
if cd_size > TAIL:
    raise SystemExit(f"central directory ({cd_size:,} B) exceeds 128 KiB tail fetch - refetch needed")
members = []
i = cd_ofs - (total - TAIL)  # central dir offset relative to fetch window
while len(members) < n_members:
    rec = tail[i:i+46]
    method = struct.unpack("<H", rec[10:12])[0]
    csize, usize = struct.unpack("<II", rec[20:28])
    nlen, elen, clen = struct.unpack("<HHH", rec[28:34])
    name = tail[i+46:i+46+nlen].decode("utf-8", "replace")
    lho = struct.unpack("<I", rec[42:46])[0]
    members.append({"name": name, "method": method, "csize": csize, "usize": usize,
                    "local_header_offset": lho})
    i += 46 + nlen + elen + clen
out["members"] = members
print(f"central dir: {len(members)} members", flush=True)
for m in members:
    print(f"  {m['name']:45s} method={m['method']} csize={m['csize']:,} usize={m['usize']:,} lho={m['local_header_offset']:,}", flush=True)

rep = next((m for m in members if m["name"].endswith("/reports.txt") or m["name"] == "reports.txt"), None)
if rep is None:
    raise SystemExit("reports.txt not found in members")
out["reports_member"] = rep

# --- 3. local header of reports.txt ---
lh = rng_fetch(rep["local_header_offset"], 512, "reports-local-header")
if lh[:4] != b"PK\x03\x04":
    raise SystemExit("bad local header signature")
nlen, elen = struct.unpack("<HH", lh[26:30])
data_start = rep["local_header_offset"] + 30 + nlen + elen
out["reports_data_start"] = data_start
print("reports.txt data starts at", f"{data_start:,}", "method", rep["method"], flush=True)

# --- 4. fetch first compressed chunk(s), inflate, look at rows ---
CHUNK = 6 * 1024 * 1024
comp = rng_fetch(data_start, CHUNK, "reports-first-chunk")
if rep["method"] == 8:
    d = zlib.decompressobj(-15)
    txt = d.decompress(comp, 40 * 1024 * 1024)  # cap uncompressed at 40 MiB
else:
    txt = comp
print(f"inflated {len(txt):,} bytes from {len(comp):,} compressed", flush=True)
out["first_chunk"] = {"compressed_fetched": len(comp), "uncompressed": len(txt)}

lines = txt.split(b"\n")
out["first_lines_preview"] = [l[:400].decode("utf-8", "replace") for l in lines[:3]]
print("PREVIEW rows:", flush=True)
for l in lines[:2]:
    print("   ", l[:400].decode("utf-8", "replace"), flush=True)

json.dump(out, open(OUT, "w"), indent=1)
print("saved", OUT, flush=True)
