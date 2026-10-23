#!/usr/bin/env python3
"""Probe 4: does the bulk file's ultimoStatus agree with the live API?

For a bounded sample of proposicoes-2019.csv rows (first 1.5 MB):
  - rows whose file status is non-terminal (e.g. 'Tramitando em Conjunto'),
  - rows whose file status is 'Arquivada',
  - rows whose file status is empty,
GET /api/v2/proposicoes/{id} and compare the API's statusProposicao
(codSituacao/descricaoSituacao) with the file row's ultimoStatus.

Answers whether the per-year bulk file is a stale snapshot for
closed-legislature cohorts (label design) or matches the live record.
"""
import csv
import io
import json
import time
import urllib.request

BASE = "https://dadosabertos.camara.leg.br/arquivos/proposicoes/csv/proposicoes-{ano}.csv"
API = "https://dadosabertos.camara.leg.br/api/v2/proposicoes/{pid}"
UA = {"User-Agent": "dataset-factory/camara-probe4"}
SAMPLE_PER_GROUP = 5


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


def main():
    year = 2019
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
    raw = fetch(url, {"Range": "bytes=0-1499999"}).decode("utf-8-sig", errors="replace")
    rows = parse(raw, header)
    print(f"{len(rows)} rows parsed from the first 1.5 MB of the {year} file")

    nonterminal_words = ("tramitando", "aguardando", "pronta para pauta")
    groups = {"file_nonterminal": [], "file_arquivada": [], "file_empty": []}
    for row in rows:
        code = (row.get("ultimoStatus_idSituacao") or "").strip()
        desc = (row.get("ultimoStatus_descricaoSituacao") or "").strip()
        presented = (row.get("dataApresentacao") or "")[:4]
        if presented != str(year):
            continue
        entry = (row["id"], code, desc, (row.get("ultimoStatus_dataHora") or "")[:19])
        if not code:
            groups["file_empty"].append(entry)
        elif "arquivada" in desc.lower():
            groups["file_arquivada"].append(entry)
        elif any(w in desc.lower() for w in nonterminal_words):
            groups["file_nonterminal"].append(entry)

    for name, entries in groups.items():
        print(f"== {name}: {len(entries)} rows in this chunk; sampling {SAMPLE_PER_GROUP}")
        for pid, fcode, fdesc, fwhen in entries[:SAMPLE_PER_GROUP]:
            try:
                data = json.loads(fetch(API.format(pid=pid)))
                dados = data.get("dados") or {}
                status = dados.get("statusProposicao") or {}
                acode = status.get("codSituacao")
                adesc = status.get("descricaoSituacao")
                agree = "AGREE" if str(acode) == fcode else "DIFFER"
                print(f"   id {pid} ({dados.get('siglaTipo')} {dados.get('numero')}/{dados.get('ano')}, "
                      f"file dataHora {fwhen}): "
                      f"file {fcode}|{fdesc[:30]!r} vs api {acode}|{adesc!r} -> {agree}")
            except Exception as error:
                print(f"   id {pid}: API fetch failed: {error}")
            time.sleep(0.4)


if __name__ == "__main__":
    main()
