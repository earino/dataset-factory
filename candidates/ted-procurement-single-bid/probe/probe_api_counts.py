#!/usr/bin/env python3
"""Reproduce the TED Search API count measurements and CN->CAN link fixtures
recorded in candidates/ted-procurement-single-bid/record.json (2026-10-27).

Anonymous POST https://api.ted.europa.eu/v3/notices/search. A "fields" list is
REQUIRED (the API returns 400 without it). Politeness: ~1 request/second with
identifying User-Agent and From headers, per the published fair-use guidance.
Run from anywhere: python3 probe_api_counts.py
"""
import json
import time
import urllib.error
import urllib.request

UA = {
    "User-Agent": "scout-dataset-factory/1.0 (dataset discovery)",
    "From": "scout@nousresearch.com",
    "Accept": "application/json",
}


def search(query, limit=3, fields=("ND", "PD", "CY", "TY", "AA", "AC")):
    body = {"query": query, "limit": limit, "fields": list(fields)}
    req = urllib.request.Request(
        "https://api.ted.europa.eu/v3/notices/search",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", **UA},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()), time.time() - t0, None
    except urllib.error.HTTPError as e:
        return None, time.time() - t0, f"{e.code} {e.read()[:200].decode('utf-8', 'replace')}"


def main():
    # 1) award-notice population counts across form families and eras
    count_queries = [
        'FT=3 AND PD>=20190601 AND PD<=20190630',      # legacy form-3 CANs
        'FT="CAN" AND PD>=20150601 AND PD<=20150630',  # eForms result notices
        'FT="CAN" AND PD>=20190601 AND PD<=20190630',
        'FT="CAN" AND PD>=20220601 AND PD<=20220630',
        'FT="CAN" AND PD>=20230101 AND PD<=20230131',
        'FT="CAN" AND PD>=20230110 AND PD<=20230110',
        'FT="CAN" AND PD>=20230101 AND PD<=20231231',
        'FT="CAN" AND PD>=20240601 AND PD<=20240630',
        'FT="CAN" AND PD>=20250601 AND PD<=20250630',
        'FT="CAN" AND PD>=20260901 AND PD<=20260930',
    ]
    for q in count_queries:
        d, el, err = search(q, limit=1)
        if d is None:
            print(f"COUNT {q} -> ERR {err}")
        else:
            print(f"COUNT {q} -> totalNoticeCount={d.get('totalNoticeCount')}"
                  f" iterationNextToken={'set' if d.get('iterationNextToken') else 'null'}"
                  f" ({el:.2f}s)")
        time.sleep(1.2)

    # 2) link fixtures: FUTURE_CAN_ID from CN CSV prefix rows -> CAN via API
    print("\nLINK FIXTURES (FUTURE_CAN_ID from the CN 2023 CSV prefix, 2026-10-27)")
    for nd, expect in [
        ("371295-2023", "CN 10-2023: PRT, Instituto Superior Tecnico, CPV 90910000"),
        ("181795-2023", "CN 2-2023: ESP, Consejeria de Presidencia"),
        ("10-2023", "the CN itself (control)"),
    ]:
        d, el, err = search(f"ND={nd}", limit=1)
        if d is None:
            print(f"ND={nd} -> ERR {err}")
        else:
            n = (d.get("notices") or [{}])[0]
            print(f"ND={nd}: total={d.get('totalNoticeCount')} PD={n.get('PD')}"
                  f" CY={n.get('CY')} AA={n.get('AA')} AC={n.get('AC')}"
                  f" TY={n.get('TY')}  # expected: {expect}")
        time.sleep(1.2)


if __name__ == "__main__":
    main()
