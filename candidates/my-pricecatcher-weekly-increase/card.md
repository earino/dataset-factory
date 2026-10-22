---
license: cc0-1.0
license_name: cc0-1.0-compilation-cc-by-4.0-source
license_link: https://github.com/earino/my-pricecatcher-weekly-increase/blob/main/LICENSE.md
language:
  - en
pretty_name: Malaysian retail price increases, week ahead (Johor)
size_categories:
  - 100K<n<1M
task_categories:
  - tabular-classification
tags:
  - economics
  - prices
  - malaysia
  - forecasting
---

# Malaysian retail price increases, week ahead

For an item-premise pair in Malaysia's PriceCatcher daily price panel, with at least three price
observations in ISO week W, predict whether the pair's **weekly modal price rises in week W+1**.

Derived from [PriceCatcher](https://data.gov.my/data-catalogue/pricecatcher) (KPDN and DOSM,
**CC BY 4.0**). The compilation is **CC0 1.0**; the source attribution must be preserved. Not an
official Malaysian government product.

## Contents

| Split | Rows | Positive rate | Target weeks |
| --- | ---: | ---: | --- |
| `data/public-train.csv` | 397,982 | 14.9% | 2023-11 .. 2024-12 |
| `data/public-eval.csv` | 280,468 | 17.5% | 2025 |
| `data/private-holdout.csv` | 154,279 | 20.4% | 2026 .. 2026-10-19 |

Scope: premises in the state of **Johor**. Eligibility requires three observations in week W; pairs
whose following week has fewer than three are counted as *unobserved outcomes* (143,978), not
silently dropped.

## Baseline

Runner-contract XGBoost: **0.7520 eval AUC**, reproduced identically by both scoring paths
(`CONTRACT OK`). References: item prior 0.5354, momentum (`delta_1w`) 0.5001, reversal
(`price_vs_mean4`) 0.4974, observation count 0.4769. The baseline clears every naive reference.

## Timing

The prediction instant is the end of ISO week W. Every feature is a merge on week-7k keys; the
build processes weeks in order, so no feature can read a later week.

## Limitations

- State-scoped: Johor only. Other states are not represented.
- The holdout is labelled and ships with the release; keep its labels outside an evaluated agent's
  workspace.
- The source is a live feed that revises monthly; a later rebuild will not reproduce these bytes.
- Price series are sparse and sentinel-coded (-1.0) where a lag is missing.

## Citation

KPDN and DOSM. PriceCatcher. data.gov.my; 2026. Derived dataset: week-ahead retail price increase,
Johor. CC BY 4.0 source, CC0 1.0 compilation.
