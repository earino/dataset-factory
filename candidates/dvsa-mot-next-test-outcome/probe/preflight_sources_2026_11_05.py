#!/usr/bin/env python3
"""Preflight source probe for dvsa-mot-next-test-outcome (coordinator, ranged reads only).

Measures, without any bulk download (every response is a bounded Range request):

  * the exact CKAN resource URLs for the per-year result files (DfT 2005-2022,
    DVSA 2023-2024), with formats and recorded sizes;
  * the zip central directory (member names + sizes) of one mid-window DfT year
    (2019), one late DfT year (2022) and the DVSA 2023 zip;
  * the first rows of the 2010 and 2005 txt.gz files (delimiter, header, result
    codes present in the pre-2018 era);
  * the first rows of the first member of the 2019 and 2023 zips (schema and
    result codes in the 2017-2022 and 2023+ eras).

Total transfer is bounded to a few MB, mirroring the 2026-10-19 probes.
"""
import json
import struct
import sys
import urllib.request
import zlib

CKAN = "https://ckan.publishing.service.gov.uk/api/3/action/package_show?id="
DFT_ID = "e3939ef8-30c7-4ca8-9c7c-ad9475cc9b2f"
DVSA_ID = "c63fca52-ae4c-4b75-bab5-8b4735e1a4c9"
TIMEOUT = 30


def fetch(url, start=None, end=None, max_bytes=None):
    """GET or ranged GET; returns (status, headers, body bytes actually read)."""
    request = urllib.request.Request(url)
    if start is not None:
        request.add_header("Range", f"bytes={start}-{end}")
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        body = response.read(max_bytes) if max_bytes else response.read()
        return response.status, dict(response.headers), body


def head_total(url):
    """Content-Length via a 1-byte ranged read (Content-Range gives the total)."""
    try:
        _, headers, body = fetch(url, start=0, end=0)
        content_range = headers.get("Content-Range", "")
        if "/" in content_range:
            return int(content_range.split("/")[-1])
        return int(headers.get("Content-Length", "-1"))
    except Exception as exc:  # noqa: BLE001 - probe reports failures, never dies
        return f"ERROR {exc}"


def zip_central(url):
    """EOCD + central directory via ranged reads: member names and sizes."""
    total = head_total(url)
    if not isinstance(total, int):
        return {"error": total}
    _, _, tail = fetch(url, start=max(0, total - 65536), end=total - 1)
    eocd = tail.rfind(b"PK\x05\x06")
    if eocd < 0:
        return {"error": "no EOCD in the last 64 KiB", "total_bytes": total}
    count, _, size, offset = struct.unpack("<HHII", tail[eocd + 10:eocd + 22])
    _, _, directory = fetch(url, start=offset, end=offset + size - 1)
    members = []
    cursor = 0
    while cursor + 46 <= len(directory) and directory[cursor:cursor + 4] == b"PK\x01\x02":
        (method, _, _, _, _, _, crc, compressed, uncompressed,
         name_len, extra_len, comment_len) = struct.unpack(
            "<HHHHHIIIHHHH", directory[cursor + 4:cursor + 46])
        name = directory[cursor + 46:cursor + 46 + name_len].decode("utf-8", "replace")
        members.append({"name": name, "bytes_uncompressed": uncompressed,
                        "bytes_compressed": compressed, "method": method,
                        "local_header_offset": struct.unpack(
                            "<I", directory[cursor + 42:cursor + 46])[0]})
        cursor += 46 + name_len + extra_len + comment_len
    return {"total_bytes": total, "members": members[:40], "member_count": len(members),
            "declared_entries": count}


def zip_first_rows(url, member, max_rows=6, budget=400000):
    """Decompress the start of one zip member via ranged reads."""
    info = zip_central(url)
    if "error" in info or not info.get("members"):
        return {"error": info.get("error", "no members"), "detail": info}
    target = info["members"][0] if member is None else next(
        (m for m in info["members"] if m["name"] == member), None)
    if target is None:
        return {"error": f"member {member!r} not found", "names": [m["name"] for m in info["members"]]}
    _, _, chunk = fetch(url, start=target["local_header_offset"],
                        end=target["local_header_offset"] + budget - 1)
    name_len, extra_len = struct.unpack("<HH", chunk[26:30])
    start = 30 + name_len + extra_len
    decompressor = zlib.decompressobj(-15)
    try:
        text = decompressor.decompress(chunk[start:], 400000)
    except zlib.error as exc:
        return {"error": f"zlib: {exc}"}
    lines = text.decode("utf-8", "replace").splitlines()[:max_rows]
    return {"member": target["name"], "first_rows": lines}


