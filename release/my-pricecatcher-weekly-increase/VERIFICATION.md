# Verification record

Built 2026-10-22 from 36 monthly PriceCatcher files (2023-11 .. 2026-10), state of Johor.

| Measure | Value |
| --- | --- |
| Gate | 1.4.0, PASSED on the full artifact |
| Artifact | `06c5cd6f8a74aef9...` (see `MANIFEST.json`) |
| Splits | train 397,982 (14.9%) / eval 280,468 (17.5%) / holdout 154,279 (20.4%) |
| Unobserved outcomes | 143,978 (week W+1 with fewer than 3 observations) |
| Baseline | **0.7520** eval AUC, both paths, `CONTRACT OK` |
| References | item prior 0.5354, momentum 0.5001, reversal 0.4974, n_obs 0.4769 |
| Dependencies | xgboost 3.4.1, scikit-learn 1.9.1, pandas 2.3.3, numpy 2.5.4 |

Timing: the prediction instant is the end of week W; features are merges on week-7k keys, and the
build processes weeks in order, so no feature can read a later week. Eligibility is decided at W;
the outcome week is used only to compute the label.

Not covered: no agent harness comparison was run; the holdout was not scored by the baseline; the
source is revised monthly and a rebuild will not reproduce these digests.
