#!/usr/bin/env python3
"""Fetch CQC current bulk files (bounded, anonymous) and pin digests."""
import hashlib
import os
import sys
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
FILES = [
    ("dir_csv.zip", "https://www.cqc.org.uk/system/files/2026-10/28_October_2026_CQC_directory.zip"),
    ("deactivated.ods", "https://www.cqc.org.uk/system/files/2026-11/02_November_2026_Deactivated_Locations.ods"),
]

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    for name, url in FILES:
        dest = os.path.join(here, "cqc_dl", name)
        if os.path.exists(dest) and os.path.getsize(dest) > 1000:
            print(f"{name}: cached {os.path.getsize(dest)} bytes")
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=300) as r, open(dest + ".part", "wb") as f:
            total = 0
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                total += len(chunk)
        os.replace(dest + ".part", dest)
        h = hashlib.sha256(open(dest, "rb").read()).hexdigest()
        print(f"{name}: {total} bytes sha256={h[:16]}... from {url}")

if __name__ == "__main__":
    sys.exit(main())
