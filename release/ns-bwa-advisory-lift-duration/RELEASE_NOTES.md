# Release notes - v2026.12

## Nova Scotia boil water advisory lift-within-30-days

Corrected re-release of `ns-bwa-advisory-lift-duration` (artifact version
`49bf4cfa427375c6b7bf90f85eb0330d78da0cc49197c119c396b6b7ea4c6144`, gate 1.5.0,
44/44 checks, exact-byte accepted on the worker and re-accepted before any
score). It supersedes the staged v2026.10 (`e8ed2a53...`), which stays private
at tag `v2026.10` and is never published.

**Why this version exists.** The 2026-11-01 independent audit of the staged
v2026.10 demonstrated exact label recovery on shipped bytes: cumulative-count
x rounded-rate arithmetic and subtraction over eight outcome-derived history
columns recovered **196/372 eval and 286/884 holdout labels exactly, zero
errors**. The operator accepted a rebuild (2026-11-02) that removes the
channel rather than disclosing it. v2026.12 ships **no outcome-derived
column**: the frame is the advisory's own issuance attributes (site, county,
facility type, reason, issue month/weekday) plus issue-date recency for the
same site and county - 11 columns. The register, population, eligibility and
splits are unchanged by design (byte-identical register fetch; train
1,069/715, eval 372/225, holdout 884/514).

**What the task is.** At the moment a boil water advisory is issued for a
public registered or municipal drinking water supply in Nova Scotia - knowing
the site name, county, facility type, reason for the report, calendar season
and how recently the same site/county last had an advisory - will it be lifted
within 30 days? The register is the only public Canadian per-advisory channel
with lift dates found at discovery (sibling provinces either lack lift dates
or publish only current advisories). Novelty was checked at discovery: no
ML-ready formulation of advisory duration-to-lift exists anywhere found;
prior art is descriptive (Texas Uri geospatial analysis 2024, Norway
2008-2019 series, West Virginia utility-cost regression 2025) or uses duration
as an explanatory variable.

**Splits (issue-year windows, unchanged).** Train 1,069 rows (2008-2017,
66.88% lift30, 585 distinct sites), eval 372 (2018-2020, 60.48%, 286), holdout
884 (2021-2024, 58.14%, 547). Censored still-active advisories are excluded
and counted per window (2/1/10); 3 negative-duration rows are excluded as
unverified outcomes; 30 unparseable-issue-date rows are excluded and counted;
279 rows in the 2025-2026 cohorts fall outside every scored window (mostly
still active).

**The measured finding - still no demonstrated headroom.** On the identical
372 eval rows, after acceptance:

| Reference / model | Eval AUC | Brier |
| --- | ---: | ---: |
| Site persistence (register-side reference; not a shipped feature) | **0.6124** | 0.2819 |
| Calendar/identity (county x month, train-estimated) | 0.5075 | 0.3101 |
| Reason prior (train-estimated) | 0.4307 | 0.2440 |
| Facility prior (train-estimated) | constant - no ranking information | 0.2429 |
| Majority-class accuracy | 0.6048 | - |
| Full model (benchmark template XGBoost, verbatim runner) | **0.5068** | not recomputed for this frame |

The stock model trails the one-line site-persistence rule by **0.1056** AUC
and sits at the calendar control. The integrity repair did not trade away
model signal: the same runner measured 0.5086 on the v2026.10 leak-carrying
19-column frame, so removing the eight columns cost **-0.0018 AUC**. Paired
bootstrap on the same rows (1000 resamples): persistence - calendar +0.1014
[0.0144, 0.1739] (excludes zero), calendar - reason +0.0779 [0.0072, 0.1492],
persistence - reason +0.1793 [0.1136, 0.2482]. No model-vs-persistence interval
was recomputed for this frame; the v2026.10 per-row diagnostic on these same
rows measured the analogous deficit with intervals excluding zero at both the
row level ([-0.1693, -0.0357]) and under site-clustered resampling
([-0.1706, -0.0383], 286 clusters), and the v2026.12 observed gap is larger.
Per issue year, persistence holds 0.6084 / 0.6203 / 0.5991 against prevalence
0.7442 / 0.6400 / 0.4153 across the measured COVID-era shift. Per the
qualification standard this is a **recorded defect of the task under this
protocol, not an encouraging result**: the task's discriminative claim above
simple references is not demonstrated by the runner's own baseline, and any
benchmark claim from this artifact must carry this comparison beside it.

**Evaluation access.** The evaluation contract declares isolated rows as the
design intent: predict each row without any other row. The v2026.10
reverse-history exposure (a later same-site row's prior-lift-rate equalled the
earlier row's label; gate-measured coverage 369 train / 56 eval / 217 holdout)
**no longer exists in these bytes** - no shipped column is a function of any
removal date. The remaining cross-row content is issue-date recency, which
reads other rows' issue dates, not their outcomes. The shipped illustrative
runner still passes the whole eval feature table to the predictor; no
enforcement claim is made, and a real evaluation must enforce the restriction
itself. Whether any new cross-row channel exists in the 11-column frame is
the fresh adversarial audit's question, and the pre-flip audit is mandated to
re-run the frozen subtraction attacks on these bytes.

**Suitability.** Retrospective research on one pinned vintage (content current
as of 2026-06-16). The register is revised in place with no historical
vintages, so training-label timing and full-row historical availability are
unverified; no point-in-time reconstruction is claimed. The labeled eval split
is development/validation data; the holdout stays outside agent development
until a design is frozen. See the suitability notice in `VERIFICATION.md`.

**Scope of this release.** One baseline through the runner's training and
validation contract; no agent or harness experiment was run and none is
implied. The holdout was never evaluated and no holdout figure exists.
