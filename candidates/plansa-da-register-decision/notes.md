# plansa-da-register-decision — probe log

All probes 2026-11-06 (UTC). Browser probes ran in the supported browser session
(`oceania-discovery`); plan.sa.gov.au answers 403 to plain curl, so every register
fact below was read in the real browser. Counts are the publisher's own displayed
totals. Nothing here is a locally derived base rate yet — no labelled rows were
extracted (that is construction, owned by advancement on a worker).

## 1. How the source was found

data.gov.au catalogue sweep for development-application registers, anonymous
CKAN `package_search` (script retained at `probe/ckan_da_catalogue.py`):

    python3 probe/ckan_da_catalogue.py
    # base: https://data.gov.au/data/api/3/action/package_search
    # queries: "development applications", "resource consents",
    #          "port state control detention", "building permit"

Hits and their licence states (catalogue `license_id`/`license_title`):

- `development-application-public-register` (SA Dept for Housing and Urban
  Development, data.gov.au id 10decd54) — cc-by / Creative Commons Attribution
  3.0 Australia. Harvested from
  https://data.sa.gov.au/data/dataset/development-application-public-register.
  Its notes describe the OLD register (decision authority DAC/Minister/Governor,
  lodged since 2010) and link the retired host `www.saplanningportal.sa.gov.au`.
- City of Adelaide `current-development-applications` — cc-by, but "will cease
  to be updated after 2021-03-19" (processing moved to the state ePlanning
  system). Dead source.
- City of Playford `development-application-register` — cc-by, per-year CSVs
  2013→, statutory register published per Regulation 98 of the Development
  Regulations 2008. Viable small fallback, not probed further.
- ACT `actgov-completed-development-applications` (ACTmapi ArcGIS Hub) —
  licence "Other", unverified.
- Moreton Bay `development-applications1` (ArcGIS Hub, weekly updates since
  2016-02-01) — licence "Other", unverified.
- Victorian `building-permit-activity-data-YYYY` (Building and Plumbing
  Commission, formerly VBA) — cc-by, per-year XLSB 2009→June 2026, ">40 pieces
  of information per record" per permit — but permits issued, no decision
  outcome, so it carries no target.

`package_show` on data.gov.au 302s to an HTML page; `package_search` works and
returns full package dicts. data.sa.gov.au `package_show` works directly:

    curl -s "https://data.sa.gov.au/data/api/3/action/package_show?id=development-application-public-register"
    # -> license_id "cc-by", license_title "Creative Commons Attribution",
    #    resources: HTML link to www.saplanningportal.sa.gov.au/public_register (dead host)

## 2. Live register (the actual source)

- Old host `www.saplanningportal.sa.gov.au`: DNS fails; bare domain resolves
  (43.245.43.80) but the connection fails. `plan.sa.gov.au` serves the current
  portal; curl gets 403 on every path; the supported browser opens it.
- Landing page: https://plan.sa.gov.au/development_application_register —
  "The Development Application Register allows you to search, track, and access
  publicly available information about development applications lodged in South
  Australia." and "If your application was lodged before 31 July 2020, it might
  be published in a council's register instead."
- Footer (licence instrument, quoted verbatim):
  "This work is licensed under a Creative Commons Attribution 3.0 Australia
  Licence" → http://creativecommons.org/licenses/by/3.0/au/deed.en
- "Search all applications" = anchor `#showall` on the same page; results are
  server-rendered on the first load, then bootstrap-table AJAX for form
  submissions.

### 2.1 Measured totals (register's own count text)

Form-driven searches (set `select[name=Status]`, `requestSubmit()`, read
"We've found N development applications"):

| Query | Count |
| --- | --- |
| default (search all) | 299,858 |
| Status=Decision Made | 260,174 |
| Status=Under Assessment | 27,083 |
| Status=Lapsed | 338 |
| Status=Withdrawn | 10,538 |
| Status=Cancelled | 1,725 |
| Lodged 01/01/2026–06/11/2026 (status All) | 17,733 |

Sum of the five statuses = 299,858, consistent with the default total.
Per-year windows for 2021–2025 were NOT measured: date-window searches settle
in 30–90 s and the 2021 window did not settle within 75 s in-session; a direct
GET with only date params renders the landing page (the search must go through
the form). Worker-side probe needed for per-year counts.

### 2.2 Search/filter schema (from the form's own inputs)

