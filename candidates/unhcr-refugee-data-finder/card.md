---
license: other
license_name: cc-by-3.0-igo-source-plus-cc0-compilation
language:
  - en
pretty_name: UNHCR Asylum Corridor Application Doubling (HDX)
size_categories:
  - 1K<n<10K
task_categories:
  - tabular-classification
tags:
  - tabular
  - unhcr
  - asylum
  - refugees
  - humanitarian
  - temporal-split
  - event-outcome
configs:
{CONFIGS_BLOCK}
---

# UNHCR Asylum Corridor Application Doubling ({RELEASE_TAG})

**Status: {STATUS_LINE}**

UNHCR's asylum-applications distribution is refreshed to carry complete data for
year D (the observed 2026-08-20 refresh carries complete data through 2025). For
an asylum corridor (origin country O, country of asylum H) whose
government-procedure applications in year D are at least 500 and whose year-D-1
value is published, **at that publication instant, will the corridor's year-D+1
government-procedure application total reach at least twice the year-D total?**
One row per eligible corridor-year; the label unfolds one year later, and every
shipped feature reads published years <= D only.

- **Artifact version:** `{ARTIFACT_VERSION}`
- **Version tag:** `{RELEASE_TAG}` (use this revision for reproducibility)
- **Rows:** {ROWS_TOTAL} corridor-year rows across three disjoint temporal splits
- **GitHub counterpart:** {GITHUB_REPOSITORY}

## Splits

| split | rows | target years | positives | positive rate |
| --- | ---: | --- | ---: | ---: |
| `train` | 3,363 | 2002-2016 | 283 | 8.42% |
| `eval` | 1,887 | 2017-2021 | 165 | 8.74% |
| `holdout` | 1,962 | 2022-2025 | 227 | 11.57% |

The splits are temporal on the target year and disjoint, with both classes in
every window. Positives arrive in origin-year clusters (`surge_cluster`), so the
clustered count is reported beside every score. Rows excluded by eligibility are
counted per split and never silently labelled: 377 without a published year-D-1
value, 33 host-silent corridors whose target year is unobserved, and 496
live-edge rows whose label year (2026) is beyond the pinned vintage. Prevalence
swings from 1.4% to 18.8% across eval label years, so per-year results - not
pooled ones - are the honest grain.

## Reference points

Measured on the identical 1,887 eval rows, after gate acceptance, through the
benchmark's unmodified runner (`train.py` + `validate.sh`, digests verbatim):

| Reference / model | Eval AUC | Brier |
| --- | ---: | ---: |
| Full model (stock XGBoost baseline) | 0.5393 | 0.085099 |
| Persistence: corridor momentum (`log_growth_d`) | **0.5742** | - |
| Persistence: surge flag (`surged_recently`) | **0.5856** | - |
| Calendar/identity prior (train rate per corridor, then origin) | 0.5409 | - |
| Recent-era constant | 0.5000 (constant, no ranking information) | - |

Paired row-bootstrap differences vs the full model (1000 resamples): momentum
**-0.0348** [-0.1056, +0.0409], surge flag **-0.0463** [-0.1103, +0.0144],
calendar/identity -0.0016 [-0.0594, +0.0587], recent-era constant +0.0394
[-0.0047, +0.0859] (a degenerate control: a constant cannot rank).
Majority-class accuracy on this split is 0.9126 at an 8.74% base rate -
uninformative; AUC is the metric.

**Finding: no demonstrated headroom over persistence under this protocol.** The
stock baseline trails both persistence references on identical rows; every
interval contains zero, so the differences are inconclusive rather than
significant, but the observed gaps are negative and are recorded here so no
reader quotes 0.5393 alone. Per label year, momentum owns 2017-2019 while the
2020 pandemic year inverts it completely (model 0.8417 vs momentum 0.1164 on 6
positives - fragile evidence, not a capability claim). Equally, one stock model
trailing persistence does not establish that no solver can beat it; that is the
benchmark's real question and it remains open. The holdout was never scored and
stays sealed.

## Timing, honestly stated

The prediction instant is a **publication instant**: the HDX refresh that
carries complete year-D data (observed refreshes 2025-11-05, 2026-02-25,
2026-06-11, 2026-06-19, 2026-06-22 and 2026-08-20; the last carries complete
data through 2025, 232 days after the 2025 period end). The publisher keeps **no
historical vintages** - one in-place-revised resource - so training-label timing
and full-row historical availability are **unverified** and the evaluation
contract is **retrospective research over the pinned 2026-08-20 vintage** with
an **isolated-rows requirement for honest evaluation**: never a certified point-in-time
reconstruction and never an operational-forecasting claim. A measured cross-row
exposure is declared and handled rather than hidden: on this panel a corridor's
`surged_recently` at T+1 equals its T label (0 mismatches on covered rows), so
honest evaluation requires isolated rows - one row presented to the solver at a
time. The shipped illustrative runner does **not** enforce this: it passes the
whole eval feature table to the predictor, and the independent pre-flip audit
(2026-10-28) measured frozen label-blind recoveries from that access (eval AUC
0.9753 from eval features alone, holdout AUC 0.9830, 0.9970 across all splits),
so scores under unrestricted access are meaningless. The shipped baseline is
illustrative - it shows one way to work with the panel, not a scoring protocol.
Labeled eval is development/validation; the holdout is the final
test and ships outside evaluated agents' workspaces.

## Source and provenance

- UNHCR, The UN Refugee Agency - asylum applications residing in each country of
  origin (annual, 2000-), distributed via the Humanitarian Data Exchange,
  dataset `74cdbe77-0a0b-441b-9535-bacc263be2a8`; fetched as one anonymous CSV
  (8,669,567 B, sha256 `d5808616c3d1...`, last-modified 2026-08-20, pinned
  vintage; full digest in `MANIFEST.json`).
- Construction: `code/build.py`, executed by worker job `unhcr-001`;
  qualification gate 1.5.0, 45/45 checks on the full artifact, exact-byte
  acceptance before any figure was computed; the declared cross-row probe ran
  on every split (2,439/1,265/1,239 rows, 0 mismatches). Baseline job
  `unhcr-baseline-001` through the unmodified runner contract.
- Corridor-year fixtures asserted in-build: SYR->DEU 2015 (doubled), AFG->USA
  2022 (doubled), AFG->DEU 2022 (not doubled), UKR->POL (below eligibility).

## Licence

The source is UNHCR asylum-applications statistics under **CC BY 3.0 IGO**
(attribution required; no implied endorsement). Attribution carries through to
every copy of the derived data: {SOURCE_ATTRIBUTION}. Our contribution to the
derived compilation is dedicated **CC0-1.0**; our code is **MIT**. This is a
derived research dataset, **not** a UNHCR product, and UNHCR has not reviewed
or endorsed it. See `LICENSE.md` for the full terms, attribution and citation.

## Use with the runner

```bash
python3 get_dataset.py --dest ./task
python3 code/qualify_dataset.py ./task
sh baseline/reproduce_baseline.sh ./task
```
