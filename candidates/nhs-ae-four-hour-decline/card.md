---
license: other
license_name: ogl-v3-attribution-plus-cc0-compilation
license_link: https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
language:
  - en
pretty_name: NHS England A&E Four-Hour Performance Month-over-Month Decline
size_categories:
  - 1K<n<10K
task_categories:
  - tabular-classification
tags:
  - tabular
  - health-services
  - emergency-care
  - nhs
  - united-kingdom
  - time-series
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

# NHS England A&E Four-Hour Performance Month-over-Month Decline ({RELEASE_TAG})

**Status: {STATUS_LINE}**

For an NHS England provider operating a consultant-led (Type 1) A&E department, will the
percentage of its Type 1 attendances admitted, transferred or discharged within 4 hours of
arrival **decline in month M+1 relative to month M**, given that provider's monthly A&E series
for all months through M? One row per (provider, target month); the label is computed from
month M+1's source row only.

The prediction instant is **the end of month M**, when month M's monthly CSV is published
(measured publication lag ~3 weeks). Every feature is derived from provider months <= M:
the within-4-hour rate and its lags and rolling summaries, attendances by department type,
over-4-hour counts, decision-to-admit waits and emergency admissions, plus the calendar.
Month M+1's counts never ship - only the binary label does.

- **Artifact version:** `{ARTIFACT_VERSION}`
- **Version tag:** `{RELEASE_TAG}` (use this revision for reproducibility)
- **Rows:** {ROWS_TOTAL} provider-months across three disjoint temporal splits
- **GitHub counterpart:** {GITHUB_REPOSITORY}

## Splits

| split | rows | target months | positive rate | distinct positive providers |
| --- | ---: | --- | ---: | ---: |
| `train` | 6,116 | 2019-01 .. 2022-12 | 53.7% | 133 |
| `eval` | 2,937 | 2023-01 .. 2024-12 | 50.3% | 124 |
| `holdout` | 2,538 | 2025-01 .. 2026-09 | 48.6% | 121 |

The splits are temporal and disjoint on the target month. The m/m-decline label is balanced in
every window by construction, which is exactly why it was chosen: the fixed standard thresholds
measured near-uniform positive rates in recent years (<95% -> 99.9% positive in the holdout;
<80% -> 95.8%), because the national four-hour standard deteriorated from ~83% (2018) to ~60%
(2026). The base rate's drift with the system's deterioration is a documented property of the
series, and the relative m/m label is threshold-free.

Positives cluster within providers (a declining provider tends to keep declining), so the
conservative independent-unit count is the distinct positive providers per window, quoted in the
table beside the row counts.

## Reference points

The bar a competent model must beat is **mean reversion** - score the row by
`rate_m - rate_mean_6m` - which measures **0.5659** rank AUC on eval and **0.6562** on holdout
(standard-library rank AUC on the written rows, measured at construction). Momentum
(`rate_delta_1m`) is anti-predictive (0.4161 eval / 0.3993 holdout), and a winter-only calendar
rule reaches 0.5473 / 0.5090. The runner-contract XGBoost baseline measured **0.5526** eval AUC
- below the mean-reversion reference, which is recorded as measured headroom information, not a
defect: any published solution should be compared against all three references, not the model.

## Source and provenance

- NHS England, A&E Attendances and Emergency Admissions statistical work area
  (monthly provider-level CSVs, 2018-04..2026-09, 102 files, 3,115,779 bytes), retrieved
  2026-10-21.
- Cross-check against the publisher's own summary product: August 2026 national Type 1
  within-4h 61.1% (publisher commentary) vs 60.86% recomputed on this panel at build time.
- Construction: `code/build.py`, executed by job `nhsae-002`; qualification gate 1.3.0,
  `ok: true`, 0 failed checks, artifact version `{ARTIFACT_VERSION}`.

## Licence

The source statistics are NHS England / Crown copyright materials under the **Open Government
Licence v3.0**; that attribution condition carries through to every copy of the derived data
("Contains public sector information licensed under the Open Government Licence v3.0"). Our
contribution to the derived compilation is dedicated **CC0-1.0**; our code is **MIT**. This is a
derived research dataset, not an official NHS England product. See `LICENSE.md` in the repository
for the full terms and attribution statement.

## Use with the runner

```bash
python3 get_dataset.py --dest ./task
python3 code/qualify_dataset.py ./task
sh baseline/reproduce_baseline.sh ./task
```