`Status` (All/Under Assessment/Decision Made/Lapsed/Withdrawn/Cancelled),
`DevAuth` (Assessment Manager, Assessment Panel, Council, DAC, Governor of
South Australia, Independent Assessor, Minister, SCAP, State Planning
Commission), `LGASearch` (all SA councils, including "Council Area Not
Recorded"), `Act` (DEV/PDI), `LodgedDateStart`/`LodgedDateEnd` (dd/mm/yyyy),
`Applicant`, `AddrSearch`, `AddrSuburbSimple`, `DevNo`, `AppId`, `Vol`, `Fol`,
`SubscriptionElements` (DM/LD/TF/TA/RDT), `SortParameters`
(LodgedNew/LodgedOld/AppIdUp/AppIdDown), `perpage` (25/50/100), `page`.
List columns: Reference number, Applicant, Property address, Description,
Lodged.

### 2.3 Detail-page fields (sample 26037018, fetched 2026-11-06)

Opened via the row's `#view-26037018-DAP` anchor (rows are `tr[data-index]`
with `data-action="#view-<ID>-DAP"`; the detail renders via AJAX
"printsingleresult"). Overview/Application summary tab:

- Application ID 26037018; Lodged 5 November 2026; Application number N/A
- Applicants: Jones Lang LaSalle
- Assessment Pathway: **Accepted**; Elements: Internal fitout
- Council area: Norwood Payneham and St Peters
- Title CT 5613/456 F139146 AL66; address 192 THE PARADE NORWOOD SA 5067
- Public Notification: Not applicable; status pill: DECISION MADE

Assessment tab (this is the decision view):

    This application requires
    Building Consent
    Development Approval - Planning, Building
    Building Consent          Granted
    Development Approval - Planning, Building          Granted

=> per-consent decision TYPE is displayed. No decision DATE was displayed on
this sample; older decided applications must be probed (next_action 1) before
the latency label is confirmed derivable.

### 2.4 Status vocabulary (the register's own JS, verbatim)

Fetched in-page:
https://plan.sa.gov.au/__data/assets/js_file_folder/0019/607321/public-register.min.js?v=0.15.5
(554,758 bytes). `PRstatusObj` descriptions:

- Lodged (blue): "The application has been formally lodged by the applicant and
  is ready for assessment."
- Under Assessment (blue): "The application is currently under assessment,
  awaiting decision."
- Approved (green): "The is approved."
- Decision Made (dark): "Assessment of this application has completed and a
  decision has been made."
- Granted (green): "The is granted."
- Decision Under Appeal (dark): "The decision made on the application by the
  relevant authority is being appealed in court, and may be upheld or
  overturned."
- Cancelled (dark): "The was cancelled."
- Withdrawn (default): "The applicant has withdrawn this application from
  assessment and no decision may be made."
- Refused (orange): "This was refused."
- Rejected (orange): "This was rejected."
- Lapsed (default): "The decision made on this application has lapsed and is no
  longer valid."

### 2.5 CSV export channel (construction recipe, from the same JS)

The CSV link is built by the page as:

    endpointCSV = <defaults.url> + "/development_application_register/assets" + envFolder + "/daregisterCSV"
    payload = btoa(JSON.stringify({
      ActionType: "csv", Config: "public_register",
      DataObject: "PublicRegisterCSV",
      Params: <$("#searchform").serializeArray() minus SortBy/perpage/resultspagenumb/givehoney/ActionType>,
      SortExpression: <SortBy value>, RecordNumber: 0 }))
    url = endpointCSV + "?payload=" + payload

There is also a fields-lookup POST `{ActionType:"fields", Config:"public_register",
DataObject:<searchForm>, Params:[]}` returning select lookups, and the results
themselves render into `#app-search-results`. A synthetic payload fetch from
page context failed ("TypeError: Failed to fetch") — construction must use the
page's own handler or replicate it exactly (padding/encoding unverified). The
in-page click of "Download .CSV of results" did not deliver a file to the
browser workspace in-session; row cap and CSV columns are unmeasured
(next_action 2).

### 2.6 Timings (coordinator browser, 2026-11-06)

- Status-only search: ~3–8 s to count text; rows render shortly after.
- Date-window search (01/01/2026–06/11/2026): settled ~25–30 s.
- Date-window search (2021 full year): did not settle within 75 s.
- perpage max 100 → ~3,000 pages for the whole register if paged.

## 3. Prior-art scan (2026-11-06, web search)

