# Release notes - v2026.10

## Nova Scotia boil water advisory lift-within-30-days

First packaged version of `ns-bwa-advisory-lift-duration` (artifact version
`e8ed2a53eaf0453c8ed52aea336edb994d888ad11e7b76f7898b663f017180a8`, gate 1.5.0,
46/46 checks, exact-byte accepted on the worker).

**What the task is.** At the moment a boil water advisory is issued for a
public registered or municipal drinking water supply in Nova Scotia - knowing
the site name, county, facility type, reason for the report, calendar season
and the prior advisory history of the same site/county computed only from
strictly earlier advisories - will it be lifted within 30 days? The register is
the only public Canadian per-advisory channel with lift dates found at
discovery (sibling provinces either lack lift dates or publish only current
advisories). Novelty was checked at discovery: no ML-ready formulation of
advisory duration-to-lift exists anywhere found; prior art is descriptive
(Texas Uri geospatial analysis 2024, Norway 2008-2019 series, West Virginia
utility-cost regression 2025) or uses duration as an explanatory variable.

**Splits (issue-year windows).** Train 1,069 rows (2008-2017, 66.88% lift30,
585 distinct sites), eval 372 (2018-2020, 60.48%, 286), holdout 884 (2021-2024,
58.14%, 547). Censored still-active advisories are excluded and counted per
window (2/1/10); 3 negative-duration rows are excluded as unverified outcomes;
30 unparseable-issue-date rows are excluded and counted; 279 rows in the
2025-2026 cohorts fall outside every scored window (mostly still active).

**The measured finding - no demonstrated headroom.** On the identical 372 eval
rows, after acceptance:

| Reference / model | Eval AUC | Brier |
| --- | --- | --- |
| Site persistence (`site_prior_lift30_rate`, shipped) | **0.6124** | 0.2819 |
| Calendar/identity (county x month, train-estimated) | 0.5075 | 0.3101 |
| Reason prior (train-estimated) | 0.4307 | 0.2440 |
| Facility prior (train-estimated) | constant - no ranking information | 0.2429 |
| Majority-class accuracy | 0.6048 | - |
| Full model (benchmark template XGBoost, verbatim runner) | **0.5086** | 0.3609 |

The stock model trails the one-line site-persistence rule by 0.1038 AUC. The
paired intervals from the per-row diagnostic (worker job ns-bwa-diag-001, 1000
resamples, seed 23) **exclude zero** at the row level
([-0.1693, -0.0357]) and under site-clustered resampling ([-0.1706, -0.0383],
286 clusters), so the deficit is not a resampling artefact. The model sits at
the calendar control (model - calendar +0.0011, interval [-0.0866, +0.0723]
contains zero - an inconclusive difference, not parity). Per issue year:

| Issue year | rows | lift30 rate | model AUC / Brier | persistence AUC / Brier |
| --- | --- | --- | --- | --- |
| 2018 | 129 | 0.7442 | 0.5554 / 0.2298 | 0.6084 / 0.2173 |
| 2019 | 125 | 0.6400 | 0.5018 / 0.3479 | 0.6203 / 0.2748 |
| 2020 | 118 | 0.4153 | 0.4886 / 0.5178 | 0.5991 / 0.3600 |

Persistence dominates every year, and the model's calibration degrades across
the measured COVID-era prevalence shift (eval rate 0.744 -> 0.415; model Brier
0.23 -> 0.52) while persistence holds. Per the qualification standard this is a
**recorded defect of the task under this protocol, not an encouraging result**:
the task's discriminative claim above simple references is not demonstrated by
the runner's own baseline. It does not prove every competent model must lose -
the persistence feature is shipped and agent-visible, so a solver that follows
it enters at ~0.61 and must beat it to claim headroom - but any benchmark claim
from this artifact must carry this comparison beside it.

**Evaluation access.** The evaluation contract declares isolated rows: predict
each row without any other row. The gate measured the cross-row exposure
(site-level reverse-history covers 369 train / 56 eval / 217 holdout rows - a
later same-site row's prior-lift-rate equals the earlier row's label when that
prior is its only resolved one). The shipped illustrative runner passes the
whole eval feature table to the predictor and does **not** enforce the
restriction; unrestricted-access scores are not meaningful for this artifact,
and a real evaluation must enforce the restriction itself.

**Suitability.** Retrospective research on one pinned vintage (content current
as of 2026-06-16). The register is revised in place with no historical
vintages, so training-label timing and full-row historical availability are
unverified; no point-in-time reconstruction is claimed. The labeled eval split
is development/validation data; the holdout stays outside agent development
until a design is frozen. See the suitability notice in `VERIFICATION.md`.

**Scope of this release.** One baseline through the runner's training and
validation contract; no agent or harness experiment was run and none is
implied. The holdout was never evaluated and no holdout figure exists.
