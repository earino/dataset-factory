# UK planning appeal outcome (pins-planning-appeal-outcome)

A binary prediction task built from the UK Planning Inspectorate's Casework Database
(GOV.UK bulk open data, the pinned 2026-10-22 edition), published under the Open
Government Licence v3.0.

**Question.** For a planning-permission-family appeal (PINS casework type `Planning
Appeal` or `Householder (HAS)`) validated by the Planning Inspectorate, will the final
decision be **Allowed** rather than **Dismissed** - predicted from only what is known
at validation: the casework type, LPA name and ONS code, received date, procedure,
development type, appeal reason fields, site descriptors and designation flags, and
LPA-level prior-outcome history computed strictly from decisions earlier than the
validation instant?

- **Prediction instant:** the appeal's **Valid Date** (`event_time`) - the instant PINS
  validates the appeal. Present on 100% of the 186,785 measured decided rows; received
  to valid is within 30 days for 85.9% of cases and valid to decision is 91-365 days
  for 74%, so the outcome window follows the instant. Every feature field is recorded
  at submission/registration and carries a publisher per-field data-quality grade.
- **Target:** `allowed` = 1 iff the publisher's Decision field is `Allowed`, 0 iff
  `Dismissed`. The Decision field and its date do not ship in any split.
- **Population:** decided s78_core appeals with a binary decision - 145,133 s78_core
  rows reduced by 2,757 non-binary decisions, 3,110 cross-file composite duplicates
  (2021 decisions appear in both publisher files) and 2 decided-before-validation rows,
  each counted, never silently dropped: **139,264 scored rows**. This is the
  publisher's own decided-cases-only population (in progress, withdrawn and turned
  away cases are not in the extract) - an outcome-conditioned population recorded as
  a property of the source.
- **Splits:** temporal split on the **validation instant** (the shipped `valid_date`
  column) because the outcome date cannot ship: train = validated before 2020-01-01
  (54,834 rows, 31.09% positive), eval = validated 2020-2021 (28,104 rows, 30.13%),
  holdout = validated on or after 2022-01-01 (56,326 rows, 31.43%, through
  2026-08-21). Disjoint windows, both classes in every window. Slow cases put a
  split's labels after the next split's earliest instants, so **training-label timing
  is UNVERIFIED** and the evaluation contract is retrospective research only.
- **Cross-row exposure, declared:** the LPA-history features embed other rows'
  labels (`lpa_last_outcome` is the previous same-LPA decided case's label verbatim).
  Honest evaluation therefore **requires isolated rows** - one row presented to the
  solver at a time. The shipped illustrative runner does NOT enforce this (it passes
  the whole eval feature table to the predictor); the requirement is stated as a
  requirement, never as an enforcement claim.

## Measured evidence (identical eval rows, after gate acceptance)

| Reference / model | Eval AUC (28,104 rows, 8,469 positives) |
| --- | --- |
| Full model - the stock XGBoost runner baseline, verbatim | **0.6108** |
| Procedure-type rate (train-fitted positive rate per procedure) | 0.5551 |
| LPA history rate (train-fitted rate per LPA, the named headroom reference) | 0.5414 |
| Shipped rate feature (the artifact's own `lpa_allow_rate_prior` column) | 0.5422 |
| Persistence (previous same-LPA decided case's outcome) | 0.5045 |
| Calendar-identity control | degenerate - collapsed onto the LPA rate exactly |
| Majority-class accuracy on this split | 0.6987 |

Paired differences (150 resamples, row-level and LPA-clustered bootstrap, job
`pins-planning-baseline-002`): model - procedure_type **+0.0558** [0.0467, 0.0626]
row / [0.0462, 0.0654] LPA-clustered; model - lpa_hist **+0.0694** [0.0622, 0.0766] /
[0.0597, 0.0792]; model - shipped_rate_feature **+0.0686** [0.0619, 0.0756] /
[0.0596, 0.0800]. Every interval excludes zero under both protocols: **demonstrated
headroom over every measured simple reference under this protocol** - an observed
result with recorded scope (one model configuration, no re-tuning; two validation
years of eval coverage; the calendar-identity control collapsed onto the LPA rate
because eval years have no train-era valid-year support, so it is recorded as a
collapsed control, not independent confirmation). Persistence is measured, not
declared not-applicable: 92%+ of eval rows' LPAs have a train-era decided-case history.

All figures were computed on a temporary worker after exact-byte acceptance of
artifact `c861bd8f4acd9bbe267bdb58e1168996fdb359c540aaf4030030a632d693c527` (gate
1.5.0 on the full artifact, failed_checks empty). The holdout was never read by any
scoring job and stays sealed. Labeled eval is development/validation evidence, never
an untouched final test.

## Layout

```
public/train.csv    train split   (validated before 2020-01-01)
public/eval.csv     eval split    (validated 2020-2021)
private/holdout.csv holdout split (validated 2022-01-01 onwards)
meta.json           runner descriptor
quality.json        qualification descriptor (timing, splits, evaluation contract)
code/               construction (build.py), the gate, references, run order
baseline/           the benchmark's own runner files + reproduction script
get_dataset.py      downloads the release assets, verifies digests, restores layout
```

GitHub release assets are flat (no `/` allowed); `get_dataset.py` restores the layout
above. `python3 get_dataset.py --dest ./task` does the download, digest verification
and layout in one step.

## Licence

Our code and documentation: MIT (`LICENSE-MIT.txt`). Our rights in the derived
compilation: CC0-1.0 (`LICENSE-CC0-1.0.txt`), scoped to our contribution only. The
underlying Planning Inspectorate Casework Database keeps its own designation and
remains subject to the Open Government Licence v3.0, whose attribution condition
carries through to every copy: *Contains public sector information licensed under the
Open Government Licence v3.0. Source: Planning Inspectorate Casework Database
(Planning Inspectorate), Casework_Database_-_2610.xlsx and
Older_Casework_Data_-_2610.xlsx, 2026-10-22 edition.* See `LICENSE.md` for the full
terms, scope, required attribution and the publisher's own data caveats. This is a
derived research dataset - not a Planning Inspectorate product.

## Provenance

- Source: the GOV.UK publication *Planning Inspectorate Casework Database*
  (https://www.gov.uk/government/publications/planning-inspectorate-appeals-database),
  2026-10-22 edition:
  `Casework_Database_-_2610.xlsx` (22,207,115 B, sha256
  `dff80bd0f17cbc640dc205009a9411269c8e58462b6df71af903c592af3c20fa`) and
  `Older_Casework_Data_-_2610.xlsx` (12,325,866 B, sha256
  `baf28d80c5cd5ad266f8a9e62c25517b2ec9d4c5d951239ab0638666bc092a4b`), two anonymous
  GETs. The build fails if these bytes change; the publisher republishes the rolling
  database monthly-to-quarterly, so the pin is the vintage.
- Constructed by worker job `pins-planning-002` (the single permitted rebuild after
  the first runner-contract failure; `--built-at 2026-10-31T00:00:00Z`); qualified by
  the same job with `code/qualify_dataset.py` (gate 1.5.0) and exact-byte accepted
  before any metric existed. The construction, baseline and diagnostic jobs all ran
  on temporary workers, since destroyed with provider receipts; the bulk bytes never
  passed through the small coordinator.
- Frame fidelity cross-checked in-build: the per-decision-year fixture reproduces the
  discovery probe exactly for all 11 decision years (kept + counted exclusions ==
  probe n; kept_allowed + excluded_allowed == probe allowed), and the flag columns'
  presence is verified by direct letter-based counts
  (`measurements.json`).
- The gate report for exactly these bytes ships as `qualification.json`.
