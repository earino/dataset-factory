# ibama-auto-infracao-recidivism — probe notes

Session: scheduled discovery tick 2026-10-30, Latin America focus. All probes read-only,
anonymous, run 2026-10-30 from the coordinator container unless noted. Probe scripts kept in
`/opt/data/cache/scratch/` during the session (probe_ibama_schema.py, probe_ibama_vol.py,
probe_ibama_sample.py); the retained recipe for every claim is below, so scratch cleanup does
not delete the only copy.

## 1. Source identity and catalog

- Portal: `https://dadosabertos.ibama.gov.br/` (CKAN). Dataset:
  `https://dadosabertos.ibama.gov.br/dataset/fiscalizacao-auto-de-infracao`
  ("Fiscalização - auto de infração", org "Dados Abertos" = IBAMA).
  Read in full in the supported browser (plain HTTP GET of the page also works via the
  web_extract route; the CKAN action API does NOT, see §5).
- Dataset metadata read 2026-10-30: Cobertura temporal "Início em 1980; em funcionamento",
  Cobertura geográfica "Território nacional", Frequência de atualização "Diária",
  Granularidade temporal "Data e hora da lavratura do auto de infração",
  Autor "Coordenação-Geral de Fiscalização Ambiental (CGFis)", Licença "Outra (Aberta)".
- Main-table downloads (publisher-listed URLs, Azure blob):
  - CSV: `https://stibamadadosabertosprd.blob.core.windows.net/dados-abertos/dados/SIFISC/auto_infracao/auto_infracao/auto_infracao_csv.zip`
  - JSON: `.../auto_infracao/auto_infracao_json.zip`
  - enquadramento legal: `.../enquadramento/enquadramento_csv.zip`
  - AIE_MOB (plain CSVs, no zip): `.../AIE_MOB/auto_infracao/aie_enquadramento.csv`, `aie_enquadramentocomp.csv`
  - aux plain CSVs: `.../SIFISC/auto_infracao/especime/especime.csv`, `coordenada/coordenada.csv`, `bioma/bioma.csv`

## 2. Schema (documented by the publisher — data dictionary)

Resource page read in the supported browser 2026-10-30 (dictionary dated 2025-08-08 by IBAMA).
Full dictionary captured in record.json `measurements.served_schema_measured`. Highlights and
the exact reading path:

- Reading path: open `.../dataset/fiscalizacao-auto-de-infracao/resource/b2aba344-95df-43c0-b2ba-f4353cfd9a00`
  in the supported browser; the "Dicionário de dados" block is in the page body. The CKAN
  datastore preview is broken ("Esta visão de recurso não está disponível no momento"), so
  row sampling happens via Range requests on the plain CSVs or the bulk zip.

- The dictionary documents NO per-auto julgamento-outcome field. Fields closest to outcomes:
  DES_STATUS_FORMULARIO (Lavrado, Cancelado, Danificado, Extraviado, Substituído por outro,
  or AIe: Impresso, Excluído), SIT_CANCELADO (S/N), DS_SIT_AUTO_AIE (situação do auto na base
  do AI-e — value list not documented). Value/date fields: VAL_AUTO_INFRACAO is the INITIAL
  value proposed by the agent, explicitly not the final adjudicated value.

- Entity key: CPF_CNPJ_INFRATOR + NOME_INFRATOR (+ NUM_PESSOA_INFRATOR as Sisreg id).
  Location: COD_MUNICIPIO (IBGE code) / MUNICIPIO / UF / coordinates / WKT.
  Enforcement context: SEQ_ACAO_FISCALIZATORIA, TIPO_ACAO (operação, fortuito, rotina,
  demanda jurídica/Ministério Público, linha verde), OPERACAO, DENUNCIA_SISLIV.
  History metadata: DT_LANCAMENTO, DT_ULT_ALTERACAO, TP_ULT_ALTERACAO, JUSTIFICATIVA_ALTERACAO.

## 3. Adjudication label — negative probe (why the task is recidivism, not julgamento)

