#!/usr/bin/env python3
"""Bounded probe: what does one extraction request actually cost, per product?

Measures HTTP requests, bytes and wall-clock for the label-bearing products a construction
script could use, on this machine class. No bulk data is stored: each response is read, its
bytes counted, and discarded. Also tests whether a product that returns *verified daily maxima*
exists, since that would replace 12 monthly 6-minute requests with one per station-year.
"""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

UA = {"User-Agent": "scout-dataset-factory/0.1 (bounded research probe)"}
DATA = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
MDAPI = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi"


def fetch(url, timeout=120):
    started = time.time()
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
    return raw, round(time.time() - started, 3)


def main():
    out = {"measured_on": "2026-09-19", "endpoints": {"data": DATA, "metadata": MDAPI}}

    # 1. The station inventory with thresholds.
    raw, secs = fetch(f"{MDAPI}/stations.json?type=waterlevels")
    stations = json.loads(raw)["stations"]
    out["station_inventory"] = {
        "url": f"{MDAPI}/stations.json?type=waterlevels",
        "stations": len(stations),
        "bytes": len(raw),
        "seconds": secs,
        "sample_fields": sorted(stations[0].keys()),
    }
    print("stations.json?type=waterlevels:", len(stations), "stations,",
          len(raw), "bytes,", secs, "s")
    print("  fields:", sorted(stations[0].keys()))

    # 2. Products, one bounded request each.
    trials = [
        ("water_level_6min_1month", f"{DATA}?product=water_level&application=scout"
         "&begin_date=20260801&end_date=20260831&datum=STND&station=8443970"
         "&time_zone=gmt&units=english&format=json"),
        ("hourly_height_1year", f"{DATA}?product=hourly_height&application=scout"
         "&begin_date=20250101&end_date=20251231&datum=STND&station=8443970"
         "&time_zone=gmt&units=english&format=json"),
        ("daily_max_1month", f"{DATA}?product=daily_max&application=scout"
         "&begin_date=20260101&end_date=20260131&datum=STND&station=8443970"
         "&time_zone=gmt&units=english&format=json"),
        ("daily_max_1year", f"{DATA}?product=daily_max&application=scout"
         "&begin_date=20250101&end_date=20251231&datum=STND&station=8443970"
         "&time_zone=gmt&units=english&format=json"),
        ("verified_6min_1month", f"{DATA}?product=water_level&application=scout"
         "&begin_date=20250801&end_date=20250831&datum=STND&station=8443970"
         "&time_zone=gmt&units=english&format=json"),
    ]
    out["product_trials"] = {}
    for name, url in trials:
        entry = {"url": url}
        try:
            raw, secs = fetch(url)
            entry.update({"bytes": len(raw), "seconds": secs, "status": "ok"})
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                entry["error"] = payload.get("error")
                for key in ("data", "predictions"):
                    if isinstance(payload.get(key), list):
                        entry["rows"] = len(payload[key])
                        entry["row_fields"] = sorted(payload[key][0].keys())
                        break
        except urllib.error.HTTPError as exc:
            entry.update({"status": f"HTTP {exc.code}",
                          "body": exc.read().decode("utf-8", "replace")[:200]})
        except Exception as exc:  # noqa: BLE001
            entry.update({"status": "failed", "body": repr(exc)[:200]})
        out["product_trials"][name] = entry
        print(f"  {name:<26} {entry.get('status'):<10} rows={entry.get('rows')} "
              f"bytes={entry.get('bytes')} s={entry.get('seconds')} err={entry.get('error')}")

    # 3. Threshold presence for the full inventory, one request per station (bounded: first 12).
    floods = {}
    for station in stations[:12]:
        sid = station["id"]
        try:
            raw, secs = fetch(f"{MDAPI}/stations/{sid}/floodlevels.json")
            payload = json.loads(raw)
            floods[sid] = payload.get("NOSminor") or payload.get("nos_minor") or payload
        except Exception as exc:  # noqa: BLE001
            floods[sid] = {"error": repr(exc)[:120]}
    out["floodlevels_sample"] = floods
    print("floodlevels sample:", json.dumps(floods)[:400])

    path = Path(__file__).with_name("cost_probe_result.json")
    path.write_text(json.dumps(out, indent=1) + "\n")
    print("wrote", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
