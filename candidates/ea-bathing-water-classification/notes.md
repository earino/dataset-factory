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

## Next action

See record.json `next_action`.
