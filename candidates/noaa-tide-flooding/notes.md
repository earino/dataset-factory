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

## Why it is not the lead

Scientific interest is high and the licence is clean (U.S. federal public domain), but
the base rate is very low at the natural threshold, so most of the modelling work is
fighting an imbalance rather than predicting a phenomenon. It is a good second or third
task.

## Next action

Choose the target threshold deliberately: either the NOS minor threshold (measured, rare,
1.37% pooled) or a per-station training-window quantile (better balanced). Then fix a
station list, decide the feature set from observations only, and write the construction
script. Multi-year 6-minute backfill, if wanted, belongs on a worker.
