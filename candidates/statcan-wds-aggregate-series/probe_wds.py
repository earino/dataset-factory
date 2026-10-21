"""Statistics Canada WDS/catalogue probe (2026-10-21 session).

Run: python3 candidates/statcan-wds-aggregate-series/probe_wds.py

Records the three probes behind the source-class park: WDS developer docs
(anonymous, key-free, 15 methods + SDMX), the data catalogue size, and the
microdata index page's state.
"""
import re
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) Chrome/128.0.0.0 Safari/537.36"


def show(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body.decode("utf-8", "replace")))
        print(f"{url}\n  HTTP {r.status}, {len(body):,} bytes")
        for pat in (r"15 methods", r"13,356", r"SDMX REST", r"public use microdata", r"api key"):
            m = re.search(pat, text, re.I)
            print(f"  /{pat}/: {'FOUND - ' + text[max(0, m.start()-60):m.start()+160] if m else 'not found'}")
    except Exception as e:
        print(f"{url}\n  FAILED {type(e).__name__}: {e}")


show("https://www.statcan.gc.ca/en/developers/wds")
show("https://www150.statcan.gc.ca/n1/en/type/data")
show("https://www.statcan.gc.ca/en/microdata/index")
