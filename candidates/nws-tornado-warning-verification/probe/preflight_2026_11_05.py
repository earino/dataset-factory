#!/usr/bin/env python3
"""Construct-only preflight for nws-tornado-warning-verification (2026-11-05).

No performance metric is computed anywhere in this script. It only:
  1. pulls the two record-pinned anchor years (2013, 2023) from the IEM cow
     API and asserts the recorded anchors reproduce EXACTLY
     (2013: 1832 events / 441 verified; 2023: 2531 / 656);
  2. pulls the 2022-04-16 national TOR day file and emits the per-warning
     list needed to pin the northern-Arkansas false-alarm fixture;
  3. (separate mode) measures the per-warning product_text fetch on a
     deterministic 500-warning sample drawn from the 2023 file, to record the
     v1 include/exclude decision with evidence.

Outputs compact JSON to probe/out/ and large pulls to scratch only.
Anonymous; urllib default User-Agent (the unhcr WAF lesson: honest UA).
"""
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SCRATCH = "/opt/data/cache/scratch/nws-preflight-2026-11-05"
API = "https://mesonet.agron.iastate.edu/api/1/cow.json"
os.makedirs(OUT, exist_ok=True)
os.makedirs(SCRATCH, exist_ok=True)

ANCHORS = {
    2013: {"events": 1832, "verified": 441},
    2023: {"events": 2531, "verified": 656},
}


def fetch(url, dest, retries=3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)  # default urllib UA
            with urllib.request.urlopen(req, timeout=180) as r, open(dest + ".part", "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            size = os.path.getsize(dest + ".part")
            if size == 0:
                raise RuntimeError("zero-length body")
            os.replace(dest + ".part", dest)
            return size
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"fetch failed after {retries}: {url}: {last}")


def year_url(year):
    return (f"{API}?begints={year}-01-01T00:00Z&endts={year}-12-31T23:59Z"
            "&phenomena=TO&significance=W")


