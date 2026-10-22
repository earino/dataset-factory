---
license: other
license_name: ogl-canada-2.0-attribution-plus-cc0-compilation
license_link: https://open.canada.ca/en/open-government-licence-canada
language:
  - en
pretty_name: TSB Railway Occurrence Casualty (Canada)
size_categories:
  - 1K<n<10K
task_categories:
  - tabular-classification
tags:
  - tabular
  - rail-safety
  - transportation
  - canada
  - temporal-split
  - event-outcome
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

# TSB Railway Occurrence Casualty ({RELEASE_TAG})

**Status: {STATUS_LINE}**

A railway occurrence begins at a known place, time and operating context on the Canadian
federal network - a crossing accident, a derailment, a trespasser event, a fire, a
collision, a movement exceeding limits of authority. **At that instant, will it result in
at least one casualty (a fatality or any injury)?** One row per TSB rail occurrence; the
label is the casualty outcome, which unfolds after onset.

Every feature is a pre-onset property of the occurrence: where (subdivision, nearest
location, province, region, decoded coordinates), which railway, when (year, month,
day-of-week, local hour, site timezone) and what the train was doing (activity type).
Everything TSB records during or after the occurrence is excluded by construction and
never ships: its accident/incident taxonomy (whose own type names embed outcomes), all
injury and dangerous-goods and damage fields, at-scene weather, investigation and
process dates, the free-text summary, and even ReportedDate/ReportedTime (the
notification instant post-dates onset). The label is derived from injury fields that are
excluded from every shipped file and cross-checked against the publisher's separate
INJURIES child table on all 1,624 positive panel rows.

- **Artifact version:** `{ARTIFACT_VERSION}`
- **Version tag:** `{RELEASE_TAG}` (use this revision for reproducibility)
- **Rows:** {ROWS_TOTAL} occurrences across three disjoint temporal splits
- **GitHub counterpart:** {GITHUB_REPOSITORY}

## Splits

| split | rows | occurrence dates | positive rate |
| --- | ---: | --- | ---: |
| `train` | 7,925 | 2016-01-01 .. 2021-12-31 | 11.1% |
| `eval` | 3,831 | 2022-01-01 .. 2024-12-31 | 12.1% |
| `holdout` | 1,976 | 2025-01-01 .. 2026-08-31 | 14.1% |

The splits are temporal and disjoint on the occurrence date. Both classes appear in every
window and every year. Each positive is an independent occurrence - there is no
storm-style clustering, so the row counts are also the independent-event counts
(distinct_events == positives in eval and holdout).

The panel starts **2016-01-01 by measurement, not assumption**: TSB's pre-2016 rows carry
a legacy taxonomy-era signature (HISTORICAL / DG LEAKER categories) that fades gradually
(2-7% through 2015, ~0 from 2017), so earlier years describe a different reporting
regime. The vintage is pinned by sha256 in `meta.json` (RODS republish of 2026-10-21,
data through 2026-08-31); RODS is republished monthly and only the current vintage
exists, which is documented rather than assumed away.

## Reference points

The references the model had to beat, measured at construction on the written rows (rank
AUC): the persistence analogue (a trailing-12-month casualty rate) reaches only **0.527
eval / 0.495 holdout**, and the best single context column, `activity_type`, reaches
**0.707 / 0.699**. The runner-contract XGBoost baseline - the benchmark's own
unmodified `train.py` + `validate.sh` on the fetched, digest-verified, gate-re-accepted
bytes - measures **0.8126 eval AUC**, reproduced exactly by validate.py's independent
recompute. The model clears persistence by +0.286 and the best single column by +0.106:
the pre-onset context carries real signal, and the persistence-dominance failure mode
seen on some panel tasks is absent here. The holdout was not scored by anything.

## Source and provenance

- Transportation Safety Board of Canada, Rail Occurrence Database System (RODS),
  "Rail transportation occurrence data from January 1983" - five anonymous bulk CSVs,
  fetched 2026-10-21 (157,183,629 bytes, per-file sha256 in `meta.json`).
- Cross-checks against the publisher's own summary product: panel year 2025 counts
  832 ACCIDENT vs 831 published and 331 INCIDENT vs 332 published (within 0.3% of TSB's
  own 2025 annual summary); label agreement with the INJURIES child table on all
  positive rows.
- Coordinates: RODS packs lat/long in three magnitude-disjoint encodings (ddmm.ff
  dominant, x10^3, x10^6); the build decodes with a measured rule (0 ambiguous,
  0 undecodable over a 3,088-value window) and asserts the Canadian envelope on all
  13,732 written rows.
- Construction: `code/build.py`, executed by worker job `tsb-004`; qualification gate
  1.4.0, 37/37 checks, 0 failed, artifact version `{ARTIFACT_VERSION}`; baseline job
  `tsb-baseline-001`, contract AUC 0.8126.

## Licence

The source data are Transportation Safety Board of Canada materials under the **Open
Government Licence - Canada 2.0**; that attribution condition carries through to every
copy of the derived data ("Contains information licensed under the Open Government
Licence - Canada"). Our contribution to the derived compilation is dedicated **CC0-1.0**;
our code is **MIT**. This is a derived research dataset, not a TSB official product, and
the TSB has not reviewed or endorsed it. See `LICENSE.md` in the repository for the full
terms and attribution statement.

## Use with the runner

```bash
python3 get_dataset.py --dest ./task
python3 code/qualify_dataset.py ./task
sh baseline/reproduce_baseline.sh ./task
```
