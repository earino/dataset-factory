#!/usr/bin/env python3
"""HEAD all rapidrail + komuter year editions (parquet + csv) 2026-11-07."""
import urllib.request
import urllib.error

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/131.0"}

urls = []
for y in range(2020, 2027):
    urls.append(f"https://storage.data.gov.my/transportation/ktmb/komuter_{y}.parquet")
for y in range(2023, 2027):
    urls.append(f"https://storage.data.gov.my/transportation/rail/rapidrail_{y}_daily.parquet")
    urls.append(f"https://storage.data.gov.my/transportation/rail/rapidrail_{y}_daily.csv")
for y in range(2023, 2027):
    urls.append(f"https://storage.data.gov.my/transportation/ktmb/komuter_{y}.csv")

for u in urls:
    name = u.split("/")[-1]
    try:
        req = urllib.request.Request(u, headers=UA, method="HEAD")
        with urllib.request.urlopen(req, timeout=45) as r:
            print(f"{name:38s} {r.status} len={r.headers.get('Content-Length'):>12} lm={r.headers.get('Last-Modified')}")
    except urllib.error.HTTPError as e:
        print(f"{name:38s} HTTPError {e.code}")
    except Exception as e:
        print(f"{name:38s} ERROR {type(e).__name__}")
