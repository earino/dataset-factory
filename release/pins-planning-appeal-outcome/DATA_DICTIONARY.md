# Data dictionary - pins-planning-appeal-outcome

One row per decided s78_core planning-permission-family appeal (publisher casework
type matching the s78_core family, e.g. `Planning Appeal`, `Householder (HAS)`) with
a binary decision, validated by the Planning Inspectorate between 2012-06-01 and
2026-08-21. 139,264 scored rows from 145,133 s78_core rows: 2,757 non-binary
decisions, 3,110 cross-file composite duplicates (2021 decisions appear in both
publisher files; deduplicated on (type, LPA, received, valid, decision date,
decision)) and 2 decided-before-validation rows are excluded and counted, never
silently dropped. Source: the 2026-10-22 edition of the Planning Inspectorate
Casework Database, two bulk Excel extracts with ~40 documented fields carrying
per-field data-quality grades. Splits: train 54,834 (validated before 2020-01-01) /
eval 28,104 (2020-2021) / holdout 56,326 (on or after 2022-01-01).

All publisher-sourced columns are **current-snapshot vintage**: values are as
published in the pinned 2026-10-22 edition, documented by the publisher with a
per-field data-quality grade and recorded at submission/registration (an
administrative record written at the event). The publisher revises the rolling
database between editions, so no historical vintage is claimed.

## Identifier

| Column | Type | Meaning |
| --- | --- | --- |
| `row_id` | string (id) | `<file>:<reference number>` (Case Number in the 5-year file, Older Casework Data Ref No in the older file). Unique across the panel, asserted at construction. Declared high-cardinality identifier by the gate, not a leak. |

## Features recorded at registration (the appeal's own record)

| Column | Type | Meaning |
| --- | --- | --- |
| `lpa_name` | string | The local planning authority whose decision is appealed (publisher LPA Name; 376-379 distinct LPAs). Also the clustering unit for the reported intervals. |
| `ons_lpa_code` | string | The publisher's ONS code for the same authority. |
| `casework_type` | string | Publisher Type of Casework, restricted to the s78_core planning-permission family that defines eligibility. |
| `procedure` | string (4 levels) | The appeal procedure: Written Representations (132,629), Hearing (4,675), Inquiry (1,945), Written representation Part 1 (15). The strongest single simple reference (train-fitted positive rate per procedure scores eval AUC 0.5551). |
| `development_type` | string (20 levels) | Publisher development-type classification of the appealed proposal (e.g. Householder developments 47,757; Minor Dwellings 45,991; Change of use 15,824). Populated on 139,212 rows. |
| `appeal_type_reason` | string (21 levels) | Publisher appeal-type reason code recorded at registration (e.g. `1. Refused planning permission` 113,260; `3. Refused prior approval of permitted development rights` 6,681; `8. Failure to decide in time` 5,288). Populated on 131,616 rows. |
| `appeal_reason` | string (9 levels) | Publisher appeal-reason summary (e.g. Refusal 120,046; Failure 5,364; Appeal Against Conditions 5,178). Populated on 138,898 rows. |
| `type_detail` | string (9 levels) | Publisher casework-type detail. |
| `link_status` | string (4 levels) | Publisher linked-case role recorded at registration; the Lead Case number itself is NOT shipped (a joinable cross-row id, excluded by design). Populated on 131,618 rows. |
| `valid_date` | date (YYYY-MM-DD) | The publisher's Valid Date - **the prediction instant of this task** (event_time). Carried as a feature and used for split membership. |
| `valid_year` | integer | Calendar year of `valid_date` (derived). |
| `valid_day_of_year` | integer | Day-of-year of `valid_date` (derived; cyclical timing within the year). |
| `received_date` | date | The publisher's Received Date (when PINS received the appeal). |
| `received_to_valid_days` | integer | `valid_date` minus `received_date`, in days (derived; within 30 days for 85.9% of measured cases). |
| `area_of_site_hectares` | float | Site area of the appealed development in hectares (publisher field, recorded at registration where known). |
| `floor_space_sqm` | float | Floorspace in square metres (publisher field, where known). The publisher's literal prose values (e.g. `Under 200 sq m floorspace`, 6 eval rows) map to missing. |
| `number_of_residences` | integer | Number of dwellings in the appealed proposal (publisher field, where known). |
| `green_belt` | binary flag | Site designation recorded at registration (populated on 138,979 rows; blank where the publisher does not state it). |
| `agricultural_holding` | binary flag | As above (populated on 125,477 rows). |
| `listed_building_setting` | binary flag | As above (populated on 16,126 rows). |
| `historic_building_grant` | binary flag | As above (populated on 6,411 rows). |
| `conservation_area` | binary flag | As above (populated on 11,529 rows). |
| `flooding_issue` | binary flag | As above (populated on 6,812 rows). |
| `aonb` | binary flag | Area of Outstanding Natural Beauty designation (populated on 13,204 rows). |
| `sssi` | binary flag | Site of Special Scientific Interest designation (populated on 6,673 rows). |

## LPA prior-outcome history (computed from strictly-earlier decisions)

These five columns carry the declared cross-row exposure: they are aggregates over
other rows' labels. Honest evaluation requires isolated rows (see
`quality.json`'s `evaluation_contract`); the shipped illustrative runner does not
enforce that.

| Column | Type | Meaning |
| --- | --- | --- |
| `lpa_decisions_prior_count` | integer | Count of the same LPA's decided s78_core cases with Decision Date strictly earlier than this row's `valid_date` (enforced in construction with a brute-force sample assertion). |
| `lpa_allowed_prior_count` | integer | Allowed decisions among them. |
| `lpa_allow_rate_prior` | float | Allowed share among them; `-1.0` sentinel when the count is zero (disambiguated by `lpa_decisions_prior_count`). The artifact's own shipped rate feature: as a scored reference it reaches eval AUC 0.5422. |
| `lpa_last_outcome` | integer | `-1` when the LPA has no decided prior case, else 1/0 for the most recent prior decision being Allowed/Dismissed. Same-day decisions break ties by validation date then row_id (deterministic total order, asserted by brute-force sample). This is the persistence feature (previous same-LPA outcome; as a scored reference eval AUC 0.5045). |
| `lpa_days_since_prev_case_valid` | integer | Days since the same LPA's previous shipped case was validated (0 when there is none). |

## Target

| Column | Type | Meaning |
| --- | --- | --- |
| `allowed` | integer (0/1) | 1 iff the publisher's Decision field is `Allowed`; 0 iff `Dismissed`. The Decision field and its Decision Date do not ship in any split (`label_source_columns`). Eval base rate 30.13% (8,469 of 28,104). |

## Columns deliberately not shipped

| Source field | Reason |
| --- | --- |
| `Decision Date` | The outcome's date - post-instant; also the reason the split key is the validation instant, not the decision year. |
| `Inspector Name` | Allocation happens after validation, and the publisher warns per-inspector outcome patterns are allocation artefacts; corrected for data errors in 2025. |
| `Start Date`, `Jurisdiction`, recovery/call-in dates, `Redetermined`, `Bespoke` | Mutable or set after the validation instant (post-hoc). |
| `Costs Applied for Indicator` | Post-instant (costs are decided with or after the outcome). |
| `Lead Case` (link number) | A joinable cross-row identifier. |
| `LPA Decision Date`, `LPA Application Reference` | Absent from the older publisher file; not uniformly derivable. |
| Enforcement-grounds count | Measured 0 populated values in the eligible population. |
| Applicant / agent identity fields | Free-text personal data, excluded by design (OGL-UK exempts personal data). |
