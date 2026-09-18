# md-sewer-overflow

**Status: shortlisted, lower priority; series may be stale (2026-09-18).**

## The task

Predict whether a Maryland collection system reports a sanitary sewer overflow on
a given day, using rainfall and facility identity as features.

## Measured evidence (2026-09-18, anonymous Socrata API)

Endpoint: `https://opendata.maryland.gov/resource/3rgd-zjxx.json`

| Query | Result |
|---|---|
| `$select=count(*)` | 27,479 rows |
| date range | 2005-01-01 to 2023-02-10 |
| fields | overflow_type, municipality_facility, npdes, date_discovered, time_discovered, quantity_in_gallons_estimated, cause, watershed, receiving_waters, county, latitude, longitude |

## Concerns

1. **The series appears to stop in February 2023.** A "new for 2023" dataset
   (`stgj-u72u`) exists in the Maryland catalog, but its REST endpoint returned
   HTTP 403 from this host, so its contents are unverified. If the current series is
   not reachable, the task is historical-only, which weakens the "fresh" requirement.
2. **Imbalance.** Event-level regulatory reports at facility-day granularity are
   likely rare; the positive rate must be measured before the protocol is fixed.
3. **Rainfall join.** NOAA GHCN-Daily or NCEI CDO is the intended feature source. It
   has not been tested from this host.

## Next action

Verify the 2023+ dataset, test the rainfall join, and measure the facility-day
event rate. Lower priority than `austin-911-response` and
`chicago-doah-adjudication`.
