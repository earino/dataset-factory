#!/usr/bin/env python3
"""Repro: ZA DWS access + licence-posture probes (za-dws-dam-storage-exceedance).
Read-only GETs; prints the same evidence recorded on 2026-10-23. Run from anywhere."""
import re
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research-probe/1.0",
      "Accept": "text/html,application/json;q=0.8,*/*;q=0.5"}

def probe(url, timeout=25, max_read=120_000):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(max_read)
            return f"{r.status} ({len(body)} B) {r.geturl()[:90]}"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code} {e.reason}"
    except Exception as e:
        return f"FAILED: {e}"

print("DWS terms/bulletins (expect 403 from the coordinator network):")
for u in ("https://www.dws.gov.za/Disclaimer.aspx",
          "https://www.dws.gov.za/Hydrology/Weekly/WeeklyBulletins.aspx"):
    print(" ", u, "->", probe(u))

print("NIWIS / legacy host / national portal:")
for u in ("https://niwis.dws.gov.za/niwis2/",
          "http://www.dwa.gov.za/Hydrology/Weekly/WeeklyBulletins.aspx",
          "https://data.gov.za/"):
    print(" ", u, "->", probe(u))

print("City of Cape Town dam levels (expect 200):")
print(" ", probe("https://www.capetown.gov.za/family-and-home/residential-utility-"
                "services/residential-water-and-sanitation-services/this-weeks-dam-levels/"))

print("Wayback CDX (licence evidence: no archived DWS terms/bulletin pages):")
for u in ("https://web.archive.org/cdx/search/cdx?url=dws.gov.za/Hydrology/Weekly/WeeklyBulletins.aspx&output=json&limit=8",
          "https://web.archive.org/cdx/search/cdx?url=dws.gov.za&matchType=domain&output=json&limit=15&collapse=urlkey"):
    out = probe(u, timeout=40)
    print(" ", u.split("url=")[1][:60], "->", out[:120])
    if out.startswith("200"):
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=40) as r:
            print("   body:", r.read(2000).decode("utf-8", "replace")[:1200])
