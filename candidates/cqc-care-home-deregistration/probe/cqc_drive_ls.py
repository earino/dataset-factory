#!/usr/bin/env python3
"""Probe CQC Drive archive year subfolders (anonymous embeddedfolderview).

Pass a folder id (and optional resourcekey); lists entries with their links so
year-subfolder ids can be re-listed to file level.
"""
import re
import sys
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

def fetch(folder_id, resourcekey=None):
    url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
    if resourcekey:
        url += f"&resourcekey={resourcekey}"
    url += "#list"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read().decode("utf-8", "replace")

ENTRY_RE = re.compile(r'<a[^>]+href="(https://drive\.google\.com/(?:drive/folders|file/d)/[^"]+)"[^>]*>.*?flip-entry-title">([^<]+)</div>', re.S)

if __name__ == "__main__":
    fid = sys.argv[1]
    rk = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        status, html = fetch(fid, rk)
        entries = ENTRY_RE.findall(html)
        print(f"status={status} entries={len(entries)}")
        for href, name in entries[:80]:
            print(f"  {name!r} -> {href}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
