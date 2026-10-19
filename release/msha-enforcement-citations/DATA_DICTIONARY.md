# Data dictionary

Every shipped column, with the publisher's own documentation of the source field it comes from
(`Violations_Definition_File.txt`, `Inspections Definition File`, `Mines Definition File` at
<https://arlweb.msha.gov/OpenGovernmentData/DataSets/>) and its availability relative to the
prediction instant. **One row = one MSHA inspection event** (`EVENT_NO`) in the constructed pool;
all 45 configs ship the identical pool and the identical 25-column shape - only the target column
name differs (`sec_<section>`).

The prediction instant is **the start of the inspection** (`INSPECTION_BEGIN_DT`, shipped as
`inspection_date`): everything the inspector observes or records during or after the visit is
post-hoc and excluded from the shipped columns. The gate (version 1.3.0) verified per config that
no shipped column determines the label and that every feature is available at that instant.

## Identifier and time columns

| column | source field | meaning | role |
| --- | --- | --- | --- |
| `event_no` | Inspections `EVENT_NO` | the MSHA inspection event number; join key to the Violations table | identifier (`id_columns`); not a feature |
| `mine_id` | Mines `MINE_ID` | the mine the inspection belongs to | feature, declared high-cardinality: the panel entity, spans split windows by design because prior history is the point of the task |
| `inspection_date` | Inspections `INSPECTION_BEGIN_DT` | the date the inspection began - the prediction instant | time column (`time_column`), feature, declared high-cardinality |

## Structural mine attributes (Mines table - static at prediction time)

| column | source field | meaning |
| --- | --- | --- |
| `coal_metal_ind` | `COAL_METAL_IND` | the mine's coal vs metal/non-metal classification (C/M) |
| `mine_type` | `CURRENT_MINE_TYPE` | facility type (e.g. Underground, Surface, Facility) |
| `state` | `STATE` | the mine's state |
| `fips_cnty_cd` | `FIPS_CNTY_CD` | the mine's county FIPS code |
| `primary_canvass` | `PRIMARY_CANVASS` | the primary SIC-based canvass (industry family, e.g. Coal, Stone/Sand/Gravel) |
| `company_type` | `COMPANY_TYPE` | the operating company's type |
| `days_per_week` | `DAYS_PER_WEEK` | operating days per week at the mine |
| `hours_per_shift` | `HOURS_PER_SHIFT` | hours per shift at the mine |
| `prod_shifts_per_day` | `PROD_SHIFTS_PER_DAY` | production shifts per day at the mine |
| `portable_operation` | `PORTABLE_OPERATION` | whether the mine is a portable operation |

## The inspection's own trigger (Inspections table - recorded when the inspection opens)

| column | source field | meaning |
| --- | --- | --- |
| `activity_code` | `ACTIVITY_CODE` / `ACTIVITY` | why the inspection happened (e.g. mandatory, complaint, follow-up) - the inspection's own trigger |
| `program_area` | `PROGRAM_AREA` | enforcement program area (Coal, Metal/Non-Metal) |
| `inspect_office_cd` | `INSPECT_OFFICE_CD` | the district office conducting the inspection |

## Calendar position of the begin date

| column | meaning |
| --- | --- |
| `month` | calendar month of `inspection_date` |
| `day_of_week` | day-of-week of `inspection_date` |

## The mine's own strictly-earlier history

All five priors use only inspections of the same mine with a **strictly earlier** begin date.
Rows of the same mine and date form one group and all see the same prior state, so a same-day
follow-up can never serve as its own evidence. `-1` marks "no strictly-earlier inspection".

| column | meaning |
| --- | --- |
| `prior_inspections` | count of the mine's strictly-earlier pooled inspections |
| `days_since_previous` | days between this begin date and the mine's most recent strictly-earlier begin date |
| `prior_citation_count` | citations accumulated over **every** strictly-earlier inspection of the mine |
| `prior_mean_citations` | `prior_citation_count / prior_inspections`, rounded to 4 decimals |
| `prior_distinct_sections` | distinct 30 CFR sections cited across the mine's strictly-earlier inspections |
| `prev_target_cited` | 1 if the **target section** was cited on the mine's **most recent** strictly-earlier pooled inspection, else 0 |

`prev_target_cited` is the feature whose semantics were corrected during construction: it
documents the most-recent-strictly-earlier snapshot, not the cumulative ever-cited set. An
earlier build wrote the cumulative reading (job msha-001); that artifact was superseded before
collection and never published. `VERIFICATION.md` records the byte-level proof that the released
bytes carry the corrected feature.

## Target

| column | meaning |
| --- | --- |
| `sec_<section>` | 1 if 30 CFR `<section>` appears among the `PART_SECTION` values cited at this inspection, else 0. The label source column is `PART_SECTION` (Violations table); it and every other violation-level attribute are excluded from the shipped columns. |

## Excluded, never shipped

The label source (`PART_SECTION`) and the post-hoc fields the publisher documents are absent
from the CSVs, not merely unlisted in a feature manifest: `SIG_SUB`, `NEGLIGENCE`, `LIKELIHOOD`,
`INJ_ILLNESS`, `NO_AFFECTED`, `ENFORCEMENT_AREA`, `SPECIAL_ASSESS`, `SECTION_OF_ACT*`,
`CIT_ORD_SAFE`, `VIOLATION_NO`, every date after the begin date (`VIOLATION_ISSUE_DT`,
`ORIG_TERM_DUE_DT`, `LATEST_TERM_DUE_DT`, `TERMINATION_DT`, `VACATE_DT`, `FINAL_ORDER_ISSUE_DT`,
`INSPECTION_END_DT`), the penalty and payment fields, the end-of-visit inspection counts
(`TOTAL_ON_SITE_HOURS`, `TOTAL_INSP_HOURS`, `NBR_INSPECTORS`, `ACTIVE_SECTIONS`, area flags,
sample counts), and the current-status fields that move after the window opens
(`CURRENT_MINE_STATUS`, `CURRENT_STATUS_DT`, `CURRENT_103I*`, controller/operator identity,
`NO_EMPLOYEES`). The full list per config is in each `quality.json`'s `post_hoc_columns` block.

## The joint matrix (dataset root, not a config)

`labels.csv` is the multi-label record the 45 binary configs are instantiated from: one row per
pooled inspection (`event_no`), one column per floor section. It ships for analysis and for
instantiating further configs; it is documented rather than gated, and the gated artifacts are
the 45 config directories.

## Missingness

`-1` encodes "no strictly-earlier history" in the five prior features (the first inspection of a
mine). Categorical mine attributes are the publisher's own codes and are not imputed anywhere.
