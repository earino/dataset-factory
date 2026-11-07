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
reason, issue month/weekday) plus recency derived only from strictly earlier
advisories' **issue dates** at the same site or county. The label (`lift30`)
comes from the removal date, which can only be observed after issuance, and
the label source columns are absent from the shipped files.

- **Artifact version:** `{ARTIFACT_VERSION}`
- **Version tag:** `{RELEASE_TAG}` (use this revision for reproducibility)
- **Rows:** {ROWS_TOTAL} advisory rows across three disjoint temporal splits
- **GitHub counterpart:** {GITHUB_REPOSITORY}

This version (v2026.12) is a corrected re-release: the independent audit of
the staged v2026.10 recovered eval and holdout labels **exactly** from eight
outcome-derived history columns (cumulative-count x rounded-rate arithmetic and
subtraction), so none of those columns ships here. The frame is 11 columns of
issuance attributes and issue-date recency; the register, population and
splits are unchanged, and the same stock runner scored within 0.002 AUC of
its v2026.10 result, so the integrity repair traded away no measured model
signal.

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
| Full model (stock XGBoost baseline, job ns-bwa-baseline-002) | 0.5068 | not recomputed for this frame |
| Site persistence: as-of prior lift30 rate (register-side reference, not a shipped feature) | **0.6124** | 0.2819 |
| Calendar/identity prior (county x issue month, train-estimated) | 0.5075 | 0.3101 |
| Reason prior (train rate per normalised reason) | 0.4307 | 0.2440 |
| Majority-class accuracy on this split | 0.6048 | - |

Site persistence covers 231 of the 372 eval rows (62.1%; global train-rate
fallback on the rest). Paired bootstrap on the same rows (1000 resamples):
persistence vs calendar **+0.1014** [0.0144, 0.1739] - excluding zero.

**Finding: no demonstrated headroom over persistence under this protocol.** The
stock baseline trails the one-line site-persistence rule by **0.1056** AUC and
sits at the calendar-control level - a recorded defect, not an encouraging
result - and this comparison is carried beside every figure in
`measurements.json`, RELEASE_NOTES.md and VERIFICATION.md. No
model-vs-persistence interval was recomputed for this frame; on these same eval
rows the superseded v2026.10 diagnostic measured the analogous deficit with
row-level and site-clustered intervals both excluding zero, and the observed
gap here is larger. Persistence dominates in every eval issue year
(0.6084 / 0.6203 / 0.5991) while eval prevalence shifts 74.4% -> 64.0% ->
41.5% across 2018-2020 (the measured COVID-era duration regime: mean advisory
duration 47-65 days in 2009-2018 vs 218 days in 2020). One stock model
trailing persistence does not establish that no solver can beat it; that
remains the benchmark's open question. The holdout was never scored and stays
sealed.

## Timing, honestly stated

The prediction instant is the **advisory's issue date** (an event-time
instant): every shipped feature is an issuance-time attribute or reads
strictly-earlier same-site/county **issue dates**, and no shipped column reads
any row's removal date - the label source columns are absent from the shipped
files, asserted by the gate. The register publishes one **revised-in-place
current vintage with no historical vintages** (pinned register sha256
`60f77ac4...`, content current as of 2026-06-16), so training-label timing and
full-row historical availability are **unverified**; the evaluation contract is
**retrospective research over the pinned snapshot**, never a certified
point-in-time reconstruction and never an operational-forecasting claim.
**Isolated rows** - one row presented to the solver at a time - remains the
declared design intent of this row-per-advisory artifact; the shipped
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
- Construction: `code/build.py`, executed by worker job `ns-bwa-002`
  (byte-identical re-fetch of the discovery vintage); qualification gate 1.5.0,
  44/44 checks on the full artifact, exact-byte acceptance before any figure
  was computed. Baseline job `ns-bwa-baseline-002` re-accepted the fetched
  bytes before scoring and printed eval AUC 0.5068 from both implementations
  (`[validate] CONTRACT OK`).

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
