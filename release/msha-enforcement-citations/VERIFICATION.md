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
| Consumer verification | clean-room container, no build-repo access, no credential (job `msha-consumer-001`, on the published bytes) | **PASSED on all 45 configs** - see below |
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

## Consumer verification: PASSED on the published bytes

Run in a clean-room container on a worker (job `msha-consumer-001`): **no access to the building
repository, no credential**. It was given the published package tree and the release assets exactly
as a consumer receives them - fetched by the worker host from the release the dataset is published
in (`earino/msha-enforcement-citations`, release 417059413, tag `v2026.10`: all 226 assets,
3,384,299,154 bytes, each against the sha256 pinned in the job's fetch spec, `failures: []`) - then
hashed the cloned package against `MANIFEST.json`, verified the fetched assets with `sha256sum -c`,
ran the published gate on **every one of the 45 configs**, and reproduced the baseline through the
published contract.

| step | result |
| --- | --- |
| published package vs `MANIFEST.json` | every listed file matched its recorded hash |
| assets fetched as a consumer receives them | 226/226, 3,384,299,154 bytes, `failures: []`, digests equal the `MANIFEST.json` entry for their level |
| `sha256sum -c SHA256SUMS` | OK - all 226 lines |
| published gate, all 45 configs | exit 0 on every config, `QUALIFICATION PASSED`, 32 checks each |
| gate artifact versions vs `MANIFEST.json` | all 45 equal the recorded `artifact_version` for their level |
| dependencies (the benchmark's declared ranges) | pandas 2.3.3, numpy 2.5.4, xgboost 3.4.1, scikit-learn 1.9.1 |
| baseline, `sec_56_12004` | `CONTRACT OK`, eval AUC **0.8036** from both contract paths - the recorded value itself |

Every gate artifact version equals the version `MANIFEST.json` records for the same level, so the
bytes a consumer receives are the gated bytes. The baseline reproduction returned the recorded value
to the digit - 0.8036 on both the `train.py` path and the independent `validate.py` re-run, against
a persistence reference of 0.5831 on the same config.


## What this verification does **not** cover

- **The documentation was revised after the consumer check ran.** The data assets were not touched:
  their digests are unchanged, the gate names the same artifact versions, and the release tag still
  carries the verified bytes. What changed is this document - the consumer row and section above -
  to record the `msha-consumer-001` pass; the revision reaches the dataset repository's `main`
  with the next documentation advance.
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
