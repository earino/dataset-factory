---
license: other
license_name: ogl-nova-scotia-1.1-source-plus-cc0-compilation
language:
  - en
pretty_name: Nova Scotia Boil Water Advisory Lift-Within-30-Days
size_categories:
  - 1K<n<10K
task_categories:
  - tabular-classification
tags:
  - tabular
  - public-health
  - water-quality
  - boil-water-advisory
  - event-outcome
  - temporal-split
  - survival-style
configs:
{CONFIGS_BLOCK}
---

# Nova Scotia Boil Water Advisory Lift-Within-30-Days ({RELEASE_TAG})

**Status: {STATUS_LINE}**

Nova Scotia publishes every boil water advisory the province has issued since
2006, with issue and removal dates, as an open register (Open Data Nova Scotia,
Socrata dataset 7t68-9xmm). **At the instant an advisory is issued, will it be
lifted within 30 days?** One row per issued advisory; the features are the
advisory's own issuance-time register attributes (site, county, facility type,
reason, issue month/weekday) plus as-of history derived only from strictly
earlier advisories at the same site or county. The label (`lift30`) comes from
the removal date, which can only be observed after issuance, and the label
source columns are absent from the shipped files.

- **Artifact version:** `{ARTIFACT_VERSION}`
- **Version tag:** `{RELEASE_TAG}` (use this revision for reproducibility)
- **Rows:** {ROWS_TOTAL} advisory rows across three disjoint temporal splits
- **GitHub counterpart:** {GITHUB_REPOSITORY}

## Splits

| split | rows | issue years | positives | positive rate |
| --- | ---: | --- | ---: | ---: |
| `train` | 1,069 | 2008-2017 | 715 | 66.88% |
| `eval` | 372 | 2018-2020 | 225 | 60.48% |
| `holdout` | 884 | 2021-2024 | 514 | 58.14% |

The splits are disjoint by issue year and ordered train -> eval -> holdout, with
both classes in every window. Advisories still active at the pinned register
vintage are censored, not labelled (2/1/10 per window plus 30 in 2025-2026,
outside the scored windows); the eligibility frame requires an issue date at or
before the vintage minus 30 days so an unresolved advisory cannot masquerade as
a negative. Three register rows with negative durations are excluded as
unverified outcomes. Advisory-site identifiers are constructed per row, so no
site-level identity crosses splits; `site_name` remains a shipped
high-cardinality feature because site recurrence is signal, not an entity key.

## Reference points

Measured on the identical 372 eval rows, after gate acceptance, through the
benchmark's unmodified runner (`train.py` + `validate.sh`, digests verbatim):

| Reference / model | Eval AUC | Brier |
| --- | ---: | ---: |
| Full model (stock XGBoost baseline, job ns-bwa-baseline-001) | 0.5086 | 0.3609 |
| Site persistence: as-of prior lift30 rate (`site_prior_lift30_rate`) | **0.6124** | 0.2819 |
| Calendar/identity prior (county x issue month, train-estimated) | 0.5075 | 0.3101 |
| Reason prior (train rate per normalised reason) | 0.4307 | 0.2440 |
| Majority-class accuracy on this split | 0.6048 | - |

Site persistence covers 231 of the 372 eval rows (62.1%; global train-rate
fallback on the rest). Paired differences vs the full model (1000 resamples,
seed 23, job ns-bwa-diag-001 which preserved per-row scores): model vs
persistence **-0.1038**, row-level 95% CI [-0.1693, -0.0357] and site-clustered
CI [-0.1706, -0.0383] (286 site clusters) - both EXCLUDING zero. Model vs
calendar is +0.0011 [-0.0866, +0.0723]: inconclusive, not parity.

**Finding: no demonstrated headroom over persistence under this protocol.** The
stock baseline trails the one-line site-persistence rule by 0.1038 AUC with
dependence-aware intervals excluding zero - a recorded defect, not an
encouraging result - and this comparison is carried beside every figure in
`measurements.json`, RELEASE_NOTES.md and VERIFICATION.md. Persistence
dominates in every eval issue year (0.6084 / 0.6203 / 0.5991 vs the model's
0.5554 / 0.5018 / 0.4886) while eval prevalence shifts 74.4% -> 64.0% ->
41.5% across 2018-2020 (the measured COVID-era duration regime: mean advisory
duration 47-65 days in 2009-2018 vs 218 days in 2020) and the model's Brier
degrades 0.23 -> 0.52. One stock model trailing persistence does not establish
that no solver can beat it; that remains the benchmark's open question. The
holdout was never scored and stays sealed.

## Timing, honestly stated

The prediction instant is the **advisory's issue date** (an event-time
instant): every shipped feature is an issuance-time attribute or reads
strictly-earlier same-site/county advisories, and no shipped column reads any
row issued on or after the scored row's issue date. The register publishes one
**revised-in-place current vintage with no historical vintages** (pinned
register sha256 `60f77ac4...`, content current as of 2026-06-16), so
training-label timing and full-row historical availability are **unverified**;
the evaluation contract is **retrospective research over the pinned snapshot**,
never a certified point-in-time reconstruction and never an
operational-forecasting claim. A measured cross-row exposure is declared rather
than hidden: a later advisory at the same site carries the earlier advisory's
lift30 outcome inside its as-of history rate whenever that prior is its only
resolved prior (the gate's own probes measured this reverse-history exposure
covering 369 train / 56 eval / 217 holdout rows), so honest evaluation requires
**isolated rows** - one row presented to the solver at a time. Isolated rows is
the **design intent** of this artifact's row-per-advisory contract; the shipped
benchmark validator passes the whole eval feature table to the predictor, so no
runtime enforcement claim is made anywhere in this package. Labeled eval is
development/validation; the holdout is the final test and stays outside
evaluated agents' workspaces.

## Source and provenance

- Boil Water Advisories register - Open Data Nova Scotia (Nova Scotia
  Department of Environment and Climate Change), Socrata dataset 7t68-9xmm;
  fetched as one anonymous CSV (283,987 bytes, sha256 `60f77ac4945c...`,
  Last-Modified 2026-06-16, 2,649 register rows, pinned vintage; full digest in
  `MANIFEST.json`).
- Construction: `code/build.py`, executed by worker job `ns-bwa-001`
  (byte-identical re-fetch of the discovery vintage); qualification gate 1.5.0,
  46/46 checks on the full artifact, exact-byte acceptance before any figure
  was computed. Baseline job `ns-bwa-baseline-001`; per-row diagnostic
  `ns-bwa-diag-001` (a second implementation replicated every reference figure
  to 4 decimal places).
- In-file fixtures asserted at build time: Maple Meadows (issued 2021-05-17,
  lifted after 307 days -> label 0, in holdout) and Canning (lifted after 1 day
  -> label 1, on the register but outside the scored windows).

## Licence

The source register is the Nova Scotia **Open Government Licence - Nova Scotia
v1.1** (free to copy, modify, publish, adapt and distribute for any lawful
purpose, including commercially, with attribution; the licence instrument is
linked from the dataset's own page and recorded in `LICENSE.md`). Attribution
carries through to every copy of the derived data: {SOURCE_ATTRIBUTION}. Our
contribution to the derived compilation is dedicated **CC0-1.0**; our code is
**MIT**. This is a derived research dataset, **not** a Government of Nova
Scotia product, and the Province has not reviewed or endorsed it. See
`LICENSE.md` for the full terms, attribution and citation.

## Use with the runner

```bash
python3 get_dataset.py --dest ./task
python3 code/qualify_dataset.py ./task
sh baseline/reproduce_baseline.sh ./task
```
