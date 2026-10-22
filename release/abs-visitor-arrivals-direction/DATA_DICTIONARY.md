# Data dictionary

One row per (country of residence, target month). `row_id` is unique.

| Column | Type | Meaning |
| --- | --- | --- |
| `row_id` | string | unique row identifier |
| `country_resid` | string | ABS country-of-residence code |
| `target_year`, `target_month_num` | int | calendar year and month of the target month M+1 |
| `target_month` | date | first day of M+1 (time column) |
| `val_m` | int | arrivals in month M |
| `val_m1`, `val_m2`, `val_m3`, `val_m6`, `val_m12` | int | arrivals 1, 2, 3, 6 and 12 months before M |
| `diff_mom` | int | val_m - val_m1 |
| `diff_quarter` | int | val_m - val_m3 |
| `diff_half` | int | val_m - val_m6 |
| `diff_yoy_m` | int | val_m - val_m12 |
| `fell_short` | int | label: 1 when arrivals in M+1 are below arrivals in the same month a year earlier |

All features are published at or before the instant (the OAD release for month M). The target month
is used only to compute the label.
