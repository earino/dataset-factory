# Chicago food inspections — violation-code prediction (40-task multi-label suite)

A benchmark suite built from the City of Chicago's **Food Inspections** dataset (Chicago Department
of Public Health): given everything documented about an establishment and its own prior inspections
**before an inspection begins**, predict **which violation codes the inspector will record for this
visit**.

The multi-label question is realized as **40 binary runner tasks** — one per shipped violation code
— plus the joint multi-label matrix (`labels.csv`). Each task is a complete, independently gated
runner layout with its own target column `code_<NN>`.

- **Version:** 2026.10 (combined `artifact_version`
  `c951bf5b42a0bfd20fea52f645486ecbd450ebef9d8c5387f01af40f70b58102`, derived from the 40 per-config
  gate versions in `MANIFEST.json` → `levels`)
- **Rows:** 226,417 inspections — 156,841 train, 35,358 eval, 34,218 private holdout (identical pool
  in every config)
- **Source:** `https://data.cityofchicago.org/resource/4ijn-s7e5.json` — anonymous Socrata API,
  frozen at build time (2026-10-05), read with no credential
- **Code:** MIT. **Data compilation:** City of Chicago Data Terms of Use (see `LICENSE.md`)

## The task

**Given** an inspection that is about to happen — the establishment's facility type, City risk
category, ZIP and location, the inspection's own type (canvass, complaint, re-inspection, …), the
calendar position of the visit, and the licence's own strictly-earlier inspection history
(prior count and results, days since the last visit, prior fail rate, mean code count, and whether
**this code** was cited last time) — **predict** whether the inspector records violation code NN.

- **Unit:** one row = one inspection (`inspection_id`) of one licensed establishment (`license_`).
- **Target (per config):** `code_<NN>` = 1 iff code NN is among the codes parsed from the
  inspection's `violations` blob. The label source column `violations` never ships.
- **Prediction time:** the moment the inspection opens, before any observation. `inspection_date`
  is known when a canvass is scheduled or a complaint triggers a visit; everything the inspector
  observes or records during or after the visit is post-hoc and excluded — `violations` (the label
  source, including the per-violation comment text) and `results` (the outcome) are absent from
  every shipped file, not merely unlisted.
- **Population:** inspections with a recorded disposition in Pass / Fail / Pass w/ Conditions, a
  parseable `violations` blob, a non-null licence, and an `inspection_date` inside a split window.
  Of the portal's 316,205 rows, 226,417 make the pool.
- **Splits:** temporal, identical in every config, by `inspection_date`, with no random component:

| split | file | period | inspections |
|---|---|---|---|
| train | `<config>/public/train.csv` | 2010-01-01 to 2020-12-31 | 156,841 |
| eval | `<config>/public/eval.csv` | 2021-01-01 to 2023-12-31 | 35,358 |
| holdout | `<config>/private/holdout.csv` | 2024-01-01 to 2026-09-30 | 34,218 |

## The 40 shipped codes

Codes are parsed **by number** (`NN.` at a pipe boundary), never by description string — 28 of the
61 observed codes have more than one wording across the 16.7-year history. A code ships as a config
iff it clears the floor stated in advance: ≥ 1% of the modelling pool **and** ≥ 30 positives on
≥ 20 distinct positive days in every window.

`code_01, code_02, code_03, code_05, code_06, code_08, code_09, code_10, code_11, code_14,
code_16, code_21, code_22, code_23, code_25, code_29, code_32, code_33, code_35, code_36, code_37,
code_38, code_39, code_40, code_41, code_43, code_44, code_45, code_47, code_48, code_49, code_51,
code_52, code_53, code_54, code_55, code_56, code_57, code_58, code_60`

Eight further codes (12, 18, 19, 24, 30, 31, 34, 42) cleared the rate floor but not the per-window
minimums and do not ship; the remaining 13 of the 61 observed codes never cleared the rate floor.

The tasks are deliberately diverse: **eval positive rates run from 0.0015 (`code_11`) to 0.5608
(`code_55`)**, median 0.066. A rate-0.56 task and a rate-0.0015 task share bytes and shape but are
not comparable difficulty.

`labels.csv` at the dataset root is the joint matrix — all 40 code columns on all 226,417
inspections — so the set formulation is consumable without re-pulling the source. It is a data
convenience, not a runner config, and is not gated.

## What is in this package

201 release assets, ~1.29 GB (asset names are flat; `get_dataset.py` restores the layout):

| per config (× 40) | becomes |
|---|---|
| `code_<NN>-public-train.csv` | `code_<NN>/public/train.csv` |
| `code_<NN>-public-eval.csv` | `code_<NN>/public/eval.csv` |
| `code_<NN>-private-holdout.csv` | `code_<NN>/private/holdout.csv` |
| `code_<NN>-meta.json` | `code_<NN>/meta.json` |
| `code_<NN>-quality.json` | `code_<NN>/quality.json` |
| `labels.csv` | `labels.csv` (dataset root) |

`SHA256SUMS` carries the full digests keyed by the logical layout paths, and `MANIFEST.json` records
them with the per-config qualification results. `DATA_DICTIONARY.md` documents every column against
the publisher's own field reference.

## Download and use

