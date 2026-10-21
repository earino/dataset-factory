# nhs-ae-four-hour-decline

Record dated evidence, decisions, and failed approaches here.

## 2026-10-21 discovery session (tick region: United Kingdom)

Publisher: NHS England statistical work area "A&E Attendances and Emergency
Admissions" - https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/

### Access probes (commands and results)

- `curl -s -A "Mozilla/5.0" .../ae-waiting-times-and-activity/` -> HTTP 200, 81,207 bytes.
  Page lists year sub-pages 2015-16..2026-27 and a cumulative
  `Monthly-AE-Time-Series-September-2026-LS35fw.xls`.
- `python3 .factory/ae_collect_urls.py` (session script, deleted after use) -> CSV
  inventory: 2018-19 through 2026-27 pages carry 12 monthly CSVs each (6 so far in
  2026-27); 2017-18 and earlier pages carry XLS only (monthly coverage before
  2018-04 needs the cumulative XLS on a worker). Total monthly CSVs: 102.
- `python3 .factory/ae_download.py` -> 102/102 CSVs downloaded OK, 0 fail,
  3,115,779 bytes, 1.2 s, from the coordinator. Sample row (September 2026 file):
  `MSitAE-SEPTEMBER-2026,NTV0B,NHS ENGLAND SOUTH EAST,ASHFORD WALK-IN-CENTRE,...`
  193 provider rows in the latest month; 21 columns (see record sources.api).

### Panel and label probes

- `python3 .factory/ae_panel.py` -> 21,649 CSV rows; 1,152 rows had non-monthly
  Period tokens (quarterly/annual artefacts in some files) - excluded;
  20,497 (org, month) keys; 97 months 2018-04..2026-09; 124 providers with
  Type 1 attendances >= 100 in >= 24 months; 9,071 provider-months.
- National Type 1 within-4h computed by calendar year: 2020 85.1%, 2021 73.2%,
  2022 62.4%, 2023 60.1%, 2024 58.6%, 2025 60.2%, 2026 YTD 61.0%.
  Cross-check, publisher's own commentary (August 2026 PDF, read via search):
  "61.1% of patients were admitted, transferred or discharged within 4 hours in
  Type 1 A&E Departments in August 2026" vs panel 60.9% for 2026-08; NAO report
  HC 588 (Sept 2026): Type 1 low 56.7% in 2022-23, 60.9% in 2025-26 - consistent
  modulo fiscal-vs-calendar-year alignment.
- Label base rates measured from the panel (volume gate applied), windowed on
  the target month:
  - m/m decline: train(2019-01..2022-12) 2,098/3,714 = 56.5%;
    eval(2023-01..2024-12) 1,152/2,449 = 47.0%; holdout(2025-01..2026-09)
    1,233/2,538 = 48.6%. Distinct positive providers 110/124/121.
  - fixed thresholds measured and refused: <95% -> eval 97.1% / holdout 99.9%
    positive (uniform-class red flag; the constitutional standard no longer
    separates); <80% -> holdout 95.8%; <74% -> holdout 90.8%.
- `python3 .factory/ae_fixture.py` -> quick national monthly series; Dec-2021
  (Omicron) 65.6% vs Nov-2021 66.2%: no clean national step, so winter pressure
  is a provider-grain signal; recorded as the reason no known-event fixture is
  claimed for this threshold-free label.

### Licence

- Work-area page footer (read 2026-10-21): menu item "Open Government Licence
  v3.0" -> https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
- NHS England statistics published under OGL v3 unless otherwise stated;
  third-party reusers state the same basis.

### Novelty

- Prior art found and recorded in record.json (novelty_check):
  - BMC Emerg Med 2020 (Springer): time-series forecasting of ED *daily
    arrivals* at two London hospitals, private data, no published benchmark.
  - github.com/rajatgaur505/nhs-ae-performance-analysis: descriptive analytics
    + 3-month regression projection over 12 monthly CSVs; not a published
    prediction task with splits/scored contract.
  - No Hugging Face/Zenodo dataset for four-hour performance prediction found.
- Verdict: differentiated - ours is the first scored, split, leak-gated
  provider-month formulation of NHS four-hour performance direction known to us.
