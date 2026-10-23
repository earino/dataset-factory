#!/usr/bin/env python3
"""Right-censoring + code-vocabulary probe v2 for camara-bill-advancement.

Corrects probe_censoring.py's naive line splitting (quoted multi-line
ements/despachos make mid-file fragments parse as garbage) with a
quote-parity-aware boundary trim, and corrects the discovery probe's
positional idSituacao indexing (r[25] is ultimoStatus_idTipoTramitacao,
not idSituacao) by keying columns on the file's own header names.

Measures, per sampled year file:
  - (ultimoStatus_idSituacao, ultimoStatus_descricaoSituacao) mix, by name;
  - share of rows with empty idSituacao (genuinely no current status?);
  - presentation-year mix (right-censoring question for 2019-2022 cohorts).

Downloads: the whole 1991 file (4.4 MB) as ground truth for a full parse,
plus 3 x ~1.5 MB spread chunks for the other years (~18 MB total).
"""
import csv
import io
import json
import time
import urllib.request

BASE = "https://dadosabertos.camara.leg.br/arquivos/proposicoes/csv/proposicoes-{ano}.csv"
UA = {"User-Agent": "dataset-factory/camara-censoring-probe2"}
WHOLE = [1991]
CHUNK_YEARS = [1995, 2000, 2005, 2010, 2015, 2019, 2021, 2022]
CHUNKS = 3
CHUNK_BYTES = 1_500_000


def fetch_range(url, start, length, attempts=3):
    last = None
    for attempt in range(attempts):
        if attempt:
            time.sleep(2 ** attempt)
        req = urllib.request.Request(url, headers={
            "Range": f"bytes={start}-{start + length - 1}", **UA})
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return resp.read()
        except Exception as error:
            last = error
    raise SystemExit(f"range fetch failed: {url} ({last})")


def file_size(url):
    req = urllib.request.Request(url, method="HEAD", headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return int(resp.headers["Content-Length"])


def trim_to_record_boundaries(text: str) -> str:
    """Drop the leading partial record (first newline outside quotes) and the
    trailing partial record (last newline outside quotes)."""
    in_quote = False
    first = None
    last = None
    for index, char in enumerate(text):
        if char == '"':
            in_quote = not in_quote
        elif char == "\n" and not in_quote:
            if first is None:
                first = index
            last = index
    if first is None:
        return ""
    return text[first + 1:last]


def parse_rows(text: str, header):
    body = trim_to_record_boundaries(text)
    reader = csv.reader(io.StringIO(body), delimiter=";", quotechar='"')
    out = []
    for row in reader:
        if len(row) == len(header):
            out.append(dict(zip(header, row)))
    return out


def header_for(url):
    raw = fetch_range(url, 0, 65536)
    text = raw.decode("utf-8-sig", errors="replace")
    in_quote = False
    cut = None
    for index, char in enumerate(text):
        if char == '"':
            in_quote = not in_quote
        elif char == "\n" and not in_quote:
            cut = index
            break
    return csv.reader(io.StringIO(text[:cut]), delimiter=";", quotechar='"').__next__()


def analyse(url, size, header, whole=False):
    rows = []
    if whole:
        raw = fetch_range(url, 0, size)
        rows = parse_rows(raw.decode("utf-8-sig", errors="replace"), header)
    else:
        for index in range(CHUNKS):
            start = (size // CHUNKS) * index if index else 0
            if index:
                start -= 4096
            raw = fetch_range(url, start, CHUNK_BYTES)
            rows.extend(parse_rows(raw.decode("utf-8-sig", errors="replace"), header))
    status, years, sit_no_desc, desc_no_sit = {}, {}, 0, 0
    for row in rows:
        code = (row.get("ultimoStatus_idSituacao") or "").strip()
        desc = (row.get("ultimoStatus_descricaoSituacao") or "").strip()
        years[(row.get("dataApresentacao") or "")[:4]] = years.get((row.get("dataApresentacao") or "")[:4], 0) + 1
        if not code and not desc:
            key = "<EMPTY_CODE>|<EMPTY_DESC>"
        else:
            key = f"{code or '<EMPTY_CODE>'}|{desc or '<EMPTY_DESC>'}"[:70]
        status[key] = status.get(key, 0) + 1
    empty = sum(n for k, n in status.items() if k.startswith("<EMPTY_CODE>"))
    return {
        "sampled_rows": len(rows),
        "empty_status_share": round(empty / max(len(rows), 1), 4),
        "presentation_years_top": sorted(years.items(), key=lambda kv: -kv[1])[:5],
        "status_top": sorted(status.items(), key=lambda kv: -kv[1])[:14],
    }


def main():
    results = {}
    for year in WHOLE + CHUNK_YEARS:
        url = BASE.format(ano=year)
        size = file_size(url)
        header = header_for(url)
        started = time.time()
        entry = analyse(url, size, header, whole=(year in WHOLE))
        entry["file_bytes"] = size
        entry["mode"] = "whole file" if year in WHOLE else f"{CHUNKS} spread chunks"
        entry["seconds"] = round(time.time() - started, 1)
        results[year] = entry
        print(f"== {year} ({entry['mode']}, {size} bytes): {entry['sampled_rows']} rows, "
              f"empty status {entry['empty_status_share']:.1%} in {entry['seconds']}s")
        for key, n in entry["status_top"]:
            print(f"    {n:6d}  {key}")
        print("    presentation years:", entry["presentation_years_top"])
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
