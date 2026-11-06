# Verification record

What was run, on what bytes, and what it does **not** cover. Prepared while
this release is private; nothing here has been published.

## The artifact

`ab-wildfire-ia-escape` artifact `c2c8ceb56c7ff52aaf748473e1251725c4ee86912edb9b17387e6b44d0e43da2` built by worker job `abwildfire-build-001`
(server 174889543, cx23/hel1, 102.1 s, exit 0) from the
pinned Government of Alberta CSV (Historical wildfire data 2006-2025, sha256
8b6ed447ab0f958dbe845a53dc15362b8ef5c0810ad9420d2143f9f5ee010a72, 10,400,030 bytes; the build asserts the digest and refuses any
other source). Population: 27,828 assessed Forest Protection Area wildfires
2006-2025, eligibility assessment-based with no outcome-conditioned rule.
Named-fire fixtures asserted in-build (Richardson 2011, Utikuma 2011, Zama
2012, Horse River 2016 485,123.6 ha, Chuckegg Creek 2019, McMillan 2019, three
2023 fires, already-controlled negative LWF002 2023) plus size-class
consistency (0 inconsistencies) and the publisher season-hectares cross-check
(2020-2024 within 1.0%; 2019 -10.4% = the documented spring revision).
The five shipped files' digests are the worker-written staging manifest entries
for release 437132110 (tag `job-abwildfire-build-001`), cross-checked against the
collected result and recorded in `candidates/.../baseline/expected_artifact.json`.

## What was executed, in order

1. **Qualification (gate 1.5.0, full artifact, on the worker where the rows
   are):** `qualify_dataset.py <extract> --json --report ...` exited 0 with
   `ok=true`, `failed_checks=[]` over all 45 checks - leakage (no shipped
   column separates the classes; `fire_id`, `assessment_ts`,
   `hours_start_to_assessment` and friends declared high-cardinality with
   their reasons), prediction timing (event_time instant = the publisher's own
   assessment timestamp; every feature documented "at the time of initial
   assessment" by the publisher's dictionary, transcribed verbatim; pre-instant
   ordering measured - reported_date at or before assessment for 27,828/27,828,
   dispatch_date after assessment for 2.41% so the dispatch block is excluded),
   units and frames (hectares, metres/minute, degrees C, %, km/h, decimal
   degrees, elapsed hours - all declared with their documented frames; the
   Horse River known-event fixture asserted against the official review), splits
   (train/eval/holdout disjoint by assessment-year windows, both classes
   everywhere, clustered distinct positive dates 156/79/
   128 recomputed from the declared event key), runner layout and
   meta agreement. The evaluation contract (retrospective_research /
   isolated_rows / unverified training-label timing / current_snapshot vintage
   with the 2019 aggregate-revision evidence and the 89-fire
   threshold-band bound) is declared in `quality.json` and gate-verified.
2. **Exact-byte acceptance before any score:** `qualify_dataset.py --accept`
   printed `ACCEPTED: /output/extract matches the qualified artifact
   c2c8ceb56c7ff52a`. The gate report is shipped here as `qualification.json`
   (sha256 16697cd8aef51394f84b125964104adea5bf9dd8536f4fde291f817469cb07bb).
3. **Post-acceptance references (worker, score.py stage):** every rate table
   estimated from train (2006-2015) rows only, evaluated on the 5,707
   eval rows; holdout never opened. Recorded in `measurements.json`.
4. **Runner-contract baseline + pre-registered deciding check (worker job
   abwildfire-baseline-002, server 174894664, 264.6 s, exit 0):** the
   five gate-digest assets re-fetched from staging release 437132110 (every
   sha256 verified on arrival and cross-checked against the staging manifest
   and the live release asset list), re-`--accept`ed BEFORE any score (same
   ACCEPTED line), workdir materialized from the public splits only (the
   private holdout was never copied into a workdir - the materialize log
   records it), the benchmark's own `train.py` + `validate.sh` run unmodified
   (bundled sha256 == runner_files.json, `unmodified: true`), `[validate]
   CONTRACT OK`. Both implementations printed eval AUC 0.9554.
   Dependencies on the worker: python 3.13.18, pandas 2.3.3, numpy 2.5.4, xgboost 3.4.1, scikit-learn 1.9.1. Staging release 437168266
   holds this job's reports.

The measured comparison, on the identical eval rows: runner model **0.9554**
vs persistence 0.9096 ([0.0154, 0.0871]), calendar/identity 0.7130
([0.1911, 0.2998]), majority constant (model day-cluster AUC CI [0.9382, 0.9686]), with
the construction-time triad beside it - persistence 0.9096, calendar
0.7130, simple logistic 0.9206 (logistic minus persistence +0.0111,
CI [-0.0292, 0.0514], INCONCLUSIVE). Verdict under the pre-registered rule:
**headroom_demonstrated**, eval 2016-2020 only.

## What this does NOT cover

- **No agent or harness comparison was run.** One XGBoost pass through the
  runner contract is not an evaluation of coding agents on this task, and
  nothing here implies one.
- **The holdout was never scored** and never copied into any runner workdir.
  Holdout evaluation requires a frozen design; until then its 257
  positives are unspent.
- **Training-label timing is UNVERIFIED.** The archive is one current
  compilation (no historical vintages, no first-publication ledger), so the
  evaluation contract is retrospective research (`use=retrospective_research`,
  `access=isolated_rows`); eval is development/validation, holdout is final.
  No historical-forecasting certification is claimed.
- **The 42.0% already-controlled-at-assessment stratum** makes the secondary
  containment-duration label a separate design decision; it is NOT shipped
  here and its diagnostics in `measurements.json` are measured context only.
- **The persistence-strong structure is part of the finding:** the
  construction-time logistic's edge over the one-feature persistence rule is
  INCONCLUSIVE (+0.0111, CI [-0.0292, 0.0514]), and the runner baseline's own verdict
  (headroom_demonstrated) is recorded beside it - whichever way it falls, no re-tuning of
  threshold, window, label or features may follow a score.
- **The consumer check runs in a fresh environment** against the released
  bytes (gate re-run, `--accept`, baseline reproduction, references
  recomputation) as the private-staging step per the dataset-release skill;
  its result is recorded in the candidate record and DESTINATIONS.json before
  any publication.
