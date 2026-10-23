# Release notes - v2026.10

First release of **nz-ea-wholesale-price-exceedance**: a binary
island-day prediction task on the New Zealand wholesale electricity market.
At the publication instant of the final wholesale energy prices for trading
day D (conservatively D + 6 calendar days, covering the maximum publication
lag measured on the publisher's daily-file channel), given the published
island daily mean final prices for trading days up to and including D, will
an island's daily mean final price on trading day D+7 exceed NZD 100/MWh?
The target day has not finished trading at the instant, so the label cannot
exist there under any publication scheme.

## What ships

| Asset | Bytes | Sha256 (first 16) |
| --- | ---: | --- |
| `public-train.csv` | 1,744,686 | `273aeb069ab29445` |
| `public-eval.csv` | 627,892 | `6302310db2fced5e` |
| `private-holdout.csv` | 364,911 | `101f6a70284aff37` |
| `meta.json` | 3,133 | `f9b8105a997e6269` |
| `quality.json` | 13,421 | `c37aed791cd38f0b` |

Artifact version `545e0e4418c1f0e5...`, gate **1.4.0**, 38/38 checks, 0
failed, re-accepted by `--accept` on the exact bytes before any scoring.
Splits (temporal, on the anchor trading day; the eval->holdout boundary is
the documented 2022-11-01 real-time pricing regime change): train
1996-10-30..2016-01-01 (14,004 rows, 19.92% positive, 404 positive
target-weeks), eval 2016-01-01..2022-11-01 (4,992 rows, 43.07%, 231 weeks),
holdout 2022-11-01..2026-10-16 (2,890 rows, 54.36%, 152 weeks) - both classes
in every split and every eval year.

## Task

New Zealand's market publishes final nodal prices per trading period for
every point of connection; the build aggregates them to the two islands'
daily means using the publisher's own mapping table and asks, one week ahead
of the anchor day, whether the island mean clears NZD 100/MWh - roughly
twice the long-run median, a level reached in sustained dry-year storage
episodes (August 2024 means measured at 815-884 $/MWh) and nearly never in
wet, quiet eras (January 1997 max 50 $/MWh). Every shipped feature is a
statistic of prices published by the instant or a calendar field; the
persistence analogue (the last published day) is the reference any solution
must be compared against.

## Baseline

The runner-contract baseline (the benchmark's own unmodified `train.py` +
`validate.sh`) measures **eval AUC 0.8924**, printed identically by both
entry points and matched by an independent recompute. The triad on identical
eval rows: calendar-only 0.5011 < persistence_value 0.8820 <
persistence_mean7 0.8843 < full model **0.8924**. **Headroom over
persistence is not demonstrated** under the criterion declared before the
run: the observed advantage (+0.0104 over persistence_value, +0.0081 over
persistence_mean7) is positive, but the target-week-clustered paired
intervals both contain zero - an inconclusive difference, not parity and not
a trailing-model defect. Calendar-only is beaten decisively (+0.391). All
numbers, with the commands that produced them, are in `VERIFICATION.md`, and
persistence is quoted beside every model number by policy.

## Construction notes

- **The instant is a publication event, conservatively placed.** The
  Authority documents that interim prices "will be declared to be final
  prices by 2pm the following business day"; the measured daily-channel
  Last-Modified lag is 0-5 calendar days over 365+ files, so the instant is
  D+6 - every feature is published by then, and the D+7 target has not
  finished trading.
- **Coverage and channels.** 10,979/10,979 trading days 1996-10-01..
  2026-10-22 present, both islands every day; the monthly channel owns dates
  <= 2025-10-31, the daily channel the rest, and the 10 overlap days agree
  exactly (max |island mean diff| 0.0).
- **Mapping.** POC -> island via the publisher's NetworkSupplyPointsTable
  (894 POCs, 0 conflicts); 9,437,515 unmapped-POC source rows (retired nodes)
  excluded and counted per year.
- **Prevalence drift is the market's property** (19.92% train -> 43.07% eval
  -> 54.36% holdout; the holdout is the post-2022-11 real-time pricing
  regime), reported per split and per year, not smoothed.
- **Vintage.** Built from the container as listed 2026-10-23; only current
  vintages exist (the monthly files carrying pre-2022 dates were themselves
  uploaded 2022-10-31), so feature values are current-vintage with the cutoff
  documented. A rebuilt later vintage is a new artifact that must be
  re-qualified before any number from it is quoted.

## Licence

Source: Electricity Authority (Te Mana Hiko) EMI datasets, CC BY 4.0
(attribution to the Authority carries through to every copy; changes are
indicated). Our derived compilation: CC0-1.0. Code and documentation: MIT.
See `LICENSE.md`. This is a derived research dataset, not the Authority's
official product.
