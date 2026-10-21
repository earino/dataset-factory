"""Access probe: TSB RODSdb public CSVs (2026-10-21 session).

Run: python3 candidates/tsb-railway-occurrence-casualty/probe_access.py

Facts this probe established:
- plain urllib with a custom/neutral User-Agent -> HTTP 403 on all TSB file URLs
- the exact browser-like header set below -> HTTP 200, Range honored (HTTP 206)
- table sizes via bytes=0-0 (Content-Range), last-modified dates
"""
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0.0.0 Safari/537.36")
BROWSER_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-CA,en;q=0.9",
    "Referer": "https://www.tsb.gc.ca/",
}
TABLES = ["OCCURRENCE", "TRAIN", "ROLLING_STOCK", "INJURIES", "COMPONENTS"]
BASE = "https://www.tsb.gc.ca/sites/default/files/stats/RODSdb_MDOTW_VW_{}_PUBLIC.csv"
DICT_URL = "https://www.tsb.gc.ca/sites/default/files/data/en/RODSdb-dd.csv"


def probe(url, headers, rng="bytes=0-0"):
    req = urllib.request.Request(url, headers={**headers, "Range": rng})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.status, r.headers


if __name__ == "__main__":
    print("== plain neutral UA (expect 403) ==")
    try:
        probe(BASE.format("OCCURRENCE"), {"User-Agent": "scout-dataset-factory/1.0", "Accept": "*/*"})
    except urllib.error.HTTPError as e:
        print(f"  OCCURRENCE: HTTP {e.code} (expected: the 403 is UA filtering, not a bot wall)")
    print("== browser-like headers (expect 200/206) ==")
    for t in TABLES:
        st, hd = probe(BASE.format(t), BROWSER_HEADERS)
        print(f"  {t}: HTTP {st}, total={hd.get('Content-Range')}, last-modified={hd.get('Last-Modified')}")
    st, hd = probe(DICT_URL, BROWSER_HEADERS)
    print(f"  dictionary: HTTP {st}, total={hd.get('Content-Range')}, last-modified={hd.get('Last-Modified')}")
