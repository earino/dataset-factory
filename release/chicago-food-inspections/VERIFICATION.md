# Verification

What was checked, how, and what it does **not** establish.

Scope: this release was built, gated, baselined and package-checked by the publisher. Independent
verification by someone else has **not** happened, and nothing here should be read as if it had.

## 1. What the artifact is, and where it was built

The full suite — 40 per-code configs plus the joint `labels.csv` — was built **on a worker**
(job `food-001`, `cx23`, Helsinki, 2 vCPU / 4 GB, 510 s wall clock), never on the coordinator. The
build pulled 316,205 source rows anonymously over 46 pages ordered by `inspection_id` (unique per
row, so the paging order is total and stable), reduced them to the 226,417-inspection modelling
pool, and wrote 1,260,504,640 bytes of split files plus the 24,319,192-byte `labels.csv`.

Nothing is quoted in this package that was not measured on those bytes: every digest, count and
rate in `MANIFEST.json` and `measurements.json` is either read from the gate's own collected
reports or recomputed from them by a script that cross-checks against the worker's uploaded asset
list (`jobs/food-001.json` → `result.assets`) by (bytes, sha256).

## 2. The gate passed, on every config, on the full artifact

`qualify_dataset.py`, version 1.3.0, ran **on the worker against each config's full rows** (1.26 GB
across the suite, not a sample): **32 checks × 40 configs, 0 failures, 0 warnings**. The per-config
check list, identical in shape for every config:

- **Leakage** — every shipped column is declared; no answer source or post-hoc column is shipped; no
  shipped column separates the classes on its own; high-cardinality columns are declared as
  identifiers or free fields.
- **Prediction timing** — the prediction instant is declared; no feature is documented as post-hoc;
  the label source is not a feature; every feature is documented as available at the instant.
- **Units and frames** — the 10 measured columns declare unit and frame (e.g. latitude/longitude:
  decimal degrees, WGS84/EPSG:4326, as published; empty when the City publishes no coordinates).
  No external threshold is used, so no known-event fixture is required.
- **Splits** — windows machine-readable; files present and non-empty; eval and holdout each carry
  both classes; declared positive counts match the rows; clustered events counted by calendar day
  and matched from the rows; enough independent positive events; rates not uniform; actual date
  ranges disjoint and inside the declared windows; **no `inspection_id` in two splits**; zero
  repeated identifiers within splits, as declared (`expected_duplicate_ids: 0`).
- **Runner compatibility** — holdout private, train/eval public; `meta.json` carries every key the
  runner reads and agrees with the files; identifiers are not also features.

The 40 per-config gate reports were collected and **every component digest in every report was
cross-checked against the staging release's own asset list** by the expected-artifact builder, so a
report describing bytes that were never uploaded cannot pass. `MANIFEST.json` → `levels` records
each config's gate-produced `artifact_version`, and the package-level `artifact_version` is
**derived** from those 40 by a documented hash — it is not a gate output and is not presented as
one.

A passing gate is evidence about the files and declarations it can see. What it cannot see is
whether the source is what it is believed to be; that rests on the publisher's own column
documentation (cited per column in `DATA_DICTIONARY.md`) and is recorded in the factory's candidate
notes with the probe commands that produced it.

## 3. The label source is excluded from the bytes, not merely from a list

The label source (`violations`, including the per-violation comment text) and the inspector's
outcome (`results`) are the two post-visit fields. The gate verified per config that no answer
source or post-hoc column is shipped (`leakage.answer_source_absent`, `timing.no_post_hoc_feature`)
and that the label source is not a feature. The other 39 codes' label columns are likewise absent
from each config's files — they parse from the same post-visit blob as the target, so shipping them
would be cross-label leakage; the joint matrix ships separately as `labels.csv`, which is a data
convenience and is not gated and not a runner input.

## 4. The benchmark runner was not modified

The baselines ran through the runner's **existing** contract, with the three runner files verified
by hash before use and recorded in the run's own report:

| file | sha256 | status |
|---|---|---|
| `train.py` | `a3c6bcf13735bc85c52129ded68f839090dffdc268ebc3810dc61b2e6ea5e7e8` | unmodified |
| `validate.py` | `b597e7f84fed614e64b4a86fbecbd6ec0145916a24d0d221a796586976418e7b` | unmodified |
| `validate.sh` | `3f06ca48f11c2e05d331b4d8394284925de660c1d4b086d2f8243959e83b7e6d` | unmodified |

## 5. Baseline

All 40 configs were baselined in **one job** (`food-baseline-003`, worker `cpx32`, Helsinki,
376.5 s, exit 0): each config's five files fetched from private staging (1,260,835,814 bytes,
each asset sha256-verified on arrival, zero failures), **re-accepted through the gate's
`--accept`** against that config's own gate report (40/40 accepted — the scored bytes are the
qualified bytes), then trained and scored through the runner's contract.

