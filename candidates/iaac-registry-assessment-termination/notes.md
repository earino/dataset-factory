# iaac-registry-assessment-termination

Opened 2026-10-30 (Canada regional tick). Discovery only; no construction ran.
All probes below were executed 2026-10-30 from the coordinator unless noted.

## Question

Who predicts what, at which instant: for a project assessment posted to the
Canadian Impact Assessment Registry, at its registry start date, will the
assessment process terminate before any determination/decision is issued, or
run to a determination? A federal authority triaging its assessment workload
(or a consultant scoping one) could use the probability to prioritize
engagement on assessments likely to stall. The label is behavioral
(proponent withdrawal / process termination), NOT the environmental finding;
the richer finding ('likely to cause significant adverse environmental
effects') is expected to be rare - measuring its rate is a named next probe.

## Licence (checked first)

open.canada.ca CKAN package_show for f4c51eaa-a6ca-48b9-a1fc-b0651da20509
("Canadian Impact Assessment Registry - Assessment Inventory"):
license_id = ca-ogl-lgo. OGL-Canada 2.0 = class A on this bench (explicit
redistribution + derivatives with attribution). Command:

    curl -sS "https://open.canada.ca/data/api/action/package_search?q=%22Assessment%20Inventory%22&rows=5"

Resources: ESRI REST EN/FR MapServer + the registry HTML app. Package notes
quote: "The assessments layer represents all assessments undertaken under the
Impact Assessment Act, including those that continue under the provisions of
the Canadian Environmental Assessment Act, 2012... as posted on the Canadian
Impact Assessment Registry Internet site."

## Probe 1 - MapServer liveness, counts, schema

    curl "https://maps-cartes.services.geo.ca/server_serveur/rest/services/IAAC/assessment_inventory_en/MapServer?f=json"
    curl ".../MapServer/$L?f=json"                      # $L in 0,1,2
    curl ".../MapServer/$L/query?where=1%3D1&returnCountOnly=true&f=json"

Layers: 0 'Completed' count=5079, 1 'In progress' count=1173,
2 'Terminated' count=348. Total 6,600 projects. Fields per layer:
project_id, project_cat_en, project_name_en, proponent_en, province_codes,
location_en, responsible_authority_en, project_url_en, start_date,
project_state_en, location_type_en, coordinates, latitude, longitude,
updated_at, description_en, OBJECTID, Shape.

## Probe 2 - full attribute fetch (aggregate, no geometry)

Script retained at probe/iaac_layer_probe.py. Measured (2026-10-30,
coordinator): 6,600 rows, 9 requests, 1,010,024 bytes, 6.58 s.

Start-year x state histogram (starts Completed/InProg/Terminated):
2006 2/0/0, 2007 0/0/1, 2009 1/0/0, 2010 12/1/5, 2011 10/0/7, 2012 24/1/22,
2013 22/2/7, 2014 12/3/8, 2015 14/1/6, 2016 11/3/4, 2017 7/0/3, 2018 10/1/7,
2019 188/11/16, 2020 717/71/48, 2021 826/91/51, 2022 749/111/47,
2023 758/150/48, 2024 724/161/32, 2025 707/208/29, 2026 285/358/7.

Reading of the histogram (recorded as interpretation):
- Volume era is 2019+ (~750-1,000 starts/year); 2010-2018 is sparse backfill
  (~30-40/year); the IAA came into force 2019-08.
- Terminal share falls with recency (2019 7.4% -> 2026 1.1% of starts) and
  the in-progress share rises (2019 5.1% -> 2025 22.0% -> 2026 55.1%):
  recent cohorts are right-censored - a terminated label can only appear
  after the process ends, so 2024-2026 terminal counts undercount.

Category mix (top): Construction 2,593; Transport Industry 1,879; Water
Management 440; Tourism 331; Waste Management 286; Environmental Management
281; Petroleum Industry 279; Energy 149; Mining Industry 144; Agriculture 89;
Defence Industry 72; Forestry Industry 57.
Province mix (top): ON 1,322; BC 1,232; AB 1,038; QC 886; SK 566; NS 373;
MB 355; NL 306.

## Probe 3 - registry page grain (dated events)

Pages fetched 2026-10-30 via the extraction backend (sample n=4):

- proj 81027 (Terminated, non-designated on federal lands): "Latest update:
  January 18, 2022 - The assessment process has been terminated." Metadata
  block: Assessment status Terminated, Start date 2020-09-29, Authorities
  Transport Canada, Assessment type 'Project on federal lands'.
- proj 84411 (Completed, non-designated): "Latest update: August 29, 2023 -
  The National Capital Commission issued its Notice of Determination and
  determined that the project is not likely to cause significant adverse
  environmental effects." Start date 2023-03-15.
- proj 80175 (Completed, designated CEAA-2012 project): Latest update
  "January 11, 2021 - The Minister ... issued the Environmental Assessment
  Decision Statement"; key-documents table with dates (Notice of
  Commencement 2019-07-05; Decision Statement 2021-01-11).
