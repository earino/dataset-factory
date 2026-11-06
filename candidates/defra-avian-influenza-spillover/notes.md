# defra-avian-influenza-spillover - discovery notes

Discovered and probed 2026-11-06 (UK-focus scheduled discovery session). All commands below
were run on the coordinator from the repo root unless a URL is given.

## The task in one sentence

At the Monday publication of APHA's weekly wild-bird HPAI findings list for ISO week t,
predict for each English county whether at least one new poultry-premises avian influenza
case will be opened during ISO week t+2 - a wild-bird-to-poultry spillover early-warning
task on open data, with control-zone preparedness and biosecurity as the decision it serves.

## Dated example (named timezone: Europe/London; machine dates UTC)

Worked end to end against the live pages on 2026-11-06:

- Feature event window: wild-bird rows with week label <= 43, i.e. the 2026 findings file as
  published Monday 26 October 2026 (page update-log entry: "26 October 2026 - Weekly update
  for Bird flu (avian influenza): cases in wild birds updated."). No row with a week label
  later than 43 is used.
- First-available timestamps/version: the week-43 state of the 2026 file; per-week vintages
  are addressed through UKGWA replay (see "Vintage evidence"), because live attachment URLs
  are current-state.
- Eligibility cutoff: every English county on the panel (county list fixed at build time;
  no outcome-conditioned county selection).
- Prediction instant: Monday 2026-10-26, taken as 23:59 Europe/London (the page records
  dates, not clock times; its atom feed is the construction-time channel for the exact
  timestamp - do not assume a clock time).
- Target start: Monday 2026-11-02 00:00 Europe/London (ISO week 45).
- Target end: Sunday 2026-11-08 23:59 Europe/London.
- Observed outcome: one premises case opened 2026-11-04 (AIV 2026/23, near Brigg,
  North Lincolnshire, Lincolnshire; H5N1; 3 km protection + 10 km surveillance zone) ->
  Lincolnshire labelled 1; every other English county-week labelled 0.
- No part of the target window precedes the instant. The week-44 report published
  2026-11-02 ("Updated the ... list with data for week 44 of 2026") falls inside the
  target window and is NOT a feature.

Why week t+2 and not t+1: the report for week t publishes on the Monday of week t+1, so a
t+1 target would include same-morning hours that precede any precisely-stated instant.
Week t+2 gives a whole-week target strictly after the instant. A t+1 target defined as
[instant, instant+7d) is constructible if the atom feed yields the publication timestamp;
that choice is construction's and must be re-stated in the evaluation contract.

## Probe 1: the target stream (live case listing)

    python3 candidates/defra-avian-influenza-spillover/probe_case_listing.py

- 7 pages, 340 entries: 339 premises cases + 1 AIPZ zone entry (the provenance mix; the
  zone entry is excluded from the target). Two title-ID generations exist: "(AIV 2026/23)"
  and 2022-era "(2022/73)" / "(SOS AIV 2022/19)"; four entries initially misclassified as
  zone entries were recovered by matching both ID forms.
- Strain mix: 334 H5N1, 1 H5N5, 4 unspecified (old-format entries).
- Per-season England cases / distinct counties / positive county-weeks:
  - 2021-22 tail: 22 / 9 / 18 (live listing reaches back only to 2022-09-03)
  - 2022-23: 162 / 36 / 93
  - 2023-24: 4 / 4 / 4
  - 2024-25: 73 / 20 / 56
  - 2025-26: 80 / 23 / 65
  - 2026-27 (in progress): 2 / 2 / 2
  - plus one legacy 2005-06 entry (outside all split windows).
- Cost: 8 requests, 1,251,470 bytes, 4.9 s.
- Parser note (recorded so nobody re-derives it): gov.uk result cards end their last
  metadata <li> with </ul> inside the card; a card regex that consumes a terminal </li>
  silently drops the last attribute ("Opened" whenever "Closed" is absent). The shipped
  regex stops at a lookahead instead.

## Probe 2: the feature stream (wild-bird findings)

    python3 candidates/defra-avian-influenza-spillover/probe_wildbirds_counts.py

Per-year files (all fetched, all small):

| year | rows | locations/counties | positive birds | schema |
| --- | --- | --- | --- | --- |
| 2016-17 | 67 | 17 | 45 | "Location (county)" |
| 2018 | 63 | 15 | 101 | "Location (county)" |
| 2020 | 166 | 37 | 277 | "Location (county)" |
| 2021 | 258 | 120 | 459 | "Location" (district/council grain) |
| 2022 | 825 | 283 | 1,876 | "Location" (district/council grain) |
| 2023 | 458 | 93 | (count column "Total") | county-normalized |
| 2025 | 1,203 | parsed from XLSX (openpyxl 3.1.5) | - | county-normalized |
| 2026 | 309 | 81 | 348 | county-normalized (Week (Year), District, County, Country, Species, Latin, Virus Isolated, Total (Positive)) |

2024/2025 attachments are XLSX (67.5 KB / 16.6 KB listed; 2025 parsed to 1,203 rows).
Schema drift and the 2021-2022 district-grain locations are construction normalization
work, not a blocker. The 2019 file (2.38 KB) exists but was not re-fetched in the final
probe run.

## Probe 3: archived vintages (the availability contract)

    python3 candidates/defra-avian-influenza-spillover/probe_archived_listings.py

- UKGWA replay: 12/12 evenly spaced probe timestamps 2021-06..2026-02 for the findings
  publication page resolved via HTTP 307 to a real snapshot (~monthly cadence).
- Dated vintage example: snapshot 20221114192220 of the findings page links and serves
  `ai-findings-week-2022-44.csv` = 570 rows, weeks 1-44 only; the current 2022 file has
  825 rows. A row's week label is its availability week at snapshot time.
- Live attachment URLs are current-state: the search-indexed 2025 files
  "...findings_2025_-_Week_8.xlsx" and "...findings_2025_-_Week_23.xlsx" served
  byte-identical 69,118-byte current-year files when fetched 2026-11-06. Vintages live in
  UKGWA captures, not at the publisher's URLs.
- Case-listing snapshots resolved: 20221027174930 (97 all-disease entries), 20221215212127
  (157), 20240105181542 (192; the publisher's own "previous cases" pointer on the latest
  situation page). Union across snapshots: 187 bird-flu premises entries, consistent with
  the live listing. The archived listing also starts at 2022-08-27 - the 2021-22 season
  bulk (cases opened Oct 2021 - Aug 2022) was never carried by this listing.
- 2021-22 bulk channel (optional construction input): APHA's 2021-22 season epidemiology
  report annex tables (gov.uk publication "reports relating to recent cases of avian
  influenza"), ~1-2 PDFs; treat as a retrospective source and document it as such, or
  restrict train to the measured 22-case tail.
- Residual assumption (stated, not proven universal): no retro-addition of rows to past
  weeks between UKGWA captures; verify 3+ additional snapshot attachments at construction
  or declare the assumption in quality.json.evaluation_contract.

## Cross-checks against the publisher's own summary products

- Season table on "latest situation in England" (read 2026-11-06): UK HPAI cases
  2021-22 158, 2022-23 207, 2023-24 6, 2024-25 82, 2025-26 100. Measured England counts
  (22-tail / 162 / 4 / 73 / 80) are England-majority subsets - consistent.
- 2026-27 to date: the latest-situation page names Belford, Northumberland (2026-10-19)
  and Brigg, North Lincolnshire (2026-11-04); the measured listing shows exactly these 2
  England cases. Known-event fixtures for any future threshold: the 2022-23 record
  epizootic (162 measured England premises cases) and the 2023-24 near-quiet season
  (4 cases) bound the label's regime range.

## Licence

- GOV.UK footer on both source pages (raw HTML, read 2026-11-06): "All content is
  available under the Open Government Licence v3.0, except where otherwise stated."
  No dataset-specific term overrides it on either page. Class A.
- Shipped rows contain no personal data: species/county/counts and county-date-strain
  abstractions of case entries the publisher already publishes at "near <town>" grain.

## What was considered and not pursued this session (same region)

- Companies House + The Gazette as an exit-label path for the parked companies-house
  candidate: Gazette content is OGL v3 (class A) but the structured Companies longitudinal
  bulk datasets are charged; free channels exist (notice search, SPARQL, FTP RDF dumps).
  It does not unlock a historical build (no historical Companies House feature vintages;
  strike-off is near-mechanical in the overdue flags) - recorded on that candidate.
- EA AIMS flood-defence asset condition (new candidate ea-flood-defence-asset-condition):
  OGL, per-asset condition fields confirmed, 141,416 assets, but current-state only ->
  parked on the forward-collection prerequisite.
- ONS and NHS Digital: recorded verdicts already cover them (aggregate-grain publisher;
  NHS performance streams are the dropped nhs-ae family; HES microdata is gated).
