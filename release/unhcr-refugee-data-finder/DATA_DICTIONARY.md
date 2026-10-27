# Data dictionary

One row per origin-asylum corridor label year T (= D+1): a corridor eligible at the last
fully published year D (its year-D government/procedure persons total >= 500 and a
published year-D-1 corridor value), with the year-D+1 outcome as the label. The panel is
built from the HDX distribution `asylum_applications_residing_world.csv` (vintage
2026-08-20): government-procedure (G) and-persons rows, all application types summed, years
2000-2025. 7,212 shipped rows of the eligible frame; every exclusion is counted with a
reason (377 `missing_history`, 21+7+5 host-silent `unobserved_target`, 496 live-edge
label-year-2026).

## Columns

| Column | Role | Definition |
| --- | --- | --- |
| `row_id` | id | Stable row identifier (`<origin>-<asylum>-<target_year>`). One row per corridor label year. |
| `doubled` | **target** | 1 if the corridor's year-T (= D+1) G/P persons total is at least 2x its year-D total, else 0. Positive rate: train 8.42%, eval 8.74%, holdout 11.57%. Corridors whose host files no G/P report at all in T are censored (label undefined), never counted as zero. |
| `target_date` | time column | 1 January of the label year T; the split time column (train < 2017-01-01 <= eval < 2022-01-01 <= holdout < 2026-01-01). |
| `surge_cluster` | event key | `<origin>|<target_year>` - the clustered-event key the gate counts independent positive events on (183/109/133 positive clusters across train/eval/holdout). |
| `target_year` | feature | The label year T (= D+1). Calendar position of the row; a declared feature (the task's information set includes the calendar). |
| `origin` | feature | ISO3 country of origin. High-cardinality identity (declared). |
| `asylum` | feature | ISO3 country of asylum. High-cardinality identity (declared). |
| `apps_d` | feature | Corridor's year-D total G/P applications (persons, all application types summed). |
| `apps_d1` | feature | Corridor's year-D-1 total G/P applications. Eligibility requires this cell to be published. |
| `log_growth_d` | feature | log(apps_d + 1) - log(apps_d1 + 1): the corridor's momentum observed at the instant. The persistence reference. |
| `surged_recently` | feature | 1 when the corridor's year-D total is at least double its year-D-1 total (it already doubled once); the binary persistence reference. |
| `host_apps_d` | feature | The host country's total year-D G/P applications across all origins. |
| `host_growth_d` | feature | log host total year D - log host total year D-1. |
| `origin_apps_d` | feature | The origin country's total year-D G/P applications across all hosts. |
| `origin_growth_d` | feature | log origin total year D - log origin total year D-1. |
| `corridor_age` | feature | year D minus the corridor's first observed panel year (how long the corridor has existed in the panel, in years). |

Every feature reads only published years <= D - knowable at the publication instant. The
year-T value never ships in any column; the label source (the year-T panel cell) is excluded
from the shipped columns and asserted absent by the construction.

## Known cross-row exposure (declared, measured)

`surged_recently` of a corridor's label-year T+1 row equals `doubled` of its label-year T
row - the panel self-answers across adjacent rows. The gate executed the declared probe
`next_label_year_exposes_outcome` on every split (coverage 2,439 / 1,265 / 1,239 rows,
0 mismatches). This is why `quality.json`'s evaluation contract fixes `access` to
`isolated_rows`: rows must be consumed under the restricted protocol (no peeking at the
same corridor's later row), and the artifact makes no historical-forecasting claim.

## Splits

Temporal on `target_date`: train label years 2002-2016 (3,363 rows / 283 positives / 183
clusters), eval 2017-2021 (1,887 / 165 / 109), holdout 2022-2025 (1,962 / 227 / 133). Both
classes are present in every window; eval and holdout sit far above the gate's minimums
(30 positives / 20 distinct events).
