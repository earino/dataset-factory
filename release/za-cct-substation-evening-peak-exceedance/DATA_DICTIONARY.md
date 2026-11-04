# Data dictionary

Grain: one row per switching substation (33/66/132kV) per target day D with at
least 30 prior evenings of history at the 06:00 SAST prediction instant
(burn-in station-days are counted and never scored). Identity `station_day`
is unique across the panel, asserted at construction. All times are
Africa/Johannesburg (SAST, UTC+2, no DST).

| Column | Unit / domain | Meaning and reference frame |
| --- | --- | --- |
| `station_day` | `<station>\|<date>` | row identifier (id column, not a feature). Names one station-day with one label; unique across the panel |
| `station` | category (41 levels) | the publisher's own switching-substation column name (e.g. `Grassy_Park_66kV`). Engineering telemetry; no personal data |
| `date` | YYYY-MM-DD (SAST) | the target day D (time column). Declared high-cardinality, not a leak: a date level is every station's station-day of that date and its label varies across stations |
| `day_of_week` | 0-6 | calendar day of week of D |
| `day_of_year` | 1-366 | calendar day of year of D |
| `doy_sin`, `doy_cos` | [-1, 1] | cyclical encoding of `day_of_year` |
| `month` | 1-12 | calendar month of D |
| `m00_00` ... `m05_30` (12 columns) | MVA | the same-day 00:00-06:00 SAST half-hourly readings of D (slot label = slot start; the `m05_30` slot completes exactly at the 06:00 instant). Publisher caveat: indicative measured MVA, not corrected for temporary load shifts or load fluctuations due to load shedding |
| `morning_mean`, `morning_max`, `morning_min` | MVA | mean / max / min of the twelve same-day morning slots |
| `hist_morningpeak_mean_90` | MVA | mean of the trailing <= 90 prior days' MORNING peaks (latest member D-1) - the only history-derived shipped column; morning peaks are never label operands |
| `exceeds` | 0/1 (target) | 1 when the day's evening peak (max half-hourly MVA over 16:00-22:00 SAST) exceeds the station's trailing-90-evening p95 (minimum 30 prior evenings); computed from the sealed evening matrix at construction |

Label source columns (the target day's evening readings 16:00-21:30 and the
trailing-evening p95 threshold) are sealed in `auxiliary/evening_peaks.csv`
outside every solver-visible frame and ship in NO split file. Post-hoc by
construction: every evening reading of any day (a sliding evening quantile's
day-over-day delta reconstructs the entering evening's exceedance at 0.995
exact agreement on synthetic bytes), which is why no evening-derived value
ships in any form - raw, rounded, windowed or differenced.

Known regimes a careful consumer should know: Cape Town's 2022-2024
load-shedding suppresses observed peaks (publisher caveat, quoted above);
winter evenings peak higher than summer (measured fixture: monthly mean
evening peak 2024-07 61.9 MVA vs 2024-12 44.1 MVA; per-station winter/summer
ratios 1.25 residential vs 0.98 CBD); positive rate drifts across splits
(11.20% train 2022, 8.39% eval 2023, 9.21% holdout 2024).
