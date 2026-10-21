# WHO FluNet influenza-positivity exceedance

**Task.** For a WHO FluNet reporting country with systematic weekly negative reporting, will
influenza test positivity in ISO week **W+4** exceed **10% of processed specimens**, given that
country's weekly laboratory series through ISO week **W**?

This is a binary country-week prediction task built from the World Health Organization's FluNet
surveillance table. It is a **derived research dataset**, not a WHO product.

- **Prediction instant:** the Sunday that closes ISO week W. Every feature is derived from weekly
  counts published for weeks <= W. The target is week W+4's row, which is not yet observed.
- **Target:** `exceeds = 1` iff week W+4 positivity `INF_ALL / (INF_ALL + INF_NEGATIVE)` is
  strictly greater than `0.10`, with at least 50 specimens in that week and systematic negative
  reporting in the target country-year.
- **Grain:** one row per (country, prediction week W). `ORIGIN_SOURCE` streams are summed.
- **Splits:** temporal by the prediction week's ISO year - train <= 2019, eval 2020-2022,
  holdout 2023 onward.

## What is in the box

| File | Rows | Positive rate | Distinct country-years |
| --- | ---: | ---: | ---: |
| `public/train.csv` | 5,779 | 59.2% | 235 |
| `public/eval.csv` | 6,831 | 23.9% | 257 |
| `private/holdout.csv` | 13,483 | 40.7% | 422 |

The base rate moves between splits because the phenomenon moved: the eval window covers the
COVID-era collapse in influenza circulation and its recovery. That is a documented property of the
series, not a split fault; see `DATA_DICTIONARY.md`.

The holdout is published, so the task is reproducible. It must stay **outside an evaluated agent's
workspace** and be used only for scoring.

## Quickstart

```bash
python3 get_dataset.py --dest ./task        # 5 files, ~6.6 MB, sha256-verified
python3 code/qualify_dataset.py ./task      # the gate: expect ok=true, 0 failed checks
sh baseline/reproduce_baseline.sh ./task    # the benchmark's own train.py + validate.sh
```

## Baseline

The runner-contract baseline (XGBoost, the benchmark's unmodified `train.py`) is recorded in
`VERIFICATION.md` and in `MANIFEST.json`'s `baseline` block. A far stronger reference is
**persistence** - score the row by week W's own positivity, which measures 0.8929 AUC on eval and
0.8745 on holdout (standard-library rank AUC, measured at construction). A solution that cannot
beat persistence is not interesting on this task.

## Prediction timing and leakage

The label source columns (`INF_ALL`, `INF_NEGATIVE` of week W+4, and the rate derived from them)
never ship. Only the binary `exceeds` label is written. Lagged counts from weeks W-1..W-4 and an
eight-week rolling summary are features; nothing from week W+1 onward is. The build recomputes a
sample of rows against a series physically truncated at week W and reports zero mismatches.

## Licence and citation

The source data are WHO materials under **CC BY-NC-SA 3.0 IGO**; those terms are carried through
unchanged to this derived compilation (attribution, non-commercial, share-alike). Our code and
documentation are MIT. See `LICENSE.md`.

Cite: World Health Organization. *FluNet*. Geneva: World Health Organization; 2026. Licence:
CC BY-NC-SA 3.0 IGO. Derived dataset: WHO FluNet influenza-positivity exceedance prediction task.

## Provenance

- Source: <https://www.who.int/tools/flunet> - full table at
  `https://xmart-api-public.who.int/FLUMART/VIW_FNT?$format=csv` (anonymous, one request,
  32,246,617 bytes, sha256 `5695e5d2...`), retrieved 2026-10-20.
- Column meanings: the publisher's own `VIW_FLU_METADATA` view (53 documented fields).
- Construction: `code/build.py`, executed by job `flunet-002`; artifact version
  `b1323a27fa02eb79...`, gate 1.3.0. Reproduction instructions in `REPRODUCE.md`.
## Measured results, and what they establish

These are the numbers this artifact ships with. They were measured on the released bytes, not on a
rebuild, and they are reported here rather than left for a reader to discover.

| Reference | Eval AUC | Notes |
| --- | --- | --- |
| Full model (benchmark baseline) | **0.869990** | Brier 0.1347. The reproducible baseline, not a best-known solution. |
| Persistence (score = week-W positivity) | **0.8929** | A one-line rule, known at the prediction instant. **It beats the full model.** |
| Calendar-only, independent replication | 0.6269 | Country + cyclical week-of-year + hierarchical seasonal prior; gradient boosting. |
| Seasonal prior (this project) | 0.5509 | Country x target week-of-year, estimated from training history only. |
| Global week-of-year prior | 0.5437 | No country identity. |

Two conclusions follow, and both belong in the record:

1. **The task is not merely seasonal.** Calendar-only references top out around 0.63 while the full
   model reaches 0.87, so there is real learned signal beyond the calendar.
2. **The current baseline does not beat persistence.** Week-W positivity alone scores 0.8929 on the
   same eval rows. That is a property of this construction — the label is largely persistent — and it
   is stated plainly here so nobody mistakes 0.87 for evidence of forecasting skill.

Replication: the persistence and seasonal-prior figures were recomputed from `public-train.csv` and
`public-eval.csv` with an independent rank-AUC implementation; the calendar-only figure came from an
external agent that did not read this project's code. Artifact version, release identifiers and
per-asset digests are recorded in `MANIFEST.json` and `DESTINATIONS.json`.

## Limitations

- **Retrospective observed-outcome forecasting.** The task is built from outcomes that have already
  been observed. It is not a live prospective forecast and makes no claim to operational validity.
- **Historical publication timing is unverified.** We could not reconstruct what a forecaster could
  actually have seen at the end of week W; the publisher exposes only the current vintage, and
  revisions are not available. The cutoff is an assumption, stated rather than proven.
- **Row eligibility depends on the future.** Whether a row is eligible depends on whether its target
  week was eventually observed and met the denominator rule — information that did not exist at
  prediction time.
- **Sentinel and non-sentinel provenance is lost.** WHO's source distinguishes SENTINEL,
  NONSENTINEL and NOTDEFINED origins (46% of rows are NOTDEFINED). This release sums them, so the
  target mixes surveillance streams, and a change in reporting composition can look like a change in
  disease activity.
- **Calibration is not established.** The baseline is reported by AUC and Brier; it was not
  recalibrated, and the calendar-only replication showed substantial overprediction.
- **110 training labels may be premature.** Rows whose target week fell after the first evaluation
  prediction date were excluded from the replication's training set; the packaged split retains them.
- **Not an official WHO product**, and not endorsed or reviewed by WHO.
