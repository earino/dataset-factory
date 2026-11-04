#!/usr/bin/env python3
"""Probe recipe: Seoul Open Data Plaza access + per-dataset licence (2026-11-04).

Reproduces the measurement recorded in candidates/kr-kosis-kma-access/record.json
under measurements.seoul_portal_probe_2026_11_04. Read-only, anonymous, no bulk
transfer; the file-download step documents the JS-mediated POST that rejects naive
clients (it is expected to FAIL with the alert '잘못된 접근입니다...' - that IS the
recorded result, not a bug).

Usage: python3 probe_kr_seoul_2026_11_04.py
"""
import io
import re
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) discovery-probe"


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


def post(url, data, referer, timeout=40):
    body = "&".join(f"{k}={v}" for k, v in data.items()).encode()
    req = urllib.request.Request(url, data=body, headers={
        "User-Agent": UA, "Referer": referer,
        "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


def main():
    st, home = get("https://data.seoul.go.kr/")
    print(f"homepage: HTTP {st}, {len(home)} bytes (server-rendered nav expected)")
    url = "https://data.seoul.go.kr/dataList/OA-23105/S/1/datasetView.do"
    st, ds = get(url)
    text = ds.decode("utf-8", "replace")
    print(f"dataset page OA-23105: HTTP {st}, {len(ds)} bytes")
    # licence instrument: the metadata block's use-permission scope
    m = re.search(r"이용허락범위[^가-힣]*([^<]{2,60})", text)
    print("이용허락범위 (use-permission scope):", m.group(1).strip() if m else "not found")
    for kw in ("저작권자", "제3저작권자"):
        i = text.find(kw)
        print(f"{kw}:", re.sub(r'<[^>]+>', ' ', text[i:i + 220]).split()[1] if i >= 0 else "?")
    # catalog: AJAX shell (nav only) - enumeration needs the supported browser
    st, lst = get("https://data.seoul.go.kr/dataList/datasetList.do?datasetKind=1&searchFlag=M")
    print(f"datasetList.do: HTTP {st}, {len(lst)} bytes (shell; "
          f"{'nav-only' if b'datasetView' not in lst else 'has items'})")
    # file download: JS-mediated POST; naive parameterised access is REJECTED
    st, dl = post("https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?&useCache=false",
                  {"infId": "OA-23105", "infSeq": "1", "seq": "1"},
                  referer="https://data.seoul.go.kr/dataList/OA-23105/S/1/datasetView.do")
    alert = re.search(rb"alert\('(.*?)'\)", dl)
    print(f"nio_download.do: HTTP {st}, naive POST -> "
          f"{alert.group(1).decode('utf-8', 'replace') if alert else dl[:60]!r} "
          "(expected failure: bulk download must go through the supported browser)")


if __name__ == "__main__":
    main()
