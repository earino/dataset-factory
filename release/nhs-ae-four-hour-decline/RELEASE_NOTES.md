# Release notes - v2026.10

First release of **nhs-ae-four-hour-decline**: a binary provider-month prediction task on NHS
England A&E four-hour performance.

## What ships

| Asset | Bytes | Sha256 (first 16) |
| --- | ---: | --- |
| `public-train.csv` | 2,543,862 | `819b6715ad55272c` |
| `public-eval.csv` | 1,246,633 | `cb786792ac321dd8` |
| `private-holdout.csv` | 1,099,411 | `527a385f12a920b0` |
| `meta.json` | 3,292 | `c2f9f43a29d23101` |
| `quality.json` | 5,148 | `e7576e8a2431bacd` |

Artifact version `9903df974f233dfa...`, gate 1.3.0, `ok: true`, 0 failed checks. The five files
are the nhsae-002 artifact as gated on the worker; they were fetched from staging for the
baseline run and digest-verified on arrival.

## Task

Will a provider's Type 1 within-4-hour rate decline next month relative to this month, given its
monthly A&E series through this month? Splits are temporal on the target month: train
2019-01..2022-12, eval 2023-01..2024-12, holdout 2025-01..2026-09. 11,591 provider-months
(6,116 / 2,937 / 2,538) over 134 volume-gated providers.

A relative m/m label is used because every fixed standard threshold measured near-uniform
positive rates in recent years (<95% -> 99.9% of the holdout positive; <80% -> 95.8%): the
national standard deteriorated from ~83% (2018) to ~60% (2026), so a threshold label's base rate
drifts with the system itself. The m/m label is balanced in every window (53.7% / 50.3% /
48.6%).

## Numbers

- Reference points (rank AUC on the written rows): mean reversion 0.5659 eval / 0.6562 holdout -
  the bar to beat; momentum anti-predictive at 0.4161 / 0.3993; winter calendar 0.5473 / 0.5090.
- Runner-contract baseline: eval AUC **0.5526** (both independent paths, `CONTRACT OK`), below
  mean reversion - recorded as headroom, not a defect. See `VERIFICATION.md`.
- Publisher cross-check: August 2026 national Type 1 within-4h 61.1% (publisher commentary) vs
  60.86% recomputed on this panel.

## Corrections carried into this release

- The discovery panel probe had two defects (UTF-8 BOM handling dropped five whole months;
  the "Number of" column-name alias missed 24 pre-2020-04 months), which understated the panel
  at 97 months / 124 providers. The corrected panel - 102 months, 134 providers, 12,765
  qualifying provider-months - is what this artifact was built from, and the split figures
  published here are the corrected ones.
- `code/build.py` gained a fetch client ladder after the publisher's CDN was measured serving
  HTTP 202 with an empty body to datacenter IPs. None of that code ran in the build that
  produced this artifact (the worker consumed a staged, digest-verified copy); the artifact
  digests are unchanged. See `VERIFICATION.md` section 5.

## Known limits

- The source is a live register with monthly revisions; a rebuild after 2026-10-21 will not
  reproduce these digests.
- Booked-appointment columns exist only from 2020-08 and are therefore not shipped (they would
  be available in some splits and absent in others).
- No agent or harness comparison was run on this artifact.