Queries (paraphrased):
- `machine learning predict development application outcome "statutory timeframe" OR "planning approval" dataset benchmark`
- `"planning application" OR "development application" approval prediction model kaggle OR huggingface OR github dataset`

Findings:

- ConfidentPlanner (github.com/athuler/ConfidentPlanner): London
  approval-likelihood tool on the GLA London Planning Datahub (OGL v3);
  logistic regression + TF-IDF description embedding, AUC ≈ 0.73, trained
  2022–26, recency-weighted split. A tool + model, not a published benchmark
  with splits and a scored contract; UK jurisdiction and decision system.
- Lin et al. 2025, Sage (Transforming urban planning through machine learning):
  NLP classification of Australian planning-application descriptions into
  development categories (DeBERTa-v3, accuracy/F1 0.944); classification, not
  decision prediction; data "available on reasonable request".
- Aggregate reporting only: Victoria "66% of all applications were processed
  within the statutory timeframes in 2023-24 (84 days median)"; NSW council
  league tables; PIA Tas table of statutory vs observed timeframes per state;
  RBA/PC 2025 housing-construction-productivity paper (Table 4.1). None
  per-application, none a prediction task.
- Portfolio family: pins-planning-appeal-outcome (GB appeals — different
  instant/population), tc-gv-licence-application-outcome (operator licensing).

No ML-ready per-application DA decision or statutory-timeframe benchmark with
splits found. Novelty verdict to be recorded with scripts/check-novelty.py
once the target is fixed (next_action 5); not recorded now because the label
family is still open between latency and refusal.

## 4. NZ coverage note (this tick's regional focus)

data.govt.nz (catalogue.data.govt.nz) is bot-walled for plain HTTP
(Imperva "Pardon Our Interruption" page to curl) but opens in the supported
browser. `resource consents` search: 327 datasets, dominated by regional-council
GIS layers (Horizons 91, Environment Canterbury 86, Otago RC 33, Hawke's Bay 21,
Gisborne 18, Northland 9, Bay of Plenty 8, Ministry for the Environment 5,
Environment Southland 4); formats HTML 319 / ArcGIS REST 282 / CSV 275 / GeoJSON
272 / ZIP 272 / KML 271 / XLSX 37; licence facets ~79 CC vs 9 "Other licensing"
(most datasets carry no visible licence in the facet list). NZ council
resource-consent registers are activity permits (discharges, water takes) —
a different population from first-instance development decisions. No NZ
candidate opened this tick; existing NZ candidates (fenz-incident-data,
nz-ea-wholesale-price-exceedance) remain with their owners.

## 5. Five contracts, reconciled against the evidence

- **Redistribution: SUPPORTED.** CC BY 3.0 AU on the register page itself and on
  the data.sa.gov.au / data.gov.au catalogue records. Class A. (Coverage: the
  licence statement is on the page that serves the data.)