- **40/40 configs: `CONTRACT OK`**, and `train.py`'s own AUC equals `validate.py`'s independent
  `predict_proba` recompute on every config (zero disagreements, to 4 decimals).
- Baseline eval AUC across the suite: **min 0.5187 (`code_32`), median 0.7208, max 0.8292
  (`code_58`)** — read each against its own config's eval positive rate (0.0015 to 0.56), never
  against 0.5.
- **`code_38` reproduced its earlier sanity-check measurement exactly** (`food-baseline-002`, same
  accepted artifact version `80a4291e3288dc07…`): eval AUC **0.6326** both times — and a third time,
  from the published bytes, by the fresh-environment consumer run (section 6): **0.6326** again.
- Persistence reference (the eval AUC of `prev_code_present` alone, measured on the build): the
  baseline clears it on **38 of 40 configs** (headroom +0.028 to +0.247) and does **not** clear it on
  `code_14` (−0.008) and `code_32` (−0.029) — for those two codes the baseline adds nothing over
  "was this code cited last time". Per-config table in `RELEASE_NOTES.md`; per-config persistence
  AUCs in `measurements.json` → `levels`.

Full evidence: the factory's `baseline/baseline_result.json` (generated from the job's own
`baseline.json`), the per-config accept/train/validate logs in the job's collected reports, and
the job's staging release `418648610`. No agent or harness comparison was run, and none is implied.

## 6. Fresh-environment consumer verification: PASSED on the published bytes

Run in a clean-room container on a worker (job `food-consumer-002`, `cpx32`, Helsinki, 145 s,
exit 0): **no dataset-factory access, no GitHub credential**. It received the published package
tree (byte-checked against `MANIFEST.json` before anything else ran) and the release assets exactly
as a consumer receives them — fetched by the worker host, which alone holds the credential, from
the release the dataset is published in (`earino/chicago-food-inspections`, private release
`v2026.10`: all **201 assets, 1,285,155,006 bytes**, each against the sha256 pinned in the job's
fetch spec, zero failures) — and then followed the published instructions end to end.

| step | result |
| --- | --- |
| published package vs `MANIFEST.json` | every listed file (22) matched its recorded hash |
| assets fetched as a consumer receives them | 201/201, 1,285,155,006 bytes, `failures: []`, laid out as `get_dataset.py` restores |
| `sha256sum -c SHA256SUMS` (the published verification command) | OK — all 201 lines |
| qualification gate `--accept`, all 40 configs | exit 0 on every config, each printing that the bytes "match the qualified artifact" (e.g. `code_38` → `80a4291e3288dc07…`) |
| baseline, `code_38` | `CONTRACT OK`, eval AUC **0.6326** from both contract paths — the recorded value itself |

The same check's **first attempt (`food-consumer-001`) did not pass, and that failure is the check
doing its job.** Steps 1–4 were green; step 5 died at the first execution of the published
materializer, because the package's `code/materialize.py` was another dataset's three-argument
variant that had been *recorded as shipped*: every hash-based check passed because the wrong file
was consistently the hashed file. Only running the published code caught it. The file was replaced
with the two-argument materializer the baseline jobs actually measured (data assets untouched —
`SHA256SUMS` byte-identical, all 201 asset digests unchanged, all 40 configs re-accepted), the
destination repository was updated (commit `0c765e3`), and the retry passed all five steps above.

Every gate artifact version the consumer re-accepted equals the version `MANIFEST.json` records
for the same level, so the bytes a consumer receives are the gated bytes, and the baseline
reproduction returned the recorded value to the digit.

## 7. Not covered

- **This document was revised after the consumer check ran.** The data assets were not touched —
  their digests are unchanged and the gate names the same artifact versions — and the passing
  consumer run above verified the package *with* the corrected `code/materialize.py` already in
  place (that correction preceded it). What changed after the check is this document — the consumer
  section above — and, with it, `MANIFEST.json`'s digest entry for this file; every other file the
  consumer verified is byte-identical to what it verified.
- **No anonymous read.** Both destinations are private at this stage; nothing here establishes that
  either is readable without a credential. That check happens at the publication flip and is
  recorded in `DESTINATIONS.json`.
- **No agent or harness comparison.** The baselines are floors through the runner's contract, not
  results about agents or models, and none is implied.
- **The source endpoint moves continuously.** The portal republishes daily; a rebuild from the live
  endpoint will not reproduce these bytes. The version is the hashes recorded here, and the frozen
  build's counts are recorded in `measurements.json` so drift is visible rather than silent.
