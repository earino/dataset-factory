#!/usr/bin/env python3
"""Probe: INEGI DENUE bulk availability - current edition size + historical editions.

Measures, anonymously:
  1. The current DENUE edition's bulk download: one zip per national activity
     sector (denue_00_<sector>_csv.zip under /contenidos/masiva/denue/) -
     HTTP status, real-zip magic bytes, and total size via Content-Range.
  2. Historical editions: INEGI's server answers HTTP 200 with an HTML error
     page to unknown paths (soft 404), so status alone proves nothing - the
     probe checks the first bytes for the PK zip magic instead. Patterns
     tried for prior versions (2015/2019/2021/2024 path variants).
  3. The Descarga Masiva app's JSON API (obtenerlistado) - records what it
     accepts, as the SPA's channel.

Writes nothing; prints a compact report. Run from the candidate directory:
    python3 probe_denue.py
"""

import json
import time
import urllib.request

BASE = "https://www.inegi.org.mx/contenidos/masiva/denue/"
SECTORS = ["23", "93", "11", "43", "46111", "46112-46311", "46321-46531",
           "46591-46911", "55", "51", "21", "31-33", "22", "81_1", "81_2",
           "72_1", "72_2", "56", "71", "62", "61", "52", "53", "54", "48-49"]
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

reqs = {"count": 0}


def fetch(url, rng=None, timeout=45, data=None, headers=None):
    reqs["count"] += 1
    h = {**UA, **(headers or {})}
    if rng:
        h["Range"] = rng
    req = urllib.request.Request(url, headers=h, data=data)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except Exception as e:  # noqa: BLE001 - record every failure mode
        return getattr(e, "code", 0), str(e).encode(), {}


def main():
    t0 = time.time()
    print("== current edition: per-sector national zips (ranged 0-15)")
    total, real, failed = 0, 0, []
    for s in SECTORS:
        url = f"{BASE}denue_00_{s}_csv.zip"
        status, body, hdr = fetch(url, rng="bytes=0-15")
        cr = hdr.get("Content-Range") or ""
        size = int(cr.split("/")[-1]) if "/" in cr else -1
        is_zip = body[:2] == b"PK"
        if is_zip and size > 0:
            total += size
            real += 1
            print(f"  sector {s}: OK {size:,} bytes")
        else:
            failed.append(s)
    print(f"  real zips: {real}/{len(SECTORS)}; failed patterns: {failed}")
    print(f"  measured current-edition bulk total: {total:,} bytes "
          f"({total / 1e6:.0f} MB) across {real} sector zips")

    print("== historical editions: do prior versions answer?")
    variants = [
        f"{BASE}2019/denue_00_23_csv.zip",
        f"{BASE}denue_2019_00_23_csv.zip",
        f"{BASE}2015/denue_00_23_csv.zip",
        f"{BASE}denue_05_2024_00_23_csv.zip",
        f"{BASE}zzz_nonexistent.zip",
    ]
    for url in variants:
        status, body, hdr = fetch(url, rng="bytes=0-15")
        kind = "REAL ZIP" if body[:2] == b"PK" else "HTML error page"
        print(f"  {status} {kind}  <- {url.split('/masiva/denue/')[-1]}")

    print("== Descarga Masiva app JSON API (channel the SPA uses)")
    api = "https://www.inegi.org.mx/app/api/descarga/descarga/descargamasiva/lista/obtenerlistado"
    st, body, _ = fetch(api, data=json.dumps(
        {"tinfo": "6", "ag": "", "prog": "", "cc": "", "subtema": "", "anio": "",
         "formato": "", "datosAbiertos": "", "textoBuscar": "", "ingles": "",
         "tipoInfo": ""}).encode(),
        headers={"Content-Type": "application/json"})
    print(f"  POST obtenerlistado: {st} {body[:140]!r}")

    print(f"== cost: {reqs['count']} requests, {time.time() - t0:.1f}s wall clock")


if __name__ == "__main__":
    main()
