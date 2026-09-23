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

## Discovery session 2026-09-21: the currency question is closed, the target question is not

Probes: `.factory/probe_md_series.py`, `.factory/probe_md_rainfall.py`,
`.factory/probe_md_rainfall2.py`, `.factory/probe_md_rainfall3.py` (all read-only).

### The two series abut; they do not duplicate

Monthly counts from `$select=date_trunc_ym(<datecol>) AS ym, count(*) AS n` on each dataset:

| series | total rows | boundary months |
|---|---|---|
| `3rgd-zjxx` | 27,479 | 2022-12: 122, 2023-01: 30, 2023-02: **7** (ends 2023-02-10) |
| `stgj-u72u` | 3,439 | 2023-01: **1**, 2023-02: 46, 2023-03: 64 ... 2026-09: 39 |

So the historical series runs out in February 2023 and the current one starts in January
2023 with a single row. No month is covered densely by both, so reconciling them is a
boundary trim rather than a de-duplication. The current series has grown by 5 rows since
2026-09-18 (3,434 -> 3,439), which is the second independent confirmation that it is live.

Row-level confirmation is **not** done: the two `$where <datecol> between '...' and '...'`
range queries failed against **both** datasets with HTTP 403 on every attempt (five on the
first run - whose traceback arrived after the session had already written up; four on the
second). The same runs' `$select`/`$group` queries all succeeded, so the refusal tracks the
quoted-literal `$where` URL shape rather than the host being down. Retry with an unquoted
range form, or page with `$limit`/`$order`, before concluding anything about the series.

### The rainfall join is feasible without a token

`https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/<ID>.csv`
answers HTTP 200 with PRCP fully populated - three station files fetched (2.4-4.5 MB each)
carry usable PRCP on 877/1055, 1291/1296 and 1242/1266 days since 2023-01-01. The CDO API v2
returns HTTP 400 without a token, so the access-CSV path is the one to use.
`ghcnd-stations.txt` (11,395,258 bytes, 132,503 lines) and `ghcnd-inventory.txt` are both
fetchable anonymously; the inventory carries per-element first/last year, which is the
recency filter the station list lacks.

**Not measured:** the Maryland active-station count. The station-id filter read the wrong
column of `ghcnd-stations.txt`, so the 6,873 in `probe_md_rainfall_result3.json` is a
US-wide count and not a Maryland figure. It must not be quoted as one.

### Why the candidate is parked, not ready

Contracts 1 (redistribution: Public Domain, read directly from both view endpoints), 2
(prediction instant: start of the target day; rainfall and facility identity are the features,
the report's own outcome fields are excluded) and 4 (positives exist in both series across
2005-2026) look satisfiable. Contract 3 does not, yet: **only facilities that reported ever
appear**, so a facility-day grid built from these tables alone has a survivorship-biased
negative class, and no Maryland collection-system registry has been identified or tested.
The novelty check has not been run either. Hence `parked` with the blocker named, rather than
a construction spent on a denominator that may not exist.

## Next action

Parked 2026-09-21 with the blocker in `record.json.parked_reason`. What is left, in order:

1. Test whether a Maryland collection-system registry is obtainable (MDE open data catalog,
   or EPA ICIS-NPDES / ECHO facility file). That is the blocker for the target contract -
   without a denominator of facilities the negative class is survivorship-biased.
2. Redo the 2023 boundary reconciliation with the working `date_trunc_ym` form (the
   `between` range queries failed on 2026-09-21).
3. Run `scripts/check-novelty.py` for "sanitary sewer overflow" / "combined sewer
   overflow prediction" - no verdict is recorded yet.

If (1) fails, drop the candidate rather than constructing the biased denominator.

Pre-session next action, kept as the record of that state: "Reconcile the 2023 overlap
between the two series, test the NOAA rainfall join, and measure the facility-day event
rate." The rainfall join is now tested (above); the other two carry forward.

## Discovery session 2026-09-23: the registry blocker is answered, and the rosters are partial

Probes: `.factory/probe_md_registry.py`, `_2.py`, `_3.py`, `_4.py`, `_5.py`, `_6.py`
(all read-only; results in `.factory/probe_md_registry*_result.json`). No worker, no credentials,
no bulk download - the EPA zip was inspected by byte-range reads only.

### A facility roster that is independent of the reports exists

| source | measured 2026-09-23 | covers |
|---|---|---|
| EPA `npdes_downloads.zip` (`ICIS_FACILITIES.csv`) | 352,268,538 bytes, anonymous, `Range: bytes=...` -> **206**, 15 zip members; member 193,927,778 bytes uncompressed | all NPDES permit holders, filterable by `STATE_CODE=MD`; fields documented on EPA's ICIS-NPDES download summary (NPDES_ID, FACILITY_TYPE_CODE, lat/long) |
| MDE `2h5v-duyx` / `ct9h-nxwr` "Significant Wastewater Treatment Plants" | 76 rows, 76 distinct `npdes_id`, all `Major`, type POTW/FEDERAL | **40** of the 322 reporting NPDES IDs; 36 roster facilities never report in either series |
| MDE `wdtu-5pbn` / `rwxr-95kt` "Point Source Discharges" | 863 rows, 829 distinct `npdesid`, categories incl. 184 Waste Water Treatment Plant, 63 Publically Owned Treatment Waste Water, 2 Combined Sewer Overflow, 39 Stormwater Discharge | **129** of the 322 reporting NPDES IDs |

So the survivorship concern is answered in principle (an external roster exists) but not yet in
coverage: **no Maryland-side dataset is exhaustive**, and the EPA file's coverage of the 322
reporting IDs can only be measured by pulling it (336 MB - worker work, not coordinator work).

### Keys and counts measured from the reports

- distinct NPDES keys: `3rgd-zjxx` **126**, `stgj-u72u` **247**, union **322**.
- reports attributable to the 76-facility major-POTW roster: **907** (old series) + **117** (new) =
  **1,024**, counted with `$where npdes in('MD...')`.
- Column names differ per dataset - `npdes`, `npdes_no`, `npdes_id`, `npdesid`. A wrong name returns
  `query.soql.no-such-column`, which reads like an empty dataset. This is the trap that compounded
  the earlier 403s.
- **The earlier 403s are explained**: `$where <col> in('...')` is accepted; the quoted-literal
  `$where <date> between '...' and '...'` form is what returned HTTP 403. So the 2023 row-level
  reconciliation is a retry with the working form, not a blocked route.

### The label is "reported", which changes what the denominator has to be

The prediction question is whether an overflow is **reported** on a facility-day. Under-reporting is
therefore part of the target, not label noise: what the grid needs is an entity roster that is not
derived from the reports themselves. That is why the roster - not a discharge measurement - is the
thing this probe was for.

### Novelty check recorded

`python3 scripts/check-novelty.py md-sewer-overflow --query ... --verdict differentiated` ->
`ok: true`, verdict **differentiated** at 2026-09-23T08:08:06+00:00. Prior art is modelling from
internal telemetry (DeepCSO), pipe-defect datasets (Sewer-ML) and loose GitHub code
(tbep-tech/sso-dash, HamedGhodsi90/CSO_Real-Time_Prediction, AlexLipp/cso_scaling); nothing ships
this facility-day task with splits. Hugging Face datasets: 0 hits for "sanitary sewer overflow" and
"combined sewer overflow prediction".

### Still parked, with the blocker narrowed

Not `ready`: the roster's coverage of the 322 reporting IDs is unmeasured, and split windows and
base rates are unmeasured. Not `dropped` either - the roster route is real and now measured.
