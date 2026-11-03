---
license: other
license_name: fts-reuse-permission-plus-cc-by-igo-source
language:
  - en
pretty_name: OCHA FTS Appeal Funding Trajectory (will the appeal reach half its requirements?)
size_categories:
  - n<1K
task_categories:
  - tabular-classification
tags:
  - tabular
  - humanitarian
  - fts
  - ocha
  - appeals
  - funding
  - temporal-split
configs:
{CONFIGS_BLOCK}
---

# OCHA FTS Appeal Funding Trajectory ({RELEASE_TAG})

**Status: {STATUS_LINE}**

For a primary humanitarian appeal plan-year (OCHA Financial Tracking Service; HPC
plan records with their original launch requirements), **at the appeal's launch,
will appeal-linked funding reach at least half of the original requirements?**
One row per appeal-plan ID × plan year (`plan_year_id`, unique across the panel;
(country, plan year) is not the grain — a country can carry several distinct
appeals in one plan year); the label is `reached_half` (2 x appeal-linked
funding >= original requirements), resolved from the FTS/HPC record; the funding
totals themselves are never shipped. Every shipped feature is fixed at launch:
plan year, plan type, GHO membership, original requirements, and the number of
years since the country's prior appeal - a calendar fact, never another row's
outcome.

- **Artifact version:** `{ARTIFACT_VERSION}`
- **Version tag:** `{RELEASE_TAG}` (use this revision for reproducibility)
- **Rows:** {ROWS_TOTAL} plan-year appeal rows across three disjoint temporal splits
- **GitHub counterpart:** {GITHUB_REPOSITORY}

## Splits

| split | rows | plan years | positives | positive rate |
| --- | ---: | --- | ---: | ---: |
| `train` | 437 | 2000-2016 | 279 | 63.8% |
| `eval` | 139 | 2017-2020 | 81 | 58.3% |
| `holdout` | 182 | 2021-2025 | 96 | 52.7% |

Splits are temporal on the plan year; the labeled holdout ships by design and is
never scored in development.

## What this is (and what was corrected before release)

The v2026.10-era construction carried country-history features (prior appeal
counts, covered rates, last-prior outcome). The independent queue audit
(2026-11-01) demonstrated those columns allowed label-blind recovery of 120/139
eval and 128/182 holdout labels exactly, and the artifact was rejected under the
operator's P0 standard. This {RELEASE_TAG} artifact is the corrected rebuild: all
outcome-derived history columns are removed; the only history-derived column
reads prior appeal YEARS, never labels, so no shipped column is a function of
another row's outcome. The corrected bytes were re-qualified through gate 1.5.0
(failed_checks empty) and must again be attacked by an independent audit before
publication.

{LOADING_NOTE}

## Measured evidence (identical eval rows, after gate acceptance)

| Reference / model | Eval AUC (139 rows, 81 positives) |
| --- | --- |
| Full model - the illustrative stock XGBoost baseline, verbatim runner | **0.6452** |
| Persistence (the last prior covered state) | **0.7171** |
| Prior mean | 0.7143 |
| Original-ask share reference | 0.7126 |
| Country rate | 0.6730 |
| Plan type | 0.6692 |
| Majority-class accuracy on this split | 0.5827 |

The illustrative baseline trails persistence on these rows - recorded as the
honest finding. An independent audit's exploratory logistic fit reached 0.7880 on
the same rows, which suggests real signal beyond the references exists, but no
headroom is claimed under the shipped protocol. The runner was deliberately denied
the last-prior-outcome feature under the P0 standard; the persistence reference
reads it scorer-side, an information asymmetry recorded beside every figure.

The shipped illustrative runner does NOT enforce isolated rows; it passes the
whole eval feature table to the predictor in one call. The isolated-rows
declaration is the conservative posture for honest evaluation, not an
enforcement claim, and any real evaluation must enforce the restriction itself.

## Suitability and evaluation

Retained for retrospective model-development research under an isolated-rows
posture declared conservatively, not enforced by the shipped runner. Training-label
timing is UNVERIFIED (current-vintage FTS record, no historical publication ledger);
historical feature availability is partial. The labeled holdout is downloadable by
design and stays outside every evaluated agent's workspace; the labeled eval split
is development/validation. No operational, real-time or point-in-time forecasting
claim is made. The version-bound suitability record with its full evidence lives in
the repository and its public notice ships with the website page.

## Source and provenance

- OCHA Financial Tracking Service (fts.unocha.org) HPC API plan and flow records
  (public anonymous endpoints, harvested 2026-10-30, per-plan compact provenance
  retained by the build), plus the HDX "Global - Requirements and Funding Data"
  bulk CSV (pinned bytes, 2026-10-29).
- Funding totals are the label numerator and never ship; original requirements are
  the launch-vintage values from the plan records.
- The FTS API exposes no historical vintages, so the panel is current-vintage
  retrospective; no as-of reconstruction is claimed and training-label timing is
  declared unverified (a train plan-year's funding can close during the first
  eval appeals' launch window).

## Licence and attribution

FTS use-and-republish permission applies (attribution, access date, source URL),
and the HDX bulk CSV input carries CC BY-IGO, preserved on
every copy of the derived data: {SOURCE_ATTRIBUTION}. Our contribution to the
derived compilation is dedicated {DATA_LICENSE}; the code is {CODE_LICENSE}.
Derived research dataset - not an OCHA or FTS product; OCHA has not reviewed,
authorised or endorsed it.
