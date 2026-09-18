# austin-911-response

**Status: selected lead candidate (2026-09-18). Column documentation read and the
`response_time` / `mental_health_flag` questions closed on 2026-09-18 (eighth
session). The construction script and worker job are implemented (ninth session); the
label-source leak found in review is fixed and guarded (tenth session). The full worker
build is still pending, so no base rate or headroom figure from the real extract exists
yet.**

## The label-source leak, and why the declared lists missed it

The first version of the construction script fetched `response_time` to derive `late` and
then wrote it into all three CSVs, because it was listed in `CARRY_COLUMNS`. It was absent
from `FEATURES`, so every declared list in the script and the manifest looked correct while
the shipped file contained the answer.

**A feature list cannot prevent this.** The runner treats every column other than the
target as model input:

- `task_template/train.py`: `feature_cols = [c for c in train.columns if c not in ID_COLS + [TARGET]]`
- `task_template/validate.py`: hands `predict_proba` the full frame with only the target dropped

So the only control that works is not shipping the column. `response_time` is now
`LABEL_SOURCE`: fetched from the API, used to compute `late`, and excluded from every CSV.
It stays visible in `manifest.json` as `label_source_column` and in `excluded_post_hoc` for
provenance, and `shipped_columns` is asserted not to contain it.

Three guards now exist, and each was checked against a deliberately re-shipped leak:
`ConstructedFiles` and `RunnerContract` in `tests/test_austin_build.py` inspect the files
the writer actually produced, and `tests/test_qualification_gate.py` runs the project's
`dataset-qualification` gate against them - the same gate that rejects a fixture shipping
`response_time` while accepting the corrected one.

## Why this is the lead

Chosen over the Chicago adjudication candidate on one hard criterion: this source is
explicitly **Public Domain**, while Chicago's is "See Terms of Use". The project must
publish a dataset publicly, and PROJECT.md requires usable source permissions, so a
source whose remaining risk is technical rather than legal is the better first
release.

Confirmed directly from the view metadata on 2026-09-18:
`GET https://datahub.austintexas.gov/api/views/e687-fx2y.json` returns
`"license": {"name": "Public Domain"}` for the view titled *APD 911 Calls for
Service 2023-2026*.

## Measured evidence (2026-09-18, anonymous API)

Endpoint: `https://datahub.austintexas.gov/resource/e687-fx2y.json`

| Query | Result |
|---|---|
| `$select=count(*)` | 1,049,636 rows |
| rows per year (`date_trunc_y`) | 2023: 286,145 / 2024: 286,035 / 2025: 285,665 / 2026 to 09-18: 191,791 |
| `priority_level` counts | P0 141,710 / P1 186,787 / P2 516,736 / P3 204,403 |
| `response_time IS NULL` | **0 across the whole dataset** |
| `incident_type` distinct values | **one value**: `Dispatched Incident` (all 1,049,636 rows) |
| bounded sample | `response_time` 165 and 848 - seconds, not minutes |

### Column inventory corrected

The dataset has **25 columns**, not 42. `GET /api/views/e687-fx2y.json` lists 25
fields and they match the 25 keys a single resource row returns exactly (no
difference in either direction). The earlier "42 columns" note was wrong; treat 25 as
the verified figure.

## Column documentation: the two open questions, both now closed

### `response_time` - unit confirmed, but its start is *before* `response_datetime`

Documented as *"the amount of time between when the 911 call was **answered** and when
the first officer arrived on scene in seconds"*, and *"not applicable to
officer-initiated incidents ... left blank for such incidents"*.

`response_datetime` is documented as *"the date and time that the 911 call-taker's
Emergency Call Taker (ECT) screen **opened following** the 911 call being answered"*.
So `response_time` starts at call-answered, which is strictly earlier than the
prediction-time snapshot. Measured on a 2,000-row sample ordered from
2025-01-01T00:00:00Z:

```
delta = (first_unit_arrived_datetime - response_datetime) - response_time
  min  -561 s   p50  -58 s   max  6287 s   mean  -56.0 s
  |delta| <= 1 s : 48 / 2000
```

