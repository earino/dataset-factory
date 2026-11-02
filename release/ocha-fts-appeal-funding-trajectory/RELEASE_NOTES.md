# Release notes - v2026.11

## ocha-fts-appeal-funding-trajectory (first versioned package)

Humanitarian-appeal funding-trajectory prediction: for a single-country
UN-coordinated appeal at its public launch instant, will it receive at least 50%
of its ORIGINAL launch-vintage requirements by the close of its plan year?
Built from OCHA's Financial Tracking Service (HPC API + HDX bulk CSV).
758 rows: train 2000-2016 (437/279), eval 2017-2020 (139/81), holdout 2021-2025
(182/96).

## What is in this version

- The rebuilt 9-column artifact `ac529cd4e9d4da90...` (gate 1.5.0, failed
  checks empty, exact-byte `--accept` on the worker, re-accepted after download
  in the baseline job).
- The P0 remediation: the 2026-11-01 independent queue audit recovered 120/139
  eval and 128/182 holdout labels exactly through the shipped prior-outcome
  features (`country_prior_appeals`, `country_prior_covered_rate`,
  `country_last_prior_covered`). Those columns no longer ship. Rows are
  unchanged vs the audited artifact; every remaining feature is a function of
  the row's own launch record, except `years_since_country_prior`, which reads
  only prior appeal YEARS and is asserted label-free at construction.
- The measured comparison on the identical 139 eval rows: stock runner
  **0.6452** vs persistence **0.7171** (and prior-mean 0.7143, ask-size 0.7126,
  country-history 0.6729, plan-type 0.6692, majority accuracy 0.5827). The
  model trails persistence by 0.0719 AUC: **no demonstrated headroom under this
  protocol for the stock runner**, recorded as a defect beside the number, with
  the information-asymmetry note (the model is deliberately denied the last
  prior same-country outcome under the P0 standard; the persistence reference
  reads it scorer-side from prior-in-time labels). A solver must beat
  `persistence_last_coverage` for any headroom claim.
- Licence: MIT (our code/docs), CC0-1.0 (our compilation contribution), source
  terms preserved (FTS use-and-republish + CC BY-IGO on the HDX bulk input) with
  attribution carried; see `LICENSE.md`.

## Known limitations (disclosed, not hidden)

- **Current-vintage retrospective.** The FTS API exposes no historical vintages,
  so no as-of reconstruction is claimed; `quality.json`'s `evaluation_contract`
  declares `isolated_rows` access and a restricted retrospective-research scope.
  Labeled eval is development/validation; the holdout is final scoring and was
  never evaluated in this package's preparation.
- **Flow totals vs the CSV.** 37/758 rows differ between the flow endpoint's
  year total and the HDX CSV's funding column (the disclosed count); flow and
  CSV agreed to the dollar on the retained fixtures, and the cross-check runs
  on every row at construction with a 10% guard.
- **Small panel.** 139 eval rows (81 positives) across 51 countries; four eval
  years. Intervals are not the point of the headline number - the comparison
  and its scope are recorded beside it.
- **Predecessor note.** The same runner measured 0.6298 on the pre-rebuild
  12-column artifact; removing the leaky features slightly improved the model
  while closing the recovery channel.

## Provenance

Construction commit, input digests, worker job IDs, the gate report and the
baseline evidence are recorded in `MANIFEST.json` and `VERIFICATION.md`. The
holdout ships as a release asset like the other splits; during evaluation runs
it stays outside the evaluated agent's workspace.
