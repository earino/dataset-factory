#!/usr/bin/env python3
"""SoQL aggregate probes against the raw telemetry table (vfth-yucv) joined to
harvested cotas - the base-rate measurement pattern from 2026-10-23 (notes s6).

Run with a station code and a cota: prints hourly obs >= cota and distinct days
over cota per window. Extend the WINDOWS list for the final split measurement.
WARNING (recorded in notes s6): join stations by codigoestacion with river/
municipio confirmation - name-only joins produce false pairs (ANGOSTURA case).
Run the zero/always-positive sanity check per station (MITU anomaly).
"""
import json
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://www.datos.gov.co/resource/vfth-yucv.json"
WINDOWS = [
    ("train 2015-2019",
     "fechaobservacion >= '2015-01-01' AND fechaobservacion < '2020-01-01'"),
    ("eval 2020-2023",
     "fechaobservacion >= '2020-01-01' AND fechaobservacion < '2024-01-01'"),
    ("holdout 2024-2026", "fechaobservacion >= '2024-01-01'"),
]


def soql(params):
    qs = urllib.parse.urlencode(params, safe=",'()*=")
    req = urllib.request.Request(f"{BASE}?{qs}",
                                 headers={"User-Agent": "research-probe/1.0"})
    return json.loads(urllib.request.urlopen(req, timeout=90).read())


code, cota = sys.argv[1], sys.argv[2]
for label, where in WINDOWS:
    w = f"codigoestacion='{code}' AND {where}"
    over_h = int(soql({"$select": "count(*) AS n",
                       "$where": f"{w} AND valorobservado >= {cota}"})[0]["n"])
    days_pos = int(soql(
        {"$select": "count(DISTINCT date_trunc_ymd(fechaobservacion)) AS d",
         "$where": f"{w} AND valorobservado >= {cota}"})[0]["d"])
    days_all = int(soql(
        {"$select": "count(DISTINCT date_trunc_ymd(fechaobservacion)) AS d",
         "$where": w})[0]["d"])
    print(f"{code} cota={cota} {label}: hourly-over={over_h} "
          f"days-over={days_pos}/{days_all}")
    time.sleep(1.2)
