---
license: other
license_name: city-of-cape-town-open-data-terms-plus-cc0-compilation
language:
  - en
pretty_name: Cape Town Switching-substation Evening-peak Exceedance
size_categories:
  - 10K<n<100K
task_categories:
  - tabular-classification
tags:
  - tabular
  - electricity
  - substation
  - load-profile
  - exceedance
  - temporal-split
  - retrospective-research
  - agent-headroom
configs:
{CONFIGS_BLOCK}
---

# Cape Town Switching-substation Evening-peak Exceedance ({RELEASE_TAG})

**Status: {STATUS_LINE}**

The City of Cape Town publishes half-hourly apparent-power (MVA) readings for
its 33/66/132kV switching substations as one closed static table
(2022-01-01 .. 2024-12-31). **For each substation, at 06:00 SAST on day D,
will that substation's evening peak (maximum half-hourly MVA over
16:00-22:00 SAST) exceed its own trailing-90-evening 95th percentile** -
predicted from only what exists at the instant: the station identity, the
calendar, the same-day 00:00-06:00 readings and the mean of the trailing
<= 90 prior days' morning peaks. The evening label matrix is sealed outside
every solver-visible frame: no evening-derived value ships in any split file,
so the model predicts exceedance of a threshold it never sees.

- **Artifact version:** `{ARTIFACT_VERSION}`
- **Version tag:** `{RELEASE_TAG}` (use this revision for reproducibility)
- **Rows:** {ROWS_TOTAL} substation-days across three disjoint yearly splits
- **GitHub counterpart:** {GITHUB_REPOSITORY}

## Splits

| split | target days | rows | positives | positive rate | distinct exceedance days |
| --- | --- | ---: | ---: | ---: | ---: |
| `train` | 2022 | 13,735 | 1,539 | 11.20% | 227 |
| `eval` | 2023 | 14,965 | 1,256 | 8.39% | 246 |
| `holdout` | 2024 | 15,006 | 1,382 | 9.21% | 247 |

Temporal split on the target day. The first 30 days of each station's series
are burn-in (no 30 prior evenings for the p95) and are counted and excluded,
never scored. Positives cluster city-wide on regime days (weather /
load-shedding), so the distinct-day counts are the independent-observation
counts. Prevalence drifts across splits (11.20% -> 8.39% -> 9.21%).

## Measured evidence (identical eval rows, after gate acceptance)

Packaged by recorded operator decision as an **agent-headroom benchmark**:
the interesting question is not the stock model's score but the distance
between it and what the shipped features provably support.

| reference / model | eval AUC |
| --- | ---: |
| `morning_ratio` = morning_max / hist_morningpeak_mean_90 (headroom reference; reads only shipped at-instant columns) | **0.7340** |
| `month_only` - train-fitted month rate table | 0.6541 |
| `calendar_identity` - train-fitted station x month table (the skill's calendar control) | 0.6504 |
| `persistence_prev_evening` - previous evening's label, recomputed scorer-side (information-asymmetric BY DESIGN: the model is denied this) | 0.6502 |
| `identity_only` - train-fitted station rate table | 0.5134 |
| full model (stock runner XGBoost, verbatim) | 0.5107 |

The stock-runner model sits **at chance**, 0.2233 AUC below the headroom
reference, while a one-line rule over the shipped at-instant columns reaches
0.7340 (paired clustered bootstrap, 150 resamples: morning_ratio over
persistence CI95 [-0.1012, -0.0706]; over calendar_identity [-0.1019,
-0.0627]; persistence vs calendar_identity is inconclusive, interval
spanning zero). The morning_ratio comparison is NOT information-asymmetric -
both read only shipped columns - so 0.7340 is a fair same-information
target: the extractable signal exists in the shipped features and the stock
template does not find it. Diagnosis candidates are recorded with the
measurement (the stock train.py spends tree budget memorising a 365-level
train-only date categorical that cannot transfer). Majority-class accuracy
on this split is 0.9161. **No figure may be quoted without this
comparison.** No model above the reference has been measured; the holdout
has never been scored and was never copied into any runner workdir.

## What this task is, honestly

A **retrospective-research** construction: the publisher released the whole
2022-2024 window as one closed table (item created 2026-02-28, static since
2026-03-02), so no historical-operational-availability claim is made, label
timing is unverified at any historical instant outside the artifact's own
timestamp order, and the evaluation contract in `quality.json` requires
**isolated rows**. The publisher's own caveat carries through: readings are
indicative MVA values not corrected for temporary load shifts or
load-shedding fluctuations, so the label measures demand-as-dispatched, not
underlying demand. The gate's measured cross-row probe on this exact
artifact (morning_history_delta_attack, the only history-derived shipped
column) bounds label-recovery mismatches at 44.9% of eval rows - the
shipped morning-peak history does not reconstruct the evening label; a
sliding evening-quantile column would, at 0.995 exact agreement, which is
why no evening-derived column ships.

## Loading

{LOADING_NOTE}

```python
from datasets import load_dataset

ds = load_dataset("{REPO_ID}", revision="{RELEASE_TAG}"{TOKEN_ARG})
```

`revision="{RELEASE_TAG}"` pins the exact release revision for
reproducibility. `token=True` makes `huggingface_hub` read `HF_TOKEN` from
the environment; the argument disappears automatically once the repository
is public. The canonical download path is the GitHub counterpart's
`get_dataset.py`, which verifies every file against `SHA256SUMS` and
restores the runner layout.

## Licence

- Source data: **City of Cape Town Open Data Terms of Use**
  ({SOURCE_LICENSE}) - disclaimer-only (as-is, no warranty, no liability),
  no restriction on reuse, redistribution or derivatives for portal data,
  together with the Council-approved Open Data Policy 27781.
  {SOURCE_ATTRIBUTION}
- Our rights in the derived compilation: **{DATA_LICENSE}** (our
  contribution only - the eligibility frame, the derived label, the
  at-instant features, the sealed evening matrix design, the partition and
  the packaging).
- Our code and documentation: **{CODE_LICENSE}**.

This is a derived research dataset - **not** a City of Cape Town product,
and the City has not reviewed or endorsed it. The publisher's designation,
requested attribution and the portal Terms of Use disclaimer carry through
unchanged to every copy.
