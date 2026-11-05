#!/usr/bin/env python3
"""Fixture test for the ibama-auto-infracao-recidivism construction (build.py).

Builds a small synthetic per-year-member zip with hand-computed expectations
and runs build.py on it as a subprocess (no import: the real CLI is what the
worker runs, and no __pycache__ is written anywhere). Proves, before the live
source is touched:

  * label semantics: (T, T+365 days] inclusive on both the 365 boundary
    (label 1) and the 366 boundary (label 0); a same-day successor labels 1;
    a successor in an EXCLUDED window (the 2020-21 gap) still labels the
    earlier row because labels read the full table;
  * entity normalization: punctuated and bare-digit spellings of one entity
    merge into one entity_id (the probe's raw-equality labels would not);
  * prior-history features: counts, windows, gaps, prior mean - computed from
    strictly-earlier autos only, including pre-2005 and gap-window context;
  * population rules: invalid entity keys excluded and counted; the
    right-censoring cutoff (max lavratura - 365d) excludes and counts the tail
    while those rows still serve as label operands;
  * ledger reconciliation, TP_PESSOA cross-check, both classes per window,
    meta/quality consistency (gate-declared counts == written rows).

The ibama-probe-001 lesson: probe-001 failed on a KeyError the local fixture
never exercised. Every rule this build enforces has a row here.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HEADER = ["SEQ_AUTO_INFRACAO", "DES_STATUS_FORMULARIO", "SIT_CANCELADO",
          "TP_PESSOA_INFRATOR", "CPF_CNPJ_INFRATOR", "DAT_HORA_AUTO_INFRACAO",
          "DT_LANCAMENTO", "DT_ULT_ALTERACAO", "ULTIMA_ATUALIZACAO_RELATORIO",
          "SEQ_ACAO_FISCALIZATORIA", "UF", "COD_MUNICIPIO",
          "TP_ORIGEM_REGISTRO_AUTO", "TIPO_AUTO", "TIPO_MULTA",
          "VAL_AUTO_INFRACAO", "GRAVIDADE_INFRACAO", "MOTIVACAO_CONDUTA",
          "TIPO_INFRACAO", "COD_INFRACAO", "DS_BIOMAS_ATINGIDOS", "TIPO_ACAO",
          "OPERACAO", "MUNICIPIO"]


def row(seq, entity, dat_hora, tp_pessoa="", dt_lanc="", dt_ult_alt="",
        valor="", des_status="Lavrado", uf="SP", cod_mun="3530607"):
    return [str(seq), des_status, "N", tp_pessoa, entity, dat_hora, dt_lanc,
            dt_ult_alt, "2026-11-05 01:26:36", "1000", uf, cod_mun, "SICAFI",
            "Multa simples", "", valor, "Leve", "COND-1", "Pesca", "ART-1",
            "Cerrado", "Rotina", "OP-1", "MOGI DAS CRUZES"]


def build_zip(path: Path, extra_unbalanced: bool = False) -> None:
    """Synthetic table. Entity keys:
      A (cpf 123.456.789-09 / 12345678909 variants): 2010-01-01 (date-only),
         2010-06-01, 2011-01-01 (boundary +365 -> labels the first row 1),
         2012-06-15 -> train 4 rows.
      B (cnpj punctuated): 2017-03-05, 2017-09-01 -> eval 2 rows.
      C (cpf): 2019-12-01 with successor 2020-06-01 in the EXCLUDED gap ->
         eval 1 row, label 1 via a gap-window auto.
      G (cpf): same-day pair 2017-04-01 08:00 / 14:00 -> eval 2 rows; the
         earlier labels 1 via its same-day successor.
      D (cnpj): 2022-05-01, 2023-05-01 (397d gap -> label 0), 2024-06-01
         (successor 2025-06-01 exactly +365 -> label 1), 2025-06-01 (past the
         cutoff -> censored, excluded, still labels the 2024 row).
      H (cnpj): 2022-01-01, 2023-01-02 (366d -> label 0) -> holdout 2 rows.
      E: empty entity key (2017) -> excluded, counted.
      F: non-11/14 key 'ABCDEF' (2010) -> excluded, counted.
    Max lavratura 2025-08-01 (added as an extra I row) -> cutoff 2024-08-01.
    """
    members = {
        "auto_infracao_2010.csv": [
            row(1, "12345678909", "2010-01-01", "PF", valor="107,00"),
            row(2, "123.456.789-09", "2010-06-01 00:00:00", "PF",
                valor="1.234,56", dt_ult_alt="2011-02-01 10:00:00"),
            row(3, "12345678909", "2011-01-01", "PF"),
            row(4, "123.456.789-09", "2012-06-15", "PF"),
            row(90, "ABCDEF", "2010-05-05"),
        ],
        "auto_infracao_2017.csv": [
            row(10, "12.345.678/0001-95", "2017-03-05", "PJ", valor="500,00"),
            row(11, "12.345.678/0001-95", "2017-09-01", "PJ"),
            row(12, "", "2017-07-07"),
            row(20, "987.654.321-00", "2017-04-01 08:00:00", "PF"),
            row(21, "98765432100", "2017-04-01 14:00:00", "PF"),
            # balanced publisher label flips: per-row disagreements that the
            # per-year aggregate anchor (the form the record measured) still
            # passes; the build must MEASURE these, not refuse on them
            row(22, "55.555.555/0001-77", "2017-05-05", "PF"),
            row(23, "666.666.666-00", "2017-06-06", "PJ"),
        ] + ([row(24, "77.777.777/0001-11", "2017-08-08", "PF")]
             if extra_unbalanced else []),
        "auto_infracao_2019.csv": [
            row(30, "111.222.333-44", "2019-12-01", "PF"),
        ],
        "auto_infracao_2020.csv": [
            row(31, "11122233344", "2020-06-01", "PF"),
        ],
        "auto_infracao_2022.csv": [
            row(40, "22.222.222/0001-33", "2022-05-01", "PJ"),
            row(50, "33.333.333/0001-11", "2022-01-01", "PJ"),
        ],
        "auto_infracao_2023.csv": [
            row(41, "22222222000133", "2023-05-01", "PJ"),
            row(51, "33333333000111", "2023-01-02", "PJ"),
        ],
        "auto_infracao_2024.csv": [
            row(42, "22.222.222/0001-33", "2024-06-01", "PJ"),
        ],
        "auto_infracao_2025.csv": [
            row(43, "22.222.222/0001-33", "2025-06-01", "PJ"),
            row(99, "44.444.444/0001-00", "2025-08-01", "PJ"),  # vintage edge
        ],
    }
    with zipfile.ZipFile(path, "w") as zf:
        for name, rows in sorted(members.items()):
            buffer = io.StringIO()
            writer = csv.writer(buffer, delimiter=";", quotechar='"',
                               lineterminator="\n")
            writer.writerow(HEADER)
            for item in rows:
                writer.writerow(item)
            zf.writestr(name, buffer.getvalue())


def read_split(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True)
    args = parser.parse_args()
    work = Path(tempfile.mkdtemp(prefix="ibama-fixture-"))  # fresh db every run
    zip_path = work / "auto_infracao_csv.zip"
    build_zip(zip_path)
    out = work / "extract"
    summary_path = work / "summary.json"

    result = subprocess.run(
        [sys.executable, args.build, "--csv", str(zip_path),
         "--out", str(out), "--work-dir", str(work / "db"),
         "--built-at", "2026-01-01T00:00:00Z",
         "--summary-out", str(summary_path)],
        capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise AssertionError("build.py failed on the synthetic zip")
    build_output = json.loads(result.stdout)

    # window counts and both classes
    expect(build_output["windows"]["train"]["n"] == 4, "train must be 4 rows")
    expect(build_output["windows"]["train"]["pos"] == 2, "train positives 2")
    expect(build_output["windows"]["eval"]["n"] == 7, "eval must be 7 rows")
    expect(build_output["windows"]["eval"]["pos"] == 3, "eval positives 3")
    expect(build_output["windows"]["holdout"]["n"] == 5, "holdout 5 rows")
    expect(build_output["windows"]["holdout"]["pos"] == 2, "holdout positives 2")
    expect(build_output["censor_cutoff"] == "2024-08-01 23:59:59",
           "cutoff = max lavratura (2025-08-01) minus 365 days")

    train = read_split(out / "public" / "train.csv")
    evald = read_split(out / "public" / "eval.csv")
    hold = read_split(out / "private" / "holdout.csv")

    # entity A: punctuated/bare variants merged into ONE entity_id
    a_rows = [r for r in train if r["entity_kind"] == "cpf"]
    expect(len(a_rows) == 4, "entity A (+ E/F excluded) train cpf rows")
    expect(len({r["entity_id"] for r in a_rows}) == 1,
           "punctuated and bare spellings must merge to one entity_id")
    by_date = {r["lavratura_date"]: r for r in a_rows}
    a1, a2, a3, a4 = (by_date["2010-01-01"], by_date["2010-06-01"],
                      by_date["2011-01-01"], by_date["2012-06-15"])
    expect(a1["n_prior_autos"] == "0" and a1["days_since_prev_auto"] == "-1",
           "first-ever row has no prior history")
    expect(a1["reautuacao_12m"] == "1", "2010-01-01 labeled by 2010-06-01")
    expect(a2["n_prior_autos"] == "1" and a2["n_prior_autos_365d"] == "1",
            "second row counts the merged first row as prior")
    expect(a2["days_since_prev_auto"] == "151", "gap 151 days")
    expect(a2["prior_value_mean"] == "107.0", "prior mean over merged priors")
    expect(a2["reautuacao_12m"] == "1", "2010-06-01 labeled by 2011-01-01")
    expect(a3["reautuacao_12m"] == "0",
           "2011-01-01 -> next auto 2012-06-15 is 531 days: boundary exclusion")
    expect(a3["n_prior_autos_365d"] == "2",
           "both priors within 365 days of 2011-01-01")
    expect(a4["reautuacao_12m"] == "0", "last row of the entity")
    expect(a4["n_prior_autos"] == "3", "all earlier autos counted")
    # Brazilian decimal parsing
    expect(a2["valor_auto"] == "1234.56" and a2["valor_auto_missing"] == "0",
           "decimal-comma value parsed")
    expect(a3["valor_auto_missing"] == "1", "empty value flagged missing")
    # post-lavratura alteration is measured, never shipped
    expect(a2.get("dt_ult_alt", "absent") == "absent",
           "no post-hoc column may ship")

    # entity B (cnpj eval pair)
    b_rows = {r["lavratura_date"]: r for r in evald
              if r["entity_kind"] == "cnpj" and r["uf"] == "SP"}
    expect(b_rows["2017-03-05"]["reautuacao_12m"] == "1",
           "B labeled by its 2017-09-01 successor")
    expect(b_rows["2017-09-01"]["reautuacao_12m"] == "0", "B last row")
    # entity C: successor in the EXCLUDED 2020-21 gap still labels
    c_rows = [r for r in evald if r["lavratura_date"] == "2019-12-01"]
    expect(len(c_rows) == 1 and c_rows[0]["reautuacao_12m"] == "1",
           "gap-window successor labels the 2019 row (full-table labeling)")
    # entity G: same-day successor
    g = [r for r in evald if r["lavratura_date"] == "2017-04-01"]
    expect(len(g) == 2, "same-day pair kept as two rows")
    earlier = [r for r in g if r["n_prior_autos"] == "0"][0]
    later = [r for r in g if r["n_prior_autos"] == "1"][0]
    expect(earlier["reautuacao_12m"] == "1",
           "same-day later auto labels the earlier row")
    expect(later["n_prior_autos"] == "1",
           "the same-day earlier auto is a prior of the later row")

    # entity D + H (holdout): +365 boundary in, +366 out, censored operand
    d = {r["lavratura_date"]: r for r in hold}
    expect(d["2022-05-01"]["reautuacao_12m"] == "1",
           "2022-05-01 labeled by 2023-05-01 (365d, inclusive)")
    expect(d["2023-05-01"]["reautuacao_12m"] == "0",
           "2023-05-01 -> 2024-06-01 is 397 days")
    expect(d["2024-06-01"]["reautuacao_12m"] == "1",
           "2024-06-01 labeled by the CENSORED 2025-06-01 row (exactly +365)")
    expect(d["2022-01-01"]["reautuacao_12m"] == "0",
           "2022-01-01 -> 2023-01-02 is 366 days: boundary exclusion")
    expect("2025-06-01" not in {r["lavratura_date"] for r in hold},
           "the censored tail row must not be scored")
    expect("2025-08-01" not in {r["lavratura_date"] for r in hold},
           "the vintage-edge row is past the cutoff and not scored")

    # exclusion ledger
    summary = json.loads(summary_path.read_text())
    buckets = summary["exclusion_buckets"]
    expect(buckets["invalid_entity_excluded"] == 1,
           "the non-11/14 entity row excluded (the empty-entity row leaves no "
           "entity to join and is counted in rows.empty_entity instead)")
    expect(summary["rows"]["empty_entity"] == 1, "empty-entity row accounted")
    expect(buckets["censored_excluded"] == 2,
           "2025-06-01 and 2025-08-01 rows censored out")
    expect(buckets["gap_2020_2021_context"] == 1, "the 2020 gap row")
    expect(summary["rows"]["dedup"] == 21, "21 synthetic rows")
    expect(summary["crosschecks"]["label_sql_vs_twopoint_mismatches"] == 0,
           "SQL cross-check agrees with the two-pointer labels")
    expect(summary["crosschecks"]["tp_pessoa_aggregate_mismatches"] == 0,
           "TP_PESSOA per-year aggregate anchor holds")
    expect(summary["crosschecks"]["tp_pessoa_perrow_disagreements"] == 2,
           "the two balanced label flips are measured, not fatal")
    expect(len(summary["crosschecks"]["tp_pessoa_perrow_samples"]) == 2,
           "both flips sampled for the record")

    # meta/quality consistency with the written files
    meta = json.loads((out / "meta.json").read_text())
    quality = json.loads((out / "quality.json").read_text())
    expect(meta["rows"] == {"train": 4, "eval": 7, "holdout": 5},
           "meta rows match the written files")
    for name, n in meta["rows"].items():
        rel = quality["splits"][name]
        rows = read_split(out / rel)
        expect(len(rows) == n, f"{name} file row count")
        pos = sum(1 for r in rows if r["reautuacao_12m"] == "1")
        expect(quality["positive_events"][name]["positives"] == pos,
               "declared positives match the rows")
        expect(quality["positive_events"][name]["distinct_events"] ==
               len({r["entity_id"][:10] for r in rows
                    if r["reautuacao_12m"] == "1"}),
               "declared clustered events match the gate's [:10] rule")
    expect(quality["evaluation_contract"]["access"] == "isolated_rows",
           "restricted protocol declared")
    expect(quality["evaluation_contract"]["use"] == "retrospective_research",
           "retrospective scope declared")
    expect(quality["evaluation_contract"]["training_label_timing"] == "unverified",
           "label timing stays unverified")
    probe_names = [p["name"] for p in
                   quality["evaluation_contract"]["cross_row_audit"]["probes"]]
    expect(probe_names == ["next_auto_gap_recovery", "prior_count_growth_365d"],
           "the two declared reverse-history probes")
    expect(str(quality["split_windows"]["holdout"]["end"]) == "2024-08-02",
           "holdout window end = cutoff + 1 day")

    # no performance metric may exist anywhere in the build outputs
    for payload in (summary, quality):
        text = json.dumps(payload)
        for bad in ('"auc"', "accuracy", "brier"):
            expect(bad not in text.lower(),
                   f"construction output must not carry a performance metric: {bad}")

    # negative scenario: one UNBALANCED flip breaks the per-year aggregate
    # anchor and the build must refuse loudly (the red side of the guard)
    bad_zip = work / "auto_infracao_csv_bad.zip"
    build_zip(bad_zip, extra_unbalanced=True)
    bad = subprocess.run(
        [sys.executable, args.build, "--csv", str(bad_zip),
         "--out", str(work / "extract-bad"), "--work-dir", str(work / "db-bad"),
         "--built-at", "2026-01-01T00:00:00Z",
         "--summary-out", str(work / "summary-bad.json")],
        capture_output=True, text=True)
    expect(bad.returncode != 0, "an unbalanced TP flip must fail the build")
    expect("aggregate anchor BROKEN" in bad.stderr + bad.stdout,
           "the refusal must name the aggregate anchor")

    print("FIXTURE PASSED: labels, boundaries, normalization, censoring, "
          "ledger, TP cross-check, meta/quality consistency all verified on "
          "the synthetic zip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
