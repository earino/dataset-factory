# Nova Scotia boil water advisory lift-within-30-days (ns-bwa-advisory-lift-duration)

A binary prediction task built from the Nova Scotia boil water advisory register
(Open Data Nova Scotia, Socrata dataset 7t68-9xmm), published under the Open
Government Licence - Nova Scotia v1.1.

**Question.** At the moment a boil water advisory is issued for a public
registered or municipal drinking water supply in Nova Scotia - knowing then the
site name, county, facility type, reason for the report, calendar season, and
the prior advisory history of the same site and county computed only from
earlier advisories - will the advisory be **lifted within 30 days**?

- **Prediction instant:** the advisory issue date (a calendar day,
  America/Halifax). Every shipped feature is a value fixed at or before that
  day: the issuing row's own register fields and derived calendar features, and
  site/county history features built only from advisories issued strictly
  earlier. The label window is the 30 days that follow the issue date; no part
  of the target window precedes the instant.
- **Target:** `lift30` = 1 if the advisory was lifted within 30 days of
  issuance, else 0, from the register's removal date / length columns
  (label-only; they are absent from the shipped files). Base rates: train
  66.88% (issue years 2008-2017), eval 60.48% (2018-2020), holdout 58.14%
  (2021-2024). Advisories still in effect at the vintage (blank removal date,
  publisher-documented censoring) are **excluded and counted per window**, never
  labelled as non-lifts; three rows with negative recomputed duration are
  excluded as invalid outcomes; 30 rows without a parseable issue date are
  excluded and counted.
- **Splits:** temporal on the issue year - train 1,069 rows / 715 positives /
  585 distinct sites, eval 372 / 225 / 286, holdout 884 / 514 / 547.
- **Vintage:** one pinned register vintage, content current as of 2026-06-16
  (CSV sha256 60f77ac4..., 2,649 rows). The publisher updates quarterly and the
  register is revised in place; a future re-fetch measures churn, not
  historical vintages. The task is declared **retrospective** on the pinned
  vintage; no historical operational-availability claim is made (see
  `quality.json`'s `evaluation_contract`).
- **Measured regime shift:** mean advisory duration ran 47-65 days (2009-2018)
  vs 218 days (2020), 143 (2021), 101 (2022), 64 (2023) - the holdout window
  straddles the spike, and within-eval prevalence falls 0.744 (2018) to 0.415
  (2020). This is a declared distribution-shift difficulty, not a construction
  fault.
- **Known cross-row exposure, measured and declared:** a later same-site row's
  `site_prior_lift30_rate` feature equals the earlier row's label when that
  prior is its only resolved one. The gate executed the declared probes across
  all splits (site-level reverse-history covers 369 train / 56 eval / 217
  holdout rows). The evaluation contract states **isolated rows** - one row
  must be predicted without any other row - as the row-wise design intent. The
  shipped illustrative runner does **not** enforce this: it passes the whole
  eval feature table to the predictor. Any real evaluation must enforce the
  restriction itself; unrestricted-access scores are not meaningful for this
  artifact.

## Measured evidence (identical eval rows, after gate acceptance)

| Reference / model | Eval AUC (372 rows, 225 positives) |
| --- | --- |
| Full model - the illustrative stock XGBoost baseline, verbatim runner | **0.5086** |
| Persistence: the site's own as-of lift history (`site_prior_lift30_rate`, a shipped feature) | **0.6124** |
| Calendar/identity prior (train rate per county x month, backoffs) | 0.5075 |
| Reason prior (train rate per normalised reason) | 0.4307 |
| Facility-type prior | constant scores, no ranking information |
| Majority-class accuracy on this split | 0.6048 |

Paired differences (bootstrap, 1000 resamples, seed 23): model - persistence
**-0.1038**, row-level interval [-0.1693, -0.0357] and site-clustered interval
[-0.1706, -0.0383] (286 site clusters) - **both intervals exclude zero**.
Model - calendar +0.0011 [-0.0866, +0.0723] (contains zero: the model sits at
the calendar control). Per issue year the model never beats persistence:
0.5554 / 0.5018 / 0.4886 vs 0.6084 / 0.6203 / 0.5991 (2018 / 2019 / 2020),
and the model's Brier degrades 0.23 -> 0.52 across the prevalence shift while
persistence holds 0.22-0.36. Read this as: **no demonstrated headroom over
simple persistence under this protocol with the stock model** - a recorded
defect, not an encouraging result. It does not prove every competent model must
lose: the persistence feature is shipped and agent-visible, so a solver that
starts from it enters at ~0.61, and the baseline-to-reference gap is part of
what an evaluated agent must discover. The full tables are in
`measurements.json` and `RELEASE_NOTES.md`.

## Layout

```
public/train.csv    labeled training rows       (agent-visible)
public/eval.csv     labeled evaluation rows     (agent-visible)
private/holdout.csv labeled holdout             (never copied into a workdir; the
                                                benchmark's score is holdout AUC)
meta.json           target, positive label, id columns, split description, counts
quality.json        the qualification descriptor the gate verified
```

## Use with the runner

```bash
python3 get_dataset.py --dest ./task
python3 code/qualify_dataset.py ./task
sh baseline/reproduce_baseline.sh ./task
```

`get_dataset.py` downloads the five release assets, verifies each digest and
restores the layout above. `code/qualify_dataset.py` is the qualification gate
that accepted this exact artifact (gate 1.5.0, 46/46 checks, artifact version
`e8ed2a53eaf0453c8ed52aea336edb994d888ad11e7b76f7898b663f017180a8`); running
it re-verifies the shipped bytes. The baseline script runs the benchmark's own
`train.py` and `validate.sh` unmodified on the public splits.

## Provenance

- Source: [Boil Water Advisories - Open Data Nova Scotia](https://data.novascotia.ca/datasets/7t68-9xmm),
  Nova Scotia Department of Environment and Climate Change; register content
  current as of 2026-06-16, fetched 2026-10-29 by worker job ns-bwa-001
  (byte-identical to the discovery fetch).
- Licence: [Open Government Licence - Nova Scotia v1.1](http://novascotia.ca/opendata/licence.asp).
  This is a derived research dataset, not a Government of Nova Scotia product;
  see `LICENSE.md` for the three grants and the required attribution statement.
- Construction: `code/build.py` (from factory commit `f8ba545`, the exact bytes
  the worker executed), `code/score.py` for the reference implementations.
- Reproduction: `REPRODUCE.md`; what was and was not verified: `VERIFICATION.md`.
- Suitability: `measured evidence and its scope` - see `VERIFICATION.md` and the
  suitability notice; the labeled eval split is development/validation data, and
  the holdout must stay outside agent development.
