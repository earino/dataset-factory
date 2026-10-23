#!/usr/bin/env python3
"""Local smoke test for the camara-bill-advancement build (no worker spend).

Generates 35 synthetic proposicoes + 35 proposicoesAutores year files with
edge cases (quoted multi-line ementas, a true id collision across year
files, an everywhere-undescribed situation code, proponente ordering, the
PL 4188/2021 fixture, out-of-window presentations), then runs the real
build.py logic with EXPECTED ranges patched to synthetic scale (loaded via
exec like the qualification fixtures, so nothing is written into the
shipped bundle) and asserts on the written extract.

Run: python3 tests_smoke_build.py   (from anywhere; writes under a temp dir)
"""
import csv
import json
import sys
import tempfile
from pathlib import Path

BUILD = Path(__file__).resolve().parents[0] / "source" / "build.py"
YEARS = list(range(1991, 2026))
ROWS_PER_YEAR = 5_000          # 35 x 5,000 = 175,000 rows, ~160k in-window
EMBED = "linha um\nlinha dois com ; ponto e vírgula"   # quoted multi-line test
FIXTURE_PID = 999_999_999      # PL 4188/2021 fixture, fixed id
COLLISION_PID = 1_000_000 + (2025 - 2020) * ROWS_PER_YEAR + 1  # first id of the 2020 file


def pid_for(file_year: int, index: int) -> int:
    """Deterministic id: unique per (file year, row index)."""
    return 1_000_000 + (2025 - file_year) * ROWS_PER_YEAR + index + 1


PROP_HEADER = ["id", "uri", "siglaTipo", "numero", "ano", "codTipo",
               "descricaoTipo", "ementa", "ementaDetalhada", "keywords",
               "dataApresentacao", "uriOrgaoNumerador", "uriPropAnterior",
               "uriPropPrincipal", "uriPropPosterior", "urlInteiroTeor",
               "urnFinal", "ultimoStatus_dataHora", "ultimoStatus_sequencia",
               "ultimoStatus_uriRelator", "ultimoStatus_idOrgao",
               "ultimoStatus_siglaOrgao", "ultimoStatus_uriOrgao",
               "ultimoStatus_regime", "ultimoStatus_descricaoTramitacao",
               "ultimoStatus_idTipoTramitacao", "ultimoStatus_descricaoSituacao",
               "ultimoStatus_idSituacao", "ultimoStatus_despacho",
               "ultimoStatus_apreciacao", "ultimoStatus_url"]
AUT_HEADER = ["idProposicao", "uriProposicao", "idDeputadoAutor", "uriAutor",
              "codTipoAutor", "tipoAutor", "nomeAutor", "siglaPartidoAutor",
              "uriPartidoAutor", "siglaUFAutor", "ordemAssinatura", "proponente"]


def prop_row(pid, file_year, index, sigla="PL", numero=None, ementa=None,
             presented=None, code="923", desc="Arquivada"):
    return [pid, "uri", sigla, numero if numero is not None else index + 1,
            file_year, "139", "Projeto de Lei",
            ementa if ementa is not None else f"Ementa sintética {pid}",
            "", "",            f"{presented} 10:00", "uri", "", "", "", "", "",
            f"{file_year}-07-01 00:00", "1", "", "180", "PLEN", "uri",
            "Estatutário", "Arquivamento", "100", desc, code, "despacho",
            "Proposição", "url"]


def aut_row(pid, order, proponente, party="PT", uf="MG", tipo="Deputado(a)"):
    return [pid, "uri", "", "uri", "10000", tipo, f"Deputado {order}",
            party, "uri", uf, str(order), str(proponente)]


def synthetic_prop_row(file_year, index):
    pid = pid_for(file_year, index)
    presented = f"{file_year}-06-15"
    if index % 50 == 7 and file_year > 1991:
        presented = f"{file_year - 1}-06-15"     # re-numbered/re-dated rows
    roll = index % 100
    if roll < 60:
        code, desc = "923", "Arquivada"
    elif roll < 62:
        code, desc = "1140", "Transformado em Norma Jurídica"
    elif roll < 64:
        code, desc = "1230", "Transformado em nova proposição"
    elif roll < 70:
        code, desc = "925", "Tramitando em Conjunto"
    elif roll < 80:
        code, desc = "", ""
    elif roll < 82:
        code, desc = "9999", ""                  # everywhere-undescribed code
    else:
        code, desc = "923", "Arquivada"
    ementa = f"Ementa sintética {pid}"
    if index % 500 == 3:
        ementa = f"Ementa com\n{EMBED} {pid}"
    return prop_row(pid, file_year, index, ementa=ementa, presented=presented,
                    code=code, desc=desc)


