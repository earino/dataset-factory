# Verification record

What was actually run, on what bytes, and what it does **not** cover. Every figure
quoted in this package is measured; the job that produced each one is recorded in
`measurements.json`.

## The artifact

The five shipped files are worker job **pins-planning-002**'s output (the single
permitted rebuild after the first runner-contract failure), constructed from the
pinned 2026-10-22 edition of the Planning Inspectorate Casework Database
(`Casework_Database_-_2610.xlsx`, 22,207,115 B, sha256
`dff80bd0f17cbc640dc205009a9411269c8e58462b6df71af903c592af3c20fa`;
`Older_Casework_Data_-_2610.xlsx`, 12,325,866 B, sha256
`baf28d80c5cd5ad266f8a9e62c25517b2ec9d4c5d951239ab0638666bc092a4b`, two anonymous
GETs). `code/build.py` (sha256 `dc0b3dde...`), `code/run.sh` (`1852faaa...`) and
`code/score.py` (`3b8298c7...`) are the exact bytes the worker executed;
`code/qualify_dataset.py` (`4fab8a34...`) is the canonical gate 1.5.0. The
construction is deterministic under its `--built-at 2026-10-31T00:00:00Z` pin;
`code/category_probe.json` is the recorded worker-side category-dtype probe verdict
the writer consumed (sha256 `08c52aa5...`, the exact bytes worker job
pins-planning-002 produced in its stage 0), shipped so the rebuild is reproducible
without the private factory repository.

## What was verified, in order

1. **Qualification (full artifact, on the worker, before any figure existed).**
   Gate 1.5.0: **45/45 checks, 0 failed**, including the `event_time` timing block
   with its `administrative_record` feature evidence and per-column
   availability/assumption records, the evaluation contract (retrospective research,
   `isolated_rows` design requirement with the declared `lpa_prev_case_exposes_outcome`
   cross-row probe, training-label timing unverified), split windows disjoint on the
   shipped `valid_date` column with both classes in every window, leakage scans over
   every shipped column, the runner contract, and the categorical-coding declaration
   (probe-driven; not applied - string levels ship verbatim). Gate `--selftest`
   passed before the launch (fixtures still bite).
2. **Exact-byte acceptance.** `qualify_dataset.py --accept` against the gate's own
   report: **ACCEPTED for artifact
   `c861bd8f4acd9bbe267bdb58e1168996fdb359c540aaf4030030a632d693c527`** on the worker,
   and re-ACCEPTED in job `pins-planning-baseline-002`, which re-fetched the five
   files from private staging with every sha256 verified on arrival before running
   anything. The report ships as `qualification.json` (sha256 `f2d33fca...`).
