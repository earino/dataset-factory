"""RSS-instrumented in-container verification of the Deflate64 member decode.

One file (the 2017 DfT zip), one member, python -u so progress survives a
kill; docker --memory caps the container so a leak surfaces as MemoryError
with output, not a silent host OOM kill.
"""
import hashlib
import json
import struct
import time
import urllib.request
import zipfile

import inflate64

URL = "https://data.dft.gov.uk/anonymised-mot-test/test_data/dft_test_result_2017.zip"


def rss(label):
    peak = current = "?"
    for line in open("/proc/self/status"):
        if line.startswith("VmPeak"):
            peak = line.split()[1] + "kB"
        elif line.startswith("VmRSS"):
            current = line.split()[1] + "kB"
    print(f"[rss] {label}: VmRSS={current} VmPeak={peak}", flush=True)


started = time.time()
digest = hashlib.sha256()
written = 0
path = "/tmp/2017.zip"
request = urllib.request.Request(URL)
request.add_header("User-Agent", "dataset-factory-construction/1.0")
with urllib.request.urlopen(request, timeout=300) as response, \
        open(path, "wb") as handle:
    while True:
        block = response.read(8 * 1024 * 1024)
        if not block:
            break
        handle.write(block)
        digest.update(block)
        written += len(block)
rss("download done")
print(json.dumps({"bytes": written, "sha256": digest.hexdigest(),
                  "seconds": round(time.time() - started, 1)}), flush=True)

archive = zipfile.ZipFile(path)
info = archive.infolist()[0]
print(f"member {info.filename} type={info.compress_type} "
      f"usize={info.file_size} csize={info.compress_size}", flush=True)

with open(path, "rb") as raw:
    raw.seek(info.header_offset)
    header = raw.read(30)
    assert header[:4] == b"PK\x03\x04"
    name_len, extra_len = struct.unpack("<HH", header[26:30])
    raw.seek(info.header_offset + 30 + name_len + extra_len)
    blob = raw.read(info.compress_size)
rss("compressed blob read")
print(f"blob={len(blob)}", flush=True)

t0 = time.time()
text = inflate64.Inflater().inflate(blob)
rss("single-shot inflate done")
print(json.dumps({"decompressed": len(text),
                  "sha256": hashlib.sha256(text).hexdigest(),
                  "seconds": round(time.time() - t0, 1),
                  "expected_size": info.file_size,
                  "size_match": len(text) == info.file_size}), flush=True)

first = text.split(b"\n", 2)
print("line1:", first[0][:120].decode("utf-8", "replace"), flush=True)
print("line2:", first[1][:120].decode("utf-8", "replace"), flush=True)
del text, blob
rss("released")
print("VERIFY-OK", flush=True)
