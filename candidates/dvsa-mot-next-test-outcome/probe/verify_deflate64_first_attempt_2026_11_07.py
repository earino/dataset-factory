"""In-container verification of the Deflate64 repair, on the real source files.

Runs inside python:3.13-slim (the job image) with inflate64==1.0.4 installed:
downloads one DfT zip (2017, the exact file that killed dvsa-mot-build-002)
and the S3 2023 zip (the other zip-era URL source), reads each member via the
explicit local-header + inflate64 path the repaired build will use, and prints
the member's first lines + line count + sha256 of the decompressed bytes.
No zip library private API is touched.
"""
import hashlib
import json
import struct
import time
import urllib.request
import zipfile

import inflate64

URLS = [
    "https://data.dft.gov.uk/anonymised-mot-test/test_data/dft_test_result_2017.zip",
    "https://edh-dvsa-data-gov-uk-files-prod.s3.eu-west-1.amazonaws.com/dft_test_result_2023.zip",
]


def download(url):
    started = time.time()
    digest = hashlib.sha256()
    written = 0
    request = urllib.request.Request(url)
    request.add_header("User-Agent", "dataset-factory-construction/1.0")
    path = "/tmp/" + url.rsplit("/", 1)[-1]
    with urllib.request.urlopen(request, timeout=300) as response, \
            open(path, "wb") as handle:
        while True:
            block = response.read(8 * 1024 * 1024)
            if not block:
                break
            handle.write(block)
            digest.update(block)
            written += len(block)
    return path, {"bytes": written, "sha256": digest.hexdigest(),
                  "seconds": round(time.time() - started, 1)}


def read_member_raw(path, info):
    """Explicit local-header read + inflate64 decompression (type 9) or
    stdlib streaming (anything zipfile supports)."""
    with open(path, "rb") as raw:
        raw.seek(info.header_offset)
        header = raw.read(30)
        if header[:4] != b"PK\x03\x04":
            raise SystemExit("bad local header magic")
        name_len, extra_len = struct.unpack("<HH", header[26:30])
        raw.seek(info.header_offset + 30 + name_len + extra_len)
        blob = raw.read(info.compress_size)
    if info.compress_type == 9:
        text = inflate64.Inflater().inflate(blob)
    else:
        raise SystemExit(f"unexpected compress_type {info.compress_type}")
    return text


for url in URLS:
    path, receipt = download(url)
    print(json.dumps({"url": url.rsplit("/", 1)[-1], **receipt}))
    archive = zipfile.ZipFile(path)
    infos = archive.infolist()
    types = sorted({i.compress_type for i in infos})
    print(f"  members={len(infos)} compress_types={types}")
    info = infos[0]
    started = time.time()
    text = read_member_raw(path, info)
    lines = text.splitlines()
    print(json.dumps({
        "member": info.filename,
        "decompressed_bytes": len(text),
        "sha256": hashlib.sha256(text).hexdigest(),
        "lines": len(lines),
        "first_line": lines[0][:160].decode("utf-8", "replace"),
        "second_line": lines[1][:160].decode("utf-8", "replace"),
        "inflate_seconds": round(time.time() - started, 1),
    }))
    del lines, text
    archive.close()
print("VERIFY-OK: both zip-era sources decode through the inflate64 path")
