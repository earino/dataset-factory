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
