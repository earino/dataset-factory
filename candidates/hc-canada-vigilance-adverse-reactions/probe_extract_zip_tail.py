#!/usr/bin/env python3
"""Canada Vigilance extract_extrait.zip central-directory probe.

Downloads ONLY the last 128 KiB of the 313.6 MB ZIP (range request), parses the
end-of-central-directory + central directory to list member files and their
uncompressed sizes. Bounded: <=128 KiB transferred. Saves the raw tail too.
"""
import io
import json
import struct
import urllib.request

UA = {"User-Agent": "scout-discovery/1.0 (dataset-factory research)"}
ZIP_URL = ("https://open.canada.ca/data/dataset/9cbaef00-b52c-4a70-9fed-d9aa8263ab74/"
           "resource/2e736909-ef1f-4d60-bfb6-f15b3be3b1fa/download/extract_extrait.zip")
TAIL = 131072  # 128 KiB


def main():
    total = 313578432  # measured HEAD, 2026-10-27
    start = max(0, total - TAIL)
    req = urllib.request.Request(ZIP_URL, headers={**UA, "Range": f"bytes={start}-{total-1}"})
    with urllib.request.urlopen(req, timeout=90) as r:
        buf = r.read()
    print(f"range fetch: status={r.status} bytes={len(buf)} content-range={r.headers.get('Content-Range')}")
    open("zip_tail.bin", "wb").write(buf)

    # find EOCD
    eocd = buf.rfind(b"PK\x05\x06")
    if eocd < 0:
        print("no EOCD in tail - tail too small; increase TAIL")
        return
    (sig, disk, cd_disk, n_disk, n_total, cd_size, cd_off, cmt_len) = struct.unpack(
        "<IHHHHIIH", buf[eocd:eocd+22])
    print(f"EOCD: entries={n_total} cd_size={cd_size} cd_offset={cd_off}")
    # central directory may start before our tail window
    if eocd - cd_size < 0:
        print("central directory truncated in window; re-fetch with larger tail")
        return
    cd = buf[eocd - cd_size:eocd]
    members = []
    p = 0
    while p + 46 <= len(cd) and cd[p:p+4] == b"PK\x01\x02":
        (nm_len, ex_len, cm_len) = struct.unpack("<HHH", cd[p+28:p+34])
        usize, csize = struct.unpack("<II", cd[p+24:p+32])
        name = cd[p+46:p+46+nm_len].decode("cp437", "replace")
        members.append({"name": name, "uncompressed": usize, "compressed": csize})
        p += 46 + nm_len + ex_len + cm_len
    with open("zip_members.json", "w") as f:
        json.dump({"total_entries": n_total, "members": members}, f, indent=1)
    print(f"parsed {len(members)} entries (of {n_total})")
    for m in members:
        print(f"  {m['name']:40s} {m['uncompressed']:>13,d} B  ({m['compressed']:>11,d} B)")


if __name__ == "__main__":
    main()
