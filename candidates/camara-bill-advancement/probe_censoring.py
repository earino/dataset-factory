#!/usr/bin/env python3
"""Right-censoring probe for camara-bill-advancement (run from the coordinator).

Measures the current-vintage ultimoStatus mix on ranged samples of the
proposicoes bulk files, per presentation-year cohort, to answer one question
before construction: are the recorded windows (train 1991-2014, eval
2015-2018, holdout 2019-2022) settled as of the current vintage, or do the
2019-2022 cohorts still carry non-terminal (right-censored) statuses?

Ranged samples: 3 x 1.5 MB per file, spread across the file so the sample is
not just the head. Anonymous, ~9-13 MB total download.
"""
import csv
import io
import json
import time
import urllib.request

BASE = "https://dadosabertos.camara.leg.br/arquivos/proposicoes/csv/proposicoes-{ano}.csv"
FILES = [1991, 1995, 2000, 2005, 2010, 2015, 2019, 2021, 2022]
CHUNKS = 3
CHUNK_BYTES = 1_500_000


def fetch_range(url: str, start: int, length: int, attempts: int = 3):
    last = None
    for attempt in range(attempts):
        if attempt:
            time.sleep(2 ** attempt)
        req = urllib.request.Request(url, headers={
            "Range": f"bytes={start}-{start + length - 1}",
            "User-Agent": "dataset-factory/camara-censoring-probe"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except Exception as error:
            last = error
    raise SystemExit(f"range fetch failed: {url} ({last})")


def content_length(url: str) -> int:
    req = urllib.request.Request(url, method="HEAD",
                                  headers={"User-Agent": "dataset-factory/camara-censoring-probe"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return int(resp.headers["Content-Length"])


def sample_rows(url: str, size: int):
    """Yield parsed rows from spread ranged chunks (first chunk starts at 0 to
    include the header; mid rows may be partial - skipped on parse)."""
    seen_header = None
    for index in range(CHUNKS):
        start = 0 if index == 0 else (size // CHUNKS) * index - 4096
        raw = fetch_range(url, start, CHUNK_BYTES)
        text = raw.decode("utf-8", errors="replace")
        # drop the leading partial line unless we are at byte 0
        if start > 0:
            text = text.split("\n", 1)[1] if "\n" in text else text
        lines = text.split("\n")
        # last line is likely partial unless it ends the file
        if index < CHUNKS - 1:
            lines = lines[:-1]
        reader = csv.reader(io.StringIO("\n".join(lines)), delimiter=";")
        header = None
        for row in reader:
            if header is None:
                if seen_header is not None and row != seen_header:
                    pass
                seen_header = row
                header = row
                continue
            if len(row) == len(header):
                yield dict(zip(header, row))


def main():
    out = {}
    for year in FILES:
        url = BASE.format(ano=year)
        size = content_length(url)
        rows = list(sample_rows(url, size))
        cohort = {}
        status = {}
        for row in rows:
            presented = (row.get("dataApresentacao") or "")[:4]
            cohort[presented] = cohort.get(presented, 0) + 1
            code = (row.get("ultimoStatus_idSituacao") or "").strip()
            desc = (row.get("ultimoStatus_descricaoSituacao") or "").strip()
            key = f"{code}|{desc[:40]}"
            status[key] = status.get(key, 0) + 1
        top = sorted(status.items(), key=lambda kv: -kv[1])[:12]
        nonterminal = sum(n for k, n in status.items()
                          if not k.split("|")[1].lower().startswith(("arquivada", "transformado")))
        out[year] = {
            "file_bytes": size, "sampled_rows": len(rows),
            "presentation_years_top": sorted(cohort.items(), key=lambda kv: -kv[1])[:4],
            "status_top": top,
            "nonterminal_share": round(nonterminal / len(rows), 4),
        }
        print(f"{year}: bytes={size} rows={len(rows)} nonterminal={out[year]['nonterminal_share']}")
        for k, n in top:
            print(f"    {n:6d}  {k}")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
