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

## Licence read from the source, not assumed (2026-09-19)

The record previously said "U.S. federal government work; NOAA CO-OPS data are public domain.
Portal attribution page not read in this session." That is an assumption with a citation-shaped
hole in it, and `dataset-discovery` treats an unread licence as unmet contract 1. Read now, from
the portal the data actually comes from:

- `https://tidesandcurrents.noaa.gov/disclaimers.html`, *Use of Data and Products*: "The
  information on government servers are in the public domain, unless specifically annotated
  otherwise, and may be used freely by the public." Attribution is *requested* ("NOS requests
  that attribution be given whenever NOS material is reproduced and re-disseminated"), not
  required; 17 U.S.C. 403 is cited.
- Corroboration: `nauticalcharts.noaa.gov/data/data-licensing.html` records NOAA data under a
  CC0-1.0 public-domain dedication; the NCEI ISO metadata for CO-OPS stations carries the same
  CC0 waiver.

**A constraint that binds the release:** the same page says "This information shall not be
modified in content and then presented as official government material." A derived dataset with
computed features and a `late`-style label *is* modified content, so the release must be labelled
as derived from NOAA/NOS data and must never be presented as official NOS data or as an official
flood determination. Recorded here so it reaches the dataset card rather than being rediscovered
at publication.

## Still open before construction

1. Freeze the station list: only stations whose published flood thresholds are usable in the
   station datum (`datum=STND`).
2. Restrict features to observations only.
3. **Measure** the extraction cost - requests, bytes, wall clock. Unmeasured as of this note, so
   the candidate does not yet meet the `ready` bar in `dataset-discovery`.

## Station list frozen and extraction cost measured: this candidate is now `ready` (2026-09-19)

Scripts (in this directory, re-runnable): `frozen_station_list.py` -> `station_list_result.json`,
`cost_probe.py` -> `cost_probe_result.json`, `clustering_frozen.py` -> the same result file.

**The threshold claim in this record was wrong, and one request showed it.** The record said all
302 water-level stations carry flood thresholds. Measured with a single request
(`mdapi/.../stations.json?type=waterlevels&expand=floodlevels`): **132 of 302 publish a numeric
`nos_minor`**; 170 publish none. The endpoint returns either a bare number or an object whose
`nos_minor` is `null`, so "the expand is present" is not "a threshold exists".

**The frozen list is computed from the source, not hand-picked.** A station qualifies if its
`nos_minor` is numeric **and** NOAA's own HTF annual product reports counts for at least 18 of the
20 target years 2006-2025 (1 request per station; 132 fetched, 0 errors, 18.6 s). Result:
**122 stations**. The full ordered list, with per-station positives, is in
`station_list_result.json`.

**Split capacity over the frozen list** (NOAA `htf/annual` `minCount`, the authoritative product):

| split | years | station-days | positives | rate | moderate+ |
|---|---|---|---|---|---|
| train | 2006-2021 | 708,830 | 11,886 | 1.68% | - |
| eval | 2022-2023 | 89,060 | 1,828 | 2.05% | - |
| holdout | 2024-2025 | 89,060 | 2,850 | 3.20% | - |

The daily product reproduced both evaluation counts exactly (1,828 / 2,850), which is a
cross-check between two NOAA products rather than a single source believed twice.

**Independent events, measured over the frozen list** from `htf/daily.json` (distinct calendar
days with at least one flood):

| split | positive station-days | distinct flood days | mean stations/day | busiest day |
|---|---|---|---|---|
| eval 2022-2023 | 1,828 | 332 | 5.51 | 52 |
| holdout 2024-2025 | 2,850 | 427 | 6.67 | 54 |

Train clustering is **not measured** - recorded as unmeasured rather than guessed. So the numbers
a score is quoted against are 332 and 427 independent events, not 1,828 and 2,850.

**Extraction cost, measured on this host** (per request, then multiplied by the counted set):

| product | rows | bytes | seconds |
|---|---|---|---|
| 6-minute water level, 1 month | 7,440 | 560,602 | 1.61 |
| hourly height, 1 year | 8,760 | 545,427 | 2.219 |
| inventory with `expand=floodlevels` | - | 777,394 | 1.338 |

`product=daily_max` **does not exist** - the API answers HTTP 400 - so verified daily maxima have
to be derived from observations. Over 122 stations x 20 years (2,430 station-years):

- **6-minute labels: 29,160 requests, 15.2 GiB, ~782 min single-threaded.** A worker backfill,
  not a coordinator job.
- **hourly labels: 2,430 requests, 1.2 GiB, ~90 min single-threaded** - 12x cheaper, but measured
  to undercount about 6% of positive days.

Wall clock *with concurrency* is not measured; the figures are sums of measured per-request times.

A second API trap, recorded because it silently produced zero rows: `htf/daily.json`'s per-day
array is `DailyFloodCount`, not a guessed key, and `minFlag` arrives as the string `"1"`. Reading
the wrong key yields "no flood days" with no error - the same shape as the datum trap.


## The 6-minute fetch was the wrong route (2026-09-19)

The record claimed `product=daily_max` did not exist (HTTP 400). It exists as **`daily_max_min`**: with
`time_zone=GMT`, `interval=6` and `datum=STND` it returns a **whole station-year of 6-minute daily
maxima in one request**. Live probe, Boston 8443970 for 2024: HTTP 200, 72,877 bytes, 366 days, every
day `pcComplete6Min=100`, values 12.074-17.930 ft STND.

Why that matters:

| route | requests | data | quality |
| --- | --- | --- | --- |
| raw `water_level` 6-minute (1-month cap per request) | 29,160 | 15.2 GiB | preliminary rows, reduced by us |
| `daily_max_min` (one request per station-year) | 2,440 | ~178 MB | **verified** maxima with completeness and quality flags |

