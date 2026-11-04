---
license: other
license_name: ogl-uk-3.0-source-plus-cc0-compilation
language:
  - en
pretty_name: CQC Care-home Deregistration
size_categories:
  - 100K<n<1M
task_categories:
  - tabular-classification
tags:
  - tabular
  - cqc
  - care-homes
  - deregistration
  - register-exit
  - temporal-split
  - administrative-record
configs:
{CONFIGS_BLOCK}
---

# CQC Care-home Deregistration ({RELEASE_TAG})

**Status: {STATUS_LINE}**

The Care Quality Commission (England's health and social care regulator)
publishes its register bulk files as open data: monthly "HSCA Active
Locations" vintages (archived in CQC's public Google Drive back to 2011) and
the cumulative "Deactivated Locations" register. **At the production instant
of a monthly active-locations vintage T, for every care home active at T, will
the location's CQC registration end within the following 12 months** -
predicted from only what the T vintage carries: latest overall rating, care
home bed count, registration/start dates, provider sector, local authority
and the per-instant pseudonymised location key.

- **Artifact version:** `{ARTIFACT_VERSION}`
- **Version tag:** `{RELEASE_TAG}` (use this revision for reproducibility)
- **Rows:** {ROWS_TOTAL} care-home vintage rows across three disjoint
  vintage-instant splits
- **GitHub counterpart:** {GITHUB_REPOSITORY}

## Splits

| split | rows | vintage instants | positives | positive rate |
| --- | ---: | --- | ---: | ---: |
| `train` | 78,138 | January 2018-2022 (2016/2017 vintages loudly dropped: unresolved required columns) | 4,418 | 5.65% |
| `eval` | 14,765 | January 2024 | 757 | 5.13% |
| `holdout` | 14,749 | January 2025 | 761 | 5.16% |

The label is `deregistered_12m = 1` when the location has status
Inactive-Dereg or Removed with a Location HSCA End Date in (T, T+365d],
joined from the Deactivated Locations register. The 2023 vintage is excluded
by design: its 12-month outcome window would still be open at the eval
prediction instant. The label source fields never ship in any split file.

## Measured evidence (identical eval rows, after gate acceptance)

| reference / model | eval AUC |
| --- | ---: |
| `rating_x_beds_rate` - train-fitted rate table over latest rating x beds (headroom reference) | **0.5871** |
| full model (stock runner XGBoost, verbatim) | 0.5659 |
| `last_rating_rate` - train-fitted rate table over latest rating (best one-line prior) | 0.5597 |
| `beds_bucket_rate` | 0.5298 |
| `hsca_start_year_rate` | 0.5226 |
| `local_authority_rate` | 0.5207 |
| `provider_sector_rate` | 0.5011 |

The stock-runner model sits **below** the headroom reference (paired
bootstrap 150 resamples for the reference-vs-next gap excludes zero:
+0.0273 [0.0123, 0.0407]). That is a **recorded defect of the stock runner
under this protocol, not a no-headroom verdict on the task**: the model beats
every one-line prior, the reference reads only shipped at-T columns (no
information asymmetry), and a verified diagnosis candidate is recorded
(the stock runner treats `instant` as a train-only categorical, so the eval
instant 2024-01 is unseen and every eval row gets NaN there). No model above
the reference has been measured. Majority-class accuracy on this split is
0.9487. **No persistence reference exists by design**: identity ships as a
per-instant pseudonym (the missing-successor P0 design), so prior-instant
labels are structurally unlinkable - for a scorer too;
`hsca_start_year_rate` is the nearest shippable history prior.

## What this task is, honestly

A **retrospective, mixed-vintage** construction: the historical active
vintages come from CQC's public Google Drive archive but no full-row
availability ledger exists for them, so training-label timing and historical
availability are unverified, and the evaluation contract in `quality.json`
is retrospective research requiring **isolated rows** (`use=retrospective_research`,
`access=isolated_rows`); eval is development/validation, holdout is final, and
no historical-forecasting or operational-validity claim is made. Cross-row
exposure is **measured, not enforced**: gate probes measured pseudonym-
successor coverage 0/0/0 and quasi-identifier (LA x beds x start year x
rating x sector) eval/holdout coverage 0 (train 11,786, where labels are
public anyway) - honest evaluation should still keep rows isolated.

The **register-event framing limit**: the label conflates registration
cessation with re-registration/transfer (CQC's own in-file note; BMJ Public
Health 2024 implies roughly 40-55% of exits are re-registrations/transfers).
Successor linkage was not built, so the target is a register event, not a
service closure.

The holdout has never been scored and was never copied into any runner
workdir; a holdout evaluation requires a frozen design.

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

This is a derived research dataset - **not** a CQC product, and CQC has not
reviewed or endorsed it. CQC's own in-sheet disclaimer carries through: CQC
is not responsible for subsequent analysis of this raw data and must not be
quoted as the source of the analysis or interpretation.
