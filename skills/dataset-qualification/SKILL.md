---
name: dataset-qualification
description: "Use when a constructed dataset is about to be scored or published. Gate for leakage, prediction timing, units/frames, temporal splits and runner compatibility."
version: 1.0.0
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [datasets, leakage, prediction-tasks, splits, evaluation, runner, benchmarks, qualification]
    category: research
    related_skills: [open-data-source-vetting, grounded-citations]
---

# Dataset qualification

## When to use

The moment a dataset stops being an investigation and starts being **evidence**. Concretely:

- A construction script has produced files that will be scored, benchmarked, or published.
- Someone is about to quote an AUC, a base rate or a headroom figure from those files.
- A candidate is moving from `candidates/<id>/` toward a public release or the harness runner.
- A review found a defect and you need to prove the corrected version is actually correct.

`open-data-source-vetting` is the step before this one - choosing a source, reading its
schema and licence, and setting the prediction-time contract. This skill is the gate that
runs *after* construction and *before* any number is reported.

## Run the checker

```bash
python3 skills/dataset-qualification/scripts/qualify_dataset.py <dataset-dir>
python3 skills/dataset-qualification/scripts/qualify_dataset.py <dataset-dir> --json
python3 skills/dataset-qualification/scripts/qualify_dataset.py --selftest
```

`<dataset-dir>` holds the runner layout (`public/train.csv`, `public/eval.csv`,
`private/holdout.csv`, `meta.json`) plus a `quality.json` descriptor. Exit status is 0 only
when every check passes; every failure names the column, split or declaration responsible.
`--selftest` runs the shipped broken and corrected fixtures and asserts the expected
verdicts for each, so the gate can be re-verified after any change to it.

**A passing checker is necessary, not sufficient.** It proves the files do not contain the
specific defects it can see. It cannot prove the source is what you think it is; the
row-level evidence for that lives in the candidate's notes.

## The five checks, and why each one exists

### 1. Leakage - no shipped column may determine the target

**A declared feature list proves nothing.** The runner treats every column other than the
target as model input: `task_template/train.py` computes
`feature_cols = [c for c in train.columns if c not in ID_COLS + [TARGET]]`, and
`task_template/validate.py` hands `predict_proba` the full frame with only the target
dropped. So a column that ships is a column a solver can use, whatever the manifest says.
The only reliable test is to look at the shipped columns: for each one, compute the best
single-column AUC against the target. A perfect score (1.0) means that column *is* the
answer, whatever it is called.

This is not hypothetical. Austin's first construction fetched `response_time` to derive the
`late` label and then wrote it into all three CSVs via a `CARRY_COLUMNS` list. Every
declared list was correct - it was absent from `FEATURES` - and the shipped file still
contained the answer. The gate catches it as `response_time@train`, `@eval` and `@holdout`
all reaching AUC 1.0.

Two refinements that keep the check honest:

- **Unique-valued columns are not leaks by themselves.** An identifier or a free timestamp
  reaches a perfect AUC by memorising one row per level. The checker reports those as
  `high_cardinality` and requires them to be declared (as an id or as a free field) rather
  than pretending they are leaks. A categorical column is only scored when every level
  carries at least five rows.
- **The label source must be absent, not merely un-listed.** Record it in
  `label_source_columns`, keep it in the exclusion list, and assert it is absent from the
  written files. Keeping it available for provenance is fine *in the manifest*; it is never
  fine in a CSV.

### 2. Prediction timing - every shipped feature must be knowable when the prediction is made

Declare the instant the prediction is made, then sort every column into available /
post-hoc / label source, and **read the column documentation for every field**, not only
the suspicious ones. A field whose name sounds dispatch-time can be documented otherwise:

- Austin's `priority_level` reads like a dispatch assignment but is documented as
  *"assigned to the incident at the time of the first officer's arrival"* - post-hoc.
- Austin's `mental_health_flag` is settable from the final problem description and the call
  disposition - post-hoc, even though a call-taker flag would have been legitimate.

Both were in the "available" list until the documentation was read. `priority_level` then
had to be removed from the feature set **and** from the shipped columns.

### 3. Units and reference frames - a silent, one-directional failure

Any value compared against an external threshold must declare its **unit** and its
**reference frame**, because a mismatch does not error - it produces a uniform wrong answer
that reads like a finding.

NOAA is the worked example. The CO-OPS metadata API publishes flood thresholds with no
datum field, and comparing `hourly_height&datum=MLLW` against `nos_minor` gave **zero
exceedance at all 12 stations across 4,380 station-days** - which looks like "this task has
no positive class" and is entirely an artefact. The thresholds are in the station datum
(`datum=STND`). The rule that settles it is an **event whose answer you already know**:
Boston's 2018-01-04 bomb-cyclone record tide peaks at 15.022 ft MLLW (below the 15.85
threshold, so "no flood") and 18.547 ft STND (correctly above it).

