#!/usr/bin/env python3
"""Retained fixture test for probe_aggregate.py (validated 2026-11-04; extended after
the ibama-probe-001 failure with the no-parseable-lavratura row that produced the
SQL none-year bucket KeyError on real data): builds a tiny synthetic ibama-like zip
(same header, per-year members, duplicates, missing entities, odd date formats, an
eff-null row), runs the probe against it via a file:// URL override, and asserts the
dedupe, mismatch-flag, label, censoring, fallback, member-skip and none-bucket
semantics. Run:
    python3 candidates/ibama-auto-infracao-recidivism/probe/test_fixture.py"""
import csv
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import os
SCRATCH = Path(os.environ.get("TMPDIR", "/tmp")) / "ibama_probe_fixture"
SCRATCH.mkdir(parents=True, exist_ok=True)

HEADER = ("SEQ_AUTO_INFRACAO;DES_STATUS_FORMULARIO;DS_SIT_AUTO_AIE;SIT_CANCELADO;"
          "NUM_AUTO_INFRACAO;SER_AUTO_INFRACAO;CD_ORIGINAL_AUTO_INFRACAO;TIPO_AUTO;"
          "TIPO_MULTA;VAL_AUTO_INFRACAO;FUNDAMENTACAO_MULTA;PATRIMONIO_APURACAO;"
          "GRAVIDADE_INFRACAO;CD_NIVEL_GRAVIDADE;MOTIVACAO_CONDUTA;EFEITO_MEIO_AMBIENTE;"
          "EFEITO_SAUDE_PUBLICA;PASSIVEL_RECUPERACAO;UNID_ARRECADACAO;DES_AUTO_INFRACAO;"
          "DAT_HORA_AUTO_INFRACAO;FORMA_ENTREGA;DAT_CIENCIA_AUTUACAO;DT_FATO_INFRACIONAL;"
          "DT_INICIO_ATO_INEQUIVOCO;DT_FIM_ATO_INEQUIVOCO;DS_UNID_CONCILIACAO;COD_MUNICIPIO;"
          "MUNICIPIO;UF;NUM_PROCESSO;NU_PROCESSO_FORMATADO;COD_INFRACAO;DES_INFRACAO;"
          "TIPO_INFRACAO;CD_RECEITA_AUTO_INFRACAO;DES_RECEITA;TP_PESSOA_INFRATOR;"
          "NUM_PESSOA_INFRATOR;NOME_INFRATOR;CPF_CNPJ_INFRATOR;QT_AREA;INFRACAO_AREA;"
          "DES_OUTROS_TIPO_AREA;CLASSIFICACAO_AREA;DS_FATOR_AJUSTE;NUM_LONGITUDE_AUTO;"
          "NUM_LATITUDE_AUTO;DS_WKT;DES_LOCAL_INFRACAO;DS_REFERENCIA_ACAO_FISCALIZATORIA;"
          "UNIDADE_CONSERVACAO;ID_SICAFI_BIOMAS_ATINGIDOS_INFRACAO;DS_BIOMAS_ATINGIDOS;"
          "SEQ_NOTIFICACAO;SEQ_ACAO_FISCALIZATORIA;CD_ACAO_FISCALIZATORIA;UNID_CONTROLE;"
          "TIPO_ACAO;OPERACAO;DENUNCIA_SISLIV;SEQ_ORDEM_FISCALIZACAO;ORDEM_FISCALIZACAO;"
          "UNID_ORDENADORA;SEQ_SOLICITACAO_RECURSO;SOLICITACAO_RECURSO;OPERACAO_SOL_RECURSO;"
          "DT_LANCAMENTO;TP_ULT_ALTERACAO;DT_ULT_ALTERACAO;JUSTIFICATIVA_ALTERACAO;"
          "WKT_GE_AREA_AUTUADA;DT_ULT_ALTER_GEOM;TP_ORIGEM_GE_AREA_AUTUADA;"
          "DS_ERRO_GE_AREA_AUTUADA;DS_WKT_GE_AREA_AUTUADA_COM_ERRO;ST_AUTO_MIGRADO_AIE;"
          "DS_ENQUADRAMENTO_ADMINISTRATIVO;DS_ENQUADRAMENTO_NAO_ADMINISTRATIVO;"
          "DS_ENQUADRAMENTO_COMPLEMENTAR;CD_TERMOS_APREENSAO;CD_TERMOS_EMBARGOS;"
          "TP_ORIGEM_REGISTRO_AUTO;ULTIMA_ATUALIZACAO_RELATORIO")
