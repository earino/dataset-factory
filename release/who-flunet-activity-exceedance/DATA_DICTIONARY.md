# Data dictionary

One row per (country, prediction week W). The label comes from week W+4; every feature comes from
weeks <= W.

## Identity and time

| Column | Type | Meaning |
| --- | --- | --- |
| `row_id` | string | Identifier of the prediction week: `<ISO2>-<iso_year>W<iso_week>`; unique in the artifact (0 duplicate values measured at build) |
| `week_start` | date | Monday of prediction week W (the time column) |
| `country_year` | string | `<ISO2>-<ISO year of the target week W+4>` - the clustered-event key: positives arrive in country-seasons, so uncertainty is quoted against distinct country-years, not rows |

## Target

| Column | Type | Meaning |
| --- | --- | --- |
| `exceeds` | int | **Target.** 1 iff week W+4 positivity `INF_ALL/(INF_ALL+INF_NEGATIVE)` is strictly greater than `0.10`, with denominator >= 50 and systematic negative reporting in the target country-year |

`positive_label` is `1`. The label source columns (`INF_ALL`, `INF_NEGATIVE` for week W+4, and the
rate derived from them) are **not shipped**: only the binary label is written.

## Country metadata (publisher's static fields, known at W)

| Column | Type | Meaning |
| --- | --- | --- |
| `iso2` | string | Country/territory ISO 3166-1 alpha-2 code (publisher's field) |
| `whoregion` | string | WHO region |
| `hemisphere` | string | Hemisphere |
| `itz` | string | Influenza transmission zone |

## Calendar position of the prediction week

| Column | Type | Meaning |
| --- | --- | --- |
| `iso_year` | int | ISO year of week W |
| `iso_week` | int | ISO week number of week W |

## Counts of week W (ORIGIN_SOURCE streams summed)

| Column | Type | Meaning |
| --- | --- | --- |
| `specimens_w` | int | `SPEC_PROCESSED_NB`: specimens processed in week W |
| `inf_a_w`, `inf_b_w` | int | Influenza A / B detections in week W |
| `inf_all_w` | int | Total influenza detections in week W |
| `inf_negative_w` | int | Specimens negative for influenza in week W |
| `denom_w` | int | `inf_all_w + inf_negative_w` (guaranteed >= 50 for a shipped row) |
| `positivity_w` | float | `inf_all_w / denom_w` - the week's own positivity |
| `ah1_w`, `ah3_w`, `ah1n12009_w` | int | Influenza A subtype counts (pandemic H1N1 2009, seasonal H1N1, H3N2) |
| `bvic_w`, `byam_w` | int | Influenza B lineage counts (`bvic_w` is the sum of the four `BVIC_*` lineage columns) |
| `adeno_w`, `boca_w`, `human_corona_w`, `metapneumo_w`, `parainfluenza_w`, `rhino_w`, `rsv_w` | int | Non-influenza respiratory virus detections in week W |

## Lags and rolling summaries (all from weeks <= W)

| Column | Type | Meaning |
| --- | --- | --- |
| `lag1_positivity` .. `lag4_positivity` | float | Positivity of week W-1 .. W-4; **-1.0** when that week has no measurable positivity (absent week or no specimens) - a sentinel outside [0,1], not a real rate |
| `lag1_inf_all`, `lag4_inf_all` | int | `INF_ALL` of week W-1 / W-4 (0 when the week is absent) |
| `lag1_inf_a`, `lag1_inf_b`, `lag1_rsv` | int | Influenza A, influenza B and RSV detections of week W-1 (0 when absent) |
| `mean8_positivity`, `max8_positivity` | float | Mean and max weekly positivity over weeks W-7..W, measurable weeks only; -1.0 when none |
| `weeks_above_threshold_8` | int | Count of weeks in W-7..W with positivity > 0.10 |
| `missing_weeks_8` | int | Count of weeks in W-1..W-7 with no measurable positivity |
| `sum4_inf_all` | int | `INF_ALL` summed over W-3..W (absent weeks contribute 0) |

## Frame rules that decide which rows exist

The publisher's table is country x ISO week x `ORIGIN_SOURCE`; this artifact sums the streams. A
candidate row is shipped only when:

1. the prediction week W has `denom_w >= 50` (the feature week is well measured);
2. the target week W+4 exists in the source with denominator >= 50;
3. the target **country-year** reports negatives systematically: at least 4 specimen-bearing weeks
   and at least 50% of them with `INF_NEGATIVE >= 1`. 1,258 of 3,349 country-years qualify.

Rule 3 exists because of a measured trap: before ~2015 most FluNet rows lack `INF_NEGATIVE`, so
positivity computed from them is 100% **by construction**. The 1995-2004 window measures 931/931
country-weeks positive before the rule (the uniform-result signature of a frame error) and 14 rows
after it. Those rows cannot carry the rate frame and are excluded.

Rows skipped by these rules: 106,611 thin prediction week; 6,881 thin target week; 8,015
not-systematic; 755 no target week.

## Splits

Temporal, by the prediction week's ISO year:

| Split | Window (prediction week) | Rows | Positives | Rate | Distinct country-years |
| --- | --- | ---: | ---: | ---: | ---: |
| train | <= 2019-12-30 | 5,779 | 3,420 | 59.2% | 235 |
| eval | 2019-12-30 .. 2023-01-02 | 6,831 | 1,636 | 23.9% | 257 |
| holdout | 2023-01-02 onward | 13,483 | 5,482 | 40.7% | 422 |

The base rate is not stationary: it rises as negative reporting becomes universal and falls during
the COVID-era collapse in influenza circulation (2020-2022). This is documented as a property of
the phenomenon. It is also why a single-year holdout is a bad idea here and the holdout spans
2023-2026.

## Known-event fixture

France, 2024-25 season, measured on the source at build time: peak weekly positivity **0.2379** in
the week of **2025-01-27** over 28 measurable weeks, and July-August off-season weeks at most
**0.0071** (17 weeks). The fixture asserts peak in (0.15, 0.95] and off-season < 0.10, which pins
both the 10% threshold and the four-week lead with margin on both sides. It is asserted on every
build, and its values are in `measurements.json`.