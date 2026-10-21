# Data dictionary

One row per (provider, target month M+1). The label comes from month M+1's source row only; every
feature, and every eligibility test, uses provider months <= M. The prediction instant is the
**publication** of month M's monthly CSV, about ten days after month M ends (observed: August 2026
data published 2026-09-10), not the period end.

## Identity and time

| Column | Type | Meaning |
| --- | --- | --- |
| `row_id` | string | `<Org Code>-<YYYY-MM>` of the target month M+1; unique in the artifact (0 duplicate values measured at build) |
| `target_month` | string | `YYYY-MM` of the target month M+1 - the time column; the prediction instant is the **publication** of month M's CSV, taken as 21 days after month M ends (a bound above every observed lag of 9-16 days) |
| `org_code` | string | Publisher's Org Code - the event key: positives cluster within providers, so scores are quoted against distinct positive providers per window |
| `parent_org` | string | Publisher's Parent Org (NHS England region), categorical |
| `target_year` | int | Calendar year of the target month (knowable at the prediction instant) |
| `target_month_num` | int | Calendar month number 1-12 of the target month |

## Target

| Column | Type | Meaning |
| --- | --- | --- |
| `declines` | int | **Target.** 1 iff `within4h_rate(M+1) < within4h_rate(M)`, where `within4h_rate(Y) = 1 - Attendances over 4hrs Type 1 / A&E attendances Type 1` for that provider-month |

`positive_label` is `1`. The label source columns (month M+1's `A&E attendances Type 1` and
`Attendances over 4hrs Type 1`) are **not shipped as columns**: only the binary label is written.
Consecutive months mean those counts can be recovered by joining a row to the next for the same
provider - documented here rather than assumed away. Month M's
own attendances and over-4-hour counts ARE knowable at the prediction instant and ship as
features.

A relative month-over-month change is used because fixed standard thresholds measured
near-uniform positive rates in recent years: <95% -> 99.9% of holdout provider-months positive,
<80% -> 95.8%. The national four-hour rate moved from ~83% (2018) to ~60% (2026 YTD), so the
base rate of a threshold label is non-stationary with the system's own deterioration. The m/m
direction label is threshold-free and balanced in every window.

## The within-4-hour rate and its history (all from months <= M)

| Column | Type | Meaning |
| --- | --- | --- |
| `rate_m` | float | Type 1 within-4h rate of month M: `1 - over4_1_m / att1_m` (proportion) |
| `rate_m1`, `rate_m2`, `rate_m3`, `rate_m6`, `rate_m12` | float | Rate of months M-1 / M-2 / M-3 / M-6 / M-12; **-1.0** when that month is absent from the provider's panel (a sentinel outside the [0,1] rate range, not a real rate) |
| `rate_mean_6m` | float | Mean of the available rates over M-5..M |
| `rate_min_6m`, `rate_max_6m` | float | Min / max of the available rates over M-5..M |
| `rate_delta_1m`, `rate_delta_2m`, `rate_delta_3m`, `rate_delta_6m` | float | `rate_m` minus the lagged rate; **-2.0** sentinel when the lag month is absent (real deltas lie in [-1, 1]) |

## Month M activity and pressure (published with month M's CSV)

| Column | Type | Meaning |
| --- | --- | --- |
| `att1_m`, `att2_m`, `att_other_m` | int | A&E attendances in month M: Type 1 (consultant-led), Type 2, other departments. `att1_m >= 100` by the volume gate |
| `over4_1_m`, `over4_2_m`, `over4_other_m` | int | Attendances over 4 hours in month M by department type |
| `dta_4_12_m`, `dta_12p_m` | int | Patients waiting 4-12h / 12h+ from decision-to-admit to admission, month M |
| `emadm_1_m`, `emadm_2_m`, `emadm_other_m`, `emadm_other2_m` | int | Emergency admissions in month M: via A&E Type 1, via A&E Type 2, via other A&E departments, other emergency admissions |
| `emadm_share_m` | float | `emadm_1_m / att1_m` - admissions per Type 1 attendance |
| `att1_delta_1m`, `att1_delta_12m` | float | `att1_m - att1_m1` / `att1_m - att1_m12`; **-99999.0** sentinel when the lag month is absent |
| `att1_mean_6m` | float | Mean of the available `att1` over M-5..M; -1.0 sentinel |
| `months_reported_12m` | int | Count of months present in the provider's panel over M-11..M (0-12) |

## Frame rules that decide which rows exist

1. **Volume gate.** A provider-month is eligible when Type 1 attendances >= 100 in month M. The
   target month is not gated: it supplies the label and never decides whether a row exists. The
   feature month M and the target month M+1, and the provider has >= 24 such qualifying months.
   Measured on the 2026-10-21 vintage: 142 candidate providers, 12,835 qualifying provider-months,
   129 providers shipping at least one row.
2. **Consecutive pair.** A row needs the target month M+1 to follow the feature month M in the
   panel (3,152 provider-months are skipped for fewer than 24 months of history; 134 have no
   excluded from the splits).
3. **Revisions.** NHS England republishes recent months as "...revised..." CSVs; duplicate
   (org, month) keys keep the copy from the latest upload (deterministic from the filename
   datestamp). On this vintage no duplicate keys exist - each month is published in exactly one
   file - and the build reports the deduplicated-key count as 0.
4. **Schema evolution.** 2018-04..2020-07 files carry 16 data columns (some prefixed "Number
   of...", normalised at load); booked-appointment columns appear from 2020-08; files from
   2024-09 carry trailing unnamed padding columns. The booked-appointment columns are parsed
   but NOT shipped: they do not exist for feature months 2018-12..2020-07, so their availability
   would be split-dependent - a prediction-timing defect wearing a feature-list costume.

## Timing and leakage self-checks (from the build)

- **Truncation self-check:** 204 rows recomputed against a panel copy physically truncated at
  month M - **0 mismatches**. Any accidental future-month access would fail this check.
- **Duplicate row_ids:** 0 across all three splits.
- **Publisher cross-check:** the panel's August 2026 volume-gated Type 1 within-4h rate is
  60.86% against the publisher's own commentary figure of 61.1% (revised-vs-provisional
  publication states); the by-year national series (83.0% in 2018 falling to ~60% in 2025-26)
  is recorded in `measurements.json`.
