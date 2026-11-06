# Release notes - v2026.11

## What this is

The first release of `ab-wildfire-ia-escape`: an all-cause, per-wildfire
initial-attack escape prediction task on Alberta Wildfire's own assessment
record (Forest Protection Area, 2006-2025, 27,828 wildfires). At the
publisher-documented initial-assessment instant, predict whether the wildfire
reaches 100 ha final area burned.

- artifact `c2c8ceb56c7ff52aaf748473e1251725c4ee86912edb9b17387e6b44d0e43da2` (gate 1.5.0, failed checks: none, exact-byte `--accept`
  on the worker in job `abwildfire-build-001`; re-accepted from fetched bytes in job
  `abwildfire-baseline-002` before any score existed)
- splits by the assessment instant's calendar year: train 2006-2015
  (15,864 rows / 297 positives), eval 2016-2020 (5,707 /
  104), holdout 2021-2025 (6,257 / 257, sealed)
- source: the Government of Alberta's pinned Historical wildfire data
  2006-2025 CSV (sha256 8b6ed447ab0f958dbe845a53dc15362b8ef5c0810ad9420d2143f9f5ee010a72); OGL-Alberta v2.2, attribution carried
  verbatim

## The recorded finding

Two comparisons travel together, both pre-registered before any score existed
and both on the identical 5,707 eval rows (2016-2020):

1. **The runner-contract baseline** (benchmark `train.py` + `validate.sh`, one
   XGBoost pass) scored eval AUC **0.9554**. Verdict under the
   pre-registered rule (beat EVERY triad member with a day-clustered CI
   excluding zero in your favour): **headroom_demonstrated** - model minus persistence
   [0.0154, 0.0871], model minus calendar/identity [0.1911, 0.2998], and the model's own
   day-cluster AUC CI [0.9382, 0.9686] against the degenerate constant member.
   Supplementary: the runner model sits +0.0348 from the
   construction-time logistic reference (0.9206) - both are models, so
   that is not a deciding member.
2. **The construction-time triad** (measured post-acceptance on the same rows):
   persistence (`assessment_hectares`) 0.9096, calendar/identity prior
   0.7130, simple full-feature logistic 0.9206, majority-class
   accuracy 0.9818. The simple logistic's edge over persistence is
   **INCONCLUSIVE**: +0.0111 with day-cluster CI [-0.0292, 0.0514] (the interval
   contains zero - an inconclusive difference, not parity).

**Headroom is demonstrated under the pre-registered rule** - the runner-contract model beats every triad member with a day-clustered paired bootstrap 95% CI excluding zero in its favour, on eval 2016-2020 only; the holdout (2021-2025) is sealed and has never been scored. The honest reading travels with the number: the persistence analogue (the fire's own observed size at assessment) ranks escape at 0.9096 on its own, and the construction-time simple logistic reference's edge over it is INCONCLUSIVE (+0.0111, CI [-0.0292, 0.0514], interval contains zero). No figure from this dataset may be quoted without the comparison above beside it. No re-tuning of threshold, window, label or features happened after any score.

The holdout (2021-2025) stays sealed; no holdout figure exists. No agent or
harness comparison was run and none is implied. The secondary
containment-duration formulation (42.0% of fires already under control at the
assessment instant) is a possible separate task instance, deliberately not
shipped here.

## Contract limitations stated everywhere

- **Retrospective research:** the archive is ONE current compilation (no
  historical per-fire vintages, no first-publication ledger); the publisher
  documents in-place revision of area, cause and location, and the 2019
  aggregate revision is measured at -10.4% against the publisher's own
  season statistics. Training-label timing is UNVERIFIED; no operational
  as-of claim is made (`use: retrospective_research`, `access:
  isolated_rows`, vintage `current_snapshot`).
- **Label-flip exposure bounded:** 89 fires lie within +-20% of the
  100 ha threshold; the threshold itself was fixed before any score and never
  re-tuned.
- **No timezone marker in the source:** timestamps are read as America/Edmonton
  local operational time, confirmed against the official 2016 Horse River
  review (a declared, corroborated assumption).
- **Non-stationarity:** holdout prevalence 4.11% vs eval 1.82%
  (the 2023 record season); recorded as a property, not repaired.
- **One jurisdiction, one record system:** generalisation beyond Alberta's
  Forest Protection Area and the 2006-2025 regime is not established.

## What is not covered

See `VERIFICATION.md`: no agent/harness loop was run, the holdout was never
scored, and the persistence-strong structure of the task is part of the
finding, not a promise of headroom in either direction.

## Provenance

Construction commit 3fc9d96 (build.py sha256 9200a30fa4cd6f7f97d3f9edc1fdf9ca0a84bf6d86f995e9a87d223d9d060418, run.sh
98a53051bad6545a1b822747c760d914fe8cdeaa8eaf5cc881fb3868819367f4, score.py 202402288a37d16c5163556ab94305ab79896ae2f82ebc224ec5c6a4e3f9687e); the gate is the canonical
`qualify_dataset.py` 1.5.0 (4fab8a34fe4f3357b7cd911087bfa243c56a96d8720e40d0d4cb2169100404d1); `baseline/` ships the harness
benchmark's runner files verbatim; `publisher-data-dictionary-transcript.md`
is the verbatim transcription of the publisher's scanned dictionary (the
documentary evidence for every shipped field's timing). Licensing: MIT for our
code and documentation, CC0-1.0 for our rights in the derived compilation (our
contribution only), OGL-Alberta v2.2 preserved for the Government of Alberta's
wildfire records, with attribution - see `LICENSE.md`.
