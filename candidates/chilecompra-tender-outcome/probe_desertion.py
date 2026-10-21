#!/usr/bin/env python3
"""Probe: ChileCompra OCDS access + desertion label base rates on bounded samples.

Measures, anonymously (no ticket, no registration):
  1. Monthly process totals via listaOCDSAgnoMes across the panel years.
  2. For a closed historical month (2019-06) and (2023-06): the first 100
     processes, each award document's statusDetails (the label vocabulary,
     e.g. '7-Desierta (o art. 3 ó 9 Ley 19.886)'), and whether every process
     in a closed month has resolved.
  3. Average tender + award document sizes (bytes) for construction-cost math.

Writes nothing; prints a compact report. Run from the candidate directory:
    python3 probe_desertion.py
"""

import json
import time
import urllib.request

BASE = "https://api.mercadopublico.cl/APISOCDS/OCDS"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

reqs = {"count": 0, "bytes": 0}


def get(url, timeout=40):
    reqs["count"] += 1
    r = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        body = resp.read()
    reqs["bytes"] += len(body)
    return body


def month_total(year, month):
    doc = json.loads(get(f"{BASE}/listaOCDSAgnoMes/{year}/{month}/1/1"))
    return doc["pagination"]["total"]


def award_statuses(year, month, n=100):
    doc = json.loads(get(f"{BASE}/listaOCDSAgnoMes/{year}/{month}/1/{n}"))
    statuses, missing_award, tender_sizes, award_sizes = {}, 0, [], []
    for i, item in enumerate(doc["data"]):
        url_award = item.get("urlAward", "").replace("http://", "https://")
        if not url_award:
            missing_award += 1
            continue
        a = get(url_award)
        award_sizes.append(len(a))
        adoc = json.loads(a)
        for rel in adoc.get("releases", []):
            aw = rel.get("awards") or []
            for x in aw:
                key = (x.get("status") or "?").strip() + \
                      (" | " + x["statusDetails"].strip() if x.get("statusDetails") else "")
                statuses[key] = statuses.get(key, 0) + 1
        if i < 5 and item.get("urlTender"):
            t = get(item["urlTender"].replace("http://", "https://"))
            tender_sizes.append(len(t))
    return statuses, missing_award, tender_sizes, award_sizes


def main():
    t0 = time.time()
    print("== monthly licitaciones totals (month 06 or 01, one request each)")
    for y, m in [(2010, 1), (2014, 1), (2018, 1), (2020, 1), (2023, 1), (2025, 1)]:
        print(f"  {y}-{m:02d}: total={month_total(y, m)}")

    for y, m in [(2019, 6), (2023, 6)]:
        print(f"== award outcomes, first 100 processes of {y}-{m:02d}")
        st, miss, ts, asz = award_statuses(y, m)
        n = sum(st.values())
        print(f"  processes with no urlAward: {miss}")
        for k, v in sorted(st.items(), key=lambda kv: -kv[1]):
            print(f"  {k}: {v} ({v / max(n, 1):.1%})")
        if asz:
            print(f"  award doc bytes: avg={sum(asz)//len(asz)} n={len(asz)}")
        if ts:
            print(f"  tender doc bytes: avg={sum(ts)//len(ts)} n={len(ts)}")
        desierta = sum(v for k, v in st.items()
                       if "unsuccessful" in k or "esierta" in k)
        print(f"  desertion fraction in sample: {desierta}/{n} = {desierta / max(n, 1):.1%}")

    print(f"== cost: {reqs['count']} requests, {reqs['bytes']:,} bytes, "
          f"{time.time() - t0:.1f}s wall clock")


if __name__ == "__main__":
    main()
