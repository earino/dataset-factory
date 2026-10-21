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

## 2026-10-21 construction session - discovery panel figures corrected (two probe defects)

The kept `probe_panel.py` reproduces its own recorded numbers, but both were computed on a
silently damaged panel. The construction build (`source/build.py`) failed its acceptance
assertions against the recorded figures, and the diagnosis found two defects in the probe:

1. **BOM handling.** The probe opens files with `encoding="utf-8"`, so the five BOM-prefixed
   files key Period as `"\ufeffPeriod"`; `d.get("Period", "")` returns `""` and every row of
   those files is counted as a non-monthly Period and dropped. BOM files (measured with
   `head -c 3` per file): July 2019, August 2021, July/August/September 2023 - five whole
   months. The probe's "1,152 rows had non-monthly Period tokens" was really 101 TOTAL
   artefact rows + 1,051 BOM-file rows.
2. **Column-name variant.** The 2018-04..2020-03 files prefix counts with "Number of"
   ("Number of A&E attendances Type 1"). The probe looks up "A&E attendances Type 1", so
   att1 parsed as 0 for 24 months and no provider-month before 2020-04 ever passed the
   >= 100 volume gate. The recorded "97 months" panel in fact had no qualifying month
   before 2020-04 - which is also why the probe's national series starts at 2020.

Corrected measurements, commands and outputs:

- `python3 .factory/nhsae_recompute.py` (kept logic inline in this entry; the same 102
  CSVs, utf-8-sig + "Number of" alias):
  `rows_read=21649 bad_period=101 provider_months=21548 months=102 ((2018, 4)..(2026, 9))`
  `providers=134 qualifying_provider_months=12765 consecutive pairs=12631` (1,040 with
  target months before 2019-01, outside the windows).
- m/m decline label, recomputed: **train 6,116 rows / 3,285 pos (53.7%) / 133 distinct
  positive providers; eval 2,937 / 1,478 (50.3%) / 124; holdout 2,538 / 1,233 (48.6%) /
  121.** The recorded 3,714 / 2,449 / 2,538 came from the damaged panel.
- Fixed-threshold labels re-computed on the corrected panel, still REFUSED: <95% ->
  train 87.2% / eval 97.5% / holdout 99.9% positive; <80% -> holdout 95.8%; <74% ->
  holdout 90.8%. The refusal conclusion is unchanged.
- National Type 1 within-4h by year, corrected: 2018 83.0%, 2019 78.1%, 2020 82.6%,
  2021 72.9%, 2022 62.4%, 2023 59.8%, 2024 58.6%, 2025 60.2%, 2026 YTD 61.0%; August 2026
  60.86% vs the publisher commentary's 61.1% - the cross-check holds.
- Revision policy re-measured: **no duplicate (org, month) keys exist** across the 102
  files (each month appears in exactly one file; revised files replace originals on the
  year page), so the recorded "keep max attendances" dedup never operated. The build
  implements prefer-latest-upload anyway and measures dedup count = 0.
- Schema evolution measured: 16 data columns 2018-04..2020-07 (with "Number of" prefixes
  through 2020-03), booked-appointment columns from 2020-08 (22 columns), unnamed padding
  columns from 2024-09 (28 header fields). Booked columns are parsed but NOT shipped -
  they are absent for train feature months 2018-12..2020-07 (split-dependent
  availability).
- Local full build exercised on the coordinator before the worker run:
  `python3 candidates/nhs-ae-four-hour-decline/source/build.py --out <scratch> --source-dir
  <scratch>/ae_csvs` -> exit 0, splits 6,116/2,937/2,538;
  `python3 skills/dataset-qualification/scripts/qualify_dataset.py <scratch>/extract` ->
  QUALIFICATION PASSED (all 32 checks, artifact 4be4ee71013ae1cb); gate `--selftest` OK.
  Reference baselines measured at construction (rank AUC, single features): momentum
  (rate_m1 - rate_m) eval 0.416 / holdout 0.399 - anti-predictive; mean reversion
  (rate_m - rate_mean_6m) eval 0.566 / holdout 0.656 - the reference a competent model
  must beat; winter (Nov/Dec) holdout 0.509.

Worker job nhsae-001 (cx23/hel1) launched by this session: the launcher's first Hetzner
POST servers returned a transient HTTP 412 with no server created (ledger recorded
provisioning, server_id null); diagnosis via read-only API calls found no leftovers and
one registered SSH key; re-issuing the identical POST created server 171522297
(scout-nhsae-001, labels factory/job/expires matching the ledger), which reconcile
adopted and `worker resume --job-file` bootstrapped.

## 2026-10-21 construction: nhsae-002 green - built, qualified, accepted

**Worker jobs** (cx23/hel1, both destroyed; ledger `jobs/nhsae-001.json`, `jobs/nhsae-002.json`):