def summarize(path):
    """Compact per-event rows + counts. One file in memory at a time."""
    with open(path) as f:
        data = json.load(f)
    # cow returns {"events": {"features": [...]}, "stormreports": {...}, "stats": {...}}
    feats = data.get("events", {}).get("features", [])
    events = []
    n_ver = 0
    wfos = set()
    ver_days = set()
    all_days = set()
    for ft in feats:
        p = ft.get("properties", {})
        v = bool(p.get("verify"))
        issue = p.get("issue", "")
        day = issue[:10]
        all_days.add(day)
        if v:
            n_ver += 1
            ver_days.add(day)
        wfos.add(p.get("wfo"))
        events.append({
            "year": p.get("year"), "wfo": p.get("wfo"), "eventid": p.get("eventid"),
            "issue": issue, "expire": p.get("expire"), "verify": v,
            "product_id": p.get("product_id"),
        })
    stats = data.get("stats", {})
    def _num(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None
    return {
        "n_features": len(feats),
        "verified": n_ver,
        "wfos": len(wfos),
        "active_days": len(all_days),
        "verified_days": len(ver_days),
        "stats_total": stats.get("events_total"),
        "stats_verified": stats.get("events_verified"),
        "stats_far1": stats.get("FAR[1]"),
        "events": events,
    }


def main_anchors():
    results = {}
    for year, anchor in ANCHORS.items():
        dest = os.path.join(SCRATCH, f"cow_{year}.json")
        t0 = time.time()
        if not os.path.exists(dest):
            size = fetch(year_url(year), dest)
        else:
            size = os.path.getsize(dest)
        dt = time.time() - t0
        s = summarize(dest)
        ok = (s["n_features"] == anchor["events"]
              and s["verified"] == anchor["verified"])
        results[str(year)] = {
            "bytes": size, "seconds": round(dt, 1),
            "n_features": s["n_features"], "verified": s["verified"],
            "wfos": s["wfos"], "active_days": s["active_days"],
            "verified_days": s["verified_days"],
            "stats": {"total": s["stats_total"], "verified": s["stats_verified"],
                      "far1": s["stats_far1"]},
            "anchor": anchor, "anchor_exact": ok,
        }
        print(json.dumps({str(year): {k: v for k, v in results[str(year)].items()}}, indent=1))
        # free memory before the next year
        del s
    with open(os.path.join(OUT, "preflight_anchors_2026_11_05.json"), "w") as f:
        json.dump(results, f, indent=1)
    bad = [y for y, r in results.items() if not r["anchor_exact"]]
    print("ANCHORS:", "EXACT" if not bad else f"MISMATCH {bad}")


def main_day():
    dest = os.path.join(SCRATCH, "cow_2022-04-16.json")
    url = (f"{API}?begints=2022-04-16T00:00Z&endts=2022-04-17T00:00Z"
           "&phenomena=TO&significance=W")
    size = fetch(url, dest)
    s = summarize(dest)
    print(json.dumps({"day_bytes": size, "n_tor_warnings": s["n_features"],
                      "verified": s["verified"],
                      "per_wfo": sorted({e["wfo"] for e in s["events"]})}, indent=1))
    with open(os.path.join(OUT, "preflight_day_2022_04_16.json"), "w") as f:
        json.dump({"bytes": size, "summary": {k: v for k, v in s.items() if k != "events"},
                   "events": s["events"]}, f, indent=1)
    print("DAY EVENTS WRITTEN:", len(s["events"]))


def main_sample(n=500):
    """Deterministic spread sample from the 2023 file; fetch product_text."""
    dest = os.path.join(SCRATCH, "cow_2023.json")
    if not os.path.exists(dest):
        fetch(year_url(2023), dest)
    with open(dest) as f:
        data = json.load(f)
    feats = data.get("events", {}).get("features", [])
    rows = []
    for ft in feats:
        p = ft.get("properties", {})
        rows.append((p.get("issue") or "", p.get("wfo") or "", p.get("eventid"),
                     p.get("product_id"), p.get("product_text")))
    rows.sort(key=lambda r: (r[0], r[1], str(r[2])))
    if len(rows) > n:
        step = len(rows) / n
        idxs = sorted({int(i * step) for i in range(n)})
    else:
        idxs = list(range(len(rows)))
    sample = [rows[i] for i in idxs]

    def get(row):
        _, _, _, _, ptext = row
        if not ptext:
            return {"ok": False, "reason": "no_product_text_field", "bytes": 0, "ms": 0}
        t0 = time.time()
        try:
            req = urllib.request.Request(ptext)  # default UA
            with urllib.request.urlopen(req, timeout=20) as r:
                body = r.read()
            return {"ok": True, "bytes": len(body), "ms": round((time.time() - t0) * 1000)}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "reason": f"{type(e).__name__}: {e}"[:200],
                    "bytes": 0, "ms": round((time.time() - t0) * 1000)}

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=5) as ex:
        out = list(ex.map(get, sample))
    dt = time.time() - t0
    ok = [o for o in out if o["ok"]]
    sizes = sorted(o["bytes"] for o in ok)
    agg = {
        "sample_n": len(sample), "ok": len(ok), "failed": len(out) - len(ok),
        "fail_reasons": sorted({str(o.get("reason")) for o in out if not o["ok"]}),
        "bytes_min": sizes[0] if sizes else None,
        "bytes_p50": sizes[len(sizes) // 2] if sizes else None,
        "bytes_max": sizes[-1] if sizes else None,
        "wall_seconds": round(dt, 1),
        "per_request_ms_p50": sorted(o["ms"] for o in ok)[len(ok) // 2] if ok else None,
        "implied_40k_serial_min": (round(sorted(o["ms"] for o in ok)[len(ok) // 2] * 40000 / 60000, 1)
                                   if ok else None),
        "implied_40k_at_5workers_min": (round(sorted(o["ms"] for o in ok)[len(ok) // 2] * 40000 / 5 / 60000, 1)
                                        if ok else None),
    }
    print(json.dumps(agg, indent=1))
    with open(os.path.join(OUT, "preflight_product_text_sample_2026_11_05.json"), "w") as f:
        json.dump(agg, f, indent=1)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "anchors"
    if mode == "anchors":
        main_anchors()
    elif mode == "day":
        main_day()
    elif mode == "sample":
        main_sample(int(sys.argv[2]) if len(sys.argv) > 2 else 500)
    else:
        raise SystemExit(f"unknown mode {mode}")
