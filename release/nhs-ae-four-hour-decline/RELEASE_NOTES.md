# Release notes - v2026.12

Third release of **nhs-ae-four-hour-decline**: a binary provider-month prediction task on NHS
England A&E four-hour performance. **v2026.12 supersedes v2026.11 and v2026.10.** An independent
audit found v2026.10 shipped a temporal defect (features published after the claimed instant)
and hindsight selection (M+1 attendance and a whole-snapshot history count); a re-audit found
v2026.11 still let the target month's attendance decide whether a row existed - the counterfactual
was a single provider-month (R0A 2022-03) whose row vanished when only the target month's
attendances changed. v2026.12 decides eligibility at M only. The superseded releases remain
under their tags and must not be used.

## What ships

| Asset | Bytes | Sha256 (first 16) |
| --- | ---: | --- |
| `public-train.csv` | 1,664,506 | `55af812900519d39` |
| `public-eval.csv` | 1,246,633 | `cb786792ac321dd8` |
| `private-holdout.csv` | 1,099,411 | `527a385f12a920b0` |
| `meta.json` | 3,579 | `196d300ec0c6b7fc` |
| `quality.json` | 6,679 | `0fb29a658ac5d097` |

Artifact version `d871b45b667448a1...`, gate **1.4.0**, `ok: true`, 0 failed checks,
`--accept` re-verified on the package bytes. The five files were built on the coordinator from
the 102 publisher CSVs (the publisher's CDN serves HTTP 202 with an empty body to datacenter IPs,
so a worker cannot fetch it; see `VERIFICATION.md` section 5). The three CSVs are byte-identical
to v2026.11's: on this snapshot the eligibility fix changes no shipped row - it changes what a
hypothetical edit to a target month could do to the population, and it makes that property hold
by construction instead of by accident.

## What changed from v2026.11

- **Eligibility is decided at M only.** A row for feature month M exists when the provider has
  24 volume-qualified months (>= 100 Type 1 attendances) at or before M and month M itself
  qualifies. The target month M+1 supplies the label and never decides membership; 134
  provider-months whose target month is absent from the register are counted as
  `unobserved_target` - missing outcome data, not exclusion. 129 providers ship, from 142
  candidates.
- **The prediction instant uses the maximum observed publication lag** (13 days; June, July and
  August 2026 were published 9, 13 and 10 days after their period ends), not a fixed 10.
- **The shipped question text now matches the enforced rule.** v2026.11's `quality.json` still
  described the population as "at least 100 Type 1 attendances in each of months M and M+1" -
  the pre-fix rule. The module docstring, the generated question and the README now state the
  M-only rule (construction commit `efb8191`).
- **The package's qualification report now describes the shipped bytes.** The first v2026.12
  attempt carried a report over mid-fix bytes that were never shipped; `qualify_dataset.py
  --accept` refused it, and this rebuild re-gated the exact bytes in the package.

## Task

Will a provider's Type 1 within-4-hour rate decline next month relative to this month, given its
monthly A&E series through this month? Splits are temporal on the target month: train
2019-01..2022-12, eval 2023-01..2024-12, holdout 2025-01..2026-09. 9,549 provider-months
(4,074 / 2,937 / 2,538) over 129 providers.

A relative m/m label is used because every fixed standard threshold measured near-uniform
positive rates in recent years (<95% -> 99.9% of the holdout positive; <80% -> 95.8%): the
national standard deteriorated from ~83% (2018) to ~60% (2026), so a threshold label's base rate
drifts with the system itself. The m/m label measures 55.5% / 50.3% / 48.6% in the shipped
windows - close to balanced, not guaranteed to be.

## Numbers

- Reference points (rank AUC on the written rows): target-month prior 0.6027 eval / 0.5294
  holdout; reversal (`rate_delta_1m`) 0.5839 / 0.6007; persistence (`rate_m`) 0.5758 / 0.6046;
  mean reversion 0.5659 / 0.6562; momentum 0.4161 / 0.3993 (anti-predictive); winter calendar
  0.5473 / 0.5090.
- Runner-contract baseline: eval AUC **0.5511** (both independent paths, `CONTRACT OK`),
  re-run on exactly these bytes - below every eval reference, recorded as headroom, not a
  defect. See `VERIFICATION.md`.
- Publisher cross-check: August 2026 national Type 1 within-4h 61.1% (publisher commentary) vs
  60.86% recomputed on this panel.

## Corrections carried into this release

- The discovery panel probe had two defects (UTF-8 BOM handling dropped five whole months; the
  "Number of" column-name alias missed 24 pre-2020-04 months), which understated the panel at
  97 months / 124 providers. The corrected panel - 102 months, 142 candidate providers, 12,835
  qualifying provider-months - is what this artifact was built from.
- `code/build.py` gained a fetch client ladder after the publisher's CDN was measured serving
  HTTP 202 with an empty body to datacenter IPs. In the v2026.10 build that code never ran (the
  worker consumed a staged, digest-verified copy); from v2026.11 on it did - the 102 CSVs were
  fetched over HTTP from the coordinator. See `VERIFICATION.md` section 5.

## Known limits

- The source is a live register with monthly revisions; a rebuild after 2026-10-21 will not
  reproduce these digests.
- Booked-appointment columns exist only from 2020-08 and are therefore not shipped (they would
  be available in some splits and absent in others).
- No agent or harness comparison was run on this artifact.
- This rebuild has not yet been re-audited by an independent party; a third audit pass focused
  on the re-audit's counterfactual is commissioned before the release is made public (see
  `VERIFICATION.md` section 5).
