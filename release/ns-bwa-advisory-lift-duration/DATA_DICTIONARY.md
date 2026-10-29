# Data dictionary

One row per issued boil water advisory (labeled). The prediction instant is the
issue date itself; every feature is a value fixed at or before that day.

| Column | Role | Unit / values | Meaning |
| --- | --- | --- | --- |
| `advisory_id` | id (excluded from model input) | `ns<NNNNNN>` | Constructed row identifier: the register row's 1-based position in the pinned CSV (stable per vintage). Unique; never crosses splits. |
| `issue_date` | time column / clustered-event key (carried, excluded from model input by the id/time convention) | ISO calendar date | The prediction instant. Split windows and the per-year reporting key. |
| `site_name` | feature (declared high-cardinality) | register free text, normalised | The supply's name as recorded for the issuing advisory; the history pool key for site features. |
| `county` | feature | Nova Scotia county name, normalised; `unknown` when blank | The county recorded for the issuing advisory (113 rows blank in the source, shipped as `unknown`; never pooled into county history). |
| `facility_type` | feature | registered / municipal / unknown | The facility classification recorded at issuance (57 blank rows shipped as `unknown`). |
| `reason` | feature | register category, normalised; `unknown` when blank | The reason for the report recorded at issuance. Spelling variants merged (e.g. `E. Coli Present` + `E.Coli Present` -> `e. coli present`, 135 rows). |
| `issue_month` | feature | calendar month 1-12 | Month of the instant. |
| `issue_dow` | feature | day of week, 0=Monday..6=Sunday | Weekday of the instant. |
| `site_prior_advisories` | feature | count | Distinct earlier issue dates at the same normalised site, strictly before the instant. |
| `site_days_since_last` | feature | days (integer), -1 when none | Instant minus the most recent earlier same-site issue date. |
| `site_prior_resolved` | feature | count | Earlier same-site advisories whose removal date is strictly before the instant and whose duration is non-negative. |
| `site_prior_lift30_rate` | feature | mean binary label in [0,1], -1 when no resolved prior | Lift30 rate over those resolved priors. **This is the site-persistence reference**: the strongest simple rule on the task (eval AUC 0.6124). |
| `site_active_prior` | feature | binary 0/1 | 1 iff an earlier same-site advisory was still in effect at the instant. |
| `county_prior_advisories` | feature | count | Distinct earlier issue dates in the same county, strictly before the instant; 0 for blank-county rows. |
| `county_days_since_last` | feature | days (integer), -1 when none | Instant minus the most recent earlier same-county issue date. |
| `county_prior_resolved` | feature | count | Earlier same-county advisories resolved strictly before the instant. |
| `county_prior_lift30_rate` | feature | mean binary label in [0,1], -1 when none | Lift30 rate over those resolved priors. |
| `county_active_prior` | feature | binary 0/1 | 1 iff an earlier same-county advisory was still in effect at the instant. |
| `lift30` | **target** | binary 0/1 | 1 iff (removal date - issue date) <= 30 days inclusive, recomputed from the register's two date columns. |

## Label source and censoring

The label is derived from the register's `Date Advisory Removed` and `Length of
Advisory in Days` columns, which are **label-only** and absent from the shipped
files. The publisher documents the censoring semantics on the dataset page:
"Values are not provided for boil advisories that are currently in effect" -
a blank removal date means the advisory was still active at the vintage
(2026-06-16). Such rows are excluded from the scored sets and counted per
window (2 train / 1 eval / 10 holdout; 30 further rows in 2025-2026 cohorts,
mostly still active). Rows whose recomputed duration is negative (3 known
register rows) are excluded as unverified outcomes. Eligibility caps the issue
date at vintage minus 30 days (2026-05-17) so an unresolved recent advisory can
never masquerade as a negative label.

## As-of history semantics

Every `site_*` / `county_*` history feature reads only advisories whose issue
date is **strictly earlier** than the scored row's, and (for the resolved/rate
features) whose removal date is also strictly before the instant. Rows sharing
the same (site, issue date) never contribute to each other's history. This was
spot-verified row by row at construction and enforced by the qualification
gate's timing checks; the gate additionally measured the cross-row exposure the
declared probes describe (a later same-site row's prior-lift-rate equals the
earlier row's label when that prior is its only resolved one).
