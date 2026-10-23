#!/usr/bin/env python3
"""Construction script for the `camara-bill-advancement` candidate.

Task: at the instant a legislative proposition is presented to the Brazilian
Camara dos Deputados, will it ultimately be transformed into legal norm
(enacted) rather than archived - given only presentation-time context
(proposition type, the ementa written at introduction, the first author's
type/party/state, author count, and the presentation calendar)?

Where this runs
---------------
On a temporary worker: 70 anonymous GETs of the publisher's bulk year files
(proposicoes-1991..2025.csv, 747.4 MB total; proposicoesAutores-1991..2025.csv,
456.0 MB total; every year 200 OK, measured 2026-10-23). Files are parsed and
deleted one at a time, so peak disk is one 90 MB file plus the artifact.
`--proposicoes-dir` / `--autores-dir` accept local copies for a full-assertion
dry run on a coordinator-class machine.

Frame rules (each measured and reported)
----------------------------------------
* Grain: one row per proposition id. Files are processed in DESCENDING year
  order and the first occurrence of an id wins, so a bill re-numbered into a
  later legislature contributes its current (latest) row; collisions counted.
  Cohorts are defined by dataApresentacao over the union of files, never by
  file year (measured: ~2% of rows in file-YYYY are older bills re-numbered
  to the current 'ano').
* Label: from the publisher's own situation vocabulary in ultimoStatus
  (current status at the 2026-10 file vintage; file and API agree, measured):
  positive = situation code whose canonical description is 'Transformado em
  Norma Juridica' (code 1140 measured; the discovery record's '251' was a
  mis-indexed tramitacao column, corrected 2026-10-23); terminal negative =
  'Arquivada*' and the other settled non-enactment states (Vetado totalmente,
  Retirado pelo(a) Autor(a), Devolvida ao(a) Autor(a), Tramitacao Finalizada,
  Enviada ao Arquivo); merged = 'Transformado em nova proposicao' - EXCLUDED
  from the scored population (the outcome is carried by the merged-into
  bill; share recorded); every other status is non-terminal, and rows with
  no status at all (25-53% by year, measured; API confirms genuinely no
  tramitacao on record) are unobserved targets - excluded and counted per
  window, never a membership decision on future data.
* Right-censoring is a measured property, not a fixed legislature boundary:
  Brazilian bills carry across legislatures (measured: bills presented 2019
  still show live statuses updated in 2025-2026), so terminality is measured
  per window from the data and recorded, with per-year unobserved shares.
* Features are presentation-time only. EXCLUDED as post-hoc with recorded
  reasons: all ultimoStatus_* (label source), keywords and the
  proposicoesTemas family (Chamber indexing service, assigned after
  presentation), uriPropAnterior/Principal/Posterior (later-created links),
  urnFinal, uri/url fields, and ano/numero (the ~2% re-numbered bills prove
  'ano' can be re-assigned after presentation).
* Splits by dataApresentacao year: train 1991-2014, eval 2015-2018,
  holdout 2019-2022 (end-exclusive). 2023+ presentations are outside the
  windows and counted per year.
* Event key: apresentacao_year - enactments cluster by congressional session
  (a productive congress passes many bills), so the conservative independent
  -event count is distinct positive years; finer (year x party) counts are
  also recorded in summary.json.
* Cross-check fixtures: PL 4188/2021 (BR do Mar cabotagem programme; the
  publisher's own search page shows Situacao 'Transformado em Norma
  Juridica') must match in the union and be positive in the holdout window;
  the portal's published facet count for that situation (11,640 propositions
  of every year and type, read 2026-10-23) bounds the panel's positive total
  from above.
* Reference baselines measured before any model spend (train-estimated rate
  tables, stdlib rank AUC on the written rows): global rate, per-type
  (siglaTipo), per-party (first_author_party), per-year (apresentacao_year),
  per-type-and-party. No persistence leg exists at bill grain - each
  proposition is scored once, like the wb-ieg project grain. The full-model
  leg of the triad is the runner-contract baseline job on the accepted
  artifact, run separately.

Runner contract: public/train.csv, public/eval.csv, private/holdout.csv,
meta.json, quality.json - the layout `skills/dataset-qualification/` gates.

Licence: Camara dos Deputados open data - portal terms: "Todas as
informacoes publicadas no Portal da Camara sao de dominio publico,
gratuitas e podem ser reproduzidas desde que citada a fonte 'Camara dos
Deputados' e a autoria da informacao, quando houver." (termo-de-uso e
politica de privacidade, read 2026-10-21). Derived research dataset - never
the Chamber's official product. Our derived compilation: CC0-1.0 per
standing policy; source attribution carries through to any release.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

NAME = "camara-bill-advancement"
TARGET = "enacted"
POSITIVE_LABEL = 1

PROP_URL = "https://dadosabertos.camara.leg.br/arquivos/proposicoes/csv/proposicoes-{ano}.csv"
AUT_URL = "https://dadosabertos.camara.leg.br/arquivos/proposicoesAutores/csv/proposicoesAutores-{ano}.csv"
API_URL = "https://dadosabertos.camara.leg.br/api/v2/proposicoes/{pid}"
YEARS = list(range(1991, 2026))

# Shipped layout: id, features, target.
ID_COLUMNS = ["id"]
FEATURES = [
    "siglaTipo", "apresentacao_year", "apresentacao_month", "apresentacao_wday",
    "leg_year", "n_authors", "first_author_type", "first_author_party",
    "first_author_uf", "ementa",
]
HIGH_CARDINALITY = ["id", "ementa"]
CARRY_COLUMNS = []
COLUMNS = ID_COLUMNS + FEATURES + CARRY_COLUMNS + [TARGET]
LAYOUT = {"train": "public/train.csv", "eval": "public/eval.csv",
          "holdout": "private/holdout.csv"}

# Split windows in dataApresentacao years (end-exclusive, matching the gate's
# rows_within_declared_windows comparison).
TRAIN_START = 1991
EVAL_START, EVAL_END = 2015, 2019
HOLDOUT_START, HOLDOUT_END = 2019, 2023

# Situation-code classification (frozen from the publisher's vocabulary and
# the 2026-10-23 measured samples BEFORE any outcome is scored; the empirical
# code table with per-code counts is written to summary.json for audit).
POSITIVE_DESC = "Transformado em Norma Jurídica"
TERMINAL_NEGATIVE_EXACT = {
    "Vetado totalmente", "Retirado pelo(a) Autor(a)",
    "Devolvida ao(à) Autor(a)", "Tramitação Finalizada",
}
MERGED_PREFIX = "Transformado em nova proposi"
ARQUIVADA_SUBSTRING = "rquivada"          # Arquivada, Arquivada por ...
ARQUIVO_SUBSTRING = "nviada ao Arquivo"   # Enviada ao Arquivo (930 measured)

LABEL_SOURCE_COLUMNS = [
    "ultimoStatus_dataHora", "ultimoStatus_sequencia", "ultimoStatus_uriRelator",
    "ultimoStatus_idOrgao", "ultimoStatus_siglaOrgao", "ultimoStatus_uriOrgao",
    "ultimoStatus_regime", "ultimoStatus_descricaoTramitacao",
    "ultimoStatus_idTipoTramitacao", "ultimoStatus_descricaoSituacao",
    "ultimoStatus_idSituacao", "ultimoStatus_despacho", "ultimoStatus_apreciacao",
    "ultimoStatus_url",
]
POST_HOC_COLUMNS = LABEL_SOURCE_COLUMNS + [
    "keywords", "urnFinal", "uriPropAnterior", "uriPropPrincipal",
    "uriPropPosterior", "urlInteiroTeor", "uri", "uriOrgaoNumerador",
    "numero", "ano",
]
POST_HOC_REASONS = {
    "ultimoStatus_*": "current/last tramitacao state - the label source",
    "keywords": "assigned by the Chamber's indexing service after presentation",
    "proposicoesTemas": "same indexing service, post-presentation (not downloaded)",
    "uriPropAnterior/uriPropPrincipal/uriPropPosterior": "later-created links",
    "urnFinal": "resulting-law URN, final state",
    "uri/url/uriOrgaoNumerador": "record links, not presentation-time facts",
    "numero/ano": "measured: ~2% of rows are older bills re-numbered to the "
                  "current 'ano' when un-archived at a legislature boundary, so "
                  "'ano' can be re-assigned after presentation",
    "ementaDetalhada": "mostly empty; the ementa carries the presentation-time abstract",
}

# Legislature start years (48th legislature began 1987; four-year terms).
LEG_START_BASE, LEG_START_YEAR = 1987, 1987

# Anchors measured at discovery/construction-probe time (2026-10-23), with
# tolerances wide enough to absorb vintage drift but tight enough to catch a
# broken union or label rule.
EXPECTED = {
    "rows_fetched_total": (700_000, 1_050_000),
    "author_rows_total": (2_500_000, 5_500_000),
    "train_rows": (180_000, 420_000), "train_positives": (2_500, 20_000),
    "eval_rows": (25_000, 90_000), "eval_positives": (250, 2_500),
    "holdout_rows": (25_000, 110_000), "holdout_positives": (200, 2_500),
    "fixture_pl_4188_2021_positive": True,
    "positives_total_max": 11_640,   # portal search facet, all years/types, 2026-10-23
    "code_1140_canonical_desc": POSITIVE_DESC,
}
# Whole-file measured anchor: proposicoes-1991.csv parses to 4,436 rows with
# 311 code-1140 positives (7.0% of rows, 11.1% of status-bearing rows).
EXPECTED["file_1991_rows"] = (4_200, 4_700)

PREDICTION_QUESTION = (
    "At the instant a legislative proposition is presented to the Brazilian "
    "Camara dos Deputados, will it ultimately be transformed into legal norm "
    "(enacted) rather than archived - given only presentation-time context: "
    "proposition type, the ementa written at introduction, the first "
    "author's type/party/federation-unit, author count, and the presentation "
    "calendar?")
PREDICTION_TIME = (
    "The instant of presentation (dataApresentacao). Every shipped feature "
    "is written at or before that instant: siglaTipo is the proposition type "
    "assigned at presentation, ementa is the abstract written at "
    "introduction, n_authors and the first author's type/party/state come "
    "from the proposicoesAutores record of presentation, and the calendar "
    "features derive from dataApresentacao itself. The publisher's "
    "indexing-service fields (keywords, proposicoesTemas), all ultimoStatus "
    "fields (the current tramitacao state - the label source), the "
    "later-created uriProp* links, urnFinal, url/uri fields, and numero/ano "
    "(re-assigned for ~2% re-numbered bills) never ship - each with a "
    "recorded reason.")


def log(message: str) -> None:
    print(message, flush=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url: str, dest: Path, attempts: int = 3) -> dict:
    last_error = None
    for attempt in range(attempts):
        if attempt:
            time.sleep(2 ** attempt)
        started = time.time()
        request = urllib.request.Request(
            url, headers={"User-Agent": "dataset-factory/camara-build"})
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                last_modified = response.headers.get("Last-Modified")
                with dest.open("wb") as handle:
                    size = 0
                    while True:
                        chunk = response.read(1 << 20)
                        if not chunk:
                            break
                        handle.write(chunk)
                        size += len(chunk)
            return {"url": url, "bytes": size, "last_modified": last_modified,
                    "seconds": round(time.time() - started, 1),
                    "sha256": sha256_file(dest)}
        except Exception as error:  # bounded retry, reported on final failure
            last_error = error
            log(f"fetch attempt {attempt + 1} failed for {url[:90]}: {error}")
    raise SystemExit(f"fetch failed after {attempts} attempts: {url} ({last_error})")


def trim_to_record_boundaries(text: str, keep_first: bool = False) -> str:
    """Trim partial CSV records at the ends (quote-parity aware); quoted
    multi-line ementas make naive line splitting corrupt rows. By default the
    leading partial record is dropped (mid-file chunk); with keep_first the
    text is assumed to start at a record boundary (whole-file read, where the
    first record is the header)."""
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
    if keep_first:
        # Whole-file read: keep everything (a final record without a trailing
        # newline still parses; an incomplete trailing record is dropped by
        # the width check in the caller).
        return text
    if last is None:
        return ""
    if first is None:
        return ""
    return text[first + 1:last]


def parse_csv_file(path: Path, header_cache: dict) -> tuple[list[str], list[list[str]]]:
    """Parse a whole semicolon CSV into rows of raw cell strings."""
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    body = trim_to_record_boundaries(text, keep_first=True)
    reader = csv.reader(io.StringIO(body), delimiter=";", quotechar='"')
    rows = []
    header: list[str] = []
    for row in reader:
        if not header:
            header = row
            continue
        if len(row) == len(header):
            rows.append(row)
    if not header:
        raise SystemExit(f"no header parsed from {path}")
    header_cache["header"] = header
    if not rows:
        raise SystemExit(f"no complete rows parsed from {path}")
    return header, rows


def api_status_for(pid: str, attempts: int = 2):
    """One API v2 lookup of a proposition's current status (bounded use)."""
    last_error = None
    for attempt in range(attempts):
        if attempt:
            time.sleep(2)
        request = urllib.request.Request(
            API_URL.format(pid=pid), headers={"Accept": "application/json",
                                              "User-Agent": "dataset-factory/camara-build"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read())
            status = ((data.get("dados") or {}).get("statusProposicao") or {})
            return {"codSituacao": status.get("codSituacao"),
                    "descricaoSituacao": status.get("descricaoSituacao")}
        except Exception as error:  # noqa: BLE001 - bounded, reported
            last_error = error
    log(f"API lookup failed for {pid}: {last_error}")
    return None


def leg_year_for(presentation_year: int) -> int:
    base = LEG_START_BASE
    start = base + 4 * ((presentation_year - base) // 4)
    return presentation_year - start


def classify(code: str, canonical_desc: str) -> str:
    """positive / terminal_negative / merged / nonterminal / unknown_desc."""
    desc = (canonical_desc or "").strip()
    if not code:
        return "empty_status"
    if not desc:
        return "unknown_desc"
    if desc == POSITIVE_DESC:
        return "positive"
    if desc.startswith(MERGED_PREFIX):
        return "merged"
    if ARQUIVADA_SUBSTRING in desc or desc in TERMINAL_NEGATIVE_EXACT \
            or ARQUIVO_SUBSTRING in desc:
        return "terminal_negative"
    return "nonterminal"


def auc(labels: list[int], scores: list[float]) -> float | None:
    """Rank-based AUC (Mann-Whitney) with ties averaged, stdlib only."""
    pairs = sorted(zip(scores, labels), key=lambda pair: pair[0])
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        return None
    ranks = [0.0] * len(pairs)
    index = 0
    while index < len(pairs):
        stop = index
        while stop < len(pairs) and pairs[stop][0] == pairs[index][0]:
            stop += 1
        average = (index + stop + 1) / 2
        for position in range(index, stop):
            ranks[position] = average
        index = stop
    positive_rank_sum = sum(rank for rank, (_, label) in zip(ranks, pairs) if label == 1)
    return (positive_rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def fit_rate_table(rows: list[dict], *keys) -> dict[tuple, float]:
    totals: Counter = Counter()
    positives: Counter = Counter()
    for row in rows:
        key = tuple(row[name] for name in keys)
        totals[key] += 1
        positives[key] += row[TARGET]
    return {key: positives[key] / totals[key] for key in totals}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=f"Build the {NAME} extract")
    parser.add_argument("--out", default="/output/extract")
    parser.add_argument("--work-dir", default="/tmp/camara")
    parser.add_argument("--built-at", default=None)
    parser.add_argument("--proposicoes-dir", default=None,
                        help="local dir with proposicoes-YYYY.csv (dry run)")
    parser.add_argument("--autores-dir", default=None,
                        help="local dir with proposicoesAutores-YYYY.csv (dry run)")
    parser.add_argument("--keep-sources", action="store_true",
                        help="do not delete downloaded files as they land")
    args = parser.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    built_at = args.built_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    sources = {"proposicoes": {}, "proposicoesAutores": {}}
    fetch_totals = {"bytes": 0, "seconds": 0.0, "requests": 0}

    # ---------------------------------------------------------------- pass A
    log("== pass A: proposicoes union (descending file year, first id wins) ==")
    header = None
    bills: dict[str, dict] = {}          # id -> minimal fields (current row)
    collisions = 0
    outside_window: Counter = Counter()   # presented-year -> rows (2023+ or bad dates)
    bad_dates = 0
    code_desc_votes: dict[str, Counter] = defaultdict(Counter)
    prop_dir = Path(args.proposicoes_dir) if args.proposicoes_dir else None

    for year in sorted(YEARS, reverse=True):
        url = PROP_URL.format(ano=year)
        local = prop_dir / f"proposicoes-{year}.csv" if prop_dir else None
        dest = local if local is not None else work / f"proposicoes-{year}.csv"
        if local is None:
            info = fetch(url, dest)
            sources["proposicoes"][year] = info
            fetch_totals["bytes"] += info["bytes"]
            fetch_totals["seconds"] += info["seconds"]
            fetch_totals["requests"] += 1
        else:
            info = {"url": "local:" + str(local), "bytes": local.stat().st_size,
                    "last_modified": None, "seconds": 0.0,
                    "sha256": sha256_file(local)}
            sources["proposicoes"][year] = info

        header, rows = parse_csv_file(dest, {"header": header})
        if header is None:
            raise SystemExit("no header parsed")
        col = {name: index for index, name in enumerate(header)}
        wanted = ["id", "siglaTipo", "numero", "ano", "ementa", "dataApresentacao",
                  "ultimoStatus_idSituacao", "ultimoStatus_descricaoSituacao"]
        missing = [name for name in wanted + ["ultimoStatus_despacho"] if name not in col]
        if missing:
            raise SystemExit(f"proposicoes header missing fields: {missing}")
        kept = 0
        for row in rows:
            pid = (row[col["id"]] or "").strip()
            if not pid:
                continue
            if pid in bills:
                collisions += 1
                continue
            presented = (row[col["dataApresentacao"]] or "").strip()[:10]
            try:
                pyear = int(presented[:4])
                pmonth = int(presented[5:7])
                pday = int(presented[8:10])
                datetime(pyear, pmonth, pday)  # rejects impossible calendar dates
            except (ValueError, IndexError):
                bad_dates += 1
                continue
            if not (TRAIN_START <= pyear < HOLDOUT_END):
                outside_window[pyear] += 1
                continue
            code = (row[col["ultimoStatus_idSituacao"]] or "").strip()
            desc = (row[col["ultimoStatus_descricaoSituacao"]] or "").strip()
            if code:
                code_desc_votes[code][desc] += 1
            bills[pid] = {
                "id": pid,
                "siglaTipo": (row[col["siglaTipo"]] or "").strip(),
                "numero": (row[col["numero"]] or "").strip(),
                "ano": (row[col["ano"]] or "").strip(),
                "ementa": (row[col["ementa"]] or "").strip(),
                "pyear": pyear, "pmonth": pmonth, "pday": pday,
                "code": code,
            }
            kept += 1
        log(f"  {year}: {len(rows)} rows parsed, {kept} new in-window ids "
            f"(bills so far {len(bills)})")
        if not args.keep_sources and prop_dir is None:
            dest.unlink()
        del rows

    log(f"union: {len(bills)} in-window bills, {collisions} id collisions, "
        f"{bad_dates} bad dates, outside-window {dict(sorted(outside_window.items())[-6:])}")

    # ------------------------------------------------------------- code table
    canonical: dict[str, str] = {}
    for code, votes in code_desc_votes.items():
        non_empty = [(d, n) for d, n in votes.items() if d]
        if non_empty:
            non_empty.sort(key=lambda kv: (-kv[1], kv[0]))
            canonical[code] = non_empty[0][0]
        else:
            canonical[code] = ""
    unresolved = sorted(code for code, desc in canonical.items() if not desc)
    api_lookups = {}
    if unresolved:
        log(f"{len(unresolved)} situation codes never seen with a description; "
            f"bounded API lookups for up to 12")
        by_code = defaultdict(list)
        for pid, bill in bills.items():
            if bill["code"] in canonical and not canonical[bill["code"]]:
                by_code[bill["code"]].append(pid)
        for code in unresolved[:12]:
            if by_code.get(code):
                lookup = api_status_for(by_code[code][0])
                api_lookups[code] = lookup
                if lookup and lookup.get("descricaoSituacao"):
                    canonical[code] = str(lookup["descricaoSituacao"])
    classification = {code: classify(code, desc) for code, desc in canonical.items()}
    code_counts = Counter(bill["code"] for bill in bills.values())
    code_table = [{"code": code, "canonical_desc": canonical[code],
                   "class": classification[code],
                   "in_window_rows": code_counts[code]}
                  for code in sorted(canonical)]
    log("situation codes: " + json.dumps(code_table[:8]) + " ... "
        f"({len(code_table)} codes, {len(unresolved)} unresolved-by-data)")

    # ---------------------------------------------------------------- pass B
    log("== pass B: proposicoesAutores (descending file year, first id wins) ==")
    authors: dict[str, dict] = {}
    author_rows_total = 0
    aut_dir = Path(args.autores_dir) if args.autores_dir else None
    for year in sorted(YEARS, reverse=True):
        url = AUT_URL.format(ano=year)
        local = aut_dir / f"proposicoesAutores-{year}.csv" if aut_dir else None
        dest = local if local is not None else work / f"proposicoesAutores-{year}.csv"
        if local is None:
            info = fetch(url, dest)
            sources["proposicoesAutores"][year] = info
            fetch_totals["bytes"] += info["bytes"]
            fetch_totals["seconds"] += info["seconds"]
            fetch_totals["requests"] += 1
        else:
            info = {"url": "local:" + str(local), "bytes": local.stat().st_size,
                    "last_modified": None, "seconds": 0.0,
                    "sha256": sha256_file(local)}
            sources["proposicoesAutores"][year] = info
        text = dest.read_text(encoding="utf-8-sig", errors="replace")
        body = trim_to_record_boundaries(text, keep_first=True)
        reader = csv.reader(io.StringIO(body), delimiter=";", quotechar='"')
        rows = []
        aut_header = None
        for row in reader:
            if aut_header is None:
                aut_header = row
                continue
            if len(row) == len(aut_header):
                rows.append(row)
        aut_col = {name: index for index, name in enumerate(aut_header or [])}
        missing = [name for name in ("idProposicao", "tipoAutor", "siglaPartidoAutor",
                                     "siglaUFAutor", "ordemAssinatura", "proponente")
                   if name not in aut_col]
        if missing:
            raise SystemExit(f"autores header missing fields: {missing}")
        author_rows_total += len(rows)
        per_bill = defaultdict(list)
        for row in rows:
            pid = (row[aut_col["idProposicao"]] or "").strip()
            if pid:
                per_bill[pid].append(row)
        for pid, group in per_bill.items():
            if pid in authors:
                continue
            def author_key(item):
                index, arow = item
                proponente = (arow[aut_col["proponente"]] or "").strip()
                try:
                    order = int((arow[aut_col["ordemAssinatura"]] or "999") or 999)
                except ValueError:
                    order = 999
                return (0 if proponente == "1" else 1, order, index)
            _index, first = min(enumerate(group), key=author_key)
            authors[pid] = {
                "n": len(group),
                "type": (first[aut_col["tipoAutor"]] or "").strip(),
                "party": (first[aut_col["siglaPartidoAutor"]] or "").strip(),
                "uf": (first[aut_col["siglaUFAutor"]] or "").strip(),
            }
        log(f"  {year}: {len(rows)} author rows, {len(per_bill)} bills covered "
            f"(authors so far {len(authors)})")
        if not args.keep_sources and aut_dir is None:
            dest.unlink()
        del rows

    log(f"authors: {author_rows_total} rows, {len(authors)} bills with author rows")

    # --------------------------------------------------------------- build
    log("== build rows ==")
    rows_by_split = {"train": [], "eval": [], "holdout": []}
    buckets = {"train": Counter(), "eval": Counter(), "holdout": Counter()}
    fixture_hits = []
    for pid, bill in bills.items():
        pyear = bill["pyear"]
        if EVAL_START <= pyear < EVAL_END:
            split = "eval"
        elif HOLDOUT_START <= pyear < HOLDOUT_END:
            split = "holdout"
        else:
            split = "train"
        # fixture match (PL 4188/2021 - BR do Mar)
        if bill["siglaTipo"] == "PL" and bill["ano"] == "2021" and bill["numero"] == "4188":
            fixture_hits.append(bill)
        if "Cabotagem" in bill["ementa"] and "BR do Mar" in bill["ementa"]:
            fixture_hits.append(bill)
        kind = classification.get(bill["code"], "empty_status")
        if kind in ("empty_status", "unknown_desc", "nonterminal"):
            buckets[split][f"unobserved_{kind}"] += 1
            continue
        if kind == "merged":
            buckets[split]["merged_excluded"] += 1
            continue
        author = authors.get(pid)
        wday = datetime(bill["pyear"], bill["pmonth"], bill["pday"]).weekday()
        rows_by_split[split].append({
            "id": pid,
            "siglaTipo": bill["siglaTipo"],
            "apresentacao_year": pyear,
            "apresentacao_month": bill["pmonth"],
            "apresentacao_wday": wday,
            "leg_year": leg_year_for(pyear),
            "n_authors": author["n"] if author else 0,
            "first_author_type": author["type"] if author else "",
            "first_author_party": author["party"] if author else "",
            "first_author_uf": author["uf"] if author else "",
            "ementa": bill["ementa"],
            TARGET: 1 if kind == "positive" else 0,
        })
        buckets[split]["scored"] += 1
    for split in ("train", "eval", "holdout"):
        log(f"{split}: {buckets[split]}")

    # ---------------------------------------------------------------- write
    stats = {}
    for split, relative in LAYOUT.items():
        path = out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = sorted(rows_by_split[split], key=lambda row: int(row["id"]))
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        positives = sum(row[TARGET] for row in rows)
        event_keys = {row["apresentacao_year"] for row in rows if row[TARGET] == POSITIVE_LABEL}
        party_keys = {(row["apresentacao_year"], row["first_author_party"])
                      for row in rows if row[TARGET] == POSITIVE_LABEL}
        stats[split] = {"rows": len(rows), "positives": positives,
                        "positive_rate": round(positives / len(rows), 6) if rows else None,
                        "distinct_positive_years": len(event_keys),
                        "distinct_positive_year_party_cells": len(party_keys)}
        log(f"{split}: {stats[split]}")

    # The label source columns must be absent from every written header.
    for split, relative in LAYOUT.items():
        with (out / relative).open(newline="", encoding="utf-8") as handle:
            written_header = next(csv.reader(handle))
        if written_header != COLUMNS:
            log(f"FAIL: {relative} header differs from the declared columns")
            return 2
        for column in written_header:
            for banned in ("ultimoStatus", "urnFinal", "keyword", "uri", "url"):
                if banned in column:
                    log(f"FAIL: {relative} ships banned column {column}")
                    return 2

    # ----------------------------------------------------------- baselines
    train_rows = rows_by_split["train"]
    train_rate = (sum(r[TARGET] for r in train_rows) / len(train_rows)) if train_rows else 0.0
    type_table = fit_rate_table(train_rows, "siglaTipo")
    party_table = fit_rate_table(train_rows, "first_author_party")
    year_table = fit_rate_table(train_rows, "apresentacao_year")
    type_party_table = fit_rate_table(train_rows, "siglaTipo", "first_author_party")

    def rounded_auc(labels, scores):
        value = auc(labels, scores)
        return None if value is None else round(value, 4)

    baselines = {"global_rate_train": round(train_rate, 6),
                 "note": ("rate tables estimated on train rows only; stdlib rank "
                          "AUC on the written rows. No persistence leg exists "
                          "at bill grain - each proposition is scored once. The "
                          "full-model leg of the triad is the runner-contract "
                          "baseline job on the accepted artifact.")}
    for split in ("eval", "holdout"):
        rows = rows_by_split[split]
        labels = [row[TARGET] for row in rows]
        baselines[split] = {
            "majority_class_accuracy": round(train_rate, 4),
            "per_type_auc": rounded_auc(labels, [type_table.get((row["siglaTipo"],), train_rate) for row in rows]),
            "per_party_auc": rounded_auc(labels, [party_table.get((row["first_author_party"],), train_rate) for row in rows]),
            "per_year_auc": rounded_auc(labels, [year_table.get((row["apresentacao_year"],), train_rate) for row in rows]),
            "per_type_party_auc": rounded_auc(labels, [type_party_table.get((row["siglaTipo"], row["first_author_party"]), train_rate) for row in rows]),
        }
    log("reference baselines: " + json.dumps(baselines))

    # ------------------------------------------------- fixtures + assertions
    fixture_ok = any(b["code"] and classification.get(b["code"]) == "positive"
                     for b in fixture_hits)
    fixture_in_holdout = any(2019 <= b["pyear"] < 2023
                             for b in fixture_hits
                             if b["code"] and classification.get(b["code"]) == "positive")
    positives_total = sum(stats[s]["positives"] for s in LAYOUT)
    failures = []
    total_rows = len(bills)
    lo, hi = EXPECTED["rows_fetched_total"]
    if not (lo <= total_rows <= hi):
        failures.append(f"in-window rows {total_rows} outside expected [{lo}, {hi}]")
    for split in ("train", "eval", "holdout"):
        lo, hi = EXPECTED[f"{split}_rows"]
        if not (lo <= stats[split]["rows"] <= hi):
            failures.append(f"{split} rows {stats[split]['rows']} outside [{lo}, {hi}]")
        lo, hi = EXPECTED[f"{split}_positives"]
        if not (lo <= stats[split]["positives"] <= hi):
            failures.append(f"{split} positives {stats[split]['positives']} outside [{lo}, {hi}]")
        if stats[split]["positives"] == 0 or stats[split]["positives"] == stats[split]["rows"]:
            failures.append(f"{split} is single-class: {stats[split]}")
    if not fixture_hits:
        failures.append("fixture PL 4188/2021 (BR do Mar) not found in the union")
    elif not fixture_ok:
        failures.append(f"fixture PL 4188/2021 matched but not positive: "
                        f"{[b['code'] for b in fixture_hits]}")
    elif not fixture_in_holdout:
        failures.append("fixture PL 4188/2021 positive but outside the holdout window")
    if canonical.get("1140") != EXPECTED["code_1140_canonical_desc"]:
        failures.append(f"code 1140 canonical description is {canonical.get('1140')!r}, "
                       f"expected {EXPECTED['code_1140_canonical_desc']!r}")
    if classification.get("1140") != "positive":
        failures.append("code 1140 is not classified positive")
    if positives_total > EXPECTED["positives_total_max"]:
        failures.append(f"positives total {positives_total} exceeds the portal "
                        f"facet bound {EXPECTED['positives_total_max']}")
    if failures:
        for failure in failures:
            log(f"FAIL: {failure}")
        (out / "summary.json").write_text(json.dumps({
            "name": NAME, "built_at_utc": built_at, "failed": failures,
            "splits": stats, "buckets": {k: dict(v) for k, v in buckets.items()},
        }, indent=1) + "\n")
        return 2

    # ------------------------------------------------------------- summary
    ementa_lens = [len(r["ementa"]) for r in train_rows[:5000]]
    no_author = Counter(split for split in LAYOUT
                         for row in rows_by_split[split] if row["n_authors"] == 0)
    per_year_rates = {}
    for split in rows_by_split:
        years = defaultdict(lambda: [0, 0])
        for row in rows_by_split[split]:
            years[row["apresentacao_year"]][0] += 1
            years[row["apresentacao_year"]][1] += row[TARGET]
        per_year_rates[split] = {str(year): round(p / n, 4)
                                 for year, (n, p) in sorted(years.items())}
    union_digest = hashlib.sha256()
    for family in ("proposicoes", "proposicoesAutores"):
        for year in sorted(sources[family]):
            info = sources[family][year]
            union_digest.update(f"{family}-{year}-{info['bytes']}-{info['sha256']}".encode())

    summary = {
        "name": NAME,
        "built_at_utc": built_at,
        "sources": {"files": {family: {str(y): sources[family][y] for y in sorted(sources[family])}
                               for family in sources},
                    "fetch_totals": fetch_totals,
                    "union_sha256": union_digest.hexdigest()},
        "grain": "one row per proposition id (descending file year, first id "
                 "wins; collisions counted)",
        "rows_fetched_in_window": total_rows,
        "id_collisions": collisions,
        "bad_dates": bad_dates,
        "outside_window_by_year": {str(k): v for k, v in sorted(outside_window.items())},
        "situation_code_table": code_table,
        "code_classification": classification,
        "api_lookups_unresolved_codes": api_lookups,
        "splits": stats,
        "eligibility_buckets": {k: dict(v) for k, v in buckets.items()},
        "fixture_pl_4188_2021": {"hits": len(fixture_hits),
                                  "positive_hits": sum(1 for b in fixture_hits
                                                       if classification.get(b["code"]) == "positive"),
                                  "codes_seen": sorted({b["code"] for b in fixture_hits})},
        "portal_facet_cross_check": {
            "situation": "Transformado em Norma Jurídica",
            "portal_count_all_years_types": EXPECTED["positives_total_max"],
            "read_at": "2026-10-23 via the portal's own proposition-search facet "
                       "(buscaProposicoesWeb); the panel's in-window positive "
                       "total must not exceed it (it covers every year and type)",
            "panel_positives_total": positives_total,
        },
        "author_rows_total": author_rows_total,
        "bills_without_author_rows": dict(no_author),
        "ementa_train_sample": {"rows": len(ementa_lens),
                                 "mean_len": round(sum(ementa_lens) / max(len(ementa_lens), 1), 1),
                                 "empty_share": round(sum(1 for n in ementa_lens if n == 0)
                                                      / max(len(ementa_lens), 1), 4)},
        "per_year_enacted_rates": per_year_rates,
        "reference_baselines": baselines,
        "right_censoring_note": "Brazilian bills carry across legislatures "
                                 "(bills presented 2019 show live statuses updated "
                                 "in 2025-2026, file and API agree), so the scored "
                                 "population is bills whose fate is terminal at "
                                 "the 2026-10 vintage; unobserved shares rise with "
                                 "recency and are recorded per window above",
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")

    # ----------------------------------------------------------------- meta
    meta = {
        "name": NAME,
        "description": PREDICTION_QUESTION,
        "source": PROP_URL.replace("{ano}", "YYYY"),
        "license": "Câmara dos Deputados open data (portal terms: public "
                   "domain, free reproduction with attribution to the "
                   "'Câmara dos Deputados'). Derived research dataset - never "
                   "the Chamber's official product. Our derived compilation: "
                   "CC0-1.0.",
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": ID_COLUMNS,
        "columns": COLUMNS,
        "rows": {split: stats[split]["rows"] for split in LAYOUT},
        "positive_rate": {split: stats[split]["positive_rate"] for split in LAYOUT},
        "split": {"strategy": "temporal by dataApresentacao year (presentation instant)",
                  "boundaries": {"train": "presented 1991 .. 2014",
                                 "eval": "presented 2015 .. 2018",
                                 "holdout": "presented 2019 .. 2022",
                                 "excluded": "presented 2023+ (counted per year); "
                                             "no-status, non-terminal and merged "
                                             "rows counted per window"}},
        "label_rule": "enacted = 1 iff the proposition's current situation "
                      "code's canonical description is 'Transformado em Norma "
                      "Jurídica' (code 1140); terminal non-enactment states "
                      "(Arquivada*, Vetado totalmente, Retirado pelo(a) "
                      "Autor(a), Devolvida ao(à) Autor(a), Tramitação "
                      "Finalizada, Enviada ao Arquivo) are 0; 'Transformado em "
                      "nova proposição' (merged) rows are excluded from the "
                      "scored population with their share recorded; every "
                      "other status (and rows with no status at all) is an "
                      "unobserved target, excluded with per-window counts.",
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "prediction_time": PREDICTION_TIME,
        "features": FEATURES,
        "built_at_utc": built_at,
        "source_union_sha256": union_digest.hexdigest(),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    # -------------------------------------------------------------- quality
    feature_doc = (
        "siglaTipo is the proposition type abbreviation assigned at "
        "presentation (PL, PEC, PLP, PRC, REQ, RIC, ...). apresentacao_year / "
        "apresentacao_month / apresentacao_wday derive from dataApresentacao "
        "(the presentation instant; wday is 0=Monday..6=Sunday). leg_year is "
        "the year offset inside the four-year legislature (year minus "
        "legislature start; legislature terms began 1987, 1991, ..., 2023). "
        "n_authors is the number of author records for the proposition in the "
        "proposicoesAutores file of its own year file family (0 when the bill "
        "has no author rows on record). first_author_type / "
        "first_author_party / first_author_uf are the tipoAutor, "
        "siglaPartidoAutor and siglaUFAutor of the proponente author (first "
        "by ordemAssinatura when no proponente row exists); empty strings "
        "when the author record or the field is absent - e.g. non-deputy "
        "authors (commissions, executive organs) carry no party. ementa is "
        "the abstract written at introduction, shipped verbatim (a "
        "high-cardinality text column; the runner's baseline drops it and "
        "richer solvers may featurize it). numero and ano are excluded "
        "because re-numbered bills prove 'ano' can be re-assigned after "
        "presentation; keywords/temas (indexing service), all ultimoStatus "
        "fields (label source), uri/url/urn fields and uriProp* links are "
        "post-hoc and never ship.")
    quality = {
        "name": NAME,
        "task": {"question": PREDICTION_QUESTION, "prediction_time": PREDICTION_TIME},
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "time_column": "apresentacao_year",
        "event_key_column": "apresentacao_year",
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "feature_documentation": feature_doc,
        "carry_columns": CARRY_COLUMNS,
        "id_columns": ID_COLUMNS,
        "high_cardinality_columns": HIGH_CARDINALITY,
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "post_hoc_columns": POST_HOC_COLUMNS,
        "post_hoc_reasons": POST_HOC_REASONS,
        "measurements": [
            {"column": "siglaTipo",
             "unit": "proposition type abbreviation (publisher vocabulary)",
             "frame": "assigned at presentation; the publisher's type table"},
            {"column": "apresentacao_year",
             "unit": "calendar year of dataApresentacao",
             "frame": "the presentation instant; also the time column and the "
                      "conservative event key (enactments cluster by "
                      "congressional session)"},
            {"column": "apresentacao_month",
             "unit": "calendar month number (1-12)",
             "frame": "month of the presentation instant"},
            {"column": "apresentacao_wday",
             "unit": "weekday of presentation (0=Monday .. 6=Sunday)",
             "frame": "day-of-week of the presentation instant"},
            {"column": "leg_year",
             "unit": "years since the legislature began (0-3)",
             "frame": "presentation year minus legislature start (1987 + 4k); "
                      "fixed public calendar facts, knowable at presentation"},
            {"column": "n_authors",
             "unit": "count of author records",
             "frame": "authors recorded at presentation "
                      "(proposicoesAutores family)"},
            {"column": "first_author_type",
             "unit": "tipoAutor of the proponente author (Deputado(a), "
                     "Órgão do Poder Executivo, COMISSÃO PERMANENTE, ...)",
             "frame": "author type as recorded at presentation; empty when no "
                      "author row exists"},
            {"column": "first_author_party",
             "unit": "party abbreviation (siglaPartidoAutor)",
             "frame": "the first author's party at presentation; empty for "
                      "non-deputy authors and missing records"},
            {"column": "first_author_uf",
             "unit": "federation unit abbreviation (siglaUFAutor)",
             "frame": "the first author's state at presentation; empty for "
                      "non-deputy authors and missing records"},
            {"column": "ementa",
             "unit": "free text (Portuguese), the bill's abstract",
             "frame": "written at introduction; high-cardinality declared - "
                      "unique-valued per row, never a leak"},
            {"column": TARGET,
             "unit": "binary indicator",
             "frame": "1 iff the proposition's current situation is "
                      "'Transformado em Norma Jurídica' (code 1140); the "
                      "situation fields never ship"},
        ],
        "provenance": {
            "situation_code_table": code_table,
            "note": "canonical descriptions resolved by majority vote over "
                    "every row carrying the code (the publisher's bulk rows "
                    "often carry empty per-row descriptions; the code is the "
                    "stable key). Codes never seen with any description were "
                    "resolved by bounded API v2 lookups; any still-unknown "
                    "code counts its rows as unobserved.",
            "right_censoring": "bills carry across legislatures; terminality "
                               "measured per window at the 2026-10 vintage and "
                               "recorded in summary.json eligibility_buckets",
        },
        "timing": {
            "prediction_instant": {
                "kind": "event_time",
                "period": "Bill presentation (the proposition's own "
                          "dataApresentacao)",
                "days_after_period_end": 0,
                "citation": "Publisher file documentation: 'cada registro "
                            "contém dados sobre uma proposição apresentada à "
                            "Câmara dos Deputados para deliberação' "
                            "(arquivos/proposicoes); dataApresentacao sampled "
                            "on every file (e.g. id 2190407 PL 1/2019 "
                            "presented 2019; id 13543 PDC 1991). The label is "
                            "the eventual outcome observed in the current "
                            "vintage - the same retro-observed-outcome shape "
                            "as the wb-ieg approval-instant task.",
            },
            "features": {
                "period": "Bill presentation",
                "published_days_after_period_end": 0,
                "source_kind": "administrative_record",
            },
            "row_selection": {
                "latest_period_used": "the row's own dataApresentacao "
                                      "(in-window cohorts 1991-2022)",
                "fields": FEATURES,
                "basis": "eligibility reads only the presentation date's "
                         "window membership; the scored population is bills "
                         "whose fate is terminal at the 2026-10 file vintage. "
                         "No-status, non-terminal and merged rows are "
                         "unobserved targets - counted per window in "
                         "summary.json, never membership decisions on future "
                         "data.",
            },
            "observations": [],
        },
        "split_windows": {
            "train": {"start": str(TRAIN_START), "end": str(EVAL_START)},
            "eval": {"start": str(EVAL_START), "end": str(EVAL_END)},
            "holdout": {"start": str(HOLDOUT_START), "end": str(HOLDOUT_END)},
        },
        "split_boundaries": {
            "train": "presented 1991 .. 2014",
            "eval": "presented 2015 .. 2018",
            "holdout": "presented 2019 .. 2022",
            "excluded": "presented 2023+ (counted per year); no-status, "
                        "non-terminal and merged rows counted per window",
        },
        "expected_duplicate_ids": 0,
        "id_columns_are_entity_keys": True,
        "id_columns_note": "one row per proposition id by construction "
                           "(descending file year, first occurrence wins); no "
                           "identifier repeats inside a split or spans two",
        "positive_events": {split: {"positives": stats[split]["positives"],
                                     "distinct_events": stats[split]["distinct_positive_years"]}
                            for split in LAYOUT},
        "positive_events_note": "an event is one distinct presentation year "
                                "carrying at least one enactment (the event "
                                "key column, exactly as the gate recomputes "
                                "it): enactments cluster by congressional "
                                "session, so the year is the conservative "
                                "cluster. The finer (year x first party) "
                                "positive cell counts are recorded in "
                                "summary.json beside it.",
        "splits": LAYOUT,
        "external_threshold": False,
        "cross_check": {
            "fixture_pl_4188_2021": {
                "bill": "PL 4188/2021 (Programa de Estímulo ao Transporte "
                        "por Cabotagem - BR do Mar)",
                "expected": "enacted (the publisher's own proposition-search "
                            "page shows Situação 'Transformado em Norma "
                            "Jurídica'; read 2026-10-23)",
                "asserted": "matched in the union, classified positive, "
                            "presented inside the holdout window",
                "hits": summary["fixture_pl_4188_2021"],
            },
            "portal_facet": summary["portal_facet_cross_check"],
        },
        "built_at_utc": built_at,
        "shipped_columns": COLUMNS,
    }
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")

    log("== done ==")
    log(json.dumps({"splits": stats, "buckets": {k: dict(v) for k, v in buckets.items()},
                    "reference_baselines": baselines}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
