# Data dictionary - ocha-fts-appeal-funding-trajectory

One row per plan-year appeal: a UN-coordinated single-country humanitarian plan
(HRP, CAP, flash appeal and similar) with a positive launch-vintage original
requirements figure, plan year 2000-2025. Population selection reads only the
appeal's own launch record; excluded groups (multi-country regional groups,
no-orig groups, the pre-2000 window and the 2026+ live edge) are counted in
`quality.json`'s exclusion buckets and never scored.

## Columns (9, shipped order)

| Column | Role | Meaning |
| --- | --- | --- |
| `plan_year_id` | id | Stable identifier for the plan-year appeal (`<planId>-<year>`); unique across the artifact; the runner's `id_columns`. |
| `plan_year_anchor` | feature | The anchor date the panel's temporal reasoning hangs off: the appeal's launch-instant anchor within its plan year (launch evidence: GHO launches early December for the following year; HRP launches end-December to early January; flash appeals launch at event onset). |
| `country_iso3` | feature | ISO3 code of the single country the appeal covers (primary population; multi-country regional groups are excluded and counted). High-cardinality by nature; declared in `quality.json`, not a leak - it reaches perfect AUC only by memorising one row per level. |
| `plan_year` | feature | The plan year the appeal covers. Also the artifact's `time_column`; the temporal split is keyed on it. |
| `plan_type` | feature | The plan's type as FTS records it (Humanitarian Response Plan, flash appeal, etc.). |
| `is_part_of_gho` | feature | Whether the plan-year is part of the Global Humanitarian Overview family, as the plan record states at harvest. |
| `orig_requirements_usd` | feature | ORIGINAL launch-vintage requirements in US dollars (`origRequirements` from the HPC plan endpoint). This is the denominator of the target's 0.5 fraction. Not the revised/current requirements: those are re-publications, unusable as launch features. |
| `years_since_country_prior` | feature | Appeal-recency: plan year minus the plan year of the country's most recent STRICTLY-EARLIER appeal; -1 when the country has no prior appeal. Reads only WHICH strictly-earlier same-country appeals exist (their years) - never any row's outcome - and is derivable by any reader from the shipped row set itself. Asserted label-free by brute-force recompute at construction. |
| `reached_half` | target | 1 when year-end funding >= 50% of original launch-vintage requirements ("covered"), else 0. `positive_label` is 1. Label source: the FTS flow endpoint's per-plan-year `incoming.fundingTotal`, cross-checked against the HDX bulk CSV's funding column on every row at construction; the funding value never ships in any split. |

## What is deliberately absent

- **No prior-outcome history.** The 2026.10-era `country_prior_appeals`,
  `country_prior_covered_rate` and `country_last_prior_covered` columns allowed
  exact cross-row label recovery (a later appeal's features contained a prior
  appeal's outcome) and were removed in the fts-appeal-003 rebuild. No shipped
  column reads any row's outcome.
- **No funding value ships.** The label numerator exists only in the label
  source, outside the CSVs.
- **No revised requirements.** Only launch-vintage `origRequirements` ships.

## Splits

| Split | Plan years | Rows | Positives | Positive rate | Distinct countries |
| --- | --- | ---: | ---: | ---: | ---: |
| train | 2000-2016 | 437 | 279 | 0.638444 | 78 |
| eval | 2017-2020 | 139 | 81 | 0.582734 | 51 |
| holdout | 2021-2025 | 182 | 96 | 0.527473 | 43 |

Temporal on `plan_year`; windows are disjoint. `plan_year_id` does not repeat
across splits (cross-split identifier check is part of the gate). Eval is
labeled development/validation; holdout is final scoring and stays outside
evaluated agents' workspaces until the design is frozen.

## Units and reference frame

Both operands of the target are US dollars from the same publisher in the same
vintage frame: year-end funding (flow `incoming.fundingTotal`) against 0.5 x
launch-vintage `origRequirements`. The 0.5 fraction is a task-defined policy
threshold fixed before construction, not data-derived. In-build fixtures pin the
unit and frame to exact dollar values (AFG 2023 orig 4,627,363,573 / funding
1,678,347,238 / label 0 with the CSV's revised 3,227,372,908 NOT the
denominator; YEM 2023 funding 1,774,327,599; Burundi RRP 2021 slice 14,978,233
of plan total 19,282,778), asserted on every build.