NC = len(HEADER.split(";"))

def row(seq, entity, dat_hora, dt_lanc="", sit="N", des="Lavrado", acao="A1",
        uf="SP", mun="3550308", tp_origem="SICAFI", tp_pessoa="F"):
    vals = [""] * NC
    for k, v in (("SEQ_AUTO_INFRACAO", seq), ("DES_STATUS_FORMULARIO", des),
                 ("SIT_CANCELADO", sit), ("TP_PESSOA_INFRATOR", tp_pessoa),
                 ("CPF_CNPJ_INFRATOR", entity), ("DAT_HORA_AUTO_INFRACAO", dat_hora),
                 ("DT_LANCAMENTO", dt_lanc), ("SEQ_ACAO_FISCALIZATORIA", acao),
                 ("UF", uf), ("COD_MUNICIPIO", mun), ("TP_ORIGEM_REGISTRO_AUTO", tp_origem),
                 ("TP_ULT_ALTERACAO", "Alterado" if seq % 2 else ""),
                 ("DT_ULT_ALTERACAO", "2026-10-01 10:00:00" if seq % 2 else ""),
                 ("ULTIMA_ATUALIZACAO_RELATORIO", "2026-11-03 01:28:15")):
        vals[HEADER.split(";").index(k)] = str(v)
    return ";".join(vals)

zip_path = SCRATCH / "fixture.zip"
with zipfile.ZipFile(zip_path, "w") as zf:
    rows_2013 = "\n".join([
        row(1, "12345678000199", "2013-03-15 10:00:00"),          # A first, later auto within 365d -> pos
        row(2, "12345678000199", "2013-09-20 09:00:00"),          # A again -> pos (next 2015-01 beyond 365d? no)
        row(3, "12345678000199", "2015-01-05 09:00:00"),          # A, prior 2013-09-20 is >365d -> neg
        row(4, "11111111111", "2013-05-05 00:00:00"),             # B cpf single -> neg
        row(5, "", "2013-06-06 00:00:00"),                          # missing entity
        row(6, "12.345.678/0001-99", "2013-07-07 00:00:00"),        # punctuated CNPJ = distinct entity from A!
        row(7, "99999999999", "", dt_lanc="2013-08-08 00:00:00"),  # dat_hora empty -> eff from dt_lanc
        row(8, "88888888888", "08/08/2013"),                        # odd format -> python fallback
    ])
    zf.writestr("auto_infracao_2013.csv", HEADER + "\n" + rows_2013 + "\n")
    # duplicate seq with DIFFERENT entity -> mismatch flag path
    rows_2023 = "\n".join([
        row(9, "22222222222222", "2023-02-02 08:00:00", acao="A9", uf="MG", mun="3129707"),
        row(9, "33333333333333", "2023-02-02 08:00:00", acao="A9", uf="MG", mun="3129707"),
        row(10, "22222222222222", "2023-11-11 08:00:00", acao="A9", uf="MG", mun="3129707"),  # within 365d of feb -> pos
        row(11, "44444444444444", "2024-01-15 08:00:00", acao="A10"),  # holdout-era
        row(12, "55555555555", "", dt_lanc=""),  # NO parseable lavratura -> SQL 'none' year bucket
    ])
    zf.writestr("auto_infracao_2023.csv", HEADER + "\n" + rows_2023 + "\n")
    # a member missing required columns -> must be skipped, not fatal
    zf.writestr("README.txt", "not a csv\n")
    zf.writestr("outra_coisa.csv", "FOO;BAR\n1;2\n")

