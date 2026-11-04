#!/usr/bin/env python3
"""Fill the ibama-auto-infracao-recidivism record with the 2026-11-04 worker-probe
evidence and promote it to ready. Run once from the repo root:
    python3 candidates/ibama-auto-infracao-recidivism/probe/fill_record_2026_11_04.py
Every number below is measured by ibama-probe-002 (staging release 433491900) or the
coordinator-side cross-check (probe/out/multas_per_year.json, multas_distinct_per_year.json,
crosscheck_per_year.json); nothing is estimated."""
import json
from pathlib import Path

REC = Path("candidates/ibama-auto-infracao-recidivism/record.json")
r = json.loads(REC.read_text())

r["status"] = "ready"
r["verdict"] = "go"

r["prediction_time"] = (
    r["prediction_time"]
    + " MEASURED 2026-11-04 (worker probe ibama-probe-002, full current vintage, "
    "705,667 rows): DAT_HORA_AUTO_INFRACAO is non-empty on 705,667/705,667 rows "
    "(91,632 date-only 'YYYY-MM-DD' concentrated in the pre-AIe eras + 614,035 full "
    "'YYYY-MM-DD HH:MM:SS'), so the lavratura instant is directly the published column "
    "on every row; the DT_LANCAMENTO fallback was never needed (0 rows fell back; "
    "DT_LANCAMENTO itself is empty on 479 rows); 0 unparseable dates. Every row carries "
    "the same export stamp 2026-11-03 01:28:15, i.e. the zip is one full daily "
    "re-export (current-vintage only). Revision churn measured from DT_ULT_ALTERACAO: "
    "rows altered within the 12 months before the export stamp are <=1.2% for every "
    "lavratura year <=2024, 30.5% for 2025 and 100% for 2026 - the current-vintage "
    "limitation is concentrated in the most recent ~18 months, matching the censoring "
    "design; the evaluation contract must state the retrospective/current-vintage "
    "as-of policy (datasus-sinasc precedent). Timestamps carry no timezone; treated as "
    "publisher-local (America/Sao_Paulo)."
)

r["target_definition"] = (
    r["target_definition"]
    + " MEASURED 2026-11-04: label computed on raw CPF_CNPJ_INFRATOR equality - entities "
    "are stored in canonical punctuated form (672,780/672,793 non-empty rows carry "
    "./- punctuation; digit-normalized length is 11 for 453,978 cpf rows (64.4%) and 14 "
    "for 218,797 cnpj rows (31.0%); 32,874 missing (4.7%, concentrated pre-1995), 18 "
    "other) - so construction MUST normalize to bare digits before joining and hashing; "
    "the probe's raw-equality rates are the measured baseline. Publisher cross-check of "
    "the entity classification: TP_PESSOA_INFRATOR matches the digit-based split exactly "
    "(2023: PF 9,929 = cpf11 9,929; PJ 6,376 = cnpj14 6,376). Right-censoring measured "
    "at the extract's max lavratura 2026-10-30: 2,347 rows of 2025 and all 10,562 rows "
    "of 2026 fall inside the unobserved 365-day window. Status-mix design input: 2023 "
    "carries Lavrado 16,250 (99.0%), Cancelado 146, Excluido 10, Substituido por outro 3; "
    "SIT_CANCELADO='S' is ~1%/yr - construction must state which side of the population "
    "these rows fall on."
)

r["split_strategy"] = (
    "Entity-instant panel over all autos in the current vintage (1977-09-03.."
    "2026-10-30 measured): one row per (entity, auto) with prior-history features "
    "strictly earlier than the lavratura instant. MEASURED 2026-11-04 on the full "
    "current table (ibama-probe-002, zip sha256 4db188142b03a598d839f5331d3c148aeb7718fd"
    "6a657f324d8e98b959621771, 123,308,204 bytes, export stamp 2026-11-03 01:28:15; "
    "705,667 rows, 0 duplicate SEQ in this export - the publisher's multiplicity "
    "warning did not materialize in the 2026-11-03 csv): windows on lavratura year, "
    "valid-entity, right-censored at 2025-10-30 23:59:59 - train 2005-2015: 251,614 "
    "rows / 44,805 positives (17.81%), 23,430 distinct positive entities, 6,149 "
    "distinct SEQ_ACAO_FISCALIZATORIA, 132 distinct (year,month), 27 UFs; eval "
    "2016-2019: 65,725 / 18,216 (27.72%), 8,573 / 13,624 / 48 / 27; holdout "
    "2022-2025: 52,741 / 14,995 (28.43%), 7,241 / 14,800 / 46 / 27. Context buckets: "
    "pre-2005 271,385 / 36,122 (13.31%, 16,340 distinct positive entities, SEQ_ACAO "
    "empty in this era); gap 2020-2021 excluded (18,419 / 4,861, 26.39%); 2026 excluded "
    "(10,562 rows, all censored). First-time vs repeat measured per year (2023: "
    "first-time 8,449 n / 1,524 pos = 18.0%; repeat 7,856 n / 3,878 pos = 49.4%); "
    "distinct entities overall 439,781 with autos-per-entity bins 1:335,785, 2:62,530, "
    "3-5:32,272, 6-20:8,613, 21+:581. Base-rate drift across windows (17.8% -> 27.7% "
    "-> 28.4%) is a measured phenomenon property (era + enforcement regime). Clustering "
    "for the gate's enough_clustered_positives check: positives cluster by entity "
    "(serial infringers) and by fiscalizacao action (SEQ_ACAO_FISCALIZATORIA) - "
    "thousands of distinct clusters per window, so the camara-style year-cluster "
    "failure cannot occur; entity (or entity+action) is the natural event key."
)