```bash
python3 get_dataset.py --dest ./task                     # everything, ~1.3 GB
python3 get_dataset.py --dest ./task --config code_38    # one config, ~32 MB
( cd task/code_38 && sha256sum -c ../../SHA256SUMS )
python3 code/qualify_dataset.py ./task/code_38
sh baseline/reproduce_baseline.sh ./task code_38
```

`get_dataset.py` verifies every file's size and SHA-256 against the release's own records and
`SHA256SUMS`, and refuses to leave a mismatched file in place.

## Baseline

One baseline per config, through the runner's own `train.py`/`validate.sh` unmodified, all 40
measured in one job on a worker that first **re-accepted every config's fetched bytes through the
qualification gate's `--accept`** — so the scored bytes are proved to be the qualified bytes before
anything is measured (`food-baseline-003`; full evidence in the factory's
`baseline/baseline_result.json` and summarized in `MANIFEST.json` → `baseline`).

Read each config's AUC against **that config's own eval positive rate** (0.0015 to 0.56 across the
suite), never against 0.5, and against the persistence reference recorded per config
(`measurements.json` → `levels.<config>.persistence_baseline`: the eval AUC of `prev_code_present`
alone), which is the floor any model must beat to show it learned anything beyond "was this code
cited last time". Nothing here is an agent or harness score, and none is implied.

Measured in one job on all 40 configs (`food-baseline-003`; every config re-accepted through the
gate's `--accept` before scoring; both runner paths agreeing on every config):

| | |
|---|---|
| configs through the contract | **40/40 `CONTRACT OK`**, zero AUC disagreements between `train.py` and `validate.py` |
| baseline eval AUC | **min 0.5187** (`code_32`) · **median 0.7208** · **max 0.8292** (`code_58`) |
| headroom over the persistence reference | +0.028 to +0.247 on **38/40** configs; none on `code_14` and `code_32` (the baseline does not beat "cited last time" there) |
| `code_38` (the earlier sanity check) | reproduced exactly: eval AUC **0.6326**, same accepted artifact version as `food-baseline-002` |

The full per-config table (rate, baseline AUC, persistence AUC, headroom) is in
`RELEASE_NOTES.md`; the recorded evidence is summarized in `MANIFEST.json` → `baseline`.

## Findings and limitations

- **The label is what the inspector recorded, not what happened.** A code's presence means the
  inspector cited it; absence means they did not record it. Nothing in this dataset establishes that
  a violation occurred.
- **The pool is a selected population.** Only inspections with a recorded Pass / Fail / Pass w/
  Conditions disposition and a parseable violations blob are modelled; the ~90,000 portal rows
  outside that (no disposition yet, no violations text, no licence) are excluded — there is nothing
  to predict for them yet.
- **`license_` recurs across split windows by design.** Prior history is the point of the task, so
  the establishment's licence key appears in several windows. It is declared a feature
  (high-cardinality, with the reason recorded in `quality.json`), not an entity key; the row
  identifier `inspection_id` is the entity key and is unique per row in every split, which
  `quality.json` asserts (`id_columns_are_entity_keys: true`, `expected_duplicate_ids: 0`) and the
  gate verifies from the rows.
- **Positive rates drift by era.** Several codes' rates move materially between train and holdout
  (both directions — e.g. `code_03` 0.102 → 0.047, `code_47` 0.299 → 0.308). This is a property of
  the City's inspection programme across 16 years, not of the split; per-config rates are recorded
  in `measurements.json`.
- **The other codes' labels are deliberately absent from each config.** They parse from the same
  post-visit `violations` blob as the target, so shipping them as features would be cross-label
  leakage. `labels.csv` carries the joint matrix instead.
- **"Not an official product."** This compilation is derived from the source below; it is not
  published by, endorsed by, or affiliated with the City of Chicago.
- **The source is republished continuously.** This version is defined by the hashes here, not by the
  live endpoint; note the endpoint may already differ.

## Why this is not a mirror

The publisher's own deployed model (Chicago food-inspections-evaluation, 2015, and its 2019
hindsight analysis, arXiv 1910.04906) predicts a **single binary** outcome — critical violation
present or not — to prioritise canvass scheduling. Kaggle and Socrata host mirrors of the raw table.
No published formulation predicts the **set of violation codes** with a stated prediction instant, a
pre-inspection-only feature set, licence-history features and temporal splits; that formulation, the
40-task packaging, the per-config gating and the persistence references are this release's
contribution.

## Attribution and citation

Data provided by the City of Chicago, Department of Public Health — Food Inspections
(`4ijn-s7e5`), used under the **City of Chicago Data Terms of Use** (see `LICENSE.md`, which
carries the required disclaimers). Please credit the City of Chicago when redistributing this
compilation.

> City of Chicago, "Food Inspections", Chicago Open Data Portal.
> https://data.cityofchicago.org/d/4ijn-s7e5 (accessed 2026-10-05). Compilation by the Scout
> project, version 2026.10.

## Versioning

`2026.10` identifies this compilation. The exact bytes are fixed by the combined `artifact_version`
above and the 40 per-config gate versions in `MANIFEST.json` → `levels`; a rebuild from the live
endpoint will differ as the City republishes. Corrections ship as a **new version**; this version's
bytes are never replaced.
