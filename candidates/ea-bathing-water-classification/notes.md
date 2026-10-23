# ea-bathing-water-classification

**Verdict: GO (2026-10-19).** Status `investigating`; novelty search recorded by
`scripts/check-novelty.py` (differentiated). Construction belongs to an
advancement session.

## The task

For a designated bathing water in England, predict whether next season's annual
rBWD classification falls below "Good" (Sufficient/Poor), using only
classification history, sample-derived history and water metadata through the
end of the previous season. Label = the EA's own published classification
(documented 4-season percentile methodology). Season-Y observations never ship.

## Probes (2026-10-19, anonymous, from the coordinator; all responses < 300 KB)

### Licence

| Command | Result |
|---|---|
| `GET https://environment.data.gov.uk/bwq/` | landing page carries "Open Government Licence v3.0" linking https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/ |
| `GET .../bwq/profiles/profile.html?site=ukc2104-04280` | "All of the bathing-water quality data published via this site is freely available under the Open Government License" |

### API contract (learned from the API's own error text)

| Request | Response taught |
|---|---|
| `GET /bwq/doc/bathingwater/ukc2104-04280.json` (and similar guesses) | 404 - the /bwq/doc/... shape is wrong; nginx default 404 |
| `GET /data/bathing-water-quality/compliance/slice/year/2024?_format=json` | 404 "Resource Not Found" - the generic `compliance` prefix does not exist; regime segment required |
| `GET .../compliance-bwd/slice/year/2024` | 404 - wrong regime literal (bwd); the reference documents `compliance-rBWD` |
| `GET .../compliance-rBWD/slice/year/2024?_format=json&_pageSize=600` | 400 "_pageSize can only be used with a list endpoint" - year slices are ITEM pages |
| `GET .../compliance-bwd/slice?year=2024` | 400 "unrecognised short name or literal: year" |
| `GET .../compliance-rBWD/slice/year/2024?_format=json` | **200, 230,623 bytes**; assessments at `result.primaryTopic.observation` |

API reference read in full: `https://environment.data.gov.uk/bwq/doc/api-reference.html`
(524,610 bytes) documents the slice families: compliance-{regime}/slice/year/{year},
.../slice/point/{point}, in-season/slice/point/{point}, in-season/slice/latest.

### Measured season classifications (compliance-rBWD year slices)

| Season | Assessments | Excellent | Good | Sufficient | Poor | Closed | Below-Good |
|---|---|---|---|---|---|---|---|
| 2015 | 415 | 264 | 109 | 29 | 11 | 2 | 42 (10.1%) |
| 2016 | 415 | 287 | 98 | 22 | 6 | 2 | 30 (7.2%) |
| 2018 | 422 | 282 | 106 | 23 | 9 | 2 | 34 (8.1%) |
| 2022 | 421 | 302 | 87 | 18 | 12 | 2 | 32 (7.6%) |
| 2023 | 424 | 281 | 99 | 25 | 18 | 1 | 44 (10.4%) |
| 2024 | 451 | 289 | 95 | 29 | 37 | 1 | 67 (14.9%) |
| 2025 | 451 | 297 | 95 | 25 | 32 | 2 | 59 (12.9%) |

- Season-slice list (2004-2025) has **no 2020 slice** - monitoring year suspended.
- Each season slice ~230 KB, answered < 1 s; the full 2015-2025 panel is ~2.5 MB
  across 11 requests - no worker needed for the panel itself.
- Distinct waters per slice = assessment count (one annual assessment per water).
- 2017/2019/2021 slices also fetched (200s); per-class counts not recorded for them.

### Sample grain

`GET .../in-season/slice/point/05300?_format=json` -> HTTP 200, 275,255 bytes;
794 sample observations for South Shields back to 1988 (first: 1988-05-11 14:40,
week 1988-W19). Per-sample records exist for feature history.

### Known-event-style cross-check for construction

The measured 2024 Poor count (37) and 2025 (32) are the fixture to match against
the EA's published annual classification announcements / Swimfo percentages.

## Novelty (checked BEFORE source work)

Prior art found by web search (2026-10-19):
- Duncan, Tyrrell, Smart, Keedwell, Djordjevic, Savic (Exeter, 2025 conference
  contribution): DT/ANN models predicting per-sample bacterial exceedances at 8
  SW-England beaches from EA weekly samples + antecedent rainfall - an early
  warning nowcast, not a season-ahead classification task.
