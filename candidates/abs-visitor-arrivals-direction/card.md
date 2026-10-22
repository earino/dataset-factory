---
license: cc0-1.0
license_name: cc0-1.0-compilation-cc-by-4.0-source
license_link: https://github.com/earino/abs-visitor-arrivals-direction/blob/main/LICENSE.md
language:
  - en
pretty_name: Australian short-term visitor arrivals, next-month shortfall
size_categories:
  - 10K<n<100K
task_categories:
  - tabular-classification
tags:
  - economics
  - tourism
  - australia
  - forecasting
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

# Australian short-term visitor arrivals ({RELEASE_TAG})

**Status: {STATUS_LINE}**

**Rows:** 27,131 across the three splits.

At the moment the ABS publishes month M of Overseas Arrivals and Departures, will short-term
visitor arrivals from a given country of residence **fall short** in the first unpublished month
(M+1) relative to the same month a year earlier?

Derived from the ABS OAD panel (**CC BY 4.0**, "Source: Australian Bureau of Statistics"). The
compilation is CC0 1.0. Not an ABS product.

## Contents

| Split | Rows | Positive rate | Target months |
| --- | ---: | ---: | --- |
| `data/public-train.csv` | 19,071 | 34.96% | through 2022 |
| `data/public-eval.csv` | 4,140 | 29.08% | 2023-2024 |
| `data/private-holdout.csv` | 3,920 | 19.59% | 2025-2026 |

70 series, 428 months (1991-01 .. 2026-08). The pandemic window 2020-01..2021-12 is excluded and
counted (1,662 rows).

## Baseline

Runner-contract XGBoost **0.6219** eval AUC, reproduced by both scoring paths (`CONTRACT OK`).
References: identity-only 0.5720, calendar-only 0.5501, persistence YoY-sign 0.3647 (anti-correlated,
so this is mean-reversion and seasonality, not repetition).

## Limitations

- The source is revised monthly; a rebuild will not reproduce these bytes.
- The pandemic window is excluded by construction, so the model sees no crisis behaviour.
- The holdout is labelled and ships by design; isolate it for blind evaluation.
