# India CPCB station-day next-day PM2.5 exceedance (23:59 IST forecast)

A binary prediction task on the Central Pollution Control Board's CAAQM PM2.5
monitoring network, as republished by the XKDR Forum's India Air Quality
Database (data.xkdr.org). At 23:59 IST on day D, for every complete
(n_hours >= 18) PM2.5 station-day, predict whether the station's next
calendar day's 24-hour mean PM2.5 will exceed 90 ug/m3 - the Poor-band lower
breakpoint of CPCB's own National AQI: `exceeds = 1`. Base rate at eval:
19,819 / 126,570 = 15.66%.

Derived research dataset, **not a CPCB, Government of India, or XKDR Forum
product**. Source: Central Pollution Control Board (CAAQM network) via the India Air Quality Database, XKDR Forum (data.xkdr.org), licensed under the Government Open Data License - India (CPCB measurements) and CC BY 4.0 (XKDR compilation). Credit: India Air Quality Database, XKDR Forum; Central Pollution Control Board (CAAQM network); US Department of State via AirNow. Export accessed 2026-09-30 (pinned; construction verifies exported_at and row count).. The republisher's own data-quality caveat carries
through: values are "as reported", with "no gap filling", and marked
"preliminary and not fully validated" (XKDR README).

This package is release v2026.11 of artifact `a749f0df2f9dd0103d0ba56524e1cc3638242fbc4710b0cac99603bcdef0d959` (gate 1.5.0,
45/45 checks, exact-byte accepted; the five files' digests are in
`MANIFEST.json` and `SHA256SUMS`).

## The recorded result, first

The runner-contract baseline (the benchmark's own unmodified `train.py` +
`validate.sh`, one XGBoost pass) scored **eval AUC 0.9734** on the
126,570 eval rows (2023), and the pre-registered deciding rule - written
before any score existed - is satisfied: the model beats **every** triad
member with a station-clustered paired bootstrap 95% CI excluding zero:

| Reference / model (identical 126,570 eval rows) | Eval AUC |
| --- | --- |
| Full model (stock runner baseline) | **0.9734** |
| `station_persistence` - day-D `pm25_mean` as the score | 0.9689 |
| `state_season_climatology` - train rate per state x season of D+1 | 0.8617 |
| `station_train_rate` - identity prior (supplementary) | 0.7616 |
| majority-class accuracy (constant fitted on train, vs eval labels) | 0.8434 |
| `global_rate` - constant train rate | degenerate (Brier 0.1351) |

- model minus station_persistence: **+0.004491**, CI95 [0.0038, 0.0052] (1,000
  resamples, 509 station clusters) - excludes zero
- model minus state_season_climatology: +0.1118, CI95 [0.1002, 0.1252] - excludes zero
- the degenerate constant member: the model's own cluster-bootstrap AUC CI
  [0.9713, 0.9753] lies entirely above 0.5
- station_persistence minus state_season_climatology: +0.1073, CI95 [0.0959, 0.1208]

**Headroom is demonstrated under the pre-registered rule - on eval 2023
only; the holdout (2024) is sealed and has never been scored.** The honest
reading travels with the number: the label is largely persistence-carried
(the station's own day-D mean ranks D+1 exceedance at 0.9689), so the
model's edge over persistence is real but small (+0.004491 AUC), while the
gap to the calendar/identity climatology is large. Persistence's supplementary
binary rule (`pm25_mean > 90` -> predict exceedance) agrees with the label
0.9350 of the time. **No figure from this dataset may be quoted without
the comparison above beside it.** No re-tuning of threshold, window, label or
features happened after any score.

## Prediction instant and contract

The instant is 23:59 IST on day D. Every shipped feature is knowable at that
instant: the station's own daily PM2.5 statistics for day D
(`pm25_mean`/`pm25_max`/`pm25_min`/`n_hours`), its trailing history
(lags 1-3, 7/30/90-day means with valid-day counts, days since a >90 day,
30-day exceedance count), the calendar of D (day-of-week, month, cyclical
day-of-year), and the station's identity (`station_id`, `state_name` - the
62 stations without a recorded state ship the declared sentinel
`UNKNOWN_STATE`, never an invented state). The label window - the D+1
calendar-day 24-hr mean - lies entirely after the instant. The label source
(`next_day_pm25_mean`, `next_day_n_hours`) is excluded from every shipped
column.