3. **References (post-acceptance, identical eval rows).** Job pins-planning-002's
   `score.py`: procedure_type_rate 0.5551 (dominant simple reference),
   lpa_hist_rate 0.5414 (the named headroom reference), persistence_last_outcome
   0.5045, majority-class accuracy 0.6987; the year-rate and global-rate controls are
   constant scores with no ranking information (degenerate controls, recorded);
   the calendar-identity control collapsed onto lpa_hist_rate exactly (eval
   validation years have no train-era valid-year support, so every eval row fell
   back to its LPA's train rate; paired diff 0.0, CI [0,0]) and is recorded as a
   collapsed control, never as independent confirmation. Per-validation-year
   reference tables computed for both eval years (2020 and 2021).
4. **Runner-contract baseline.** Job pins-planning-baseline-002: the benchmark's own
   `train.py` + `validate.sh`, bundled verbatim (digests equal the read-only clone's:
   train.py `a3c6bcf1...`, validate.py `b597e7f8...`, validate.sh `3f06ca48...`),
   exit 0, `[validate] CONTRACT OK`; both eval AUC prints agree at **0.6108** on the
   28,104 eval rows. The holdout was never copied into any workdir. Dependencies
   pinned: python 3.13.18, pandas 2.3.3, numpy 2.5.4, xgboost 3.4.1,
   scikit-learn 1.9.1.
5. **Paired model-vs-reference intervals (the decisive numbers).** Job
   pins-planning-baseline-002, derived evidence on the identical eval rows after the
   verbatim contract run: model - procedure_type **+0.0558** [0.0467, 0.0626] row /
   [0.0462, 0.0654] LPA-cluster; model - lpa_hist **+0.0694** [0.0622, 0.0766] /
   [0.0597, 0.0792]; model - shipped_rate_feature **+0.0686** [0.0619, 0.0756] /
   [0.0596, 0.0800] - 150 resamples, every interval excluding zero under both the
   row-level and the LPA-clustered protocol. The references were reimplemented
   independently (pandas groupby), not imported from the build job's score.py; the
   shipped-rate-feature reference scores the artifact's own `lpa_allow_rate_prior`
   column, cross-checking the LPA-rate implementation (0.5422 vs 0.5414).
6. **The rebuild defect that produced this artifact, recorded not papered over.**
   Job pins-planning-baseline-001 failed at the verbatim `train.py` predict step:
   `floor_space_sqm` carried the publisher's literal prose (`Under 200 sq m
   floorspace`) in 6 of 28,104 eval rows, arriving object-dtype. The single permitted
   rebuild (pins-planning-002) mapped unparseable prose to missing and ran a
   worker-side synthetic probe that settled the open category-dtype question before
   the writer ran: the verbatim predict path accepts category dtypes under
   xgboost 3.4.1, so string levels ship verbatim and 001's category-column listing
   was the dtype validator's message shape. train.csv and holdout.csv are
   sha256-identical to 001; eval.csv differs only in those 6 cells. A second failure
   of this defect class would mean re-targeting, not a third rebuild.

## Suitability notice (version-bound, applies to v2026.10 / this artifact)

Retained for **retrospective model-development research**. The evaluation contract
requires `isolated_rows` for honest evaluation - the LPA-history features embed other
rows' labels (`lpa_last_outcome` is the previous same-LPA decided case's label) -
while the shipped illustrative runner passes the whole eval feature table to the
predictor, so unrestricted-access scores overstate honest performance. The publisher
exposes the current rolling-database edition only (no historical vintages), so
training-label timing and full-row historical availability are **unverified**; the
vintage is the **pinned 2026-10-22 edition**; selection is at prediction time on the
row's own registration fields, with the decided-cases-only population fixed by the
publisher itself (in progress, withdrawn and turned away cases are excluded from the
extract) - an outcome-observability conditioning recorded as a limitation. Supported:
retrospective research, method comparison, agent evaluation with the labeled eval
split as development/validation and the holdout sealed. Not supported: operational
screening claims, point-in-time historical reconstruction, live validation-instant
prediction claims. Structural qualification and baseline scores do not certify
operational validity.

## What this does NOT cover

- **No agent or harness experiment** was run on this artifact; the baseline is a
  single XGBoost pass through the runner contract and says nothing about
  coding-agent outcomes.
- **The holdout was never evaluated.** It ships as an asset so a future frozen-design
  evaluation can use it; no holdout figure exists anywhere in this package.
- **No historical-vintage or operational claim.** One pinned edition exists; none is
  reconstructed, and training-label timing stays unverified.
- **The model's per-validation-year AUC and Brier were not computed** (the
  references were computed per year; the model was not). No per-year model figure is
  claimed anywhere in this package.
- **The headroom finding is scoped**: one model configuration with no re-tuning, two
  validation years of eval coverage, row-level and LPA-clustered intervals. Beating
  the measured references does not enumerate all simple rules and does not prove a
  causal signal; the calendar-identity control was degenerate rather than
  independent.
- **Isolated-rows evaluation is not enforced** by the shipped runner; the honest
  protocol is the artifact's stated requirement, and no unrestricted-access score is
  quoted as if it were an isolated-rows result.
