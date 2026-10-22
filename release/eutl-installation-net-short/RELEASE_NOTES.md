# Release notes - v2026.10

First release of **eutl-installation-net-short**: a binary installation-year prediction
task on EU carbon-market compliance. At the close of compliance year t-1's surrender
cycle (30 April of year t), will a stationary EU ETS installation's verified emissions
for year t exceed the free allocation it holds for year t - a net-short year in which
the operator must buy allowances or face the excess-emissions penalty? Every shipped
feature is a registry value settled at the instant (t-1 emissions, t-1 and announced
year-t allocation); year t's verified emissions - the label's other side - are reported
only by 31 March of year t+1 and are absent from the registry at the instant.

## What ships

| Asset | Bytes | Sha256 (first 16) |
| --- | ---: | --- |
| `public-train.csv` | 9,421,952 | `c7f23c557d9605c9` |
| `public-eval.csv` | 1,660,374 | `0d9f35d5393734a9` |
| `private-holdout.csv` | 1,507,248 | `1c694e5e6b0bc0b3` |
| `meta.json` | 2,810 | `b0e54387f5a5348d` |
| `quality.json` | 10,270 | `88222d66bfd02aa5` |

Artifact version `3540ad2180d8df8a...`, gate **1.4.0**, 38/38 checks, 0 failed,
re-accepted by `--accept` on the bytes before any scoring. Splits (temporal, by
compliance year): train 2006..2019 (141,732 rows, 45.53% positive), eval 2020..2022
(24,322 rows, 74.02%), holdout 2023..2025 (22,151 rows, 72.20%) - both classes in every
window and every year, positives carried by thousands of distinct installations
(11,357 train / 7,810 eval / 6,283 holdout).

## Task

An installation closes year t-1 with settled verified emissions, surrendered allowances
and an already-published year-t free allocation (fixed in advance by the phase-4
national implementation measures; the registry carries allocation rows through 2030).
Predict whether its year-t verified emissions - reported a year later - will exceed that
allocation. The comparison is a market position: net-short means buying allowances at
auction or on the secondary market, net-long means surplus to sell.

## Baseline

The runner-contract baseline (the benchmark's own unmodified `train.py` + `validate.sh`)
measures **eval AUC 0.9199**, printed identically by both entry points. The triad on
identical eval rows: calendar-only 0.527 < identity-only 0.5719 < persistence (t-1
net-position margin) 0.8671 < full model **0.9199** (+0.0532 over persistence). Most of
the edge is the announced-allocation margin rule (`margin_t` alone: 0.8988) - the task's
natural one-line solver rule - and the model adds +0.021 beyond it. The label is
persistent (P(short|short) = 0.857) but persistence does not win by construction; all
numbers, with the commands that produced them, are in `VERIFICATION.md`.

## Construction notes

- **The eligibility frame is settlement-lagged.** A row exists for (installation, year t)
  only when both t-1 values are numeric; 16,709 insufficient-history rows (all of 2005
  plus each installation's first active year) are excluded rather than imputed. The
  partially-defined surrender-history feature `SURR_ALL(t-1)` was dropped (missing on
  10,647 of 188,205 eligible rows, measured) rather than shipped half-defined.
- **Publisher cross-check.** The shipped panel reconciles with the EEA's own EU ETS
  summary product when summed over exactly activity codes {10, 20-99} (the EEA sheet
  mixes detail and aggregate rows): DE 2022 verified emissions match exactly, 2023
  within 4 t, free allocation within 4.3e-4.
- **Prevalence drift is the documented ETS phase property** (45.53% -> 74.02% -> 72.20%
  across splits; the phase-3 allocation cut is the known-event fixture), reported per
  split and per year, not smoothed.
- **Vintage.** Built from the daily extract of 2026-10-22 (`SNAPSHOT_DATE` 2026-10-22,
  last-modified 10:08:26 GMT). The extract refreshes daily; live 2026 rows (6,449) gain
  verified emissions on 31 March 2027, and a rebuilt later vintage is a new artifact
  that must be re-qualified before any number from it is quoted.

## Licence

Source: European Commission reuse policy, CC BY 4.0 (attribution and indication of
changes carry through to every copy). Our derived compilation: CC0-1.0. Code and
documentation: MIT. See `LICENSE.md`. This is a derived research dataset, not the
European Commission's official product.
