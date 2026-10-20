# Data dictionary

Every shipped column, with the publisher's own documentation of the source field it comes from
(the Food Inspections column reference at
<https://data.cityofchicago.org/d/4ijn-s7e5>, 21 documented columns, read 2026-09-27) and its
availability relative to the prediction instant. **One row = one inspection of one Chicago food
establishment** (`inspection_id`) in the constructed pool; all 40 configs ship the identical pool
and the identical 18-column shape - only the target column name differs (`code_<NN>`).

The prediction instant is **the moment the inspection opens** (the `inspection_date`, shipped
unchanged): the date is known when a canvass is scheduled or a complaint triggers a visit, and
everything the inspector observes or records during or after the visit is post-hoc. The label
source (`violations`) and the inspection outcome (`results`) are excluded from the shipped
columns, not merely unlisted. The gate (version 1.3.0) verified per config that no shipped column
determines the label and that every feature is available at that instant.

## Identifier and time columns

| column | source field | meaning | role |
| --- | --- | --- | --- |
| `inspection_id` | `Inspection ID` | the portal's unique inspection identifier | identifier (`id_columns`); not a feature |
| `license_` | `License #` | the establishment's licence number - the entity whose prior inspections form the history features | feature, declared high-cardinality: spans split windows by design because prior history is the point of the task |
| `inspection_date` | `Inspection Date` | the date the inspection was performed - the prediction instant | time column (`time_column`), feature, declared high-cardinality |

## Static facility attributes (known before any visit)

| column | source field | meaning |
| --- | --- | --- |
| `facility_type` | `Facility Type` | the publisher's facility description (restaurant, grocery store, school, ...) |
| `risk` | `Risk` | the City's risk category for the facility (Risk 1 / 2 / 3 or empty) |
| `zip` | `Zip` | the facility's ZIP code |
| `latitude` | `Latitude` | the facility's latitude | 
| `longitude` | `Longitude` | the facility's longitude |

`latitude`/`longitude` are declared high-cardinality; they ship as documented location fields
with the publisher's own precision, not as a coarsened block.

## The inspection's own trigger (recorded when the inspection opens)

| column | source field | meaning |
| --- | --- | --- |
| `inspection_type` | `Inspection Type` | the inspection's own type (canvass, complaint, re-inspection, license, ...) - known when the visit is scheduled or triggered |

## Calendar position of the inspection date

| column | meaning |
| --- | --- |
| `day_of_week` | day-of-week of `inspection_date` (0 = Monday) |
| `month` | calendar month of `inspection_date`, 1-12 |

## The licence's own strictly-earlier history

All six priors use only pooled inspections of the **same licence** with a **strictly earlier**
`inspection_date`. Inspections of the same licence on the same date form one group and all see
the same prior state, so a same-day re-inspection can never serve as its own evidence. `-1` marks
"no strictly-earlier pooled inspection"; `previous_result` is the empty string for that case.

| column | meaning |
| --- | --- |
| `prior_inspections` | count of the licence's strictly-earlier pooled inspections |
| `days_since_previous` | calendar days between this `inspection_date` and the licence's most recent strictly-earlier `inspection_date`; `-1` when none exists |
| `previous_result` | the `results` value of the licence's most recent strictly-earlier pooled inspection (Pass / Fail / Pass w/ Conditions); empty when none exists |
| `prior_fail_rate` | share of the licence's strictly-earlier pooled inspections whose `results` value is Fail, in [0,1]; `-1` when none exists |
| `prior_mean_code_count` | mean number of distinct violation codes over the licence's strictly-earlier pooled inspections, rounded to 4 decimals; `-1` when none exists |
| `prev_code_present` | 1 if the **target code** was cited on the licence's **most recent** strictly-earlier pooled inspection, 0 if it was not, `-1` when none exists |

`prev_code_present` is the one feature that differs between configs: each config's copy answers
about its own target code. It is also the persistence reference: `MANIFEST.json`
(`measurements.levels.<config>.persistence_baseline`) records the eval AUC of
`prev_code_present` alone on each config's own bytes, so any model's headroom over the target
code's own persistence is checkable per config.

## The target (per config)

| column | meaning |
| --- | --- |
| `code_<NN>` | 1 if violation code NN is among the codes parsed from this inspection's `violations` blob, else 0. The label source column `violations` never ships. Codes are parsed by number (`\d+.` at a pipe boundary), never by description string: 28 of the 61 observed codes have more than one wording across the 16.7-year history. |

The 40 shipped codes are the ones clearing the floor on the constructed pool (>= 1% pool rate
and >= 30 positives on >= 20 distinct days in every window). Codes 12, 18, 19, 24, 30, 31, 34 and
42 cleared the rate floor but not the per-window minimums and do not ship.

## The joint multi-label matrix

`labels.csv` at the dataset root is not a runner config and is not gated: it is the 40 shipped
code columns of every pooled inspection in one file (226,417 rows), so the set formulation is
consumable without re-pulling the source. Its digest is recorded in `MANIFEST.json`
(`measurements.labels_csv`) and `SHA256SUMS`.

## What never ships

`violations` (the label source, including the per-violation comment text) and `results` (the
inspection outcome) are the publisher's post-visit fields and are excluded from every shipped
CSV. The remaining documented portal fields either never enter the pool (the pool keeps results
in Pass / Fail / Pass w/ Conditions only) or are dropped at construction: `Inspection ID`
survives only as the identifier, and the address block, the inspector's `Inspections`-internal
fields and every comment string are dropped in favour of the documented columns above.
