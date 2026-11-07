---
license: other
license_name: ogl-alberta-2.2-source-plus-cc0-compilation
language:
  - en
pretty_name: Alberta Wildfire Initial-Attack Escape Prediction (100 ha)
size_categories:
  - 10K<n<100K
task_categories:
  - tabular-classification
tags:
  - tabular
  - wildfire
  - alberta
  - initial-attack
  - escape
  - temporal-split
  - retrospective-research
configs:
{CONFIGS_BLOCK}
---

# Alberta Wildfire Initial-Attack Escape Prediction ({RELEASE_TAG})

**Status: {STATUS_LINE}**

Alberta Wildfire's own historical record documents, for every wildfire in
the Forest Protection Area 2006-2025, the crew-observed **initial
assessment** - the instant at which the agency itself makes its
initial-attack resourcing decision. **At that recorded assessment instant,
will the wildfire escape initial attack** - end at 100 ha or more final
area burned (`escape = 1`) - predicted from only what the assessing crew
observed: size at assessment, rate of spread, fire behaviour type, position
on slope, the in-situ weather over the fire, the FBP fuel type, plus
pre-instant timing fields (reported, discovered, estimated ignition), the
detection channel and calendar/geography. Base rate at eval: 104 / 5,707 =
1.82%.

- **Artifact version:** `{ARTIFACT_VERSION}`
- **Version tag:** `{RELEASE_TAG}` (use this revision for reproducibility)
- **Rows:** {ROWS_TOTAL} assessed wildfires across three disjoint temporal splits
- **GitHub counterpart:** {GITHUB_REPOSITORY}

## Splits

| split | rows | assessment years | positives | positive rate | distinct positive days |
| --- | ---: | --- | ---: | ---: | ---: |
| `train` | 15,864 | 2006-2015 | 297 | 1.87% | 156 |
| `eval` | 5,707 | 2016-2020 | 104 | 1.82% | 79 |
| `holdout` | 6,257 | 2021-2025 | 257 | 4.11% | 128 |

The label derives from the record's own post-instant fields (final area
burned, first under control); every label-source and post-instant family
(cause, dispatch, suppression milestones, discovered size) is excluded from
every shipped file. Eligibility is assessment-based, not outcome-conditioned:
every discovered wildfire is assessed, so all 27,828 assessed FPA wildfires
are rows, winter rows kept. Splits follow the assessment instant's calendar
year in Alberta local operational time. The holdout is **sealed and has never
been scored**.

## Measured evidence (identical 5,707 eval rows, after gate acceptance)

| reference / model | eval AUC |
| --- | ---: |
| full model (stock runner baseline, benchmark's own `train.py` + `validate.sh`) | **0.9554** |
| persistence analogue - the fire's own observed size at assessment (`assessment_hectares`) | 0.9096 |
| calendar/identity prior - train rate per month x forest area | 0.7130 (Brier 0.0179) |
| construction-time full-feature L2 logistic (simple reference, supplementary) | 0.9206 (Brier 0.0158) |
| majority-class accuracy (constant fitted on train, vs this split's labels) | 0.9818 |

The pre-registered deciding rule (written before any score existed) is
satisfied on eval 2016-2020: the model beats every triad member with a
day-clustered paired bootstrap 95% CI excluding zero - model minus
persistence **+0.0459, CI95 [0.0154, 0.0871]** (500 resamples, cluster =
assessment day); model minus calendar/identity +0.2428, CI95 [0.1911,
0.2998]; and the model's own cluster-bootstrap AUC CI [0.9382, 0.9686] lies
entirely above 0.5. **No figure from this dataset may be quoted without the
comparison above beside it.**

## What this task is, honestly

- **The persistence bar is high.** The fire's own observed size at assessment
  already ranks escape at AUC 0.9096 on its own; the bar for any model is
  that rule, not 0.5. The stock runner clears it with a CI excluding zero
  (+0.046). The construction-time *simple* logistic reference's edge over
  persistence is **INCONCLUSIVE** (+0.0111, CI [-0.0292, 0.0514], interval
  contains zero): a simple linear model over the shipped features does not
  demonstrably beat the one-feature rule - the demonstrated headroom is the
  richer model's, and beating the bar is the benchmark's question.
- **Retrospective research, not certified operational forecasting.** The
  publisher ships one living current compilation (no per-fire historical
  vintages); the dictionary documents in-place revision of area burned
  (spring aerial-photography interpretation), cause and location, and the
  2019 season total differs from the current archive by -10.4% (measured
  against the publisher's own season PDF). `training_label_timing` is
  therefore unverified, the evaluation contract is `use:
  retrospective_research`, `access: isolated_rows`, vintage
  `current_snapshot`. Label-flip exposure from revision is bounded and
  measured: 89 fires lie within +-20% of the 100 ha threshold. Timestamps
  carry no timezone marker and are read as Alberta local operational time
  (confirmed against the official 2016 Horse River review's documented
  detection time). Eval is development/validation; the holdout is the final
  test and stays outside evaluated agents' workspaces.
- **Prevalence shift is a property, not a repair.** The positive rate rises
  into the holdout (1.87% train, 1.82% eval, 4.11% holdout - the 2021-2025
  window contains the 2023 record season), so the holdout is an
  out-of-distribution test as much as a temporal one. Positives arrive on
  the same extreme fire-weather days, so distinct positive assessment days
  (156 / 79 / 128) are the conservative independent-observation count and
  every deciding interval is day-clustered.

## Known-event fixtures

The label is bound to the publisher's own record: the 2016 Horse River
Wildfire (MWF009) is asserted in-build at its documented final size of
485,123.6 ha (escape 1), corroborated by the Government of Alberta's
official review (detection 16:03h MDT 2016-05-01, under control
2016-07-04); nine further named fires are asserted at their
publisher-documented final sizes, including an already-controlled negative
(2023 LWF002, 0.01 ha). A unit or threshold error would move these fixtures
to their extremes and fail the build. The current CSV's season hectares
match the publisher's season PDFs to <= 1.0% for 2020-2024 (2019 differs by
-10.4%, the documented revision).

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

- Source data: **Open Government Licence - Alberta v2.2** for the
  Government of Alberta's Historical wildfire data 2006-2025
  ({SOURCE_LICENSE}). {SOURCE_ATTRIBUTION}
- Our rights in the derived compilation: **{DATA_LICENSE}** (our
  contribution only - the all-cause assessment-instant population frame,
  the derived binary escape label, the at-instant feature derivations, the
  excluded-column policy, the temporal partition, the packaging).
- Our code and documentation: **{CODE_LICENSE}**. The benchmark's own
  runner files (`baseline/train.py`, `baseline/validate.py`,
  `baseline/validate.sh`) ship verbatim and unmodified under their existing
  terms, with their provenance recorded.

This is a derived research dataset - **not** a Government of Alberta or
Alberta Wildfire product, and neither has reviewed or endorsed it. The
publisher's own designations, field definitions and suggested citation are
preserved verbatim (the full data-dictionary transcript ships with the
package), and changes from the source are indicated in the package.
