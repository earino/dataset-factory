#!/usr/bin/env python3
"""Probe: Camara dos Deputados bulk proposition CSVs - bounded ranged samples.

Measures, anonymously:
  1. Year-file sizes via ranged GET (bytes=0-0) for a spread of years.
  2. From 4 x 1 MB ranged chunks of proposicoes-2019.csv and
     proposicoes-2005.csv: row parse, then distributions of
     - dataApresentacao year (tests what the per-year file actually holds:
        propositions *presented* that year vs propositions whose current
        'ano' attribute is that year - bills un-archived at a new
        legislature are re-numbered with the new year);
     - ultimoStatus_descricaoSituacao (last tramitacao status vocabulary);
     - urnFinal non-empty (bill became law -> resulting law URN);
     - a proxy 'advanced' fraction (status mentions Senado / Lei /
        Promulgação / Transformad - i.e. the bill passed the Chamber).
Writes nothing; prints a compact report. Run from the candidate directory:
    python3 probe_samples.py
"""

import csv
import io
import time
import urllib.request

BASE = "https://dadosabertos.camara.leg.br/arquivos/proposicoes/csv/proposicoes-%d.csv"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

reqs = {"count": 0, "bytes": 0}


def ranged(url, start, length, timeout=60):
    reqs["count"] += 1
    req = urllib.request.Request(url, headers={**UA, "Range": f"bytes={start}-{start + length - 1}"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.headers


def file_size(url):
    body, hdr = ranged(url, 0, 1)
    cr = hdr.get("Content-Range") or ""
    return int(cr.split("/")[-1]) if "/" in cr else len(body)


def rows_from_chunk(chunk):
    text = chunk.decode("utf-8-sig", errors="replace")
    lines = text.split("\n")
    # drop first (may be partial) and last (likely partial) line; caller adds header
    body = "\n".join(lines[1:-1])
    if not body.strip():
        return []
    rdr = csv.reader(io.StringIO(body), delimiter=";", quotechar='"')
    return [r for r in rdr if len(r) > 28]


def analyse(year, chunks=4, chunk_len=1_048_576):
    url = BASE % year
    size = file_size(url)
    print(f"== proposicoes-{year}.csv: total {size:,} bytes")
    samples = []
    for i in range(chunks):
        off = (size // chunks) * i + (16 if i == 0 else 0)
        body, _ = ranged(url, off, chunk_len)
        samples.extend(rows_from_chunk(body))
    print(f"   parsed rows in sample: {len(samples)}")
    by_year, statuses, urn_final, advanced = {}, {}, 0, 0
    for r in samples:
        dp = r[10] or ""
        yr = dp[:4] or "?"
        by_year[yr] = by_year.get(yr, 0) + 1
        sit = (r[25] or "?").strip()
        statuses[sit] = statuses.get(sit, 0) + 1
        if (r[16] or "").strip():
            urn_final += 1
        if any(w in sit for w in ("Senado", "Lei", "Promulg", "Transformad")):
            advanced += 1
    print(f"   dataApresentacao year distribution (top 8):")
    for k, v in sorted(by_year.items(), key=lambda kv: -kv[1])[:8]:
        print(f"     {k}: {v} ({v / len(samples):.0%})")
    print(f"   ultimoStatus_descricaoSituacao (top 12):")
    for k, v in sorted(statuses.items(), key=lambda kv: -kv[1])[:12]:
        print(f"     {k}: {v} ({v / len(samples):.1%})")
    n = len(samples)
    print(f"   urnFinal non-empty (became law): {urn_final}/{n} = {urn_final / n:.1%}")
    print(f"   advanced-out-of-Chamber proxy: {advanced}/{n} = {advanced / n:.1%}")


def main():
    t0 = time.time()
    for y in [1991, 2000, 2005, 2019, 2025]:
        print(f"   size probe {y}: {file_size(BASE % y):,} bytes")
    for y in [2005, 2019]:
        analyse(y)
    print(f"== cost: {reqs['count']} requests, {reqs['bytes']:,} bytes, "
          f"{time.time() - t0:.1f}s wall clock")


if __name__ == "__main__":
    main()
