#!/usr/bin/env python3
"""Repro: Nigeria NBS terms-clause probe (ng-nbs-state-price-exceedance).
Read-only GETs; prints the decisive no-redistribution clause. Run from anywhere."""
import re
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research-probe/1.0"}

def get(url, timeout=25, max_read=400_000):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(max_read).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, str(e)
    except Exception as e:
        return None, f"FAILED: {e}"

st, txt = get("https://nigerianstat.gov.ng/")
print("nigerianstat.gov.ng homepage:", st)
for href, label in re.findall(r'href="([^"]*)"[^>]*>([^<]*(?:Terms|Open Data)[^<]*)<', txt or "", re.I):
    print("  footer link:", label.strip()[:30], "->", href)

st, txt = get("https://nigerianstat.gov.ng/page/terms")
print("\n/page/terms:", st)
i = (txt or "").find("will not be redistributed")
if i >= 0:
    seg = re.sub(r"<[^>]+>", " ", txt[max(0, i - 500):i + 700])
    seg = re.sub(r"\s+", " ", seg)
    print("\nDECISIVE CLAUSE:\n  ..." + seg + "...")
else:
    print("clause NOT found - re-read the page before relying on the record")

print("\nlegacy ODP host (expect DNS failure):")
print("  nigeria.opendataforafrica.org ->", get("https://nigeria.opendataforafrica.org/", timeout=15)[0])