`response_time` therefore exceeds the elapsed time visible in the row by about a
minute at the median, and the two are nowhere near equal. **No column in this dataset
records when the call was answered**, so the true label start cannot be
reconstructed. Two consequences for the construction script:

1. The target must be the portal's own `response_time`, not a recomputed
   `first_unit_arrived_datetime - response_datetime`. Recomputing silently changes the
   label by an unbounded amount (the sample's delta range spans nearly two hours).
2. Every feature must be available at or before `response_datetime`. The label
   includes roughly one minute of call-taking that happens before the feature
   snapshot, which biases any threshold toward the positive class by an unknown but
   bounded amount. Record this as a documented property of the release rather than
   trying to correct it.

### `mental_health_flag` - post-hoc, must be excluded

The description is decisive. An incident may be flagged because of *"the final problem
description, the call disposition, because a crisis counselor was assigned to the
call ... or because the subject of a use of force ... displayed 'Emotionally Disturbed
Person' conduct"*, and flagging from a call disposition *"indicate[s] that a responding
officer assessed that mental health had a role"*. Those determinations happen at or
after the response. **Exclude `mental_health_flag`.** The question left open in the
previous session is closed.

### `priority_level` - also post-hoc, and it was previously listed as a feature

Documented as *"the priority level assigned to the incident **at the time of the first
officer's arrival**"*. That is after the response being predicted, so it is not
available at the prediction time. It was listed as a dispatch-time feature in the
earlier notes; that was wrong. **Exclude `priority_level`.**

## Features available at the prediction time (revised)

`incident_type`, `sector`, `council_district`, `geoid`, `blkgpnm`,
`response_day_of_week`, `response_hour`, plus derived calendar position, **and the two
initial-problem fields**:

- `initial_problem_description` - *"a preliminary description of the problem ... based
  on either the information given to the 911 call taker ... or information collected by
  officers"*.
- `initial_problem_category` - a general category derived from the initial
  description.

These two are the strongest genuinely dispatch-time signals in the table (free-text
and categorical call type) and were missing from the earlier feature list. Their
distinction from the `final_*` fields is exactly the initial-versus-final cut the
column docs describe, so the exclusion of `final_problem_description` and
`final_problem_category` stays.

## Columns that must be excluded (post-hoc)

`first_unit_arrived_datetime`, `call_closed_datetime`, `response_time` (the label
source), `priority_level`, `mental_health_flag`, `final_problem_description`,
`final_problem_category`, `call_disposition_description`, `number_of_units_arrived`,
`unit_time_on_scene`, `report_written_flag`, and all three
`*injured_killed_count` fields.

## Target: measured response_time distribution and threshold base rates

Whole-dataset aggregate (`response_time` is never null):

| Statistic | Seconds |
|---|---|
| min | 0 |
| max | 182,878 (~50.8 h) |
| mean | 2,414.0 |

Bounded 2,000-row sample from 2025-01-01 (percentiles):

| p25 | p50 | p75 | p90 | p99 |
|---|---|---|---|---|
| 436 | 933 (15.6 min) | 3,018 (50.3 min) | 8,832 (2.45 h) | 29,503 (8.2 h) |

Positive-class base rate `P(response_time > T)`, counted over the whole series and over
the proposed training window (`response_datetime < 2025-07-01`, 714,314 rows):

| T | full series (1,049,636) | training window (714,314) |
|---|---|---|
| 5 min | 0.8716 | 0.8784 |
| 10 min | 0.6368 | 0.6460 |
| 15 min | 0.4838 | 0.4919 |
| **20 min** | **0.3938** | **0.4008** |
| 30 min | 0.2934 | 0.2988 |
| 60 min | 0.1659 | 0.1696 |

The class balance is stable between the full series and the training window (largest
gap 0.0074 at T = 20 min), so a threshold frozen from the training window is not a
moving target. **T = 20 minutes is the leading choice**: a ~40% positive rate is far
from degenerate, sits near the middle of the response-time mass, and does not depend on
the far tail where timestamp noise dominates.

No AUC, headroom figure or acceptance verdict has been measured. Nothing above is a
scored result.

## Construction plan

1. ~~Read the column documentation for `response_time` and `mental_health_flag`.~~
   **Done**; see above.
2. Write the construction script: pull the full series on a worker, freeze an extract
   with recorded SHA-256 checksums, keep the dispatch-time feature list above, and
   freeze T = 20 min (seconds: 1200) from the training window only, before any scoring.
3. Temporal split by `response_datetime`; report the base rate of the positive class.
4. Simple baseline first, then compare a competent model.
5. Record the `response_time` start-vs-snapshot offset as a documented dataset
   property in the release notes.

## Open blockers

- No licence text has been read beyond the catalog's Public Domain field; the catalog
  field is the recorded basis. A link to the source's own terms has not been captured.

## Measured 2026-09-18: `incident_number` is not unique, and paging depended on it

The first full extraction (job `austin-001`) built all three splits and then **failed
qualification** on one check. Investigating the rows rather than the declarations produced two
findings.

**1. The source is not unique on `incident_number`.** Aggregate queries against
`e687-fx2y` report 1,049,636 rows and **1,049,612 distinct** `incident_number` values: 24
incident numbers carry two rows each. The extract reproduced exactly those 24, all inside
train, none spanning two splits - so this is the source's grain, not leakage. It is now
declared in `quality.json` as `expected_duplicate_ids`, measured from the rows during the
build, which pins the known-good count: if paging ever starts repeating rows, the gate sees a
count above the declaration and fails.

**3. The paging key was not total.** `stream_rows` ordered by `incident_number` alone while
paging with `$offset`. On a non-unique sort key the backend's order among ties is not
guaranteed to be the same between requests, so offset paging can repeat or skip rows. The
first extract did not appear to lose or duplicate rows (its 24 duplicates match the source's
24), but the guarantee was accidental. `:id` is unique per row - verified 1,049,636 rows,
1,049,636 distinct - and `$order=incident_number,:id` is accepted and returns identical
results across repeated calls, so the order is now total and the paging deterministic.

**4. Four of the 24 repeated numbers carry different labels - because they are different
events.** `austin-002` re-ran with 1-3 fixed and failed one check: `230990471`, `241321558`,
`250081425` and `251971574` each have two rows whose `late` differs. Reading the source rows
settles it - `230990471` is an "Alarms"/Baker call at 07:33 with a 618-second response *and*
an "Other"/Frank call at 16:38 with a 6,164-second response. Same number, seven hours apart,
different category, different sector, different priority. So **`incident_number` identifies a
call, not a row**, and one label per incident number is not a property this source has.

That made the gate's new check wrong for this dataset: it asserted one label per repeated
identifier, an assumption nothing in the data supports. The check now applies only when the
descriptor claims `id_columns_are_entity_keys` - a statement about the source - and otherwise
records the measured disagreement in the report instead of refusing a usable extract. The
descriptor deliberately makes no such claim, with the reasoning recorded in `quality.json`.
This is the same trap as the first three defects: a check that fails a good dataset for a
property it never claimed. The `documented-repeats` fixture pins the Austin shape so it cannot
regress.

Note this also means the split partition is conservative: two distinct events sharing a number
are forced into the same split. None of the 24 pairs straddles a boundary (the splits are by
year and most pairs are the same day), so no row was moved from eval or holdout to achieve it.

**The gate was also wrong.** It reported a repeat inside one split as if it spanned two,
producing `"... in train and train"` for a dataset with no cross-split overlap, and refused a
usable extract for the wrong reason. Cross-split overlap and within-split repetition are now
separate checks. Gate version 1.3.0; three new fixtures (`broken-duplicates`,
`broken-duplicate-labels`, `documented-repeats`) and 123 tests cover all of it.

Job `austin-001` itself completed correctly: the extract was built, the failure was detected
by the gate on the worker, the diagnostics and the extract were preserved in staging, and the
worker was destroyed. That is the intended behaviour for a failing qualification. The
extraction was re-run as `austin-002` with the fixes above.