r["measurements"]["worker_probe_2026_11_04"] = (
    "ibama-probe-002 (cx23/hel1, succeeded, 64.6 s; ibama-probe-001 failed at 61.1 s "
    "on a diagnosed code defect and measured nothing): full-table aggregate pass over "
    "auto_infracao_csv.zip - 48 per-year members auto_infracao_1977..2026.csv, 705,667 "
    "rows, 0 duplicate SEQ, coverage 1977-09-03..2026-10-30, one export stamp "
    "2026-11-03 01:28:15 on all rows. Entity keys: cpf 453,978 / cnpj 218,797 / missing "
    "32,874 / other 18; TP_PESSOA_INFRATOR cross-check exact; canonical punctuated "
    "storage on 672,780/672,793 non-empty rows. Regime mix (TP_ORIGEM_REGISTRO_AUTO): "
    "SICAFI 100% through 2018, mixed 2019 (SICAFI 12,521 / AI-e 1,922), AI-e dominant "
    "2020+ with a small late-recorded SICAFI tail (110-188/yr 2023-2026). Window and "
    "clustered counts: see split_strategy. PUBLISHER-SUMMARY CROSS-CHECK (record "
    "next_action step 2): the 'Multas Ambientais Distribuidas por Bens Tutelados' "
    "product (24,655,019-byte csv zip, sha256 aa3173ce48a80694437a4ea98c3eeae644a2246f5"
    "07a12f15c57a9a39e6ddfca, 27 UF files, 725,081 rows, Tipo Auto mix Multa 719,326 / "
    "Advertencia 5,317 / Multa Diaria 438) is NOT an aggregate count table but a second "
    "per-auto listing; at distinct-N-AI grain per Data Auto year it tracks the main "
    "table within ratio 1.02-1.20 for 1977-2019 (probe higher: advertencia autos are in "
    "the main table but not in the multas product) and 0.82-0.90 for 2020-2026 (the "
    "multas product carries 11-18% MORE distinct autos than the main table in the AIe "
    "era; unexplained - hypothesis, unverified: different date semantics or inclusion "
    "of voided app-era forms). CONSTRUCTION DESIGN INPUT: define the population from "
    "the main table alone and never mix products; the discrepancy is recorded, not "
    "resolved. The 'Diagnostico de Delitos Ambientais' annual PDFs were not re-fetched; "
    "the multas product served as the publisher-summary cross-check. PROBE DEFECTS "
    "RECORDED (cosmetic, aggregate-level only): the windows.json 'censored_excluded' "
    "column is always 0 because the window dict never increments it (per-year "
    "censored_n is correct: 2,347 for 2025, 10,562 for 2026); pre-2005 acao_pos is 0 "
    "because SEQ_ACAO_FISCALIZATORIA is empty in that era (rows_without_seq_acao "
    "525,203 overall). Raw outputs retained in probe/out/: summary.json, "
    "probe_report.json, per_year.json, windows.json, members.json, multas_per_year.json, "
    "multas_distinct_per_year.json, crosscheck_per_year.json, probe_002_container.txt."
)
r["measurements"]["extraction_cost_worker_measured"] = (
    "Worker-side, measured 2026-11-04 (cx23/hel1, 2 vCPU/4 GB, provider rate 0.01152 "
    "EUR/h): download 123,308,204 bytes in 26.1 s, sqlite load of 705,667 rows 14.7 s, "
    "label pass 4.8 s, whole job 64.6 s. Reservations EUR 0.04 per job (two probe jobs "
    "this tick; November ledger total with cqc-chd-001 = EUR 0.12 of the EUR 20 "
    "allowance); actual compute cost ~EUR 0.002 for both workers combined. Bulk data "
    "never touched the coordinator: the only coordinator fetches were bounded (256 KB "
    "Range header probe; the 24.7 MB aggregate multas cross-check zip)."
)
r["measurements"]["measured_on"] = (
    r["measurements"]["measured_on"]
    + " Worker aggregate probe 2026-11-04 (ibama-probe-002); commands and raw outputs in probe/ and probe/out/."
)

