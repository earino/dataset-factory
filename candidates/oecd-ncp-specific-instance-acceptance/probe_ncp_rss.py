#!/usr/bin/env python3
"""Probe: enumerate the OECD NCP specific-instances database via its RSS channel.

Reproduces the discovery measurement of 2026-11-03 (candidate
oecd-ncp-specific-instance-acceptance, notes.md P1):

  - total item count across RSS pagination (46 x 15 + 10 = 700 at discovery time),
  - the page-size cap (size parameter is clamped to 15),
  - writes nothing; prints the counts and the first/last titles per fetched page.

Bounded by design: pass --max-pages to fetch only the first N pages (default 3).
The full 47-page enumeration is construction work (worker), not a discovery probe.

Channel:
  https://api.oecd.org/webcms/search/rss?siteName=oecd&interfaceLanguage=en&hiddenFacets=siteName%3Amne-guidelines&page=N&size=15
A JSON variant does not exist (api.oecd.org/webcms/search -> HTTP 404, recorded 2026-11-03).
Case pages are client-side rendered; plain curl returns a ~5.7 KB shell — a JS-rendering
client is required for case content (measured 2026-11-03).
"""
import argparse
import sys
import urllib.request
import xml.etree.ElementTree as ET

RSS = ("https://api.oecd.org/webcms/search/rss?siteName=oecd"
       "&interfaceLanguage=en&hiddenFacets=siteName%3Amne-guidelines&page={page}&size={size}")
UA = "Mozilla/5.0 (X11; Linux x86_64) dataset-factory-discovery-probe"


def fetch_page(page: int, size: int = 15) -> list:
    url = RSS.format(page=page, size=size)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    root = ET.fromstring(data)
    items = root.findall(".//item")
    return items


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-pages", type=int, default=3,
                    help="fetch only the first N pages (bounded probe); default 3")
    ap.add_argument("--full", action="store_true",
                    help="enumerate ALL pages until an empty page (construction-time use)")
    args = ap.parse_args()

    total = 0
    page = 0
    limit = 10**9 if args.full else args.max_pages
    while page < limit:
        items = fetch_page(page)
        if not items:
            print(f"page {page}: 0 items (end of feed)")
            break
        total += len(items)
        first = (items[0].findtext("title") or "")[:60]
        last = (items[-1].findtext("title") or "")[:60]
        print(f"page {page}: {len(items)} items | first: {first!r} | last: {last!r}")
        page += 1
    print(f"items fetched: {total}"
          + ("" if args.full else f" (bounded probe, first {args.max_pages} pages; "
             "discovery measured 46x15+10=700 total on 2026-11-03)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
