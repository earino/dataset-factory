# Verification record

What was run, on what, and what it does not cover. Every number below is measured; the command
that produced it is named beside it.

**This is the v2026.11 rebuild.** It replaces the v2026.10 artifact
(`9903df974f233dfa`), which an independent audit on 2026-10-21 found to have a temporal defect
(features published about ten days after the claimed prediction instant) and hindsight selection
(the population chosen with month M+1 attendance and a whole-snapshot history count). Both are
fixed here, and the fix is described in section 2.

## Artifact identity

| File | Bytes | Sha256 |
| --- | ---: | --- |
| `public/train.csv` | 1,664,506 | `55af812900519d39b5a294c38c76f554ed67f0aeb721862592b4d3c588ea7430` |
| `public/eval.csv` | 1,246,633 | `cb786792ac321dd851c272bd159fed24e13d6b633276606b294ddc976e72f266` |
| `private/holdout.csv` | 1,099,411 | `527a385f12a920b019434c70588c6532af1bd4dd5459eb64ed46809b5ef99b70` |
| `meta.json` | 3,432 | `778b863389e2e65326168c3dbbc39e4683a9ec45c74f0052c70dc074e93bf03d` |
| `quality.json` | 6,123 | `31600cdf1d166bd4ae11189b2d1c7717ecb7abf418bc051a92be8c0b8f6c714b` |

Artifact version **`0990af0f90fbe304...`** (`MANIFEST.json.artifact_version`), built
2026-10-21T12:38:18Z on the coordinator from the 102 locally cached source CSVs.

Eval and holdout bytes are **unchanged** from v2026.10: the fix removes training rows that a
provider had not yet earned and changes no eval or holdout row. Eval and holdout label arithmetic
therefore carries over, and the audit's finding that 11,457 reconstructed labels agree still applies
to those splits.

## 1. Qualification gate

- Command: `python3 qualify_dataset.py release/nhs-ae-four-hour-decline --report qualification.json`,
  gate **1.4.0**, over the full artifact (9,549 rows).
- Result: `ok: true`, no failed checks. Shipment of `qualification.json` is required with the
  manifest.
- The gate now includes the five timing checks added after the audit:
  `timing.instant_declared` (kind `publication`, citation present),
  `timing.publication_lag_measured` (one observed `period_end -> published` pair),
  `timing.features_available_at_instant` (10d <= 10d),
  `timing.instant_accounts_for_publication_lag`, and
  `timing.selection_uses_only_available_data` (`latest_period_used: M`).

## 2. Response to the 2026-10-21 audit

| Audit finding | Disposition |
| --- | --- |
| 25 features carry month-M values published ~10 days after month end | **Fixed in the description and in the gate.** The prediction instant is now the publication date (observed: 2026-08-31 period end -> 2026-09-10 publication), stated in `README.md`, `DATA_DICTIONARY.md`, `quality.json` and `meta.json`. No feature changed; the claim about when they exist did. |
| Eligibility used M+1 attendance and a whole-snapshot >=24-month count | **Fixed in `code/build.py`.** `make_rows` counts qualifying months at or before M (`index + 1 < MIN_PROVIDER_MONTHS` skips the row) and no longer filters providers on total panel length. 2,042 training rows disappear; 3,144 row-candidates are skipped for insufficient history. Providers 134 -> 141 because a provider now qualifies when it has history, not when it has a long future. |
| `rate_delta_1m` documented with the wrong sign | **Fixed.** The build reports both directions: `momentum_auc` (`rate_m1 - rate_m`) 0.4161 eval and `reversal_auc` (`rate_m - rate_m1`, the shipped column) 0.5839. The README table names both and says the column is a reversal signal. |
| Baseline loses to persistence and a calendar prior | **Fixed by publication.** Persistence (`rate_m`) 0.5758 / 0.6046 and a train-only target-month prior 0.6027 / 0.5294 are now shipped references, alongside mean reversion and the winter rule. The baseline is 0.5511 and is stated to be below all of them. |
| Holdout labels ship | **Disclosed, unchanged.** The holdout is labelled by design; blind evaluation needs isolation, which `REPRODUCE.md` states. |
| Docs: "public/no credentials", checksum paths, downloader | **Fixed.** `README.md` and `REPRODUCE.md` describe the private staging and the correct paths. |

## 3. Timing and frame self-checks (from the build)

- Truncation self-check: **204 rows** recomputed against a panel copy physically truncated at
  month M - **0 mismatches**. Any accidental future-month access would fail this check.
- Selection self-check: eligibility is counted from the provider's history at M; the build records
  `skipped.insufficient_history = 3,144`, so the retained population is auditable from the summary.
- Duplicate `row_id` values: **0**.
- Publisher cross-check: panel August 2026 volume-gated Type 1 within-4h rate **60.86%** against the
  publisher's **61.1%**; the difference is revised-vs-provisional publication states.

## 4. Runner-contract baseline

Run on the coordinator with the contract's dependency ranges (the harness runner files are shipped
verbatim and were not edited):

| Measure | Value |
| --- | --- |
| `train.py` Eval AUC | **0.5511** |
| `validate.py` independent predict_proba AUC | **0.5511** |
| Contract line | `[validate] CONTRACT OK` |
| Dependencies | python 3.13, xgboost 3.4.1, scikit-learn 1.9.1, pandas 2.3.3, numpy 2.5.4 |

**Reference points measured at construction** (standard-library rank AUC on the written rows):

| Reference | Eval | Holdout |
| --- | ---: | ---: |
| Target-month-of-year prior (train only) | **0.6027** | 0.5294 |
| Reversal (`rate_delta_1m`) | 0.5839 | 0.6007 |
| Persistence (`rate_m`) | 0.5758 | 0.6046 |
| Mean reversion (`rate_m - rate_mean_6m`) | 0.5659 | **0.6562** |
| Winter calendar rule | 0.5473 | 0.5090 |
| Momentum (`rate_m1 - rate_m`) | 0.4161 | 0.3993 |
| Runner-contract XGBoost | 0.5511 | not scored |

The XGBoost pass sits below every eval reference. That is the honest state of this task: the label
is largely persistent and seasonal, and a competent solution has to beat 0.6027 on eval and 0.6562
on holdout to be interesting.

## 5. What this does not cover

- **No agent or harness comparison was run.** Nothing here says how well a coding agent performs.
- The holdout was **not scored** by the baseline.
- The source is a live register with a monthly revision cycle. A rebuild after 2026-10-21 picks up
  later and revised months and will not reproduce these digests.
- **The build ran on the coordinator, not a worker.** The audit reproduced the v2026.10 bytes from
  the published artifact; this rebuild has not yet been re-audited by an independent party. It
  should be before the flip.
- The gate proves the artifact lacks the defects it can see. It cannot read `code/build.py` and
  verify that the row selection matches the declaration; that is what the independent audit is for.
- Provider organisational changes are carried as-is by the publisher's Org Code.
