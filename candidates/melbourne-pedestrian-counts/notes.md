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

## Licence - unconfirmed, and now checked exhaustively

Re-checked on 2026-09-18 through every channel that should carry a licence. **None
declares one.**

| Channel | Result |
|---|---|
| `GET /api/explore/v2.1/catalog/datasets/pedestrian-counting-system-monthly-counts-per-hour` | no `license` / `licence` / `terms` key, and none inside `metas` either |
| Dataset information page HTML | no licence text node, no `creativecommons.org` link; the only `license` occurrences are OpenDataSoft feature flags |
| DataVic CKAN harvest (search "pedestrian counting system monthly counts per hour", 3 matches) | `licence_id: "other-open"`, `license_title: "other-open"`, `license_url: null` for all three Pedestrian Counting System datasets |
| `https://data.melbourne.vic.gov.au/pages/terms-of-use/` and `/pages/terms/` | HTTP 404 |
| `https://www.melbourne.vic.gov.au/open-data` | HTTP 403 from this host |

The City of Melbourne commonly publishes under CC BY 4.0, but that is an assumption
and is recorded here as one. `other-open` names no terms and is not a publishable
licence. **Do not make a release claim for this candidate until a licence is actually
read.** The next step is a decision from the operator or the Council's open-data policy
page reached through a channel that is not blocked from this host.

## Split trap

A per-sensor quantile threshold computed over the whole series leaks holdout
information into the label definition. Compute thresholds from the training window
only and freeze them.

## Next action

Confirm the licence, explain the 2025 record jump, then measure per-sensor hourly
distributions.

## Parking verdict (2026-09-19)

Status set to `parked`. Every channel re-checked on 2026-09-18 declares no licence; a name commonly assumed is not evidence. The four contracts are met except redistribution, so the blocker is a decision rather than work.
