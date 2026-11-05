#!/usr/bin/env python3
"""Pin the northern-Arkansas tornado-emergency false-alarm fixture (2026-11-05).

Keylon 2025 (arXiv 2510.25011) documents a nontornadic northern-Arkansas storm
on 2022-04-16 whose TOR warnings produced all 3 tornado-emergency false alarms
of 2014-2023. The 2022-04-16 UTC day file alone is NOT sufficient to identify
the storm's warnings: LZK also issued two VERIFIED early-morning warnings that
UTC day (00:09Z, 00:45Z). This probe therefore pulls the wider LZK TOR window
2022-04-13..2022-04-20, fetches each warning's product_text, and identifies the
tornado-emergency warnings by their own IBW wording. The fixture = every LZK
TOR warning in this window whose product text declares a TORNADO EMERGENCY must
read verify=false (a false alarm). Construct-only: no performance metric.
"""
import json
import os
import re
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
API = "https://mesonet.agron.iastate.edu/api/1/cow.json"

URL = (f"{API}?begints=2022-04-13T00:00Z&endts=2022-04-20T00:00Z"
       "&phenomena=TO&significance=W&wfo=LZK")


def fetch_text(url, retries=3, timeout=30):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)  # default urllib UA
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"fetch failed: {url}: {last}")


def main():
    body = fetch_text(URL, timeout=120)
    print("day-window bytes:", len(body))
    data = json.loads(body)
    feats = data.get("events", {}).get("features", [])
    rows = []
    for ft in feats:
        p = ft.get("properties", {})
        ptext_url = p.get("product_text")
        text = fetch_text(ptext_url) if ptext_url else ""
        has_em = bool(re.search(r"TORNADO\s+EMERGENCY", text, re.I))
        rows.append({
            "wfo": p.get("wfo"), "eventid": p.get("eventid"),
            "issue": p.get("issue"), "expire": p.get("expire"),
            "verify": bool(p.get("verify")),
            "product_id": p.get("product_id"),
            "tornado_emergency_in_text": has_em,
            "text_headline": text.strip().splitlines()[0] if text.strip() else None,
            "text_bytes": len(text),
        })
        print(rows[-1]["issue"], rows[-1]["eventid"], "verify=", rows[-1]["verify"],
              "EMERGENCY=" if has_em else "emerg=no")
    em = [r for r in rows if r["tornado_emergency_in_text"]]
    fixture = {
        "window": "2022-04-13..2022-04-20 wfo=LZK phenomena=TO significance=W",
        "all_lzk_tor_warnings": rows,
        "tornado_emergency_warnings": em,
        "fixture_rule": ("Every warning with tornado_emergency_in_text=true must "
                         "read verify=false (Keylon 2025: all 3 tornado-emergency "
                         "false alarms 2014-2023 came from this storm)."),
        "fixture_holds": all(not r["verify"] for r in em) if em else False,
        "n_emergency": len(em),
    }
    with open(os.path.join(OUT, "arkansas_fixture_2026_11_05.json"), "w") as f:
        json.dump(fixture, f, indent=1)
    print(json.dumps({k: fixture[k] for k in ("n_emergency", "fixture_holds")}, indent=1))


if __name__ == "__main__":
    main()
