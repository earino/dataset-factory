---
license: other
license_name: city-of-chicago-data-terms-of-use
license_link: https://www.chicago.gov/city/en/narr/foia/data_disclaimer.html
language:
  - en
pretty_name: Chicago Food Inspections - Violation Codes
size_categories:
  - 100K<n<1M
task_categories:
  - tabular-classification
tags:
  - tabular
  - food-safety
  - public-health
  - inspections
  - multi-label
  - temporal-split
configs:
{CONFIGS_BLOCK}
---

# Chicago Food Inspections - Violation Codes ({RELEASE_TAG})

**Status: {STATUS_LINE}**

Will this inspection of a Chicago food establishment cite violation code **NN**? One binary task
instance per violation code, {N_CONFIGS} of them, over the same {ROWS_TOTAL} pooled inspections and
the same time-ordered splits. Every instance carries 18 columns: the inspection's identifier, the
establishment's licence number, the inspection date, the facility attributes the City records
before any visit, the inspection's own type, the calendar position of the visit, and six
prior-history features computed from the licence's strictly-earlier inspections.

The prediction instant is **the moment the inspection opens**. The date is known when a canvass is
scheduled or a complaint triggers a visit; everything the inspector observes or records during or
after the visit is post-hoc and does not ship. The label source (`violations`, including the
per-violation comment text) and the inspection outcome (`results`) are excluded from every shipped
file, not merely unlisted.

- **Artifact version:** `{ARTIFACT_VERSION}`
- **Version tag:** `{RELEASE_TAG}` (use this revision for reproducibility)
- **Rows:** {ROWS_TOTAL} inspections - one pool, identical in every config
- **GitHub counterpart:** {GITHUB_REPOSITORY}

## The task instances

For config `code_38`, the target is "this inspection will cite violation code 38" - the label is
`1` when code 38 is parsed from the row's `violations` blob, `0` otherwise. Codes are parsed by
number, never by description text: 28 of the 61 codes observed in the 16.7-year history have more
than one wording. The {N_CONFIGS} shipped codes are the ones clearing a stated floor (at least 1%
of the pool and at least 30 positives on at least 20 distinct days in every window); codes 12, 18,
19, 24, 30, 31, 34 and 42 cleared the rate floor but not the per-window minimums and do not ship.

Rows and splits are identical in every config, by design - the configs are alternative binary
targets over one panel of inspections, not different populations:

| split | rows | window |
| --- | --- | --- |
| `train` | 156,841 | 2010-01-01 to 2021-01-01 |
| `eval` | 35,358 | 2021-01-01 to 2024-01-01 |
| `holdout` | 34,218 | 2024-01-01 to 2026-10-01 |

Split boundaries are calendar dates, so eval and holdout are later in time than training; no
`inspection_id` appears in more than one split. The establishment (`license_`) does span splits by
design - prior history is the point of the task - and each config's own persistence feature
(`prev_code_present`) is the floor any model must beat. Prevalence varies by code and by window
(eval positive rates from 0.0015 to 0.56 across the suite), so compare across configs by AUC,
never by accuracy.

Each config also ships `meta.json` (feature list, label definition, provenance, split windows) and
`quality.json` (per-split prevalence, event clustering, measurements). The extract root carries
`labels.csv`: one row per pooled inspection, one column per shipped code, so the joint multi-label
problem can be reconstructed from the same bytes. It is documented rather than gated.

## Baseline

One baseline was measured on **every one of the {N_CONFIGS} configs** in one uniform run, through
the runner's own training and validation contract, on the exact bytes in this release (fetched and
digest-verified, not rebuilt):

- eval AUC across the suite: **min 0.5187 (`code_32`), median 0.7208, max 0.8292 (`code_58`)**;
- `code_38` (mid-prevalence reference): **0.6326**, identical from the training path and an
  independent validation re-run, reproduced again from the published bytes by a fresh-environment
  consumer run;
- persistence reference (`prev_code_present` alone) is recorded per config in `measurements.json`,
  so headroom over each code's own persistence is checkable: the baseline clears it on 38 of 40
  configs and does not on `code_14` and `code_32`.

