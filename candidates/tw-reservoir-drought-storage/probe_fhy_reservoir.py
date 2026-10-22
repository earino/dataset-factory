#!/usr/bin/env python3
"""Probe: WRA reservoir history availability (2026-10-22). Documents the 401/HTML results."""
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (scout-research; dataset-factory)"}

for url in ("https://fhy.wra.gov.tw/Api/v2/Event/Year/2025",
            "https://fhy.wra.gov.tw/Api/v2/Event/Active",
            "https://fhy.wra.gov.tw/disaster/Reservoir/Comparison",
            "https://opendata.wra.gov.tw/openapi/swagger/index.html"):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=45) as r:
            body = r.read(400)
            print(url, "->", r.status, "len>=400" if len(body) == 400 else len(body), body[:60])
    except urllib.error.HTTPError as e:
        print(url, "-> HTTP", e.code, e.read()[:80])
    except Exception as e:
        print(url, "->", type(e).__name__, e)
# Expected (2026-10-22): 401 for the /Api/v2/ endpoints, an AngularJS HTML shell for
# Reservoir/Comparison, and an SSL verification failure for opendata.wra.gov.tw.
