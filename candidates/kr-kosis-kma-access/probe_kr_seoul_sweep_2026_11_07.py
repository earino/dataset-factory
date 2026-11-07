#!/usr/bin/env python3
"""Probe recipe: Seoul Open Data Plaza keyword sweep for event-grain registers
outside the bench's existing task families (East Asia tick 2026-11-07).

Background: kr-kosis-kma-access is parked with the gate 'a Seoul candidate needs
no operator credential; the remaining gate is task-family crowding - the catalog
must be enumerated for an event-grain register outside the bench's existing
families before any candidate opens' (record.next_action). This script performs
the bounded keyword sweep that answers it, anonymously, from the coordinator.

Mechanism: the portal's search form posts to /dataList/datasetList.do
(name=datasetMVO, hidden pageIndex/sortColBy, searchValue) and the result page is
server-rendered; a plain-client POST with matching form fields reproduces what
the browser shows (browser-verified 2026-11-07: '사고' -> 검색결과 67건).

Output: for each keyword - result count, and titles of the first ~12 result
cards with their category tag. Read-only; no bulk download.

Usage: python3 probe_kr_seoul_sweep_2026_11_07.py
"""
import re
import sys
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) discovery-probe"
BASE = "https://data.seoul.go.kr/dataList/datasetList.do"

# Families to exclude (bench carries them) are NOT keywords here: the sweep
# targets families the bench lacks. Each keyword names a candidate family.
KEYWORDS = [
    "사고",        # accident (any event-grain incident register?)
    "재난",        # disaster incidents
    "응급",        # emergency medical / EMS
    "화재",        # fire incidents
    "붕괴",        # structural failure
    "감염",        # infection (event grain, not weekly bulletin)
    "식중독",      # food poisoning events
    "리콜",        # product recalls
    "민원",        # civil complaints (per-complaint lifecycle)
    "도로 노면",   # road surface defects / potholes
    "공사 지연",   # construction delay
    "지하수",      # groundwater
    "도시가스",    # gas safety incidents
    "엘리베이터",  # elevator incidents
    "전력 사고",   # power incidents
    "항공",        # aviation events
]


def post_search(keyword, timeout=40):
    body = urllib.parse.urlencode({
        "pageIndex": "1",
        "sortColBy": "R",
        "searchValue": keyword,
    }).encode()
    req = urllib.request.Request(
        BASE, data=body,
        headers={"User-Agent": UA,
                 "Content-Type": "application/x-www-form-urlencoded"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def parse_results(html):
    m = re.search(r"검색결과\s*([0-9,]+)건", html)
    count = int(m.group(1).replace(",", "")) if m else None
    # result cards: <dl class="type-a"> blocks; title is the first long text run
    blocks = re.split(r'<dl class="type-a">', html)[1:]
    titles = []
    for b in blocks[:12]:
        text = re.sub(r"<[^>]+>", " ", b)
        text = re.sub(r"\s+", " ", text).strip()
        # keep the dataset title: text before '수정일자'
        cut = text.split("수정일자")[0]
        # drop the category bracket token and file-type tokens at the end
        cut = re.sub(r"^(통계|공공데이터)\s*\[[^\]]*\]\s*", "", cut)
        cut = re.sub(r"\s(SHEET|CHART|OPENAPI|FILE|LINK|AI친화)+\s*$", "", cut)
        cut = cut[:110]
        if cut:
            titles.append(cut)
    return count, titles


def main():
    for kw in KEYWORDS:
        try:
            status, html = post_search(kw)
            count, titles = parse_results(html)
            print(f"\n=== {kw!r}: HTTP {status}, 검색결과 {count}건")
            for t in titles:
                print("   -", t)
            sys.stdout.flush()
        except Exception as exc:  # noqa: BLE001 - probe records the failure
            print(f"\n=== {kw!r}: FAILED {exc!r}")


if __name__ == "__main__":
    main()