r["jobs"] = [
    {
        "id": "ibama-probe-001",
        "kind": "discovery aggregate probe",
        "launched_by": "scheduled discovery tick 2026-11-04 (Latin America focus)",
        "launched_at": "2026-11-04T03:43:38Z (server 174421747, cx23/hel1, reservation EUR 0.04)",
        "collected_at": "2026-11-04T03:47:10Z (staging release 433488550 verified: "
                        "probe_error.json 323 B sha256 f64596658ae9867e7ccb3aa24ab4053086cf5c63"
                        "f81bc600fddaae96fd34fb1d, source.tar 122,880 B, container log, manifest.json)",
        "destroyed_at": "2026-11-04T03:48:12Z (worker destroy command; ledger status deleted)",
        "destroy_verified": "destroy command returned status deleted for server 174421747",
        "result": "failed, exit 1, executor elapsed 61.1 s, oom_killed false",
        "failure_class": "probe code defect (not infrastructure, not scientific): summary "
                         "serialization indexed d['scored_n'] on the SQL per-year 'none' "
                         "bucket (rows with no parseable lavratura date), which the label "
                         "merge never populates - KeyError. Download, member load, dedupe, "
                         "eff normalization and the label pass had all completed; nothing "
                         "scientific was measured and no figure is quotable from this "
                         "attempt. Diagnosed from the preserved probe_error.json traceback; "
                         "the retained fixture test was extended with the none-bucket row "
                         "(green locally) and the one changed retry was executed as "
                         "ibama-probe-002.",
    },
    {
        "id": "ibama-probe-002",
        "kind": "discovery aggregate probe",
        "launched_by": "scheduled discovery tick 2026-11-04 (Latin America focus)",
        "launched_at": "2026-11-04T03:49:37Z (server 174422247, cx23/hel1, reservation EUR 0.04)",
        "collected_at": "2026-11-04T03:53:07Z (staging release 433491900 verified: summary.json "
                        "5,662 B, probe_report.json 54,544 B, per_year.json 5,632-row table, windows.json "
                        "617 B, members.json 2,408 B, container log 669 B, manifest.json; all "
                        "assets sha256-verified by collect and fetched for the record into probe/out/)",
        "destroyed_at": "2026-11-04T03:55:20Z (worker destroy command; ledger status deleted)",
        "destroy_verified": "destroy command returned status deleted for server 174422247",
        "result": "succeeded, exit 0, executor elapsed 64.6 s, oom_killed false; zip sha256 "
                   "4db188142b03a598d839f5331d3c148aeb7718fd6a657f324d8e98b959621771 "
                   "(123,308,204 bytes); full-table measurements recorded in "
                   "measurements.worker_probe_2026_11_04 and split_strategy",
    },
]

r["artifacts"] = [
    {"kind": "probe outputs (source aggregates, not a dataset)",
     "dir": "candidates/ibama-auto-infracao-recidivism/probe/out/",
     "files": ["summary.json", "probe_report.json", "per_year.json", "windows.json",
               "members.json", "multas_per_year.json", "multas_distinct_per_year.json",
               "crosscheck_per_year.json", "probe_002_container.txt"],
     "origin": "ibama-probe-002 staging release 433491900 (collect-verified) plus the "
               "coordinator-side multas cross-check (zip sha256 aa3173ce48a80694437a4ea9"
               "8c3eeae644a2246f507a12f15c57a9a39e6ddfca)"},
]

