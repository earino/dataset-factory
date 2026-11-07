#!/usr/bin/env python3
"""Header + head-of-file probes across rapidrail editions (2026-11-07).

Checks: identical schema across 2023/2024/2025/2026; whether 'A0: All Stations'
appears as an ORIGIN anywhere at the head of a file; first/last dates per edition.
Bounded: ~10 Range requests of <=32 KB.
"""
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/131.0"}


def head_and_tail(url, nbytes=24_000):
    req = urllib.request.Request(url, headers={**UA, "Range": f"bytes=0-{nbytes-1}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        head = r.read()
    req = urllib.request.Request(url, method="HEAD", headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        size = int(r.headers["Content-Length"])
        lm = r.headers.get("Last-Modified")
    req = urllib.request.Request(url, headers={**UA, "Range": f"bytes={size-nbytes}-{size-1}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        tail = r.read()
    return head.decode("utf-8", "replace"), tail.decode("utf-8", "replace"), size, lm


files = {
    "2023": "https://storage.data.gov.my/transportation/rail/rapidrail_2023_daily.csv",
    "2025": "https://storage.data.gov.my/transportation/rail/rapidrail_2025_daily.csv",
    "2026": "https://storage.data.gov.my/transportation/rail/rapidrail_2026_daily.csv",
}
for yr, url in files.items():
    head, tail, size, lm = head_and_tail(url)
    hl = [l for l in head.splitlines() if l][:14]
    tl = [l for l in tail.splitlines() if l][-6:]
    print(f"== rapidrail_{yr}_daily.csv  size={size:,} lm={lm}")
    print("   head:", hl[0])
    for l in hl[1:8]:
        print("      ", l[:100])
    print("   tail:")
    for l in tl:
        print("      ", l[:100])
    a0_origin = sum(1 for l in hl[1:] if l.startswith("A0"))
    print(f"   A0-as-origin rows in head sample: {a0_origin}")
    print()