def synthetic(out_dir: Path, kind: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    for file_year in sorted(YEARS, reverse=True):
        path = out_dir / f"{kind}-{file_year}.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter=";", quotechar='"',
                                quoting=csv.QUOTE_ALL)
            if kind == "proposicoes":
                writer.writerow(PROP_HEADER)
                for index in range(ROWS_PER_YEAR):
                    writer.writerow(synthetic_prop_row(file_year, index))
                if file_year == 2021:
                    # the fixture: PL 4188/2021, enacted, presented 2021-11-26
                    writer.writerow(prop_row(
                        FIXTURE_PID, 2021, 0, numero=4188,
                        ementa="Institui o Programa de Estímulo ao Transporte "
                               "por Cabotagem - BR do Mar",
                        presented="2021-11-26",
                        code="1140", desc="Transformado em Norma Jurídica"))
                if file_year == 2019:
                    # true collision: re-uses the 2020 file's first id, whose
                    # row already entered the union (presented 2020)
                    writer.writerow(prop_row(
                        COLLISION_PID, 2019, 0,
                        ementa="duplicada entre arquivos",
                        presented="2019-03-03", code="923", desc="Arquivada"))
            else:
                writer.writerow(AUT_HEADER)
                for index in range(ROWS_PER_YEAR):
                    pid = pid_for(file_year, index)
                    if index % 10 == 5:
                        # proponente on the higher-ordemAssinatura row: the
                        # build must prefer the proponente (PROPR) over the
                        # lower-ordem non-proponente row (PSDB)
                        writer.writerow(aut_row(pid, 2, 1, party="PROPR", uf="XX"))
                        writer.writerow(aut_row(pid, 1, 0, party="PSDB", uf="SP"))
                    else:
                        writer.writerow(aut_row(pid, 1, 1))
                if file_year == 2021:
                    writer.writerow([FIXTURE_PID, "uri", "", "uri", "30000",
                                     "Órgão do Poder Executivo",
                                     "Poder Executivo", "", "", "", "1", "1"])


