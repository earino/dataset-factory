# Verification record

What was run, on what, and what it does not cover. Every number below is measured; the command
that produced it is named beside it.

**This is the v2026.12 rebuild (build c).** It replaces v2026.11 (`0990af0f90fbe304`) and
v2026.10 (`9903df974f233dfa`). An independent audit on 2026-10-21 found v2026.10 had a temporal
defect (features published after the claimed instant) and hindsight selection (M+1 attendance and
a whole-snapshot history count); a re-audit the same day found v2026.11 still let a volume-qualified
target month decide whether a row existed. Both are fixed here.

**How this rebuild came to exist.** The first v2026.12 attempt (2026-10-21 15:26Z) fixed the rule
but shipped an internally inconsistent package: its `qualification.json` carried per-file digests
(train `b5f2721d...`, eval `b2519cba...`, holdout `4d837f39...`) that matched no shipped bytes -
`qualify_dataset.py --accept` refused the package. This rebuild ran the committed `build.py`
(construction commit `efb8191`, which also corrected the module docstring and
`PREDICTION_QUESTION` to the M-only rule; no data-path change), regenerated the artifact from the
same 102 publisher CSVs (source composite sha256 `99cb3339...`, unchanged), re-ran the gate over
the exact bytes that ship, and re-ran the baseline on those bytes. The three CSVs came out
byte-identical to v2026.11's; `meta.json` and `quality.json` differ (rebuilt timestamps and the
corrected question text).

## Artifact identity

| File | Bytes | Sha256 |
| --- | ---: | --- |
| `public/train.csv` | 1,664,506 | `55af812900519d39b5a294c38c76f554ed67f0aeb721862592b4d3c588ea7430` |
| `public/eval.csv` | 1,246,633 | `cb786792ac321dd851c272bd159fed24e13d6b633276606b294ddc976e72f266` |
| `private/holdout.csv` | 1,099,411 | `527a385f12a920b019434c70588c6532af1bd4dd5459eb64ed46809b5ef99b70` |
| `meta.json` | 3,579 | `196d300ec0c6b7fc3e8b04809019f075c2d2f93a76bdc66d2b26cdd08122aadc` |
| `quality.json` | 6,679 | `0fb29a658ac5d097994534177de60a463b46fe8cf0adac37f3ec742a40690256` |

Artifact version **`d871b45b667448a1...`** (`MANIFEST.json.artifact_version`), built
2026-10-21T18:06:51Z on the coordinator from the 102 publisher CSVs fetched over HTTP
(source composite sha256 `99cb3339b31ae204...`). The CSVs are byte-identical to v2026.11's, whose
labels an earlier audit reconstructed (11,457 in agreement), so that finding carries over to these
bytes.

## 1. Qualification gate

- Command: `python3 skills/dataset-qualification/scripts/qualify_dataset.py
  <task-dir> --report qualification.json`, gate **1.4.0**, over the full artifact (9,549 rows):
  `QUALIFICATION PASSED`, `ok: true`, 0 failed checks.
- Re-acceptance on the package bytes:
  `qualify_dataset.py --accept release/nhs-ae-four-hour-decline/qualification.json
  release/nhs-ae-four-hour-decline` -> `ACCEPTED: ... matches the qualified artifact
  d871b45b667448a1` (2026-10-21 evening). The same command on the 15:26 package refused it -
  that refusal is what surfaced the stale report.
- The gate includes the five timing checks added after the first audit:
  `timing.instant_declared` (kind `publication`, citation present),
  `timing.publication_lag_measured` (three observed `period_end -> published` pairs:
  2026-06-30 -> 2026-07-09, 2026-07-31 -> 2026-08-13, 2026-08-31 -> 2026-09-10),
  `timing.features_available_at_instant` (13d <= 13d, the **maximum** observed lag),
  `timing.instant_accounts_for_publication_lag`, and
  `timing.selection_uses_only_available_data` (`latest_period_used: M`).

## 2. Response to the 2026-10-21 audits