sys.path.insert(0, str(SCRATCH))
spec = importlib.util.spec_from_file_location(
    "probe_aggregate", "/opt/data/dataset-factory/candidates/ibama-auto-infracao-recidivism/probe/probe_aggregate.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.URL = zip_path.as_uri()

out = SCRATCH / "out"
mod.main.__wrapped__ = None
import argparse
old_argv = sys.argv
sys.argv = ["probe_aggregate.py", "--out", str(out), "--work-dir", str(SCRATCH / "work")]
try:
    mod.main()
finally:
    sys.argv = old_argv

summary = json.loads((out / "summary.json").read_text())
report = json.loads((out / "probe_report.json").read_text())
print("\n=== SUMMARY ===")
print(json.dumps({k: v for k, v in summary.items() if k != "per_year_scored"}, indent=1))
print("per_year_scored:", json.dumps(summary["per_year_scored"], indent=1))
print("\nwindows.csv:")
print((out / "windows.csv").read_text())
print("per_year.csv:")
print((out / "per_year.csv").read_text())
print("members:")
print((out / "members.csv").read_text())

# assertions (verified by hand against the fixture semantics)
assert summary["zip_members"] == 4, summary["zip_members"]
assert summary["rows_dedup"] == 12, summary["rows_dedup"]       # seqs 1..12, dup 9 merged
assert summary["rows_raw"] == 13, summary["rows_raw"]           # 13 raw rows
assert summary["dup_extra_rows"] == 1
assert summary["dup_mismatches"]["dup_entity_mismatch"] == 1
assert summary["dup_mismatches"]["dup_date_mismatch"] == 0
assert summary["entity_kind_overall"] == {"cnpj": 7, "cpf": 4, "missing": 1}
assert report["entity_rows_with_punctuation"] == 1
w = summary["windows"]
train = w["train_2005_2015"]
assert train["n"] == 7, train   # 2013 seqs 1,2,4,6,7,8 + 2015 seq3 (all valid-entity, uncensored)
assert train["pos"] == 1, train # only seq1 (seq2->seq3 is 472 days, so seq2 label 0)
assert train["ent_pos"] == 1 and train["ent_all"] == 5, train
assert train["acao_pos"] == 1 and train["month_pos"] == 1, train
hold = w["holdout_2022_2025"]
# 2023/2024 rows all fall inside the censor window (max_eff 2024-01-15 -> cutoff 2023-01-15):
# scored 0, naive carries the labels.
assert hold["n"] == 0, hold
y = summary["per_year_scored"]
assert y["2013"]["n"] == 6 and y["2013"]["pos"] == 1, y["2013"]
assert y["2013"]["base_rate"] == round(1 / 6, 4), y["2013"]
assert y["2023"]["n"] == 0 and y["2023"]["pos"] == 0, y["2023"]
assert report["per_year"]["2023"]["naive_n"] == 2, report["per_year"]["2023"]
assert report["per_year"]["2023"]["naive_pos"] == 1, report["per_year"]["2023"]
# odd-format row 8 must have been rescued by the fallback with eff 2013-08-08
assert report.get("eff_python_fallback_fixed", 0) == 1, report.get("eff_python_fallback_fixed")
assert report["datetime_format_probe"]["dat_hora"].get("other", 0) == 1
assert report["per_year"]["2013"]["dt_lanc_only_rows"] == 1
# the no-parseable-lavratura row lands in the SQL 'none' year bucket and must not crash
# the summary (the ibama-probe-001 failure mode), nor leak into scored populations
assert summary["per_year_scored"]["none"] == {"n": None, "pos": None, "base_rate": None}
assert report["per_year"]["none"]["rows"] == 1
assert report["per_year"]["none"]["eff_null"] == 1
skipped = [m["member"] for m in report["members"] if m["status"].startswith("skipped")]
assert skipped == ["README.txt", "outra_coisa.csv"], skipped
assert summary["export_stamps_top10"] == {"2026-11-03 01:28:15": 12}
print("\nALL FIXTURE ASSERTIONS PASSED")
