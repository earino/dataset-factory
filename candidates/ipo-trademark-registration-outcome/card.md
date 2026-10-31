---
license: other
license_name: ogl-uk-3.0-source-plus-cc0-compilation
language:
  - en
pretty_name: UK Trade Mark Application Registration Outcome
size_categories:
  - 100K<n<1M
task_categories:
  - tabular-classification
tags:
  - tabular
  - intellectual-property
  - trademarks
  - administrative-outcome
  - cohort-split
  - filing-time-features
configs:
{CONFIGS_BLOCK}
---

# UK Trade Mark Application Registration Outcome ({RELEASE_TAG})

**Status: {STATUS_LINE}**

The UK Intellectual Property Office publishes its domestic trade mark
register as open data (the frozen `opendatadomestic.zip` snapshot of
2018-02-13, Open Government Licence v3.0). **For a trade mark application
filed in 2010-2016, will it reach registration** (a recorded Registered
date) as resolved in that snapshot - predicted from what is fixed at
filing: the mark text, its Nice class coverage (45 binary columns),
category, mark type, series membership and size, the owner's
country / region / postcode area, and the filing date?

- **Artifact version:** `{ARTIFACT_VERSION}`
- **Version tag:** `{RELEASE_TAG}` (use this revision for reproducibility)
- **Rows:** {ROWS_TOTAL} applications across three disjoint filing-year cohort splits
- **GitHub counterpart:** {GITHUB_REPOSITORY}

## Splits

| split | rows | filing years | positives | positive rate |
| --- | ---: | --- | ---: | ---: |
| `train` | 106,990 | 2010-2012 | 92,668 | 86.61% |
| `eval` | 97,274 | 2013-2014 | 81,699 | 83.99% |
| `holdout` | 115,172 | 2015-2016 | 99,385 | 86.29% |

Applications whose outcome was still unresolved at the snapshot (in
examination, opposition or appeal) are **censored** - excluded and counted
per cohort (21 / 172 / 809), never labelled negative. The label source
columns (Status, Published, Registered, Expired, Renewal Due Date) are
absent from every shipped file.

## Measured evidence (identical eval rows, after gate acceptance)

| reference / model | eval AUC |
| --- | ---: |
| full model (stock runner XGBoost, verbatim) | **0.6224** |
| mark-type rate (dominant simple reference) | 0.5650 |
| nice-class rate | 0.5421 |
| series-flag rate | 0.5213 |
| owner-country rate | 0.5191 |
| category rate | 0.5031 |
| calendar-month rate | 0.4972 |

Paired row-level intervals excluding zero on all three model-vs-reference
comparisons (+0.0574 [+0.0533, +0.0605] vs mark-type; +0.0803 [+0.0748,
+0.0862] vs nice-class; +0.1252 [+0.1174, +0.1315] vs calendar), holding in
both eval filing years at flat prevalence: demonstrated headroom over these
references under this protocol. Scope recorded beside it: row-level
intervals only, one model configuration, two filing years of eval coverage,
and no operational-validity claim. Persistence is not applicable (every
scored row is a new application). Majority-class accuracy on this split is
0.8399 - accuracy is the wrong lens on an 84%-positive split.

## What this task is, honestly

A **retrospective, single-snapshot** construction: the publisher serves one
frozen vintage and no historical vintages, so training-label timing and
historical availability are unverified and no point-in-time reconstruction
or live screening claim is made. The evaluation contract in `quality.json`
declares retrospective research under an isolated-rows design intent. Owner
and class columns are snapshot-vintage (ownership can be assigned after
filing, classes can be narrowed) - a declared uniform-vintage limitation.

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

- Source data: **Open Government Licence v3.0** ({SOURCE_LICENSE}). Contains
  public sector information licensed under the Open Government Licence v3.0.
  {SOURCE_ATTRIBUTION}
- Our rights in the derived compilation: **{DATA_LICENSE}** (our contribution
  only - eligibility frame, derived label, features, partition, packaging).
- Our code and documentation: **{CODE_LICENSE}**.

This is a derived research dataset - **not** an Intellectual Property Office
product, and the IPO has not reviewed or endorsed it.
