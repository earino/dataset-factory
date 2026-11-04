#!/usr/bin/env python3
"""CPCB reopen probe, 2026-11-04: XKDR terms + meta + PM2.5 per-year coverage.

Bounded, read-only, anonymous. Decides split capacity (stations with PM2.5
per year) for the reopened cpcb-aqi-exceedance candidate.
"""
import json
import re
import sys
import urllib.request

BASE = "https://airquality.xkdr.org"


def get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": "scout-factory-probe/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def main():
    out = {}

    # 1. front page: demo key + any licence/terms statement
    st, body = get(BASE + "/")
    html = body.decode("utf-8", "replace")
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    out["front_page_status"] = st
    m = re.search(r"aqi_demo_[A-Za-z0-9_]+", text)
    out["demo_key_published_on_front_page"] = bool(m)
    key = m.group(0) if m else None
    for kw in ["CC BY", "CC-BY", "license", "licence", "License", "terms", "open data"]:
        i = text.find(kw)
        if i >= 0:
            out.setdefault("front_page_kw", {})[kw] = text[max(0, i - 120): i + 260]

    hdr = {"Authorization": "Bearer " + key} if key else {}

    def api(path, params):
        url = BASE + path + ("&" if "?" in path else "?") + params
        req = urllib.request.Request(url, headers=hdr)
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.status, r.read()
        except Exception as e:
            return "ERR", repr(e).encode()

    # 2. meta
    st, body = api("/v1/meta", "")
    out["meta_status"] = st
    try:
        meta = json.loads(body)
        out["meta_keys"] = sorted(meta.keys()) if isinstance(meta, dict) else str(type(meta))
        if isinstance(meta, dict):
            for k in ("num_measurements", "total_stations", "stations", "parameters",
                      "start", "end", "first_date", "last_date", "total_measurements"):
                if k in meta:
                    v = meta[k]
                    out["meta_" + k] = v if not isinstance(v, (list, dict)) else len(v)
            # common summary shapes
            if isinstance(meta.get("summary"), dict):
                out["meta_summary"] = {k: (v if not isinstance(v, (list, dict)) else len(v))
                                        for k, v in meta["summary"].items()}
    except Exception as e:
        out["meta_parse_error"] = repr(e)
        out["meta_body_head"] = body[:300].decode("utf-8", "replace")

    # 3. PM2.5 monthly coverage per year (sample years; 10k rows/query demo cap)
    per_year = {}
    for year in (2016, 2019, 2020, 2022, 2024, 2025):
        st, body = api(
            "/v1/measurements",
            f"parameter=PM2.5&agg=monthly&start={year}-01-01&end={year}-12-31&format=json",
        )
        if st != 200:
            per_year[str(year)] = {"status": st, "err": body[:200].decode("utf-8", "replace")}
            continue
        try:
            rows = json.loads(body)
            if isinstance(rows, dict):
                rows = rows.get("data") or rows.get("rows") or []
            stations = {}
            for r in rows:
                sid = r.get("station_id") or r.get("site_id") or r.get("id")
                stations[sid] = stations.get(sid, 0) + 1
            # months actually covered
            months = sorted({(r.get("period_start") or "")[:7] for r in rows})
            per_year[str(year)] = {
                "rows": len(rows),
                "stations_with_pm25": len(stations),
                "months_present": len(months),
                "first_month": months[0] if months else None,
                "last_month": months[-1] if months else None,
                "sample_row_keys": sorted(rows[0].keys()) if rows else [],
            }
        except Exception as e:
            per_year[str(year)] = {"parse_error": repr(e), "head": body[:200].decode("utf-8", "replace")}
    out["pm25_monthly_by_year"] = per_year

    json.dump(out, open("cpcb_reopen_probe_out.json", "w"), indent=1)
    print(json.dumps(out, indent=1)[:4000])


if __name__ == "__main__":
    sys.exit(main())
