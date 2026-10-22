# Verification record

Built 2026-10-22 from the complete ABS OAD_COUNTRY panel via the ABS Data API: 59,452 observations,
428 months (1991-01 .. 2026-08), 70 series, 0 missing values.

| Measure | Value |
| --- | --- |
| Gate | 1.4.0, 38/38 checks, 0 failed |
| Artifact | `afb46c6b29e6c4aa...` |
| Splits | 19,071 (34.96%) / 4,140 (29.08%) / 3,920 (19.59%) |
| Excluded | pandemic 2020-01..2021-12 (1,662 rows); 224 without history; 10 unobserved targets |
| Baseline | **0.6219** eval AUC, both paths, `CONTRACT OK` |
| References | identity 0.5720, calendar 0.5501, persistence 0.3647 |
| Dependencies | xgboost 3.4.1, scikit-learn 1.9.1, pandas 2.3.3, numpy 2.5.4 |

Timing: the panel is gated on the publisher's release calendar, so every feature for month M exists
when M is published, and the target month is not published at that instant. Provenance checks
confirm the extract mixes only the 06/05 country series and the TSEST=10 original series, so no
seasonally-adjusted stream can leak into the features.

Known events land where they should: the 2020 border closure produces a 92.5% down-share and the
2022 reopening a 97.7% up-share, against a 75% threshold.

Not covered: no agent harness comparison; the holdout was not scored by the baseline; the source is
revised monthly, so a later rebuild will not reproduce these digests.
