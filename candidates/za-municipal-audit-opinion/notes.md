# za-municipal-audit-opinion — notes

National Treasury Municipal Finance Data / Municipal Money (South Africa). Opened 2026-10-21
in the Africa discovery tick. All probes run anonymously from the coordinator
(scratch: `.factory/http_probe.py` and friends, session-local, deleted at session end;
nothing here needed a ticket, key or registration).

## Access probes (all 2026-10-21, HTTP 200 unless stated)

- `https://www.data.gov.za` and `https://data.gov.za` (also http): DNS resolution failure
  ("Temporary failure in name resolution"); `getent ahosts data.gov.za` returns nothing.
  The named national portal is unreachable from DNS - SAPS/StatsSA/Treasury have to be
  probed directly. Recorded as a portal-level finding, not a per-dataset one.
- `https://www.statssa.gov.za/` (also apex): resolves (45.60.123.5) but serves a 212-byte
  Incapsula bot-challenge page (`noindex,nofollow` + `/_Incapsula_Resource` script).
  Headless clients are walled; a real-browser re-read is required before any StatsSA
  licence silence is recorded. Not pursued further this session (municipaldata was live
  and richer).
- `https://www.saps.gov.za/` (see candidate saps-station-crime-quarter): 200 but the host
  presents an incomplete TLS chain ("unable to get local issuer certificate") - every probe
  of SAPS this session was run with verification disabled, and that is recorded as a
  consumer-side access property.
- `https://municipalmoney.gov.za/` 200; `/api/` returns a JSON index:
  `{"geography/geography": ..., "municipality-profile": ...}`.
  `/api/municipality-profile/` = 6,971,176 B JSON, count 292; `/api/municipality-profile/?limit=2`
  = 88,628 B saved and parsed. Indicator names include grants, capital_budget_spending,
  cash_balance, cash_coverage, current_debtors_collection_rate, current_ratio,
  expenditure breakdowns, grants totals with phases ACT/ORGB/SCHD/TRFR per year,
  income/spending adjustments, revenue sources.
- `https://municipaldata.treasury.gov.za/` 200 ("Municipal Finance Data ... National
  Treasury"); `/docs` 200 (cube list + bulk downloads); site banner: "Figures have been
  updated with the latest 2026 Q2 data. This data is in the process of being verified for
  completeness and integrity". `/terms` 200 (quoted in record.json).

## Bulk downloads (S3, anonymous, each cube has index.json with md5/sha1/sizes)

Probed via the bulk URL list extracted from `/docs`:

- `audit_opinion_facts/audit_opinion_facts_2026-07-30_11-42-36.csv` — 733,716 B,
  3,689 rows incl. header. Columns: Demarcation Code, Name, Year End, Code, Label,
  "Auditor General's Report URL". 292 demarcation codes, 14 label years 2011-2024.
- `cflow_facts_v2/cflow_facts_v2_2025__2026-07-30_14-07-55.csv` — 2,352,464 B, all rows
  length='year' (closed years collapse to annual); `_2026_` file 2,518,189 B carries the
  live year's months 1-9 plus annual rows. 257 municipalities. Duplicate column names in
  the header (Code/Label appear twice) - parse positionally.
- `incexp_facts_v2/incexp_facts_v2_2025__2026-08-05_10-30-47.csv` — 76,734,977 B,
  396,080 rows, 17 columns, all length='year'; amount types AUDA 84,696 / PAUD 87,903 /
  ORGB 37,873 / TABB 36,849 / IBY1 37,553 / IBY2 37,751 / ITY1 36,628 / ITY2 36,827.
  "All" single file = 834,044,751 B; per-year from 2018 (12,134,397 B) to 2025.
- index.json for cflow_facts_v2: "All" = 25,119,450 B, regenerated 2026-07-30_14-07-55.
- Sample AGSA report URL from the label CSV
  (`.../2010-11/01.%20Metros/CPT%20Cape%20Town/CPT%20Cape%20Town%20Audit%20report%202010-11.pdf`)
  redirects to an mfma.treasury.gov.za directory listing (HTML 200) - the deep PDF links
  in the label file are old-pathed; the label values themselves are what we use.

## Label stats (command: `python3 candidates/za-municipal-audit-opinion/probe_label_stats.py <audit_opinions.csv>`)

- Binary qualified-or-worse rate per year (outstanding excluded): 2011 53.09%, 2012 54.86%,
  2013 56.47%, 2014 46.40%, 2015 40.43%, 2016 34.98%, 2017 42.35%, 2018 51.38%,
  2019 51.53%, 2020 50.00%, 2021 39.91%, 2022 43.92%, 2023 41.70%, 2024 43.32%.
- Split windows computed from the file: train 2011-2017 1,863 rows/47.13% pos;
  eval 2018-2020 738/50.95%; holdout 2021-2024 982/42.26%.
- Persistence (last opinion predicts this year): 619/738 = 83.88% on 2018-2020;
  transitions clean->bad 69, bad->clean 50. The level label is persistence-shaped -
  hence the onset-conditioned primary formulation.

## Licence (read 2026-10-21 at https://municipaldata.treasury.gov.za/terms)

- "free to use the data ... freely and flexibly, for both commercial and non-commercial
  purposes, at no cost"; MAY "Download, copy, publish, distribute and transmit",
  "Adapt and extract"; MUST "acknowledg[e] the source of the data and the date of
  publication"; no endorsement/trademark use. Full quotes in record.json.

## Timing evidence (observed, not assumed)

- AGSA media release "Auditor-general says local government audit outcomes are not showing
  meaningful improvement" dated 27 August 2024 (FY2022-23 general report; mfma-2023.agsa.co.za/pages/media).
- "Auditor-General Tsakani Maluleke tabled the Consolidated Report on Local Government
  Audit Outcomes 2024-25 on 24 June 2026" (agsa.co.za/reports/mfma-reports).
- FY2023-24 general report: "audits ... completed by 31 January 2025 (the cut-off date for
  inclusion in this report)" (mfma-2024.agsareports.co.za/pages/overview); 41 municipalities
  (16%) received clean audits per the same page - cross-checkable against the cube's 41
  unqualified rows for year_end 2024. (The publisher's own summary product, matched.)

## Novelty searches (2026-10-21)

- Prior art found and recorded in record.json: PLOS ONE 17(3):e0261245 (2022);
  MDPI Sustainability 15(1):12 (2023); MDPI Economies 8(1):18 with Zenodo
  10.5281/zenodo.18376321 (adjacent financial-distress task). Differentiation: those are
  post-hoc same-year formulations with no published task artifact; ours is ex-ante at the
  statutory submission instant, onset-conditioned, with temporal splits and baselines.

## Quirks to carry into construction

- The label CSV's per-row AGSA report URLs are stale deep links; do not chase them for
  data, use them only as provenance.
- The cube lags AGSA tabling: year_end 2025 opinions absent from the 2026-07-30 bulk even
  though the FY2024-25 report was tabled 24 June 2026. Snapshot by checksum and state the
  max label year the artifact carries.
- incexp/cflow CSVs have duplicate column names; parse positionally.
- 2016 has 243 rows and 2011-2016 counts differ (municipal demarcation changes); the
  demarcation_changes cube exists for that reason. Disestablished codes are in the label
  file (292 codes vs 257 live municipalities).