The daily maximum is exactly what the label needs, so the primary task now takes the second route:
**12x fewer requests and ~85x less data, from the publisher rather than from us.** The raw series is
only needed for sub-daily tasks (onset timing, lead time) and that becomes a deliberate decision
rather than the default - which also removes the "does a 4 GB table belong on Hugging Face" question
from this dataset entirely.

Lesson, again the same one: a negative finding from a wrong probe is not a finding. The API's own
error message lists the valid product names, and reading it would have caught this immediately.

## The task design, decided on measured capacity (2026-09-19)

The plumbing was settled earlier; what was open was what the dataset *is*. Decided here, with the
capacity measured rather than assumed. Scripts: `spatial_split_capacity.py` ->
`spatial_split_result.json` (one request to NOAA's annual product returned every station-year).

**Target.** Does station S's daily maximum observed water level exceed S's published NOS **minor**
flood threshold on the next local day?

**Label: the publisher's own flood days.** NOAA's HTF daily product (`htf/htf_daily.json`,
`minFlag`), one request per station-year. The reconstruction route was rejected on measurement -
see below. The verified 6-minute daily maxima (`product=daily_max_min`, `interval=6`,
`datum=STND`, `time_zone=GMT`) are the **feature** source instead. Verified rather than preliminary
rows, with `pcComplete6Min` completeness and quality flags, and it is exactly the reduction the
label needs - so the 29,160-request raw-series route is not used. Build cost: **2,440 requests,
~178 MB**.

**Prediction time.** The end of the previous local day. Every feature is knowable then.

**Features: observations only, station-normalised.** NOAA tide predictions and model guidance are
excluded *because they are not observations* - and because including them is the obvious way an
agent defeats the task. Station-relative quantities (margin against that station's published
threshold, trailing mean/spread of its own maxima, days since its last exceedance, exceedance count
over trailing windows) with day-of-year for the seasonal cycle. Station statistics are computed from
**trailing** windows only: a whole-series normalisation would feed the future into the features,
which is the leakage the qualification gate exists to catch.

**Two evaluation levels, both scored:**

| level | split | positives (station-days) | independent events |
| --- | --- | --- | --- |
| `temporal` | train 2006-2021 / eval 2022-2023 / holdout 2024-2025, all 122 stations | 11,886 / 1,828 / 2,850 | 332 (eval), 427 (holdout) |
| `station_disjoint` | train on group1+group2, evaluate on group0 - never seen in training | holdout 1,090; eval 792 | **337 (holdout), 298 (eval)** |

The partition is deterministic and published, not hand-picked: sort the 122 frozen stations by NOS
station id and take every third into group0 (~41 stations). The three groups' positives sum to the
temporal totals exactly (4,307 + 3,328 + 4,251 = 11,886), which is a cross-check between the
partition and the counts already recorded.

**Why the split is worth a monthly slot.** A station-disjoint evaluation asks whether an agent
learned something transferable rather than memorising one station's local tide behaviour. NOAA
publishes the observations, the verified maxima and the annual counts - so access is cheap and the
access is *not* the contribution. Nothing published scores this transfer question on a frozen panel
with a leak-free contract, and that is the whole basis of the novelty verdict.

**Per-station rates differ by more than 10x** (median 1.47%, p75 2.38%, max 16.4%, one station with
no positives in 20 years), so held-out stations are not interchangeable with training stations: the
partition bites, rather than being a technicality.

**Independent events on held-out stations, measured** (`spatial_clustering.py`, HTF daily
product, the same rule used for the temporal splits): the eval window holds 792 positive
station-days over **298 distinct flood days** (2.66 stations/day), the holdout window 1,090 over
**337 distinct flood days** (3.23 stations/day). Both station-day totals reproduce the annual
product's counts for the same group exactly, so two NOAA products agree on this partition. A score
on held-out stations is quoted against 298 and 337 independent events.

## The label route was wrong, and a year with real signal showed it (2026-09-19)

The 2025 cross-check that validated the STND reconstruction matched 12/12 stations (60 days vs 60) -
but 2025 had almost no flooding (Boston: 2 days), so it was a weak test. Re-running the comparison
on **2024**, where the sampled stations have 94 positive station-days, exposed a 20% disagreement:

| route | four-station total, 2024 | vs NOAA's 94 |
| --- | --- | --- |
| 6-minute daily maxima, `time_zone=GMT` | 114 | +20 |
| 6-minute daily maxima, `time_zone=LST` | 113 | +19 |
| hourly reconstruction at STND | 98 | +4 |
| **NOAA's own `htf_daily` flags** | **94** | **exact, station by station (25/26/23/20)** |

Time zone is not the cause (GMT and LST differ by one day in total). Our own reduction of 6-minute
maxima counts brief pokes above the threshold that NOAA's determination does not, so a dataset
labelled by our reconstruction would ship a definition that disagrees with the publisher's own
product - and would have to explain why. `label_route_check.py` -> `label_route_result.json`.

The label is therefore **NOAA's own minor-flood day flags**, which is better provenance than our
reconstruction and costs the same (one small request per station-year). The observations remain the
feature source. Cost is now **2 requests per station-year** (maxima + flags): 4,880 requests,
~180 MB.

Dry run over three stations and two years: labels match NOAA's counts except at window boundaries
(123 vs 126, 55 vs 59, 59 vs 59), where a flood day on the first date of the window has no previous
row to be labelled from. With the full contiguous window that loss is confined to a single day.

**Known limits.** A ~1.4-3% positive rate is rare; the transfer level has fewer independent events
than the temporal one, so its uncertainty is wider and has to be quoted against distinct flood days
rather than station-days. Both are recorded rather than smoothed over.
