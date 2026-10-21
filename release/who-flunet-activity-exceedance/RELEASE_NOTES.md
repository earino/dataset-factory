# Release notes - v2026.10

First release of **who-flunet-activity-exceedance**: a binary country-week prediction task on WHO
FluNet influenza test positivity.

## What ships

| Asset | Bytes | Sha256 (first 16) |
| --- | ---: | --- |
| `public-train.csv` | 1,496,272 | `2515289b43bdd49b` |
| `public-eval.csv` | 1,589,403 | `7d809b16ed3b833b` |
| `private-holdout.csv` | 3,482,298 | `f7dd814a73c864df` |
| `meta.json` | 2,915 | `592552716187b664` |
| `quality.json` | 5,610 | `efa583ba6a07c108` |

Artifact version `b1323a27fa02eb79...`, gate 1.3.0, `ok: true`, 0 failed checks. The five files are
the flunet-002 artifact as gated on the worker; they were fetched from staging for the baseline
run and digest-verified on arrival.

## Task

Positivity in ISO week W+4 above 10% of processed specimens, predicted from a country's weekly
FluNet series through week W. Splits are temporal: train <= 2019, eval 2020-2022, holdout 2023
onward. 26,093 country-weeks; 5,779 / 6,831 / 13,483 across the splits.

## Numbers

- Base rates 59.2% / 23.9% / 40.7% - the movement is the phenomenon (COVID-era trough, later
  systematic negative reporting), documented rather than smoothed.
- Persistence reference: 0.8929 AUC eval, 0.8745 holdout.
- Runner-contract baseline: see `VERIFICATION.md`.

## Corrections carried into this release

- The construction script's module docstring quoted the candidate record's superseded
  ">40% at peak" France fixture. The build itself pinned the measured blended frame (peak 0.2379,
  floor 0.15); the docstring was corrected to match. Documentation only - no code path, threshold
  or output byte changed.
- The record's 40%-at-peak fixture came from sentinel-only curves of stronger seasons; this frame
  sums `ORIGIN_SOURCE` streams, where the 2024-25 French peak is 23.8%.

## Known limits

- The source is a live weekly register; a rebuild today will not reproduce these digests.
- Country testing practice varies; the systematic-negative rule removes the largest known break
  (pre-2015 missing negatives) but is not a guarantee of comparability.
- No agent or harness comparison was run on this artifact.