r["review"] = (
    "Five contracts, reconciled against written evidence (worker probe ibama-probe-002, "
    "full current vintage, 2026-11-04): (1) Redistribution SUPPORTED - class A per "
    "Decreto 8.777/2016 art. 2 III / art. 4 as amended by Decreto 9.903/2019 (permissive "
    "instruments quoted 2026-10-30 in licence_note and license_evidence), dataset marked "
    "'Outra (Aberta)'; LGPD duty recorded: entity keys shipped hashed, NOME_INFRATOR "
    "never shipped. (2) Prediction timing SUPPORTED with documented vintage limitation - "
    "instant = lavratura, present on 705,667/705,667 rows (measured; DT_LANCAMENTO "
    "fallback unused); the zip is one full daily re-export (single stamp on all rows) "
    "and no publisher archive of past vintages exists, so the as-of policy is "
    "retrospective/current-vintage - revision churn measured at <=1.2%/yr for "
    "lavratura years <=2024, 30.5% for 2025, 100% for 2026, and the evaluation contract "
    "must state it (datasus-sinasc precedent); the 12-month target window lies strictly "
    "after the instant by construction. (3) Target SUPPORTED - mechanical same-table "
    "label (entity + strictly-later lavratura within 365 days), label source columns "
    "excludable, entity coverage 95.3% measured and cross-validated against the "
    "publisher's TP_PESSOA_INFRATOR column (exact match), right-censoring measured "
    "(2,347 rows of 2025, all 10,562 of 2026 inside the unobserved window); this is a "
    "re-AUTUACAO task under enforcement attention, not a reoffense claim - stated in the "
    "task card, not hidden. (4) Split capacity SUPPORTED, measured on the full table - "
    "every window carries both classes with thousands of independent clusters (train "
    "44,805 positives over 23,430 entities / 6,149 actions; eval 18,216 over 8,573 / "
    "13,624; holdout 14,995 over 7,241 / 14,800), so the clustered-positives gate "
    "cannot fail camara-style; base-rate drift 17.8% -> 27.7% -> 28.4% recorded as a "
    "phenomenon property. (5) Not a mirror SUPPORTED - differentiated novelty verdict "
    "recorded 2026-10-30 (mechanical check; prior art = causal survival analyses of "
    "flora subsets 2000-2010, no ML-ready benchmark with splits and a scored contract); "
    "the formulation is unchanged by this measurement and the recorded verdict stands. "
    "Cross-check against the publisher's own summary product done with a measured "
    "discrepancy recorded honestly (multas product distinct-AI ratios 1.02-1.20 "
    "pre-2020, 0.82-0.90 in the AIe era) - construction must define the population from "
    "the main table alone. Verdict: READY for construction handoff."
)

r["next_action"] = (
    "READY -> construction on a worker, owned by ADVANCEMENT, in the standing order "
    "(construct -> full-artifact gate 1.5 on the worker -> exact-byte acceptance -> "
    "reference triad BEFORE any model figure -> runner-contract baseline): (1) job "
    "ibama-build-001: download the CURRENT daily export and pin its sha256 + export "
    "stamp at build time (the 2026-11-03 vintage measured by ibama-probe-002, sha256 "
    "4db18814..., is already gone - the blob is overwritten daily; treat the probe's "
    "per-window counts as a nearby-vintage reference and record drift, do not assert "
    "equality), normalize entity keys to bare digits before joining/hashing (canonical "
    "punctuated storage measured on 672,780/672,793 non-empty rows), dedupe on "
    "SEQ_AUTO_INFRACAO (0 duplicates measured in the 2026-11-03 export; assert), define "
    "the population from the MAIN TABLE ONLY (never mix the multas product; its AIe-era "
    "excess is unexplained), state the treatment of Cancelado/Excluido/Substituido "
    "(~1%/yr) and SIT_CANCELADO='S' rows, build the entity-instant panel with prior "
    "history strictly earlier than lavratura, splits train 2005-2015 / eval 2016-2019 / "
    "holdout 2022-2025 (2020-2021 excluded enforcement dip; 2026 excluded, fully "
    "censored), per-window counts re-measured on the pinned vintage; (2) gate 1.5 with "
    "evaluation_contract declaring the retrospective/current-vintage as-of policy, "
    "event_key at entity (or entity+action) level, and the cross-row self-answer risk "
    "addressed (a T+365d re-autuacao is a later row's prior-history feature: anti-join "
    "design + reverse-history probes required); (3) exact-byte acceptance; (4) "
    "references: persistence (entity's prior 12-month re-autuacao signal), identity "
    "(entity auto-count history), calendar, then the full model via the runner contract; "
    "(5) runner baseline. No external threshold applies (same-table label), so no "
    "known-event fixture is owed; the TP_PESSOA cross-check and the multas-product "
    "comparison are the recorded anchors."
)

REC.write_text(json.dumps(r, indent=1, ensure_ascii=False) + "\n")
print("record updated: status", r["status"], "| verdict", r["verdict"])
print("jobs:", [j["id"] for j in r["jobs"]])
print("measurements keys:", sorted(r["measurements"].keys()))
