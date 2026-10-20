# Chicago food inspections violation-code suite — `v2026.10`

First release. A leakage-checked, time-split **40-task multi-label suite** built from the City of
Chicago's public **Food Inspections** records: given everything documented about an establishment
and its own prior inspections **before an inspection begins**, predict **which violation codes the
inspector will record**. The multi-label question ships as one binary runner task per floor
violation code (`code_01` … `code_60`, 40 shipped), plus the joint matrix `labels.csv`.

**226,417 inspections**, three time-separated splits identical in every config, City of Chicago
open data. Combined artifact version
`c951bf5b42a0bfd20fea52f645486ecbd450ebef9d8c5387f01af40f70b58102` (derived from the 40 per-config
gate versions recorded in `MANIFEST.json` → `levels`; it is not itself a gate output). **Private at
this stage** — prepared for review; publication is a separate, operator-approved step that changes
no data byte.

## Get it

```bash
git clone https://github.com/earino/chicago-food-inspections.git   # private until publication
cd chicago-food-inspections
python3 get_dataset.py --dest ./task --config code_38    # one config, ~32 MB
python3 get_dataset.py --dest ./task                     # everything, ~1.3 GB
( cd task/code_38 && sha256sum -c ../../SHA256SUMS )
python3 code/qualify_dataset.py ./task/code_38           # the qualification gate, 32 checks
sh baseline/reproduce_baseline.sh ./task code_38          # the recorded baseline for that config
```

## What ships

GitHub does not allow `/` in asset names, so the 201 assets are flat (`code_38-public-train.csv`);
`get_dataset.py` restores the runner layout: `<config>/public/{train,eval}.csv`,
`<config>/private/holdout.csv`, `<config>/{meta,quality}.json`, and `labels.csv` at the root.

| split | period | inspections |
|---|---|---|
| train | 2010-01-01 to 2020-12-31 | 156,841 |
| eval | 2021-01-01 to 2023-12-31 | 35,358 |
| holdout | 2024-01-01 to 2026-09-30 | 34,218 |

Every config ships the identical pool and the identical 18-column shape; only the target column
`code_<NN>` and the one config-specific feature `prev_code_present` differ. The holdout is part of
the package; it must stay out of an evaluated agent's workspace during a benchmark run.

## What was checked before this was staged

- **Qualification gate 1.3.0: 32 checks × 40 configs, 0 failures**, on a worker over each config's
  full rows (1.26 GB across the suite) — leakage, prediction timing, units/frames, split capacity
  and boundary integrity, and the runner's input contract.
