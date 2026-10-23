# Verification

What was run, on what bytes, and what it does **not** cover. Every number below
was read back from collected job results and fetched reports, not from a
console.

## 1. Artifact identity and the gate

- Built by worker job **nz-ea-002** (server 172091812, cx23/hel1, 91 min, exit
  0) from the EMI FinalEnergyPrices blob container as listed 2026-10-23:
  728 blobs listed, **714 price files processed** (3 interim and 1 incomplete
  variant excluded and counted), monthly channel owning trading dates
  <= 2025-10-31 and the daily channel owning later dates. The bulk fetch
  (~3.6 GB) happened on the worker; the bytes never passed through the
  coordinator. Anchor inputs recorded by the build: the container listing
  (460,102 B, sha256 `b1bb79a6...`) and the NetworkSupplyPointsTable vintage
  20261021 (442,717 B, sha256 `ffb2a554...`, last-modified 2026-10-22).
- Qualification gate **1.4.0** ran on the **full artifact** on the worker:
  **38/38 checks, 0 failed** - leakage over shipped columns (no column
  separates the classes on its own; `anchor_date` and `row_id` declared
  high-cardinality identifiers), prediction timing (publication instant
  D+6d >= the 5-day maximum measured daily-channel lag; 11/11 observed
  publication dates usable; row selection reads only days <= D), units and
  reference frames (11 measured columns declare unit and frame; known-event
  fixture recorded), temporal splits (declared windows machine-readable and
  matched by the rows: train 1996-10-30..2015-12-31, eval 2016-01-01..
  2022-10-31, holdout 2022-11-01..2026-10-15, disjoint, both classes in
  eval and holdout, clustered positives 231/152 >= the 20-event minimum),
  and runner compatibility. The report ships as `qualification.json`;
  artifact version `545e0e4418c1f0e5...`.
- `qualify_dataset.py --accept` re-verified the exact bytes on the worker
  before any scoring (`ACCEPTED: /output/extract matches the qualified
  artifact 545e0e4418c1f0e5`). The baseline job **nz-ea-baseline-003**
  fetched the five files from private staging release 422246241,
  digest-verified them and re-ACCEPTED them through the gate **before**
  running the runner.
- The two earlier baseline attempts (nz-ea-baseline-001/002) failed at the
  fetch stage and scored nothing: the job fetch spec carried one
  hand-mis-transcribed hex character in the holdout digest, and the worker's
  digest guard correctly refused the correct bytes against the wrong
  expectation. Root cause diagnosed programmatically by diffing the spec
  against the bundled gate report; the guard was right both times. Recorded
  here because the failure is part of the evidence chain, not a data defect.
- A full synthetic-fixture dry run of build + gate ran **before** any worker
  spend (gate 1.4.0 passed on the fixture; one defect found and fixed first -
  a duplicate `island` header, the exact one-column-list failure mode the
  qualification skill documents). Fixture data is fabricated and nothing from
  it is quotable.

## 2. Label and publisher cross-checks (measured in-build)

- Label integrity: the label reads the D+7 island daily mean; the label source
  columns (`target_day_island_mean_price`,
  `target_day_DollarsPerMegawattHour_rows`) are excluded from every shipped
  file, and the gate's single-column AUC sweep found no shipped column that
  separates the classes on its own.
- Coverage: 10,979/10,979 trading days present 1996-10-01..2026-10-22
  (0 missing), both islands every day; the 10 overlap days 2025-10-22..31
  exist in both the monthly and the daily channel and were cross-checked
  (18 island-days compared, max |island mean diff| 0.0).
- Mapping: POC -> island from the publisher's NetworkSupplyPointsTable
  (2,633 rows, 894 distinct POCs, 0 island conflicts measured); rows whose POC
  is absent from the current-vintage table (retired POCs) are excluded from
  island aggregation and counted per year (9,437,515 source rows over
  1996-2026).
