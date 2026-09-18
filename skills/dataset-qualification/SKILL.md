---
name: dataset-qualification
description: "Use when a constructed dataset is about to be scored or published. Gate for leakage, prediction timing, units/frames, temporal splits and runner compatibility."
version: 2.0.0
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [datasets, leakage, prediction-tasks, splits, evaluation, runner, benchmarks, qualification]
    category: research
    related_skills: [dataset-discovery, dataset-release, grounded-citations]
---

# Dataset qualification

## When to use

The moment a dataset stops being an investigation and starts being **evidence**:

- A construction script has produced files that will be scored, benchmarked or published.
- Anyone is about to quote an AUC, base rate or headroom figure from those files.
- A candidate is moving toward a release, a benchmark task, or another team's runner.
- A defect was found and the corrected version must be *proved* correct, not assumed correct.

Not for reading a source's schema or licence - that is `dataset-discovery`. Not for packaging
and publication - that is `dataset-release`. This skill is the gate between construction and
any number taken from the result.

## Commands

```bash
# the gate, over a dataset directory in runner layout
python3 skills/dataset-qualification/scripts/qualify_dataset.py <dataset-dir>
python3 skills/dataset-qualification/scripts/qualify_dataset.py <dataset-dir> --json --report out.json

# the downstream gate: a written report must still match the bytes on disk
python3 skills/dataset-qualification/scripts/qualify_dataset.py --accept <report.json> <dataset-dir>

# prove the gate itself still detects what it claims to detect
python3 skills/dataset-qualification/scripts/qualify_dataset.py --selftest
```

`<dataset-dir>` holds the runner layout (`public/train.csv`, `public/eval.csv`,
`private/holdout.csv`, `meta.json`) plus a `quality.json` descriptor. Exit status is 0 only
when every check passes; each failure names the column, split or declaration responsible.

**Run it on the full artifact, where the rows are.** The gate reads rows, so a bounded local
sample cannot stand in for it; run it on the worker as part of the build job. Exceeding the
coordinator's disk or RAM budget to run it locally is not a trade worth making.

## Required evidence

Every one of these must exist before "qualified" can be claimed. Absence is not a pass:

1. A `quality.json` declaring `time_column`, `event_key_column`, machine-readable per-split
   `split_windows`, the label source, and - where an external threshold is used - a
   `known_event` fixture with a named event, its expected verdict and a source.
2. A **passing** report from the current gate version, written against the exact artifact
   version that will be scored or shipped.
3. `--accept` re-verifying that report against the bytes on disk at hand-off time.
4. A `--selftest` run showing the shipped broken fixtures still fail and the corrected fixture
   still passes, after any change to the checker or fixtures.
5. Row-level evidence in the candidate's notes for the claims the gate cannot test: that the
   source is what it is believed to be, and that each column's meaning was read from the
   publisher's documentation.

A passing gate is **necessary, not sufficient**: it proves the files lack the defects it can
see. It says nothing about whether the source is what you think it is, and nothing about
whether a model can beat the baseline.

## The five checks

### 1. Leakage - no shipped column may determine the target

A declared feature list proves nothing. The runner treats every column other than the target
as model input (`feature_cols = [c for c in columns if c not in ID_COLS + [TARGET]]`), so a
column that ships is a column a solver can use, whatever the manifest says. The only reliable
test is over the shipped columns: for each, compute the best single-column AUC against the
target. A perfect score means that column *is* the answer, whatever its name.

Example: a construction that fetches `response_time` to derive a `late` label, then writes it
into all three CSVs via a carry list, ships the answer. Every declared list is correct - the
column is absent from `FEATURES` - and the file still contains it. The gate reports it at AUC
1.0 in all three splits.

- **Unique-valued columns are not leaks by themselves.** An id or a free timestamp reaches
  perfect AUC by memorising one row per level; those are reported as `high_cardinality` and
  must be *declared*, not mistaken for leaks. A categorical column is scored only when every
  level carries at least five rows.
- **The label source must be absent from the CSVs, not merely un-listed.** Record it in
  `label_source_columns`, keep it in the exclusion list, and assert its absence in the written
  files. Keeping it *in the manifest* for provenance is fine; in a CSV it is fatal.

### 2. Prediction timing - every shipped feature must be knowable when the prediction is made

Declare the instant the prediction is made, then sort every column into available / post-hoc /
label source. **Read the column documentation for every field**, not only the suspicious ones:
a name that sounds dispatch-time can be documented otherwise. Fields documented as set at
officer arrival, at call disposition, or from a final problem description are post-hoc, and
removing them from `FEATURES` is not enough - they must leave the shipped columns too.

### 3. Units and reference frames - a silent, one-directional failure

Any value compared against an external threshold must declare its **unit** and its **reference
frame**, because a mismatch does not error. It produces a uniform wrong answer that reads like
a finding.

Worked example: a publisher's threshold API with no datum field, compared against the wrong
datum, gave zero exceedance at 12 of 12 stations across 4,380 station-days - which looks like
"this task has no positive class" and is entirely an artefact. What settles it is an **event
whose answer you already know**: a named storm tide that must exceed (and a datum under which
it must not). Land that as a checked-in fixture plus an offline assertion, then cross-check the
aggregate against the publisher's own summary product.

**Uniform results are a red flag, not a finding.** A split that is all-positive or all-negative
is what a unit or frame error looks like, and the gate refuses it.

