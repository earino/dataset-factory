---
license: other
license_name: godl-india-1.0-and-cc-by-4.0-source-plus-cc0-compilation
language:
  - en
pretty_name: India CPCB Station-day Next-day PM2.5 Exceedance
size_categories:
  - 100K<n<1M
task_categories:
  - tabular-classification
tags:
  - tabular
  - air-quality
  - pm25
  - india
  - cpcb
  - exceedance
  - next-day
  - temporal-split
  - retrospective-research
configs:
{CONFIGS_BLOCK}
---

# India CPCB Station-day Next-day PM2.5 Exceedance ({RELEASE_TAG})

**Status: {STATUS_LINE}**

The Central Pollution Control Board's CAAQM network measures hourly PM2.5
across India, republished by the XKDR Forum's India Air Quality Database
(data.xkdr.org). **At 23:59 IST on day D, for every complete
(n_hours >= 18) PM2.5 station-day, will the station's next calendar day's
24-hour mean PM2.5 exceed 90 ug/m3** - the Poor-band lower breakpoint of
CPCB's own National AQI (`exceeds = 1`) - predicted from only what is
knowable at that instant: the station's own day-D daily statistics, trailing
history (lags, 7/30/90-day means, days since a >90 day, 30-day exceedance
count), the calendar of day D, and the station's identity. Base rate at
eval: 19,819 / 126,570 = 15.66%.

- **Artifact version:** `{ARTIFACT_VERSION}`
- **Version tag:** `{RELEASE_TAG}` (use this revision for reproducibility)
- **Rows:** {ROWS_TOTAL} station-days across three disjoint temporal splits
- **GitHub counterpart:** {GITHUB_REPOSITORY}

## Splits

| split | rows | window (prediction instant = day D) | positives | positive rate | stations | distinct positive days |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| `train` | 288,754 | 2019-2022 | 61,075 | 21.15% | 389 | 1,248 |
| `eval` | 126,570 | 2023 | 19,819 | 15.66% | 509 | 351 |
| `holdout` | 145,124 | 2024 | 18,222 | 12.56% | 529 | 352 |

The label is the D+1 calendar-day 24-hour mean PM2.5 > 90 ug/m3; the label
source columns (`next_day_pm25_mean`, `next_day_n_hours`) are excluded from
every shipped file. Row selection reads day-D completeness plus a D+1
*observability* rule that never reads the label value; unlabelable, thin and
outside-window rows are excluded and counted per split. The holdout is
**sealed and has never been scored**.

## Measured evidence (identical 126,570 eval rows, after gate acceptance)

| reference / model | eval AUC |
| --- | ---: |
| full model (stock runner baseline, benchmark's own `train.py` + `validate.sh`) | **0.9734** |
| `station_persistence` - the station's day-D `pm25_mean` as the score | 0.9689 |
| `state_season_climatology` - train rate per state x season of D+1 | 0.8617 |
| `station_train_rate` - identity prior (supplementary) | 0.7616 |
| majority-class accuracy (constant fitted on train, vs this split's labels) | 0.8434 |
| `global_rate` - constant train rate | degenerate (Brier 0.1351) |

The pre-registered deciding rule (written before any score existed) is
satisfied on eval 2023: the model beats every triad member with a
station-clustered paired bootstrap 95% CI excluding zero - model minus
persistence **+0.004491, CI95 [0.0038, 0.0052]** (1,000 resamples, 509
station clusters); model minus climatology +0.1118, CI95 [0.1002, 0.1252];
and the model's own cluster-bootstrap AUC CI [0.9713, 0.9753] lies entirely
above 0.5. **No figure from this dataset may be quoted without the
comparison above beside it.**

## What this task is, honestly

The defining limitation travels with the number: **the label is largely
persistence-carried**. The station's own day-D mean already ranks D+1
exceedance at AUC 0.9689, so the model's edge over persistence is real but
small (+0.0045 AUC, CI [+0.0038, +0.0052]), while the gap to the
calendar/identity climatology is large. A scorer that ships `pm25_mean`
inherits most of the structure; the task's residual challenge is the
short-term departure from persistence, and the honest reading of any
headline AUC is "persistence plus a small edge".

- **Retrospective research, not certified historical forecasting.** The
  archive is ONE pinned XKDR export (exported_at 2026-09-30, verified by the
  build, which refuses any other export): no historical vintages or
  first-publication ledger exist, so `training_label_timing` is unverified
  and the evaluation contract is `use: retrospective_research`,
  `access: isolated_rows`, vintage `current_snapshot`. Eval is
  development/validation; the holdout is the final test and stays outside
  evaluated agents' workspaces. CPCB intraday publication latency is
  unmeasured; treating day-D trailing hours as complete at 23:59 IST is a
  declared assumption.
- **Cross-row exposure is demonstrated, not denied.** A same-station
  offset-1 blind join reproduces the label BY CONSTRUCTION (the donor's
  `pm25_mean` is the label operand) - a declared identity recorded as
  `recovery_demonstrated`, mitigated by the enforced isolated-rows protocol
  and the exclusion of label-source columns from every shipped file. Honest
  evaluation keeps rows isolated.
- **Prevalence drift and clustering are properties, not repairs.** Positive
  rate declines across splits (21.15% -> 15.66% -> 12.56%), an
  out-of-distribution as well as temporal test; positives are
  winter-clustered (eval 2023: DJF 33.0% vs JJAS 1.0%), so distinct
  positive days are the conservative independent-observation count and
  every deciding interval is station-clustered.

## Known-event and negative-control fixtures

The label is bound to the publisher's own instrument: CPCB's Daily AQI
Bulletin of 2024-11-18 (Delhi Severe, AQI 494, prominent pollutant PM2.5,
36/39 stations) - and the panel confirms it, 36/36 complete Delhi
station-days that day exceed. The monsoon trough day 2023-08-15 is the
negative control: 389 complete all-India station-days, 1 exceed. A unit or
reference-frame error would move either fixture to its extreme and fail the
build.

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

- Source data: **Government Open Data License - India (GODL-India v1.0)** for
  the CPCB CAAQM measurements and **CC BY 4.0** for the XKDR compilation
  ({SOURCE_LICENSE}). {SOURCE_ATTRIBUTION}
- Our rights in the derived compilation: **{DATA_LICENSE}** (our
  contribution only - the station-day eligibility frame, the derived binary
  label, the at-instant trailing-history features, the excluded-and-counted
  accounting, the temporal partition, the packaging).
- Our code and documentation: **{CODE_LICENSE}**.

This is a derived research dataset - **not** a CPCB, Government of India, or
XKDR Forum product, and none of them has reviewed or endorsed it. The
publishers' own designations, credits and data-quality caveats carry through
(values "as reported", "no gap filling", "preliminary and not fully
validated" - XKDR README), and changes from the source are indicated in the
package.