- proj 87425 (In progress): Latest update "April 17, 2024 - The public comment
  period ... is closed"; key-documents table with dates.

Dated terminal-event lines verified 3/3 for the terminal/completed samples;
n is too small to generalize - cohort-scale share is the named next probe.
Clean page sizes: 8.6 KB (80175), 12.2 KB (87425), 42.6 KB (81027; much of it
'nearby assessments' nav noise), 149.8 KB (84411). Bulk-export capability of
the 'All records' exploration view (iaac-aeic.gc.ca/050/evaluations/
exploration?projDocs=<id>) NOT probed yet.

## Dated worked examples (prediction-instant anchoring)

Registry dates are published at DAY grain, no time-of-day, timezone unstated
by the publisher (registry dates read as Canada-local calendar dates; the
prediction instant inherits that day grain - an assumption to carry into any
evaluation_contract).

Terminated example (America/Halifax local dates):
- Feature window: attributes published with the posting on 2020-09-29
  (category 'Transport Industry', province NS, responsible authority
  Transport Canada, location Sydney NS, description text, start date).
- First available: 2020-09-29 (registry posting creation; date grain).
- Prediction instant: 2026-10-30 retrospective formulation anchored at the
  posting date 2020-09-29.
- Target start: 2020-09-30 (the day after the instant, date grain).
- Target end: bounded by the censoring horizon (unmeasured; see uncertainty).
- Observed terminal event: 2022-01-18, 476 days after start.

Completed example (America/Toronto local dates):
- Start 2023-03-15, determination issued 2023-08-29 (167 days after start),
  wording: "not likely to cause significant adverse environmental effects".

## Five contracts (current state, investigating - NOT ready)

- Redistribution: SUPPORTED - OGL-Canada 2.0 (ca-ogl-lgo on the package),
  class A; attribution carries into LICENSE.md.
- Prediction timing: PARTIALLY SUPPORTED - features are posting-time
  attributes (documented by the publisher); the terminal event is a dated
  future event relative to the instant. UNRESOLVED: the dated-event share
  across the cohort, the terminal-event lag distribution (needed to fix the
  censoring rule), and page-vintage/as-of policy (the registry is a live
  current archive; no historical page vintages - task is
  retrospective-within-current-archive and must say so).
- Target: SUPPORTED in shape - binary terminal state from a dated registry
  event; the determination-outcome variant's positive rate UNMEASURED.
- Split capacity: SUPPORTED on volume (2019-2026, both classes every year);
  UNRESOLVED at the edges: censoring of 2024-2026 cohorts and the sparse
  pre-2019 backfill.
- Mirror/contribution: PRELIMINARY - no ML-ready Canadian registry-outcome
  benchmark found in a web search (2026-10-30); the AU analogue on this bench
  (epbc-referral-controlled-action) was dropped on licence class D, not on
  task shape, so the family slot is open. Formal check-novelty.py run and
  verdict still required before any ready verdict.

## Costs measured

- MapServer full attribute fetch: 9 requests / 1.01 MB / 6.58 s
  (coordinator). MapServer service+counts+samples: 7 small requests.
- Registry pages via extraction backend: 4 pages, 8.6-150 KB clean text each.
- Cohort-scale page extraction (6,600 pages): NOT measured - named next step.

## Uncertainty that decides this lead

The share of the 6,600 registry pages that expose a machine-parseable dated
terminal event, and the per-page cost of getting it. If the dated-event share
is high (the 3/3 sample suggests structured pages), the lead advances to a
formal novelty check and a worker extraction measurement; if pages are mostly
unstructured or undated, timing cannot be supported and the lead parks.

## Commands retained

probe/iaac_layer_probe.py - liveness, counts, samples, full attribute fetch
with cost measurement (reproduces every aggregate number above).
