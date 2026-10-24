# Independent static-benchmark leakage audit — all ten published datasets

Auditor: Codex, operator-commissioned, 2026-10-24. No contact with Scout. Plan frozen
10:49:47 UTC before any eval download; rulebook, attack code and all 94 configurations'
predictions frozen 11:05:53 UTC before any label was opened; freeze hashes preserved by
the auditor. Label-blind construction throughout; holdouts never downloaded, opened,
decoded, counted or scored. Every AUC computed two independent ways (Mann-Whitney and
pair-counting), exact agreement. 376/376 public assets matched default-branch MANIFEST
digests. Bounded attack search: 15 active minutes per repository; not a security proof.
The auditor's full artifact bundle (PLAN.md, RULEBOOK.md, proof.py, results.json,
witnesses.json, PREDICTIONS-FROZEN.json, REPRODUCE.md) is held by the operator; this file
preserves the findings and the overall verdict.

## Verdict

SEVEN repositories FAIL as unrestricted static-batch benchmarks under the stated attacker
model. Six permit exact label recovery on large eval subsets (blind AUC 1.0, zero
mismatches); NOAA permits near-perfect ranking (AUC ~0.9993) from the future outcome day's
measurements, with explicitly nonzero errors against the official flag. Three receive
bounded PASS verdicts (no recovery found; not a proof that no stronger shortcut exists).

| Repository | Verdict | Covered / eval | Binary mismatches | Blind AUC |
|---|---|---:|---:|---:|
| austin-911-response | PASS, bounded | 75,300 / 285,665 | 25,154 | 0.6386 |
| abs-visitor-arrivals-direction | FAIL | 4,071 / 4,140 | 0 | 1.0 |
| chicago-doah-adjudication | PASS, bounded | 57 / 3,436 | 4 | 0.4732 |
| chicago-food-inspections, all 40 configs | FAIL | 22,309 / 35,358 | 0 | 1.0 |
| msha-enforcement-citations, all 45 configs | FAIL | 36,054 / 49,233 | 0 | 1.0 |
| my-pricecatcher-weekly-increase | FAIL | 264,956 / 280,468 | 0 | 1.0 |
| noaa-tide-flooding, temporal | FAIL, approximate | 88,915 / 89,038 | 423 | 0.99929 |
| noaa-tide-flooding, station-disjoint | FAIL, approximate | 29,889 / 29,930 | 191 | 0.99922 |
| tsb-railway-occurrence-casualty | PASS, bounded | 0 / 3,831 | n/a | undefined |
| who-flunet-activity-exceedance | FAIL | 6,022 / 6,831 | 0 | 1.0 |
| eutl-installation-net-short | FAIL | 14,731 / 24,322 | 0 | 1.0 |

## The defect class: the reverse-history lag join

Every decisive failure is later rows exposing earlier outcomes — not duplicate train
rows, not ID uniqueness (no exact non-ID feature row crossed train/eval in any
configuration). The label of row (entity, T) is a function of the outcome at T+horizon;
the shipped files also contain the row (entity, T+horizon), whose lagged feature columns
carry exactly that outcome:

- abs: (country, T+1) rows ship val_m / val_m12 — the two operands of T's label.
- chicago-food (all 40) and msha (all 45): a later inspection S with
  S.inspection_date − S.days_since_previous = T.inspection_date ships
  prev_target_cited — T's label — via the days_since_previous reverse-history join.
- my-pricecatcher: (premise, item, T+7) rows ship the prices whose comparison is T's label.
- who-flunet: (country, W+28 days) rows ship inf_all_w / denom_w — T's operands.
- eutl: (installation, t+1) rows ship net_short_l1 — T's label.
- noaa: (station, D+1) rows ship observed_max_ft for the outcome day (and the D+2
  margin_ft alternative still scores ~0.9993, so deleting the obvious column is not a fix).

Secondary findings: noaa's dictionary/build disagree on the day definition (build assigns
the official minFlag to date+1); food/MSHA ship joint labels.csv matrices whose
documentation says they include holdout outcomes (packaging concern; not used in the
attack); who-flunet has 44 shared country-years across splits (1,068 eval rows); several
datasets share calendar-week boundaries (measured, not used for FAIL verdicts).

## Minimum fix (auditor's words, accepted)

Prevent a solver from receiving any row or derived history that exposes another scored
row's outcome: evaluate chronologically with predictions locked before later features are
released, or rebuild a static test at a common information cutoff and purge
outcome-bearing later rows and lagged fields. Inspection suites must keep joint label
matrices outside solver inputs. NOAA additionally needs its day definition and
raw-max/official-flag distinction corrected. Version the rebuilt artifacts and repeat the
blind joins before treating scores as forecasting results.

## Reproduction

Standalone proof uses only the Python standard library and writes/hash-freezes
predictions before scoring; eight independent executions reproduced the principal
findings exactly. Per-dataset one-liners: `python3 proof.py <dataset> [--config <c>]`.
The full artifact bundle is with the operator; the machine-readable register
(results.json, configuration-results.csv, witnesses.json) is preserved there.