def main():
    root = Path(tempfile.mkdtemp(prefix="camara-smoke-"))
    prop_dir = root / "proposicoes"
    aut_dir = root / "autores"
    synthetic(prop_dir, "proposicoes")
    synthetic(aut_dir, "proposicoesAutores")
    print(f"synthetic files under {root}")

    namespace = {"__name__": "camara_build_smoke"}
    with BUILD.open() as handle:
        code = compile(handle.read(), str(BUILD), "exec")
    exec(code, namespace)  # noqa: S102 - intentional load of our own build

    # Patch the anchors to synthetic scale, then run the real main().
    expected = namespace["EXPECTED"]  # type: ignore[index]
    assert isinstance(expected, dict)
    expected.update({
        "rows_fetched_total": (100_000, 250_000),
        "author_rows_total": (100_000, 500_000),
        "train_rows": (50_000, 130_000), "train_positives": (100, 5_000),
        "eval_rows": (8_000, 25_000), "eval_positives": (50, 1_200),
        "holdout_rows": (8_000, 25_000), "holdout_positives": (50, 1_200),
    })
    main_fn = namespace["main"]  # type: ignore[index]
    out = root / "extract"
    status = main_fn([
        "--out", str(out), "--work-dir", str(root / "work"),
        "--built-at", "2026-10-23T00:00:00Z",
        "--proposicoes-dir", str(prop_dir),
        "--autores-dir", str(aut_dir),
    ])
    print(f"build exit status: {status}")
    if status != 0:
        sys.exit(status)

    problems = []
    for split, relative, low, high in (("train", "public/train.csv", 1991, 2015),
                                       ("eval", "public/eval.csv", 2015, 2019),
                                       ("holdout", "private/holdout.csv", 2019, 2023)):
        path = out / relative
        if not path.exists():
            problems.append(f"missing {relative}")
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        years = {int(r["apresentacao_year"]) for r in rows}
        if not years <= set(range(low, high)):
            problems.append(f"{split} years outside window: {sorted(years)[:5]}")
        ids = [r["id"] for r in rows]
        if len(ids) != len(set(ids)):
            problems.append(f"{split}: duplicate ids")
        for r in rows[:200]:
            for banned in ("ultimoStatus", "keywords", "urnFinal"):
                if banned in r:
                    problems.append(f"{split} ships banned column {banned}")
                    break
        print(f"{split}: {len(rows)} rows, {sum(int(r['enacted']) for r in rows)} positives")

    # fixture row must be in holdout, positive, with the executive author type
    with (out / "private/holdout.csv").open(newline="", encoding="utf-8") as handle:
        rows = {r["id"]: r for r in csv.DictReader(handle)}
    fixture = rows.get(str(FIXTURE_PID))
    if fixture is None:
        problems.append("fixture row missing from holdout")
    else:
        if fixture["enacted"] != "1":
            problems.append("fixture row not positive")
        if fixture["apresentacao_year"] != "2021":
            problems.append("fixture presented-year wrong")
        if fixture["first_author_type"] != "Órgão do Poder Executivo":
            problems.append(f"fixture author type wrong: {fixture['first_author_type']!r}")

    # the collision bill must appear exactly once, with the 2020-file row
    collision_rows = [r for r in rows.values() if r["id"] == str(COLLISION_PID)]
    if len(collision_rows) != 1:
        problems.append(f"collision id appears {len(collision_rows)} times")
    elif collision_rows[0]["apresentacao_year"] != "2020":
        problems.append("collision row kept the wrong (later) occurrence")

    # multi-line ementa survives: a train row whose ementa contains a newline
    with (out / "public/train.csv").open(newline="", encoding="utf-8") as handle:
        multiline = [r for r in csv.DictReader(handle) if "\n" in r["ementa"]]
    if not multiline:
        problems.append("no multi-line ementa survived in train")

    # proponente ordering: bills whose proponente has the higher
    # ordemAssinatura must carry the proponente's party (PROPR), never the
    # lower-ordem non-proponente row's party (PSDB)
    with (out / "public/train.csv").open(newline="", encoding="utf-8") as handle:
        first_rows = list(csv.DictReader(handle))[:2000]
    propr = [r for r in first_rows if r["first_author_party"] == "PROPR"]
    psdb = [r for r in first_rows if r["first_author_party"] == "PSDB"]
    if not propr:
        problems.append("proponente ordering rule never produced a PROPR row")
    if psdb:
        problems.append("non-proponente party (PSDB) won the author ordering")

    summary = json.loads((out / "summary.json").read_text())
    buckets = summary["eligibility_buckets"]
    unknown = sum(b.get("unobserved_unknown_desc", 0) for b in buckets.values())
    merged = sum(b.get("merged_excluded", 0) for b in buckets.values())
    empty = sum(b.get("unobserved_empty_status", 0) for b in buckets.values())
    if unknown == 0:
        problems.append("unknown_desc bucket never used")
    if merged == 0:
        problems.append("merged_excluded bucket never used")
    if empty == 0:
        problems.append("empty_status bucket never used")
    if summary["id_collisions"] < 1:
        problems.append("id collision not counted")
    print(f"id collisions counted: {summary['id_collisions']}; unknown={unknown}, "
          f"merged={merged}, empty={empty}")

    for name in ("meta.json", "quality.json", "summary.json"):
        if not (out / name).exists():
            problems.append(f"missing {name}")
    quality = json.loads((out / "quality.json").read_text())
    for key in ("timing", "split_windows", "positive_events", "shipped_columns",
                "event_key_column", "time_column"):
        if key not in quality:
            problems.append(f"quality.json missing {key}")

    if problems:
        print("SMOKE FAILURES:")
        for problem in problems:
            print(f"  - {problem}")
        sys.exit(1)
    print("SMOKE OK")
    print(f"smoke scratch kept at {root} (delete manually if inspecting)")


if __name__ == "__main__":
    main()
