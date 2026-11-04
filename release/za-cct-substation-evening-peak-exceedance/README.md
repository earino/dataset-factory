# Cape Town switching-substation evening-peak exceedance (same-day 06:00 forecast)

A binary prediction task on the City of Cape Town's published switching-substation
load telemetry (half-hourly MVA per 33/66/132kV switching substation, 2022-2024).
At 06:00 SAST on day D, for every substation with at least 30 prior evenings of
history, predict whether the evening peak load (maximum half-hourly MVA over
16:00-22:00 SAST) will exceed the station's trailing-90-evening 95th percentile:
`exceeds = 1`. Base rate at eval: 1,256 / 14,965 = 8.39%.

Derived research dataset, **not a City of Cape Town product**. Source: City of
Cape Town Open Data Portal, Switching Substation Load Profile (ArcGIS item
bebf20c25bfa4ffaa7fc07a1a94ba287), Open Data Terms of Use. Source: City of Cape Town Open Data Portal - Switching Substation Load Profile (ArcGIS item bebf20c25bfa4ffaa7fc07a1a94ba287), accessed 2026-11-01.. The
publisher's own caveat carries through: readings are indicative measured MVA,
not corrected for temporary load shifts or load fluctuations due to load
shedding - the label measures demand-as-dispatched, not underlying demand.

## The recorded result, first

This package is an **agent-headroom benchmark** (operator decision (a), recorded
2026-11-04): the recorded stock-runner result sits far below a one-line reference
computed from the same shipped columns, so the reference ladder - not the stock
model - is the target a solver must beat. The runner-contract baseline (the
benchmark's own unmodified `train.py` + `validate.sh`, one XGBoost pass) scored
**eval AUC 0.5107** on the 14,965 eval rows:

| Reference / model (identical 14,965 eval rows) | Eval AUC |
| --- | --- |
| `morning_ratio` - morning_max / hist_morningpeak_mean_90 (headroom reference) | **0.7340** |
| `month_only` - train-fitted month rate | 0.6541 |
| `calendar_identity` - station x month rate from train | 0.6504 |
| `persistence_prev_evening` - prior evening's exceedance (info-asymmetric by design) | 0.6502 |
| `identity_only` - station rate from train | 0.5134 |
| Full model (stock runner baseline) | **0.5107** |

Majority-class accuracy on eval is 0.9161 (constant fitted on train, measured
against eval labels); the global constant is degenerate as a score. The stock
runner is at chance - below even the identity-only control. `morning_ratio` is
the pre-registered headroom reference: it reads only shipped at-instant columns
(`morning_max / hist_morningpeak_mean_90`), so there is **no information
asymmetry** - a consumer of this artifact computes it in one line. Its edge over
persistence is measured with a paired clustered bootstrap (150 resamples,
(station, day) clusters): difference [-0.1012, -0.0706] over persistence and [-0.1019, -0.0627]
over calendar_identity, both excluding zero; persistence vs calendar_identity
[-0.0168, 0.0161] spans zero, so those two are inseparable. The reference proves the
extractable signal is in the shipped features; the stock template does not find
it. Recorded diagnosis candidates: (a) the stock `train.py` spends the tree
budget partly on train-date memorization (`date` is a train-only categorical;
eval dates unseen -> NaN), (b) the model must express the morning ratio through
splits - the one-line rule is not among the stock features, (c) no misalignment
or post-hoc reference (both AUC figures from the runner's own two
implementations on the same accepted bytes), (d) prevalence shift (11.20%
train -> 8.39% eval) cannot explain a fall to chance. **No model above
the reference has been measured, and no figure from this dataset may be quoted
without the comparison above beside it.** Fitting until a score wins is not the
protocol.

`persistence_prev_evening` needs a note of its own: it is recomputed scorer-side
from the labels of strictly-earlier same-station rows. A shipped prior-evening
label would be exactly the cross-row recovery this artifact's design excludes,
so the model is DENIED that information - the model-vs-persistence comparison
is information-asymmetric by design, while `morning_ratio` is a fair
same-information target.

## Prediction instant and contract

The instant is 06:00 SAST (Africa/Johannesburg, UTC+2, no DST) on the target day
D. Every shipped feature is knowable at that instant: the twelve same-day
00:00-06:00 half-hourly MVA slots (the 05:30 slot completes exactly at 06:00),
their mean/max/min, the calendar of D, the station identity, and the mean of
the trailing <= 90 prior days' MORNING peaks (latest member D-1). The evening
window 16:00-22:00 SAST lies entirely after the instant. Row selection reads
only days strictly before D; the burn-in station-days (1,230 of them, with
fewer than 30 prior evenings for the p95) are counted and never scored as
negatives. Worked example: Grassy_Park_66kV on 2024-07-15 (Monday, mid-winter),
trailing-90-evening p95 146.82 MVA, evening peak 150.38 MVA -> label 1.

**No evening-derived value ships.** Evening readings, evening peaks and the
trailing-evening p95 are the label's operands; a sliding evening quantile's
day-over-day delta reconstructs the entering evening's exceedance almost
exactly (the synthetic rehearsal pinned that attack at 0.995 exact agreement),
so they are sealed outside every solver-visible frame (staging-side
`auxiliary/evening_peaks.csv`, never a solver input) and the model predicts
exceedance of a threshold it never sees. The gate's cross-row probe measured
the one history column that does ship (`hist_morningpeak_mean_90`, MORNING
peaks) at 44.9% eval mismatches under the strongest label-recovery join - no
recovery. The evaluation contract is **retrospective research** (`use:
retrospective_research`, `access: isolated_rows`): the publisher serves the
2022-2024 window as one closed static table (item created 2026-02-28, has
no earlier vintages), so no operational availability at historical instants is
claimed, and honest evaluation keeps rows isolated.

## Splits

Temporal on the target day (Africa/Johannesburg), one year per frame:

- train: 2022 - 13,735 rows / 1,539 positives (11.20%), 227 distinct exceedance days
- eval: 2023 - 14,965 rows / 1,256 positives (8.39%), 246 distinct exceedance days
- holdout: 2024 - 15,006 rows / 1,382 positives (9.21%), 247 distinct exceedance days (sealed; never evaluated)

41 substations, 1,096 days, 52,608 raw half-hourly readings
(48 x 1,096, gapless), fetched anonymously from the publisher's FeatureServer in
54 pinned requests. Positives cluster city-wide on regime days (cold-front and
load-shedding evenings), so the distinct-day counts are the conservative
independent-observation count; positive rate drifts across splits
(11.20% -> 8.39% -> 9.21%) and is recorded as a property of
the regime, not repaired.

## Contents

- `public/train.csv`, `public/eval.csv`, `private/holdout.csv`, `meta.json`,
  `quality.json` - release assets (flat names; `get_dataset.py` restores the
  layout and verifies every sha256)
- `code/` - the construction script (`build.py`, stdlib-only, harvests and pins
  the source pages itself), the worker pipeline (`run.sh`), the references
  implementation (`score.py`), the runner workdir materializer
  (`materialize.py`) and the qualification gate (`qualify_dataset.py` 1.5.0)
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
compilation CC0-1.0 (our contribution only); the City of Cape Town source keeps
its own Open Data Terms of Use with attribution - see `LICENSE.md`.
