# za-cct-c3-service-request-surge — discovery notes

City of Cape Town Open Data Portal (ArcGIS Hub: odp-cctegis.opendata.arcgis.com),
dataset "Service Requests Jan 2023 to Present" (SAP C3 Notifications). All probes were
run read-only against the public FeatureServer from this coordinator on 2026-10-29;
commands are reproducible via `python3 candidates/za-cct-c3-service-request-surge/probe_c3.py`
(flags: --panel, --series "<category>", --surge, --timing, --mask).

## Source identity

- Hub item: https://odp-cctegis.opendata.arcgis.com/datasets/da3b6d46845e4671bde500e8de7e1d3e/about
- Item id: da3b6d46845e4671bde500e8de7e1d3e (table, no geometry); spatial twin
  6e8f77f27ea84763abbc11023561a406 (only the ~72% of rows with coordinates — NOT used).
- Query endpoint (anonymous, documented in the item description):
  https://services6.arcgis.com/nyYfO9SxHU2ChQd9/arcgis/rest/services/schema_jan2023_iso/FeatureServer/0
- Deprecated predecessor "Service Requests 2023 until 06 October 2026"
  (90711027d33940b5a06e96ad8a8f7ede) was frozen by the publisher on 2026-10-06 with a
  deprecation notice pointing to the live item — evidence the publisher maintains
  dataset lifecycle in the open (checked 2026-10-29).
- Publisher: Open Data Team, City of Cape Town (open.data@capetown.gov.za); operational
  source: SAP C3 Notifications via SAP BEx extract ("Notifications by Org Responsibility").
- The item description is full field-level documentation (unusually complete for this
  portal): every field is documented, including the update and revision policy:
  "Update: daily (Mon–Fri)" and "Daily incremental inserts keyed on Notification ID" +
  "Monthly reconciliation of Changed_on and Completed_Date on historical records".

## Provenance / mixture (measured 2026-10-29, --panel)

