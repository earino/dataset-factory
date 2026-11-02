# datasus-sinasc-cesarean-share-decline — discovery notes

Session: scheduled discovery tick, regional focus Latin America (Brazil), 2026-11-02.
All probes run from the hosted coordinator container, anonymous HTTPS, source-side aggregates
only (TABNET POSTs ~198 KB each) plus bounded 64 KB partial reads of the public CSV zips.
No bulk data, no workers, no construction. Everything below is reproducible from
`probe/probe_tabnet_parto.py` (retained) and the raw outputs retained in `probe/out/`.

## Decision

`ready` — first maternal-health / vital-statistics task on the bench. At the final-publication
instant of complete-year T SINASC data, predict whether a Brazilian municipality's cesarean
share among resident live births falls ≥ 2 pp from year T to complete year T+2 (the next
complete year entirely after the instant). All five contracts reconciled in record.json
`review`; handoff ordered in `next_action`.

## Licence (checked first)

- Package instrument (dataset-specific): CKAN package 441cc6bd-684a-4afd-a88b-ba4734c9e83e
  carries `license_id: "cc-by"`, `license_title: "Creative Commons Atribuição"`,
  `license_url: http://www.opendefinition.org/licenses/cc-by`. Read from the dataset page's
  `__NEXT_DATA__` on 2026-11-02 (embedded CKAN JSON; the /api/3/action path serves the SPA
  shell, so the page embed is the accessible form).

  Command (evidence extraction):
  ```
  curl -s https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc -o ds.html
  grep -o '"license_id":"[^"]*"' ds.html   # -> "cc-by" (1 hit)
  # full package metadata (license, 95 resources, created/last_modified stamps) parsed from the
  # same page's <script id="__NEXT_DATA__"> JSON; retained transcript in the session log and
  # quoted in record.json sources/measurements.
  ```

- Conflict, recorded: every page of dadosabertos.saude.gov.br (including this dataset's own
  page and its resource pages) shows the footer "Todo o conteúdo deste site está publicado sob
  a licença Creative Commons Atribuição-SemDerivações 3.0" (CC BY-ND 3.0). Resolution per the
  discovery policy (dataset-specific terms over a general site banner): cc-by governs the
  dataset. Corroborations: PDA-MS 2024-2026 ("toda a informação lá disponível pode ser
  utilizada, reutilizada e redistribuída, desde que mantida a mesma licença e a necessidade de
  citação da fonte") and the third-party healthbr-data HF mirror redistributing the same
  microdata under CC-BY 4.0. The conflict and its escalation path (if the footer is read as
  governing, the candidate becomes class D and must not be built) are recorded in
  record.json license_evidence[1] and licence_note.

- `licence_class: A` (CC BY on the package instrument). TABNET pages state no licence; TABNET
  was used only for bounded discovery aggregates, never as the redistribution channel.

## Prediction contract

- Instant: publication of complete-year T data, publisher-stamped final no later than early
  December T+1. Measured anchors: TABNET footnote "Dados finais disponíveis até 2024 - data de
  extração 02/12/2025"; CKAN CSV resource stamps (2025 "preliminar" created 2025-10-21,
  2024 resource created 2024-06-11 as preview, refreshed 2026-05-08).
- Features: municipality-year aggregates of final complete years ≤ T only. Preliminares (T+1)
  and previews (partial T+1/T+2) are excluded by design.
