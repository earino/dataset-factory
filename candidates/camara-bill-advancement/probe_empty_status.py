#!/usr/bin/env python3
"""Probe 3: what are the empty-ultimoStatus rows, and does the API agree?

1. Parse the whole proposicoes-1991.csv (4.4 MB) and the first 1.5 MB of
   proposicoes-2019.csv with the quote-parity parser (probe_censoring2).
2. Split by ultimoStatus_idSituacao present/empty; tabulate siglaTipo mix
   and dataApresentacao year mix for each group.
3. For up to 6 sample ids with empty status, GET /api/v2/proposicoes/{id}
   and print the API's statusProposicao (descricaoSituacao/codSituacao) to
   test whether the empty status is a file gap or a real 'no tramitacao
   on record' state.
"""
import csv
import io
import json
import time
import urllib.request

BASE = "https://dadosabertos.camara.leg.br/arquivos/proposicoes/csv/proposicoes-{ano}.csv"
UA = {"User-Agent": "dataset-factory/camara-probe3"}


def fetch(url, headers=None, attempts=3):
    last = None
    for attempt in range(attempts):
        if attempt:
            time.sleep(2 ** attempt)
        try:
            req = urllib.request.Request(url, headers={**(headers or {}), **UA})
            with urllib.request.urlopen(req, timeout=90) as resp:
                return resp.read()
        except Exception as error:
            last = error
    raise SystemExit(f"fetch failed: {url} ({last})")


def trim(text):
    in_quote = False
    first = last = None
    for i, ch in enumerate(text):
        if ch == '"':
            in_quote = not in_quote
        elif ch == "\n" and not in_quote:
            if first is None:
                first = i
            last = i
    return "" if first is None else text[first + 1:last]


def parse(text, header):
    reader = csv.reader(io.StringIO(trim(text)), delimiter=";", quotechar='"')
    return [dict(zip(header, r)) for r in reader if len(r) == len(header)]


def year_rows(year, size):
    url = BASE.format(ano=year)
    head = fetch(url, {"Range": "bytes=0-65536"}).decode("utf-8-sig", errors="replace")
    in_q = False
    cut = None
    for i, ch in enumerate(head):
        if ch == '"':
            in_q = not in_q
        elif ch == "\n" and not in_q:
            cut = i
            break
    header = next(csv.reader(io.StringIO(head[:cut]), delimiter=";", quotechar='"'))
    raw = fetch(url, {"Range": f"bytes=0-{size - 1}"}).decode("utf-8-sig", errors="replace")
    return header, parse(raw, header)


def main():
    for year, size in ((1991, 4451452), (2019, 1500000)):
        header, rows = year_rows(year, size)
        groups = {"empty": [], "status": []}
        for row in rows:
            code = (row.get("ultimoStatus_idSituacao") or "").strip()
            (groups["empty"] if not code else groups["status"]).append(row)
        print(f"== {year}: {len(rows)} rows, empty {len(groups['empty'])} "
              f"({len(groups['empty'])/max(len(rows),1):.1%})")
        for name, group in groups.items():
            types = {}
            for row in group:
                t = (row.get("siglaTipo") or "?").strip()
                types[t] = types.get(t, 0) + 1
            top = sorted(types.items(), key=lambda kv: -kv[1])[:10]
            print(f"   {name} ({len(group)}): types {top}")
        sample = [r["id"] for r in groups["empty"][:6]]
        for pid in sample:
            try:
                data = json.loads(fetch(f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{pid}"))
                status = (data.get("dados") or {}).get("statusProposicao") or {}
                tipo = (data.get("dados") or {}).get("siglaTipo")
                print(f"   id {pid} ({tipo}): API status code="
                      f"{status.get('codSituacao')!r} desc={status.get('descricaoSituacao')!r}")
            except Exception as error:
                print(f"   id {pid}: API fetch failed: {error}")
            time.sleep(0.4)


if __name__ == "__main__":
    main()
