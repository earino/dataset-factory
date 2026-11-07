# Verification record

What was actually run, on what bytes, and what it does **not** cover. Every
figure quoted in this package is measured; the command that produced each one
is recorded in `measurements.json` (`measurement_commands`).

## The artifact

The five shipped files are worker job **ns-bwa-002**'s output, constructed
from the pinned NS register (sha256 `60f77ac4...`, content current as of
2026-06-16, byte-identical to the discovery fetch and to the v2026.10 build;
the rebuild changes the shipped frame, never the population). The
construction code is factory commit `0d36ffc`: `code/build.py` (sha256
`2253fe59...`), `code/run.sh` (sha256 `ee73a468...`) and `code/score.py`
(sha256 `ab4d9fd5...`) are the exact bytes the worker executed, per its
bundle-owner record. The gate shipped as `code/qualify_dataset.py` (sha256
`4fab8a34...`, version 1.5.0) is the repository's current gate, unchanged
from the v2026.10 package.

## What was verified, in order

1. **Pre-launch smoke on the coordinator** (before any worker spend): a
   synthetic 162-row register exercising both mandatory build fixtures; as-of
   recency semantics asserted (strictly-earlier only; same-(site, issue date)
   rows never see each other; blank-county sentinel; county recency
   recomputed independently); gate 1.5.0 two-phase PASSED plus exact-byte
   `--accept` ACCEPTED on the synthetic artifact; no synthetic column
   separates the label (pre-checked with the gate's own scorer); the
   register-side persistence helper unit-checked with a monkeypatched
   register; gate `--selftest` PASSED.
2. **Qualification (full artifact, on the worker, before any figure
   existed).** Gate 1.5.0: **44/44 checks, 0 failed**, including the timing
   block (event-time instant, administrative record), the evaluation contract,
   split windows, both-classes minimums, leakage scoring over every shipped
   column, and the assertion that the label source columns
   (`date_advisory_removed`, `length_of_advisory_in_days`, `lift14`) are
   absent from all shipped files.
3. **Exact-byte acceptance.** `qualify_dataset.py --accept`: **ACCEPTED for
   artifact `49bf4cfa427375c6b7bf90f85eb0330d78da0cc49197c119c396b6b7ea4c6144`**
   on the worker (job ns-bwa-002), and re-ACCEPTED on the baseline job's
   fetched bytes (ns-bwa-baseline-002) **before any score was computed**. The
   report ships as `qualification.json`.
4. **References (post-acceptance, identical eval rows).** Job ns-bwa-002's
   `score.py`: persistence 0.6124 (Brier 0.2819, covered 231/372, register
   recomputation asserted sha256-identical to the artifact's own vintage),
   calendar 0.5075 (0.3101), reason 0.4307 (0.2440), facility constant
   (0.2429), majority accuracy 0.6048; paired bootstrap (1000 resamples):
   persistence - calendar +0.1014 [0.0144, 0.1739], calendar - reason
   +0.0779 [0.0072, 0.1492], persistence - reason +0.1793 [0.1136, 0.2482].
   Per-issue-year persistence AUC 0.6084 / 0.6203 / 0.5991 against prevalence
   0.7442 / 0.6400 / 0.4153. All four reference figures are equal to the
   v2026.10 measurements - the register-side reimplementation of the
   persistence reference is validated by reproduction.
5. **Runner-contract baseline.** Job ns-bwa-baseline-002: re-accept of the
   five fetched assets against the gate's collected report BEFORE any score;
   the benchmark's own `train.py` + `validate.sh`, bundled verbatim (digests
   equal the read-only clone's: train.py `a3c6bcf1...`, validate.py
   `b597e7f8...`, validate.sh `3f06ca48...`), exit 0, `[validate] CONTRACT
   OK`; both eval AUC prints agree at **0.5068**. The holdout was never
   copied into any workdir (materialize.log in the job's evidence). The
   same runner measured 0.5086 on the superseded v2026.10 frame, so the
   integrity repair cost -0.0018 AUC.
6. **Coordinator-side byte pinning (this packaging).** The byte-pinned
   `meta.json`, `quality.json` and the gate report were fetched from private
   staging release 437529809 and verified against the worker-written staging
   manifest before being placed in this package; `get_dataset.py`'s EXPECTED
   digests are generated from the gate's artifact block.

## Suitability notice (version-bound, applies to v2026.12 / this artifact)

Retained for **retrospective model-development research** under an
**isolated-rows** protocol that is stated as a requirement, not enforced by
the shipped runner (the illustrative runner contract passes the whole eval
feature table to the predictor). The register is revised in place and
publishes no historical vintages, so training-label timing and full-row
historical availability are **unverified**; the vintage is the **current
snapshot** (2026-06-16 content); selection is at prediction time (eligibility
is decidable from the issue date and the vintage, never from the outcome).
Supported: retrospective research, method comparison, agent evaluation under
an enforced isolated-rows protocol. Not supported: operational/real-time
forecasting claims, point-in-time historical reconstruction,
unrestricted-access scoring. Structural qualification and baseline scores do
not certify operational forecasting validity.

## What this does NOT cover

- **No agent or harness experiment** was run on this artifact; the baseline is
  a single XGBoost pass through the runner contract and says nothing about
  coding-agent outcomes.
- **The holdout was never evaluated** (sealed until a design is frozen). It
  ships as an asset so a future evaluation can use it; no holdout figure exists
  anywhere in this package.
- **No historical-vintage claim.** The publisher revises in place; a future
  re-fetch measures churn, not what was knowable earlier.
- **No headroom claim.** The stock baseline trails the register-side
  persistence reference by 0.1056 on identical rows; nothing here demonstrates
  (or refutes) that a better model could beat it - see `RELEASE_NOTES.md` for
  the exact comparison.
- **No per-row diagnostic on this frame.** The v2026.10 diagnostic job
  (ns-bwa-diag-001) was not repeated for v2026.12, so this package carries no
  model Brier, no per-issue-year model figures, and no recomputed
  model-vs-persistence interval; the interval figures quoted in the notes
  belong to the superseded v2026.10 frame on the same eval rows and are
  labelled as such.
- **The frozen `quality.json` carries a v2026.10-era `known_event`
  declaration** naming two register rows and their durations, including one
  scored holdout row. For this internal-threshold task the gate requires no
  known-event fixture (it records "no external threshold, so no known-event
  fixture is required") and does not verify that block; the declaration is
  builder content inherited from v2026.10 inside bytes that are pinned by the
  accepted artifact version. No package document repeats its contents. The
  fresh adversarial pre-flip audit is mandated to rule on whether that
  declaration is acceptable as shipped or requires a fixture-to-train-row
  rebuild; a rebuild changes the artifact version and would be a new reviewed
  release.
