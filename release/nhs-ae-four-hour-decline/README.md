# NHS England A&E four-hour performance month-over-month decline

**Task.** For an NHS England provider operating a consultant-led (Type 1) A&E department with at
least 100 Type 1 attendances in each of months M and M+1, will the provider's Type 1
within-4-hour performance rate **decline in month M+1 relative to month M**, given the
provider's monthly A&E series for all months through M, plus the calendar?

This is a binary provider-month prediction task built from NHS England's monthly provider-level
A&E statistics. It is a **derived research dataset**, not an NHS England product.

- **Prediction instant:** the **publication** of month M's monthly CSV, about ten days after month M
  ends (observed: the August 2026 file was published 2026-09-10). This is not the period end - at
  the end of month M those values did not yet exist. Every feature, and every eligibility test, uses
  provider months <= M only. The label is month M+1's within-4-hour rate versus month M's, published
  about a month after the prediction.
- **Target:** `declines = 1` iff `within4h_rate(M+1) < within4h_rate(M)`, where
  `within4h_rate(Y) = 1 - Attendances over 4hrs Type 1 / A&E attendances Type 1`. A relative
  month-over-month change is used because every fixed standard threshold measured near-uniform
  positive rates in recent years (<95% -> 99.9% positive in the holdout window; <80% -> 95.8%):
  the national standard deteriorated from ~83% (2018) to ~60% (2026), so the base rate's drift is
  a documented property of the phenomenon, not a construction choice.
- **Grain:** one row per (provider, target month M+1), keyed `row_id = <ORG CODE>-<YYYY-MM>`.
  Provider-months with Type 1 attendances < 100 in either month are excluded.
- **Splits:** temporal on the target month - train 2019-01..2022-12, eval 2023-01..2024-12,
  holdout 2025-01..2026-09.

## What is in the box

| File | Rows | Positive rate | Distinct positive providers |
| --- | ---: | ---: | ---: |
| `public/train.csv` | 4,074 | 55.5% | 114 |
| `public/eval.csv` | 2,937 | 50.3% | 124 |
| `private/holdout.csv` | 2,538 | 48.6% | 121 |

The label is balanced in every window by construction; the underlying four-hour rate is not
stationary (see `DATA_DICTIONARY.md`). Positives cluster within providers, so the distinct
positive provider count is the conservative independent-unit figure beside the row counts.

The holdout is published, so the task is reproducible. It must stay **outside an evaluated
agent's workspace** and be used only for scoring.

## Quickstart

```bash
python3 get_dataset.py --dest ./task        # 5 files, ~4.9 MB, sha256-verified
python3 code/qualify_dataset.py ./task      # the gate: expect ok=true, 0 failed checks
sh baseline/reproduce_baseline.sh ./task    # the benchmark's own train.py + validate.sh
```

## Reference points (the bar to beat)

Measured at construction on the written rows (standard-library rank AUC, single
prediction-time-safe features):

| Reference | Eval AUC | Holdout AUC |
| --- | ---: | ---: |
| Momentum (`rate_m1 - rate_m`) | 0.4161 | 0.3993 |
| Reversal (`rate_delta_1m`, the same signal read the other way) | 0.5839 | 0.6007 |
| Persistence (`rate_m`) | 0.5758 | 0.6046 |
| Mean reversion (`rate_m - rate_mean_6m`) | **0.5659** | **0.6562** |
| Target-month-of-year prior, train only | **0.6027** | 0.5294 |
| Winter calendar rule | 0.5473 | 0.5090 |
| Runner-contract XGBoost baseline | 0.5511 | not scored (see `VERIFICATION.md`) |

The strongest eval references are the target-month prior (0.6027) and reversal (0.5839); on the
holdout it is mean reversion (0.6562). Momentum is anti-predictive, and `rate_delta_1m` is that same
signal negated - a rising rate predicts a decline, which is why the two rows appear together. The
XGBoost contract baseline sits **below** every one of them on eval - recorded
as measured headroom information, not a defect.

## Prediction timing and leakage

The label source - month M+1's `A&E attendances Type 1` and `Attendances over 4hrs Type 1` - is
never written into any shipped file; only the binary `declines` ships. Month M's own
attendances, over-4-hour counts, decision-to-admit waits and emergency admissions ARE knowable
at the prediction instant and ship as features. The build recomputes a sample of rows against a
panel copy that physically contains no months after M and reports zero mismatches (201 rows
checked). Booked-appointment columns exist only from 2020-08, so they are parsed but not
shipped: their availability would be split-dependent.

## Licence and citation

The source statistics are NHS England / Crown copyright materials under the **Open Government
Licence v3.0**; the attribution condition carries through to every copy of the derived data.
Our contribution to the derived compilation is dedicated CC0-1.0; our code and documentation
are MIT. See `LICENSE.md`.

Attribute: "NHS England, A&E Attendances and Emergency Admissions (monthly provider-level
statistics). Contains public sector information licensed under the Open Government Licence
v3.0."

## Provenance

- Source: <https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/> -
  102 monthly provider-level CSVs (2018-04..2026-09), 3,115,779 bytes, composite sha256
  `99cb3339b31ae204...`, retrieved 2026-10-21.
- Cross-check against the publisher's own commentary: August 2026 national Type 1 within-4h
  61.1% (publisher) vs 60.86% recomputed on this panel at build time (revised-vs-provisional
  publication states).
- Construction: `code/build.py`, executed by job `nhsae-002`; artifact version
  `9903df974f233dfa...`, gate 1.3.0. Reproduction instructions in `REPRODUCE.md`.
