---
license: other
license_name: city-of-chicago-data-terms-of-use
license_link: https://www.chicago.gov/city/en/narr/foia/data_disclaimer.html
language:
  - en
pretty_name: Chicago DOAH Ordinance Violation Adjudication (2026.09)
size_categories:
  - 10K<n<100K
task_categories:
  - tabular-classification
tags:
  - tabular
  - public-safety
  - municipal-adjudication
  - temporal-split
configs:
  - config_name: default
    data_files:
      - split: train
        path: data/train.csv
      - split: eval
        path: data/eval.csv
      - split: holdout
        path: data/holdout.csv
---

# Chicago DOAH Ordinance Violation Adjudication (2026.09)

**Status: {STATUS_LINE}**

At the moment a City of Chicago Department of Administrative Hearings ordinance-violation case is
docketed, predict whether the hearing officer will find the respondent **liable on at least one
charge**. Everything shipped is on the notice or on the docket at that instant; no disposition,
fine or administrative cost is knowable yet.

- **Artifact version:** `{ARTIFACT_VERSION}`
- **Version tag:** `{RELEASE_TAG}` (use this revision for reproducibility)
- **GitHub counterpart:** {GITHUB_REPOSITORY}
- **Rows:** {ROWS_TOTAL} cases across three disjoint temporal splits

## Loading

Version-pinned. `revision` is the tag, not a branch, so the bytes cannot change under you.

```python
from datasets import load_dataset

ds = load_dataset("__REPO_ID__", revision="{RELEASE_TAG}")
print(ds)
# DatasetDict({
#     train: Dataset({features: [...], num_rows: 47414}),
#     eval: Dataset({features: [...], num_rows: 3436}),
#     holdout: Dataset({features: [...], num_rows: 2913})
# })

# the label is `outcome`, a two-value string target: "Liable" / "Not Liable"
print(ds["train"].features["outcome"])
```

{LOADING_NOTE}

```python
ds = load_dataset("__REPO_ID__", revision="{RELEASE_TAG}"{TOKEN_ARG})
```

The files are also plain CSVs, so they can be used without `datasets`:

```bash
hf download __REPO_ID__ --repo-type dataset --revision {RELEASE_TAG} \
    --include "data/*.csv" --local-dir ./chicago
```

## Splits

One row per `docket_number` (case). The source publishes one row per violation charge, so the case
table was reduced before splitting: a row-level split would leak a case across periods. Split by
the case's earliest recorded violation date, three disjoint periods:

| split | rows | positives | positive rate | window |
| --- | --- | --- | --- | --- |
| `train` | 47,414 | 29,959 | 0.6319 | 2008-01-01 to 2018-01-01 |
| `eval` | 3,436 | 3,077 | 0.8955 | 2018-01-01 to 2022-01-01 |
| `holdout` | 2,913 | 2,715 | 0.9320 | 2022-01-01 to 2026-09-01 |

The rising positive rate is a property of the source, not of the construction: the City republishes
this dataset continuously and older dockets are progressively cleaned up, so recent notice dates
retain mostly the cases that ended in a liability finding. Rates are computed over the shipped
bytes and recorded in `quality.json`.

## The label

`outcome` is the case-level derivation of the City's per-charge `case_disposition`:

- a case is **`Liable`** when at least one of its charges carries a `Liable` disposition;
- a case is **`Not Liable`** when none does and at least one charge carries `Not Liable`;
- a case whose charges are all undecided (`Continuance`, blank, `Non-Suit`, `Default`,
  `Adjudication Performance / Other`, and similar) does **not** ship.

`case_disposition` is the label source column and is not published in the dataset. On the full
source extract, 76,696 of the 130,318 docket numbers seen carry at least one charge that is neither
`Liable` nor `Not Liable` - a mixed-disposition case is the normal case here, not the exception - so
the label is a case-level rule and is documented as derived.

The reduction, measured on the frozen extract (823,955 source rows): 130,318 docket numbers seen,
74,387 dropped with no decided charge, 53 dropped for an incomplete lead charge, 2,115 dropped
outside the declared windows, **53,763 shipped**.

## What is deliberately not shipped

The City's `hearing_date` column is **not published here**, and neither is anything derived from
it. It is documented as "the date of the most recent hearing", so on a decided case it is the
hearing at which the disposition was recorded - after the prediction instant. An earlier version of
this artifact shipped `hearing_date` and a derived `days_to_hearing`, and that derived column
separated the classes on its own at rank AUC **0.8365**. Both were removed before this artifact was
built and gated. The gate itself passed that earlier version: its post-hoc rule keys off the
artifact's own declarations, so a wrong declaration passes. This is worth knowing when reading the
gate result below.

No shipped column separates the classes alone. Rank AUC over the built training split: `ward` 0.505,
`violation_date` 0.502, `street_direction` 0.508, `street_type` 0.503, `distinct_code_count` 0.565,
`charge_count` 0.566.

## Provenance

- Source: City of Chicago - Department of Administrative Hearings (DOAH) Ordinance Violations
  (dataset `6br9-quuz`), https://data.cityofchicago.org/d/6br9-quuz
- Extract frozen at **2026-09-01**: 823,955 rows fetched against a reported 823,955, in 17 pages at
  50,000 rows ordered by `:id`; the source-row digest and the case-table digest are recorded in
  `MANIFEST.json`.
- Extraction: **18 HTTP requests** (1 row-count probe, 17 pages), 92.6s on a 2 vCPU / 2 GB worker.
- Rebuild: `MANIFEST.json` pins the build timestamp, so a rebuild is byte-identical.

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

**Attribution.** City of Chicago, Department of Administrative Hearings Ordinance Violations, City
of Chicago Open Data Portal, https://data.cityofchicago.org/d/6br9-quuz, accessed 2026-09-26.

**Disclaimer (the City's own wording, preserved).** This site provides applications using data that
has been modified for use from its original source, www.cityofchicago.org, the official website of
the City of Chicago. The City of Chicago makes no claims as to the content, accuracy, timeliness,
or completeness of any of the data provided at this site. The data provided at this site is subject
to change at any time. It is understood that the data provided at this site is being used at one's
own risk.

This dataset is **derived** from the City of Chicago's open data and is labelled as derived; it is
**not an official City of Chicago product**, and it carries no endorsement by the City.

## Qualification and baseline

- Gate: **PASSED - 32 checks, 0 failed on the full 53,763-case artifact** (gate 1.3.0), run on the
  worker over the full artifact.
- One baseline through the runner's existing training and validation contract: **eval AUC 0.6915**,
  obtained identically by the runner's `train.py` and `validate.py` on the published bytes. No agent
  or harness comparison was run and none is implied.

Every number above is measured, with the command that produced it recorded in `measurements.json`
and `MANIFEST.json`; figures that are estimates are labelled as such.
