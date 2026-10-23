---
license: other
license_name: cc-by-4.0-source-plus-cc0-compilation
language:
  - en
pretty_name: NZ Wholesale Electricity Price Exceedance (New Zealand)
size_categories:
  - 10K<n<100K
task_categories:
  - tabular-classification
tags:
  - tabular
  - energy
  - electricity-markets
  - new-zealand
  - temporal-split
  - time-series
  - exceedance
configs:
{CONFIGS_BLOCK}
---

# NZ Wholesale Electricity Price Exceedance ({RELEASE_TAG})

**Status: {STATUS_LINE}**

New Zealand's wholesale electricity spot prices are published as final prices with a
documented lag: the Electricity Authority states interim prices "will be declared to be
final prices by 2pm the following business day", and on the publisher's daily-file channel
the measured delay is 1-5 calendar days. **At the instant day D's final prices are
published, will a pricing island's daily mean final wholesale energy price exceed NZD
100/MWh on trading day D+7** - about a week ahead? One row per (island, anchor trading day);
the label is the D+7 island mean, which cannot exist at the instant because that trading
day has not finished.

Every feature is a function of final prices for trading days up to and including D only:
the island's last published daily mean, trailing 7/30-day means and max, 7-day volatility,
days above threshold in the trailing 30, the cross-island ratio, and calendar cycles of the
anchor day. The label source columns (the target day's prices) are excluded from every
shipped file, and the qualification gate verifies this over the shipped columns.

- **Artifact version:** `{ARTIFACT_VERSION}`
- **Version tag:** `{RELEASE_TAG}` (use this revision for reproducibility)
- **Rows:** {ROWS_TOTAL} island-days across three disjoint temporal splits
- **GitHub counterpart:** {GITHUB_REPOSITORY}

## Splits

| split | rows | anchor trading days | positive rate |
| --- | ---: | --- | ---: |
| `train` | 14,004 | 1996-10-30 .. 2016-01-01 | 19.9% |
| `eval` | 4,992 | 2016-01-01 .. 2022-11-01 | 43.1% |
| `holdout` | 2,890 | 2022-11-01 .. 2026-10-16 | 54.4% |

The splits are temporal on the anchor trading day and disjoint. The eval-to-holdout
boundary is the market's documented 2022-11-01 transition from ex-post to real-time
pricing, so no window straddles that structural break and the holdout is a different market
regime by design. Positives cluster into multi-day dry-year storage episodes, so the gate
counts capacity by distinct positive target weeks (404 / 231 / 152), which are a capacity
floor rather than an independence proof. The panel covers every trading day from
1996-10-01 to 2026-10-22 (10,979 days, both islands, 0 missing).

The positive rate moves 19.9% -> 43.1% -> 54.4% across the splits: the eval window is
prevalence-shifted relative to training, and any score on it is as much an
out-of-distribution test as a temporal one. Per-target-year rates and scores are reported
beside the headline numbers rather than smoothed away.

## Reference points

The pre-declared criterion: headroom is demonstrated only if the runner-contract model
exceeds the stronger persistence reference **and** the week-clustered paired interval for
that difference excludes zero. Measured on the identical 4,992 eval rows, all through the
benchmark's unmodified `train.py` + `validate.sh` on the fetched, digest-verified,
gate-re-accepted bytes:

- **Full model (XGBoost):** eval AUC **0.8924**, reproduced identically by validate.py's
  independent recompute and a third stdlib implementation.
- **Persistence (last published day mean):** 0.8820. **Persistence (7-day trailing
  mean):** 0.8843. Week-clustered paired 95% intervals for model minus persistence:
  +0.0104 [-0.0010, +0.0226] and +0.0081 [-0.0028, +0.0206] - **both contain zero, so
  headroom over persistence is NOT demonstrated.** The observed advantage is positive but
  inconclusive at the dependence-aware level; this is neither parity nor a claim that no
  model can beat persistence.
- **Calendar-only (island x target week, train-fitted):** 0.5011 - beaten decisively
  (+0.391), so the task is not solved by seasonality and identity alone.

The holdout was never scored by anything and stays sealed; it sits in the post-2022-11
real-time pricing regime at 54.4% prevalence.

## Timing, honestly stated

The prediction instant is the **publication** of day D's final prices, placed
conservatively at D + 6 calendar days to cover the maximum measured lag (documented rule:
final by 2pm the following business day; measured Last-Modified minus trade date over the
365 relevant daily files: 1-5 calendar days, p50 1.8 days). A period-end instant would be
an oracle here, because a feature stamped "day M" did not exist at the end of day M. The
current-vintage caveat is documented rather than assumed away: the publisher exposes only
current final prices (no historical vintages), and the monthly-channel files carrying
pre-2022 trading dates were themselves uploaded 2022-10-31, so feature values are stated
as current-vintage with the cutoff anchored on the publisher's own documented finality
rule and the measured lags.

## Source and provenance

- Electricity Authority (Te Mana Hiko) EMI datasets: "Final energy prices" (anonymous
  Azure blob container: 360 monthly files 199610..202609 and daily files since 2025-10-21)
  and "Network supply points table" (POC -> island mapping with POC start/end dates).
- Channel ownership is explicit: monthly files own trading dates <= 2025-10-31, daily files
  own later dates; the 10 overlap days were cross-checked between channels
  (max |island mean diff| 0.0). POCs absent from the current-vintage mapping (retired
  nodes) are excluded from island aggregation and counted per year.
- Known-event fixtures asserted in-build from the constructed panel: the August 2024
  dry-year episode (four fixture days at daily means 814.77-883.56 $/MWh, matching the
  Authority's own review: "in early August the average daily price reached $820/MWh")
  exceeds; 2008-07-01 (mean 305.79) exceeds; the January 1997 quiet-era control (max 50.0)
  does not.
- Construction: `code/build.py`, executed by worker job `nz-ea-002`; qualification gate
  1.4.0, 38/38 checks, 0 failed, artifact version `{ARTIFACT_VERSION}`; baseline job
  `nz-ea-baseline-003` through the unmodified runner contract.

## Licence

The source data are Electricity Authority (Te Mana Hiko) materials under **CC BY 4.0**
(EMI LegalInformation and the successor hub's copyright statement). That attribution
condition carries through to every copy of the derived data: "www.emi.ea.govt.nz
provided by the Electricity Authority (New Zealand)". Our contribution to the derived
compilation is dedicated **CC0-1.0**; our code is **MIT**. This is a derived research
dataset, not the Authority's official product, and the Authority has not reviewed or
endorsed it. See `LICENSE.md` in the repository for the full terms, attribution and
citation.

## Use with the runner

```bash
python3 get_dataset.py --dest ./task
python3 code/qualify_dataset.py ./task
sh baseline/reproduce_baseline.sh ./task
```
