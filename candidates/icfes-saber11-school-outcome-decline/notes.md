# icfes-saber11-school-outcome-decline — discovery notes

Opened 2026-11-01 (regional focus: Latin America; scheduler tick). Discovery-only session: no
construction, qualification, packaging, publication or worker launched. All probes are bounded
anonymous HTTPS from the coordinator; source-side aggregates only, no bulk microdata transferred
(~8 MB total, all aggregate rows).

## Lead selection (why this source)

Portfolio gap measured first (`python3 scripts/discovery-coverage.py`, `python3 -m factory candidate
list`): 119 candidates, 43 live, Latin America 10 (BR 4, MX 2, CL 2, CO 1, AR 1) — no education-outcome
task anywhere on the bench, and the heavy families are already loaded (procurement: austender +
canadabuys + chilecompra-dropped; entity-exit: companies-house GB + 3 CA registry variants; aggregate
forecast: abs-visitor-arrivals + za-statsa-liquidations; air/environment: many). Colombia is a named
focus country. Saber 11 (ICFES national exit exam) gives a census-grade, annually repeated, fully
documented school outcome series — the first education task on the bench, on a clean prediction
contract (next school-year outcome vs published history).

## Licence (checked first)

- `curl -s https://www.datos.gov.co/api/views/kgxf-xxbe.json` (also rnvb-vnyh, a8xr-en99):
  `licenseId: CC_40_BY_SA`, `license: Creative Commons Attribution | Share Alike 4.0 International`,
  `attribution: Instituto Colombiano para la Evaluación de la Educación - ICFES, Bogotá D.C.`,
  `provenance: official`, owner account `bpbw-gs2u` ("ICFES DATOS ABIERTOS").
  → Class B (attribution + share-alike; carried into LICENSE.md). Dataset-level instrument on the
  publisher's own account; not inferred from a portal-wide policy.
- `7vdz-x7ah` ("Microdato de resultados en pruebas Saber 11", licenceId None) turned out to be a
  FEDERATED Medellín (meData) catalog entry, not a national distribution — not used.
- DataIcfes (registration-gated channel): terms UNREAD — part of the recorded next action; no grant
  assumed.

## Schema / column documentation (publisher's own instrument)

`kgxf-xxbe` = "Resultados únicos Saber 11", 7,109,704 rows × 51 columns, `rowsUpdatedAt`
2023-08-23T22:52:07Z. Every column carries a description in the view metadata (read in full via
`python3 probe/dump_columns.py kgxf-xxbe` (retained); key fields):
`periodo` (Periodo de los resultados), `estu_consecutivo` (unique examinee id, embeds period code),
`cole_codigo_icfes` (Código ICFES del Establecimiento; 7,085,971 non-null),
`cole_cod_dane_establecimiento`/`_sede`, `cole_calendario`, `cole_naturaleza`, `cole_jornada`,
`cole_bilingue`, `cole_caracter`, depto/mcpio codes and names, `fami_*` (estrato, parental education,
household size/assets), scores `punt_ingles` (7.11M), `punt_matematicas` (7.11M),
`punt_sociales_ciudadanas`/`punt_c_naturales`/`punt_lectura_critica`/`punt_global` (4,500,181 =
2014-2 onward), `estu_estadoinvestigacion` (publication-consent status).
`rnvb-vnyh` (2020-2) = 81 columns, richer (percentiles, desemp levels, `estu_inse_individual`,
`estu_nse_establecimiento`), scores typed number.

## Probes (commands → results)

