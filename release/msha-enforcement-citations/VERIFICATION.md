# Verification

What was verified, on what, and by which command. Nothing here is asserted from memory: each line
names the evidence.

| what | how | result |
| --- | --- | --- |
| Artifact qualified | `python3 code/qualify_dataset.py <config>` on the worker, for each of the 45 configs (job `msha-002`) | **PASSED - gate 1.3.0, 32 checks per config, 0 failed, 45/45** |
| Gate reports describe the uploaded bytes | all 45 `qualification-*.json` reports fetched back from staging release 410471211 and read; the set with a report is exactly the set with a `public/train.csv` layout | **45/45, every report `ok: true`** |
| Digest chain | 50 collected assets (the 45 reports plus `meta.json`, `quality.json`, `labels.csv`, `summary.json`, `build_summary.json`, `container.log`) sha256-verified against the staging release manifest | **50/50 match** |
| Manifest digests are the gate's own | `expected_artifact.json` built from the gate reports by `scripts/build-msha-expected-artifact.py`; every per-config `artifact_version` read from the gate's own report | **226 files, digests not retyped** |
| The corrected feature is in the released bytes | `sec_75_400` `public/eval.csv` fetched from both the superseded (410447826) and accepted (410471211) releases, each verified against its published digest | **identical size/rows; exactly one column differs (`prev_target_cited`, 4,933 rows); label and all other columns byte-identical** |
| The correction is material | persistence baseline (`build_summary.json`), all 45 configs | **mean 0.754 -> 0.576, fell on all 45, rose on none (`sec_75_400` 0.9403 -> 0.6733)** |
| Baseline through the runner's contract | the accepted artifact's `sec_56_12004` files fetched from staging and measured in place; the benchmark's own `train.py` / `validate.py` / `validate.sh`, unmodified (job `msha-baseline-001`) | **eval AUC 0.8036 from both paths, `CONTRACT OK`; train AUC 0.8036** |
| Runner files are the benchmark's | sha256 of the bundled `train.py` / `validate.py` / `validate.sh` vs the committed task_template | `a3c6bcf1...` / `b597e7f8...` / `3f06ca48...` - **identical** |
| The worker ran the committed script | bundled `build.py` sha256 vs the committed `candidates/.../source/build.py` | **1c80c1ae... = committed (job msha-002); the superseded msha-001 ran b9ef8352...** |
| Worker cleaned up | server destroyed after collection; provider inventory read back | **0 servers** (destroyed 2026-10-12T10:30:15Z) |
| Package consistency | `python3 scripts/check-package.py release/msha-enforcement-citations` | **OK** |
| CI for the construction commit | GitHub Actions run for the pushed SHA | recorded in the factory repository's `STATE.md` |

## The baseline, in numbers (job `msha-baseline-001`)

On `sec_56_12004` (4th by pool prevalence; positive rate 0.0886 train / 0.1063 eval / 0.0996
holdout): the runner's own `train.py` prints **Eval AUC: 0.8036** (Training time: 2.0s), and the
independent `validate.py` re-run - which retrains and scores via `predict_proba` with the target
column removed - prints **0.8036, CONTRACT OK**. Both numbers were read back out of the
collected release assets (each sha256-verified against the staging release 412476894 manifest),
not from the console. The installed stack was recorded with the report: pandas 2.3.3, numpy
2.5.4, xgboost 3.4.1, scikit-learn 1.9.1, scipy 1.18.1.

The persistence reference on the same config: `prev_target_cited` alone scores **0.5831** eval
AUC (from the accepted build's own summary, collected and digest-verified). The full 24-feature
model clears it by 0.2205. `prev_target_cited` is the only single feature measured individually,
so no strongest-feature claim is made.

## What this verification does **not** cover

- **The full 226-asset download has been exercised only five files at a time.** The baseline job
  fetched one config's five files from staging and verified them in transit; the package's own
  `get_dataset.py` path - all 226 assets, `SHA256SUMS` verification, a gate re-run on fetched
  bytes - has not been run against this package's release, because the release it would read from
  is created by the packaging step itself. It is the first thing a consumer run must exercise
  (and the recording of that run belongs in this file when it happens).
- **The holdout was never scored.** No model selection, threshold choice or tuning used it. It
  ships labelled, as a reported result, not as a hidden test set.
- **Only one config of 45 has an end-to-end baseline.** `sec_56_12004` demonstrates the scoring
  path; the other 44 carry gate reports and per-config persistence references but no measured
  full-model AUC. A per-config baseline sweep is future work, not an implied claim.
- **No agent or harness comparison.** The baseline is one pass through the training and
  validation contract; nothing about coding-agent performance is measured or implied.
- **`labels.csv` is documented, not gated.** The joint multi-label matrix ships as the record the
  45 binary configs were instantiated from; the gated artifacts are the per-config directories.
- **The raw zips are not re-fetched.** The build streams them from the publisher; re-running
  `code/build.py` reproduces an extract from the *live* weekly-updated source, which will differ
  from this frozen artifact by design. The frozen bytes are what the digests pin.
