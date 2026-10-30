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
