#!/usr/bin/env python3
"""Follow-up probe 2026-11-05: 2016 GLD #38 duplicate features with
disagreeing `verify` refused the build (nws-tornado-build-001 exit 1).

Pulls the cow TO.W rows for WFO GLD, year 2016, isolates every feature
whose (year, wfo, eventid) == (2016, GLD, 38), prints the fields that
differ between the duplicates, and dumps the tornado storm reports in
the warning window so the semantically right `verify` can be judged
from source evidence. Bounded: WFO+year response only; the national
year pull is never kept on this host.
"""
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
API = "https://mesonet.agron.iastate.edu/api/1/cow.json"
URL = (f"{API}?begints=2016-01-01T00:00Z&endts=2016-12-31T23:59Z"
       "&phenomena=TO&significance=W&wfo=GLD")
RAW = os.path.join("/opt/data/cache/scratch/nws-followup-2026-11-05",
                   "cow-2016-GLD.json")


def fetch(url, dest, retries=3):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=180) as r, \
                    open(dest + ".part", "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            if os.path.getsize(dest + ".part") == 0:
                raise RuntimeError("zero-length body")
            os.replace(dest + ".part", dest)
            return os.path.getsize(dest)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"fetch failed after {retries}: {url}: {last}")


def main():
    size = fetch(URL, RAW)
    print(f"cow 2016 GLD response: {size} bytes -> {RAW}")
    with open(RAW) as f:
        data = json.load(f)
    feats = data.get("events", {}).get("features", [])
    print(f"GLD 2016 TO.W features: {len(feats)}")
    hits = [ft["properties"] for ft in feats
            if ft.get("properties", {}).get("eventid") == 38]
    print(f"features with eventid 38: {len(hits)}")
    for i, p in enumerate(hits):
        print(f"--- duplicate #{i} ---")
        print(json.dumps(p, indent=1, sort_keys=True, default=str))
    if len(hits) >= 2:
        keys = sorted(set(hits[0]) | set(hits[1]))
        diff = {k: [hits[0].get(k, "<absent>"), hits[1].get(k, "<absent>")]
                for k in keys if hits[0].get(k, "<absent>") != hits[1].get(k, "<absent>")}
        print("--- differing fields (dup #0 vs dup #1) ---")
        print(json.dumps(diff, indent=1, sort_keys=True, default=str))
    else:
        print("NOTE: fewer than 2 features returned - wfo filter may have "
              "changed the eventid space; verify against national pull.")
    srs = data.get("stormreports", {})
    if isinstance(srs, dict):
        srs = srs.get("features", [])
    tor = [ft.get("properties", {}) for ft in (srs or [])
           if str(ft.get("properties", {}).get("type", "")).upper().startswith("T")]
    print(f"tornado storm reports in GLD 2016 window: {len(tor)}")
    with open(os.path.join(OUT, "followup_2016_GLD_38.json"), "w") as f:
        json.dump({"url": URL, "raw_bytes": size, "duplicates": hits,
                   "tornado_lsr_count": len(tor)}, f, indent=1, default=str)
    print("saved: probe/out/followup_2016_GLD_38.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
