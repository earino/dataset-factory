# Malaysian retail price increases, week ahead

A binary prediction task built from Malaysia's PriceCatcher daily price-monitoring panel (KPDN and
DOSM, published through data.gov.my). **Derived research dataset, not an official Malaysian
government product.**

For an item-premise pair with at least three price observations in ISO week W, predict whether the
pair's weekly modal price is **higher in week W+1 than in week W**.

- **Prediction instant:** end of ISO week W (Sunday 23:59 MYT). Every feature is computed from
  observations dated on or before that instant. The publisher's bulk storage carries same-day rows,
  so no publication lag is modelled.
- **Universe:** Premises in the state of **Johor** - the artifact is state-scoped, and other states
  can be released later under the same construction.
- **Rows:** 397,982 train (target weeks 2023-11 .. 2024-12), 280,468 eval (2025), 154,279 holdout
  (2026 through 2026-10-19). Positive rate 14.9% / 17.5% / 20.4%.
- **Eligibility:** at least 3 observations in week W. Pairs whose week W+1 has fewer than 3
  observations have an *unobserved outcome* (143,978 of them) and are counted, not silently excluded.

## Baseline and references

| Predictor | Eval AUC |
| --- | ---: |
| Runner-contract XGBoost (shipped) | **0.7520** |
| Item prior (train-only share of weeks that rose) | 0.5354 |
| Momentum (`delta_1w`) | 0.5001 |
| Reversal (`price_vs_mean4`) | 0.4974 |
| Observation count | 0.4769 |

The baseline clears every naive reference by a wide margin: the signal is real, not a persistence
artefact.

## Files

| Path | Contents |
| --- | --- |
| `public/train.csv` | 397,982 rows |
| `public/eval.csv` | 280,468 rows |
| `private/holdout.csv` | 154,279 rows |
| `meta.json` | task contract, columns, split boundaries |
| `quality.json` | feature documentation, measurement frames, timing declaration |
| `baseline/` | the harness runner, unmodified |
| `code/` | the build that produced this artifact |

The holdout is labelled and ships with the release; keep its labels outside an evaluated agent's
workspace.
