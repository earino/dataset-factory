# Data dictionary

One row per (island, anchor trading day D). Target: `target_high_price`.
Id column: `row_id`. Every shipped quantity is derived from the publisher's
FinalEnergyPrices values (TradingDate, TradingPeriod, PointOfConnection,
DollarsPerMegawattHour) or from the calendar; the island assignment comes from
the publisher's NetworkSupplyPointsTable mapping. The price unit is
NZD/MWh (nominal), and every price statistic is the **island daily mean**:
the mean of `DollarsPerMegawattHour` over every (POC x trading period) row of
that island and trading day, using POCs mapped by the current-vintage mapping
table (unmapped POCs are excluded and counted).

## Shipped columns

| Column | Role | Unit | Documented meaning and reference frame | Available at the instant (D + 6 days)? |
|---|---|---|---|---|
| `row_id` | id | composite `{island}-{anchor_date}` | Unique per row; the runner's id column. | yes (row identity) |
| `target_high_price` | target | binary indicator | 1 iff the island daily mean price on trading day D+7 exceeds NZD 100/MWh (threshold frozen from the training-window design). | no - the label |
| `anchor_date` | carry (time column) | calendar date | The anchor trading day D whose final prices have just been published; the split time column. Declared high-cardinality, not a leak: a date identifies one row per island. | yes (row identity) |
| `target_week` | carry (event key) | ISO week | ISO week of the target day D+7, market-wide (both islands share a week). The clustered event key: positives arrive in multi-day weather/storage episodes, so split capacity is counted per distinct positive target-week (404/231/152 in train/eval/holdout). Weeks within one long storage crisis are not fully independent; the count is a capacity floor, not an independence proof. | yes (derived from the anchor date) |
| `island` | feature | NI / SI | The island whose daily mean price is predicted: the publisher's two-island market structure. | yes |
| `last_day_mean` | feature | NZD/MWh (nominal) | Island daily mean final price for the anchor day D itself - the most recent published value, and the persistence analogue the task must beat. | yes |
| `mean_7d` | feature | NZD/MWh (nominal) | Mean of the island daily mean over trading days D-6..D (published). | yes |
| `mean_30d` | feature | NZD/MWh (nominal) | Mean of the island daily mean over trading days D-29..D (published). | yes |
| `max_30d` | feature | NZD/MWh (nominal) | Maximum island daily mean over D-29..D (published). | yes |
| `std_7d` | feature | NZD/MWh (nominal) | Standard deviation of the island daily mean over D-6..D (published). | yes |
| `days_above_threshold_30d` | feature | count (days) | Number of trading days in D-29..D whose island daily mean exceeded the same NZD 100/MWh threshold. | yes |
| `cross_island_ratio_7d` | feature | ratio (dimensionless) | The row's island 7-day mean divided by the other island's 7-day mean (both published in the same files; the market's hydro-transfer imbalance signal). | yes |
| `anchor_month` | feature | month number | Calendar month of the anchor day D (seasonality). | yes |
| `anchor_dow` | feature | day of week | Day of week of the anchor day D. | yes |
| `anchor_doy_sin` / `anchor_doy_cos` | feature | dimensionless (cyclical) | sin/cos of the anchor day's day-of-year angle - the cyclical encoding of position in the year. | yes |

## Excluded by construction (never shipped)

The label source columns and every post-hoc quantity are excluded from all
shipped files, and their absence is asserted in-build against every written
header:

- `target_day_island_mean_price` and `target_day_DollarsPerMegawattHour_rows` -
  the label source: the D+7 island mean and the row count it was computed from.
- Every per-POC price of the target day D+7 (the target day has not finished
  trading at the instant).
- Interim (`_I`) and incomplete price-file variants - excluded and counted
  (3 interim + 1 incomplete over the 728 listed blobs).
- Rows whose POC is absent from the current-vintage NetworkSupplyPointsTable
  (retired POCs) - excluded from island aggregation and counted per year
  (9,437,515 source rows in total over 1996-2026).

## Units and reference frames

The threshold and every price feature share one unit and frame: NZD/MWh
(nominal), island daily mean of the publisher's final
`DollarsPerMegawattHour` values. The comparison `>` is frame-consistent by
construction, and the threshold is fixed at NZD 100/MWh from the
training-window design (the Authority's own review records 2019 average spot
$127/MWh and 2020 $105/MWh). The known-event fixtures are asserted in-build
on the constructed panel: the August 2024 dry-year episode (four days at
814.77-883.56 market means must exceed; the Authority's Review of winter 2024
records "in early August the average daily price reached $820/MWh"),
2008-07-01 (mean 305.79 must exceed) and the January 1997 quiet control
(max 50.0 must not).

## Timing (prediction instant)

The publication instant of final prices for trading day D, placed at D + 6
calendar days. The Authority documents that interim prices "will be declared
to be final prices by 2pm the following business day"; measured on the
publisher's daily-file channel, Last-Modified minus trade date is 0-5 calendar
days over 365+ files, so D+6 covers the maximum measured lag. Features read
final prices for trading days <= D; the target day D+7 has not finished
trading at the instant, so its price cannot exist there under any publication
scheme. Membership requires only data published by the instant (both islands'
daily means for D-29..D); a missing target day is missing outcome data, never a
membership decision. See `quality.json`'s `timing` block for the full
declaration, including the observed publication dates.