| Audit finding | Disposition |
| --- | --- |
| 25 features carry month-M values published 9-13 days after month end | **Fixed.** The instant is the publication date, using the **maximum** observed lag (13 days), not a mean or a fixed 10: NHS published 9, 13 and 10 days after the period end in June, July and August 2026. All three observations ship in `quality.json`. No feature changed; the claim about when they exist did. |
| Eligibility used M+1 attendance and a whole-snapshot >=24-month count | **Fixed twice.** The v2026.11 fix removed the whole-snapshot count but still built the pair list from volume-qualified months, so the target month still decided membership - the re-audit caught it at `build.py:634-642`. The rule is now: the provider has 24 volume-qualified months at or before M, and month M qualifies. The target month is looked up only to compute the label; if it is absent the row is counted as `unobserved_target` (134 provider-months), which is missing outcome data, not exclusion. 129 providers ship from 142 candidates. |
| `rate_delta_1m` documented with the wrong sign | **Fixed.** The build reports both directions: `momentum_auc` (`rate_m1 - rate_m`) 0.4161 eval and `reversal_auc` (`rate_m - rate_m1`, the shipped column) 0.5839. The README table names both and says the column is a reversal signal. |
| Baseline loses to persistence and a calendar prior | **Fixed by publication.** Persistence (`rate_m`) 0.5758 / 0.6046 and a train-only target-month prior 0.6027 / 0.5294 ship as references, alongside mean reversion and the winter rule. The baseline is 0.5511 and is stated to be below all of them. |
| Holdout labels ship | **Disclosed, unchanged.** The holdout is labelled by design; blind evaluation needs isolation, which `REPRODUCE.md` states. |
| Docs: "public/no credentials", checksum paths, downloader | **Fixed.** `README.md` and `REPRODUCE.md` describe the private staging and the correct paths. |
| Docs: `build.py`'s docstring and `quality.json`'s question still described the pre-fix M+1 volume gate | **Fixed in this rebuild** (construction commit `efb8191`): the module docstring, `PREDICTION_QUESTION` and the generated `quality.json`/`meta.json` question text now state the M-only rule. The 15:26 package enforced the fix in code while its shipped question text still described the pre-fix population. |

## 3. Timing and frame self-checks (from the build)

- Truncation self-check: **204 rows** recomputed against a panel copy physically truncated at
  month M - **0 mismatches**. Any accidental future-month access would fail this check.
- Selection self-check: eligibility is counted from the provider's history at M; the build
  records `skipped.insufficient_history = 3,152` and `skipped.unobserved_target = 134`, so the
  retained population is auditable from `summary.json`.
- Duplicate `row_id` values: **0**.
- Publisher cross-check: panel August 2026 volume-gated Type 1 within-4h rate **60.86%** against the
  publisher's **61.1%**; the difference is revised-vs-provisional publication states.

## 4. Runner-contract baseline

Re-run on the exact shipped bytes (build c) with the contract's dependency ranges, on the
coordinator (the harness runner files are shipped verbatim and were not edited):

| Measure | Value |
| --- | --- |
| `train.py` Eval AUC | **0.5511** |
| `validate.py` independent predict_proba AUC | **0.5511** |
| Contract line | `[validate] CONTRACT OK` |
| Dependencies | python 3.14.7, xgboost 3.4.1, scikit-learn 1.9.1, pandas 2.3.3, numpy 2.5.4 |

Command: `sh baseline/reproduce_baseline.sh .` from the package root (exit 0). The identical
0.5511 was measured on the byte-identical v2026.11 CSVs under python 3.13.16.

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
- **The build ran on the coordinator, not a worker.** The publisher's CDN serves HTTP 202 with an
  empty body to datacenter IPs (measured on worker job nhsae-001), so no worker can fetch this
  source; the fetch, gate and baseline all ran on the coordinator class that hosts the factory.
- The gate proves the artifact lacks the defects it can see. It cannot read `code/build.py` and
  verify that the row selection matches the declaration; that is what the independent audit is
  for. A third audit pass - focused on the counterfactual the re-audit used (change only a target
  month's attendances and confirm the row survives) - is commissioned before the flip.
- Provider organisational changes are carried as-is by the publisher's Org Code.