- 4,509,409 rows; CreatedOnDT 2022-12-31 .. 2026-10-28 (day granularity only — the
  publisher converted SAP's DD.MM.YYYY export; no time-of-day). Item description states
  row count "4,425,943 (through 05 October 2026)" — the table keeps growing daily.
- Suburb fields: `Suburb` (raw, as-reported, always present) and `Suburb_Clean`
  (normalised against the official suburb register; publisher says use this for
  analysis). MEASURED BACKFILL LAG: Suburb_Clean is NULL for 310,395/3,461,621 = 9.0%
  of pre-2026 rows but 95,356/205,225 = 46.5% of rows created since 2026-09-01 — the
  monthly reconciliation populates it with a lag of weeks. Construction consequence:
  a prediction instant inside the last ~6 weeks cannot rely on Suburb_Clean for the
  newest rows; use raw `Suburb` or restrict suburb-keyed features to reconciled weeks.
- Complaint categories: >1,000 distinct C3_Complaint_Type values (group-by hit the
  1000-row result cap), long messy tail including hygiene labels ("Duplicate" 68,370
  rows; "DO NOT USE (Tree Complaint)" 26,081). Top by volume (measured):
  No Power 463,757; SEW: Blocked/Overflow 463,307; Street Lights - All Lights Out
  193,973; Street Lights - Single Light Out 183,787; Damaged Bin - 240L 120,889;
  Stolen Bins - 240L 112,208; Suspect Tampering 83,519; ... The task must pin a
  curated category list at construction and exclude hygiene types.
- ~28% of notifications carry no usable coordinates (Longitude/Latitude = 0/NULL);
  the tabular item (used here) contains every notification, the spatial twin does not.
- Post-hoc fields: ChangedOnDT and CompletedDT are completion-side and are explicitly
  revised monthly by the publisher's reconciliation. They are EXCLUDED as features for
  the created-count task; only CreatedOnDT (append-only insert key) drives the label.

## Prediction timing (measured)

- Availability probe at a named instant, 2026-10-29T08:31:51 SAST (06:31:51 UTC):
  rows created 2026-10-28 present (3,853), rows created 2026-10-29 NOT yet present (0).
  So at ~08:30 SAST the previous day's created-rows are queryable; same-day rows are not.
- The publisher documents updates Mon–Fri only. Weekend rows (created Sat/Sun) become
  queryable with the Monday update (measured presence pattern: Sat 2026-10-24 3,367 and
  Sun 2026-10-25 2,290 rows present on Wed 2026-10-29).
- CONTRACT (conservative): prediction instant = Tuesday 06:00 SAST. Features use
  created-dates through Sunday (D-2; guaranteed posted by Monday's update). Target
  window = created-dates Wednesday .. Tuesday (7 whole SAST days, first one starting
  ~18h after the instant). No part of the target window precedes the instant, and no
  target-window row can be queryable at the instant (created-date granularity cannot
  straddle it because the whole first target day is the day after the instant's day).

### Dated worked example (all times SAST, UTC+2)

- Prediction instant: Tuesday 2026-11-03 06:00.
- Feature event window (guaranteed available): created-dates ≤ Sunday 2026-11-01
  (posted by Monday 2026-11-02's Mon–Fri update; observed D-1 availability at 08:31
  SAST on 2026-10-29 supports this with margin).
- Eligibility: category (and suburb, for the expansion) has ≥ 26 weeks of
  reconciled history before the instant.
- Target start/end: created-dates 2026-11-04 00:00 .. 2026-11-10 23:59 (Wed..Tue).
- Label: 1 iff target-window created-count > 1.25 × median of the 8 weekly counts
  for weeks starting 2026-09-07 .. 2026-10-26 (all ending before the instant).
- Leakage control for construction: no shipped row may carry a created-date inside
  any scored target window (the abs-visitor-arrivals cross-row-join defect class);
  monthly-reconciled fields (Suburb_Clean, CompletedDT, ChangedOnDT) must not be used
  as features for weeks inside the reconciliation lag.

## Split capacity (measured, city-level series; --surge / --series)

Full-range day-level series fetched per category via paged group-by (5 categories,
196 weeks, Dec 2022 .. Oct 2026; saved snapshot: weekly_series_5cats.json). Surge label
(week > 1.25 × trailing-8-week median), scorable weeks by window:

| category | train (weeks ≤2024) | eval (2025) | holdout (2026) |
| --- | --- | --- | --- |
| No Power | 15/98 | 15/47 | 8/43 |
| SEW: Blocked/Overflow | 9/98 | 6/47 | 4/43 |
| Street Lights - All Lights Out | 17/98 | 13/47 | 9/43 |
| Illegal Dumping | 14/98 | 9/43 | 7/43 |
| Damaged Bin - 240L | 10/98 | 9/43 | 8/43 |

Both classes present in every window for every probed category (surge base rate
~9–17% train, ~13–32% eval, ~9–21% holdout). Positives cluster in category-level
regime waves (e.g. "No Power" surges track outage/load-shedding periods), so the
week-level counts above, not per-day totals, are the clustered evidence. The
suburb × category expansion (population: suburbs with ≥26 weeks history per
category) multiplies these rows by hundreds of units; its full counts are a
construction-time measurement on the worker — the city-level counts here are the
discovery sample and are not claimed to bound the suburb-level base rates.

## Extraction cost (measured where stated)

- Aggregate group-by queries (day-level counts, one category): 2 pages × ≤1000 rows,
  ~0.6–1.5 s/page from this coordinator (measured 2026-10-29; 5-category full-range
  series ≈ 10 requests, ~65 KB JSON total).
- Sibling-service fetch-rate measurement (same FeatureServer host, 2 small fields,
  1000 rows/page): 49,947 rows in 27.2 s ≈ 0.55 s/page → the full 4.5M-row panel
  ≈ 4,509 pages ≈ 40–75 min single-threaded DERIVED from the measured page rate
  (clearly an estimate; construction on the worker must re-measure with the actual
  field set and parallelism). Bulk CSV via the Hub "Download" button is an
  alternative construction path, unmeasured here.
- Coordinator discipline: the full panel never passes through this host; extraction
  is a worker job.

## Licence (read 2026-10-29; quoted in record.json license_evidence)

- Open Data Terms of Use page (section-specific instrument, disclaimer-only, no
  reuse restriction), Open Data Policy 27781 (Council-approved 2020-12-03) defining
  the portal's data as "freely used, shared and built-on by anyone, anywhere, for
  any purpose", the item's own licence field, and the general-site copyright
  statement are all quoted with URLs. Class A recorded; flagged for the normal
  release-stage licence review.
- Third-party reuse observed (not a grant): StreetSignal (streetsignal.co.za)
  publishes descriptive suburb profiles computed from this dataset
  (volumes, resolution-time percentiles, complaint rates) and labels its rights
  status "UNKNOWN, terms route checked".

## Novelty (full verdict in record.json novelty_check)

- Closest prior art (task family): NYC 311 service-request volume forecasting and
  resolution-time prediction — abundant as projects/tutorials/papers on the NYC
  Open Data 311 feed (e.g. github rab175/311_Project SARIMA/LSTM; BigQuery ML
  codelabs; Zenodo spatiotemporal 311 studies). Comparator, not a mirror: different
  publisher, country, population, category ontology, regime drivers.
- Cape Town C3 specifically: StreetSignal aggregates this source into descriptive
  suburb statistics; no ML-ready prediction task with a stated prediction instant,
  splits and a scored contract was found (searches recorded by check-novelty.py).
- Contribution: first scored, split, publication-instant-anchored prediction task on
  Cape Town C3 (weekly category/suburb surge exceedance), with the revision/reconciliation
  policy of the source documented as part of the contract.

## Historic extension (optional, not required by the task)

The item description links per-year archived C3 items ("Historic Data: 2024; 2023;
... 2011"). Extracted item ids: 04b3d8d46b9b45cdb75a6cd66c191875, 120ea6d8fd764a8cae494e3c568ae7b8,
2d7c8c68affa4610924d1443e20feff7, 42bcf338fc8943f1b0158b319dd5e02b, 572e642ae39f46fd9d72d5bb6924cac6,
659a6f32dc3c4360a713c5230d141f01, 780408b974054153b2ef1300964772b8, 800372c282074ef7b899bf7bc42c18d5,
91ef214562524c808d4c8affe7a0547e, a3d976cc16e54f0b946048e4274f211d, ca510809b5e94c3abb43cabf78094bcd,
e5b2133cdcf540d581bf75de85a561f8, eaabc5f8fe0a4fb6ab95219989cc3cdd, fa06c544c9594b279cf301b91becfe2e.
Pre-2023 years would let construction extend the train window; the task as scoped
needs only the live table (Dec 2022 → present).

## Known-event fixtures (to assert at construction)

- The measured "No Power" series should show its strongest 2023–2024 surge weeks
  during South Africa's high load-shedding period, with a regime shift to fewer
  surges after the 2025 recovery — assert direction on the shipped series, citing
  the public load-shedding record (Eskom), and name the exact top-3 surge weeks
  from the data at construction time.
- Winter-rainfall storm weeks should coincide with SEW: Blocked/Overflow surges;
  construction picks one named Cape Town storm week (e.g. the June 2024 cut-off-low
  flooding) and asserts the surge label is positive for that week.
