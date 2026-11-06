#!/usr/bin/env python3
"""Probe: WRA fhyv2 /Disaster history API from a PLAIN client (no browser session).

The 2026-10-22 park recorded "no anonymous historical bulk source" based on /Api/v2/*
returning 401 to plain clients. This probe tests the OTHER API family the SPA uses:
POST /Disaster/api/ReservoirHistoryApi/GetComparision (form-encoded, found in
/disaster/Reservoir/Comparison -> /Disaster/bundles/Comparision.js on 2026-11-06).

Bounded: 6 requests total, all read-only. Run: python3 probe_fhy_history_2026_11_06.py
"""
import json
import time
import urllib.request
import urllib.parse

BASE = "https://fhy.wra.gov.tw/Disaster/api/ReservoirHistoryApi/GetComparision"
STATIONS = "10201,10205,10401,10405,10501,10601,20101,20201,20202,20501,20502,20503,20509,30301,30401,30501,30502,30503,30802,30901,31201"


def post(stno, sd, ed, note=""):
    body = urllib.parse.urlencode({"ST_NO": stno, "StartDate": sd, "EndDate": ed}).encode()
    req = urllib.request.Request(BASE, data=body, method="POST", headers={
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "scout-discovery-probe/1.0 (dataset-factory candidate tw-reservoir-drought-storage)",
    })
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8", "replace")
            dt = time.time() - t0
            rec = {"note": note, "status": r.status, "bytes": len(raw), "sec": round(dt, 2)}
            try:
                j = json.loads(raw)
                if isinstance(j, list):
                    rec["n"] = len(j)
                    if j:
                        rec["fields_nonnull_first"] = sorted(
                            k for k, v in j[0].items() if v is not None)
                        rec["dates"] = [x.get("DATE") for x in j][:5]
                        rec["stations"] = sorted({x.get("ST_NO") for x in j})
                else:
                    rec["head"] = raw[:200]
            except Exception:
                rec["head"] = raw[:200]
            return rec
    except Exception as e:
        return {"note": note, "error": repr(e)}


def main():
    out = []
    # 1. plain client, no cookies/referer, single station, single day
    out.append(post("10201", "2021/03/02", "2021/03/02", "plain single-day single-station"))
    # 2. same, 2026 current month day (recent)
    out.append(post("10201", "2026/11/04", "2026/11/04", "plain recent-day"))
    # 3. all 21 stations in one request, single day
    out.append(post(STATIONS, "2021/03/02", "2021/03/02", "all-21 one day"))
    # 4. all 21 stations, 3-day range (boundary semantics under many stations)
    out.append(post(STATIONS, "2021/03/01", "2021/03/03", "all-21 3-day range"))
    # 5. latency burst: 2 repeats to observe consistency
    out.append(post("10201", "2021/06/15", "2021/06/15", "repeat latency a"))
    out.append(post("10201", "2021/09/15", "2021/09/15", "repeat latency b"))
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
