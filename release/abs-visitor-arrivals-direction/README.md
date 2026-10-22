# Australian short-term visitor arrivals: will next month fall short?

A binary prediction task built from the Australian Bureau of Statistics' Overseas Arrivals and
Departures (OAD) panel, published through the ABS Data API. **Derived research dataset, not an ABS
product.**

At the moment the release for reference month M is published, predict whether short-term visitor
arrivals from a country of residence in the first month not yet published (M+1) will **fall short**
of the same month a year earlier - a year-on-year decline.

- **Prediction instant:** publication of the OAD release for month M. The panel is lag-gated: only
  months already published are used, and the target month M+1 is unpublished at that instant.
- **Rows:** 19,071 train / 4,140 eval / 3,920 holdout; positive rates 34.96% / 29.08% / 19.59%.
- **Universe:** 70 visitor-arrival series (50 named countries, Northern Ireland, nine "Other"
  groupings, nine regional totals and the total), 428 months from 1991-01 to 2026-08.
- **Excluded and counted:** the pandemic window 2020-01 .. 2021-12 (1,662 rows) is excluded rather
  than allowed to dominate; 224 rows fail the history requirement and 10 have an unobserved target.

## Baseline and references

| Predictor | Eval AUC | Holdout AUC |
| --- | ---: | ---: |
| Runner-contract XGBoost (shipped) | **0.6219** | not scored |
| Identity only | 0.5720 | 0.5317 |
| Calendar only | 0.5501 | 0.5364 |
| Persistence (YoY sign) | 0.3647 | 0.2256 |

Persistence is anti-correlated, so this is a mean-reversion and seasonality task, not a
"repeat last year" task. The full model beats every reference; the margin over the calendar-only
rule is +0.0718.

## Files

| Path | Contents |
| --- | --- |
| `public/train.csv` | 19,071 rows |
| `public/eval.csv` | 4,140 rows |
| `private/holdout.csv` | 3,920 rows |
| `meta.json` | task contract, columns, splits |
| `quality.json` | feature documentation, units, timing declaration |
| `baseline/` | the harness runner, unmodified |
| `code/` | the build that produced this artifact |

The holdout is labelled and ships with the release; keep its labels outside an evaluated agent's
workspace.
