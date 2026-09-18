# noaa-tide-flooding

**Status: shortlisted. Per-station exceedance base rates now MEASURED (2026-09-18).**
The task is viable but rare-event: the NOS minor threshold is exceeded on roughly 0-5% of
station-days depending on station.

## The task

Predict whether a station's daily maximum observed water level exceeds its published
minor flood threshold tomorrow.

## Measured evidence (2026-09-18, anonymous CO-OPS APIs)

| Query | Result |
|---|---|
| `mdapi/prod/webapi/stations.json?type=waterlevels` | 302 water-level stations |
| same, `expand=floodlevels` | all 302 carry flood thresholds |
| Boston 8443970 flood levels | nos_minor 15.85, nos_moderate 16.73, nos_major 18.04, nws_minor 16.03 |
| 6-minute water level, Boston, 2026-09-01 | 240 rows, `q=p` preliminary |
| hourly water level, Boston, 2025 | 8,760 rows, one request per station-year |

Retrieval limits matter: 6-minute data is limited to one month per request, hourly data
to 200 years. A multi-year 6-minute backfill is therefore many requests, which is
exactly the kind of work that belongs on a worker. One station-year of hourly data is a
single ~8,760-row request, so base-rate work does not.

## Datum trap - this cost a whole measurement pass, record it

**The published `nos_minor` threshold is in the station datum (STND), not MLLW.** The
CO-OPS metadata API returns the thresholds with no datum field, and nothing in the
response says which one it is.

Comparing `hourly_height&datum=MLLW` against `nos_minor` gives **zero exceedance at all
12 sampled stations across 4,380 station-days** - a result that looks like "this task has
no positive class" and is entirely wrong. The check that exposes it is a known event:

```
Boston 8443970, nos_minor 15.85, 2018-01-03..2018-01-05
  datum=MLLW  peak 15.022 ft at 2018-01-04 18:00  -> exceeds nos_minor: False
  datum=STND  peak 18.547 ft at 2018-01-04 18:00  -> exceeds nos_minor: True
```

The 2018-01-04 bomb-cyclone tide is Boston's documented record. Under MLLW the
comparison denies flooding during the record storm, which is impossible. **Use
`datum=STND`.** The same Boston year reads peak 12.374 ft MLLW versus 15.899 ft STND.

An equivalent trap applies to the CO-OPS flood-status product: its own documentation
states the datum defaults to STND for the daily flood count. NOAA's
`dpapi/prod/webapi/htb.json` was tried as an authoritative shortcut and returned
`count: 0` with an empty `floodLikelihood` list for every station, date and range tried
(including Boston 2018 and range values 7, 31, 365, 366), so it could not be used from
this host.

## Per-station exceedance base rates, station-year 2025

Method: one `hourly_height` request per station for 2025-01-01..2025-12-31 at
`datum=STND`, `units=english`, daily maximum from the hourly rows, compared to
`nos_minor`. Hourly rows are streamed and discarded; only daily maxima are retained.

| Station | ID | nos_minor (ft) | Days | Minor-flood days | Rate | Annual max (ft) |
|---|---|---|---|---|---|---|
| Portland, ME | 8418150 | 20.50 | 365 | 0 | 0.0000 | 20.489 |
| Boston, MA | 8443970 | 15.85 | 365 | 2 | 0.0055 | 15.899 |
| The Battery, NY | 8518750 | 10.19 | 365 | 7 | 0.0192 | 10.942 |
| Sandy Hook, NJ | 8531680 | 9.59 | 365 | 7 | 0.0192 | 10.144 |
| Atlantic City, NJ | 8534720 | 11.38 | 365 | 4 | 0.0110 | 11.755 |
| Sewells Point, VA | 8638610 | 8.89 | 365 | 17 | 0.0466 | 10.522 |
| Charleston, SC | 8665530 | 10.40 | 365 | 7 | 0.0192 | 11.083 |
| Key West, FL | 8724580 | 8.08 | 365 | 0 | 0.0000 | 8.035 |
| Galveston Pier 21, TX | 8771450 | 7.49 | 365 | 4 | 0.0110 | 7.956 |
| San Francisco, CA | 9414290 | 13.69 | 365 | 0 | 0.0000 | 13.497 |
| Seattle, WA | 9447130 | 21.39 | 365 | 0 | 0.0000 | 21.375 |
| Honolulu, HI | 1612340 | 6.71 | 365 | 12 | 0.0329 | 6.965 |

