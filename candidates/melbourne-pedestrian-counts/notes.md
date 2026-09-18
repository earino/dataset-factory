# melbourne-pedestrian-counts

**Status: shortlisted; licence unconfirmed (2026-09-18).**

## The task

Predict whether a sensor's hourly pedestrian count exceeds a per-sensor
high-traffic threshold set from the training window.

## Measured evidence (2026-09-18, anonymous OpenDataSoft v2.1 API)

| Query | Result |
|---|---|
| `.../records?limit=2` | `total_count` 1,621,901 |
| portal year filter | 2024: 223,972 / 2025: 815,447 / 2026: 582,482 |
| sample record | `{id, location_id: 37, sensing_date: 2025-07-17, hourday: 14, direction_1: 97, direction_2: 113, pedestriancount: 210, sensor_name: "Lyg260_T", location: {lon, lat}}` |
| fields | id, location_id, sensing_date, hourday, direction_1, direction_2, pedestriancount, sensor_name, location |

The 2025 jump to 815,447 records is a sensor-count change, not necessarily a
footfall change; it must be understood before any cross-year comparison.

## Licence - unconfirmed

Neither the dataset information page nor the v2.1 metadata endpoint exposed a
licence field. The City of Melbourne portal commonly publishes under CC BY 4.0, but
that is not evidence for this dataset. Verify on the dataset page's licence section
before any release claim.

## Split trap

A per-sensor quantile threshold computed over the whole series leaks holdout
information into the label definition. Compute thresholds from the training window
only and freeze them.

## Next action

Confirm the licence, explain the 2025 record jump, then measure per-sensor hourly
distributions.
