# Data dictionary

One row per assessed wildfire in Alberta's Forest Protection Area, 2006-2025
(27,828 rows), at the publisher's own initial-assessment instant
(`assessment_datetime`, "the date and time the wildfire was originally
assessed by Alberta Wildfire employees"). Timestamps carry no timezone marker
and are read as America/Edmonton local operational time (confirmed against the
official 2016 Horse River review). Units: hectares for areas, metres/minute
for rate of spread, degrees Celsius, percent relative humidity, km/h wind,
decimal degrees for coordinates, hours for elapsed times. The publisher's own
field definitions for every column are transcribed verbatim in
`publisher-data-dictionary-transcript.md` - that transcript, not this summary,
is the documentary authority.

## Identifier and target

| Column | Role | Meaning |
| --- | --- | --- |
| `fire_id` | id | `<YEAR>-<FIRE_NUMBER>`, unique across the population (asserted at construction) |
| `escape` | target | 1 if final area burned (`current_size`, the publisher's "final area burned of the wildfire") is >= 100 ha on the current compilation's recorded value; 0 otherwise. The label sources (`current_size`, `size_class`, `first_uc_date`) are excluded from every shipped file |

## Features (all documented at/before the assessment instant)

| Column | Meaning | Coverage train/eval/holdout |
| --- | --- | --- |
| `assessment_ts`, `assessment_date` | the prediction instant (naive local Alberta time; high-cardinality keys, declared) | 100% |
| `assessment_hectares` | size of the wildfire at the time of assessment, to the nearest hectare or hundredth of a hectare - the persistence feature | 100% |
| `fire_spread_rate` | rate of spread at the time of initial assessment (m/min) | 88.9% / 86.8% / 94.6% |
| `fire_type` | fire behaviour type at assessment (categorical) | 89.2% / 88.1% / 96.0% |
| `fire_position_on_slope` | position on slope at assessment (categorical) | 88.8% / 86.5% / 94.2% |
| `weather_conditions_over_fire` | in-situ weather conditions over the fire at assessment (categorical) | 88.7% / 86.5% / 94.2% |
| `temperature`, `relative_humidity`, `wind_speed`, `wind_direction` | in-situ weather over the fire at the time of initial assessment | ~88.7% / ~86.5% / ~94.1% |
| `fuel_type` | FBP fuel type at assessment (categorical) | 68.9% / 70.8% / 81.6% |
| `detection_agent_type` | detection channel category (lookup/planned/unplanned/other; the publisher documents blanks for unplanned detection) | 100% |
| `hours_report_to_assessment` | elapsed hours from REPORTED_DATE (first report to Alberta Wildfire) to the assessment instant | 100% |
| `hours_discovery_to_assessment` | elapsed hours from DISCOVERED_DATE; blank where the discovery timestamp is absent (dictionary-documented unplanned-detection blanks) | 89.1% / 71.9% / 59.9% |
| `hours_start_to_assessment` | elapsed hours from FIRE_START_DATE (estimated or witnessed start); blank where absent | 97.4% / 97.2% / 97.6% |
| `day_of_week`, `month`, `doy_sin`, `doy_cos` | calendar of the assessment instant and cyclical day-of-year | 100% |
| `forest_area` | the Forest Protection Area zone prefix of the fire (categorical) | 100% |
| `latitude`, `longitude` | ignition-area location (GPS; the shipped value is the current confirmed ignition-area location - flagged in the evaluation contract, since the dictionary documents it may be further investigated as the wildfire progresses) | 100% |

Blank cells are real missingness, shipped as blank (never imputed by the
build); the missingness pattern itself drifts with the detection-channel mix
(recorded in `measurements.json`). Excluded by the build's column policy with
measured ordering evidence: the cause family (temporary under-investigation
cause), the dispatch block (dispatch_date falls after assessment for 2.41% of
rows), all suppression/milestone fields, `fire_name`, `fire_origin`,
`discovered_size`, `detection_agent` and both label sources - the full list is
in `measurements.json` `column_policy`.

## Splits (temporal on the assessment instant's calendar year)

| Split | Window | Rows | Positives | Rate | Distinct positive dates |
| --- | --- | --- | --- | --- | --- |
| `public/train.csv` | 2006-2015 | 15,864 | 297 | 1.87% | 156 |
| `public/eval.csv` | 2016-2020 | 5,707 | 104 | 1.82% | 79 |
| `private/holdout.csv` | 2021-2025 (sealed) | 6,257 | 257 | 4.11% | 128 |

Winter (Nov-Feb) rows are kept and counted (587); 356 winter carryover
fires assessed in the year after their record year move with their assessment
instant, and the label-side counts are identical under either split rule.

## Threshold provenance

100 ha is not a publisher standard: it is the escape-from-initial-attack
reading fixed at discovery (variants at 4/40/200 ha measured and recorded in
the candidate record; 100 ha sits inside the publisher's size-class D band,
40-200 ha), anchored by ten named-fire fixtures asserted at their
publisher-documented final sizes - Horse River 2016 (MWF009) at 485,123.6 ha
must be a positive, the already-controlled LWF002 2023 (0.01 ha) must be a
negative - and bounded by the revision-sensitivity measurement: 89 fires
lie within +-20% of the threshold, so the documented in-place area revisions
can flip at most that band.
