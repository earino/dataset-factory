# noaa-tide-flooding

**Status: shortlisted; needs base-rate measurement (2026-09-18).**

## The task

Predict whether a station's daily maximum observed water level exceeds its
published minor flood threshold tomorrow.

## Measured evidence (2026-09-18, anonymous CO-OPS APIs)

| Query | Result |
|---|---|
| `mdapi/prod/webapi/stations.json?type=waterlevels` | 302 water-level stations |
| same, `expand=floodlevels` | all 302 carry flood thresholds |
| Boston 8443970 flood levels | nos_minor 15.85, nos_moderate 16.73, nos_major 18.04, nws_minor 16.03 feet |
| 6-minute water level, Boston, 2026-09-01 | 240 rows, `q=p` preliminary |

Retrieval limits matter: 6-minute data is limited to one month per request, hourly
data to 200 years. A multi-year 6-minute backfill is therefore many requests, which
is exactly the kind of work that belongs on a worker.

## Leakage discipline

NOAA publishes tide predictions and model guidance for the same stations
(`product=tide_predications`, `product=ofs_water_level`). Those are model output.
Including them turns the task into "reproduce NOAA's model" and inflates scores.
Observation-only features are the defensible version.

## Why it is not the lead

Scientific interest is high and the licence is clean (U.S. federal public domain),
but the exceedance rate has not been measured and thresholds vary per station, so
the headroom question is entirely open. It is a good second or third task.

## Next action

Measure per-station exceedance base rates for a candidate station set, then choose
threshold and station list before writing the construction script.