1. Period coverage — `python3 probe_period_coverage.py` (3 SoQL aggregate GETs):
   rows per periodo: 20101 41,656; 20102 628,374; 20111 32,978; 20112 617,442; 20121 38,432;
   20122 641,956; 20131 35,179; 20132 548,596; 20141 24,910; 20142 546,727; 20151 25,973;
   20152 544,491; 20161 13,095; 20162 550,275; 20171 13,018; 20172 548,269; 20181 32,348;
   **no 20182**; 20191 12,561; 20194 1,096,524; 20201 15,435; **no 20202** (exists as rnvb-vnyh:
   504,872 rows); 20211 15,528; **no 20212**; 20221 20,049; 20224 1,065,888; **nothing after 20224**.
   `punt_global` populated only 20142 onward (global-score era starts 2014-2 — matches the third-party
   Croma guide, independently read: "The exam took its current form in the second sitting of 2014").
   **Decisive negative: the Calendario A school-years 2018 and 2021 are absent from the whole
   anonymous channel.**
2. Per-school aggregates — `python3 probe_per_school.py` (16 SoQL group-by GETs, ~9 s each,
   `avg(punt_global::number)` works on the text-typed column; per_school/*.csv retained):
   Cal-A schools/school-year: 11,793 / 11,980 / 12,134 / 12,972 / 13,189(2019) / 13,654(2022);
   2020 (rnvb-vnyh): 13,395. Cal-B sittings 2015-1..2022-1: 381/348/350/390/348/377/386/405.
   Score sanity: school means 102–415 on 0–500; Cal-A sitting averages 238.5–247.5, Cal-B 306.9–315.2.
3. Transition capacity — `python3 probe_transitions.py` (local join of the per-school aggregates;
   transition_stats.json retained):
   Cal-A: 2014→15 9,925 schools, decline 52.42% (≥5 pt 31.98%, ≥10 pt 16.08%); 2015→16 9,883,
   20.66% (9.87%, 4.45%), mean delta +8.35; 2016→17 9,092, 62.54% (42.23%, 24.01%), delta −2.97;
   2019→20 9,091, 51.04% (33.55%, 19.69%), delta −0.24. Only FOUR transitions exist on the anonymous
   channel (2018/2021 absent) → cannot fill three disjoint windows.
   Cal-B (complete series): 2015→16 289 schools decline 34.26%; 2016→17 290, 77.24%; 2017→18 293,
   33.79%; 2018→19 304, 49.34%; 2019→20 283, 76.68%; 2020→21 288, 37.85%; 2021→22 308, 48.38%.
   Measured equating caveat: national school-mean shifts between sittings are large
   (+8.35, −2.97 Cal-A; −8.83, −9.54 Cal-B) → an absolute-margin label partially measures national
   equating drift; percentile-rank label is the equating-invariant alternative (construction decides).
4. Row model — SoQL `count(distinct estu_consecutivo)` on 20194: 546,211 distinct vs 1,096,524 rows
   → the 2019-2 sitting is loaded twice (dedupe by consecutivo at construction). 20224 sample:
   1,000/1,000 distinct. `estu_estadoinvestigacion` on 20224: 'PUBLICAR' 1,065,436 /
   'VALIDEZ OFICINA JURÍDICA' 452 (publication-consent governance column).
5. Registration channel — DataIcfes inventory image (403 to plain HTTP clients; fetched through the
   supported browser, 178,717 bytes; vision-read): "Examen Saber 11° — Disponibilizada 1996 - 2024 —
   Nivel de observación: Estudiante". "Nuevas bases" image: "Examen Saber 11°: Desde 1996 hasta 2024".
   Per-sitting presence of 2018-2/2021-2/2023/2024 NOT verifiable without registering (access link is
   auto-emailed to the registrant — needs an inbox this environment does not have). Old portal URL
   `icfes.gov.co/web/guest/data-icfes` redirects to the public homepage (no public listing).
   Independent evidence: IADB working paper (temperature/SABER 11) used second-semester sittings
   2009-2..2019-2 and documents downloading period folders 2009-2 through 2019-2 from the OLD
   DataIcfes → 2018-2 existed there; Croma guide (docs.usecroma.com, read 2026-11-01): "Two second
   sittings are missing from what it has published, 2018-2 and 2021-2"; Mendeley jg6kkv8mg6 used
   Saber 11 periods 2014-2..2021-1.
6. Timing — official calendars (PDFs + dated news): Cal-A 2025 exam 2025-08-10 (reprogrammed
   2025-08-31 for some municipalities), individual results published 2025-10-10; Cal-B 2025 exam
   2025-04-06, results 2025-06-06; Cal-B 2026 exam 2026-03-15, results 2026-05-15; 2026 Cal-A
   results-publication news dated 2026-09-22. Open-microdata lag measured (rowsUpdatedAt 2023-08-23
   with data through 2022; per-year 2020 datasets createdAt 2021-03-15) → panel is current-vintage
   retrospective; an operational system at the instant would use ICFES's same-day aggregate reports
   ("Otros resultados examen Saber 11°": Clasificación de Planteles, Reportes de Resultados Agregados).
7. Cost — ~40 anonymous GETs, ~8 MB total; each SoQL aggregate ~9 s (hosted coordinator, 4 vCPU /
   1.9 GiB). Bulk: unified table 7.1M×51 (CSV export streams, no Content-Length; >1.5 GB estimate) —
   worker-class. Socrata legacy export endpoint carries `Deprecation`/`Sunset: 2026-12-22` headers →
   construction should page the resource API instead (measured working, incl. count(distinct)).

## Dated example (Calendario A, Colombia Time COT = UTC−05:00, no DST)

- Feature event window (latest): sitting T = school-year 2025 Cal-A — exam applied Sunday
  2025-08-10; individual results (and aggregate school reports) published Friday 2025-10-10.
- Prediction instant: 2025-10-10 COT (publisher states the date, not the hour — date-level instant).
- Eligibility at instant: school has ≥10 scored examinees with valid PUNT_GLOBAL in sitting T
  (measured ~10.7–12.8k schools qualify in prior sittings).
- Target start/end: school-year T+1 Cal-A sitting — exam ~August 2026, results ~Sept/Oct 2026; the
  whole target window lies 11–13 months after the instant. No part of the target window precedes
  the instant (future-event target, checked on timestamps not day labels).

## Novelty

`python3 scripts/check-novelty.py icfes-saber11-school-outcome-decline --query ... --verdict
differentiated` recorded (queries: "Saber 11", "school performance prediction", "Colombia education
dataset", "school aggregate outcomes forecasting"). Prior art read: student-level cross-sectional
same-exam ML (CRISP-DM Saber 11 papers; family-variable classification trees 2016; lagging-regions
EDM+Shapley study; Saber Pro level prediction from Saber 11 scores; linked Saber11/SaberPro Mendeley
dataset; a Kaggle microdata mirror; school-specific single-school case study). No school-aggregate
next-school-year outcome benchmark with temporal splits found in HF/zenodo/arXiv/web. Nearest bench
sibling: ofsted-childrens-home-next-rating (GB regulatory inspection rating — different population,
label, instant). Third-party Croma API serves per-school Saber 11 aggregates 2010-2022 (useful
cross-check comparator at construction; it is an aggregator, not the publisher).

## Decision

`investigating` — promising lead, one bounded probe from a ready/drop decision. Split capacity on the
primary (Cal-A) population is the only unresolved contract: the anonymous channel yields 4 transitions
(2018-2/2021-2 missing from every published open copy); the renovated DataIcfes claims Saber 11
1996-2024 but per-sitting presence of the gap years and fresh tail is unverified (registration is
auto-emailed — needs an operator-provided inbox). Acceptance criteria for each outcome are in
record.json next_action (advance / Cal-B redesign decision / park with reopening trigger).
The Cal-B fallback is measured complete (7 consecutive transitions) but ~20× smaller — recorded as an
explicit redesign decision, not silently taken.

## Probe scripts retained here

- `probe/probe_period_coverage.py` — period × coverage aggregates (rows, scored rows, calendar mix).
- `probe/probe_per_school.py` — per-sitting per-school aggregates → `per_school/*.csv` + summary.
- `probe/probe_transitions.py` — adjacent-sitting join → `transition_stats.json` (base rates).
- `per_school/`, `transition_stats.json`, `period_coverage.json` — aggregate probe outputs (small).
