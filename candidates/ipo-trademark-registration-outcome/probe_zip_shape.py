# Probe: ranged zip reads of the IPO trade mark domestic snapshot - shape, header, dates.
# Bounded: HEAD both zips + first 1 MiB of the domestic zip + central directory.
# Run 2026-10-27. Reproduces the zip-shape rows of notes.md.
import urllib.request, zlib, struct, json

URL = "https://assets.publishing.service.gov.uk/media/5a82e5f4e5274a2e87dc387d/opendatadomestic.zip"
IR = "https://assets.publishing.service.gov.uk/media/5a82a5f4e5274a2e8ab589f5/opendataIR.zip"

def head(url):
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=30) as r:
        return {k: r.headers.get(k) for k in ("Content-Length", "Last-Modified")}

def ranged(url, start, end=None):
    h = {"Range": f"bytes={start}-{end}" if end else f"bytes={start}-"}
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

for u in (URL, IR):
    print("HEAD", u.rsplit("/", 1)[-1], head(u))

blob = ranged(URL, 0, (1 << 20) - 1)
nlen, elen = struct.unpack("<HH", blob[26:30])
name = blob[30:30 + nlen].decode("utf-8", "replace")
print("member:", name)
d = zlib.decompressobj(-15)
txt = d.decompress(blob[30 + nlen + elen:], 1 << 24).decode("utf-16-le", "replace")
lines = txt.split("\r")
cols = lines[0].strip("\n").split("|")
print("ncols:", len(cols))
print("header:", json.dumps(cols))
print("first row (first 14 fields):", json.dumps(lines[1].strip("\n").split("|")[:14], ensure_ascii=False))
print("rows visible in first-MiB window:", len(lines) - 1)

req = urllib.request.Request(URL, headers={"Range": "bytes=-65536"})
with urllib.request.urlopen(req, timeout=60) as r:
    tail = r.read()
entries = []
j = tail.find(b"PK\x01\x02")
while j >= 0 and len(entries) < 10:
    unc, csize = struct.unpack("<II", tail[j + 24:j + 28] + tail[j + 20:j + 24])
    nl = struct.unpack("<H", tail[j + 28:j + 30])[0]
    nm = tail[j + 46:j + 46 + nl].decode("utf-8", "replace")
    entries.append([nm, unc, csize])
    j = tail.find(b"PK\x01\x02", j + 46 + nl)
print("central entries (name, uncompressed, compressed):", json.dumps(entries))
