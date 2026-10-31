---
license: other
license_name: ogl-uk-3.0-source-plus-cc0-compilation
language:
  - en
pretty_name: UK Planning Appeal Outcome
size_categories:
  - 100K<n<1M
task_categories:
  - tabular-classification
tags:
  - tabular
  - planning
  - appeals
  - administrative-outcome
  - temporal-split
  - validation-time-features
configs:
{CONFIGS_BLOCK}
---

# UK Planning Appeal Outcome ({RELEASE_TAG})

**Status: {STATUS_LINE}**

The UK Planning Inspectorate publishes its Casework Database as open data
(GOV.UK, Open Government Licence v3.0; this build pins the 2026-10-22
edition). **For a planning-permission-family appeal validated by the
Planning Inspectorate, will the final decision be Allowed rather than
Dismissed** - predicted from only what is known at validation: casework
type, LPA identity, received date, procedure, development type, appeal
reason fields, site descriptors and designation flags, and LPA-level
prior-outcome history computed strictly from decisions earlier than the
validation instant?

- **Artifact version:** `{ARTIFACT_VERSION}`
- **Version tag:** `{RELEASE_TAG}` (use this revision for reproducibility)
- **Rows:** {ROWS_TOTAL} decided appeals across three disjoint
  validation-instant splits
- **GitHub counterpart:** {GITHUB_REPOSITORY}

## Splits

| split | rows | validation instants | positives | positive rate |
| --- | ---: | --- | ---: | ---: |
| `train` | 54,834 | before 2020-01-01 | 17,048 | 31.09% |
| `eval` | 28,104 | 2020-2021 | 8,469 | 30.13% |
| `holdout` | 56,326 | 2022-01-01 onwards | 17,705 | 31.43% |

The population is decided s78_core planning-permission-family appeals with
a binary decision (139,264 scored rows; 2,757 non-binary decisions, 3,110
cross-file duplicates and 2 decided-before-validation rows excluded and
counted). The publisher's database contains decided cases only - an
outcome-conditioned population recorded as a limitation. The label source
(the Decision field and its date) is absent from every shipped file.

## Measured evidence (identical eval rows, after gate acceptance)

| reference / model | eval AUC |
| --- | ---: |
| full model (stock runner XGBoost, verbatim) | **0.6108** |
| procedure-type rate (dominant simple reference) | 0.5551 |
| shipped rate feature (`lpa_allow_rate_prior`) | 0.5422 |
| LPA history rate (named headroom reference) | 0.5414 |
| persistence (previous same-LPA outcome) | 0.5045 |

Paired row-level AND LPA-clustered intervals excluding zero on all three
model-vs-reference comparisons (+0.0558 [0.0467, 0.0626] vs procedure-type;
+0.0694 [0.0622, 0.0766] vs LPA rate; +0.0686 [0.0619, 0.0756] vs the
shipped rate feature, with matching LPA-clustered intervals), at flat
prevalence across the two eval validation years: demonstrated headroom
over these references under this protocol. Scope recorded beside it: one
model configuration, no re-tuning, two validation years of eval coverage,
and no operational-validity claim. The calendar-identity control collapsed
onto the LPA rate exactly (eval years have no train-era valid-year support)
and is recorded as degenerate, not as independent confirmation.
Persistence is measured (92%+ of eval rows' LPAs have train-era history).
Majority-class accuracy on this split is 0.6987.

## What this task is, honestly

A **retrospective, current-snapshot** construction: the publisher serves a
rolling database (republished monthly-to-quarterly) and no historical
vintages, so training-label timing and historical availability are
unverified and no point-in-time reconstruction or live screening claim is
made. The evaluation contract in `quality.json` requires **isolated rows**
for honest evaluation, because the LPA-history features embed other rows'
labels (`lpa_last_outcome` is the previous same-LPA case's label); the
shipped illustrative runner does not enforce that requirement, so
unrestricted-access scores overstate honest performance. The split key is
the validation instant (the outcome date cannot ship), so a split's labels
can postdate the next split's earliest instants.

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
  only - eligibility frame, counted exclusions, deduplication, derived
  label, features, partition, packaging).
- Our code and documentation: **{CODE_LICENSE}**.

This is a derived research dataset - **not** a Planning Inspectorate
product, and the Planning Inspectorate has not reviewed or endorsed it. The
publisher's own data caveats carry through unchanged.
