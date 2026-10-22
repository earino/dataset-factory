# Release notes - v2026.10

First release of **tsb-railway-occurrence-casualty**: a binary occurrence-level
prediction task on Canadian rail safety. When a railway occurrence begins on the
Canadian federal network - at a known place, time and operating context - will it
result in at least one casualty? Every feature is a pre-onset property of the
occurrence; TSB's own outcome-embedding taxonomy, injury fields, at-scene weather,
investigation and process fields are excluded by construction and never ship.

## What ships

| Asset | Bytes | Sha256 (first 16) |
| --- | ---: | --- |
| `public-train.csv` | 980,529 | `4a032f68c4ad944a` |
| `public-eval.csv` | 474,335 | `2f1dcafb6cc701b1` |
| `private-holdout.csv` | 244,586 | `b00bf00bd4f918ce` |
| `meta.json` | 2,606 | `5f3852f3150cd808` |
| `quality.json` | 7,131 | `a7343bd15a119c67` |

Artifact version `e75a59bb1116e39b...`, gate **1.4.0**, 37/37 checks, 0 failed,
re-accepted by `--accept` on the bytes before any scoring. Splits (temporal, by
occurrence date): train 2016..2021 (7,925 rows, 11.14% positive), eval 2022..2024
(3,831 rows, 12.09%), holdout 2025..2026-08 (1,976 rows, 14.07%) - both classes in
every window, each positive an independent occurrence.

## Task

A derailment, crossing accident, trespasser event, fire or collision begins at a known
subdivision, local hour and activity type, on a known railway. Predict, at onset,
whether anyone will be killed or injured. The casualty outcome unfolds after onset;
the label is derived from injury fields that are excluded from every shipped file.

## Baseline

The runner-contract baseline (the benchmark's own unmodified `train.py` + `validate.sh`)
measures **eval AUC 0.8126**, printed identically by both entry points. The
construction-time references it had to beat: a trailing-12-month casualty-rate
persistence analogue (0.527 eval / 0.495 holdout rank AUC) and the best single context
column, `activity_type` (0.707 / 0.699). The full model clears both - the task teaches
real pre-onset signal and is not a persistence exercise. All three numbers, with the
commands that produced them, are in `VERIFICATION.md`.

## Construction notes

- **The panel start is measured, not assumed.** TSB's pre-2016 rows carry a legacy
  taxonomy-era signature that fades gradually (2-7% through 2015, ~0 from 2017), so the
  panel starts 2016-01-01; the per-year decay table is in the candidate record and the
  build asserts the band [2014, 2018].
- **Coordinates arrive in three mixed encodings.** RODS packs lat/long in ddmm.ff,
  x10^3 and x10^6; the build decodes with a measured rule (0 ambiguous, 0 undecodable
  over a 3,088-value window) and asserts the Canadian envelope. An earlier single-scale
  assumption misread four good values as "corrupt" - the correction is recorded in
  `measurements.json`.
- **Publisher cross-check.** The panel's 2025 accident/incident counts reconcile with
  TSB's own annual summary to within 0.3%, and the label agrees with the publisher's
  separate INJURIES child table on all 1,624 positive rows.
- **Vintage.** Built from the RODS republish of 2026-10-21 (data through 2026-08-31).
  RODS is republished monthly; a later vintage is a new artifact and must be
  re-qualified before any number from it is quoted.

## Licence

Source: Open Government Licence - Canada 2.0 (attribution carries through to every
copy). Our derived compilation: CC0-1.0. Code and documentation: MIT. See `LICENSE.md`.
This is a derived research dataset, not a TSB official product.