### 4. Temporal splits - disjoint, ordered, and able to carry a score

Declarations are not evidence. `quality.json` records split windows, positive counts and
clustered event counts; the gate recomputes all of them from the rows and refuses when they
disagree. Two false passes both look perfect in every declaration:

- **Evaluation rows inside the training period** - the declared windows are clean and disjoint,
  and the eval file simply contains training-year rows. Only the rows reveal it. Caught by
  `splits.actual_ranges_disjoint` and `splits.rows_within_declared_windows`.
- **An evaluation split with no negative examples** - it scores a meaningless AUC however
  carefully its counts are declared. Caught by `splits.eval_and_holdout_have_both_classes`.

Two measured properties decide whether a score means anything:

- **Enough independent positives.** Report the *clustered* count, not the row count, when
  positives arrive in clusters, and put confidence intervals on it.
- **Whether the base rate is stationary.** A rate that drifts with the phenomenon (e.g. rising
  with sea level) makes a single-year holdout a bad idea; document it as a property rather than
  treating it as a construction fault.

Three identifier properties are checked separately, because conflating them fails usable data:

- `splits.no_cross_split_entities` - an identifier in two splits is leakage. Hard fail.
- `splits.duplicate_entities_within_splits` - the same identifier twice *inside* one split is
  the source's grain. Refused unless the descriptor pins the known count with
  `expected_duplicate_ids`, so the build states its expectation instead of the gate guessing.
- `splits.repeated_identifiers_carry_one_label` - meaningful only against a claim. A descriptor
  asserting `id_columns_are_entity_keys` claims the identifier names one entity with one true
  label, and a contradiction fails. A descriptor making no such claim has the measured
  disagreement **recorded in the report** instead: a reused identifier is a property of the
  source, and refusing a dataset for a claim it never made rejects usable data for the wrong
  reason. The clustered event count is a claim like the others and is recomputed from the
  declared `event_key_column`, so inflating it is refused rather than believed.

"Not declared" is never "fine": missing declarations fail the gate rather than passing silently.

### 5. Runner compatibility - match the contract the runner actually reads

The layout is fixed (`public/train.csv`, `public/eval.csv`, `private/holdout.csv`,
`meta.json`) and the task reads `target`, `positive_label` and `id_columns` from `task.json`.
See `references/runner-contract.md`.

The defects that bite: a public holdout (it reaches the agent's workdir), a `meta.json` whose
`rows`/`positive_rate` disagree with the files, an `id_columns` entry that is also a feature,
and any column shipped beyond the declared set.

## Common failure modes

| Symptom | Cause | Action |
| --- | --- | --- |
| A shipped column scores AUC 1.0 | Label source (or its derivation input) written into a CSV | Remove from the written columns, not just from `FEATURES`; re-run the gate |
| Gate passes, numbers still wrong | Declarations trusted over rows | Recompute counts/windows from rows; the gate does this - read its report |
| Zero positives everywhere | Unit or reference-frame mismatch | Add a known-event fixture, fix the frame, cross-check against the publisher |
| Eval or holdout uniformly one class | Split built by a rule that correlates with the label | Rebuild the split; a uniform split cannot carry a score |
| Selftest passes but detects nothing | Fixtures drifted out of the defect they encode | Regenerate with `fixtures/build_fixtures.py`; re-run `--selftest` |
| Gate rejects a source's own grain | Descriptor is silent where the gate needs a claim | Declare `expected_duplicate_ids`, or drop a claim the source never made |
| Checker very slow / memory-heavy at scale | Per-level statistics built inside the row loop; a dict per row | Build the level table once, score in a second pass, read splits column-wise |
| Test contaminates the artifact | Loading code under test by path writes `__pycache__` into a bundled dir | `exec(compile(...))`, or assert no bytecode is written |
| Passes under UTC, fails elsewhere | Timezone-free timestamp parsed with `astimezone` under host TZ | Treat timestamps as UTC explicitly; run the suite under a TZ ahead of UTC too |
| A whole directory disappeared | `rmtree` on a user-supplied path | Clear generated paths through an ownership marker; name exact owned paths |

## Completion criteria

Qualified means all of the following are true and recorded:

- [ ] `quality.json` declares time column, event key, split windows, label source, and a
      known-event fixture where an external threshold is used.
- [ ] The gate exits 0 on the **full** artifact, on the worker, for this artifact version.
- [ ] `--accept` re-verifies that report against the on-disk bytes at hand-off.
- [ ] `--selftest` passes with the broken fixtures still broken.
- [ ] Every number that will be quoted is measured, with the command that produced it recorded
      beside it, and estimates are labelled as estimates.
- [ ] The candidate's notes carry the row-level evidence for source identity and for each
      column's documented meaning.

## References

- `references/runner-contract.md` - the exact input contract, quoted from the read-only
  benchmark checkout, including the column-selection code that makes leakage possible.
- `scripts/qualify_dataset.py` - the gate. `--selftest` proves it rejects every broken fixture
  and accepts the corrected one; `--accept` gates an artifact against its report.
- `fixtures/` - broken fixtures plus the corrected one, regenerated by
  `fixtures/build_fixtures.py`. `broken/` covers the general defect set, `broken-overlap/` the
  eval-rows-in-training-period false pass, `broken-single-class/` the eval-split-with-no-
  negatives false pass, `broken-duplicates/` and `broken-duplicate-labels/` the identifier
  claims, and `documented-repeats/` the measured-disagreement path.
