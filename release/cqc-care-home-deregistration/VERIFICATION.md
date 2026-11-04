# Verification record

What was run, on what bytes, and what it does **not** cover. Prepared while
this release is private; nothing here has been published.

## The artifact

`cqc-care-home-deregistration` artifact
`afe9ee203f302f3ca41b9b01ad74a937e111d1b830590c7e662bb0b7b6df85d7` built by
worker job `cqc-chd-004` (server 174428318, 376.4 s, exit 0) from the pinned
CQC source bytes (Deactivated Locations 2026-11-02 edition, 27,644,723 B,
sha256 49dc3062...; January active-locations vintages 2018-2022 + 2024 + 2025,
per-file sha256 pinned in code/build.py). The five shipped files' digests are
the worker-written staging manifest entries for release 433536764, read back
live from the staging API and recorded in `candidates/.../baseline/expected_artifact.json`.

## What was executed, in order

1. **Qualification (gate 1.5.0, full artifact, on the worker where the rows
   are):** `python3 /workspace/qualify_dataset.py /output/extract --json
   --report ...` exited 0 with `ok=true`, `failed_checks=[]` over all 107,652
   rows - leakage (no shipped column separates the classes; `location_key`
   declared high-cardinality), timing (period_end instant, 0-day
   administrative-record lag, as-of asserted: 0/14,765 eval rows with a rating
   publication date after T; row selection reads only the T vintage), units
   and frames, splits (train/eval/holdout disjoint by instant, both classes
   everywhere, 757/761 clustered eval/holdout positives), runner layout and
   meta agreement.
2. **Exact-byte acceptance before any score:** `qualify_dataset.py --accept`
   printed `ACCEPTED: /output/extract matches the qualified artifact
   afe9ee203f302f3c`. The gate report is shipped here as
   `qualification.json` (sha256 6624400547a9b0e...).
3. **Post-acceptance references (worker, score.py stage 4):** every rate
   table estimated from train rows only, evaluated on the 14,765 eval rows;
   holdout never opened. Recorded in `measurements.json`.
4. **Runner-contract baseline (worker job cqc-chd-baseline-001, 63.4 s,
   exit 0):** the five gate-digest assets re-fetched from staging
   (13,155,319 bytes, 5/5 digests verified on arrival), re-`--accept`ed
   BEFORE any score (same ACCEPTED line), workdir materialized from the
   public splits only, the benchmark's own `train.py` + `validate.sh` run
   unmodified (bundled sha256 == runner_files.json, `unmodified: true`),
   `[validate] CONTRACT OK`. Both implementations printed eval AUC 0.5659
   (train.py's own Eval AUC and validate.py's independent predict_proba
   recompute agree). Dependencies on the worker: python 3.13.18, pandas
   2.3.3, numpy 2.5.4, xgboost 3.4.1, scikit-learn 1.9.1.

The measured comparison, on the identical eval rows: `rating_x_beds_rate`
0.5871 > model 0.5659 > `last_rating_rate` 0.5597 > ... (full ladder in
README and measurements.json). The model trailing the reference is a
recorded defect of the stock runner under this protocol.

## What this does NOT cover

- **No agent or harness comparison was run.** One XGBoost pass through the
  runner contract is not an evaluation of coding agents on this task, and
  nothing here implies one.
- **The holdout was never scored** and never copied into any runner workdir.
  Holdout evaluation requires a frozen design; until then its 761 positives
  are unspent.
- **Training-label timing is UNVERIFIED.** The Google Drive archive exposes
  the historical active-locations vintages, but no full-row availability
  ledger exists for them, so the evaluation contract is retrospective
  research (`use=retrospective_research`, `access=isolated_rows`); eval is
  development/validation, holdout is final. No historical-forecasting
  certification is claimed.
- **The register-event framing limit:** the label conflates cessation with
  re-registration (CQC's own in-file note; BMJ Public Health 2024 implies
  ~40-55% re-registrations/transfers). Successor linkage was not built.
- **Cross-row exposure is measured, not enforced:** gate probes measured
  pseudonym-successor coverage 0/0/0 and quasi-identifier (LA x beds x start
  year x rating x sector) eval/holdout coverage 0 (train 11,786 where labels
  are public anyway); honest evaluation should still keep rows isolated.
- **The stock-runner gap is not fully diagnosed:** the `instant`
  train-only-categorical finding is verified by code reading, not by a
  counterfactual rerun; no model above the reference has been measured.
- **Worker environment variance:** the baseline ran once, on one cx23 worker
  (2 vCPU); no seed-variance study is claimed beyond the runner's fixed
  seed 42.

Worker cleanup for both jobs was provider-verified (servers 404 on read-back;
project+account inventory 0 servers / 0 primary IPs).
