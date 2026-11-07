"""Bounded coordinator probe: does the DVSA S3 origin mirror the DfT 2017-2022
zips, and in what compression? Ranged reads only (S3 answers Range, measured
2026-10-19): HEAD for existence/size, then a 64 KB tail GET per file to read
the end-of-central-directory and the member compress types. Never downloads a
whole file.
"""
import json
import struct
import urllib.request

BASE = "https://edh-dvsa-data-gov-uk-files-prod.s3.eu-west-1.amazonaws.com/"
FILES = [f"dft_test_result_{year}.zip" for year in range(2017, 2024)]
TAIL = 65558          # bytes=-65558 covers EOCD + small central directories


def fetch(url, headers=None):
    request = urllib.request.Request(url, headers=headers or {})
    request.add_header("User-Agent", "dataset-factory-construction/1.0")
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.headers, response.read()


def central_directory(blob):
    """Parse EOCD + central-directory entries from a zip tail."""
    index = blob.rfind(b"PK\x05\x06")
    if index < 0:
        return None
    _, _, _, _, entries, size, offset, _ = struct.unpack(
        "<IHHHHIIH", blob[index:index + 22])
    members = []
    walk = blob.rfind(b"PK\x01\x02")
    while walk >= 0 and len(members) < entries:
        try:
            fixed = blob[walk:walk + 46]
            if len(fixed) < 46 or fixed[:4] != b"PK\x01\x02":
                break
            fields = struct.unpack("<IHHHHHHIIIHHHHHII", fixed)
            compress_type = fields[4]
            name_len, extra_len, comment_len = fields[10], fields[11], fields[12]
            name = blob[walk + 46:walk + 46 + name_len]
            members.append({"name": name.decode("utf-8", "replace"),
                            "compress_type": compress_type})
            walk = blob.rfind(b"PK\x01\x02", 0, walk)
        except Exception:
            break
    return {"entries": entries, "cd_size": size, "cd_offset": offset,
            "parsed": members}


for name in FILES:
    url = BASE + name
    try:
        headers, _ = fetch(url, {"Range": "bytes=0-0"})
        size = headers.get("Content-Range", "?")
    except Exception as error:
        print(json.dumps({"file": name, "exists": False,
                          "error": f"{type(error).__name__}: {str(error)[:120]}"}))
        continue
    try:
        _, tail = fetch(url, {"Range": f"bytes=-{TAIL}"})
        directory = central_directory(tail)
    except Exception as error:
        directory = {"error": f"{type(error).__name__}: {str(error)[:120]}"}
    print(json.dumps({"file": name, "exists": True, "size": size,
                      "total_bytes": size.split("/")[-1] if size else None,
                      "directory": directory}, indent=1)[:900])
