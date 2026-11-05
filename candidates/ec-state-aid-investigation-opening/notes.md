# ec-state-aid-investigation-opening

Opened 2026-10-28, EU/EEA regional tick. Channel discovery only at opening - no data downloaded then.

## What was probed

- data.europa.eu search for state-aid sources (2026-10-28): the EC's own register is
  republished as "EU Competition: State Aid case publications"
  (https://data.europa.eu/data/datasets/fa8d67be-d050-42a4-97ff-9e849805acf9~~1),
  JSON distribution, access rights public, created 2025-03-13, modified 2026-10-11;
  landing page https://competition-cases.ec.europa.eu/search. The publisher's
  description: records carry "standard fields such as Title; notification/registration
  date; legal basis; Aid instrument", coverage "starts in June 1993 (some cases) but
  more systematic publication began in the early 2000".
- DG COMP's own documentation (State aid Scoreboard annex, EUR-Lex CELEX:52008DC0304):
  "The Commission's State Aid Register has been online since 2001... detailed
  information on all State Aid cases which have been the object of a final Commission
  decision since 1st January 2000... updated daily."

## Probe evidence measured 2026-10-30 (committed at 5fe48f5, never entered this record until 2026-11-05)

Probe scripts (all retained in `probe/`): `sa_range_probe.py` (ranged GET sampling of
`case-data-SA.json`, 703,863,715 B, on
`compcases-open-data-portal-files-prod.s3.eu-west-1.amazonaws.com` - the full file never
transited this host), `sa_decompose.py`, `sa_exact_openings.py`, `sa_final_counts.py`,
`sa_nodec_sample.py`. Outputs: `sa_year_counts.json`, `sa_notified_split_counts.json`,
`sa_opening_cases_exact.json`.

- Population and label as measured: population = SA cases with a recorded
  `caseNotificationDate` (excludes ex-officio cases, which have no notification
  instant); label = a distinct case number carrying at least one `DecisionTypeA44`
  decision (Article 108(2) formal investigation opening), counted per case
  `caseInitiationDate` year. Publisher search API:
  `webgate.ec.europa.eu/es/search-api/rest/search?apiKey=CS_PROD_ODSE_PROD`, with
  Origin/Referer competition-cases.ec.europa.eu; bounded per-year aggregate and
  distinct-case queries (<=~40 pages of 100).
- All SA cases / opening cases by initiation year (`sa_year_counts.json`), e.g.
  1993 17/6, 2004 1601/145, 2011 1098/149, 2014 1535/84, 2019 2825/199, 2020
  4089/32, 2021 4437/18, 2022 3851/6, 2023 5041/6, 2024 5433/6, 2025 3862/8,
  2026 3106/0.
- Notified cases / opening cases by initiation year (`sa_notified_split_counts.json`),
  e.g. 2000 516/53, 2004 1444/120, 2011 1055/54, 2014 1481/31, 2015 3009/10,
  2019 2803/54, 2020 4025/10, 2021 4364/6, 2022 3749/2, 2023 4845/1, 2024 2106/0,
  2025 0/0, 2026 0/0.
- Exact distinct opening cases (`sa_opening_cases_exact.json`): TOTAL 1,083 over
  1993-2026 (2004 120, 2011 54, 2019 55, 2023 3, 2025 4, 2026 0).
- MEASURED COVERAGE CAVEAT: the notified-population filter returns 0 for 2025-2026
  although 3,862 and 3,106 SA cases are indexed for those years - notification-date
  coverage is incomplete for the newest vintage, so recent-year counts are not usable
  split evidence. The opening prevalence also collapses from ~5-8% (2000s) to ~0.3%
  (2015+) - a regime change the task definition must state.

## Licence probe 2026-11-05 (this tick; `probe/probe_licence_2026_11_05.py`)

Read-only, anonymous, bounded:

1. data.europa.eu hub record (200, 59,502 B): `licence: null` on the dataset AND on
   its single JSON distribution; downloadURL the S3 object; distribution modified
   2026-11-02.
2. competition-cases.ec.europa.eu landing page (200, 56,823 B): no legal/licence/reuse
   links in plain HTML; `/legal-notice`, `/en/legal-notice`, `/about`, `/api/config`
   all return the identical 56,823-byte SPA shell (catch-all). Inaccessible evidence,
   not proof the terms are absent - the dataset-specific notice needs a JS browser.
3. S3 HEAD: 704,703,783 B, Last-Modified 2026-11-03T03:49:43Z, no licence metadata,
   lifecycle rule DeleteOldODPLogs (x-amz-expiration 2026-12-04). Bucket listing 403.
4. The EC general legal notice says CC BY 4.0 "unless otherwise indicated" - a general
   policy page, deliberately NOT used as a dataset grant (discovery skill class-C rule).

=> licence_class C (unstated at dataset level; instrument unreadable from the vantages
used).

## Decision (2026-11-05)

parked / verdict park. Blocker: (1) dataset-specific reuse instrument unreadable;
(2) recent-vintage notification/decision coverage unmeasured and demonstrably
incomplete in the search index. Novelty sweep deferred until both resolve. Reopening:
read the portal's legal-notice/about in the supported browser; measure
notification-date coverage in the JSON dump (ranged samples) rather than the index;
then check-novelty.py, five-contract reconciliation, split re-measurement on the pinned
dump vintage (the object is regenerated, so pin its digest).
