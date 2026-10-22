# Verification

What was run, on what bytes, and what it does **not** cover. Every number below was read
back from collected job results and fetched reports, not from a console.

## 1. Artifact identity and the gate

- Built by worker job **tsb-004** (server 171730217, cx23/hel1, 31.1 s, exit 0) from the
  RODS vintage of 2026-10-21 (five source CSVs, per-file sha256 in `meta.json` and
  `measurements.json`; 157,183,629 bytes fetched on the worker - never on the
  coordinator).
- Qualification gate **1.4.0** ran on the **full artifact** on the worker:
  **37/37 checks, 0 failed** (leakage over shipped columns, prediction timing, units and
  reference frames, temporal splits, runner compatibility). The report ships as
  `qualification.json`; artifact version `e75a59bb1116e39b...`.
- Re-verified at packaging: the report's five artifact sha256s (train/eval/holdout/
  meta/quality) were re-matched against the staging release manifest's asset digests, and
  the baseline job re-accepted the exact fetched bytes through
  `qualify_dataset.py --accept` before any scoring
  (`ACCEPTED: /data/extract matches the qualified artifact e75a59bb1116e39b`).

## 2. Label and publisher cross-checks (measured in-build)

- Label integrity: `InjuriesIND` and the fatal+serious+minor totals agree on all 1,624
  positive panel rows (0 disagreements either way); the separate INJURIES child table
  corroborates all 1,624. Label source columns are excluded from every shipped file.
- Publisher cross-check: panel year 2025 counts 832 ACCIDENT vs 831 in TSB's own 2025
  annual summary and 331 INCIDENT vs 332 - within 0.3%.
- Panel bookkeeping: 70,706 occurrences parsed; 139 byte-identical exported duplicates
  dropped; 56,865 pre-window and 109 post-window rows excluded; 7 non-identical
  `occ_no` collisions suffixed and pinned (`expected_duplicate_ids: 13`,
  `id_columns_are_entity_keys: false`).
- Coordinate frame: measured three-encoding decode (ddmm.ff / x10^3 / x10^6; 0
  ambiguous, 0 undecodable over a 3,088-value window); frame check on the written rows:
  0 of 13,732 values outside the Canadian envelope.

## 3. The baseline triad (identical eval rows)

All three were measured on the same artifact; the first two at construction on the
written rows (rank AUC), the third through the runner's contract on the fetched,
digest-verified, gate-re-accepted bytes (worker job **tsb-baseline-001**, server
171753063, 73.7 s, exit 0):

| Reference | Eval AUC | Holdout AUC |
| --- | ---: | ---: |
| Persistence analogue (trailing-12-month casualty rate) | 0.5270 | 0.4952 |
| Best single context column (`activity_type`) | 0.7070 | 0.6987 |
| **Full model (XGBoost via the runner contract)** | **0.8126** | not scored |

`train.py` printed 0.8126 and `validate.py`'s independent predict_proba recompute
printed 0.8126 - zero disagreement - with `[validate] CONTRACT OK`. The runner files
ran unmodified (bundled sha256 equal the benchmark's declared hashes:
`train.py a3c6bcf1...`, `validate.py b597e7f8...`, `validate.sh 3f06ca48...`).
Dependencies on the worker: python 3.13.17, pandas 2.3.3, numpy 2.5.4, xgboost 3.4.1,
scikit-learn 1.9.1. The private holdout was never copied into the workdir and was not
scored by anything. The model clears the persistence analogue by +0.286 and the best
single column by +0.106: the pre-onset context carries real signal, and the
persistence-dominance failure mode is absent.

## 4. Download path executed

`get_dataset.py` was executed end-to-end against the private GitHub release of this
package (token download through the API asset-id path, all five assets, every digest
verified, runner layout restored, exit 0) and `qualify_dataset.py --accept` re-verified
the downloaded tree. Once the release is public the same script runs anonymously.

## 5. What is not covered

- **No agent or harness comparison was run, and none is implied.** The 0.8126 baseline is
  a single XGBoost pass through the runner contract - the floor a solver inherits, not a
  statement about coding-agent performance.
- **The holdout AUC is deliberately not measured.** The holdout exists to be scored
  against future solutions; quoting its AUC here would spend it.
- **Only the current RODS vintage exists.** TSB republishes monthly and does not expose
  historical vintages, so a true point-in-time reconstruction of what was knowable at
  each occurrence date is not performable; features are stated as current-vintage with
  the vintage pinned by sha256 in `meta.json`. ReportedDate/ReportedTime (which post-date
  onset) are excluded from the shipped columns, so no shipped field depends on the
  notification lag.
- **Per-year label drift is a property of the source**, not a construction fault: the
  casualty rate falls from ~30% (1980s) to ~11-14% (2016-2026) as reporting and safety
  changed; the panel start and split windows are pinned to the modern regime.
