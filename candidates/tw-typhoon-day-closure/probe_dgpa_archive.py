#!/usr/bin/env python3
"""Probe: DGPA historical closure archive - depth, pagination, attachment formats (2026-10-22).

Run: python3 candidates/tw-typhoon-day-closure/probe_dgpa_archive.py [--full]

The DGPA host fails strict SSL validation (chain missing Subject Key Identifier), so the
probe uses an unverified context - record this in the construction script.
"""
import re
import ssl
import sys
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (scout-research; dataset-factory)"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
BASE = "https://www.dgpa.gov.tw"

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40, context=CTX) as r:
        return r.read()

def list_items(page):
    html = get(f"{BASE}/informationlist?uid=374&pgnum=50&page={page}").decode("utf-8", "replace")
    out = []
    for m in re.finditer(r'href="information\?uid=374&(?:amp;)?pid=(\d+)"[\s\S]{0,140}?<dt>([\d.]+)</dt>\s*<dd>\s*<p>\s*(\d+年\S+日)', html):
        out.append((m.group(1), m.group(2), m.group(3)))
    return out

pages = [1, 50] if "--full" not in sys.argv else range(1, 51)
for pg in pages:
    for pid, d, title in list_items(pg):
        det = get(f"{BASE}/information?uid=374&pid={pid}").decode("utf-8", "replace")
        atts = [a.replace("&amp;", "&") for a in re.findall(r'href="(/FileConversion[^"]+)"', det)]
        kinds = []
        for a in atts:
            raw = get(BASE + a)
            kinds.append(f"{len(raw)}B:" + ("table" if sum(1 for c in [\"臺北市\", \"台北市\", \"高雄市\", \"照常辦公\", \"停止辦公\"] if c.encode() in raw or c in raw.decode("utf-8", "replace")) >= 2 else "shell"))
        print(d, "pid=" + pid, "|".join(kinds))
