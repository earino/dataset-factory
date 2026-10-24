# Independent pre-publication audit — nz-ea-wholesale-price-exceedance (v2026.10)

Auditor: Codex (operator-commissioned, no contact with Scout, no dataset implementation reused).
Date: 2026-10-24. Scope: staged private release 422360451 / repo earino/nz-ea-wholesale-price-exceedance.
Holdout: opaque byte stream hashed and discarded; never decoded, fitted or scored.

## Verdict

WOULD NOT PUBLISH as a static batch benchmark. Integrity and all three reference AUCs
reproduce exactly; two independent train-only models reach 0.8954 / 0.8894, supporting
the ~0.89 performance scale; headroom over persistence remains inconclusive (corroborated).
The decisive defect: later eval feature rows expose earlier rows' target-source prices.
A label-blind shortcut achieves AUC 1.0 on the full eval set. Secondary defects: a wrong
documented week count (58 claimed vs 358 actual), and 14 eval targets crossing the declared
2022-11-01 regime break.

## Decisive finding — cross-row target-source exposure (CRITICAL FAIL)

The named target-source columns are absent from the public headers, but the source VALUES
are present as `last_day_mean` seven days later. For each eval row (island, D), the lookup
of (same island, D+7) in the eval features yields a price whose comparison against the
threshold matches 4,978/4,992 labels with zero mismatches; the 14 uncovered rows
(2022-10-25..31, whose future anchors are not in eval) score a constant 0.5 and happen to
be negative, so the full eval AUC is 1.0. No fitting, no holdout access, predictions
constructed before labels are read. Proof artifacts: shortcut_proof.py, shortcut-proof.json.

## Other findings

- References: persistence_value 0.8820357429258793, persistence_mean7 0.884293406215734,
  calendar_only 0.5010555946516537 — all reproduce exactly (two independent AUC
  implementations agree). Calendar reference falls back on 4,986/4,992 rows (almost
  constant by construction); an independent recurring island/month calendar reaches
  0.5354, so the calendar comparison does not demonstrate absence of seasonal signal.
- Independent models: xgb 0.8954313208844082, histgb 0.8894197502577614 (both train-only,
  plans fixed before eval metrics). Both inconclusive against persistence_mean7 under
  week clustering; xgb vs persistence_value is borderline (lower endpoint within Monte
  Carlo noise of zero).
- Week-clustered paired bootstrap corroborates "headroom not demonstrated"; moving-block
  (4/13-week) sensitivities also contain zero.
- VERIFICATION.md claims 58 distinct eval weeks; actual: 358 (356 full + partials of 6 and 2).
- 14 eval anchors 2022-10-25..31 target 2022-11-01..07, on/after the declared regime break.
- Train/eval share target week 2016-W01 (six rows) — event-cluster separation FAIL.
- Threshold (100) rationale cites 2020-06 sample and 2019/2020 prices while train ends
  2015-12-31 — training-window-only provenance NOT VERIFIED.
- Strict point-in-time causality NOT VERIFIED (first eval prediction 2016-01-07; 12 train
  labels publish after it under the same D+6 lag; no release-vintage evidence in artifact).
- Everything else audited PASSES: digests, counts, prevalence, grain/identity, calendar
  coverage, derived-feature consistency, no duplicate columns/rows, no single-column
  determiner (best one-column AUC 0.8843 = mean_7d).

## Required before any publication

An as-of evaluation interface that hides future covariate rows (or an equivalent
construction change), purged regime-boundary and shared-week edges, corrected evidence
documentation, and renewed headroom evaluation on the corrected artifact. Renaming
columns does not fix the leak.

Reproduction: Python 3.13, scripts fetch_assets.py / audit.py / bootstrap.py /
refine_week_bootstrap.py / shortcut_proof.py / verify_results.py / supplement.py /
write_report.py; machine-readable check-register.json, audit-results.json,
bootstrap-results.json, shortcut-proof.json.
