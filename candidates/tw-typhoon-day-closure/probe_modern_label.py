#!/usr/bin/env python3
"""Probe: modern-era per-county closure label extraction paths (2026-10-31).

Two questions:
 A. Does the DGPA daily view /typh/daily/nds.html parameterise history (a past date)?
 B. Do county-portal CSVs (Taichung/Taoyuan, listed as related to data.gov.tw 20457)
    give machine-readable historical per-county statuses?

Run: python3 candidates/tw-typhoon-day-closure/probe_modern_label.py
DGPA SSL chain fails strict validation -> unverified context (recorded in probe_dgpa_archive.py).
"""
import re, ssl, sys, urllib.request, urllib.error, json

UA = {"User-Agent": "Mozilla/5.0 (scout-research; dataset-factory)"}
CTX = ssl.create_default_context(); CTX.check_hostname=False; CTX.verify_mode=ssl.CERT_NONE

def get(url, binary=False, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        raw = r.read()
    return raw if binary else raw.decode("utf-8", "replace")

def county_rows(html):
    """Count per-county status rows in a daily-view or attachment HTML."""
    n = 0
    for pat in ("臺北市","台北市","新北市","桃園市","臺中市","高雄市","基隆市"):
        if pat in html: n += 1
    stop = html.count("停止辦公") + html.count("照常辦公")
    return n, stop

# --- A. daily view and its date parameterisation -------------------------------
print("== A. daily view ==")
try:
    today = get("https://www.dgpa.gov.tw/typh/daily/nds.html")
    n, stop = county_rows(today)
    print(f"today view: {len(today)}B, {n}/7 known county names, {stop} status phrases")
    # look for form/query hints in the page
    for m in sorted(set(re.findall(r'(?:name|id|parameter|date|yy|mm|dd|d)=["\']?[\w-]*', today)))[:0]: pass
    hints = sorted(set(re.findall(r'<form[^>]*>', today)))[:5]
    print("forms:", hints)
    hints2 = sorted(set(re.findall(r'href="[^"]*nds[^"]*"', today)))[:10]
    print("nds links:", hints2)
    hints3 = sorted(set(re.findall(r'(?:select|input|option)[^>]*(?:date|ymd|Date)[^>]*>', today)))[:10]
    print("date-ish controls:", hints3)
except Exception as e:
    print("daily view FAILED:", repr(e))

# try date parameter variants on a known closure day: 2024-10-03 (Typhoon Krathon, national closures)
known = [("2024-10-03","1131003"),("2024-10-04","1131004")]
variants = [
    "/typh/daily/nds.html?date=2024-10-03",
    "/typh/daily/nds.html?d=1131003",
    "/typh/daily/nds.html?yy=113&mm=10&dd=3",
    "/typh/daily/nds.html?y=113&m=10&dd=03",
    "/typh/daily/nds.html?ymd=1131003",
    "/typh/daily/nds.html?Date=2024/10/03",
]
for v in variants:
    try:
        h = get("https://www.dgpa.gov.tw" + v)
        n, stop = county_rows(h)
        same = (h == today) if isinstance(today, str) else "?"
        print(f"{v}: {len(h)}B counties={n} statuses={stop} same_as_today={same}")
    except Exception as e:
        print(f"{v}: FAILED {e!r}")

# --- B. data.gov.tw 20457 related datasets -------------------------------------
print("\n== B. data.gov.tw 20457 ==")
for api in [
    "https://data.gov.tw/api/3/action/package_show?id=20457",
    "https://data.gov.tw/api/rest/dataset/20457",
]:
    try:
        j = get(api)
        d = json.loads(j)
        if d.get("success"):
            res = d.get("result", {})
            rel = res.get("related_datasets") or []
            print(api, "-> title:", res.get("title"))
            print("  related:", json.dumps(rel, ensure_ascii=False)[:400])
            for r in res.get("resources", []):
                print("  res:", r.get("format"), (r.get("url") or "")[:110])
        else:
            print(api, "-> success=false")
    except Exception as e:
        print(api, "FAILED", repr(e))