- **No leakage:** `violations` (the label source, with all comment text) and `results` (the
  inspector's outcome) are excluded from every file, not merely unlisted; the other codes' label
  columns are absent from each config (they parse from the same post-visit blob, so as features
  they would be cross-label leakage); no shipped column separates the classes on its own.
- **Splits are temporal and disjoint**, identical in every config; no `inspection_id` appears in two
  splits; eval and holdout carry both classes in every config; declared counts recomputed from the
  rows by the gate.
- **Digest chain:** every component digest in every gate report was cross-checked against the
  staging release's own asset list when the expected artifact was built, so the manifest cannot
  describe bytes that were never uploaded.
- **Provenance:** the build pulled 316,205 source rows anonymously over 46 pages ordered by the
  unique `inspection_id`; 226,417 make the modelling pool; 40 codes clear the floor (≥ 1% pool
  rate, ≥ 30 positives on ≥ 20 distinct days in every window), 8 more cleared the rate floor only,
  13 of 61 observed codes never cleared it.

## Measured — baselines on every config, one job

`food-baseline-003`: every config's bytes fetched from staging (digest-verified on arrival),
**re-accepted through the gate's `--accept` against that config's own gate report before scoring**,
then run through the benchmark's own `train.py` and `validate.sh`, unmodified (hashes recorded).
**40/40 `CONTRACT OK`; `train.py` and `validate.py` agree on every config.**

| | |
|---|---|
| baseline eval AUC across the suite | **min 0.5187** (`code_32`) · **median 0.7208** · **max 0.8292** (`code_58`) |
| configs clearing the persistence reference | **38/40** (headroom +0.028 to +0.247); `code_14` and `code_32` do not |
| `code_38` vs its earlier sanity check (`food-baseline-002`) | identical: eval AUC **0.6326**, same accepted artifact version |
| job cost | worker `cpx32`, Helsinki, 376.5 s, exit 0, destroyed and reconciled |

Eval positive rates run from 0.0015 to 0.56 across the suite — read each AUC against its own
config's rate, never against 0.5. Baselines are floors, not results. **No agent or harness
comparison has been run**, and none should be inferred.

Per config (eval split; persistence AUC = `prev_code_present` alone, measured on the build):

| config | eval positive rate | baseline eval AUC | persistence AUC | headroom |
|---|---|---|---|---|
| `code_01` | 0.059958 | 0.6791 | 0.5755 | +0.1036 |
| `code_02` | 0.117597 | 0.6709 | 0.5873 | +0.0836 |
| `code_03` | 0.102919 | 0.7380 | 0.5321 | +0.2059 |
| `code_05` | 0.086656 | 0.7413 | 0.5067 | +0.2346 |
| `code_06` | 0.005063 | 0.7422 | 0.5753 | +0.1669 |
| `code_08` | 0.006675 | 0.7573 | 0.5432 | +0.2141 |
| `code_09` | 0.006448 | 0.7184 | 0.5492 | +0.1692 |
| `code_10` | 0.228689 | 0.6199 | 0.5221 | +0.0978 |
| `code_11` | 0.001471 | 0.6543 | 0.5188 | +0.1355 |
| `code_14` | 0.007042 | 0.5902 | 0.5977 | −0.0075 |
| `code_16` | 0.085667 | 0.7344 | 0.5562 | +0.1782 |
| `code_21` | 0.014367 | 0.6910 | 0.5499 | +0.1411 |
| `code_22` | 0.064794 | 0.7441 | 0.5467 | +0.1974 |
| `code_23` | 0.016545 | 0.7277 | 0.5989 | +0.1288 |
| `code_25` | 0.036541 | 0.8074 | 0.5884 | +0.2190 |
| `code_29` | 0.006986 | 0.6708 | 0.5662 | +0.1046 |
| `code_32` | 0.004327 | 0.5187 | 0.5478 | −0.0291 |
| `code_33` | 0.045930 | 0.6054 | 0.4649 | +0.1405 |
| `code_35` | 0.012303 | 0.6049 | 0.5768 | +0.0281 |
| `code_36` | 0.087873 | 0.6994 | 0.5092 | +0.1902 |
| `code_37` | 0.127637 | 0.7681 | 0.6205 | +0.1476 |
| `code_38` | 0.207450 | 0.6326 | 0.5275 | +0.1051 |
| `code_39` | 0.108745 | 0.7208 | 0.5828 | +0.1380 |
| `code_40` | 0.046977 | 0.7386 | 0.6151 | +0.1235 |
| `code_41` | 0.067283 | 0.7545 | 0.6238 | +0.1307 |
| `code_43` | 0.039567 | 0.7856 | 0.6076 | +0.1780 |
| `code_44` | 0.042395 | 0.7306 | 0.6084 | +0.1222 |
| `code_45` | 0.040896 | 0.7441 | 0.6307 | +0.1134 |
| `code_47` | 0.299480 | 0.7301 | 0.6267 | +0.1034 |
| `code_48` | 0.079473 | 0.6822 | 0.5008 | +0.1814 |
| `code_49` | 0.302873 | 0.7473 | 0.6558 | +0.0915 |
| `code_51` | 0.260648 | 0.6814 | 0.5753 | +0.1061 |
| `code_52` | 0.026133 | 0.6786 | 0.5079 | +0.1707 |
| `code_53` | 0.185333 | 0.6930 | 0.5482 | +0.1448 |
| `code_54` | 0.061881 | 0.6765 | 0.5359 | +0.1406 |
| `code_55` | 0.560778 | 0.6847 | 0.6153 | +0.0694 |
| `code_56` | 0.218649 | 0.7029 | 0.6014 | +0.1015 |
| `code_57` | 0.152328 | 0.7639 | 0.5993 | +0.1646 |
| `code_58` | 0.177357 | 0.8292 | 0.5827 | +0.2465 |
| `code_60` | 0.077267 | 0.7632 | 0.5942 | +0.1690 |

## Known properties, stated rather than hidden

- **The 40 tasks share one pool.** They are 40 targets on the same rows, not 40 datasets; scores
  across configs are correlated through the shared rows and history features.
- **Two codes' baselines do not beat persistence.** On `code_14` and `code_32` the XGBoost
  baseline scores no better than "was this code cited on the licence's most recent inspection";
  a model for those codes has to earn its keep against that one-feature floor first.
- **The label is what was recorded, not what happened** — an inspector's citation, with all the
  programme's scheduling and inspector assignment effects inside it.
- **The pool is selected**: only inspections with a recorded Pass / Fail / Pass w/ Conditions
  disposition and a parseable violations blob; ~90k portal rows are outside it.
- **Positive rates drift by era** in both directions (e.g. `code_03` 0.102 → 0.047 train → holdout;
  `code_47` 0.299 → 0.308); per-config rates are recorded in `measurements.json`.
- **`license_` spans split windows by design** — prior history is the point — and is declared a
  feature, with `inspection_id` as the unique per-row entity key the gate checks.
- **Not an official City of Chicago product**; the City's Data Terms of Use govern the data
  (see `LICENSE.md`), including its right to require termination of use for any reason.

## Provenance and cost

| | |
|---|---|
| Build (all 40 configs + `labels.csv`) | worker `cx23`, Helsinki, 2 vCPU / 4 GB, **510 s**, 46 pages + 1 count probe, 1,260,504,640 B of split files |
| Gate | 40 × 32 checks on the worker, 0 failures |
| Baseline suite | worker `cpx32`, **376.5 s**, fetch 1,260,835,814 B verified on arrival, 40 × accept + train + validate |
| Extraction cost probe (coordinator class) | 20,000 rows: 5 requests, 28,948,432 B, 23.2 s; the ~458 MB full-pull figure is an **estimate** from that probe |
