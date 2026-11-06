# Verification record

What was run, on what bytes, and what it does **not** cover. Prepared while
this release is private; nothing here has been published.

## The artifact

`cpcb-aqi-exceedance` artifact `a749f0df2f9dd0103d0ba56524e1cc3638242fbc4710b0cac99603bcdef0d959` built by worker job `cpcb-aqi-build-004`
(server 174751006, cpx32/hel1, 924.6 s, exit 0) from the
pinned XKDR export of the CPCB CAAQM PM2.5 stream (data.xkdr.org; the build
asserts exported_at 2026-09-30T11:25:11+00:00 and 196,521,834 rows through /v1/meta and
refuses any other export). The panel: 717,429 station-days across
546 reporting stations (549
registered), fetched in 168 monthly requests, 54,138,890 bytes,
0 truncated, 0 unparseable. The five shipped files' digests are the
worker-written staging manifest entries for release 436180445 (tag
`job-cpcb-aqi-build-004`), cross-checked against the collected result and the
baseline job's on-arrival verification, and recorded in
`candidates/.../baseline/expected_artifact.json`.

## What was executed, in order

1. **Qualification (gate 1.5.0, full artifact, on the worker where the rows
   are):** `qualify_dataset.py <extract> --json --report ...` exited 0 with
   `ok=true`, `failed_checks=[]` over all 45 checks - leakage (no shipped
   column separates the classes; `station_id` and `date` declared
   high-cardinality with their reasons), prediction timing (event_time
   instant 23:59 IST day D; every feature an administrative-record value of
   day D or an aggregate of strictly prior days; the D+1 observability rule
   never reads the label value), units and frames (ug/m3 as published,
   naive IST calendar-day convention; the external 90 ug/m3 threshold is the
   publisher's own AQI band edge, pinned by the Delhi 2024-11-18 known-event
   fixture - 36/36 complete station-days exceed - and the
   monsoon 2023-08-15 negative control - 389 complete,
   1 exceed), splits (train/eval/holdout disjoint by year,
   both classes everywhere, clustered distinct positive days 1,248/351/352
   recomputed from the declared event key), runner layout and meta agreement.
2. **Exact-byte acceptance before any score:** `qualify_dataset.py --accept`
   printed `ACCEPTED: /output/extract matches the qualified artifact
   a749f0df2f9dd010`. The gate report is shipped here as `qualification.json`
   (sha256 d2d367b63b6cd59235251f4131845862783a462258f90416d30e1b7ad2882fea).
3. **Post-acceptance references (worker, score.py stage):** every rate table
   estimated from train (2019-2022) rows only, evaluated on the 126,570
   eval rows; holdout never opened. Recorded in `measurements.json`.
4. **Runner-contract baseline + pre-registered deciding check (worker job
   cpcb-aqi-baseline-001, server 174753994, 1043.7 s, exit 0):** the
   five gate-digest assets re-fetched from staging release 436180445 (every
   sha256 verified on arrival and cross-checked against the staging manifest
   and the live release asset list), re-`--accept`ed BEFORE any score (same
   ACCEPTED line), workdir materialized from the public splits only (the
   private holdout was never copied into any workdir - the materialize log
   records it), the benchmark's own `train.py` + `validate.sh` run unmodified
   (bundled sha256 == runner_files.json, `unmodified: true`),
   `[validate] CONTRACT OK`. Both implementations printed eval AUC 0.9734
   (train.py's own Eval AUC and validate.py's independent recompute agree to
   ~2e-6; the report's 1e-9 agreement flag is a recorded reporting defect).
   Dependencies on the worker: python 3.13.18, pandas 2.3.3, numpy 2.5.4, xgboost 3.4.1, scikit-learn 1.9.1. Staging release 436196921
   holds this job's reports.

The measured comparison, on the identical eval rows: model **0.9734** >
station_persistence 0.9689 > state_season_climatology 0.8617
(supplementary station_train_rate 0.7616; majority accuracy 0.8434;
global_rate degenerate, Brier 0.1351). Model minus persistence
+0.004491, CI95 [0.0038, 0.0052]; model minus climatology +0.1118, CI95
[0.1002, 0.1252]; model AUC CI [0.9713, 0.9753] entirely above 0.5; persistence minus
climatology +0.1073, CI95 [0.0959, 0.1208]. Verdict under the pre-registered rule:
**headroom_demonstrated**, eval 2023 only.

## What this does NOT cover

- **No agent or harness comparison was run.** One XGBoost pass through the
  runner contract is not an evaluation of coding agents on this task, and
  nothing here implies one.
- **The holdout was never scored** and never copied into any runner workdir.
  Holdout evaluation requires a frozen design; until then its 18,222
  positives are unspent.
- **Training-label timing is UNVERIFIED.** The archive is one pinned export
  (no historical vintages, no first-publication ledger), so the evaluation
  contract is retrospective research (`use=retrospective_research`,
  `access=isolated_rows`); eval is development/validation, holdout is final.
  No historical-forecasting certification is claimed.
- **Intraday publication latency at CPCB is unmeasured.** Day-D trailing
  completeness at the 23:59 IST instant is a declared assumption, recorded
  in `quality.json`'s timing block; the publisher's own daily bulletins show
  non-participating stations.
- **The model-over-persistence edge is small** (+0.004491 AUC, CI
  [0.0038, 0.0052]): demonstrated headroom under the pre-registered rule, not a
  claim of large headroom, and the persistence-carried structure of the label
  is part of the finding.
- **The consumer check runs in a fresh environment** against the released
  bytes (gate re-run, `--accept`, baseline reproduction, references
  recomputation) as the private-staging step per the dataset-release skill;
  its result is recorded in the candidate record and DESTINATIONS.json before
  any publication.