- Catalog search (browser, 2026-10-30) for "julgamento":
  found `dataset/julgamentos-de-auto-de-infracao-realizado-no-ambito-do-ibama`
  ("Apresenta o volume/quantidade de Julgamento de Auto de Infração distribuídos por bens
  tutelados ... todos os AI julgados, sendo em primeira ou segunda instância"), resources
  per UF under `/dados/SICAFI/<UF>/Volume/volumeJulgamentoAI.{html,csv,json,xml}`.
  These are per-state VOLUME summaries, not per-auto records; they cannot label an auto.
- Publisher tutorial PDF (gov.br/ibama "Tutorial de Autos de Infração..." 2025-10-10, fetched
  2026-10-30, 5,765,859 bytes, text layer extracted): directs bulk access to the open-data
  platform; the full administrative process content is in SEI, accessed per process
  ("a petição de acesso deve ser individual"). No bulk julgamento outcome exists.
- Conclusion recorded: "fine sustained / reduced / dismissed at julgamento" has no obtainable
  per-auto label from open data. The re-autuação task does not need it: label columns are
  CPF_CNPJ_INFRATOR + DAT_HORA_AUTO_INFRACAO in the same table.

## 4. Access cost (measured, no bulk download on the coordinator)

`HEAD` and `Range` probes 2026-10-30 (probe_ibama_sample.py recipe):

```
auto_infracao_csv.zip   123,283,033 bytes  (HTTP 200, anonymous)
auto_infracao_json.zip  171,573,685
enquadramento_csv.zip     8,182,013
especime.csv              5,337,755
coordenada.csv            9,906,264
bioma.csv                14,326,751
aie_enquadramento.csv     34,363,213  (total, via Content-Range)
```

- Range requests honored on plain CSVs: first 32 KB of `aie_enquadramento.csv` shows
  `SEQ_AUTO_INFRACAO;NUM_AUTO_INFRACAO;CD_SERIE__AUTO_INFRACAO;SQ_ENQUADRAMENTO;ADMINISTRATIVO;TP_NORMA;NU_NORMA;...;ULTIMA_ATUALIZACAO_RELATORIO`
  with rows e.g. `2037927;EN3959TS;;601;N;Decreto;6514;50;2;;;2026-10-30 00:17:40`.
  Semicolon separator, UTF-8 BOM. AI-e autos carry alphanumeric NUM_AUTO_INFRACAO (e.g. EN3959TS).
- `bioma.csv` head sample: SEQ values as low as single digits (1980s-era autos) — full
  historical coverage is present, not just recent years.
- All rows in a sample carry the SAME export stamp (e.g. `2026-10-30 01:13:53`), i.e. the
  file is a full daily re-export: current-vintage only, no publisher archive of vintages.

## 5. Access quirks (recorded so the next session does not re-derive them)

- CKAN action API (`/api/3/action/package_show`, `/api/3/action/datastore_search`) returns
  HTTP 403 to plain urllib clients from this egress, even with browser-like headers;
  the same endpoints may work in the supported browser. HTML pages of the same host render
  fine in the browser. The static path `/dados/SICAFI/.../volumeJulgamentoAI.csv` also 403'd
  to plain urllib. The Azure blob host serves plain clients without restrictions.
- dados.gov.br catalog API (`https://dados.gov.br/dados/api/3/action/package_search`)
  returns HTTP 401 to unauthenticated plain clients (2026-10-30).
- Duplication warning from the publisher resource description (read 2026-10-30): autos
  lavrados from October 2019 may appear multiple times when linked to multiple polygons or
  attributes — dedupe on SEQ_AUTO_INFRACAO before counting.

## 6. Licence (class A reasoning in record.json licence_note)

Instruments read 2026-10-30:
- Decreto 8.777/2016 art. 2 III (in.gov.br DOU text): open licence permitting "livre
  utilização, consumo ou cruzamento, limitando-se a creditar a autoria ou a fonte".
- Decreto 8.777/2016 art. 3 IV and art. 4 + §1º as amended by Decreto 9.903/2019
  (planalto.gov.br / camara.leg.br Legis text): "permissão irrestrita de reuso";
  "de livre utilização ... pela sociedade"; "autorizada a utilização gratuita das bases de
  dados" for Union-held rights.
- Dataset-level mark: "Licença: Outra (Aberta)" on both dataset and resource pages.
- LGPD design note: NOME_INFRATOR/CPF_CNPJ_INFRATOR are personal data; shipped features must
  hash entity keys (or restrict to CNPJ). To settle at construction, recorded in licence_note.

## 7. Timing contract basis (documented process, publisher instrument)

IN Ibama nº 19, de 02.06.2023 (gov.br/ibama legislação page, read 2026-10-30): ciência do auto
→ alegações finais → julgamento 1ª instância (decisão em 30 dias do recebimento do processo,
§1º do art. 108; não observância do prazo não implica nulidade) → recurso voluntário 20 dias
(art. 111) → julgamento do recurso 30 dias do recebimento (art. 116) → notificação para
pagamento/parcelamento (art. 117) → Cadin. All of these are POST-lavratura events: none is a
prediction-time feature; the prediction instant (lavratura) precedes all of them.

## 8. Prior art (novelty searches, 2026-10-30)

Queries used (recorded in record.json novelty_check.queries):
- "environmental enforcement repeat offender recidivism prediction machine learning benchmark
  EPA IBAMA reoffending reincidencia infracao"
- "IBAMA multa julgamento recurso prediction machine learning previsão"

Findings:
- ANPEC 2018 (XLVI Encontro Nacional de Economia paper, anpec.org.br PDF): IBAMA flora
  infractions 2000-2010, 127,873 records / 98,006 violators, survival analysis of recidivism;
  23.36% of infringements are recidivism cases, 15.1% of violators recidivate.
- Journal of Quantitative Criminology 39(4) 2023 (Springer, ideas.repec.org entry):
  "Does Reaching the Statute of Limitations Affect the Recidivist Behavior of Environmental
  Aggressors in Brazil?" — same universe, survival/reweighting causal analysis; recidivism
  risk +188% individuals / +34% firms after prescription.
- US EPA/OECA recidivism-rate reports (archive.epa.gov): program measurement (FY2005 rates
  12-44% by media), not prediction benchmarks.
- No ML-ready benchmark with splits and a scored contract located for environmental-enforcement
  recidivism (any jurisdiction) or IBAMA re-autuação specifically.

Verdict recorded via `python3 scripts/check-novelty.py ibama-auto-infracao-recidivism ...`:
**differentiated** (see record.json). The JQCR/ANPEC papers are causal-econometric studies of
a flora subset, not prediction benchmarks; our contribution is the ML-ready formulation,
publication-instant gating, hashed entity keys, splits with clustered counts, and the scored
contract over the full 1980-2026 table.

## 9. What is NOT yet measured (do not mistake for facts)

- Row counts of the full table (by year), per-window positives, clustered positive counts,
  entity-key coverage (share of rows with valid CPF_CNPJ_INFRATOR), cancel/substitution
  rates by year. These need ONE streaming pass over the 123 MB zip = worker-side probe.
- Re-autuação base rate on the full current table (the 15.1% literature figure is flora
  2000-2010 only and is cited as a design anchor, not a measurement).
- Cross-check of any constructed count against the publisher's own summary products
  ("Diagnóstico de Delitos Ambientais" annual PDFs; "Multas Ambientais Distribuídas por Bens
  Tutelados" dataset).

## 10. Next action (discovery owns)

1. Worker-side aggregate probe (bulk stays off the coordinator): stream
   `auto_infracao_csv.zip` once; dedupe on SEQ_AUTO_INFRACAO; compute per-lavratura-year
   counts, entity-key coverage, 12-month re-autuação base rates (first-time vs repeat),
   clustered positives by entity and SEQ_ACAO_FISCALIZATORIA, status mix per year.
2. Publisher-summary cross-check.
3. Reconcile the five contracts; refresh novelty; re-verdict (ready only with measured
   split counts carrying both classes per window).

## 11. Bounded zip-header probe (2026-11-04, coordinator; recipe retained)

`probe/probe_zip_header.py` (retained; ran 2026-11-04 from the coordinator): Range-request the
FIRST 256 KB of `auto_infracao_csv.zip`, parse the zip local-file header, raw-inflate
the compressed prefix. Findings (evidence for the worker job's schema assumptions):

- The zip contains PER-YEAR members: first member `auto_infracao_1977.csv` (usize 2,772 B)
  — coverage starts 1977, not 1980.
- Real served header: 86 columns, semicolon-separated, UTF-8, including all four
  required keys verbatim (SEQ_AUTO_INFRACAO, CPF_CNPJ_INFRATOR, DAT_HORA_AUTO_INFRACAO,
  DT_LANCAMENTO) plus DES_STATUS_FORMULARIO, SIT_CANCELADO, TP_PESSOA_INFRATOR,
  SEQ_ACAO_FISCALIZATORIA, UF, COD_MUNICIPIO, DT/TP_ULT_ALTERACAO,
  ULTIMA_ATUALIZACAO_RELATORIO and the per-row regime marker TP_ORIGEM_REGISTRO_AUTO.
- 1977-era rows carry DATE-ONLY DAT_HORA ('1977-10-16') and EMPTY CPF_CNPJ_INFRATOR —
  entity coverage in the oldest years is poor (measured below).
- Both sampled rows carried the same export stamp 2026-11-03 01:28:15 (full daily
  re-export).

## 12. ibama-probe-001 failure and diagnosis (2026-11-04)

Worker cx23/hel1, 61.1 s, exit 1 (staging release 433488550; probe_error.json +
container log preserved). Failure: summary serialization indexed `d['scored_n']` on the
SQL per-year 'none' bucket (rows with no parseable lavratura date), which the label
merge never populates — KeyError. The local fixture had no such row, so the case was
untested. Download, member load, dedupe, eff normalization and the label pass had all
completed; nothing scientific was measured, no figure quotable. Fix: `d.get(...)`; the
retained fixture test (`probe/test_fixture.py`) was extended with a no-parseable-date
row and re-run green before relaunch. One changed retry (ibama-probe-002) per the job's
recorded stopping condition; a second same-class failure would be a blocker.

## 13. ibama-probe-002 measurements (2026-11-04, the decisive full-table probe)

Job: cx23/hel1, exit 0, 64.6 s (download 123,308,204 B in 26.1 s, sqlite load 14.7 s,
label pass 4.8 s). Zip sha256 `4db188142b03a598d839f5331d3c148aeb7718fd6a657f324d8e98b959621771`,
Last-Modified 2026-11-03 04:45:55 GMT, export stamp 2026-11-03 01:28:15 on every row.
48 per-year members `auto_infracao_1977..2026.csv`, ALL loaded. Raw outputs retained in
`probe/out/` (summary.json, probe_report.json, per_year.json, windows.json, members.json,
multas_*.json, crosscheck_per_year.json, probe_002_container.txt).

- Rows: 705,667 raw = 705,667 deduped. ZERO duplicate SEQ in this export — the
  publisher's multi-polygon duplication warning did not materialize in the 2026-11-03
  csv (n_occ all 1; mismatch flags all 0). Coverage 1977-09-03 .. 2026-10-30 14:30:49.
- Entity keys: cpf(11) 453,978 (64.4%) / cnpj(14) 218,797 (31.0%) / missing 32,874
  (4.7%, concentrated pre-1995) / other 18. Valid-entity share 95.3%. Entities are
  stored in CANONICAL PUNCTUATED form on 672,780/672,793 non-empty rows ('.'/'-'/'/') —
  construction must normalize to bare digits before joining and hashing. Publisher
  cross-check: TP_PESSOA_INFRATOR matches the digit-based split exactly (2023: PF 9,929
  = cpf11; PJ 6,376 = cnpj14). 439,781 distinct entities; autos-per-entity bins
  1: 335,785 / 2: 62,530 / 3-5: 32,272 / 6-20: 8,613 / 21+: 581.
- Timing columns: DAT_HORA_AUTO_INFRACAO non-empty on 705,667/705,667 rows (91,632
  date-only + 614,035 full timestamps) — the DT_LANCAMENTO fallback was never needed
  (479 rows have empty DT_LANCAMENTO; 0 unparseable lavraturas). 0 rows fall in the
  'none' eff bucket (the probe-001 crash case exists in principle but is empty on this
  vintage).
- Windows (valid entity, right-censored at 2025-10-30 23:59:59):

  | window | n | positives | rate | distinct pos entities | distinct pos actions | distinct pos months |
  |---|---|---|---|---|---|---|
  | pre-2005 (context) | 271,385 | 36,122 | 13.31% | 16,340 | 0 (SEQ_ACAO empty this era) | 263 |
  | train 2005-2015 | 251,614 | 44,805 | 17.81% | 23,430 | 6,149 | 132 |
  | eval 2016-2019 | 65,725 | 18,216 | 27.72% | 8,573 | 13,624 | 48 |
  | gap 2020-2021 (excluded) | 18,419 | 4,861 | 26.39% | 2,596 | 4,621 | 24 |
  | holdout 2022-2025 | 52,741 | 14,995 | 28.43% | 7,241 | 14,800 | 46 |

  Censoring: 2,347 rows of 2025 and all 10,562 rows of 2026 sit inside the unobserved
  365-day window. First-time vs repeat (2023): first-time 8,449 n / 1,524 pos = 18.0%;
  repeat 7,856 n / 3,878 pos = 49.4%. Base-rate drift 17.8% -> 27.7% -> 28.4% across
  train/eval/holdout is a measured phenomenon property.
- Regime mix (TP_ORIGEM_REGISTRO_AUTO): SICAFI 100% through 2018; 2019 mixed (SICAFI
  12,521 / AI-e 1,922); AI-e dominant from 2020 with a small late-recorded SICAFI tail
  (110-188/yr 2023-2026). The 2019-10-08 boundary in the record holds.
- Status mix (2023): Lavrado 16,250 (99.0%), Cancelado 146, Excluído 10, Substituído
  por outro 3; SIT_CANCELADO='S' 159 (~1%). Construction must state which side of the
  population these rows fall on.
- Revision evidence (current-vintage limitation): DT_ULT_ALTERACAO non-empty on
  96.7-100% of rows in every year, but rows altered within 12 months of the export
  stamp are <=1.2% for every lavratura year <=2024, 30.5% for 2025 and 100% for 2026 —
  the churn is concentrated in the most recent ~18 months, matching the censoring
  design. TP_ULT_ALTERACAO (2023): Alterado 15,199 / Preenchido 1,164 / Cancelado 45.
- PUBLISHER-SUMMARY CROSS-CHECK (step 2): the "Multas Ambientais Distribuídas por Bens
  Tutelados" product (csv zip 24,655,019 B, sha256 `aa3173ce48a80694437a4ea98c3eeae644a
  2246f507a12f15c57a9a39e6ddfca`, 27 UF files, 725,081 rows; Tipo Auto: Multa 719,326 /
  Advertencia 5,317 / Multa Diária 438) is NOT an aggregate count table but a second
  per-auto listing (rows duplicate an auto across bens tutelados). At distinct-Nº-AI
  grain per Data Auto year it tracks the main table at ratio 1.02-1.20 for 1977-2019
  (probe higher: advertência autos are in the main table only) and 0.82-0.90 for
  2020-2026 (the multas product carries 11-18% MORE distinct autos than the main table
  in the AIe era — unexplained; hypothesis, unverified: different date semantics or
  voided app-era forms). DESIGN INPUT: define the population from the main table alone;
  never mix products. The "Diagnóstico de Delitos Ambientais" annual PDFs were not
  re-fetched; the multas product served as the cross-check.
- PROBE DEFECTS (cosmetic, aggregate-level): the windows table's 'censored_excluded' field is
  always 0 (the window dict never increments it; per-year censored_n is correct);
  pre-2005 acao_pos = 0 because SEQ_ACAO is empty in that era (rows_without_seq_acao
  525,203 overall).
- DATED EXAMPLE (America/Sao_Paulo; source timestamps carry no timezone and are
  treated as publisher-local): an auto lavrado at T = 2023-06-15 09:30 local
  (DAT_HORA_AUTO_INFRACAO, present on every row). Features: (a) the current auto's
  issuance-time attributes (type, infraction code, initial proposed value, gravity,
  conduct, UF/município, bioma, action type); (b) the SAME entity's prior autos with
  lavratura strictly earlier than T — current-vintage history, with revision share
  quantified above. First publication: the daily bulk export publishes the current
  vintage (stamp 2026-11-03 01:28:15); no historical vintages exist, so the as-of
  policy is retrospective/current-vintage and the evaluation contract must state it
  (datasus-sinasc precedent). Eligibility: valid entity key (95.3% of rows) and
  lavratura <= 2025-10-30 23:59:59 (censoring). Prediction instant: T. Target: another
  same-entity auto with lavratura in (T, T+365d] = (2023-06-15 09:30, 2024-06-15 09:30]
  local — entirely after T. Measured context: 2023 scored 16,305 rows / 5,402 positives
  (33.1%); a first-time 2023 entity measured 18.0% vs 49.4% for a repeat entity. No
  entity is named here on purpose: entity rows are personal data (LGPD), never pulled
  to the coordinator; the probe measured aggregates only and construction ships hashed
  keys.

## 14. Verdict (2026-11-04): READY (go)

All five contracts have measured evidence (see record.json `review`): licence class A
(quoted instruments, 2026-10-30); timing supported with the current-vintage limitation
measured and to be declared in the evaluation contract; target mechanical, entity
coverage 95.3% measured and publisher-validated, censoring measured; split capacity
measured on the full table with thousands of independent clusters per window (the
camara year-cluster failure mode cannot occur); novelty differentiated (recorded
2026-10-30; formulation unchanged by this measurement). Handoff to ADVANCEMENT in the
standing order: construct -> full-artifact gate 1.5 -> exact-byte acceptance ->
reference triad BEFORE any model figure -> runner-contract baseline. Design inputs
carried in record.json next_action: pin the build's own daily-export vintage, normalize
entity digits before hashing, population from the main table only, state cancelled/
excluded/substituted treatment, event_key at entity level, anti-join for the cross-row
self-answer risk (a T+365d re-autuação is a later row's prior-history feature).