- **Prediction timing: PARTIAL.** Prediction instant (lodgement) and the
  lodgement-time feature set are stateable and documented by the publisher's
  own field labels; two items unresolved: whether Assessment Pathway/category
  is the at-lodgement value, and no per-application decision date observed yet.
  The register is current-state (yesterday's lodgements visible today), so a
  historical build is retrospective with an explicit as-of assumption; post-hoc
  decision changes exist (Decision Under Appeal, Lapsed).
- **Target: PARTIAL.** Decision TYPE is evidenced (Granted/Approved/Refused/
  Rejected in the register's own vocabulary and on the sample Assessment tab);
  refusal label derivable and source columns excludable. Latency label blocked
  on the decision-date probe. Withdrawn/Lapsed/Cancelled are censoring states,
  not negatives.
- **Split capacity: PARTIAL.** Volume is not in doubt (260,174 decided rows,
  2020H2→present, 17,733 lodged in 2026-to-date alone), but per-year counts and
  the label's class mix (refusal rate / within-timeframe rate) are unmeasured,
  and positives will cluster by council and season — clustered counts still to
  be recorded.
- **Not a mirror: PARTIAL.** Prior art scanned and clearly distinct at task
  level (tool/model for London approvals; aggregate league tables; AU text
  classification); the novelty verdict is deliberately not recorded until the
  target is fixed, so nothing here overclaims.

Verdict: **investigating** — a strong lead with licence, access, volume and
utility evidenced; three named measurements stand between it and `ready`.

## 6. Endpoint layer + label channel measured (2026-11-07, Oceania discovery session)

All probes read-only, in the supported browser session (plan.sa.gov.au and its
data CDN both 403 to plain curl; the browser fetches below run from page
context, `about:blank` works because the CDN answers cross-origin). No bulk
data landed on the coordinator; every number below is an aggregate printed
from in-page computations. Register grew during the session: 300,032
applications (was 299,858 on 2026-11-06); decided all-time 260,311.

### 6.1 The three machine endpoints (recipes, verified 2026-11-07)

The register is NOT just the slow HTML search. Three plain-HTTP JSON/CSV
channels exist, all driven by base64 payloads exactly as the page's own JS
builds them (`public-register.min.js` v0.15.5, `getSearchtoCSV` /
`getSearchResults` / `getSingleResult`):

1. CSV export - GET
   `https://plan.sa.gov.au/development_application_register/assets/daregisterCSV?payload=<btoa>`
   with payload `{"ActionType":"csv","Config":"public_register","DataObject":
   "PublicRegisterCSV","Params":[{name,value},...],"SortExpression":"LodgedNew",
   "RecordNumber":0}`. Columns: Unique ID, Development No, Application Status
   (coarse only), Address, Description, Lodged (m/d/yyyy), Register Code.
   NO decision date, NO Granted/Refused outcome.
2. Search - POST `https://cdn.plan.sa.gov.au/prs/fFGE56_reg8R` with
   `payload=<btoa>` body,
   `{"ActionType":"select","Config":"public_register","DataObject":
   "PublicRegisterSearch","Params":[filters,Page,PageSize],"MaxRecords":N}`.
   The response's own `Count` is UNRELIABLE (0 with rows present); the
   authoritative total is read from the row's `TotalRecords` column (field
   index resolved via `Fields.Fields[].FieldCode=="TotalRecords"`).
3. Per-application detail - POST to the same endpoint with
   `DataObject` per register code (DAP->DAPRegisterDetail, LUA/LUC->
   LandUseRegisterDetail, LDE->LandDivisionRegisterDetail, MD->
   MajorDevelopmentRegisterDetail), `Params:[{AppId},{Base:<code>}]`. The
   response has 9 named children; `DecisionDetails` carries per-consent
   rows `[CT=Decision type, DRT=Decision, DD=Decision date]`.

Date semantics: the CSV endpoint parses Lodged dates as m/d/yyyy (a
21/06/2021-21/06/2021 window returns 0 bytes; 04/01/2021-10/01/2021 returns
April-October rows). The HTML form displays dd/mm/yyyy. Construction MUST
send m/d/yyyy to the CSV endpoint and verify windows by echo.

### 6.2 THE LABEL CHANNEL EXISTS (probe A answered: both candidate A and B constructible)

Detail fetch for 6154 (LUA, 10 Milsteads Road Port Macdonnell, heritage
cottage repairs, lodged 1 Apr 2021): DecisionDetails = one consent row
"Development Approval / Granted / 30 Apr 2021". Decision dates and per-consent
outcomes ARE published per application, in machine-readable form, separate
from every lodgement-time feature field. Candidate A (statutory-timeframe
latency, lodgement->DD in days) and candidate B (refusal, DRT) are both
derivable; label sources are excludable (separate JSON child).

### 6.3 BUT the label channel degrades under sustained querying (measured)

After ~100 detail POSTs across the session (bursts of 3-7, then 16), the
SAME query that returned full DecisionDetails for 6154 began returning
hollow children (children present, FieldValues empty), and even a 30 s pause
did not restore it in-session. Early-session reads were complete and
consistent; late-session identical queries came back hollow. Trigger
undetermined (burst pacing vs backend load vs time-of-day - unmeasured).
CONSEQUENCE: the extraction must pace requests, validate every row
(re-fetch on hollow DecisionDetails), and never treat an empty read as
"no decision". Refusal prevalence therefore stayed UNMEASURED this
session: a 42-app sample across all seven years returned hollow responses
after the degradation began (batch scripts retained). This is the ONE
measurement now gating the ready verdict (see 6.6).

### 6.4 CSV export is NON-DETERMINISTIC above ~789 KB (measured, decisive for construction)

Dual-fetch of the same full-year-2020 decided window, one call, hashed
in-page: bytes1 == bytes2 == 789,151 BUT hash1 != hash2 and `t1===t2` false -
the server returns a DIFFERENT ~789,151-byte subset of the window on every
call. My parser is proven deterministic (double-parse of one response gives
identical counts: 2,287 both times). Full-year 2020 decided fetches parsed
2,287 / 3,022 / 3,052 / 4,188 / 4,349 rows across five identical calls - all
far below the backend's own count. Sub-cap windows ARE complete: Sep-2020
month (696 rows / 102 KB), Q4-2020 (1,266 rows / 299 KB), and half-month
windows 2021-2026 (478-1,944 rows / 72-294 KB) returned coherent row sets.
CONSTRUCTION RULE: enumerate via the CSV only in windows kept under ~780 KB
(month-scale), reconcile per-window counts against the search TotalRecords,
and never trust a window whose response is near the 789,151-byte signature.
Also: descriptions contain UNQUOTED newlines (e.g. 5584's summary, the
" conference" dirty keys, a 2025-09 window of 250,490 bytes with only 80
parseable rows) - CSV parsing must be quote-aware AND row-validated.

### 6.5 Population: TWO ERAS, measured from the publisher's own backend

Status-only search POSTs (TotalRecords, 2026-11-07): Act=DEV 73,464 rows;
Act=PDI 226,568 (sum 300,032 = register total). Decided rows lodged
2000-2009: 26,532; lodged 2010-2019: 36,067. So the register ingests the old
Development Act register back to at least 2000 - a DIFFERENT population
(state-referred/major development under DEV authorities), not the all-council
PDI population. The clean task frame is the PDI era (lodged >= 31 Jul 2020).
Per-year PDI-era counts (search TotalRecords, m/d/yyyy windows):

| Lodgement year | ALL | Decision Made | Under Assessment |
| --- | --- | --- | --- |
| 2020 | 5,761 | 5,235 | 252 |
| 2021 | 38,448 | 34,482 | 1,613 |
| 2022 | 40,485 | 35,782 | 2,428 |
| 2023 | 35,563 | 31,356 | 2,403 |
| 2024 | 38,982 | 34,549 | 2,862 |
| 2025 | 38,102 | 33,280 | 3,867 |
| 2026 (to date) | 34,531 | 23,028 | 11,101 |

Sum decided 2020-2026 = 198,312; the remaining ~62k decided rows are DEV-era
(62,599 measured as 26,532 + 36,067, boundary overlaps account for the ~600
difference). Register-code mix (CSV samples): 2020 LUA 736/LDE 2,649/DAP 803
in the whole-year fetch; DAP dominates 2021+ (~99%); LUC appears from 2026.
DEV-era rows would need their own DataObject/provenance treatment if ever
included; the PDI-era frame avoids it.

Status-filter validation: Status="Refused"/"Granted"/"Approved"/"Rejected"
POSTs return no TotalRecords and no rows while Status="Decision Made" returns
260,311 + rows - the coarse-status design is backend-enforced, negative
validated by a working positive control. No enumeration of refusals exists
without per-application details.

### 6.6 What still gates `ready` (reconciled five contracts)

1. Redistribution: SUPPORTED (CC BY 3.0 Australia, re-verified live on the
   register footer 2026-11-07; attribution carried verbatim at packaging).
2. Prediction timing: SUPPORTED for a current-compilation retrospective
   (lodgement instant; pathway/elements/applicants/council/description all
   documented at that instant; decision fields post-instant and excludable;
   statutory-timeframe target definition documented from PlanSA's own
   "Stages and timeframes" page: 5-95 business days by pathway, 5-day
   verification + 2-day issue, and a documented clock-SUSPENSION confounder
   for info requests - a latency label must declare it; single live
   compilation, no historical vintages claimed).
3. Target: DERIVABLE (6.2) but label-row AVAILABILITY RATE under paced
   extraction unmeasured (6.3) and refusal prevalence per window unmeasured.
4. Split capacity: rows per window measured (6.5); positives (refusals) per
   window UNMEASURED - unresolved until the paced detail pass.
5. Not a mirror: prior art unchanged (notes s3); no ML-ready per-application
   SA first-instance decision/latency benchmark found; formal verdict stays
   deferred until the label family is confirmed by the paced pass.

Next probe (discovery-owned, one session): paced detail pass (>= 1.5 s
spacing, hollow-read re-fetch, ~30 apps/window x 3 windows drawn from
month-scale CSV windows) measuring refusal prevalence + DD availability per
window; if refusals appear in all three windows, record the novelty verdict
and set ready with exact-row counts + sample-measured positives, naming the
full 260k-detail sweep as construction's first worker step.
