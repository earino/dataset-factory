# Fill the icfes-saber11-school-outcome-decline candidate record with measured
# discovery evidence (session 2026-11-01). One-shot script retained as the recipe
# for exactly what was written into record.json and when; re-running would
# overwrite the record with the 2026-11-01 snapshot, so do not run it again.
#   python3 candidates/icfes-saber11-school-outcome-decline/probe/fill_record_2026_11_01.py
import json
from pathlib import Path

REC = Path(__file__).parent.parent / "record.json"
r = json.loads(REC.read_text())
now = "2026-11-01T00:28:00+00:00"

r["updated_at"] = now
r["status"] = "investigating"
r["domain"] = (
    "education - school-aggregate outcome dynamics on Colombia's national exit exam "
    "(Saber 11, ICFES): next-school-year outcome decline early warning"
)
r["prediction_question"] = (
    "For a Colombian Calendario A secondary school whose Saber 11 school-year T sitting results are "
    "published (individual results are published on a dated official calendar, e.g. sitting 2025: exam "
    "applied 2025-08-10, individual results published 2025-10-10), predict whether the school's mean "
    "global score (PUNT_GLOBAL, 0-500 scale, school-year T+1 sitting) falls below its school-year T mean "
    "by at least a fixed margin. Features are the school's own published history up to and including "
    "sitting T: per-subject school means and cohort sizes for sittings <= T, school registry attributes "
    "(calendar, naturaleza oficial/no oficial, genero, jornada, bilingue, area, DANE department/municipality "
    "codes), and cohort context shares from the publisher's own questionnaire fields (FAMI_*: estrato, "
    "parental education, household assets), all documented in the publisher's 51-column schema with "
    "descriptions."
)
r["prediction_time"] = (
    "Prediction instant = the official publication date of the sitting's individual results (dated example, "
    "Colombia Time COT=UTC-05:00, no DST): sitting T = Calendario A school-year 2025, exam applied Sunday "
    "2025-08-10 (ICFES calendar PDF 2025_Calendario11A_V03.pdf; ICFES news 2025-08-08 '640 mil personas "
    "presentaran las pruebas Saber 11 calendario A' este domingo 10 de agosto; some municipalities "
    "reprogrammed to 2025-08-31 per news 2025-08-12), individual results published Friday 2025-10-10 "
    "(calendar PDF row 'Publicacion de resultados individuales Saber 11 en pagina web: viernes 10 de "
    "octubre de 2025'). INSTANT = 2025-10-10 COT (hour not stated by the publisher; date-level instant). "
    "Feature event window closes at the instant: school aggregates for sittings <= T are published (with "
    "sitting T's results, ICFES also publishes its per-school aggregate reports - 'Otros resultados examen "
    "Saber 11': Clasificacion de Planteles, Reportes de Resultados Agregados). Eligibility at instant: "
    "school has >=10 scored examinees with valid PUNT_GLOBAL in sitting T (measured school counts per "
    "sitting: 10,701-12,778 at n>=10 of 11,906-13,748 raw). Target window = Calendario A school-year T+1 "
    "sitting: exam applied ~August T+1 (2026 Cal-A sitting: results-publication news dated 2026-09-22), "
    "results published ~Sept/Oct T+1 - the whole target window (exam, scoring, publication) falls ~11-13 "
    "months AFTER the instant; no part of it precedes the instant. AS-OF / VINTAGE POLICY (recorded "
    "limitation, not resolved): the open MICRODATA for a sitting is published on datos.gov.co with a long "
    "lag (measured: per-year 2020 datasets uploaded 2021-03-15; unified table's 2022 sitting appears at "
    "rowsUpdatedAt 2023-08-23), so the constructed panel is a CURRENT-VINTAGE RETROSPECTIVE panel: an "
    "operational system at the historical instant would have used ICFES's same-day aggregate reports, not "
    "the open microdata; no point-in-time operational claim is made for the microdata channel, and "
    "microdata revisions between snapshots are not excluded (the 'Resultados unicos' table is itself a "
    "publisher curation; ESTU_ESTADOINVESTIGACION is a publication-consent status, measured values "
    "'PUBLICAR' 1,065,436 / 'VALIDEZ OFICINA JURIDICA' 452 for 20224). Label-definition caveat (measured): "
    "national sitting-level mean shifts between adjacent sittings are large (school-mean deltas: +8.35 "
    "(2015->2016), -2.97 (2016->2017), -8.83/-9.54 on Calendario B pairs) because ICFES equates scores per "
    "sitting, so an absolute-points decline label partially reflects national equating drift; construction "
    "must either define the label relative to the sitting's school-mean distribution (percentile-rank drop, "
    "equating-invariant) or ship sitting-level national aggregates as history features and state the "
    "conflation explicitly."
)
r["target_definition"] = (
    "Binary label per (school, transition T->T+1): 1 if the school's mean PUNT_GLOBAL over its scored "
    "examinees in the Calendario A school-year T+1 sitting is lower than its school-year T mean by at least "
    "the fixed margin (margin or a percentile-rank variant chosen at construction; both measured feasible). "
    "Label source columns: PUNT_GLOBAL of sitting T+1 (and the sitting T+1 rows generally) - excluded from "
    "shipped features by construction (features use sittings <= T only). Measured base rates (schools with "
    "n>=10 examinees on both sides, server-side aggregates): any decline 52.42% / 20.66% / 62.54% / 51.04%; "
    "decline >=5 points 31.98% / 9.87% / 42.23% / 33.55%; decline >=10 points 16.08% / 4.45% / 24.01% / "
    "19.69% for the four available Cal-A transitions 2014->15, 2015->16, 2016->17, 2019->20. Censoring: a "
    "school with no sitting-T results is not eligible (excluded, not imputed); a school with no T+1 sitting "
    "(closed/merged/moved to another calendar) is observed absence of an outcome and is excluded from the "
    "scored panel - construction must record the non-random-exit rate as part of the definition (school "
    "persistence measured: 9,025-10,952 of ~11.9-13.7k schools appear in adjacent sittings)."
)
r["sources"] = [
    {
        "name": "Resultados unicos Saber 11 (student-level anonymized microdata, sittings 2010-2022), datos.gov.co, published by ICFES DATOS ABIERTOS",
        "url": "https://www.datos.gov.co/Educaci-n/Resultados-nicos-Saber-11/kgxf-xxbe",
        "api": "https://www.datos.gov.co/resource/kgxf-xxbe.json (Socrata SoQL, anonymous)",
        "metadata": "https://www.datos.gov.co/api/views/kgxf-xxbe.json",
        "measured": "7,109,704 rows x 51 columns; rowsUpdatedAt 2023-08-23T22:52:07Z; PUNT_GLOBAL populated 4,500,181 rows (2014-2 onward, the 0-500 global-score era; pre-2014 sittings carry only matematicas/ingles on the old scale); stable school keys COLE_CODIGO_ICFES (7,085,971 non-null) + COLE_COD_DANE_ESTABLECIMIENTO/SEDE; COLE_CALENDARIO A/B/OTRO; per-sitting rows measured by probe (Cal A: 546,727 / 544,491 / 550,275 / 548,269 for 2014-2..2017-2; 2019 school-year = periodo 20194 with 1,096,524 rows = 546,211 distinct consecutivos, i.e. the 2019-2 sitting loaded twice - dedupe by ESTU_CONSECUTIVO at construction; 2022 school-year = periodo 20224 with 1,065,888 rows; 2018-2 and 2021-2 ABSENT, measured; nothing after the 2022 school-year).",
    },
    {
        "name": "Saber 11 2020-2 (Calendario A 2020 sitting, richer 81-column schema incl. ESTU_INSE_INDIVIDUAL/percentiles), datos.gov.co, ICFES DATOS ABIERTOS",
        "url": "https://www.datos.gov.co/Educaci-n/Saber-11-2020-2/rnvb-vnyh",
        "api": "https://www.datos.gov.co/resource/rnvb-vnyh.json (Socrata SoQL, anonymous)",
        "measured": "504,872 rows x 81 columns, all five subject scores + PUNT_GLOBAL typed number; per-school aggregates measured (13,395 schools; 9,091 join to the 2019 school-year at n>=10); uploaded 2021-03-15 (bulk backfill of the 2020 sittings; creation dates on the per-year datasets do not evidence the natural publication cadence).",
    },
    {
        "name": "Saber 11 2020-1 (Calendario B 2020 sitting), datos.gov.co, ICFES DATOS ABIERTOS",
        "url": "https://www.datos.gov.co/Educaci-n/Saber-11-2020-1/a8xr-en99",
        "measured": "present on the same ICFES account, same licence; Calendario B sittings 2015-1..2022-1 all present in the unified table (12,561-15,528 rows each).",
    },
    {
        "name": "DataIcfes portal (renovated 2025; registration-gated repository of all ICFES exam microdata)",
        "url": "https://www.icfes.gov.co/investigaciones/data-icfes/",
        "measured": "Registration via public Microsoft Forms link, access link auto-emailed to registrant (process documented in IADB working paper data appendix: registration is automatic and immediate); the portal's own inventory image (read 2026-11-01 from https://www.icfes.gov.co/wp-content/uploads/2025/03/inventario_img.jpg, fetched through the supported browser after a 403 to plain HTTP clients) lists 'Examen Saber 11: Disponibilizada 1996 - 2024, Nivel de observacion: Estudiante'; the 'nuevas bases' image (2025/03) states 'Examen Saber 11: Desde 1996 hasta 2024'. Per-sitting presence of the anonymous-channel gaps (2018-2, 2021-2) and of 2023/2024 sittings is NOT verifiable without registering (the access link is emailed to the registrant; cannot be completed from this environment). Independent evidence: an IADB working paper used second-semester sittings 2009-2..2019-2 and documents downloading period folders 2009-2 through 2019-2 from the OLD DataIcfes (so 2018-2 existed there); a third-party API guide (docs.usecroma.com, read 2026-11-01) independently states 'Two second sittings are missing from what it has published, 2018-2 and 2021-2'; a Mendeley linked Saber11/SaberPro dataset (jg6kkv8mg6) used Saber 11 periods 2014-2..2021-1.",
    },
    {
        "name": "ICFES official exam/result calendars (timing evidence)",
        "url": "https://www.icfes.gov.co/evaluaciones-icfes/cronograma-de-evaluaciones/cronograma-examen-saber-11/",
        "measured": "Calendario A 2025: registro Mar-Apr 2025, aplicacion domingo 2025-08-10 (reprogrammed 2025-08-31 for some municipalities), resultados individuales viernes 2025-10-10 (PDF 2025_Calendario11A_V03.pdf + V01). Calendario B 2025: aplicacion domingo 2025-04-06 (moved from 2025-03-23), resultados 2025-06-06 (news 2025-03-04). Calendario B 2026: aplicacion 2026-03-15, resultados 2026-05-15 (PDF calendario-2026-11B-vf.pdf). 2026 Cal A: results-publication news dated 2026-09-22.",
    },
]
r["license_evidence"] = [
    {
        "quote": "license: Creative Commons Attribution | Share Alike 4.0 International (licenceId CC_40_BY_SA; termsLink http://creativecommons.org/licenses/by-sa/4.0/legalcode); attribution: 'Instituto Colombiano para la Evaluacion de la Educacion - ICFES, Bogota D.C.'; provenance: official",
        "source": "Socrata view metadata for kgxf-xxbe 'Resultados unicos Saber 11', https://www.datos.gov.co/api/views/kgxf-xxbe.json, read 2026-11-01 (same licenceId CC_40_BY_SA and attribution measured on rnvb-vnyh 'Saber 11 2020-2' and a8xr-en99 'Saber 11 2020-1'; dataset-level instrument on the publisher's own official account)",
    },
    {
        "quote": "Examen Saber 11: Disponibilizada 1996 - 2024, Nivel de observacion: Estudiante",
        "source": "DataIcfes inventory image, https://www.icfes.gov.co/wp-content/uploads/2025/03/inventario_img.jpg, read via supported browser 2026-11-01 (403 to plain HTTP clients; browser fetch succeeded, 178,717 bytes) - evidence of coverage claim on the registration channel, NOT a licence statement; DataIcfes terms are UNREAD (registration-gated) and are part of the recorded next probe",
    },
]
r["licence_class"] = "B"
r["licence_note"] = (
    "Class B: CC BY-SA 4.0 on the publisher's own official datos.gov.co datasets (kgxf-xxbe, rnvb-vnyh, "
    "a8xr-en99) - attribution ('Instituto Colombiano para la Evaluacion de la Educacion - ICFES') plus "
    "share-alike: derived rows ship under CC BY-SA 4.0 with the attribution statement; conditions carried "
    "into LICENSE.md. UNRESOLVED: the licence/terms of the registration-gated DataIcfes channel (needed "
    "for the 2018/2021 gap years and 2023/2024 sittings) is unread and must be classified before any of "
    "those bytes enter construction; no grant is assumed."
)
r["jurisdiction"] = {
    "country": "CO",
    "region": "Latin America",
    "publisher": "Instituto Colombiano para la Evaluacion de la Educacion (ICFES), Bogota D.C. - national standardized exit exam (Saber 11); distribution channels: Portal Nacional de Datos Abiertos datos.gov.co (MinTIC Socrata, publisher account 'ICFES DATOS ABIERTOS') and the ICFES DataIcfes repository",
    "recorded_at": "2026-11-01",
}
r["split_strategy"] = (
    "PROPOSED (blocked, measured): panel unit = (school, transition T->T+1); windows disjoint by TARGET "
    "school-year. If the DataIcfes channel fills the gaps (2018, 2021) and adds 2023/2024: Calendario A "
    "school-years 2014-2024 give 10-11 transitions -> e.g. train targets 2015-2019 (4-5 transitions), "
    "eval targets 2020-2022 (2-3), holdout targets 2023-2024 (2); per-transition rows measured at "
    "9,025-10,952 (n>=10 both sides) with both classes present in every measured transition. MEASURED "
    "BLOCKER on the anonymous channel: only 4 consecutive Cal-A transitions exist (2014->15, 2015->16, "
    "2016->17, 2019->20; 2018-2/2021-2 absent from all published open data, nothing after the 2022 "
    "school-year) - a 1-transition holdout is not a defensible window, so the anonymous channel alone "
    "cannot fill three windows. MEASURED FALLBACK (not chosen): Calendario B sittings 2015-1..2022-1 are "
    "complete and consecutive (7 transitions; 283-308 schools per pair, both classes in every pair) but "
    "the population is ~20x smaller and private/Atlantic-coast concentrated - a redesign decision to make "
    "explicitly, not silently. Cluster structure: positives within a transition share the cohort-year "
    "shock (equating drift measured above) - the independence scale is the transition, and any reference "
    "comparison must use transition-clustered intervals."
)
r["measurements"] = {
    "period_coverage_2026_11_01": {
        "method": "probe_period_coverage.py - 3 SoQL aggregate queries (rows per periodo; punt_global non-null per periodo; calendar mix among scored rows), anonymous HTTPS",
        "rows_per_periodo": "20101 41,656; 20102 628,374; 20111 32,978; 20112 617,442; 20112-era sittings carry no PUNT_GLOBAL (old scale); 20141 24,910; 20142 546,727; 20151 25,973; 20152 544,491; 20161 13,095; 20162 550,275; 20171 13,018; 20172 548,269; 20181 32,348; NO 20182; 20191 12,561; 20194 1,096,524; 20201 15,435; NO 20202 in this table (exists as rnvb-vnyh, 504,872 rows); 20211 15,528; NO 20212; 20221 20,049; 20224 1,065,888",
        "scored_rows": "PUNT_GLOBAL populated from 20142 onward: 546,727 / (20151) 25,973 / 544,491 / 13,095 / 550,275 / 13,018 / 548,269 / 32,348 / 12,561 / 1,096,524 / 15,435 / 15,528 / 20,049 / 1,065,888; global-score era starts 2014-2 (matches third-party guide: 'The exam took its current form in the second sitting of 2014')",
        "calendario_mix": "Cal-A sittings (periodo *2/*4): 542,466-1,087,902 scored rows Cal-A per school-year; Cal-B sittings (periodo *1): 11,865-25,829 scored rows; a few hundred Cal-A schools also test in -1 sittings from 2018",
    },
    "school_counts_per_sitting_2026_11_01": {
        "method": "probe_per_school.py - per-sitting SoQL group-by on (cole_calendario, cole_codigo_icfes, cole_cod_dane_establecimiento) with count(*) and avg(punt_global::number); 16 queries, ~8 MB total transferred; per_school/*.csv retained",
        "calendario_A_schools": "20142 11,906 (11,793 Cal-A); 20152 12,097 (11,980); 20162 12,209 (12,134); 20172 13,073 (12,972); 20194 13,297 (13,189); 20224 13,748 (13,654); 20202 (rnvb-vnyh) 13,395; n>=10 filter keeps 10,701-12,778",
        "calendario_B_schools": "20151 381; 20161 348; 20171 350; 20181 390; 20191 348; 20201 377; 20211 386; 20221 405 (n>=10 keeps 306-394)",
        "score_sanity": "school means 102-415 on the 0-500 scale; Cal-A sitting averages 238.5-247.5; Cal-B 306.9-315.2 (private-heavy population scores higher) - plausible and consistent with published national results",
    },
    "transition_capacity_2026_11_01": {
        "method": "probe_transitions.py - joins the per-school aggregates for adjacent sittings (n>=10 both sides); transition_stats.json retained",
        "calendario_A": "2014->15: n_both 9,925, decline 52.42% (>=5pt 31.98%, >=10pt 16.08%); 2015->16: 9,883, 20.66% (9.87%, 4.45%), mean school delta +8.35; 2016->17: 9,092, 62.54% (42.23%, 24.01%), delta -2.97; 2019->20: 9,091, 51.04% (33.55%, 19.69%), delta -0.24. Both classes present in all four; only four transitions exist on the anonymous channel (2018/2021 school-years absent).",
        "calendario_B": "2015->16: 289 schools, decline 34.26%; 2016->17: 290, 77.24%; 2017->18: 293, 33.79%; 2018->19: 304, 49.34%; 2019->20: 283, 76.68%; 2020->21: 288, 37.85%; 2021->22: 308, 48.38%. Complete consecutive series; small population.",
        "identity_stability": "COLE_CODIGO_ICFES joins cleanly across adjacent sittings (9,025-10,952 of ~11.9-13.7k schools) and across datasets (the 2019->20 transition joins kgxf-xxbe 20194 to rnvb-vnyh 20202 with sensible deltas); school-code changes/renumbering across 11 years must be checked at construction (known risk, not measured).",
    },
    "row_model_2026_11_01": {
        "unit": "one row per (student, sitting); ESTU_CONSECUTIVO is the unique examinee-sitting id and embeds the period code (SB1120194..., SB1120224..., SB1120201...)",
        "duplication": "periodo 20194: 1,096,524 rows vs 546,211 distinct consecutivos (SoQL count(distinct)) - the 2019-2 sitting is loaded twice; periodo 20224 sample shows no systematic duplication (1,000/1,000 distinct); 20172 sample 995/1,000 (rare genuine repeats)",
        "consent_column": "ESTU_ESTADOINVESTIGACION measured values on 20224: 'PUBLICAR' 1,065,436, 'VALIDEZ OFICINA JURIDICA' 452 - publication-consent status governed by ICFES, rows shipped are the publisher's own cleared-for-publication release",
    },
    "timing_calendar_2026_11_01": {
        "calendario_A_2025": "exam applied Sunday 2025-08-10 (reprogramed 2025-08-31 for some municipalities); individual results published Friday 2025-10-10 (official calendar PDFs 2025_Calendario11A_V01/V03)",
        "calendario_B": "2025: exam 2025-04-06 (moved from 2025-03-23), results 2025-06-06; 2026: exam 2026-03-15, results 2026-05-15 (official PDFs/news)",
        "microdata_lag": "open microdata lags the results by months-to-a-year (measured: unified table rowsUpdatedAt 2023-08-23 with data through the 2022 school-year; per-year 2020 datasets createdAt 2021-03-15) - the reason the panel is recorded as current-vintage retrospective",
    },
    "extraction_cost_2026_11_01": {
        "discovery_probes": "~40 anonymous HTTPS GETs to datos.gov.co (view metadata 5-100 KB each; SoQL aggregates ~9 s per query, ~8 MB total); machine class: hosted coordinator (4 vCPU, 1.9 GiB)",
        "construction_scale": "unified table = 7,109,704 rows x 51 columns (bulk CSV export measured streaming, Content-Length 0; estimated >1.5 GB CSV) + rnvb-vnyh 504,872 x 81 - worker-class harvest, never coordinator; note the Socrata legacy export endpoint carries Deprecation/Sunset headers (Sunset: 2026-12-22, support link 43491231777047) so construction should use the resource API with $limit paging (SoQL count(distinct) and group-by measured working) or the new export path; DataIcfes period files (registration channel) are pipe-delimited .txt per sitting per the publisher FAQ",
    },
}
r["review"] = (
    "Five contracts reconciled against recorded evidence. (1) REDISTRIBUTION: supported for the anonymous "
    "channel - CC BY-SA 4.0 (licenceId CC_40_BY_SA) on the publisher's own official datasets with ICFES "
    "attribution (class B; attribution + share-alike carried into LICENSE.md); UNRESOLVED for the "
    "registration-gated DataIcfes bytes that the missing school-years (2018, 2021) and fresh tail (2023, "
    "2024) would come from - terms unread, no grant assumed. (2) TIMING: supported - the instant is the "
    "publisher's own dated results-publication calendar (worked dated example 2025-10-10 COT; target window "
    "~11-13 months after the instant, no part precedes it), with the current-vintage retrospective posture "
    "recorded explicitly (open microdata lags the instant by months-to-a-year; an operational system would "
    "have used the same-day aggregate reports) and the equating year-shift caveat recorded for the label "
    "definition. (3) TARGET: supported - label from the next school-year's published sitting aggregate; "
    "source column excludable by shipping only sittings <= T; eligibility from information at the instant; "
    "school non-persistence (no T+1 sitting) is observed absence, excluded and to be quantified at "
    "construction. (4) SPLIT CAPACITY: UNRESOLVED - the decisive blocker: the anonymous channel yields only "
    "4 Cal-A transitions (2018-2/2021-2 absent from every published open copy, measured; third-party guide "
    "independently states the same), which cannot fill three disjoint windows; the complete Cal-B fallback "
    "(7 transitions, 283-308 schools) is viable but ~20x smaller and population-narrow - an explicit "
    "redesign decision, not a silent one; the publisher's own renovated-platform inventory claims Saber 11 "
    "1996-2024, and one bounded registration+listing probe settles either the full 2014-2024 Cal-A panel "
    "(10-11 transitions) or the fallback/park decision. (5) NOT A MIRROR: supported - mechanical novelty "
    "check recorded verdict 'differentiated' (HF/zenodo/arxiv queries in novelty_check); published Saber 11 "
    "ML work is student-level cross-sectional same-exam prediction (CRISP-DM Saber 11 models; Saber Pro "
    "level prediction from Saber 11; a linked Saber11/SaberPro Mendeley dataset; a Kaggle microdata mirror) "
    "- none ships a school-aggregate next-school-year outcome task with temporal splits; nearest bench "
    "sibling ofsted-childrens-home-next-rating is a regulatory inspection rating (different population, "
    "label and instant). Conclusion: a promising lead one bounded probe from a ready/drop decision; kept "
    "investigating - split capacity must not be assumed from an inventory image."
)
r["next_action"] = (
    "Resolve the one decisive uncertainty: whether the renovated DataIcfes repository (registration via the "
    "public Microsoft Forms link at icfes.gov.co/investigaciones/data-icfes, access link auto-emailed to the "
    "registrant per the IADB-documented process - requires an inbox this environment does not have, so the "
    "operator or a worker with an operator-provided contact completes it) contains student-level Saber 11 "
    "results for the Calendario A school-years 2018, 2021, 2023 and 2024 (and reads the DataIcfes terms for "
    "licence classification of those bytes). ACCEPTANCE CRITERIA: (a) if all four school-years are present "
    "at student level with PUNT_GLOBAL and the terms permit redistribution of derived rows (class A/B): "
    "advance to construction readiness - panel = Cal-A school-years 2014-2024 (dedupe 20194 by "
    "ESTU_CONSECUTIVO), one worker pass to compute full-panel split counts per window (>=2 transitions per "
    "window, both classes measured present), then the standing order construction -> full-worker "
    "qualification -> exact-byte acceptance -> reference scoring; (b) if 2018-2 or 2021-2 are absent from "
    "DataIcfes too: decide explicitly between the Calendario-B redesign (complete 2015-2022 series, 7 "
    "transitions, ~300 schools - utility and population narrowness to be weighed against the education gap "
    "on the bench) or PARK with reopening trigger 'ICFES publishes the missing Cal-A school-years or "
    "2023+ sittings on an anonymous channel'; (c) if DataIcfes terms do not permit redistribution: the "
    "buildable panel is the anonymous-channel years only -> split capacity fails -> park with the same "
    "trigger. Cross-checks at construction: per-school means against ICFES's own aggregate reports "
    "('Reportes de Resultados Agregados'/'Clasificacion de Planteles') for at least one sitting, and the "
    "label-definition decision (margin vs percentile-rank) made against the recorded equating-shift "
    "evidence."
)
r["novelty_note"] = None
json.dump(r, REC.open("w"), indent=1, ensure_ascii=False)
print("record written:", REC)
print("status:", r["status"], "| licence_class:", r["licence_class"])
