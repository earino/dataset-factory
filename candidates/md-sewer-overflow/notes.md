# md-sewer-overflow

**Status: shortlisted. Currency concern RESOLVED 2026-09-18; promoted out of "lower
priority".** The remaining work is the rainfall join and the facility-day event rate.

## The task

Predict whether a Maryland collection system reports a sanitary sewer overflow on
a given day, using rainfall and facility identity as features.

## Measured evidence (2026-09-18, anonymous Socrata API)

### Historical series - `3rgd-zjxx`, "Reported Sewer Overflows"

Endpoint: `https://opendata.maryland.gov/resource/3rgd-zjxx.json`

| Query | Result |
|---|---|
| `$select=count(*)` | 27,479 rows |
| date range | 2005-01-01 to 2023-02-10 |
| licence | Public Domain (view metadata, read directly) |
| fields | overflow_type, municipality_facility, npdes, date_discovered, time_discovered, quantity_in_gallons_estimated, cause, watershed, receiving_waters, county, latitude, longitude |

### Current series - `stgj-u72u`, "Reported Sewer Overflows (New for 2023)"

**This is the concern that is now closed.** An earlier session recorded HTTP 403 from
this host and left the contents unverified. On 2026-09-18 it answers **HTTP 200** for
both the view metadata and the resource, so the series is reachable:

| Query | Result |
|---|---|
| view metadata | name `Reported Sewer Overflows (New for 2023)`, licence **Public Domain**, `rowsUpdatedAt` 1789723444 |
| `rowsUpdatedAt` as a date | **2026-09-18** - the series is actively updated, not historical |
| `$select=count(*)` | 3,434 rows |
| rows per year | 2023: 708 / 2024: 999 / 2025: 1,026 / 2026 to update: 700 / undated: 1 |
| columns | 19 including `start_date`, `facility_collection_system`, `npdes_no`, `duration_*`, `discharge_volume`, `overflow_cause`, `receiving_water`, `county`, `penalty_id`, lat/long |

**Trap worth recording:** this dataset names its date column `start_date`, not
`date_discovered`. Querying it with the historical series' column name returns
`query.soql.no-such-column`, which is easy to misread as "the dataset is empty" - the
mistake the earlier 403 compounded. Use `start_date` for this series.

Top collection systems measured: Patapsco WWTP - Baltimore City 580, Back River WWTP -
Baltimore City 377, John J. DiFonzo (Cumberland) 181, Frostburg 178, Private System 163.

The host sits behind Cloudflare and does return an intermittent 403 on a first
attempt (observed on the very first count query of this session, then 200 on retry).
**Queries against this host must retry.**

## Concerns

1. ~~The series appears to stop in February 2023.~~ **Resolved.** `stgj-u72u` carries
   2023-2026 and was updated the same day. The remaining wrinkle is that the two series
   overlap or abut in 2023 and must be reconciled (deduplicate) before use.
2. **Imbalance.** Event-level regulatory reports at facility-day granularity are
   likely rare; the positive rate must be measured before the protocol is fixed. Still
   unmeasured.
3. **Rainfall join.** NOAA GHCN-Daily or NCEI CDO is the intended feature source. It
   has not been tested from this host.

## Next action

Reconcile the 2023 overlap between the two series, test the NOAA rainfall join, and
measure the facility-day event rate.