Row selection reads day-D completeness (knowable at the instant) plus a D+1
*observability* rule that never reads the label value; unlabelable rows are
excluded and counted per split (train/eval/holdout: 17,416 / 9,368 / 10,879), as are thin
day-D rows (33,586 / 18,065 / 20,101) and rows outside the declared windows (42,638).
The 2025-04..09 partial tail (47,566 station-days, 829 valid-day
positives) is excluded and counted; the 2025-01..03 and 2025-10..12 hole
months in the export are asserted empty.

**Retrospective-research scope, stated everywhere.** The archive is ONE
pinned export (exported_at 2026-09-30T11:25:11+00:00, 196,521,834 rows; the build
asserts both and refuses any other export), so no operational as-of claim is
made and training-label timing stays unverified (`use:
retrospective_research`, `access: isolated_rows`, vintage `current_snapshot`).
CPCB intraday publication latency is unmeasured; treating day-D trailing
hours as complete at the instant is a declared assumption. Honest evaluation
keeps rows isolated.

## Known-event and negative-control fixtures

The label is bound to the publisher's own instrument: CPCB's Daily AQI
Bulletin of 2024-11-18 (Delhi Severe 494, prominent pollutant PM2.5,
36/39 stations) - and the measured panel confirms it: 36/36
complete Delhi station-days on 2024-11-18 carry a 24-hr mean above 90 ug/m3
(the station registry carries 39 Delhi stations; the 3 exceptions
are incomplete days, matching the bulletin's own 36/39 denominator). The
monsoon trough day 2023-08-15 is the negative control: 389
complete all-India station-days, 1 exceed - a unit or
reference-frame error would move this to its extreme and fail the build.

## Splits

Temporal on the prediction instant (IST), declared windows:

- train: 2019-2022 - 288,754 rows / 61,075 positives (21.15%),
  1248 distinct positive days, 389 stations
- eval: 2023 - 126,570 rows / 19,819 positives (15.66%),
  351 distinct positive days, 509 stations
- holdout: 2024 - 145,124 rows / 18,222 positives (12.56%),
  352 distinct positive days, 529 stations
  (**sealed; never evaluated**)

Panel: 717,429 station-days across 546 reporting
stations (549 registered), fetched from the pinned
export in 168 monthly requests (54,138,890 bytes, 0 truncated,
0 unparseable). Positives are winter-clustered (eval 2023: DJF 33.0% vs
JJAS 1.0% prevalence), so distinct-positive-day counts are the
conservative independent-observation count and every interval in the
deciding check is station-clustered. Positive rate declines across the
split (21.15% -> 15.66% -> 12.56%): an
out-of-distribution as well as temporal test, recorded as a property of the
data, not repaired.

## Contents

- `public/train.csv`, `public/eval.csv`, `private/holdout.csv`, `meta.json`,
  `quality.json` - release assets (flat names; `get_dataset.py` restores the
  layout and verifies every sha256)
- `code/` - the construction script (`build.py`, stdlib-only, fetches from
  the pinned XKDR export and refuses a changed export), the worker pipeline
  (`run.sh`), the references implementation (`score.py`), the runner workdir
  materializer (`materialize.py`) and the qualification gate
  (`qualify_dataset.py` 1.5.0)
- `baseline/` - the harness benchmark's own runner files, verbatim, plus the
  reproduce script
- `measurements.json`, `MANIFEST.json`, `SHA256SUMS`, `VERIFICATION.md`,
  `REPRODUCE.md`, `RELEASE_NOTES.md`, `DATA_DICTIONARY.md`, `LICENSE.md`

## Quick start

```bash
python3 get_dataset.py --dest ./task          # download, verify, lay out
python3 code/qualify_dataset.py ./task        # gate 1.5.0 over the artifact
sh baseline/reproduce_baseline.sh ./task      # the recorded baseline
```

Licensing: our code and documentation MIT; our rights in the derived
compilation CC0-1.0 (our contribution only); the CPCB measurements keep
GODL-India and the XKDR compilation keeps CC BY 4.0, both with attribution -
see `LICENSE.md`.
