# Verification

What was run, on what bytes, and what it does **not** cover. Every number below was read
back from collected job results and fetched reports, not from a console.

## 1. Artifact identity and the gate

- Built by worker job **eutl-001** (server 171845011, cx23/hel1, 40.7 s, exit 0) from the
  Union Registry daily extract of 2026-10-22 (5,965,780 B panel GET, sha256
  1c7db552...; plus the EEA aggregate zip 10,794,107 B, sha256 9005e05f..., used only
  for the in-build cross-check; 16.76 MB fetched on the worker - never on the
  coordinator).
- Qualification gate **1.4.0** ran on the **full artifact** on the worker:
  **38/38 checks, 0 failed** (leakage over shipped columns, prediction timing, units and
  reference frames, temporal splits, runner compatibility). The report ships as
  `qualification.json`; artifact version `3540ad2180d8df8a...`.
- Re-verified at qualification: all six staging assets (five extract files plus the gate
  report) were re-downloaded on the coordinator, every sha256 matched the staging
  release manifest (420810883), and `qualify_dataset.py --accept` re-verified the
  collected bytes. The baseline job re-accepted the exact fetched bytes through
  `--accept` before any scoring
  (`ACCEPTED: /data/extract matches the qualified artifact 3540ad2180d8df8a`).
- A full coordinator dry run of build + gate **before** worker spend produced
  byte-identical CSVs (train `c7f23c55...`, eval `0d9f35d5...`, holdout `1c694e5e...`)
  to the worker's, so the shipped bytes were verified twice from independent runs.

## 2. Label and publisher cross-checks (measured in-build)

- Label integrity: the label reads two registry values (`VERIFIED_EMISSIONS(t)`,
  `ALLOCATION(t)`); both are excluded from every shipped file (asserted in-build against
  every written header), and the gate's single-column AUC sweep found no column at 1.0
  - the strongest shipped column is `margin_t` at ~0.90, the task's intended one-line
  rule. Exact ties are counted and labelled 0 (4,224 rows).
- Publisher cross-check: the shipped panel summed over exactly EEA activity codes
  {10, 20-99} (the EEA sheet carries per-activity detail AND aggregate rows - the sum
  must use that exact code set) matches the EEA's own EU ETS summary product:
  DE 2022 verified emissions exactly (361,145,695), DE 2023 within 4 t (rel 1.3e-8),
  DE 2022/2023 free allocation within 4.3e-4.
- Known-event fixtures asserted in-build on the shipped rows: (AT, installation 1,
  2005) net-long VE 41,399 < ALLOCATION 44,894; (2007) net-short VE 51,041 > 44,894;
  (2030) advance allocation 30,485 with no emissions; and the phase-3 allocation cut -
  eligible-row net-short rate 0.2472 (2012) -> 0.5783 (2013), gap 0.3311 (>= 0.25).
- Panel bookkeeping: 617,448 panel rows / 23,748 installations / 32 registries on the
  2026-10-22 snapshot; 16,709 insufficient-history rows excluded (all of 2005 plus each
  installation's first active year); 6,449 live 2026 rows (allocation published,
  emissions due 31 March 2027) kept out of the splits and countable as future rows;
  `EXCLUDED(t)=YES` on 81 of 204,914 in-frame rows, kept with the mix recorded
  (label 0/1 = 53/28).

## 3. The baseline triad (identical eval rows)

All three were measured on the same artifact; the first two at construction on the
written rows (rank AUC, rate tables estimated on train rows only), the third through
the runner's contract on the fetched, digest-verified, gate-re-accepted bytes (worker
job **eutl-baseline-001**, server 171847046, 41.3 s, exit 0):

| Reference | Eval AUC | Holdout AUC |
| --- | ---: | ---: |
| Calendar-only (registry x phase) | 0.5270 | 0.5708 |
| Identity-only (registry) | 0.5719 | 0.5708 |
| Persistence (t-1 net-position margin) | 0.8671 | 0.8789 |
| Announced-allocation rule (`margin_t` alone) | 0.8988 | 0.8881 |
| **Full model (XGBoost via the runner contract)** | **0.9199** | not scored |

`train.py` printed 0.9199 and `validate.py`'s independent predict_proba recompute
printed 0.9199 - zero disagreement - with `[validate] CONTRACT OK`. The runner files ran
unmodified (bundled sha256 equal the benchmark's declared hashes: `train.py a3c6bcf1...`,
`validate.py b597e7f8...`, `validate.sh 3f06ca48...`). Dependencies on the worker:
python 3.13.17, pandas 2.3.3, numpy 2.5.4, xgboost 3.4.1, scikit-learn 1.9.1. The
private holdout was never copied into the workdir and was not scored by anything.

Interpretation: the full model clears the persistence margin by **+0.0532**, so the
level target stands (no re-target to onset/transition needed). Most of the edge is the
announced-allocation margin rule (`margin_t` alone 0.8988); the full model adds
+0.021 over that rule. Per-year eval texture (written rows): 2020 rate 0.6713 /
persistence 0.9046; 2021 0.8075 / 0.8269; 2022 0.7582 / 0.8723. Persistence is
recorded beside every model number.

## 4. Download path executed

`get_dataset.py` was executed end-to-end against the private GitHub release of this
package (token download through the API asset-id path, all five assets, every digest
verified, runner layout restored, exit 0) and `qualify_dataset.py --accept` re-verified
the downloaded tree. Once the release is public the same script runs anonymously.

## 5. What is not covered

- **No agent or harness comparison was run, and none is implied.** The 0.9199 baseline is
  a single XGBoost pass through the runner contract - the floor a solver inherits, not a
  statement about coding-agent performance.
- **The holdout AUC is deliberately not measured.** The holdout exists to be scored
  against future solutions; quoting its AUC here would spend it.
- **Only the current registry vintage exists.** The Union Registry publishes a daily
  snapshot and does not expose historical vintages, so a true point-in-time
  reconstruction of what was knowable at each past surrender deadline is not performable;
  feature values are stated as current-vintage with the vintage pinned by sha256 in
  `meta.json`, and the timing claim is a documented assumption against the statutory
  registry calendar (verified emissions due 31 March, surrender due 30 April, year-t
  allocation fixed in advance).
- **Prevalence drift is a property of the ETS phases**, not a construction fault: the
  net-short rate rises from 45.53% (train 2006-2019) to 74.02% (eval 2020-2022) and
  72.20% (holdout 2023-2025) as the free-allocation share fell while the cap declined.
  A model trained on the early period faces an out-of-distribution eval window by
  design; per-year rates are in `measurements.json`.
- **`age_years` is left-truncated**: installations operating before 2005 have their age
  understated because the extract starts at the ETS's first year.
