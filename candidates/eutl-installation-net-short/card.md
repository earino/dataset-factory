---
license: other
license_name: cc-by-4-0-commission-reuse-policy-plus-cc0-compilation
license_link: https://commission.europa.eu/legal-notice_en
language:
  - en
pretty_name: EU ETS Installation Net-Short (European Commission, Union Registry)
size_categories:
  - 100K<n<1M
task_categories:
  - tabular-classification
tags:
  - tabular
  - carbon-markets
  - eu-ets
  - emissions-trading
  - compliance
  - european-union
  - temporal-split
configs:
  - config_name: default
    data_files:
      - split: train
        path: data/public-train.csv
      - split: eval
        path: data/public-eval.csv
      - split: holdout
        path: data/private-holdout.csv
---

# EU ETS Installation Net-Short ({RELEASE_TAG})

**Status: {STATUS_LINE}**

At the close of compliance year t-1's surrender cycle (30 April of year t), a stationary
EU ETS installation has settled its t-1 verified emissions and surrendered allowances, and
holds a year-t free allocation that was fixed in advance by the phase-4 national
implementation measures - the registry publishes allocation rows through 2030.
**Will its verified emissions for year t exceed that free allocation - a net-short year in
which the operator must buy allowances or face the excess-emissions penalty?** One row per
(registry, installation, compliance year); the label is the year-t market position, which
the registry learns only when year-t emissions are reported the following spring.

Every shipped feature is a registry value settled at the instant: the installation's t-1
verified emissions, its t-1 and announced year-t free allocations, the derived margins and
its registry identity. The label source values (`VERIFIED_EMISSIONS(t)`, `ALLOCATION(t)`)
are excluded from every shipped file, all post-hoc registry fields (year-t surrender,
change-tracking and exclusion flags, snapshot date) are excluded by construction, and the
gate's single-column AUC sweep confirmed no shipped column determines the label.

- **Artifact version:** `{ARTIFACT_VERSION}`
- **Version tag:** `{RELEASE_TAG}` (use this revision for reproducibility)
- **Rows:** {ROWS_TOTAL} installation-years across three disjoint temporal splits
- **GitHub counterpart:** {GITHUB_REPOSITORY}

## Splits

| split | rows | compliance years | positive rate |
| --- | ---: | --- | ---: |
| `train` | 141,732 | 2006 .. 2019 | 45.5% |
| `eval` | 24,322 | 2020 .. 2022 | 74.0% |
| `holdout` | 22,151 | 2023 .. 2025 | 72.2% |

The splits are temporal and disjoint on the compliance year. Both classes appear in every
window and every year, and positives are carried by thousands of distinct installations
(11,357 train / 7,810 eval / 6,283 holdout). The rising base rate is the documented ETS
phase property - the free-allocation share fell while the cap declined (the phase-3
allocation cut is the build's known-event fixture) - reported per split and per year, not
smoothed.

## Reference points

The references the model had to beat, measured at construction on the written rows (rank
AUC, rate tables estimated on train rows only): calendar-only (registry x phase) reaches
**0.527 eval / 0.5708 holdout**, identity-only (registry) **0.5719 / 0.5708**, and the
persistence margin (t-1 net position) **0.8671 / 0.8789**. The runner-contract XGBoost
baseline - the benchmark's own unmodified `train.py` + `validate.sh` on the fetched,
digest-verified, gate-re-accepted bytes - measures **0.9199 eval AUC**, reproduced exactly
by validate.py's independent recompute. The model clears persistence by +0.0532, so the
level target stands; most of the edge is the announced-allocation margin rule (`margin_t`
alone: 0.8988 / 0.8881), the task's natural one-line solver rule, and the model adds
+0.021 beyond it. The label is persistent (P(short|short) = 0.857), so persistence is
quoted beside every model number. The holdout was not scored by anything.

## Source and provenance

- European Commission, Directorate-General for Climate Action - Union Registry Public
  Website, EUTL public extracts (`operators_yearly_activity` daily extract), fetched
  2026-10-22 (5,965,780 B, sha256 in `meta.json`; the extract refreshes daily).
- Cross-check against the publisher's own summary product: the shipped panel, summed
  over exactly EEA activity codes {10, 20-99}, matches the EEA's EU ETS data - DE 2022
  verified emissions exactly, 2023 within 4 t, free allocation within 4.3e-4.
- Construction: `code/build.py`, executed by worker job `eutl-001`; qualification gate
  1.4.0, 38/38 checks, 0 failed, artifact version `{ARTIFACT_VERSION}`; baseline job
  `eutl-baseline-001`, contract AUC 0.9199.

## Licence

The source data are Commission-owned Union Registry public extracts under the
**Commission reuse policy (CC BY 4.0)**: reuse is allowed provided appropriate credit is
given and changes are indicated, and those conditions carry through to every copy of the
derived data. Our contribution to the derived compilation is dedicated **CC0-1.0**; our
code is **MIT**. This is a derived research dataset, not the European Commission's
official product, and the Commission has not reviewed or endorsed it. See `LICENSE.md` in
the repository for the full terms and attribution statement.

## Use with the runner

```bash
python3 get_dataset.py --dest ./task
python3 code/qualify_dataset.py ./task
sh baseline/reproduce_baseline.sh ./task
```