def gz_first_rows(url, max_rows=8, budget=400000):
    """Decompress the start of a remote .gz file via one ranged read."""
    _, _, chunk = fetch(url, start=0, end=budget - 1)
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        text = decompressor.decompress(chunk, 400000)
    except zlib.error as exc:
        return {"error": f"zlib: {exc}"}
    lines = text.decode("utf-8", "replace").splitlines()[:max_rows]
    return {"first_rows": lines, "total_bytes": head_total(url)}


def ckan_resources(package_id):
    _, _, body = fetch(CKAN + package_id)
    payload = json.loads(body)
    result = payload.get("result", {})
    resources = []
    for resource in result.get("resources", []):
        resources.append({"name": resource.get("name"), "format": resource.get("format"),
                          "url": resource.get("url"),
                          "size": resource.get("size")})
    return {"license": result.get("license_title"),
            "organization": (result.get("organization") or {}).get("name"),
            "resources": resources}


def pick(resources, needle):
    for resource in resources:
        if needle in (resource.get("url") or ""):
            return resource["url"]
    return None


def main():
    ckan_only = "--ckan-only" in sys.argv
    report = {"measured_at_utc": None}
    import datetime
    report["measured_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    dft = ckan_resources(DFT_ID)
    dvsa = ckan_resources(DVSA_ID)
    report["dft_resources"] = dft["resources"]
    report["dvsa_resources"] = dvsa["resources"]
    out = "preflight_result_2026_11_05.json"
    with open(out, "w") as handle:
        json.dump(report, handle, indent=1)
    print(json.dumps({"dft_license": dft["license"], "dft_resource_count": len(dft["resources"]),
                      "dvsa_license": dvsa["license"], "dvsa_resource_count": len(dvsa["resources"]),
                      "written": out}, indent=1))
    print(json.dumps({"dft": [r["url"] for r in dft["resources"]],
                      "dvsa": [r["url"] for r in dvsa["resources"]]}, indent=1))
    if ckan_only:
        return report
    # NOTE (measured 2026-11-05): data.dft.gov.uk IGNORES Range headers - a ranged
    # probe pulls whole multi-GB files through the client. Only the DVSA S3 origin
    # answers ranged reads; DfT-era schemas are measured on the worker instead.

    probes = {}
    steps = [("dft_2019_zip", "dft", "dft_test_result_2019", "zip_rows"),
             ("dft_2022_zip_shape", "dft", "dft_test_result_2022", "zip_shape"),
             ("dft_2010_txt_gz", "dft", "test_result_2010", "gz"),
             ("dft_2005_txt_gz", "dft", "test_result_2005", "gz"),
             ("dvsa_2023_zip", "dvsa", "(2023)", "zip_rows")]
    sources = {"dft": dft, "dvsa": dvsa}
    for key, package, needle, kind in steps:
        print(f"probe {key} ...", flush=True)
        url = pick(sources[package]["resources"], needle)
        if not url:
            probes[key] = {"error": f"url for {needle!r} not found"}
            continue
        try:
            if kind == "zip_rows":
                probes[key] = {"url": url, **zip_first_rows(url, None)}
            elif kind == "zip_shape":
                probes[key] = {"url": url, **zip_central(url)}
            else:
                probes[key] = {"url": url, **gz_first_rows(url)}
        except Exception as exc:  # noqa: BLE001 - report and continue
            probes[key] = {"url": url, "error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps({key: {k: v for k, v in probes[key].items()
                                 if k != "first_rows"}}), flush=True)
    report["probes"] = probes
    print(json.dumps(probes, indent=1))
    return report


if __name__ == "__main__":
    data = main()
    out = "preflight_result_2026_11_05.json"
    with open(out, "w") as handle:
        json.dump(data, handle, indent=1)
    print(f"written: {out}")
