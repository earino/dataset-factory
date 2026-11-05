# Find archived OpenAQ v2 API responses enumerating INDIAN locations, so CPCB
# locationids in the anonymous S3 archive can be identified without a v3 API key.
import urllib.request, urllib.parse, json, time

UA = {"User-Agent": "Mozilla/5.0 (dataset-factory-discovery/1.0)"}

def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()

# 1. CDX search for any capture of api.openaq.org/v2/locations with country=IN
cdx_urls = [
    "http://web.archive.org/cdx/search/cdx?url=api.openaq.org/v2/locations%3Fcountry%3DIN&matchType=prefix&output=json&collapse=urlkey&limit=500",
    "http://web.archive.org/cdx/search/cdx?url=api.openaq.org/v2/locations&matchType=prefix&output=json&collapse=urlkey&limit=2000&filter=urlkey:.*country.*",
]
for cu in cdx_urls:
    try:
        st, body = get(cdu := cu)
        print(f"CDX ok {st}, {len(body)} B for url={cu[:110]}...")
        txt = body.decode("utf-8", "replace")
        print(txt[:3000])
    except Exception as e:
        print(f"CDX FAIL {type(e).__name__}: {str(e)[:200]} for url={cu[:110]}")
    print("-" * 80)
