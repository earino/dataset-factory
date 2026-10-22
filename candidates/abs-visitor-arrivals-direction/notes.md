# abs-visitor-arrivals-direction - row-level notes

Session: scheduled discovery, 2026-10-22 (Oceania tick). Verdict: **go (ready)**, licence class A.

## Source identity

- ABS Data API (SDMX 2.1), dataflow `ABS,OAD_COUNTRY,1.0.0` - "Visitor arrivals and
  resident returns, Selected Countries of Residence/Destinations", monthly.
- Landing page:
  https://www.abs.gov.au/statistics/industry/tourism-and-transport/overseas-arrivals-and-departures-australia/latest-release
  (reference period August 2026, released 13/10/2026, 11:30am AEDT)
- API base: https://data.api.abs.gov.au/rest/ (user guide:
  https://www.abs.gov.au/statistics/application-programming-interfaces-apis/data-api-user-guide)

## Licence triage (first, 2026-10-22)

ABS "Privacy and legals" (https://www.abs.gov.au/privacy-and-legals): "All material
presented on this website is provided under a Creative Commons Attribution 4.0
International licence, with the exception of: the Commonwealth Coat of Arms, the ABS
logo, material protected by a trade mark, unit record data (microdata), content
supplied by third parties." -> class A. No per-dataset exception applies to OAD
aggregate time series.

## Commands and measured results

1. Dataflow inventory: `curl https://data.api.abs.gov.au/rest/dataflow/ABS` ->
   3,230,544 bytes; 1,228 dataflows. Parsed with `.factory/abs_flows.py`:
   OAD_COUNTRY among the tourism/transport flows (also RT "Retail Trade" - which the
   landing page shows CEASED with the June 2025 release, so retail was not taken).

2. Structure (`.factory/abs_structure_dump.py` on
   `data/api.abs.gov.au/rest/dataflow/ABS/OAD_COUNTRY?references=all`,
   100,939 bytes, 2.72 s):
   - CL_OAD_CAT_TRAVEL: `05 = Short-term (less than one year) Residents returning`,
     `06 = Short-term (less than one year) Visitors arriving`
   - CL_OAD_ARRIVALS_COUNTRY: 78 codes (names saved to scratch, e.g. 6203/OT7/TO2)
   - CL_TSEST: 10=Original, 20=Seasonally Adjusted, 30=Trend, 40/50=Sensitivity
   - DSD dimensions: CAT_TRAVELLER, COUNTRY_RESID, TSEST, FREQ
   -> every column's meaning is documented by the publisher; only Original (10) exists
   in this dataflow, so seasonality must be learned (calendar-only baseline is
   meaningful), and no SA column can leak the label.

3. Full panel fetch (`.factory/abs_oad_probe.py`,
   `https://data.api.abs.gov.au/rest/data/ABS,OAD_COUNTRY,1.0.0/all?format=csv&startPeriod=1991-01`):
   - HTTP 200, 3,308,454 bytes, 3.47 s, **1 request** (measured cost of the whole panel)
   - 59,452 observation rows; 428 months 1991-01..2026-08; 77 COUNTRY_RESID;
     2 CAT_TRAVELLER; TSEST=10 only; 0 missing OBS_VALUE
   - CSV columns: DATAFLOW, CAT_TRAVELLER, COUNTRY_RESID, TSEST, FREQ, TIME_PERIOD,
     OBS_VALUE, UNIT_MEASURE (NUM), OBS_STATUS, OBS_COMMENT

4. Label base rates (same probe):
   - MoM direction pairs: 58,082 (up 30,466 / down 30,048 / 568 flat) - near coin-flip,
     so a persistence-of-sign rule cannot dominate
   - YoY direction pairs: 56,843; per-year up/down e.g. 2004: 1,218/424; 2020: 159/1,492
     (pandemic collapse); 2022: 1,645/9 (reopening surge)
   - Split windows on the YoY label (candidate partition):
     train 1991-2014: up=24,166 down=13,575 flat=520; eval 2015-2019: up=5,588
     down=2,630 flat=61; holdout 2022-2026: up=6,167 down=1,533 flat=140.
     All windows carry both classes; every year inside each window has both classes.
   - 2020-2021 sit outside the candidate partition (either dropped as pandemic
     extremes or folded into train; construction decides and documents).

5. Prediction timing (observed release dates from the ABS release pages, read
   2026-10-22):
   - Aug 2026 reference period released 13/10/2026 (43 days after month end)
   - Jul 2026 released 11/09/2026 (42 days); Apr 2026 released 12/06/2026 (43 days)
   - Next-release schedule published: Oct 2026 due 15/12/2026; Nov 2026 due 19/01/2027
   - Note "Caution: Data in Data Explorer is currently released after the 11:30am
     release on the ABS website" (Jul 2026 page) - SDMX/website sync same day.
   -> prediction instant = release of month M; target month M+1 is unpublished at that
   instant; max observed lag 43 days.
   - Revision caveat (methodology History of changes): "March 2026, state or territory
     of stay/residence - Once linked Medicare data became available, the ABS
     reprocessed and revised overseas arrivals and departures data for March 2026,
     which was released in the April 2026 issue". Only the current vintage is
     downloadable; feature values are current-vintage, cutoff documented as an
     assumption (same posture as NHS A&E on this bench).

6. Known-event fixtures, verified directly in the fetched panel: 2020 border closure
   -> YoY down 1,492 vs up 159; 2022 reopening -> YoY up 1,645 vs down 9.

## Novelty

Prior art recorded by scripts/check-novelty.py (see record.json novelty_check):
tourism-forecasting literature and M-competition style series exist; Tourism Research
Australia publishes its own forecasts (a publisher cross-check product); no ML-ready,
publication-lag-gated, country-panel direction benchmark for Australian arrivals was
found. Verdict: differentiated.

## Construction pointer

Fetch panel (1 request), build (06-visitor, country) x month grid, features =
history <= published M + calendar + country identity, label = YoY direction of M+1,
splits per the candidate partition, baseline triad before any headroom claim. All bulk
work on the worker; the coordinator only ever holds the ~3.3 MB probe copy (deleted
after this session).

## Construction (2026-10-22, session: advancement tick)

Build script: `candidates/abs-visitor-arrivals-direction/source/build.py`; worker job
`abs-001` (server 171801245, cx23, launched 10:14:40Z, job elapsed 19.3 s, exit 0,
EUR 0.04 reservation, worker destroyed 10:26:49Z). Staging release 420574099; gate
report asset sha256 `3589d5e2ea75397f...`.

### Coordinator dry run (before the worker launch) - commands and what they caught

`curl` of the panel (3,308,454 bytes, byte-identical to the record's measured fetch)
and structure (100,939 bytes) into scratch, then:

```
python3 candidates/abs-visitor-arrivals-direction/source/build.py \
  --out "$TMPDIR/abs-dry/extract" --work-dir "$TMPDIR/abs-dry/work" \
  --panel-file ... --structure-file ... --built-at 2026-10-22T12:00:00Z
python3 skills/dataset-qualification/scripts/qualify_dataset.py "$TMPDIR/abs-dry/extract"
```

Three defects caught before any worker spend, each fixed and re-run:

1. **Baseline lookup bug**: `fit_rate_table` keys are tuples; the identity lookup used
   the bare string, so every country's score collapsed to the constant global rate and
   identity AUC printed exactly 0.5 in both windows. A full-precision recompute from
   the written CSVs gave 0.572 eval / 0.532 holdout - the exactly-0.5 twice was the
   tell. Fixed; the AUC helper was separately verified against 7 hand-computed cases
   (`.factory/test_abs_auc.py`, deleted with the scratch).
2. **Known-event fixture window**: the record measured the border-closure collapse on
   **2020** target months; the build first asserted it over the combined 2020-01..2021-12
   pandemic window, which 2021's reopening dilutes to down-share 0.6528 (< 0.75) and
   failed. Fixed to the 2020-only texture (down 766 / up 59 / flat 3 = 0.9251).
3. A `month_text` use-before-definition in the pandemic accounting branch (caught by
   the editor's type check, never reached a run).

Dry-run gate: 38/38 PASS, zero FAIL. Dry-run scratch deleted by exact filename after
the worker run (panel.csv, structure.xml, extract/*).

### Worker run (abs-001) - measured results

Panel: 59,452 rows, 428 months 1991-01..2026-08, TSEST=10 only, FREQ=M only,
OBS_STATUS empty on all 59,452 rows, UNIT_MEASURE=NUM only, 0 missing OBS_VALUE, 0
non-integer values; 77 distinct COUNTRY_RESID over both categories, 70 with a 06
visitor series (7 countries carry residents-returning only). CL_OAD_ARRIVALS_COUNTRY
parsed 78 codes, every in-panel country named.

Shipped visitor panel (CAT_TRAVELLER=06): train 19,071 rows / 6,668 positives (34.96%)
/ 310 flat / 275 distinct positive months (1992-02..2014-12 - the first month with the
required 13 months of panel history); eval 4,140 / 1,204 (29.08%) / 44 flat / 60 months
(2015-01..2019-12); holdout 3,920 / 768 (19.59%) / 72 flat / 45 months
(2022-01..2026-08). Accounted: 224 insufficient_history, 10 unobserved_target,
1,662 pandemic-excluded target months (2020-01..2021-12: up 494 / down 1,085 / flat 83),
70 live-month rows (features published, outcome due with the next OAD release).

Label rule as shipped: fell_short = 1 iff OBS_VALUE(T) < OBS_VALUE(T-12); exact ties
count flat and label 0. Both label source values (target month, year-earlier month)
are excluded from every written header - asserted in-build, and the gate's
single-column sweep found nothing above identity level.

Gate 1.4.0 on the worker: ok, 0 failed checks of 38, artifact
`afb46c6b29e6c4aa7668afcbd8f14c3f02ad56066bb7fbd5af263802740ad442`. Coordinator
re-verification: the five extract files + report re-downloaded from staging 420574099,
every digest matched the release manifest, `qualify_dataset.py --accept` on the
collected bytes -> ACCEPTED.

Reference baselines (in-build, stdlib rank AUC, train-estimated tables):

| reference | eval AUC | holdout AUC |
| --- | --- | --- |
| persistence (YoY sign observed at M) | 0.3647 | 0.2256 |
| identity only (country) | 0.5720 | 0.5317 |
| calendar only (country x calendar month) | 0.5501 | 0.5364 |

Persistence is **anti**-correlated with the label in both scored windows (sign
accuracy 0.67/0.81 but rank AUC far below 0.5): in the eval/holdout eras a falling
YoY trend at M predicts a *recovery*, not another fall. The task is a
mean-reversion + seasonality problem; the nhs-ae persistence-defect cannot occur
here. Prevalence drift 34.96% -> 29.08% -> 19.59% positives is the documented
post-2022 recovery boom, recorded as a property. The full-model leg
(`abs-baseline-001`, runner contract on staging 420574099) is the remaining triad
step; headroom is unclaimed until it lands.

### Full-model leg: `abs-baseline-001` (runner contract, 2026-10-22)

Bundle `candidates/abs-visitor-arrivals-direction/baseline/` (run.sh, materialize.py,
report.py, the gate's own collected qualification.json, qualify_dataset.py, plus
train.py/validate.py/validate.sh copied verbatim out of the read-only benchmark clone;
assembled via `scripts/assemble-job.py abs-baseline` - the bundle was checked to carry
the runner files before launch). Worker 171804060, cx23, job elapsed 76.6 s, exit 0,
EUR 0.06 reservation, destroyed 10:37:25Z. Report at staging release 420587459.

Measured (container.log / baseline_result.json, read back from staging and
digest-verified on the coordinator):

- fetched bytes re-ACCEPTED before scoring: "matches the qualified artifact afb46c6b29e6c4aa"
- runner files unmodified: bundled sha256 == expected for train.py, validate.py, validate.sh
- `train.py` eval AUC **0.6219**; `validate.py` independent predict_proba recompute **0.6219**; CONTRACT OK

Triad on identical eval rows (4,140 rows, 1,204 positives):

| leg | eval AUC |
| --- | --- |
| persistence (YoY sign at M) | 0.3647 |
| calendar-only (country x cal-month) | 0.5501 |
| identity-only (country) | 0.5720 |
| full model (runner contract, abs-baseline-001) | **0.6219** |

The model clears calendar-only by +0.0718 and identity-only by +0.0499: learned signal
beyond seasonality and country identity. Headroom is now claimed with the full triad
recorded beside it.

Cosmetic defect, recorded: the run's `baseline_result.json` purpose string says
"TSB rail occurrence casualty artifact" - report.py was copied verbatim from the tsb
bundle and its purpose line was hardcoded. Every artifact fact in the same report is
abs's (name, target fell_short, rows 19071/4140/3920, accepted artifact afb46c6b...),
and the purpose line in the abs copy now derives the name from meta.json, so a re-run
cannot mislabel. The tsb original is untouched.
