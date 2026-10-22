# Data dictionary

One row per (premise, item, target week). `row_id` = `<premise_code>-<item_code>-<target week start>`.

| Column | Type | Meaning |
| --- | --- | --- |
| `row_id` | string | unique row identifier |
| `target_week` | date | Monday of week W+1, the outcome week (time column) |
| `price` | float | modal price in week W (MYR); ties broken toward the higher price |
| `n_obs` | int | observations of this pair in week W |
| `price_lag1`, `price_lag2`, `price_lag4` | float | modal price in W-1, W-2, W-4; **-1.0 sentinel** when absent |
| `delta_1w`, `delta_4w` | float | price minus the lagged price; -1.0 sentinel when the lag is absent |
| `mean4`, `std4`, `min4`, `max4` | float | statistics over the modal prices of W, W-1, W-2, W-4 |
| `price_vs_mean4` | float | price minus mean4 |
| `week_of_year` | int | ISO week number of W |
| `month` | int | calendar month of W |
| `item_code`, `premise_code` | int | publisher identifiers (categorical) |
| `state` | string | premise state; this artifact ships Johor only |
| `increases` | int | label: 1 when the modal price in W+1 is strictly higher than in W |

Sentinel values are negative and cannot collide with a price, which is strictly positive.
