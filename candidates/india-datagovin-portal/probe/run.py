"""Discovery probe: can an EU (Helsinki, Hetzner) network reach data.gov.in / api.data.gov.in?

Recorded unpark step for candidates/india-datagovin-portal (network reachability was the
recorded blocker; the coordinator network gets TCP-refused). Read-only: a bounded set of
HTTP GETs, no bulk transfer, no credentials. Writes one compact JSON report to /output.
"""
import json
import socket
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"

TARGETS = [
    "https://www.data.gov.in/",
    "https://data.gov.in/",
    "https://api.data.gov.in/",
    # if the portal answers, a bounded first look at machine-readable catalog surfaces:
    "https://www.data.gov.in/robots.txt",
    "https://www.data.gov.in/sitemap.xml",
    "https://www.data.gov.in/catalogs",
    "https://api.data.gov.in/catalog.json",
]


def fetch(url, timeout=30):
    rec = {"url": url}
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(400_000)
            rec.update(
                status=r.status,
                final_url=r.url,
                bytes_seen=len(body),
                content_type=r.headers.get("Content-Type", ""),
                server=r.headers.get("Server", ""),
                body_head=body[:400].decode("utf-8", "replace"),
            )
    except urllib.error.HTTPError as e:
        rec.update(status=e.code, error="HTTPError", body_head=e.read(400)[:400].decode("utf-8", "replace"))
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        rec.update(status=None, error=f"{type(e).__name__}: {e}")
    rec["seconds"] = round(time.time() - t0, 3)
    return rec


def main():
    report = {
        "probe": "india-portal-probe-001",
        "purpose": "EU-network reachability probe for data.gov.in / api.data.gov.in (coordinator network is TCP-refused)",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "vantage": fetch("https://api.ipify.org?format=json", timeout=20),
        "results": [],
    }
    for url in TARGETS:
        report["results"].append(fetch(url))
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    with open("/output/probe_report.json", "w") as fh:
        json.dump(report, fh, indent=1)
    for r in report["results"]:
        print(r["url"], "->", r.get("status"), r.get("error") or r.get("bytes_seen"))


if __name__ == "__main__":
    main()
