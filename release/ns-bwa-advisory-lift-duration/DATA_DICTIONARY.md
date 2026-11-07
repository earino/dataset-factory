# Data dictionary

One row per issued boil water advisory (labeled). The prediction instant is the
issue date itself; every feature is a value fixed at or before that day. The
v2026.12 frame is **issuance attributes + issue-date recency only** - no
shipped column is a function of any row's removal date or label.

| Column | Role | Unit / values | Meaning |
| --- | --- | --- | --- |
| `advisory_id` | id (excluded from model input) | `ns<NNNNNN>` | Constructed row identifier: the register row's 1-based position in the pinned CSV (stable per vintage). Unique; never crosses splits. |
| `issue_date` | time column / clustered-event key (carried, excluded from model input by the id/time convention) | ISO calendar date | The prediction instant. Split windows and the per-year reporting key. |
| `site_name` | feature (declared high-cardinality) | register free text, normalised | The supply's name as recorded for the issuing advisory; the recency pool key for site features. |
| `county` | feature | Nova Scotia county name, normalised; `unknown` when blank | The county recorded for the issuing advisory (113 rows blank in the source, shipped as `unknown`; never pooled into county recency). |
| `facility_type` | feature | registered / municipal / unknown | The facility classification recorded at issuance (57 blank rows shipped as `unknown`). |
| `reason` | feature | register category, normalised; `unknown` when blank | The reason for the report recorded at issuance. Spelling variants merged (e.g. `E. Coli Present` + `E.Coli Present` -> `e. coli present`, 135 rows). |
| `issue_month` | feature | calendar month 1-12 | Month of the instant. |
| `issue_dow` | feature | day of week, 0=Monday..6=Sunday | Weekday of the instant. |
| `site_days_since_last` | feature | days (integer), -1 when none | The instant minus the most recent earlier same-site issue date. Reads other rows' **issue dates only**. |
| `county_days_since_last` | feature | days (integer), -1 when none | The instant minus the most recent earlier same-county issue date; 0 for blank-county rows. Reads other rows' **issue dates only**. |
| `lift30` | **target** | binary 0/1 | 1 iff (removal date - issue date) <= 30 days inclusive, recomputed from the register's two date columns. |

Removed in v2026.12 (present in the superseded v2026.10, never in these
files): `site_prior_advisories`, `site_prior_resolved`,
`site_prior_lift30_rate`, `site_active_prior`, `county_prior_advisories`,
`county_prior_resolved`, `county_prior_lift30_rate`, `county_active_prior`.
The independent audit recovered labels exactly from those eight
outcome-derived columns via cumulative-count x rounded-rate arithmetic and
subtraction; the channel is closed by removing them, and the
site-persistence value they carried survives only as a register-side
**reference** in the measured evidence, never as a shipped feature.

## Label source and censoring

The label is derived from the register's `Date Advisory Removed` and `Length of
Advisory in Days` columns, which are **label-only** and absent from the shipped
files (the gate asserts their absence). The publisher documents the censoring
semantics on the dataset page: "Values are not provided for boil advisories
that are currently in effect" - a blank removal date means the advisory was
still active at the vintage (2026-06-16). Such rows are excluded from the
scored sets and counted per window (2 train / 1 eval / 10 holdout; 30 further
rows in 2025-2026 cohorts, mostly still active). Rows whose recomputed
duration is negative (3 known register rows) are excluded as unverified
outcomes. Eligibility caps the issue date at vintage minus 30 days
(2026-05-17) so an unresolved recent advisory can never masquerade as a
negative label.

## As-of recency semantics

The two recency features read only advisories whose issue date is **strictly
earlier** than the scored row's. Rows sharing the same (site, issue date)
never contribute to each other's recency, and neither feature reads any
removal date, duration or label - the register columns those derive from are
not in the shipped files. This was spot-verified row by row at construction,
unit-checked in the pre-launch smoke probe (strictly-earlier-only recency,
same-(site, issue date) isolation, blank-county sentinel, county recency
recomputed independently), and enforced by the qualification gate's timing
checks.
