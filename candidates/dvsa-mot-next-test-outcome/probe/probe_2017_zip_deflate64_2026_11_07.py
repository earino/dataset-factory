"""Worker-side bounded probe: identify the compression method blocking the 2017
DfT zip. Downloads one file (data.dft.gov.uk ignores Range, measured
2026-11-05), reads the central directory, tries one member read, deletes the
file. Runs on the idle dvsa-mot-build-002 worker; output is the evidence.
"""
import hashlib
import json
import time
import urllib.request
import zipfile
from pathlib import Path

URL = "https://data.dft.gov.uk/anonymised-mot-test/test_data/dft_test_result_2017.zip"
DEST = Path("/tmp/probe_2017.zip")

started = time.time()
digest = hashlib.sha256()
written = 0
request = urllib.request.Request(URL)
request.add_header("User-Agent", "dataset-factory-construction/1.0")
with urllib.request.urlopen(request, timeout=300) as response, \
        DEST.open("wb") as handle:
    while True:
        block = response.read(8 * 1024 * 1024)
        if not block:
            break
        handle.write(block)
        digest.update(block)
        written += len(block)
print(json.dumps({"url": URL, "bytes": written,
                 "sha256": digest.hexdigest(),
                 "seconds": round(time.time() - started, 1)}))

archive = zipfile.ZipFile(DEST)
infos = archive.infolist()
print("members:", len(infos))
for info in infos[:5]:
    print(json.dumps({"name": info.filename, "compress_type": info.compress_type,
                      "file_size": info.file_size,
                      "compress_size": info.compress_size}))
print("compress_types present:",
      sorted({info.compress_type for info in infos}))
try:
    with archive.open(infos[0]) as member:
        print("first line:", member.readline()[:200])
    print("READ-OK")
except Exception as error:
    print("READ-FAILED:", type(error).__name__, str(error)[:200])
DEST.unlink()
print("probe file deleted")