So when an external threshold is used, `quality.json` must carry a `known_event` fixture:
a named event, the expected verdict, and a source. Land it as a checked-in fixture plus an
offline assertion (Austin's and NOAA's live in `candidates/*/`, with
`tests/test_noaa_datum.py` reproducing all four recorded peaks), and then **cross-check the
aggregate against the publisher's own summary product**. NOAA's `htf/annual.json` matched
the reconstruction at 12 of 12 stations, 60 days against 60.

Finally: **uniform results are a red flag, not a finding.** Every split all-positive or
all-negative is what a unit or frame error looks like, and the checker refuses it.

### 4. Temporal splits - disjoint, ordered, and able to carry a score

Splits must be declared as distinct boundaries, non-empty, and with positives in every
split. Beyond that, two measurements decide whether a score is meaningful:

- **Enough positives**, and enough *independent* positives. NOAA's eval split carries 234
  positive station-days and its holdout 256, but flood days cluster at about two stations
  each, so the effective counts are **118 and 126 distinct flood days**. Report the
  clustered number and put confidence intervals on it.
- **Whether the base rate is stationary.** NOAA's rate rises with sea level across the
  series (1.83% train, 2.67% eval, 2.92% holdout), so a temporal split carries systematic
  base-rate shift. That is a property of the phenomenon to document, not a construction
  fault - and it means a single-year holdout is a bad idea.

The checker enforces minimums (`MIN_EVAL_POSITIVES`, `MIN_DISTINCT_EVENTS`) and verifies
the declared counts against the files, so a declared number cannot drift from the data.

### 5. Runner compatibility - match the contract the runner actually reads

From `../harness_benchmark`: `datasets/common.py` fixes the layout
(`public/train.csv`, `public/eval.csv`, `private/holdout.csv`, `meta.json`), and
`task_template/` reads `target`, `positive_label` and `id_columns` from `task.json`. The
score is AUC on the private holdout. See `references/runner-contract.md`.

The defects that actually bite: a public holdout (it reaches the agent's workdir), a
`meta.json` whose `rows`/`positive_rate` disagree with the files, an `id_columns` entry
that is also a feature, and - again - any column shipped beyond the declared set.

## Worked example: Austin, end to end

The full loop this skill is meant to drive, from the lead candidate's record:

1. Read every column's documentation; drop `priority_level` and `mental_health_flag`.
2. Test the label's documented derivation against the rows. `response_time` is documented
   as starting when the call was *answered*, and no column records that instant; measured
   against the row, the difference `(first_unit_arrived - response_datetime) - response_time`
   has a median of -58 s and a range of -561 s to +6,287 s, so the label cannot be
   recomputed. The portal column is the only valid target.
3. Freeze T from the training window by rule, not by hand (binary search on the aggregate;
   COUNT queries only), landing on T = 1200 s at a training rate of 0.4038.
4. Write the runner layout with checksums, withholding the label source.
5. Run the gate; a deliberately re-shipped `response_time` must be rejected.
6. Only then score, and report the base rate as an explicit baseline.

## Pitfalls

- **Trusting the declared lists.** They are not the artefact. Read the file that was written.
- **A passing gate treated as a score.** Qualification says the files are sound; it says
  nothing about whether a model can beat the baseline.
- **Skipping the known-event check because the code runs.** A uniform result is the failure
  signature, and the code never errors.
- **Letting the fixture rot.** The broken fixture must stay broken in the ways the gate
  claims to detect, or the selftest becomes decorative. Regenerate with
  `fixtures/build_fixtures.py` and re-run `--selftest` after any change to the checker.
- **A test that contaminates the artefact under test.** Austin's test loader imported the
  worker source by path, which wrote `__pycache__` into the job's source directory; the
  worker then refused to bundle it, and a sibling test that asserted the directory was clean
  failed. Load code under test with `exec(compile(...))` or assert no bytecode is written.
- **A host-local time assumption in a check.** A helper that parsed a timezone-free
  timestamp with `datetime.fromisoformat(...).astimezone(timezone.utc)` interpreted it in
  the host timezone: the test passed under `TZ=UTC` and `TZ=America/Los_Angeles` and failed
  under `TZ=Asia/Tokyo`, moving a January 1 instant into the previous year. Run the suite
  under a timezone ahead of UTC as well as UTC.

## References

- `references/runner-contract.md` - the exact input contract of `../harness_benchmark`,
  quoted from the read-only checkout, with the column-selection code that makes leakage
  possible.
- `scripts/qualify_dataset.py` - the gate. `--selftest` proves it rejects the broken
  fixture and accepts the corrected one.
- `fixtures/` - the broken and corrected fixture pairs, regenerated by
  `fixtures/build_fixtures.py`.
