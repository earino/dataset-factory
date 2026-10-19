# MSHA enforcement citations - will this inspection cite 30 CFR section X?

A derived, inspection-level prediction dataset built from the Mine Safety and Health
Administration's (MSHA) Open Government Data Sets. **45 binary prediction tasks** ship in this
release, one per frequently-cited 30 CFR section: for each MSHA inspection, predict - at the
moment the inspection begins - whether that section will be cited.

- **Prediction instant:** the start of the inspection (`INSPECTION_BEGIN_DT`), before any
  observation. Every feature is either a structural mine attribute, the inspection's own recorded
  trigger (activity, program area, office), the calendar position of the begin date, or a field of
  an earlier inspection of the same mine.
- **Target:** the section appears among the `PART_SECTION` values cited at that inspection
  (multi-label in the source: mean 5.79 sections per inspection, median 2). Each config is one
  binary instance of that multi-label problem; the joint matrix ships as `labels.csv`.
- **Scale:** 497,897 pooled inspections (2001-2025) - train 2001-2020: 415,088 rows /
  eval 2021-2023: 49,233 / holdout 2024-2025: 33,576 - identical across all 45 configs.
- **Splits:** temporal by inspection year, no random component, three disjoint windows.
- **Gate:** every config passed the qualification gate (version 1.3.0, 32 checks, 0 failed) on
  the full artifact on the worker that built it.

This release is **private**, prepared for human review. Nothing here has been published.

## Why this task

Enforcement citations are the outcome that mine-safety regulation actually produces, and the
cited standard is the piece with real content: it names the hazard (fire watch - 30 CFR
47.41(a) - versus housekeeping - 56.12004) rather than just "a violation happened". The source
tables are updated weekly by the publisher, every column is documented in the publisher's own
definition files, and the label arrives with a natural prediction instant - the moment the
inspector opens the inspection. No ML-ready package ships this task (the recorded novelty check
is in the factory repository; prior art predicts accident counts or which mines to inspect, not
the cited-standard set at a declared instant).

## What ships

226 release assets: 45 per-section config directories, each with the runner layout
(`public/train.csv`, `public/eval.csv`, `private/holdout.csv`, `meta.json`, `quality.json`),
plus the joint multi-label matrix `labels.csv` at the dataset root. Flat asset names on the
release (`sec_56_12004-public-train.csv`, ...); `get_dataset.py` restores the layout.

```
task/sec_56_12004/public/train.csv     task/sec_56_12004/public/eval.csv
task/sec_56_12004/private/holdout.csv  task/sec_56_12004/meta.json
task/sec_56_12004/quality.json         ... 45 configs ...
task/labels.csv                        (joint multi-label matrix, 93,605,740 bytes)
```

Per config: 25 columns - `event_no` (identifier), `inspection_date` (time column), 22 features,
the target column, and no others. The label source (`PART_SECTION`) and every post-hoc field the
publisher documents (significance, negligence, penalty, termination dates, on-site hours, ...)
are excluded from the shipped columns, not merely unlisted.

## Baseline (through the runner's own contract)

On `sec_56_12004` (4th by pool prevalence), the benchmark's unmodified `train.py` /
`validate.py` score **eval AUC 0.8036** (train 0.8036, so no overfit gap), `CONTRACT OK` from
both paths. The persistence reference - `prev_target_cited` alone, the corrected
most-recent-strictly-earlier semantics - scores **0.5831**, so the full model's headroom over the
target section's own persistence is 0.2205. Per-config persistence references for all 45 configs
are in `MANIFEST.json` (`measurements.levels`), measured on the same bytes.

## Use it with the existing runner

```bash
python3 get_dataset.py --dest ./task                # or: --config sec_56_12004
python3 code/qualify_dataset.py ./task/sec_56_12004
sh baseline/reproduce_baseline.sh ./task sec_56_12004
```

See `REPRODUCE.md` for the full path from a clean checkout, `DATA_DICTIONARY.md` for every
column's documented meaning and availability, and `VERIFICATION.md` for what has been verified
and by which command.

## Licensing

Our code and documentation: **MIT**. Our rights in the derived compilation: **CC0-1.0**, covering
our contribution only (row selection, the derived per-section labels, the declared prediction
instant, the partitions, the packaging). The source's own status - **US federal government work,
public domain by statute (17 USC 105)**, the publisher stating no terms - is preserved and not
relicensed. **This is a derived dataset, not an official MSHA or US Department of Labor product.**
See `LICENSE.md`.

Source: MSHA Open Government Data Sets (Violations, Inspections, Mines),
<https://arlweb.msha.gov/OpenGovernmentData/DataSets/>, accessed 2026-10-12.