- `nhsae-001` **failed**, exit 2 in 11.9 s (release 419218537): "only 0 monthly CSV URLs
  enumerated". Two infrastructural findings, both measured:
  1. The launcher's first Hetzner POST /servers returned HTTP 412 with no server created
     (record written first, server_id null - the ledger's designed ambiguous-response
     state). Read-only API diagnosis found no leftover servers and one registered SSH key;
     re-issuing the identical POST created server 171522297, reconcile adopted it, and
     `worker resume --job-file` bootstrapped normally. The 412 did not recur for nhsae-002.
  2. The build failure itself: **www.england.nhs.uk (CloudFront) serves HTTP 202 with an
     empty body to the worker's datacenter IP** (fetched a year page from the worker: status
     202, 0 bytes, no CSV links; the same URL from the coordinator: 200, 82,127 B, 12 links,
     under three UAs). The publisher is not fetchable from Hetzner workers.
- `nhsae-002` **succeeded**, exit 0 in 12.1 s (release 419222791): fetch job consuming the
  staged source. The 102 CSVs (the coordinator's measured publisher fetch, 3,115,779 bytes)
  were packed deterministically (`tar --sort=name --owner=0 --group=0 --mtime=@0 | gzip -n`)
  into nhsae-source.tar.gz (608,327 B, sha256 8d8bc1b1a9e9f8303c8e0125aa2d6b7668fe3ebaf15
  051cd511bd74f2800d1fb), staged in private release source-nhsae-001 (419221351, asset
  661561799), fetched by the executor with sha256 verification, extracted and re-verified
  per-file by build.py. Inner composite digest 99cb3339b31ae2045c990c950a40fb44dc93f1dfc4d
  58f1ae1879fa851666833 - identical to the coordinator exercise.

**Built artifact** (extract in release 419222791, runner layout + quality.json):

- train 6,116 rows / 3,285 positives (53.7%) / 133 distinct positive providers;
  eval 2,937 / 1,478 (50.3%) / 124; holdout 2,538 / 1,233 (48.6%) / 121.
- Timing self-check: 121 rows recomputed against a physically truncated panel, 0 mismatches.
- Label-source columns absent from every shipped header (asserted in-build).
- National cross-check on the built panel: August 2026 Type 1 within-4h 60.86% vs the
  publisher commentary's 61.1% (revised-vs-provisional states).
- Reference baselines (std rank AUC, prediction-time-safe single features):
  momentum (rate_m1 - rate_m) eval 0.4161 / holdout 0.3993 (anti-predictive);
  mean reversion (rate_m - rate_mean_6m) eval 0.5659 / holdout 0.6562 - the reference bar;
  winter (Nov/Dec) holdout 0.5090.

**Qualification**: gate 1.3.0 over the full artifact ON THE WORKER, all checks green
(report in the release). Hand-off re-verification on the coordinator: every extract file
fetched from the release, each sha256 verified against the release manifest, then
`qualify_dataset.py --accept output/qualification-nhs-ae-four-hour-decline.json output/extract`
-> **ACCEPTED, artifact 9903df974f233dfa**. Gate `--selftest` re-run this session: PASSED.

**Reproducibility note**: the default build path (HTTP enumeration + download) is retained
and is the documented path for an unblocked network; from this project's workers the
publisher is CDN-blocked, so the staged-fetch path is the operative one and is recorded in
summary.source.provenance of the built artifact.


## Runner-contract baseline (nhsae-baseline-001, 2026-10-21)

Worker 171525370 (cx23/hel1), 56.8 s, result release 419227918, destroyed 06:41:51Z. Fetched
the five extract files from staging release 419222791 (4,898,346 B, every sha256 verified on
arrival, 0 failures) - the released bytes, not a rebuild. The qualification gate re-accepted
them before scoring (ACCEPTED, artifact 9903df974f233dfa). The runner workdir carried task.json
(target=declines, positive_label=1, id_columns=['row_id']) and data/train.csv + eval.csv only -
the private holdout was never copied in. The benchmark's own train.py and validate.sh ran
unmodified (bundled sha256 == the declared benchmark hashes):

- train.py: eval AUC 0.5526 (training 0.2 s, eval 0.0 s)
- validate.py: eval AUC via predict_proba 0.5526, [validate] CONTRACT OK
- deps: python 3.13.16, pandas 2.3.3, numpy 2.5.4, xgboost 3.4.1, scikit-learn 1.9.1

Headroom reading: the off-the-shelf XGBoost pass (0.5526 eval) sits below the construction-time
mean-reversion single-feature reference (0.5659 eval / 0.6562 holdout) - that reference is the
bar a competent model must beat, so the task is not saturated by a generic pipeline; momentum is
anti-predictive (0.4161/0.3993). Reports: .factory/nhsae-baseline-001/reports/.
