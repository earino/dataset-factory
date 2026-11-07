# Nova Scotia boil water advisory lift-within-30-days (ns-bwa-advisory-lift-duration)

A binary prediction task built from the Nova Scotia boil water advisory register
(Open Data Nova Scotia, Socrata dataset 7t68-9xmm), published under the Open
Government Licence - Nova Scotia v1.1.

**Question.** At the moment a boil water advisory is issued for a public
registered or municipal drinking water supply in Nova Scotia - knowing then the
site name, county, facility type, reason for the report, calendar season, and
how recently the same site and county last had an advisory (computed only from
earlier advisories' **issue dates**) - will the advisory be **lifted within 30
days**?

- **Prediction instant:** the advisory issue date (a calendar day,
  America/Halifax). Every shipped feature is a value fixed at or before that
  day: the issuing row's own register fields, derived calendar features, and
  site/county recency built only from advisories issued strictly earlier. The
  label window is the 30 days that follow the issue date; no part of the target
  window precedes the instant.
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

## What v2026.12 changes, and why

The independent pre-flip audit of the staged v2026.10 (2026-11-01) recovered
**196 of 372 eval and 286 of 884 holdout labels exactly, with zero errors**,
from eight shipped outcome-derived history columns (site/county prior-advisory
counts, resolved counts, lift30 rates, active flags) using cumulative-count x
rounded-rate arithmetic and subtraction. That channel is closed **by
construction** in v2026.12: none of those columns ships. The shipped frame is
**issuance attributes + issue-date recency only** - 11 columns, of which the
only cross-row content is `site_days_since_last` / `county_days_since_last`,
functions of other rows' *issue dates*, never of any removal date or label. The
gate asserts the label source columns are absent from every shipped file. The
population, splits and register vintage are unchanged by design (byte-identical
register; train 1,069/715, eval 372/225, holdout 884/514). The cost of closing
the channel was measured: the same stock runner scored 0.5086 on the v2026.10
19-column frame and 0.5068 on this 11-column frame - **-0.0018 AUC**.

Because the persistence feature no longer ships, the site-persistence
**reference** is recomputed register-side after acceptance (the register fetch
is asserted sha256-identical to the artifact's own vintage, so the reference
reads no information the artifact's construction did not). It is a comparison
figure, not a model input.

**Cross-row access posture.** The evaluation contract still declares
**isolated rows** - one row predicted without any other row - as the design
intent of this row-per-advisory artifact. The shipped illustrative runner does
**not** enforce this: it passes the whole eval feature table to the predictor.
No enforcement claim is made anywhere in this package; an evaluation that
wants the isolated-rows protocol must enforce it itself. Unlike v2026.10, no
shipped column reads another row's outcome, so the declared reverse-history
exposure of the superseded version (369 train / 56 eval / 217 holdout rows) no
longer exists in these bytes; whether any *new* cross-row channel exists in
the 11-column frame is exactly what the fresh adversarial audit must attack.

## Measured evidence (identical eval rows, after gate acceptance)

| Reference / model | Eval AUC (372 rows, 225 positives) |
| --- | --- |
| Full model - the illustrative stock XGBoost baseline, verbatim runner | **0.5068** |
| Persistence: the site's own as-of lift history (register-side reference; not a shipped feature) | **0.6124** |
| Calendar/identity prior (train rate per county x month, backoffs) | 0.5075 |
| Reason prior (train rate per normalised reason) | 0.4307 |
| Facility-type prior | constant scores, no ranking information |
| Majority-class accuracy on this split | 0.6048 |

The model trails persistence by **0.1056** on identical rows and sits at the
calendar-control level. Paired bootstrap (1000 resamples) on the same rows:
persistence - calendar +0.1014 [0.0144, 0.1739] (excludes zero); calendar -
reason +0.0779 [0.0072, 0.1492]; persistence - reason +0.1793 [0.1136,
0.2482]. No paired model-vs-persistence interval was recomputed for this
frame; on these same eval rows the v2026.10 per-row diagnostic measured the
analogous deficit at -0.1038 with row-level interval [-0.1693, -0.0357] and
site-clustered interval [-0.1706, -0.0383], both excluding zero, and the
v2026.12 observed gap is larger. Per issue year persistence holds 0.6084 /
0.6203 / 0.5991 while prevalence falls 0.744 -> 0.640 -> 0.415 (2018 / 2019 /
2020). Read this as: **no demonstrated headroom over simple persistence under
this protocol with the stock model** - a recorded defect, not an encouraging
result. It does not prove every competent model must lose; it says the
runner's own baseline does not demonstrate the task's discriminative claim
above simple references. The full tables are in `measurements.json` and
`RELEASE_NOTES.md`.

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
that accepted this exact artifact (gate 1.5.0, 44/44 checks, artifact version
`49bf4cfa427375c6b7bf90f85eb0330d78da0cc49197c119c396b6b7ea4c6144`); running
it re-verifies the shipped bytes. The baseline script runs the benchmark's own
`train.py` and `validate.sh` unmodified on the public splits.

## Provenance

- Source: [Boil Water Advisories - Open Data Nova Scotia](https://data.novascotia.ca/datasets/7t68-9xmm),
  Nova Scotia Department of Environment and Climate Change; register content
  current as of 2026-06-16, fetched 2026-11-07 by worker job ns-bwa-002
  (byte-identical to the discovery fetch and to the v2026.10 build).
- Licence: [Open Government Licence - Nova Scotia v1.1](http://novascotia.ca/opendata/licence.asp).
  This is a derived research dataset, not a Government of Nova Scotia product;
  see `LICENSE.md` for the three grants and the required attribution statement.
- Construction: `code/build.py` (from factory commit `0d36ffc`, the exact bytes
  the worker executed), `code/score.py` for the reference implementations.
- Reproduction: `REPRODUCE.md`; what was and was not verified: `VERIFICATION.md`.
- Suitability: `measured evidence and its scope` - see `VERIFICATION.md` and the
  suitability notice; the labeled eval split is development/validation data, and
  the holdout must stay outside agent development.
- This version supersedes the staged v2026.10 (`e8ed2a53...`), which remains
  private and pinned at tag `v2026.10` and is never published.
