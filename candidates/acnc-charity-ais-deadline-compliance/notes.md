# acnc-charity-ais-deadline-compliance — discovery notes

Opened and advanced to `ready` in the 2026-10-31 scheduled discovery session (regional
focus: Oceania). All measurements below were made on 2026-10-31 from the live publisher
endpoints by the hosted coordinator with bounded fetches into `/opt/data/cache/scratch`
(24 h auto-prune). `probe_ais_metrics.py` in this directory reproduces every number; the
CSVs themselves were fetched once, measured, and left to auto-prune (bulk data never
enters the repository).

## Source and licence

- ACNC Registered Charities (register bulk dataset):
  https://data.gov.au/data/dataset/acnc-register
  (package `b050b242-4487-4306-abf5-07ca073e5594`). Dataset page "Licence" field and every
  resource individually labelled **Creative Commons Attribution 3.0 Australia** (read
  2026-10-31). CSV resource `datadotgov_main.csv`, 15,156,962 bytes.
- ACNC Annual Information Statement datasets, one per reporting-period year 2013-2024,
  published on data.gov.au (landing list: ACNC "Download Charity Register data" page,
  which also states the cadence: "published on an annual basis, and updated weekly").
  Per-year licences read from `package_show` on 2026-10-31: 2024 and 2023 **CC BY 3.0
  Australia**; 2019-2022 **CC BY 2.5 Australia**; 2015 **CC BY 4.0 International**; 2013,
  2014 also cc-by. All class A; per-year variants must be stated per-year in LICENSE.md.
- Register page "About the ACNC Charity Register" (read 2026-10-31) records the
  withheld-record mechanism: approved-withheld information "won't appear in these
  datasets from the date of approval onwards".
- Deadline policy: https://www.acnc.gov.au/for-charities/annual-information-statement/annual-information-statement-due-dates
  — "must be submitted within six months of the end of the charity's reporting period",
  with the Commissioner's standing extension for standard 1 July-30 June periods to the
  following 31 January (footnote on the same page).

## Probe commands and observed outputs

    # catalogue enumeration (56 ACNC-tagged packages; AIS years 2013-2024 located)
    curl -s -A "Mozilla/5.0" "https://data.gov.au/data/api/3/action/package_search?q=ACNC&rows=40"
    curl -s -A "Mozilla/5.0" "https://data.gov.au/data/api/3/action/package_show?id=276ec1bc-4971-461c-88bc-be9f3c99a0f8"
    # bounded schema probe (first 6 KB of the register CSV, Range request)
    curl -sL -r 0-6000 "https://data.gov.au/data/dataset/b050b242-4487-4306-abf5-07ca073e5594/resource/8fb32972-24e9-4c95-885e-7140be51be8a/download/datadotgov_main.csv"
    # full-file fetches with measured cost (single anonymous HTTPS GET each)
    # register 15,156,962 B / 3.0 s; ais19 44,462,950 / 4.4 s; ais20 32,540,058 / 4.1 s;
    # ais21 32,983,235 / 4.2 s; ais22 35,588,791 / 4.1 s; ais23 36,881,236 / 4.0 s;
    # ais24 38,072,279 / 4.2 s; 2024 group-members xlsx 66,137 B.
    python3 probe_ais_metrics.py            # reproduces the metrics below

Observed (see record.json `measurements` for the full numbers):

- Register: 66,541 rows / 65,933 unique ABNs; **no** status, revocation-date or AIS-date
  columns (columns A-BQ are identity/location/size/subtype/beneficiary flags) — the
  register alone cannot carry the task; the per-year AIS datasets can.
- AIS schema (2023/2024 headers): `abn`, `charity name`, `registration status`,
  `charity size`, `basic religious charity`, **`ais due date`**, **`date ais received`**,
  `financial report date received`, activities, staffing, ~30 financial columns,
  state/fundraising registration fields, key-management-personnel fields. 2019 file has
  167 columns (address/state/activities/beneficiaries), 2020-2024 files 91-97 columns
  (address dropped). Core label/feature columns present in every year 2019-2024.
- Per-year rows and lateness (label operand `date ais received` vs `ais due date`):
  2019 51,040 rows (on-time 71.85% / late 28.07%); 2020 51,438 (67.88% / 32.09%);
  2021 51,841 (70.10% / 29.89%); 2022 53,053 (72.24% / 27.75%); 2023 53,548
  (73.96% / 26.03%); 2024 54,145 (74.95% / 25.05%). 2024 late-lag days: median 57,
  p90 376, max 950.
