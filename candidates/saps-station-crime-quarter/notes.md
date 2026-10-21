# saps-station-crime-quarter — notes

South African Police Service (SAPS) quarterly crime statistics. Opened 2026-10-21 in the
Africa discovery tick. Probes run anonymously from the coordinator; all SAPS fetches this
session required TLS verification disabled (incomplete certificate chain, measured).

## Access probes (2026-10-21)

- `https://www.saps.gov.za/` — HTTP 200 (with `--insecure`); strict TLS fails:
  `certificate verify failed: unable to get local issuer certificate`. The host serves an
  incomplete chain; browsers survive via AIA fetching, plain HTTP clients do not.
- `https://www.saps.gov.za/services/crimestats.php` — 200, 23,156 B. Download links are
  RELATIVE: `downloads/2025/2025-2026_-_2nd_Quarter_WEB.xlsx` etc. resolve under
  `/services/downloads/...`. The absolute path `/downloads/2025/...` 404s (measured).
- `https://www.saps.gov.za/services/downloads/2025/2025-2026_-_2nd_Quarter_WEB.xlsx` —
  200, 11,554,369 B, PK magic verified. 36 zip entries, 8 worksheets, 162,533 shared
  strings. Measured header row: Station, District, Province, Crime_Category, Code,
  "National contribution placement", "National count diff placement",
  "Provincial contribution placement", "Provincial count diff placement".
  Category vocabulary observed: Murder, Attempted murder, Culpable homicide, Robbery with
  aggravating circumstances, Common robbery, Public violence, Rape, Crimen injuria,
  Neglect and ill-treatment of children, Kidnapping, Abduction, Assault GBH, Common
  assault, Burglary (non-residential / residential), Theft of/from motor vehicle,
  All theft not mentioned elsewhere, Robbery of cash in transit.
- `https://www.saps.gov.za/services/older_crimestats.php` — 200; lists quarterly
  workbooks FY2019/20 through FY2024/25 plus annual files. Current-page listing continues
  FY2023-24 Q1 onward through FY2026-27 Q1 (XLSM). Release-calendar PDFs observed:
  `Pre-Release-Crime-Statistics-Release-Calendar-For-2023-2024.pdf`,
  `Postponement-of-crime-statistics-release-for-the-first-quarter-letter.pdf`
  (a calendar slip is itself evidence the cadence is real and published).

## Licence (read 2026-10-21)

- `https://www.saps.gov.za/copyright.php` — "All material on this site is subject to
  copyright." (complete copyright statement; badge-use restrictions beside it).
- `https://www.saps.gov.za/disclaimer.php` — "The sole purpose of this Web site is to
  provide information to anyone who enters the South African Police Service Web site";
  warranty disclaimer; no reuse/redistribution terms anywhere.
- No Creative Commons, no open-data licence, no portal-level fallback: `data.gov.za`
  does not resolve (DNS; `getent ahosts data.gov.za` empty - measured, see the
  za-municipal-audit-opinion notes).

## Verdict reasoning

Licence checked first per the order of work: it is a veto, and it fires. Affirmative
copyright + no reuse grant = derived station-quarter tables cannot be published without
written SAPS permission; recorded as a decision to escalate, not an assumed permission.

Secondary (recorded, not the blocker): station-quarter counts are persistence-shaped; a
level task would trail the naive no-change rule, so an unpark needs an onset/change
formulation designed in from the first probe.

Novelty was NOT checked: the licence veto precedes it. For whoever unparks: SAPS annual
statistics have circulated on Kaggle and academic repositories for years; run
check-novelty.py then.

## Cost

One quarter workbook = 11.55 MB measured. Full quarterly series FY2019/20-FY2026/27
(~28 quarters) ≈ 300 MB over ~28 requests (estimate). Cheap - access is not the problem.
