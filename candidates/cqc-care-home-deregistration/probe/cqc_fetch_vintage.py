#!/usr/bin/env python3
"""Fetch one historical CQC 'HSCA Active Locations' vintage from the Drive archive.

Proves anonymous downloadability of archived vintages; pins sha256.
"""
import hashlib
import os
import sys
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

TARGETS = [
    ("active_2024_01.ods", "1WsUwZAarJARNYwPLnlZ5C1p1dooRBX61"),  # 05 January 2024 HSCA Active Locations.ods
    ("active_now.ods", None),  # current filters file straight from cqc.org.uk
]
CURRENT_URL = "https://www.cqc.org.uk/system/files/2026-11/02_November_2026_HSCA_Active_Locations.ods"


def drive_url(fid):
    return f"https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t"


def fetch(name, url):
    here = os.path.dirname(os.path.abspath(__file__))
    dest = os.path.join(here, "cqc_dl", name)
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        print(f"{name}: cached {os.path.getsize(dest)} bytes")
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r, open(dest + ".part", "wb") as f:
        total = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
    with open(dest + ".part", "rb") as f:
        head = f.read(4)
    if head[:2] != b"PK":
        with open(dest + ".part", "rb") as f:
            snippet = f.read(400).decode("utf-8", "replace")
        print(f"{name}: NOT a zip (magic {head!r}): {snippet[:200]}")
        os.remove(dest + ".part")
        return
    os.replace(dest + ".part", dest)
    h = hashlib.sha256(open(dest, "rb").read()).hexdigest()
    print(f"{name}: {total} bytes sha256={h[:16]}... from {url[:80]}")


def main():
    for name, fid in TARGETS:
        if fid:
            fetch(name, drive_url(fid))
        else:
            fetch(name, CURRENT_URL)


if __name__ == "__main__":
    sys.exit(main())