- Target: complete year T+2, every month after the instant.
- Dated example (America/Sao_Paulo, UTC-03, no DST): T = 2024; instant 2025-12-02 (the
  publisher's own final-data stamp for 2024); feature events 1996-01-01..2024-12-31; eligibility
  = ≥ floor resident births in T (floor ∈ {100,200,500} measured); target window
  2026-01-01..2026-12-31. No target month precedes the instant.
- As-of policy: current-vintage retrospective. Historical vintages do not exist (the whole
  1996-2025 CSV archive was last refreshed 2026-05-08; resource `last_modified` read from the
  package page). The FINAL/PRELIMINAR/PRÉVIA ladder is the publisher's own revision structure,
  observed on recent years; no operational point-in-time claim is made for history.
- Cross-row self-answer risk: a row's T+2 share is a later row's feature value. Construction
  must ship pre-aggregated lagged feature matrices only, keep unit × year keys out of
  solver-visible files, and run the docs/PREDICTION-CONTRACT.md gate-1.5 reverse-history probes
  on the exact artifact (recorded in next_action; same anti-join design as
  za-statsa-liquidations-exceedance).

## Probes (commands and results)

TABNET national SINASC table, POST format recovered from the def page
(`/cgi/tabcgi.exe?sinasc/cnv/nvbr.def`; form fields Linha/Coluna/Incremento/Arquivos=nvbr<yy>.dbf,
`formato=prn`; values must be percent-encoded as latin-1 bytes — a UTF-8-encoded `ã` produces
the server error "Campo Incremento nao encontrado em SINASC\bases\final\nvbr94.dbf", which is
how the encoding was fixed; read errors before treating output as empty).

```
python3 probe/probe_tabnet_parto.py national    # year x parto, all periods 1994-2026
python3 probe/probe_tabnet_parto.py months 2024 # month x parto, nvbr24.dbf
python3 probe/probe_tabnet_parto.py mun <year>  # municipality x parto, per year
python3 probe/probe_tabnet_parto.py transitions # base rates from saved outputs
python3 probe/fill_record.py                    # record.json numbers, computed not typed
```

Outputs retained in `probe/out/` (national_year_parto.txt, month_2024_parto.txt,
mun_parto_<year>.txt for 1998, 2000, 2002, 2004, 2009, 2011, 2012, 2014, 2015, 2016, 2017,
2019, 2021, 2022, 2024; ~198 KB each; 17 POSTs, ~3.3 MB total this session).

Results (computed by `transitions`, embedded verbatim in record.json measurements):

- National cesarean share (residence-based, ces/total incl. Ignorado): 1994 32.0%,
  2009 50.0%, 2014 57.0%, 2019 56.3%, 2024 60.59% (1,447,691/2,389,325), 2025 (preliminar)
  61.5%. Known-event fixture for construction: 2024 = 60.59%.
- 2024 completeness: all 12 months present; monthly totals sum to the annual total.
- Transition base rates T→T+2 (both classes in all 24 cells; eligible n at floors 100/200/500):
  1998→2000 decline 34.9/33.8/30.1% rise 37.6/37.2/34.9%; 2002→2004 decline 15.4/13.5/10.6%
  rise 59.9/59.9/60.3%; 2009→2011 decline 12.9/10.7/8.2% rise 67.5/68.3/67.7%;
  2012→2014 decline 22.6/19.9/19.2% rise 50.9/50.7/45.6%; 2014→2016 decline 41.1/40.8/42.7%
  rise 30.1/28.0/21.0%; 2017→2019 decline 25.2/23.1/21.0% rise 44.7/42.6/39.4%;
  2019→2021 decline 25.1/23.4/20.6% rise 45.1/43.9/41.0%; 2022→2024 decline 18.6/15.7/12.4%
  rise 56.4/58.2/55.7%. Era drift (rise-dominant pre-2015, mixed after) is a measured cluster
  structure, not an assumption.
- Municipality rows per year: 5560 (2002-2008), 5565 (2009-2013), 5570 (2014-2024) — mesh drift.
- Data quality eras: Ignorado 15.3% (1994), 1.5% (1995), <1.5% (1996+), <0.2% (2002+);
  Fórceps/outro column populated only 1994-1995 → feature history starts 1996.

## Schema (publisher-documented)

- Dictionary (probe evidence): `SINASC - Estrutura.pdf` (2 pp), linked as the package's
  "Dicionário de Dados": PARTO "Tipo de parto: 1- Vaginal; 2- Cesário; 9- Ignorado"; PESO
  "Peso ao nascer em gramas"; GESTACAO week bands; CONSULTAS prenatal-visit bands; CODMUNRES
  "Código IBGE do município de residência"; DTNASC "dd mm aaaa"; per-field evolution
  (alteração year/type/size) documents schema drift 1996-2019.
- Actual public CSV headers (64 KB partial fetch + partial inflate, no bulk download):
  1996 = 21 columns; 2024 = 62 columns (adds TPROBSON, KOTELCHUCK, PARIDADE, SEMAGESTAC,
  CONSPRENAT, QTDPARTCES, STCESPARTO, ESCMAE2010...). Core label/feature fields present in
  both eras. TABNET labels the cesarean column "Cesáreo" in the national table and "Cesário"
  in the municipality table — parser normalizes both (recorded; caught by the first
  transitions run returning 0 with Cesáreo>0, i.e. a wrong-probe negative avoided).
- 2025 preliminar CSV has the same 62-column header (quoted form).

## Extraction cost (measured, not estimated)

- CSV channel HEAD sizes: 1996 32,281,109 B; 2015 127,210,201 B; 2023 106,371,533 B;
  2024 92,289,354 B; 2025-prelim 102,484,647 B → ~3 GB zipped for 1996-2025, worker-only.
  Anonymous S3 HTTPS, no registration (contrast with the icfes registration-gated channel).
- TABNET aggregate probes: 17 POSTs, ~3.3 MB, 2-6 s each, 4-vCPU coordinator container.

## Novelty (mechanical check recorded 2026-11-02, verdict differentiated)

Searches run via scripts/check-novelty.py (HF datasets, Zenodo, arXiv) plus manual web search.
What exists: SINASC microdata mirrors (HF SidneyBissoli/sinasc 1994-2022 Parquet, healthbR
package); national/macro-region/FU-level ARIMA/joinpoint trend projections of cesarean rates
(CSC 2023); individual-level clinical prediction of cesarean delivery (US NCHS, Ethiopia) and
individual-level SINASC-based ML (preterm-birth stratification, neonatal mortality targeting).
What does not exist: a municipality-year cesarean share-transition benchmark with a
publication-instant contract, eligibility floor, temporal splits and scored baselines.
Similar subject matter is not a mirror: different population (municipalities, not mothers),
different instant (annual publication, not point-of-care), different target (share transition,
not individual delivery mode).

## Next (construction prerequisites recorded, not blockers discovered late)

1. Worker pass over the 30 CSV zips: freeze + sha256; recompute municipality-year counts must
   reproduce the TABNET probe tables and the 60.59% national fixture.
2. Exact per-window class counts (train 2000-2012 / eval 2013-2018 / holdout 2019-2024) at the
   chosen floor/margin; adjust margin/floor on measured grid before any scoring.
3. Anti-join design + gate-1.5 reverse-history probes per docs/PREDICTION-CONTRACT.md.
4. Municipality-code mesh mapping; 1996+ feature era; Ignorado kept in denominator.
5. LICENSE.md: attribution + cc-by package link + current-vintage notice + footer-conflict
   disclosure.
