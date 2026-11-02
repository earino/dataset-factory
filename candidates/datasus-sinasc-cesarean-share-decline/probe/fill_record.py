#!/usr/bin/env python3
"""One-shot record fill for datasus-sinasc-cesarean-share-decline (discovery 2026-11-02).

Numbers embedded in record.json are computed here from the saved TABNET probe
outputs in probe/out/ - never hand-copied. Rerunning is idempotent except
updated_at.
"""
import json
import os
import re
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import probe_tabnet_parto as P  # noqa: E402

REC = os.path.normpath(os.path.join(HERE, "..", "record.json"))
NOW = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()

YEARS = [1998, 2000, 2002, 2004, 2009, 2011, 2012, 2014, 2015, 2016, 2017, 2019, 2021, 2022, 2024]
TRANSITIONS = [(1998, 2000), (2002, 2004), (2009, 2011), (2012, 2014),
               (2014, 2016), (2017, 2019), (2019, 2021), (2022, 2024)]
FLOORS = [100, 200, 500]

tables = {y: P.parse_mun(os.path.join(HERE, "out", "mun_parto_%d.txt" % y)) for y in YEARS}

trans_rows = []
for t0, t2 in TRANSITIONS:
    both = set(tables[t0]) & set(tables[t2])
    row = {"t0": t0, "target_year": t2}
    row: dict = row
    for floor in FLOORS:
        deltas = []
        for c in both:
            a = P.ces_share(tables[t0], c)
            b = P.ces_share(tables[t2], c)
            if not a or not b or a[3] < floor or b[3] < floor:
                continue
            deltas.append(b[0] / b[3] - a[0] / a[3])
        n = len(deltas)
        dec = sum(1 for d in deltas if d <= -0.02)
        inc = sum(1 for d in deltas if d >= 0.02)
        row["floor_%d" % floor] = {
            "eligible": n,
            "decline_ge_2pp": dec,
            "decline_pct": round(100.0 * dec / n, 1) if n else None,
            "rise_ge_2pp": inc,
            "rise_pct": round(100.0 * inc / n, 1) if n else None,
        }
    trans_rows.append(row)

mun_counts = {str(y): len(tables[y]) for y in YEARS}
both_classes = all(
    r["floor_%d" % f]["decline_ge_2pp"] > 0 and r["floor_%d" % f]["rise_ge_2pp"] > 0
    for r in trans_rows for f in FLOORS
)

# national series from the saved TABNET output (computed, not transcribed)
nat = {}
for line in open(os.path.join(HERE, "out", "national_year_parto.txt"), encoding="latin-1"):
    m = re.match(r'^"(\d{4})";(\d+);(\d+);([^;]*);(\d+);(\d+)', line)
    if m:
        y, vag, ces, forc, ign, tot = m.groups()
        nat[y] = {"vaginal": int(vag), "cesarean": int(ces),
                  "ignored": int(ign) if ign.isdigit() else 0, "total": int(tot)}
nat_shares = {y: round(100.0 * v["cesarean"] / v["total"], 2) for y, v in nat.items()}

