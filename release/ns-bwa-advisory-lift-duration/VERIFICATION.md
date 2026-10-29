# Verification record

What was actually run, on what bytes, and what it does **not** cover. Every
figure quoted in this package is measured; the command that produced each one
is recorded in `measurements.json` (`measurement_commands`).

## The artifact

The five shipped files are worker job **ns-bwa-001**'s output, constructed
from the pinned NS register (sha256 `60f77ac4...`, content current as of
2026-06-16, byte-identical to the discovery fetch). The construction code is
factory commit `f8ba545`: `code/build.py` (sha256 `cd23315c...`) and
`code/run.sh` (sha256 `219f66bb...`) are the exact bytes the worker executed.
The worker executed `score.py` at sha256 `e6f0e953...`; the shipped
`code/score.py` (sha256 `b674f5b5...`) is the same computation with one
corrected report-field echo (`report.artifact.version` ->
`report.artifact.artifact_version.digest`) - the earlier run printed
`artifact_version: null` in its references JSON; every number is unaffected.
Both digests are recorded here so the difference is visible, not hidden.

## What was verified, in order

1. **Qualification (full artifact, on the worker, before any figure existed).**
   Gate 1.5.0 (`skills/dataset-qualification/scripts/qualify_dataset.py`, the
   same file shipped as `code/qualify_dataset.py`): **46/46 checks, 0 failed**,
   including the timing block, the evaluation contract with both declared
   cross-row probes (site-level reverse-history covers 369/56/217
   train/eval/holdout rows), split windows, both-classes minimums, and the two
   in-file known-event fixtures (Maple Meadows Campground Inc, issued
   2024-08-31, lifted after 307 days -> holdout row with lift30 = 0; Canning
   1-day advisory -> lift30 = 1). Gate `--selftest` passed before the launch.
2. **Exact-byte acceptance.** `qualify_dataset.py --accept` against the
   collected report: **ACCEPTED for artifact
   `e8ed2a53eaf0453c8ed52aea336edb994d888ad11e7b76f7898b663f017180a8`** on the
   worker, and re-ACCEPTED in both later jobs (ns-bwa-baseline-001,
   ns-bwa-diag-001) against the fetched bytes. The report ships as
   `qualification.json`.
3. **References (post-acceptance, identical eval rows).** Job ns-bwa-001's
   `score.py`: persistence 0.6124 (Brier 0.2819), calendar 0.5075 (0.3101),
   reason 0.4307 (0.2440), facility constant (0.2429), majority accuracy
   0.6048; paired bootstrap (1000, seed 23): persistence - calendar +0.1014
   [0.0144, 0.1739], calendar - reason +0.0779 [0.0072, 0.1492], persistence -
   reason +0.1793 [0.1136, 0.2482]. Per-issue-year persistence AUC 0.6084 /
   0.6203 / 0.5991 against prevalence 0.7442 / 0.6400 / 0.4153.
4. **Runner-contract baseline.** Job ns-bwa-baseline-001: the benchmark's own
   `train.py` + `validate.sh`, bundled verbatim (digests equal the read-only
   clone's: train.py `a3c6bcf1...`, validate.py `b597e7f8...`, validate.sh
   `3f06ca48...`), exit 0, `[validate] CONTRACT OK`; both eval AUC prints agree
   at **0.5086**. The holdout was never copied into any workdir
   (materialize.log in the job's evidence).
5. **Per-row diagnostic.** Job ns-bwa-diag-001 (gate `--accept` re-run first,
   then validate.sh re-checked CONTRACT OK at 0.5086, then per-row
   `predict_proba` scores preserved): model - persistence -0.1038 with
   row-bootstrap interval [-0.1693, -0.0357] and site-clustered interval
   [-0.1706, -0.0383] (286 clusters), both **excluding zero**; model - calendar
   +0.0011 [-0.0866, +0.0723]; per-issue-year model AUC 0.5554 / 0.5018 /
   0.4886 and Brier 0.2298 / 0.3479 / 0.5178. Every reference figure recorded
   by ns-bwa-001 and the baseline's 0.5086 were **replicated by this second,
   independent implementation** to 4 decimal places on the same bytes
   (dependencies pinned in both jobs: python 3.13.18, pandas 2.3.3, numpy
   2.5.4, xgboost 3.4.1, scikit-learn 1.9.1).

## Suitability notice (version-bound, applies to v2026.10 / this artifact)

Retained for **retrospective model-development research** under an
**isolated-rows** protocol that is stated as a requirement, not enforced by the
shipped runner (the illustrative runner contract passes the whole eval feature
table to the predictor; the gate measured the same-site label recovery the
declared probes describe). The register is revised in place and publishes no
historical vintages, so training-label timing and full-row historical
availability are **unverified**; the vintage is the **current snapshot**
(2026-06-16 content); selection is at prediction time (eligibility is decidable
from the issue date and the vintage, never from the outcome). Supported:
retrospective research, method comparison, agent evaluation under the enforced
isolated-rows protocol. Not supported: operational/real-time forecasting
claims, point-in-time historical reconstruction, unrestricted-access scoring.
Structural qualification and baseline scores do not certify operational
forecasting validity.

## What this does NOT cover

- **No agent or harness experiment** was run on this artifact; the baseline is
  a single XGBoost pass through the runner contract and says nothing about
  coding-agent outcomes.
- **The holdout was never evaluated** (sealed until a design is frozen). It
  ships as an asset so a future evaluation can use it; no holdout figure exists
  anywhere in this package.
- **No historical-vintage claim.** The publisher revises in place; a future
  re-fetch measures churn, not what was knowable earlier.
- **No headroom claim.** The stock baseline trails the persistence reference
  with intervals excluding zero; nothing here demonstrates (or refutes) that a
  better model could beat it - see `RELEASE_NOTES.md` for the exact comparison.
- The baseline scope is eval-split only; per-year and Brier figures for the
  model come from the diagnostic job's per-row scores.
