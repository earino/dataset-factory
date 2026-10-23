#!/usr/bin/env python3
"""Repro: Ghana data.gov.gh access probes (gh-opendata-coverage).
Expect connection refused on the CKAN action API from this coordinator. Run from anywhere."""
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research-probe/1.0"}

for u in ("https://data.gov.gh/api/3/action/package_list",
          "https://data.gov.gh/data/api/3/action/package_list"):
    req = urllib.request.Request(u, headers={**UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read(400_000)
            print(u, "->", r.status, f"({len(body)} B)  [PORTAL IS REACHABLE - update the record]")
    except urllib.error.HTTPError as e:
        print(u, "-> HTTP", e.code, "[reachable but errored - re-probe]")
    except Exception as e:
        print(u, "-> FAILED:", e)

print("\nIf both fail, the recorded evidence stands: the portal is unreachable from this")
print("network. Retry from a worker (different ASN) before closing Ghana; also try the")
print("browser for the human catalogue. Access failure is not a scientific rejection.")