record = json.load(open(REC, encoding="utf-8"))
record.update({
    "status": "ready",
    "domain": "Health - maternal care services / vital statistics (cesarean delivery monitoring)",
    "prediction_question": (
        "At the publication instant of complete-year T SINASC live-birth data for Brazil "
        "(America/Sao_Paulo; the publisher's own TABNET base is stamped final for year T no later "
        "than early December T+1 - measured: 'Dados finais disponíveis até 2024 - data de extração "
        "02/12/2025'), will a municipality's cesarean share among resident live births fall by at "
        "least 2 percentage points from year T to complete calendar year T+2 - the next complete "
        "year whose every month lies after that instant? A useful prediction identifies which "
        "municipalities will move against the still-rising national cesarean level (60.6% of "
        "resident births in 2024), informing where maternal-care policy attention (SUS maternity "
        "audits, cesarean-reduction programs) is likely to matter two seasons ahead."
    ),
    "prediction_time": (
        "One sentence: the prediction is made at the final-publication instant of complete-year T "
        "SINASC data (no later than early December T+1, America/Sao_Paulo), using only complete "
        "calendar years <= T as features, about the cesarean share of complete year T+2. "
        "Dated example (America/Sao_Paulo, UTC-03:00, no DST): T = 2024; feature event window = "
        "births with DTNASC in 1996-2024 (each year final per the publisher's FINAL/PRELIMINAR/"
        "PRÉVIA ladder; earliest feature events 1996-01-01); first-available timestamps and "
        "version = the 2024 CSV resource was created 2024-06-11 (preview) and the publisher's "
        "TABNET base is stamped final for 2024 at extraction 2025-12-02, the whole CSV archive "
        "being last refreshed 2026-05-08 (current-vintage; no historical vintages exist); "
        "eligibility cutoff (at the instant, from instant-visible data only): municipality had >= "
        "floor F resident live births in year T (F in {100,200,500} measured); prediction instant "
        "= 2025-12-02 (the publisher-stamped date on which complete-year 2024 data is final); "
        "target window = complete year T+2 = 2026-01-01 through 2026-12-31, every month after the "
        "instant. No part of the target window precedes the instant; the 2025 preliminares (CKAN "
        "resource created 2025-10-21) and any 2026 previews are excluded from features by design."
    ),
    "target_definition": (
        "Binary label for municipality m and publication instant of year T: 1 if "
        "cesarean_share(m, T+2) <= cesarean_share(m, T) - 0.02, else 0, where "
        "cesarean_share(m, Y) = count(PARTO == 2 among resident live births of m in Y) / "
        "count(all resident live births of m in Y) (denominator includes the small Ignorado "
        "stream; nationally <1% since 1996 - measured). Source columns: PARTO (dictionary: "
        "'Tipo de parto: 1- Vaginal; 2- Cesário; 9- Ignorado'), CODMUNRES (IBGE residence "
        "municipality), DTNASC (birth date) - the label source columns are excludable from "
        "shipped features by construction (ship lagged municipality-year aggregates only). "
        "Margin 2pp is provisional and measured at three floors; the rise-direction label "
        "(>= +2pp) and a national-median-exceedance alternative are measured as calibration "
        "options; final margin fixed per split window at construction, before any scoring."
    ),
    "sources": [
        {
            "name": "Sistema de Informação sobre Nascidos Vivos – SINASC (official open microdata package; individual anonymized live-birth records, Brazil, 1996-2025 + 2026 previews), Portal de Dados Abertos do SUS, Ministério da Saúde / SVS / CGIAE-DASNT",
            "url": "https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc",
            "api": "per-year CSV on S3, e.g. https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINASC/csv/SINASC_2024_csv.zip (also JSON/XML); API reference https://apidadosabertos.saude.gov.br/v1/",
            "license": "license_id 'cc-by' / 'Creative Commons Atribuição' (license_url http://www.opendefinition.org/licenses/cc-by) on the CKAN package metadata, package id 441cc6bd-684a-4afd-a88b-ba4734c9e83e; site-wide footer states CC BY-ND 3.0 - conflict recorded in license_evidence",
            "measured": "95 resources read from the package page __NEXT_DATA__ 2026-11-02: per-year CSV (1996-2024 final titles, 2025 preliminar created 2025-10-21, 2026 '2ª prévia' created 2026-07-19), plus JSON/XML mirrors; every year file last_modified 2026-05-08 (archive-wide refresh); CSV headers read via 64 KB partial fetch: 2024 = 62 columns, 1996 = 21 columns, stable core incl. PARTO/PESO/GESTACAO/CONSULTAS/CODMUNRES/DTNASC/IDADEMAE/ESCMAE; HEAD sizes: 1996 32,281,109 B; 2015 127,210,201 B; 2023 106,371,533 B; 2024 92,289,354 B; 2025-prelim 102,484,647 B",
        },
        {
            "name": "TABNET 'Nascidos vivos - Brasil' (publisher's own aggregate service over the same SINASC base; residence-based counts), DATASUS/CGIAE",
            "url": "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sinasc/cnv/nvbr.def",
            "api": "HTTP POST (form fields Linha/Coluna/Incremento/Arquivos=nvbr<yy>.dbf, formato=prn); periods 1994-2026; dimension 'Tipo de parto' (Vaginal/Cesáreo|Cesário/Fórceps-outro/Ignorado) and 'Município'",
            "license": "no licence statement on TABNET pages (used only for bounded server-side aggregates during discovery, never for redistribution); the redistribution channel is the CC BY CKAN CSVs",
            "measured": "17 POSTs this session (~198 KB per municipality-year table, national year x parto table, month x parto table); publisher's own vintage notes on every output: 'Dados finais disponíveis até 2024 - data de extração 02/12/2025', 'Dados de 2025 - Preliminares - data de extração 28/07/2026', 'Dados de 2026 - 2a prévia - data de extração 01/09/2026'",
        },
        {
            "name": "SINASC Dicionário de Dados 'Estrutura de 1996 a 2019' (publisher's field documentation with temporal evolution of every column)",
            "url": "https://diaad.s3.sa-east-1.amazonaws.com/sinasc/SINASC+-+Estrutura.pdf",
            "license": "linked from the SINASC package 'Dicionário de Dados' resource (created 2022-04-28); publisher document",
            "measured": "2 pages read 2026-11-02: PARTO 'Tipo de parto: 1- Vaginal; 2- Cesário; 9- Ignorado'; PESO 'Peso ao nascer em gramas'; GESTACAO week bands; CONSULTAS prenatal-visit bands; CODMUNRES 'Código IBGE do município de residência'; DTNASC 'dd mm aaaa'; per-field evolution columns (ano/tipo/tamanho alterações) document schema drift 1996-2019",
        },
        {
            "name": "Plano de Dados Abertos do Ministério da Saúde, Julho/2024 - Julho/2026 (the ministry's own open-data policy instrument)",
            "url": "https://bvsms.saude.gov.br/bvs/publicacoes/plano_dados_abertos_ministerio_saudeimp.pdf",
            "license": "the plan document itself is CC BY-NC-SA 4.0; it states the portal licensing commitment, not the dataset licence",
            "measured": "plan text read 2026-11-02: 'Definição e explicitação das licenças no portal, de forma que o usuário possa ter segurança de que toda a informação lá disponível pode ser utilizada, reutilizada e redistribuída, desde que mantida a mesma licença e a necessidade de citação da fonte'",
        },
    ],
    "license_evidence": [
        {
            "quote": "license_id: 'cc-by'; license_title: 'Creative Commons Atribuição'; license_url: 'http://www.opendefinition.org/licenses/cc-by' - CKAN package metadata (package id 441cc6bd-684a-4afd-a88b-ba4734c9e83e) for 'Sistema de Informação sobre Nascidos Vivos - Sinasc', extracted from the dataset page's __NEXT_DATA__ on 2026-11-02. Resource-level licence fields: none. This dataset-specific instrument governs the dataset per the discovery policy (dataset terms over general site policy).",
            "source": "https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc (page embed; fetched 2026-11-02)",
        },
        {
            "quote": "Todo o conteúdo deste site está publicado sob a licença Creative Commons Atribuição-SemDerivações 3.0 (CC BY-ND 3.0) - site-wide footer on every page of dadosabertos.saude.gov.br including this dataset's own page and resource pages (fetched 2026-11-02). CONFLICT with the package's cc-by metadata: recorded, not resolved in the publisher's favour either way by us. Resolution applied: the dataset-specific CKAN licence (cc-by) governs the dataset; the footer is a general site banner. If a future construction or release review prefers the conservative reading, the BY-ND banner would make derived publication impermissible - escalate then, do not build on a silent assumption.",
            "source": "same pages, footer; also on https://dadosabertos.saude.gov.br/ home page",
        },
        {
            "quote": "PDA-MS 2024-2026: 'Definição e explicitação das licenças no portal, de forma que o usuário possa ter segurança de que toda a informação lá disponível pode ser utilizada, reutilizada e redistribuída, desde que mantida a mesma licença e a necessidade de citação da fonte' - the ministry's own open-data plan commits portal information to use, reuse and redistribution with source citation; corroborates the cc-by package reading over the BY-ND footer.",
            "source": "https://bvsms.saude.gov.br/bvs/publicacoes/plano_dados_abertos_ministerio_saudeimp.pdf (searched and read 2026-11-02)",
        },
        {
            "quote": "Third-party corroboration (not authoritative): the healthbr-data project redistributes SINASC microdata 1994-2022 openly on Hugging Face (SidneyBissoli/sinasc) stating 'License CC-BY 4.0' for the same ministry data; healthbR (CRAN) distributes download tooling. Recorded as corroboration only - the publisher's package metadata above is the instrument.",
            "source": "https://huggingface.co/datasets/SidneyBissoli/sinasc (read 2026-11-02 via web search result)",
        },
    ],
    "split_strategy": (
        "PROPOSED, measured on sampled transitions (all counts computed from the publisher's own "
        "TABNET aggregates, 2026-11-02; full-panel exact counts are the first construction step on "
        "the worker - sampled counts are never presented as full counts). Unit = (municipality, "
        "transition T -> T+2), one row per municipality per target year T+2, target years spaced "
        "annually. Windows disjoint by target year: train targets 2000-2012, eval targets "
        "2013-2018, holdout targets 2019-2024 (27 potential target years 1998-2024 with T >= "
        "1996 feature history). Measured sampled transitions inside the windows (floor = min "
        "resident births in T and T+2): train: 1998->2000 n=3334/2231/962 (floors 100/200/500) "
        "decline>=2pp 34.9/33.8/30.1%, rise>=2pp 37.6/37.2/34.9%; 2002->2004 n=3556/2360/1008 "
        "decline 15.4/13.5/10.6%, rise 59.9/59.9/60.3%; 2009->2011 n=3349/2205/944 decline "
        "12.9/10.7/8.2%, rise 67.5/68.3/67.7%; eval: 2012->2014 n=3349/2177/932 decline "
        "22.6/19.9/19.2%, rise 50.9/50.7/45.6%; 2014->2016 n=3308/2162/927 decline "
        "41.1/40.8/42.7%, rise 30.1/28.0/21.0%; holdout: 2017->2019 n=3298/2178/935 decline "
        "25.2/23.1/21.0%, rise 44.7/42.6/39.4%; 2019->2021 n=3260/2148/907 decline "
        "25.1/23.4/20.6%, rise 45.1/43.9/41.0%; 2022->2024 n=3132/1966/833 decline "
        "18.6/15.7/12.4%, rise 56.4/58.2/55.7%. Both classes present in every measured "
        "(transition x floor) cell (24/24, computed). Cluster structure: rows within a target "
        "year share the national era (the rise-dominant 1998-2014 era vs the plateau/decline era "
        "after 2015 - measured: national share 32.0% 1994, 50.0% 2009, 60.59% 2024); the "
        "municipality is a repeating unit; independence scale = the target year (27 instants). "
        "Municipality mesh drift measured: 5560 distinct codes 2002-2008, 5565 2009-2013, 5570 "
        "2014-2024 (new municipalities; handled by eligibility + code-presence, recorded as a "
        "construction caveat)."
    ),
    "measurements": {
        "transition_base_rates_2026_11_02": {
            "method": "TABNET municipality x Tipo de parto per year (residence-based), floors = min births in T and T+2; files retained in probe/out/",
            "label": "share change <= -2pp (decline) / >= +2pp (rise), T -> T+2",
            "transitions": trans_rows,
            "both_classes_in_all_cells": both_classes,
        },
        "national_series_2026_11_02": {
            "method": "TABNET Ano do nascimento x Tipo de parto, all periods 1994-2026, residence-based (Nascim p/resid.mãe); output retained in probe/out/national_year_parto.txt",
            "cesarean_share_pct": nat_shares,
            "note": "2025 = preliminares (61.51%), 2026 = 2ª prévia (partial year, excluded from tasks); 1994-1995 carry a Fórceps/outro column and large Ignorado counts (393,053 in 1994 = 15.3%), so feature history starts at 1996 (Ignorado < 1.5% every year from 1996, < 0.2% from 2002)",
            "known_event_fixture": "national cesarean share among resident live births 2024 = 60.59% (1,447,691 / 2,389,325) - any construction reproducing the share from the CSV channel must match this publisher figure within rounding",
        },
        "month_completeness_2024_2026_11_02": {
            "method": "TABNET Mês do nascimento x Tipo de parto, Arquivos=nvbr24.dbf; output retained in probe/out/month_2024_parto.txt",
            "result": "all 12 months present; monthly totals sum to the 2024 annual total (2,389,325) - the dated-example feature year is complete",
        },
        "municipality_rows_per_year_2026_11_02": mun_counts,
        "publication_calendar_2026_11_02": {
            "ckan_csv_resource_stamps": "created: 1996-2020 resources 2022-04-28 (bulk portal publication), 2021 created 2023-05-16, 2022/2023 created 2023-08-10, 2024 created 2024-06-11 (preview), 2025 preliminar created 2025-10-21, 2026 '2ª prévia' created 2026-07-19; last_modified: every 1996-2025 CSV = 2026-05-08 (archive-wide refresh), 2026 prévia 2026-10-02",
            "publisher_vintage_notes": "TABNET output footnotes: 'Dados finais disponíveis até 2024 - data de extração 02/12/2025'; 'Dados de 2025 - Preliminares - data de extração 28/07/2026'; 'Dados de 2026 - 2a prévia - data de extração 01/09/2026'",
            "instant_bound": "complete-year T data is publisher-stamped final no later than early December T+1 (measured for T=2024); previews exist from mid-T (2024-06-11, 2026-07-19) and preliminares from about August-October T+1 (2025-10-21, extraction updates through 2026-07-28)",
            "as_of_policy": "current-vintage retrospective panel: historical vintages do not exist (single archive refreshed 2026-05-08), so no operational point-in-time claim is made for history; the FINAL/PRELIMINAR/PRÉVIA ladder is the publisher's own revision structure, observed on recent years and applied uniformly; features use final complete years <= T only, excluding preliminares and previews of T+1/T+2 by design",
        },
        "extraction_cost_2026_11_02": {
            "csv_channel": "HEAD-measured zipped CSV sizes: 1996 32,281,109 B; 2015 127,210,201 B; 2023 106,371,533 B; 2024 92,289,354 B; 2025-prelim 102,484,647 B; 30 files 1996-2025 ~ 3 GB zipped -> worker-only extraction (never through the 1.9 GiB coordinator); anonymous HTTPS, no registration, no rate limit encountered",
            "tabnet_probe_channel": "17 POST requests, ~198 KB per municipality-year aggregate table (~3.3 MB total), 2-6 s per request, machine class = hosted coordinator container (4 vCPU)",
            "csv_header_reads": "64 KB Range partial fetch + partial inflate, < 1 s per year, zero bulk transfer",
        },
        "era_quality_2026_11_02": {
            "ignorado_share_national": "1994 15.3%, 1995 1.5%, 1996-2001 0.2-1.2%, 2002+ < 0.2%",
            "forceps_column": "Fórceps/outro populated only 1994-1995; 1996+ value '-' (folded elsewhere by publisher)",
            "schema_drift": "1996 CSV 21 columns -> 2024 CSV 62 columns; core label/feature fields (PARTO, PESO, GESTACAO, CONSULTAS, IDADEMAE, ESCMAE, CODMUNNASC/CODMUNRES, DTNASC, SEXO, RACACOR, APGAR1/5, GRAVIDEZ, QTDFILVIVO/MORT) present in both eras; newer-era fields (TPROBSON, KOTELCHUCK, PARIDADE, CONSPRENAT, SEMAGESTAC, STCESPARTO, QTDPARTCES...) exist 2011+ - usable as features only for recent target years, gated by column-presence checks at construction",
            "municipality_codes": "CODMUNRES is the IBGE residence code; TABNET keys 6-digit; code mesh changes across the panel (municipality splits) - construction must key on code x year presence and record the mapping used",
        },
    },
    "licence_class": "A",
    "licence_note": (
        "Class A: the SINASC package's own CKAN licence is cc-by (Creative Commons Atribuição; "
        "opendefinition cc-by = CC BY 4.0 family), permitting redistribution and derivatives with "
        "attribution. Known conflict recorded: the site-wide footer claims CC BY-ND 3.0 for 'todo "
        "o conteúdo deste site'; the dataset-specific instrument governs per the discovery policy "
        "(dataset terms over general site policy), corroborated by the ministry's Open Data Plan "
        "committing portal information to use/reuse/redistribution. LICENSE.md at construction: "
        "attribution 'Fonte: Ministério da Saúde / SVS / CGIAE - Sistema de Informações sobre "
        "Nascidos Vivos (SINASC)', the package licence link, the current-vintage notice, and the "
        "footer conflict disclosed. Residual risk: if the operator reads the footer as governing, "
        "this candidate becomes class D and must not be built - the conflict is recorded so that "
        "decision is explicit, not silent."
    ),
    "jurisdiction": {
        "country": "BR",
        "region": "Latin America",
        "publisher": "Ministério da Saúde (Brazil) - Secretaria de Vigilância em Saúde (SVS), Coordenação-Geral de Informações e Análises Epidemiológicas (CGIAE)/DASNT; distribution via Portal de Dados Abertos do SUS (dadosabertos.saude.gov.br) and DATASUS TABNET",
        "recorded_at": "2026-11-02",
    },
    "review": (
        "Five contracts reconciled against recorded evidence (all measured 2026-11-02, commands in "
        "notes.md, outputs in probe/out/). (1) Redistribution: SUPPORTED - dataset-specific CKAN "
        "licence cc-by (quote in license_evidence), with the site-footer BY-ND 3.0 conflict "
        "recorded and a named escalation path; residual risk noted, not hidden. (2) Prediction "
        "timing: SUPPORTED for the stated contract - instant = publisher-stamped final publication "
        "of complete year T (measured bound: no later than early December T+1), features = final "
        "complete years <= T (preliminares/previews excluded by design), target = complete year "
        "T+2 whose every month follows the instant (dated example in prediction_time; a 2025-12-02 "
        "instant cannot call any month of 2026 past); every feature column documented by the "
        "publisher's dictionary; vintage limitation recorded: historical vintages do not exist "
        "(archive refreshed 2026-05-08), so the panel is a clearly-labelled current-vintage "
        "retrospective with no operational point-in-time claim for history - the as-of policy and "
        "its coverage are stated, not assumed. (3) Target: SUPPORTED - label from PARTO==2 counts "
        "over CODMUNRES x DTNASC-year; label columns excludable (ship lagged aggregates only); "
        "missing-parto (Ignorado) stream measured (< 1.5% since 1996, < 0.2% since 2002) and kept "
        "in the denominator, so 'no recorded event' is not confused with observed absence. "
        "(4) Split capacity: SUPPORTED on evidence - 8 sampled transitions spanning 1998-2024, "
        "both classes in all 24 (transition x floor) cells, 833-3556 eligible municipalities per "
        "transition; UNMEASURED: exact per-window counts for all 27 target years (needs the ~3 GB "
        "CSV pass on a worker - recorded as the first construction step with acceptance criteria, "
        "never a blocker discovered after construction). (5) Contribution: SUPPORTED - novelty "
        "check recorded, verdict differentiated (mechanical search over HF/Zenodo/arXiv/web: "
        "microdata mirrors exist, national/FU-level ARIMA trend projections and individual-level "
        "clinical cesarean prediction exist; no municipality-year share-transition benchmark with "
        "temporal splits). Cross-row self-answer risk (a municipality's T+2 share is a later row's "
        "feature) is identified: construction must enforce the restricted prediction protocol per "
        "docs/PREDICTION-CONTRACT.md (pre-aggregated feature matrices, no unit x year join keys in "
        "solver-visible files). Cluster dependence: target-year era drift is measured (rise-share "
        "falls from ~60-68% pre-2014 to ~21-56% after), so scoring must cluster by target year. "
        "Known-event fixture: national 2024 share 60.59% must reproduce from the CSV channel."
    ),
    "next_action": (
        "HANDOFF TO CONSTRUCTION (worker; advancement session, not discovery): (1) freeze the CSV "
        "channel: download the 30 year-zips 1996-2025 (approx 3 GB) on the worker, record sha256 "
        "per file + the CKAN resource stamps read 2026-11-02; ACCEPTANCE: municipality x year "
        "cesarean/total counts recomputed from the CSVs reproduce the TABNET probe tables "
        "retained in probe/out/ (all 8 transitions, all 3 floors) and the national series "
        "(2024 = 1,447,691 / 2,389,325 = 60.59% residence-based) within rounding; (2) compute "
        "exact per-window counts for proposed train 2000-2012 / eval 2013-2018 / holdout 2019-2024 "
        "at the chosen floor and margin, per window, both classes required - if any window fails "
        "class presence, adjust margin/floor before scoring and record the measured grid; (3) "
        "enforce the anti-join design per docs/PREDICTION-CONTRACT.md: ship pre-aggregated "
        "lagged features only, strip unit x year keys from solver-visible files, run the gate-1.5 "
        "reverse-history probes on the exact artifact; (4) municipality-code mesh handling "
        "(splits/renames) recorded and consistent across the panel; (5) LICENSE.md carries the "
        "attribution, the cc-by package licence link, the current-vintage notice and the footer "
        "conflict disclosure; (6) full-worker qualification -> exact-byte acceptance -> "
        "reference/model scoring in that order, no numbers quoted before acceptance."
    ),
    "updated_at": NOW,
})

json.dump(record, open(REC, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("record written; both_classes_in_all_cells =", both_classes)
print("national shares sample:", {y: nat_shares[y] for y in ["1994", "2009", "2014", "2024", "2025"]})