Scope of these numbers: baselines only, through the runner's contract. No agent or harness
comparison was run, and none is implied.

## Loading

Version-pinned. `revision` is the tag, not a branch, so the bytes cannot change under you.

```python
from datasets import load_dataset

ds = load_dataset("{REPO_ID}", "code_38", revision="{RELEASE_TAG}"{TOKEN_ARG})
# every config is loaded the same way; the config has to be named
```

{LOADING_NOTE}

The files are also plain CSVs, so they can be used without `datasets`:

```bash
hf download {REPO_ID} --repo-type dataset --revision {RELEASE_TAG} \
    --include "data/*.csv" --local-dir ./chicago-food
```

The GitHub counterpart carries the identical files and digests:
{GITHUB_REPOSITORY}, with `MANIFEST.json`, `SHA256SUMS` and `get_dataset.py`.

## Provenance

- Source: City of Chicago - Department of Public Health, Food Inspections (dataset `4ijn-s7e5`),
  https://data.cityofchicago.org/d/4ijn-s7e5
- Extract frozen at **2026-10-05**: 316,205 source rows fetched anonymously over 46 pages ordered
  by `inspection_id`, reduced to the 226,417-inspection modelling pool; the source-row and pool
  digests are recorded in `MANIFEST.json`.
- The portal republishes continuously (daily), so a rebuild from the live endpoint will not
  reproduce these bytes. The version is the recorded digests, and the frozen build's counts live
  in `measurements.json` so drift is visible rather than silent.

## Qualification

- Gate: **PASSED - 32 checks x {N_CONFIGS} configs, 0 failed, 0 warnings** (gate 1.3.0), run on the
  worker over the full artifact on the rows, not a sample.
- A fresh-environment consumer job re-verified the published bytes end to end: package digests,
  `sha256sum -c` over all 201 files, the qualification gate's `--accept` on every config, and the
  `code_38` baseline reproduced at 0.6326 through the unmodified contract.

Every number above is measured, with the command that produced it recorded in `measurements.json`
and `MANIFEST.json`; figures that are estimates are labelled as such.

## Licence and attribution

| | |
| --- | --- |
| Source data (City of Chicago) | **{SOURCE_LICENSE}** - no standard open licence; the City's Data Terms of Use are preserved unchanged |
| Our rights in this derived compilation | **{DATA_LICENSE}** |
| Code and documentation in the GitHub counterpart | **{CODE_LICENSE}** |

**Scope, stated plainly:** there is no CC0 dedication here and none is claimed. The City's Data
Terms of Use regulate distribution and secondary or derivative use of the source data; they do not
grant a right to sublicense the source rows, so this compilation is distributed under those same
Terms. Our own code and documentation are MIT. Nothing in this release may be presented as CC0,
CC-BY, public domain or any other standard open licence - the source does not support it.

**Attribution.** {SOURCE_ATTRIBUTION}

**Disclaimer (the City's own wording, preserved).** This site provides applications using data that
has been modified for use from its original source, www.cityofchicago.org, the official website of
the City of Chicago. The City of Chicago makes no claims as to the content, accuracy, timeliness,
or completeness of any of the data provided at this site. The data provided at this site is subject
to change at any time. It is understood that the data provided at this site is being used at one's
own risk.

This dataset is **derived** from the City of Chicago's open data and is labelled as derived; it is
**not an official City of Chicago product**, and it carries no endorsement by the City.

## Limitations

- The label is the set of violation codes an inspector recorded, which is an enforcement outcome,
  not an underlying hazard measurement; establishments inspected more often generate more
  citations.
- Prior-history features use only the same licence's strictly-earlier inspections, and a licence
  spans split windows by design - the temporal split, not entity disjointness, is what prevents
  leakage here.
- Codes under the stated prevalence floor do not ship, so this is not a census of the 61 observed
  violation codes.
- `labels.csv` is a documented convenience, not a gated runner input.
- No agent or harness comparison was run on this artifact, and none is implied.