- Prior-filer absence (the never-lodge component): 2021→2022 2.78%, 2022→2023 3.41%,
  2023→2024 3.61%. Of the 1,935 absent in 2023→2024, 1,035 carry 'Voluntarily
  Revoked*' status codes, 49+ 'Revoked Double Defaulter' (the ACNC's own non-lodgment
  outcome), 812 still 'Registered' in the 2023-file snapshot.
- Group reporting: 2024 group-members file lists 1,315 member ABNs (group name, member
  ABN, member name, membership start/end); only 5 also carry an individual period-2024
  AIS row (60 in 2023, 242 in 2019). Members must be excluded from the frame.
- Eligibility-frame counts (prior AIS received <= target due date - 90 days):
  target 2020: 37,970 eligible / 31.01% positive; 2021: 39,387 / 29.02%; 2022: 39,432 /
  25.97%; 2023: 41,545 / 25.79%; 2024: 42,885 / 25.73%. Windows: train 2020-2021
  77,357 rows / 23,205 positives; eval 2022-2023 80,977 / 20,958; holdout 2024 42,885 /
  11,035. Both classes in every window and every year.

## Publisher cross-checks

1. ACNC Annual Report 2025-26, KPI 1.3: "Percentage of 2025 Annual Information
   Statements submitted by the due date (Target: 75%, Result: 76%)"; "At 30 June 2026,
   76% of charities had submitted their Annual Information Statement by the due date ...
   compared to 73% in the previous year." Measured bulk-file on-time shares: 74.95%
   (2024 file), 73.96% (2023 file) — the label construction matches the publisher's own
   compliance KPI; the small gaps are the fixed census date vs the final file.
2. Australian Charities Report 11th edition: 52,314 individual 2023 statements + 313
   group AISs covering 1,281 charities (census) vs 53,548 rows in the final 2023 file —
   a measured +1,234 post-census rows, quantifying the weekly trickle channel. The
   label is stable under trickle: a period-Y AIS received later is still after the past
   due date.

## Dated example (real; instants in Australia/Sydney, AEDT)

Integricare Limited, ABN 11000073870, financial year 1 July - 30 June.

- Feature row: period 01/07/2022-30/06/2023, recorded due date 31/01/2024, `date ais
  received` 18/01/2024 — on time, observable well before the instant.
- Target period: 01/07/2023-30/06/2024, recorded due date 31/01/2025 (30-June end + 7
  months, the Commissioner's standing 31 January extension, recorded in-file).
- Prediction instant T = 31/01/2025 - 90 days = **02/11/2024** (eligibility satisfied:
  prior lodgment 18/01/2024 <= T).
- Target window: lodgment of the period-2024 AIS in **(02/11/2024, 31/01/2025]**. No
  part of the target window precedes T.
- Observed outcome: `date ais received` **03/02/2025** > 31/01/2025 → label 1 (failed to
  lodge by the due date, by 3 days).

## Contract reconciliation (summary; full text in record.json `review`)

1. Redistribution — supported: explicit CC BY on every input dataset (class A);
   per-year licence variants recorded.
2. Prediction timing — supported with recorded vintage assumptions: per-charity instant
   T = recorded due date - 90 days; prior-period features are lodgment-observable before
   T by the eligibility rule; label columns excluded. Channels recorded: weekly dataset
   updates (trickle measured +1,234 rows post-census; label stable), withheld-record
   removal (mechanism quoted, rate unmeasured, direction bounded — can only create
   false positives), current-vintage `registration status` (post-hoc exclusions must be
   declared at construction; 'Revoked Double Defaulter' must not be an exclusion).
3. Obtainable target — supported: publisher-recorded label operands; censoring
   publisher-coded (voluntary-revocation status codes; group-membership files); residual
   mixture measured and declared (812 'Registered'-status absentees of 1,935 in
   2023→2024).
4. Split capacity — supported: measured counts above; disjoint temporal windows; both
   classes everywhere; positives spread across tens of thousands of charities.
5. Not a mirror — supported: `check-novelty.py` verdict `differentiated` recorded
   2026-10-31; no ML-ready lodgment-deadline formulation found; closest external work
   predicts charity size from the same register.

Uncertainty that remains (construction-time, non-blocking): withheld-record
false-positive rate; 2013-2018 XLSX backfill for a longer train window; announcement
timing of the 31-January extension for the earliest train years (reverse-history probe
per docs/PREDICTION-CONTRACT.md).

## Decision

`ready` — construction is the recorded next action and belongs to advancement
(construction -> full-worker qualification -> exact-byte acceptance -> reference/model
scoring -> reporting). Prior-lateness is the natural dominant simple reference and must
be measured first among references.
