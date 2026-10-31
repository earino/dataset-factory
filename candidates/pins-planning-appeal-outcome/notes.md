# pins-planning-appeal-outcome — discovery notes

Probed 2026-10-31 (scheduled discovery session, UK regional focus: ONS, NHS Digital,
Defra, Environment Agency, Companies House, data.gov.uk). Publisher: Planning
Inspectorate (England, GB). Coordinator probes only; no bulk data retained
(34.5 MB of source xlsx fetched to scratch, counted, deleted).

## Source family (one GOV.UK publication, OGL v3.0)

Publication: "Planning Inspectorate Casework Database"
(https://www.gov.uk/government/publications/planning-inspectorate-appeals-database),
last updated 22 October 2026, update log documents monthly-to-quarterly publication
since 21 March 2018. Two bulk Excel files:

1. Casework_Database_-_2610.xlsx — decisions in the last 5 years.
   22,207,115 B, sha256 dff80bd0f17cbc640dc205009a9411269c8e58462b6df71af903c592af3c20fa.
   91,216 data rows, 44 columns, sheet "Data Set".
2. Older_Casework_Data_-_2610.xlsx — decisions 5-10 years ago.
   12,325,866 B, sha256 baf28d80c5cd5ad266f8a9e62c25517b2ec9d4c5d951239ab0638666bc092a4b.
   95,569 data rows, 38 columns, sheet "Older Appeals Data".

Field list with per-field data-quality grades: "Appeals Data: Data notes and guidance"
(same publication). Direct download URLs (assets.publishing.service.gov.uk, anonymous).

## Licence (read 2026-10-31)

Data notes page: "This publication is licensed under the terms of the Open Government
Licence v3.0 except where otherwise stated." OGL emblem + Crown copyright on the
publication page. licence_class A. Caveats carried into license_evidence (subjective
categorisation, between-edition revisions, decided-cases-only population, TPO valid-date
removal, inspector-name correction 2025, no challenge to decision-maker appointment).

## Probe evidence

Command (from /opt/data/cache/scratch/pins-probe, 2026-10-31):

    curl -sS -o Casework_5yr.xlsx  https://assets.publishing.service.gov.uk/media/6ad9fcc1c818345ad8aca325/Casework_Database_-_2610.xlsx
    curl -sS -o Casework_older.xlsx https://assets.publishing.service.gov.uk/media/6ad9fcd12263175ac2aca2f7/Older_Casework_Data_-_2610.xlsx
    python3 <repo>/candidates/pins-planning-appeal-outcome/probe_count.py Casework_5yr.xlsx Casework_older.xlsx

Full JSON kept at probe_results_2026-10-31.json (this directory). Key measured
results (2 GETs, 34,532,981 B, ~1.2 s download, 26-33 s stdlib parse):

- 186,785 decided cases over decision years 2016-2026 (5-yr: 91,216 / older: 95,569;
  2021 split complementary between files: 4,277 + 12,670 = 16,947, in line with
  neighbouring years - no evidence of overlap; construction must still dedup on the
  date composite because older-file reference numbers are publisher-documented as
  NOT linkable to 5-yr case numbers).
- Zero duplicate case numbers within each file; zero missing Received/Valid/Decision
  dates in both files (0/186,785 for each of the three).
- Decisions (both files): Dismissed 111,284; Allowed 49,680; intermediate/other
  vocabulary recorded (Split Decision 2,790; Unknown 5,155; Notice upheld/varied
  12,373 - enforcement-family vocabulary, out of core scope).
- Casework types: Planning Appeal 101,142; Householder (HAS) 43,991 (= s78_core
  145,133 across both files); Enforcement Notice 17,774; LDC 5,053; Listed building
  4,185; TPO 3,242; 20+ smaller types.
- Procedure: Written Representations 172,629 (92.4%); Hearing 7,526; Inquiry 4,542.
- Valid->decision lag: 74% of 5-yr cases decide in 91-365 days; received->valid lag
  85.9% within 30 days (validation is a sharp, dated instant).
- Site flags populated: Site Green Belt 89,011/91,216 (97.6%), Agricultural Holding
  64.5%, AONB 11.4%, SSSI 4.5%, Costs Applied for Indicator 22.0% (5-yr file).
- s78_core allow rate by decision year (probe family_year cross-tab): 2016 34.6%,
  2017 32.4%, 2018 31.9%, 2019 27.1%, 2020 27.0%, 2021 29.7-30.1%, 2022 29.4%,
  2023 30.5%, 2024 30.0%, 2025 31.9%, 2026(partial) 31.9%. Both classes in every
  year; no drift.

Cross-check vs publisher's own summary product: PINS Annual Report 2022-23 states
"three out of every ten appeals were allowed"; measured s78_core rates 29.0% (Planning
Appeal) and 34.3% (Householder) in the 5-yr file. Consistent.

## Dated example (real row, Casework_Database_-_2610.xlsx, sheet "Data Set")

Case 3236151, Planning Appeal, Waverley Borough Council (ONS E60000279), procedure
Hearing, development type "Minor Dwellings", appeal reason "1. Refused planning
permission". All dates Europe/London:

- LPA decision (refusal): 2019-05-24
- Received by PINS: 2019-08-29 (97 days after refusal - inside the 6-month s.78
  deadline; the 12-week householder deadline does not apply to s.78 full appeals)
- Prediction instant: 2019-09-12 (Valid Date; case start 2020-07-10 and decision
  2021-10-01 both postdate it)
- Target: Decision Date 2021-10-01, Decision "Dismissed" (negative). The whole
  target window is after the instant; the valid->decision lag of 415 days sits in
  the measured 181-365+/366+ buckets (Hearing procedure).

## Feature availability at the prediction instant (from the publisher's field docs)

In-feature (recorded at submission/registration; quality grade from data notes):
Type of Casework (Excellent), LPA Name + ONS codes (Excellent/Good), LPA Decision
Date (Good), Received/Valid Dates (Good), Procedure (Excellent), Development Type
(Subjective - recorded, noted), Appeal Type Reason (Good), Reason for the Appeal
(Good), Type-Detail (Good), Link Status/Lead Case (Good - linkage known at
registration; verify at construction), Area/Floor Space/Number of Residences
(Moderate, "if known"), site flags green belt / agricultural / listed-building
setting / conservation area / flooding / AONB / SSSI (Moderate, "if known"),
LPA Application Reference (Good), Enforcement Grounds Count/Grounds (Excellent,
selected when the appeal is raised).

Excluded as post-instant (contract, not judgment): Decision, Decision Date,
Inspector Name (allocation after validation; publisher also warns apparent
per-inspector outcome patterns are allocation artefacts), Start Date, Jurisdiction
(mutable via recovery/derecovery), Date Recovered, Date Not Recovered Or Derecovered,
Call In Date, Redetermined, Bespoke (timetable agreed after validation).
Costs Applied for Indicator: verify-at-construction (a costs application can be
lodged after validation).
Dropped as unnecessary PII from any shipped artifact: Appellant, Agent, Site Address,
Inspector Name.

## Eligibility and censoring (stated in target_definition)

The database contains decided cases only (in-progress, withdrawn and turned-away
cases are excluded by the publisher), so the labelled population is
outcome-conditioned by construction. The task is "among validated appeals that
reach a PINS decision, which succeed". Labelled population = s78_core with Decision
in {Allowed, Dismissed}; measured exclusion masses for all other outcome values are
recorded in record.json. Split/part/unknown rows are excluded, not coerced.

## Prior art (novelty verdict: differentiated, recorded 2026-10-31)

- PlanSureAI (plansureai.com/appeals): commercial appeal-decision search, 199,531
  decisions, LPA overturn-rate analytics, inspector-reasoning extraction on a
  subset. Search + descriptive stats over the same open data; no prediction
  benchmark, no splits, no scored contract.
- APE Autonomous Research, "The Inspector Lottery That Isn't: Small-Sample Bias in
  Examiner Leniency Designs Applied to England's Planning Appeals"
  (ape.socialcatalystlab.org, 2026-04-09): econometric IV study, 2,227 scraped
  appeals 2019-2023, inspector-identity extraction; no ML-ready benchmark release.
- Public-health thematic studies of small PINS appeal subsets (PMC8392781: 52
  hot-food-takeaway appeals; PMC10683341: 2016-2020 HFT appeals).
- PINS's own quarterly official statistics: aggregate counts and "% allowed" only.

Ours: the scored, temporally-split binary prediction task over the full official bulk
panel (11 decision years, ~145k s78_core rows) with the submission-time feature
contract above and a reproducible construction script. No prior ML-ready release of
this task was found (mechanical check queries recorded in record.json
novelty_check).

## Five contracts (reconciled in record.verdict)

All five supported with the evidence above; see record.json verdict.contracts.
Retrospective scope is explicit: fixed benchmark on pinned file bytes; between-edition
revision policy recorded; vintage-evidence path (web archives over the 2018+ update
log) named for any future historical-availability claim, not needed for this one.

## Handoff to construction (advancement owns)

Order: construction on a worker -> full-worker qualification -> exact-byte
acceptance -> reference/model scoring -> reporting. Baselines before comparison
figures: LPA historical allow rate (computed from decision dates strictly before
each row's validation instant), procedure/casework-type base rates, calendar-only.
Go/no-go on demonstrated headroom over the LPA-prior reference. Expected artifact
~130-145k rows x ~25 columns, ~25-40 MB CSVs.