- Known-event fixtures asserted in-build from the constructed panel: the
  August 2024 dry-year episode - four fixture days 2024-08-05..08 at market
  daily means 814.77 / 861.95 / 883.56 / 825.31 NZD/MWh, all exceeding (the
  Authority's Review of winter 2024 records "in early August the average
  daily price reached $820/MWh"); 2008-07-01 at 305.79 exceeding; the January
  1997 quiet-era control at max 50.0 not exceeding.

## 3. The baseline triad (identical eval rows)

All measured on the same 4,992 eval rows / 2,150 positives of the accepted
artifact. The references were computed post-acceptance by the build's
`score.py` (rate tables estimated on train rows only) and **independently
recomputed** by `reference_check.py` in the baseline job with exact agreement
on every value; the full model is the benchmark's own unmodified `train.py` +
`validate.sh` (worker job **nz-ea-baseline-003**, server 172109172, 1.2 min,
exit 0), with `validate.py`'s predict_proba recompute and a third independent
stdlib recompute all agreeing at 0.8924:

| Reference | Eval AUC |
| --- | ---: |
| Calendar-only (train-fitted island x target-week rate) | 0.5011 |
| Persistence (last published day, `last_day_mean`) | 0.8820 |
| Persistence (published 7-day mean, `mean_7d`) | 0.8843 |
| **Full model (XGBoost via the runner contract)** | **0.8924** |

Majority-class accuracy on the same rows: 0.5693 (the constant fit on train,
measured against this split's labels). The runner files ran unmodified
(bundled sha256 equal the benchmark's declared hashes: `train.py a3c6bcf1...`,
`validate.py b597e7f8...`, `validate.sh 3f06ca48...`). Dependencies on the
worker: python 3.13, pandas 2.3.3, numpy 2.5.4, xgboost 3.4.1,
scikit-learn 1.9.1. The private holdout was fetched for re-acceptance only,
never copied into the workdir, and was not scored by anything.

Interpretation, under the criterion declared **before** the run (headroom
demonstrated only if the model exceeds persistence_mean7 AND the
target-week-clustered paired interval excludes zero): the model's observed
advantage is positive but **headroom over persistence is NOT demonstrated** -
paired target-week-clustered 95% bootstrap intervals for
model - persistence_value (+0.0104) and model - persistence_mean7 (+0.0081)
both contain zero ([-0.0010, +0.0226] and [-0.0028, +0.0206]; 1000 resamples,
58 distinct eval weeks). That is an **inconclusive difference**, not parity
and not a trailing-model defect. Calendar-only is beaten decisively
(+0.391 observed; the calendar-only reference is near-chance at 0.5011
because 4,986 of 4,992 eval rows fall back to the global train rate - the
eval weeks are almost all unseen in training, which is what a temporal split
should do). Per-year eval texture is in `measurements.json`; the extremes
matter: 2016 carries only 6 positives (model AUC 0.39, persistence 0.46 -
nearly-negative years are hard for everyone), while 2017-2021 episodes are
carried by both model and persistence at 0.75-0.95.

## 4. Download path executed

`get_dataset.py` was executed end-to-end against the private GitHub release of
this package (all five assets, every digest verified, runner layout restored,
exit 0) and `qualify_dataset.py --accept qualification.json` re-verified the
downloaded tree (`ACCEPTED`, artifact `545e0e4418c1f0e5`). Once the release is
public the same script runs anonymously.

## 5. What is not covered

- **No agent or harness comparison was run, and none is implied.** The 0.8924
  baseline is a single XGBoost pass through the runner contract - the floor a
  solver inherits, not a statement about coding-agent performance.
- **The holdout AUC is deliberately not measured.** The holdout is the
  post-2022-11 real-time pricing regime (prevalence 0.544), out-of-distribution
  relative to training by design; it exists to be scored against future
  solutions and quoting its AUC would spend it.
- **Headroom over persistence is not established.** The pre-declared criterion
  was not met (intervals contain zero). The observed gap is recorded as
  inconclusive: neither "the task is persistence" nor "the model beats
  persistence" is a supported claim. One weak runner model does not establish
  that no useful prediction is possible.
- **Only current vintages exist.** The EMI container publishes current final
  prices; historical vintages are not exposed, so a true point-in-time
  reconstruction of what was knowable at each past instant is not performable.
  Feature values are current-vintage, the cutoff is documented, and the timing
  claim is anchored on the publisher's own documented finality rule ("final
  by 2pm the following business day") plus the measured daily-channel
  Last-Modified lags (0-5 days over 365+ files; the instant is placed
  conservatively at D+6). The monthly-channel files carrying pre-2022 trading
  dates were themselves uploaded 2022-10-31 (Last-Modified measured), which is
  why the publication instant for the historical era is an anchored assumption
  rather than an observation.
- **Prevalence drift is a property of the market, not a construction fault**:
  19.92% (train, ex-post pricing era) -> 43.07% (eval) -> 54.36% (holdout,
  real-time pricing regime). A model trained on the early period faces an
  out-of-distribution eval window by design; per-year rates are in
  `measurements.json`, and pooled eval numbers must not be read as a clean
  temporal claim.
- **One recorded evidence blemish, resolved elsewhere in the chain**: the
  construction job's `references.json` wrote `accepted_artifact_version: null`
  (a recording defect, not an artifact defect). The acceptance record, the gate
  report and the baseline job's result all record artifact
  `545e0e4418c1f0e5...`, the stage order in the job's container.log ties the
  references to the accepted bytes, and the report shipped here
  (`qualification.json`, sha256 `51e5b46a...`) carries the correct version.
