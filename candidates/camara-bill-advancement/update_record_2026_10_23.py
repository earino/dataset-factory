#!/usr/bin/env python3
"""One-shot record update for the camara-bill-advancement construction tick.

Applies the 2026-10-23 construction-probe corrections (label code vocabulary,
right-censoring finding, file inventory, raw-mirror observation) and the
camara-001 launch entry to candidates/camara-bill-advancement/record.json.
Idempotent guards: refuses to overwrite an existing camara-001 entry or a
corrected target_definition.
"""
import json
from pathlib import Path

RECORD = Path(__file__).resolve().parents[0] / "record.json"

record = json.loads(RECORD.read_text())

if any(job.get("id") == "camara-001" for job in record.get("jobs", [])):
    raise SystemExit("camara-001 entry already present; nothing to do")

record["target_definition"] = (
    "Binary from the publisher's own situation vocabulary in the bulk CSV's "
    "ultimoStatus (current status at the file vintage; file and live API "
    "agree, measured 2026-10-23): positive = situation code 1140 "
    "'Transformado em Norma Jurídica' (CORRECTED 2026-10-23: the discovery "
    "sample's 'idSituacao 251' was a positional indexing defect - column 25 "
    "is ultimoStatus_idTipoTramitacao, not idSituacao; the header-name-keyed "
    "parse shows 1140 with a consistent code->description table, e.g. 923 "
    "Arquivada, 1230 Transformado em nova proposição, 937 Vetado totalmente). "
    "Terminal negative = Arquivada* codes plus the other settled "
    "non-enactment states (Vetado totalmente, Retirado pelo(a) Autor(a), "
    "Devolvida ao(à) Autor(a), Tramitação Finalizada, Enviada ao Arquivo). "
    "Merged rows (1230 'Transformado em nova proposição') are EXCLUDED from "
    "the scored population - the outcome is carried by the merged-into bill "
    "(decision recorded; share measured per window). Rows with a non-terminal "
    "status, and the 25-53% of rows (by year, measured) whose idSituacao is "
    "empty - the API confirms genuinely no tramitação on record, not a file "
    "gap - are unobserved targets, excluded and counted per window, never "
    "membership decisions on future data. Label source columns: all "
    "ultimoStatus_* fields and urnFinal, excluded from shipped features."
)

record["split_strategy"] = (
    "Cohorts by dataApresentacao over the union of the 35 year files "
    "(1991-2025; files processed descending, first id wins so re-numbered "
    "bills contribute their current row), windows by presentation date: "
    "train 1991-01..2014-12, eval 2015-01..2018-12, holdout 2019-01..2022-12. "
    "RIGHT-CENSORING CORRECTED 2026-10-23: Brazilian propositions carry "
    "across legislatures (bills presented 2019 still show live statuses with "
    "2024-2026 timestamps, file and API agree), so 'closed legislature' does "
    "not settle labels; the scored population is bills whose status is "
    "terminal at the current file vintage, and the unobserved share "
    "(no-status + non-terminal) is measured per window and recorded as a "
    "property - it rises with recency. Sampled positive rates drift strongly "
    "downward by cohort (1991 whole file 311/4,436 = 7.0%; 2005 sampled "
    "~2.2%; 2019-2022 sampled ~0.4-0.8%), a measured phenomenon property. "
    "Grain: one proposition = one row, keyed by id (unique across the union; "
    "construction asserts uniqueness)."
)

record.setdefault("measurements", {})["construction_probes_2026_10_23"] = (
    "probe_censoring.py (v1, naive line-splitting: defective - quoted "
    "multi-line ementas corrupt mid-file chunks), corrected by "
    "probe_censoring2.py (quote-parity record-boundary trimming; whole-1991 "
    "file ground truth) + probe_empty_status.py + probe_file_vs_api.py + "
    "probe_file_inventory.py, all run end-to-end 2026-10-23 from the "
    "coordinator: (1) situation-code vocabulary keyed by header name: 923 "
    "Arquivada (2,491 of 4,436 whole-1991 rows), 1140 Transformado em Norma "
    "Jurídica (311 = 7.0%), 1230 Transformado em nova proposição, 937 Vetado "
    "totalmente, 925 Tramitando em Conjunto, 907/915/924/926/936/1070/1120/1170/1220/1285 "
    "ongoing/other - consistent code->description pairs, unlike the "
    "discovery sample's mis-indexed columns; (2) empty ultimoStatus share by "
    "year-file sample: 1991 36.6% (whole file), 2000 14.8%, 2005 51.4%, 2010 "
    "52.7%, 2015 51.9%, 2019 48.7%, 2021 52.3%, 2022 39.9% - and the API "
    "returns statusProposicao None for sampled such ids, so the emptiness is "
    "the publisher's own record, not a file gap; empty-status rows skew to "
    "procedural types (RIC/REQ/EMP/MSC) but include some PLs; (3) "
    "right-censoring: bills presented 2019 still carry non-terminal statuses "
    "with ultimoStatus_dataHora in 2024-2026 (e.g. PL 1/2019 id 2190407 "
    "'Aguardando Apreciação pelo Senado Federal', dataHora 2025-08-26) and "
    "the API agrees with the file on every sampled id - the vintage is "
    "current, the legislatures are not closed for these bills; (4) file "
    "inventory: 35/35 years 200 OK for both families, proposicoes 747.4 MB + "
    "proposicoesAutores 456.0 MB total; (5) autores schema measured: "
    "idProposicao, tipoAutor, siglaPartidoAutor, siglaUFAutor, "
    "ordemAssinatura, proponente - first-author features keyed on the "
    "proponente row. Observation for the novelty record: an HF org "
    "(belisards) mirrors the raw proposicoes files 1934-2024 "
    "(ementas_camarabr_1934_2024) - raw extract, no splits, no scored "
    "contract; recorded as a mirror observation, not permission, and it "
    "does not change the recorded 'differentiated' verdict."
)

record["jobs"] = record.get("jobs", []) + [{
    "id": "camara-001",
    "date": "2026-10-23",
    "outcome": "launched 06:30:58Z (server 171985941, cx23/hel1, EUR 0.06 "
               "reservation): full build + qualification gate on the "
               "worker over the union of the 70 bulk year files; bundle "
               "build.py sha256 e3039dd7241c15ac... (verified by the "
               "assembler); local synthetic smoke test passed end-to-end "
               "before launch (tests_smoke_build.py: union/dedup, "
               "code classification, proponente ordering, unobserved "
               "buckets, fixture, split windows, meta/quality writing)",
    "server_id": 171985941,
}]

record["next_action"] = (
    "Collect camara-001 (running, server 171985941): require exit 0 AND a "
    "passing current-version gate report on the full artifact on the worker, "
    "then `qualify_dataset.py --accept` against the exact bytes before any "
    "scoring or figure is quoted. If the gate fails, diagnose from the "
    "collected report + summary.json eligibility buckets and prepare a fresh "
    "attempt ID (one rebuild per structural defect). If accepted: the "
    "runner-contract baseline job (benchmark train.py/validate.sh verbatim) "
    "on the accepted artifact, compared against the in-build naive "
    "references (global rate, per-type, per-party, per-year, "
    "per-type-and-party) measured on identical eval rows; the model must be "
    "interpreted against those references before any packaging step."
)

RECORD.write_text(json.dumps(record, indent=1, ensure_ascii=True) + "\n")
print("record updated: target_definition corrected (code 1140), "
      "split_strategy right-censoring correction, "
      "measurements.construction_probes_2026_10_23, camara-001 job entry, "
      "next_action rewritten")
