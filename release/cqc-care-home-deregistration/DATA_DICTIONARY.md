# Data dictionary

Grain: one row per care-home location active on the CQC register at a January
"HSCA Active Locations" vintage instant T (`'Care home?' = Y` in that
vintage's own column, read at T). Identity `location_key` is a per-instant
salted pseudonym `sha256(salt|instant|location_id)[:16]`; no name, address,
postcode, provider identifier, Companies House or charity number ships.

| Column | Unit / domain | Meaning and reference frame |
| --- | --- | --- |
| `location_key` | 16-hex pseudonym | row identifier (id column, not a feature). Salted per instant, so the same physical home at different instants carries different keys by design |
| `instant` | YYYY-MM | the vintage production month, Europe/London (feature). The vintage is the register state AT that instant |
| `care_home_beds` | beds (integer) | the location's registered care-home beds at T, as published in the T vintage; -1 = not stated |
| `beds_bucket` | category | derived bucket of `care_home_beds` (1-9, 10-24, 25-49, 50+; missing kept separate) |
| `latest_overall_rating` | category / -1 | the location's latest overall CQC rating as carried in the T vintage (Inadequate, Requires improvement, Good, Outstanding); -1 = no published rating at T |
| `rating_recency_bucket` | category | derived recency of the rating's publication date relative to T |
| `inherited_rating` | flag | the vintage's inherited-rating flag (rating inherited from a previous registration) |
| `hsca_start_year` | calendar year | the year the location's HSCA registration started; -1 = not stated |
| `local_authority` | category | the location's local authority as published in the vintage |
| `region` | category | the English region as published in the vintage |
| `provider_sector` | category | the provider's sector (e.g. Independent) as published in the vintage |
| `svc_nursing` | flag (0/1/-1) | service-type flag at T: care home service WITH nursing; -1 = column absent in that vintage |
| `svc_residential` | flag (0/1/-1) | service-type flag at T: care home service WITHOUT nursing; -1 = column absent in that vintage |
| `svc_other_count` | count (integer) | other registered service types at T |
| `users_dementia` | flag (0/1/-1) | service user band flag at T; -1 = column absent in that vintage |
| `users_older_people` | flag (0/1/-1) | service user band flag at T; -1 = column absent in that vintage |
| `users_learning_disabilities` | flag (0/1/-1) | service user band flag at T; -1 = column absent in that vintage |
| `users_physical_disability` | flag (0/1/-1) | service user band flag at T; -1 = column absent in that vintage |
| `users_mental_health` | flag (0/1/-1) | service user band flag at T; -1 = column absent in that vintage |
| `users_other_count` | count (integer) | other service user bands at T |
| `deregistered_12m` | 0/1 (target) | 1 when the location's registration ended within (T, T+365d]: Location Status Inactive-Dereg or Removed with a Location HSCA End Date inside the window, joined from the pinned Deactivated Locations edition by real Location ID at construction |

Label source columns (real Location ID, Location HSCA End Date, Location
Status, end-date-adjacent fields) are used at construction only and never
ship; the gate scores every shipped column for single-column separation of the
target (none found; `location_key` is declared high-cardinality).

Known eras that a careful consumer should know: the single-assessment rating
change (~2024, location-level overall ratings for multi-service ASC locations)
and the 1 April 2019 regulatory-history inheritance change both fall inside
the train-to-eval span; the eval instant is the first January vintage after
the rating-configuration change. The publisher's system migration is delaying
reflection of recent registration cancellations in current files, so the
build pins the deactivated edition and measures the lag (max observed end
date 2026-10-27, holdout window end 2026-01-01, margin 299 days).
