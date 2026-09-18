# austin-911-response

**Status: selected lead candidate (2026-09-18).**

## Why this is the lead

Chosen over the Chicago adjudication candidate on one hard criterion: this source is
explicitly **Public Domain** in the Socrata catalog metadata, while Chicago's is
"See Terms of Use". The project must publish a dataset publicly, and PROJECT.md
requires usable source permissions, so a source whose remaining risk is technical
rather than legal is the better first release.

## Measured evidence (2026-09-18, anonymous API)

Endpoint: `https://datahub.austintexas.gov/resource/e687-fx2y.json`

| Query | Result |
|---|---|
| `$select=count(*)` | 1,049,636 rows |
| rows per year (`date_trunc_y`) | 2023: 286,145 / 2024: 286,035 / 2025: 285,665 / 2026 to 09-18: 191,791 |
| `priority_level` counts | P0 141,710 / P1 186,787 / P2 516,736 / P3 204,403 |
| `response_time IS NULL` | 0 |
| bounded sample | `response_time` 165 and 848 - seconds, not minutes; confirm against timestamps |

42 columns are present, including dispatch-time, arrival-time, closing-time and
injury fields. No distribution of `response_time` has been measured yet, so no
threshold and no headroom claim is possible.

## Features available at the prediction time

`incident_type`, `priority_level`, `sector`, `council_district`, `geoid`, `blkgpnm`,
`response_day_of_week`, `response_hour`, plus derived calendar position.

## Columns that must be excluded (post-hoc)

`first_unit_arrived_datetime`, `call_closed_datetime`, `response_time` (the label
source), `final_problem_description`, `final_problem_category`,
`call_disposition_description`, `number_of_units_arrived`, `unit_time_on_scene`,
`report_written_flag`, all three `*injured_killed_count` fields, and
`mental_health_flag` unless the column docs show it is set at dispatch.

`mental_health_flag` is the one open question: a flag set by the call-taker before
dispatch is legitimate, a later determination is leakage. Confirm before building.

## Construction plan

1. Read the column documentation for `response_time` and `mental_health_flag`.
2. Build a bounded sample on the coordinator (never the full million rows).
3. Write the construction script that pulls the full series on a worker, freezes an
   extract with recorded SHA-256 checksums, measures the `response_time`
   distribution, and fixes threshold T from the training window only.
4. Temporal split by `response_datetime`; report the base rate of the positive class.
5. Simple baseline first, then compare a competent model.

## Open blockers

- Worker credentials and allowance are not provisioned, so the full extraction
  cannot run yet. Nothing here depends on that: the API and the schema are verified.
- No licence text has been read beyond the catalog's Public Domain field.
