# Verification record

What was actually run, on what bytes, and what it does **not** cover. Every figure
quoted in this package is measured; the job that produced each one is recorded in
`measurements.json`.

## The artifact

The five shipped files are worker job **ipo-tm-004**'s output, constructed from the
pinned IPO snapshot (sha256 `3b6063bed36a78e8a04f10a5383f2881f4072a1be13e706a81ab097fb56ee571`,
63,238,846 B, Last-Modified 2018-02-13T13:19:48Z, one anonymous GET). `code/build.py`
(sha256 `70b8e634...`), `code/run.sh` (`39bd461b...`) and `code/score.py`
(`9f39ff5b...`) are the exact bytes the worker executed; `code/qualify_dataset.py`
(`4fab8a34...`) is the canonical gate 1.5.0. The construction is deterministic under
its `--built-at 2026-10-30T00:00:00Z` pin.

## What was verified, in order

1. **Qualification (full artifact, on the worker, before any figure existed).**
   Gate 1.5.0: **45/45 checks, 0 failed**, including the `event_time` timing block
   with its `administrative_record` feature evidence, the evaluation contract
   (retrospective research, isolated-rows design intent, training-label timing
   unverified), split windows disjoint with both classes in every window, leakage
   scans over every shipped column (mark text and postcode area reported as declared
   high-cardinality identifiers, not leaks), the in-file known-event fixtures
   (UK00000000001 'BASS & Co's PALE ALE' 1876; UK00003171385 'Brexit'; UK00003041794),
   and the runner contract. Gate `--selftest` passed before the launch (fixtures
   still bite).
2. **Exact-byte acceptance.** `qualify_dataset.py --accept` against the gate's own
   report: **ACCEPTED for artifact
   `2c1dade2913d0a8b643c89e628095a18e03223a6167beb9363316389486a544d`** on the worker,
   and re-ACCEPTED in the three later jobs (ipo-tm-baseline-001, ipo-tm-diag-001,
   ipo-tm-diag-002), each of which re-fetched the five files from private staging and
   verified every sha256 on arrival before running anything. The report ships as
   `qualification.json` (sha256 `33855b34...`).
3. **References (post-acceptance, identical eval rows).** Job ipo-tm-004's `score.py`:
   nice_class_rate 0.5421, mark_type_rate 0.5650 (dominant simple reference),
   owner_country_rate 0.5191, calendar_month_rate 0.4972, category_rate 0.5031,
   series_flag_rate 0.5213, majority-class accuracy 0.8399; persistence recorded
   not-applicable (every scored row is a new application). Per-filing-year reference
   tables computed for both eval years.
4. **Runner-contract baseline.** Job ipo-tm-baseline-001: the benchmark's own
   `train.py` + `validate.sh`, bundled verbatim (digests equal the read-only clone's:
   train.py `a3c6bcf1...`, validate.py `b597e7f8...`, validate.sh `3f06ca48...`),
   exit 0, `[validate] CONTRACT OK`; both eval AUC prints agree at **0.6224** on the
   97,274 eval rows. The holdout was never copied into any workdir (materialize.log
   in the job's evidence). Dependencies pinned: python 3.13.18, pandas 2.3.3,
   numpy 2.5.4, xgboost 3.4.1, scikit-learn 1.9.1.
5. **Per-row comparison (the decisive numbers).** Job ipo-tm-diag-002 (the fixed
   resampler relaunch; `--accept` re-run first, validate.sh re-checked CONTRACT OK,
   then per-row `predict_proba`): model - mark_type **+0.0574** [0.0533, 0.0605],
   model - nice_class **+0.0803** [0.0748, 0.0862], model - calendar **+0.1252**
   [0.1174, 0.1315] - all row-level paired bootstrap intervals (150 resamples,
   seed 31) **excluding zero**, `resampler_alignment_ok` true. Per filing year the
   advantage holds in both eval years (0.6233/0.6216 vs mark_type 0.5639/0.5660) with
   flat prevalence. A pandas second implementation replicated all 10 recorded
   reference figures exactly (`all_match` true). Model AUC 0.6224 measured four ways
   (sklearn 0.622376, midrank 0.6223756, train.py print, validate recompute); Brier
   0.1318.
   The precursor job ipo-tm-diag-001 produced **invalid intervals** (a
   positional-weight resampler defect that collapsed every difference to noise);
   they are preserved in `measurements.json` as the defect they were. Its point
   figures were unaffected, and diag-002's `per_row_scores.csv` is byte-identical
   to diag-001's (sha256 `380756fc...`) - the fix touches only the resampler.

## Suitability notice (version-bound, applies to v2026.10 / this artifact)

Retained for **retrospective model-development research**. The evaluation contract
declares `isolated_rows` as the artifact's design intent - one row is one application
with no cross-row features - while the shipped illustrative runner passes the whole
eval feature table to the predictor; unlike panel-shaped candidates this artifact
ships no history or aggregate features, and the gate found no cross-row exposure to
probe. The publisher exposes exactly one frozen snapshot (2018-02-13) and no
historical vintages, so training-label timing and full-row historical availability
are **unverified**; the vintage is the **frozen snapshot**; selection is at
prediction time (membership is fixed by the filing date, never by the outcome;
unresolved marks are censored and counted, which is outcome-observability
conditioning recorded as a limitation). Supported: retrospective research, method
comparison, agent evaluation with the labeled eval split as development/validation
and the holdout sealed. Not supported: operational/real-time screening claims,
point-in-time historical reconstruction, live filing-time prediction claims.
Structural qualification and baseline scores do not certify operational validity.

## What this does NOT cover

- **No agent or harness experiment** was run on this artifact; the baseline is a
  single XGBoost pass through the runner contract and says nothing about
  coding-agent outcomes.
- **The holdout was never evaluated.** It ships as an asset so a future frozen-design
  evaluation can use it; no holdout figure exists anywhere in this package.
- **No historical-vintage or operational claim.** One frozen snapshot exists; owner
  fields and class columns are snapshot-vintage (assignment can move ownership after
  filing, classes can be narrowed) - a declared uniform-vintage limitation.
- **The headroom finding is scoped**: row-level intervals only (no dependence cluster
  measurable from the shipped columns - tm_number is unique per row), one model
  configuration, no re-tuning, two filing years of eval coverage. Beating the
  measured rate references does not enumerate all simple rules and does not prove a
  causal signal.
- The baseline scope is eval-split only; per-year and Brier figures for the model
  come from the diagnostic job's per-row scores.