- EA's operational Pollution Risk Forecasting (171 of 424 sites, per the EA blog
  2024): daily nowcasts, operational, not a dataset.
- "Bacti" (Exeter/EA/South West Water, 2012-13): bacterial exceedance nowcasting.
- US EPA Virtual Beach family: exceedance nowcasting tools.
None publishes predict-the-annual-classification with splits.

What is ours: season-ahead regulatory classification prediction from prior-season
history only (label not computable from features by construction), frozen temporal
splits 2015-2021 / 2022-2023 / 2024-2025, scored runner contract.

## Caveats recorded honestly

Small panel (~450 entities x 11 label seasons). Strong persistence baseline
expected (4-year rolling window) - headroom above persistence is the
make-or-break measurement at construction; publish or demote on that finding.

## Pre-launch persistence ceiling measured 2026-10-23 (advancement session)

Before spending a worker job, the panel this candidate would ship was built from the
publisher's own ten season slices (2015-2025; 2020 suspended) and the two simplest
references were measured on the declared split windows. Command:
`python3 candidates/ea-bathing-water-classification/eab_ceiling.py` over data fetched by
`candidates/ea-bathing-water-classification/eab_fetch.py` into `.factory/eab-probe/data`
(ignored scratch; both scripts ship with the record). Report: `candidates/ea-bathing-water-classification/ceiling-2026-10-23.json`.
This is a **pre-launch measurement on published slices**, not a qualification report:
no gate has run, nothing was accepted, and no model was fitted.

Panel: 3,359 rows of (bwspid, season) with a season Y-1 classification present. Frame
losses measured: 17 Closed labels excluded; 878 water-seasons dropped for having no
prior-season observation (415 for 2015, which has no 2014 slice, and 419 for 2021,
whose Y-1 season 2020 does not exist) - so the usable label seasons are 2016-2019,
2022-2023 and 2024-2025, not 2015-2025.

| split | rows | positives | rate | binary persistence AUC | **ordinal persistence AUC** |
| --- | --- | --- | --- | --- | --- |
| train 2016-2019 | 1,652 | 121 | 0.073 | 0.850 | **0.951** |
| eval 2022-2023 | 836 | 71 | 0.085 | 0.820 | **0.958** |
| holdout 2024-2025 | 871 | 102 | 0.117 | 0.940 | **0.981** |

Positive waters (declared event key = bwspid): 50 / 44 / 67 per split. Transition
counts 2022+ (bg1 -> y): 1511 stay-negative, 138 stay-positive, 35 onset, 23 recovery.

The decisive number is the **ordinal** persistence reference, not the binary one.
Last season's published classification used on its own 4-level scale (Poor <
Sufficient < Good < Excellent) already reaches 0.958 on eval and 0.981 on holdout,
because the label is a 4-season rolling percentile that already contains three of the
four seasons being classified. A model given the same information starts at that
ceiling; the richer 3-season count reference is *worse* (0.847 / 0.941), so no simple
recombination of the same history adds anything. The gap the candidate would have
claimed against the binary collapse (0.82 -> ~0.95) is an artefact of scoring
persistence more coarsely than the data allows, not headroom.

Decision: **parked, not constructed.** A season-ahead classification task whose
information set is definitionally dominated by the previous year's value of the same
lagging regulatory quantity is a persistence task, and the skill's rule for that case
is to re-target a change/onset label or stop - not to spend a build to demonstrate it.
This is a pre-launch ceiling finding, recorded as such: it is not a model-vs-persistence
measurement on a gate-accepted artifact, and it does not establish that no model could
beat 0.958 by a small margin.

What would reopen it (a new task instance, with its own qualification cycle):

- A **change** target with enough events (onset of below-Good from Good: 35 onsets
  across 2022-2025 - too thin for a clustered event count of 20 per split without a
  longer window).
- An information set that is **upstream of the label**: antecedent rainfall, storm
  overflow/EDM discharge events, or catchment land use. The publisher's own in-season
  slices were re-measured today and carry only the sample date and ISO week
  (`_about`, `sampleWeek`) - **no bacterial result value** - so this dataset cannot
  supply sample-derived features; an upstream-pressure re-scope needs a different
  source (EA EDM/storm-overflow releases, Met Office rainfall) and a fresh novelty
  and licence pass.

## Next action

See record.json `next_action`.
