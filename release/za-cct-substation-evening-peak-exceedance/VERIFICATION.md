# Verification record

What was run, on what bytes, and what it does **not** cover. Prepared while
this release is private; nothing here has been published.

## The artifact

`za-cct-substation-evening-peak-exceedance` artifact `9f2e10ce485635f65e695072e2bbd904024ebf58b1465d12fb969f8bb0692180` built by worker
job `za-cct-001` (server 174300532, cx23/hel1, 110 s, exit 0) from the pinned
publisher pages (FeatureServer table Switching_Substation_Load_Profile/0, item
bebf20c25bfa4ffaa7fc07a1a94ba287, 52,608 rows fetched anonymously in 54
requests, 67,346,440 bytes, every per-page sha256 pinned in `code/build.py`
- the build fails if any pinned bytes change). The five shipped files' digests
are the worker-written staging manifest entries for release 432591871 (tag
`job-za-cct-001`), cross-checked three ways before use and recorded in
`candidates/.../baseline/expected_artifact.json`.

## What was executed, in order

1. **Qualification (gate 1.5.0, full artifact, on the worker where the rows
   are):** `qualify_dataset.py <extract> --json --report ...` exited 0 with
   `ok=true`, `failed_checks=[]` over all 43,706 rows and 45 checks - leakage
   (no shipped column separates the classes; `date` declared high-cardinality
   with its reason), prediction timing (period_end instant 06:00 SAST, 0-day
   administrative-record lag; every feature a slot ending at or before the
   instant or an aggregate of strictly prior days), units and frames (MVA as
   published, SAST grid), splits (train/eval/holdout disjoint by year, both
   classes everywhere, clustered 227/246/247 distinct positive days
   recomputed from the declared event key), runner layout and meta agreement.
2. **Exact-byte acceptance before any score:** `qualify_dataset.py --accept`
   printed `ACCEPTED: /output/extract matches the qualified artifact
   9f2e10ce485635f6`. The gate report is shipped here as `qualification.json`
   (sha256 0f1bb6a9324c32806a24e5920fcbba472633508cc9d6e63491e9f8b6ffeafc94).
3. **Post-acceptance references (worker, score.py stage 4):** every rate table
   estimated from train (2022) rows only, evaluated on the 14,965 eval rows;
   holdout never opened. Recorded in `measurements.json`.
4. **Runner-contract baseline (worker job za-cct-baseline-001, server
   174337518, 41.6 s executor, exit 0):** the five gate-digest assets
   re-fetched from staging release 432591871 (8,420,906 bytes, 5/5 digests
   verified on arrival and cross-checked against the staging manifest and the
   live release asset list), re-`--accept`ed BEFORE any score (same ACCEPTED
   line), workdir materialized from the public splits only (the private
   holdout was never copied), the benchmark's own `train.py` + `validate.sh`
   run unmodified (bundled sha256 == runner_files.json, `unmodified: true`),
   `[validate] CONTRACT OK`. Both implementations printed eval AUC 0.5107
   (train.py's own Eval AUC and validate.py's independent predict_proba
   recompute agree). Dependencies on the worker: python 3.13.18, pandas 2.3.3,
   numpy 2.5.4, xgboost 3.4.1, scikit-learn 1.9.1. Staging release
   432863325 holds this job's reports.

The measured comparison, on the identical eval rows: `morning_ratio`
**0.7340** > `month_only` 0.6541 > `calendar_identity` 0.6504 ~
`persistence_prev_evening` 0.6502 > `identity_only` 0.5134 > model
**0.5107** (full ladder in README and measurements.json, with the paired
clustered bootstrap intervals). The stock runner trailing the reference by
0.2233 AUC is the recorded property this agent-headroom benchmark ships with.

## What this does NOT cover

- **No agent or harness comparison was run.** One XGBoost pass through the
  runner contract is not an evaluation of coding agents on this task, and
  nothing here implies one.
- **The holdout was never scored** and never copied into any runner workdir.
  Holdout evaluation requires a frozen design; until then its 1,382
  positives are unspent.
- **Training-label timing is UNVERIFIED.** The publisher serves 2022-2024 as
  one closed static table (created 2026-02..03, hasStaticData, no historical
  vintages), so the evaluation contract is retrospective research
  (`use=retrospective_research`, `access=isolated_rows`); eval is
  development/validation, holdout is final. No historical-forecasting
  certification is claimed.
- **Cross-row exposure is measured, not enforced:** the gate's real-artifact
  probe measured the morning-history delta attack at 44.9% eval mismatches
  (no recovery), and the sealed evening matrix bounds the evening-p95 delta
  attack at 0.995 on synthetic bytes, which is why no evening-derived column
  ships; honest evaluation should still keep rows isolated.
- **The stock-runner gap is not fully diagnosed:** four recorded candidates
  (train-date memorization; ratio not expressible as a stock feature; no
  misalignment or post-hoc reference; prevalence shift insufficient) come
  from code reading, not a counterfactual rerun; no model above the reference
  has been measured.
- **The label measures demand-as-dispatched:** the publisher's caveat (no
  correction for temporary load shifts or load-shedding fluctuations) carries
  through; 2022-2024 falls inside Cape Town's load-shedding regime.
- **Worker environment variance:** the baseline ran once, on one cx23 worker
  (2 vCPU); no seed-variance study is claimed beyond the runner's fixed seed
  42.

Worker cleanup for both jobs was provider-verified (servers 404 on read-back;
project+account inventory 0 servers / 0 primary IPs; re-confirmed read-only by
the 2026-11-03 follow-up).
