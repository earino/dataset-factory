# Data dictionary

One row per complete (n_hours >= 18) CPCB CAAQM PM2.5 station-day D (as
republished by the XKDR Forum's India Air Quality Database) with a labelable
D+1, at the 23:59 IST prediction instant of day D. Units: PM2.5 in
micrograms/m3 as published (24-hour mean convention); timestamps are naive
IST calendar days (UTC+05:30); the external threshold 90 ug/m3 is the
Poor-band lower breakpoint of CPCB's own National AQI for 24-hour PM2.5.

## Identifier and target

| Column | Role | Meaning |
| --- | --- | --- |
| `station_day` | id | `<station_id>|<date>` - unique across the panel (asserted at construction); the gate's entity key |
| `exceeds` | target | 1 if the station's D+1 calendar-day 24-hr mean PM2.5 is strictly > 90 ug/m3 (both D and D+1 must carry n_hours >= 18); the label source columns (`next_day_pm25_mean`, `next_day_n_hours`) are excluded from every shipped file |

## Features (all knowable at 23:59 IST on day D)

| Column | Meaning |
| --- | --- |
| `station_id` | the publisher's own station identity (high-cardinality, declared) |
| `state_name` | the station's state; the 62 stations without a recorded state ship the declared sentinel `UNKNOWN_STATE`, never an invented state |
| `date` | day D (high-cardinality calendar key, declared) |
| `day_of_week`, `month` | calendar of day D |
| `doy_sin`, `doy_cos` | cyclical day-of-year of D |
| `pm25_mean` | station-day 24-hr mean of hourly PM2.5 (the archive's daily aggregate of the cpcb_caaqm stream) - the persistence feature |
| `pm25_max`, `pm25_min` | station-day maximum / minimum of hourly PM2.5 (same daily aggregate) |
| `n_hours` | hourly readings the daily aggregate covers; >= 18 required for a usable day |
| `pm25_mean_lag1` | the station's mean on D-1 when that day exists with n >= 18; -1.0 otherwise (lags 2 and 3 analogous) |
| `pm25_mean_7d` | mean of the station's valid-day means over D-6..D; -1.0 when fewer than 4 valid days fall in the window |
| `pm25_days_valid_7d` | valid days in that 7-day window (carries the count the mean's sentinel hides) |
| `pm25_mean_30d` | mean over D-29..D; -1.0 under 10 valid days |
| `pm25_days_valid_30d` | valid days in that 30-day window |
| `pm25_hist_mean_90d` | trailing 90-day mean over D-89..D; -1.0 under 30 valid days |
| `days_since_gt90` | days back to the most recent valid day with mean > 90 ug/m3 within D-89..D (0 = today); -1.0 when none |
| `exceed_count_30d` | valid days with mean > 90 ug/m3 in D-29..D |

The `-1.0` sentinels are declared values meaning "not enough valid history",
always paired with the count columns where one exists; they are never imputed
measurements. `state_name` is the only categorical geography feature; the
build never infers a state from a station name.

## Splits (temporal on the prediction instant)

| Split | Window | Rows | Positives | Rate | Distinct positive days | Stations |
| --- | --- | --- | --- | --- | --- | --- |
| `public/train.csv` | 2019-2022 | 288,754 | 61,075 | 21.15% | 1248 | 389 |
| `public/eval.csv` | 2023 | 126,570 | 19,819 | 15.66% | 351 | 509 |
| `private/holdout.csv` | 2024 (sealed) | 145,124 | 18,222 | 12.56% | 352 | 529 |

Excluded and counted per split: thin day D (n_hours < 18) 33,586 / 18,065 / 20,101;
unlabelable D+1 (no row with n_hours >= 18) 17,416 / 9,368 / 10,879; outside the declared
windows 42,638; the 2025-04..09 partial tail 47,566 station-days
(829 valid-day positives); the 2025-01..03 and 2025-10..12 hole
months are asserted empty (0 rows). A thin D+1 is missing outcome data -
counted, never a membership decision on the D row.

## Threshold provenance

90 ug/m3 is not a chosen cut: it is the Poor-band lower breakpoint of CPCB's
own National AQI for 24-hour PM2.5 (About AQI PDF + AQI-Calculator.xlsx,
retained in the candidate's probe evidence), and the label is cross-anchored
to the publisher's own Daily AQI Bulletin (2024-11-18, Delhi Severe 494,
36/39 stations; 36/36 complete station-days exceed in the
measured panel) with the monsoon trough 2023-08-15 as negative control
(389 complete, 1 exceed).
