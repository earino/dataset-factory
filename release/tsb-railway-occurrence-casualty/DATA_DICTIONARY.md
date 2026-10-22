# Data dictionary - TSB Railway Occurrence Casualty

Grain: one row per TSB rail occurrence, keyed by `occ_no`. Panel 2016-01-01..2026-08-31
(vintage of 2026-10-21). Every source field's meaning was read from the publisher's own
RODSdb data dictionary (RODSdb-dd.csv, 699 rows) before it was allowed to ship; fields
the publisher documents as set during or after the occurrence are excluded and listed at
the bottom.

## Shipped columns

| Column | Meaning (publisher-documented unless derived) | Role | Available at |
| --- | --- | --- | --- |
| `occ_no` | TSB occurrence number, the publisher's unique identifier; non-identical duplicate numbers in the current vintage are suffixed (`-2`, ...) and pinned via `expected_duplicate_ids` (13) | id column | onset (register key) |
| `occ_year` | calendar year of the occurrence date (derived from OccDate) | feature | onset |
| `occ_month` | calendar month (derived from OccDate) | feature | onset |
| `occ_day_of_week` | day of week (derived from OccDate) | feature | onset |
| `occ_hour` | local hour of day at the occurrence site, 0-23 (parsed from OccDate's local time; the DST-aware site timezone ships separately in `timezone`, so no offset map is applied) | feature | onset |
| `timezone` | site timezone as recorded by TSB (TimeZoneID_DisplayEng) | feature | onset |
| `activity_type` | what the train was doing at the time of the occurrence (ActivityTypeID): e.g. main-line train, switching, cut of cars, employee/volunteer passenger train | feature | onset |
| `subdivision` | subdivision name where the occurrence took place (SubdNameID) | feature (high-cardinality free field) | onset |
| `subd_mileage` | miles from the start of the named subdivision (SubdMileage), shipped verbatim; empty when the source records none | feature (high-cardinality free field) | onset |
| `railway` | railway company responsible (SUBD_OWNER_ABBREV / SubdOwnerID) | feature | onset |
| `near_location` | nearest city/town recorded by TSB | feature (high-cardinality free field) | onset |
| `province` | province of the occurrence (ProvinceID) | feature | onset |
| `region` | TSB region of occurrence (RegionOfOccurrence) | feature | onset |
| `latitude` | occurrence latitude in decimal degrees, north positive. The publisher packs coordinates in three magnitude-disjoint encodings (ddmm.ff packed degrees+minutes+hundredths dominant; decimal-degrees x 10^3; x 10^6), measured over 3,088 values with zero ambiguous and zero undecodable; the build decodes and requires exactly one decode inside the Canadian envelope 41-72 N (Ottawa 452500 -> 45 deg 25.00' = 45.4167, exact) | feature (high-cardinality free field) | onset |
| `longitude` | occurrence longitude, east-positive (West negative): same three-encoding decode, envelope 52-145 W, then negated (1181200 -> 118 deg 12.00' -> -118.2, Revelstoke BC) | feature (high-cardinality free field) | onset |
| `occ_date` | occurrence date (OccDate), the split/decision time column | time column (not a model feature; declared high-cardinality) | onset |
| `casualty` | **target.** 1 iff the occurrence resulted in at least one casualty: InjuriesIND == 1 or TotalFatal+TotalSerious+TotalMinor injuries > 0 | label | after onset - never shipped as a feature |

Label source columns (excluded from every shipped file): `InjuriesIND`,
`TotalFatalInjuries`, `TotalSeriousInjuries`, `TotalMinorInjuries`. The label agrees
with the publisher's separate INJURIES child table on all 1,624 positive panel rows
(0 disagreements either way).

## Prediction instant

`event_time`: the instant the occurrence begins (OccDate/OccTime, local time at the
site, timezone documented per row). RODS is an administrative register whose rows are
written at/after the event, so no publication lag applies to the features; the vintage
(last-modified + sha256 of the five source CSVs) is recorded in `meta.json`.

## Excluded by construction (never shipped)

Post-hoc / outcome-embedding fields documented by the publisher as recorded during or
after the occurrence: the accident/incident and occurrence-type taxonomy
(AccIncTypeID*, OccurrenceTypeID*, OccClassID* - TSB's own type names embed outcomes,
e.g. "NON-MAIN-TRACK TRAIN DERAILMENT (NO DAMAGE)"), ReportedDate/ReportedTime (the
notification instant, which post-dates onset), the free-text Summary, train/rolling-stock
counts and derailment flags, Fire/Explosion/Evacuation/DG indicators and counts,
IsolationRadius, NumEvacuated, DeployedIND, process dates (ENTRY_DT, RELEASE_DT,
DAILY_RELEASED_DT, OccClosedDate), and the at-scene weather block (Temperature_Celsius,
WeatherSourceID, Light/Wind/Precipitation/Sky conditions). The full exclusion list is
machine-readable in `quality.json` (`post_hoc_columns`, `label_source_columns`).

## Splits

Temporal by occurrence date - train 2016-01-01..2022-01-01, eval 2022-01-01..2025-01-01,
holdout 2025-01-01..2026-09-01 (data through 2026-08-31, one settling month behind the
vintage). Both classes in every window; positives are independent occurrences
(distinct_events == positives in eval and holdout).
