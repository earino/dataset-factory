#!/usr/bin/env python3
# Bounded probe: read the FIRST 256 KB of auto_infracao_csv.zip over HTTP Range,
# parse the zip local-file header, raw-inflate the compressed prefix, and print the
# real CSV header + first rows. No bulk download: max 262144 bytes on the wire.
import struct, sys, urllib.request, zlib

URL = ("https://stibamadadosabertosprd.blob.core.windows.net/dados-abertos/"
       "dados/SIFISC/auto_infracao/auto_infracao/auto_infracao_csv.zip")
N = 262144

req = urllib.request.Request(URL, headers={"Range": f"bytes=0-{N-1}",
                                           "User-Agent": "scout-bounded-probe/1.0"})
with urllib.request.urlopen(req, timeout=90) as r:
    blob = r.read()
    print("range_status:", r.status, "| content-range:", r.headers.get("Content-Range"),
          "| got:", len(blob), "bytes")

if blob[:4] != b"PK\x03\x04":
    print("NOT a zip local header:", blob[:8].hex())
    sys.exit(1)

(sig, ver, flags, method, mtime, mdate, crc, csize, usize,
 nlen, elen) = struct.unpack("<IHHHHHIIIHH", blob[:30])
name = blob[30:30+nlen].decode("utf-8", "replace")
print(f"member={name!r} method={method} csize={csize} usize={usize} flags={flags:#x}")

data = blob[30+nlen+elen:]
if method == 8:
    d = zlib.decompressobj(-15)
    try:
        out = d.decompress(data, 400000)
    except zlib.error as e:
        print("inflate stopped (expected on truncated stream):", e)
        out = b""
        # retry byte-by-byte trim: find the longest usable prefix
        step = max(1, len(data) // 64)
        for cut in range(len(data), 0, -step):
            try:
                out = zlib.decompressobj(-15).decompress(data[:cut], 400000)
                if out:
                    break
            except zlib.error:
                continue
    print("inflated prefix bytes:", len(out))
elif method == 0:
    out = data
    print("stored member; prefix bytes:", len(out))
else:
    print("unsupported method", method)
    sys.exit(1)

text = out.decode("utf-8-sig", "replace")
lines = text.split("\r\n") if "\r\n" in text[:10000] else text.split("\n")
print("\n== HEADER ==")
print(lines[0])
print("\n== FIRST ROWS ==")
for ln in lines[1:4]:
    print(ln[:600])
print("\n== line count in prefix ==", len([l for l in lines if l.strip()]))
