# Release notes - v2026.11

Second release of **nhs-ae-four-hour-decline**: a binary provider-month prediction task on NHS
England A&E four-hour performance. **v2026.11 supersedes v2026.10**: an independent audit on
2026-10-21 found v2026.10 had a temporal defect (25 features carried month-M values published
about ten days after the claimed prediction instant) and hindsight selection (eligibility used
month M+1 attendance and a whole-snapshot history count). Both are fixed here; the v2026.10
assets remain under the `v2026.10` tag and must not be used.

## What ships

| Asset | Bytes | Sha256 (first 16) |
| --- | ---: | --- |
| `public-train.csv` | 1,664,506 | `55af812900519d39` |
| `public-eval.csv` | 1,246,633 | `cb786792ac321dd8` |
| `private-holdout.csv` | 1,099,411 | `527a385f12a920b0` |
| `meta.json` | 3,432 | `778b863389e2e653` |
| `quality.json` | 6,123 | `31600cdf1d166bd4` |

Artifact version `0990af0f90fbe304...`, gate **1.4.0**, `ok: true`, 0 failed checks. The five
files were built on the coordinator from the 102 publisher CSVs (the publisher's CDN serves
HTTP 202 with an empty body to datacenter IPs, so a worker cannot fetch it; see
`VERIFICATION.md` section 5). Eval and holdout bytes are unchanged from v2026.10; only training
rows a provider had not yet earned were removed.

## What changed from v2026.10

- **Prediction instant restated as the publication date** of month M's CSV, about ten days
  after month end (observed: the August 2026 file, period end 2026-08-31, was published
  2026-09-10). No feature changed; the claim about when they exist did. Gate 1.4.0 now refuses
  the old period-end claim.
- **Eligibility counts a provider's qualifying months at or before M.** 2,042 training rows a
  provider had not yet earned are gone (train 6,116 -> 4,074; providers 134 -> 141, because a
  provider now qualifies when it has history, not when it has a long future). Eval and holdout
  are byte-identical.
- `rate_delta_1m` documented with the correct sign: it is a **reversal** signal (0.5839 eval /
  0.6007 holdout), with momentum (its negation, 0.4161 / 0.3993) reported beside it.
- References shipped with the artifact: target-month-of-year prior, persistence, reversal,
  mean reversion and the winter rule. The runner-contract baseline (0.5511) is below every
  eval reference and the documentation says so.

## Task

Will a provider's Type 1 within-4-hour rate decline next month relative to this month, given its
monthly A&E series through this month? Splits are temporal on the target month: train
2019-01..2022-12, eval 2023-01..2024-12, holdout 2025-01..2026-09. 9,549 provider-months
(4,074 / 2,937 / 2,538) over 141 volume-gated providers.

A relative m/m label is used because every fixed standard threshold measured near-uniform
positive rates in recent years (<95% -> 99.9% of the holdout positive; <80% -> 95.8%): the
national standard deteriorated from ~83% (2018) to ~60% (2026), so a threshold label's base rate
drifts with the system itself. The m/m label is balanced in every window (55.5% / 50.3% /
48.6%).

## Numbers

- Reference points (rank AUC on the written rows): target-month prior 0.6027 eval / 0.5294
  holdout; reversal (`rate_delta_1m`) 0.5839 / 0.6007; persistence (`rate_m`) 0.5758 / 0.6046;
  mean reversion 0.5659 / 0.6562; momentum 0.4161 / 0.3993 (anti-predictive); winter calendar
  0.5473 / 0.5090.
- Runner-contract baseline: eval AUC **0.5511** (both independent paths, `CONTRACT OK`), below
  every eval reference - recorded as headroom, not a defect. See `VERIFICATION.md`.
- Publisher cross-check: August 2026 national Type 1 within-4h 61.1% (publisher commentary) vs
  60.86% recomputed on this panel.

## Corrections carried into this release

- The discovery panel probe had two defects (UTF-8 BOM handling dropped five whole months;
  the "Number of" column-name alias missed 24 pre-2020-04 months), which understated the panel
  at 97 months / 124 providers. The corrected panel - 102 months, 141 gated providers,
  12,834 qualifying provider-months under history-only selection - is what this artifact was
  built from, and the split figures published here are the corrected ones.
- `code/build.py` gained a fetch client ladder after the publisher's CDN was measured serving
  HTTP 202 with an empty body to datacenter IPs. In the v2026.10 build that code never ran
  (the worker consumed a staged, digest-verified copy); in this v2026.11 build it did - the
  102 CSVs were fetched over HTTP from the coordinator. See `VERIFICATION.md` section 5.

## Known limits

- The source is a live register with monthly revisions; a rebuild after 2026-10-21 will not
  reproduce these digests.
- Booked-appointment columns exist only from 2020-08 and are therefore not shipped (they would
  be available in some splits and absent in others).
- No agent or harness comparison was run on this artifact.
- The rebuild has not yet been re-audited by an independent party; it should be before the
  release is made public (see `VERIFICATION.md` section 5).
