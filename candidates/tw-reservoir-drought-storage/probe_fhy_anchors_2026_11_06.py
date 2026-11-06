#!/usr/bin/env python3
"""Anchor probe: label presence in known drought episodes + panel start + same-day availability.

Bounded: 8 single-day all-station requests, plain client, read-only.
Days chosen against Taiwan's documented drought episodes (northern 2015 spring,
island-wide 2021 spring, southern 2024 spring) plus pre-2010 panel-start probes
and today's boundary for the same-day publication datapoint.
Run: python3 probe_fhy_anchors_2026_11_06.py
"""
import datetime
import json
import time
import urllib.request
import urllib.parse

BASE = "https://fhy.wra.gov.tw/Disaster/api/ReservoirHistoryApi/GetComparision"
STATIONS = "10201,10205,10401,10405,10501,10601,20101,20201,20202,20501,20502,20503,20509,30301,30401,30501,30502,30503,30802,30901,31201"

# name -> why
DAYS = {
    "2015/03/15": "northern 2015 drought (Shihman lows)",
    "2021/04/15": "2021 island-wide drought",
    "2024/04/15": "2024 southern drought (Zengwen/ Wushantou lows)",
    "2025/06/15": "recent non-drought mid-year",
    "2003/06/01": "panel-start probe A",
    "2005/01/01": "panel-start probe B",
    "2008/01/01": "panel-start probe C",
}
TODAY_TPE = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).strftime("%Y/%m/%d")
DAYS[TODAY_TPE] = "today (Taipei) same-day availability datapoint"


def post(stno, sd, ed):
    body = urllib.parse.urlencode({"ST_NO": stno, "StartDate": sd, "EndDate": ed}).encode()
    req = urllib.request.Request(BASE, data=body, method="POST", headers={
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "scout-discovery-probe/1.0 (dataset-factory candidate tw-reservoir-drought-storage)",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, json.loads(r.read().decode("utf-8", "replace"))


def main():
    out = []
    for day, why in sorted(DAYS.items()):
        try:
            status, recs = post(STATIONS, day, day)
            rec = {"day": day, "why": why, "status": status, "n": len(recs)}
            rates = {x["ST_NO"]: x.get("CapacityRate") for x in recs}
            rec["nonnull_rate"] = sum(1 for v in rates.values() if v is not None)
            below30 = sorted(k for k, v in rates.items() if v is not None and v < 0.30)
            below25 = sorted(k for k, v in rates.items() if v is not None and v < 0.25)
            rec["below_0.30"] = below30
            rec["below_0.25"] = below25
            rec["min_rate"] = min((v for v in rates.values() if v is not None), default=None)
            rec["rates"] = rates
            out.append(rec)
        except Exception as e:
            out.append({"day": day, "why": why, "error": repr(e)})
        time.sleep(1.0)
    print(json.dumps({"today_taipei": TODAY_TPE, "probes": out}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