Pooled: **60 minor-flood days across 4,380 station-days, 1.37%**. Per-station rates span
0.00% to 4.66%.

Two things to read carefully in that table:

1. **Several annual maxima sit just under the threshold** - Portland 20.489 vs 20.50,
   Key West 8.035 vs 8.08, San Francisco 13.497 vs 13.69, Seattle 21.375 vs 21.39. That
   is a coherent pattern rather than noise, and it means these stations' 2025 rates are
   sensitive to a residual sub-0.2 ft offset. The pooled rate is a defensible estimate;
   any single near-zero station could move by a day or two.
2. **The class is rare.** At the NOS minor threshold a station-day positive rate near
   1-5% makes accuracy meaningless and demands precision/recall-style metrics and an
   explicit base-rate baseline. A per-station threshold set from the training window (for
   example a high quantile of that station's own daily maxima) would be a better-balanced
   target than the regulatory threshold, and is the honest way to keep headroom.

## Leakage discipline

NOAA publishes tide predictions and model guidance for the same stations
(`product=tide_predications`, `product=ofs_water_level`). Those are model output.
Including them turns the task into "reproduce NOAA's model" and inflates scores.
Observation-only features are the defensible version. Note that the 2025 daily maxima
above are *observed* values, which is what a label should be built from.

## Cross-check against NOAA's own product - VALIDATED (2026-09-18)

The reconstruction above is not self-reported. NOAA publishes its own flood determination in
the High Tide Flooding products, and for station-year 2025 **my `datum=STND` reconstruction
matches NOAA's authoritative `minCount` at 12 of 12 stations: 60 flood days against NOAA's
60.** The rejected `datum=MLLW` reconstruction produced 0.

```
station                  id        NOAA min  mine STND  match
Portland, ME             8418150          0          0   True
Boston, MA               8443970          2          2   True
The Battery, NY          8518750          7          7   True
Sandy Hook, NJ           8531680          7          7   True
Atlantic City, NJ        8534720          4          4   True
Sewells Point, VA        8638610         17         17   True
Charleston, SC           8665530          7          7   True
Key West, FL             8724580          0          0   True
Galveston Pier 21, TX    8771450          4          4   True
San Francisco, CA        9414290          0          0   True
Seattle, WA              9447130          0          0   True
Honolulu, HI             1612340         12         12   True
TOTAL                                    60         60   True
```

Endpoint: `dpapi/prod/webapi/htf/htf_annual.json?station=<id>` returns, per year,
`minCount` / `modCount` / `majCount`. `dpapi/prod/webapi/htf/htf_daily.json?station=<id>&
start_date=YYYYMMDD&end_date=YYYYMMDD` returns per-day rows.

**Two traps in that API, both recorded:** `htf/daily.json`'s `count` field is the number of
**days returned** (365), not a flood count - reading it as one makes every station look like
it flooded every day of the year. And the per-day field is `day` in `MM/DD/YYYY` form with a
`minFlag`, not a `date`/`minorFlood` pair. Only `htf/annual.json` gives counts.

Sewells Point had 3 moderate-or-worse days in 2025; every other station-year in the set had
none at a higher threshold.

## Does hourly sampling miss brief exceedances? Yes, occasionally

The base rates came from the hourly product because it allows long ranges. The 6-minute
product resolves the tide cycle far better but is capped at one month per request. Comparing
daily maxima from both, at the stations and months with the most flood days:

| Station | Month | Flood days | Caught | Missed by hourly | Largest daily-max gap |
|---|---|---|---|---|---|
| Sewells Point, VA | 2025-10 | 9 | 9 | 0 | 0.157 ft |
| Honolulu, HI | 2025-10 | 5 | 4 | **1** (`2025-10-07`) | 0.063 ft |
| The Battery, NY | 2025-08 | 3 | 3 | 0 | 0.285 ft |

**1 day missed out of 17 caught**, so the hourly-derived rate undercounts by roughly 6% of
positive days in the periods examined. The pooled hourly figure **1.37% is therefore a lower
bound**, and label construction should use 6-minute data where the budget allows - which is
worker work, given the one-month-per-request limit.

## Target threshold - kept physical, by decision

**Keep `nos_minor`.** It is a real, externally defined threshold with physical meaning, and
it is now validated against NOAA's own product. Replacing it with a per-station quantile
would invent the event and would not correspond to flooding. The class imbalance is a
property of the phenomenon: document it, report precision/recall-style metrics alongside
AUC, and use the base rate as an explicit baseline. Do not engineer the imbalance away.

## Do the splits have enough positives? Yes on counts, with clustering

Using NOAA's authoritative annual counts (up to 107 years per station):

| Split | Years | Station-days | Positives | Rate | Moderate or worse |
|---|---|---|---|---|---|
| train | 2006-2021 | 70,080 | 1,279 | 0.0183 | 80 |
| eval | 2022-2023 | 8,760 | 234 | 0.0267 | 13 |
| holdout | 2024-2025 | 8,760 | 256 | 0.0292 | 16 |

234 and 256 positives are comfortably enough for a scored claim. **But they are not
independent**: flood days cluster at about two stations each, so

- eval: 234 positive station-days over **118 distinct flood days**
- holdout: 256 positive station-days over **126 distinct flood days**

Confidence intervals on any AUC must be computed over the clustered count, not the row
count. Two further properties to carry into the protocol:

1. **The base rate is not stationary.** Total flood days across the 12 stations rose from 54
   in 2005 to 196 in 2024, and the split rates rise with it (1.83% train -> 2.92% holdout).
   A temporal split therefore has systematic base-rate shift, which is a real feature of the
   phenomenon rather than a construction fault.
2. **Year-to-year variation is large.** 2025 had 60 days against 2024's 196, so any single
   year is a noisy estimate and the holdout should not be a single year.

## Boston event preserved as a regression test

- `datum_regression.json` - the recorded peaks for both datums, the threshold, the expected
  verdicts, and NOAA's own 2025 count as external validation.
- `datum_check.py` - the rule as code (`REQUIRED_DATUM = "STND"`), plus a live re-check that
  re-fetches both datums for both windows. Verified 2026-09-18: **all four recorded peaks
  reproduced with delta 0.000.**
- `tests/test_noaa_datum.py` - 9 offline tests. If a future change ever makes the MLLW
  comparison exceed the threshold, the trap has changed shape and the notes need revisiting.

## Analysis scripts

- `crosscheck_htf.py` -> `htf_crosscheck_result.json`
- `sampling_check.py` -> `sampling_check_result.json`
- `split_capacity.py` -> `split_capacity_result.json`
- `clustering_check.py` -> `clustering_result.json`


## Why it is not the lead

Scientific interest is high and the licence is clean (U.S. federal public domain), and the
measurement programme above is now complete - but the base rate at the physical threshold is
1.37% pooled, so most of the modelling work is fighting an imbalance rather than predicting a
phenomenon. That is a legitimate reason for a task to be third rather than first, and it is a
measured reason rather than a guess. It is a good second or third task.

## Next action

Fix the station list, restrict the feature set to observations only, and write the
construction script. Prefer 6-minute labels where the budget allows, since hourly sampling
undercounts positive days by roughly 6% in the periods tested; the multi-year 6-minute
backfill belongs on a worker.
