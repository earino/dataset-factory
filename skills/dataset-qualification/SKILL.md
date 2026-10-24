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
sample cannot stand in for it; run it and exact-byte `--accept` on the worker. Keep the
full dataset off the coordinator even when it happens to fit; collect compact evidence.

Make the worker entrypoint's order explicit: **construct → qualify → accept exact
bytes → score → report**. Stop before scoring on any failed stage. Construction may
write the diagnostics the gate needs, but must not compute/log baseline performance
or present its rates as qualified findings before acceptance. A later passing report
does not retroactively make earlier scoring comply. Inspect the invoked build script,
not just the shell wrapper, for hidden early scoring.

The boundary is the computation, not its name or output format. Joining published
periods into examples with lag features/targets and computing persistence AUC is
construction and scoring, even entirely in memory with no CSV or fitted model.
Do not run it locally as a "pre-launch ceiling", "cheap probe" or "go/no-go test".
If numerical task-performance evidence is needed, construct and qualify the full
artifact on a worker, accept its exact bytes, then compute references. Otherwise
use bounded source metadata, schema, coverage/counts and documented semantics to
decide the next step without scoring a prediction panel. A persistence result is
a comparator, not a proven upper bound on every other model's performance.

### Worked worker order: review the code that each command calls

Adapt these filenames/arguments to the job bundle; this illustrates ordering, not
a replacement runner. `build.py` only constructs files and gate diagnostics.
`score.py` invokes the existing runner/references and never rewrites qualified files.

```sh
set -eu
python3 /workspace/build.py --out /output/extract
python3 /workspace/qualify_dataset.py /output/extract --json \
    --report /output/qualification.json
python3 /workspace/qualify_dataset.py --accept \
    /output/qualification.json /output/extract
python3 /workspace/score.py --data /output/extract
```

Any failed command stops before the next one. Keep the failed gate report for
collection. A wrapper ordered this way is still wrong if `build.py` computes AUC
internally: move that computation and its logging into the accepted scoring stage.
Trace imports/helpers too. A previous candidate's script is historical evidence,
not a vetted template; preserve its old results but do not copy its defects.

Before launch, cite the actual row filter and stage boundaries in a compact source
preflight. Check that every declared eligibility field matches the filter. Selecting
only records with a terminal outcome at today's snapshot can condition evaluation
on future completion; labelling the others "unobserved" does not resolve that bias.
A checker trusting the declaration cannot establish its truth. Resolve the intended
population and observation mechanism before launch, or leave an explicit hold.

For a majority-class accuracy reference, fit the constant label on **train** and
measure its agreement with **that evaluated split's labels** after acceptance:
`majority = int(train_positive_rate >= 0.5)`;
`accuracy = sum(y == majority for y in eval_labels) / len(eval_labels)`.
Handle an empty split explicitly. Copying `train_positive_rate` into an accuracy
field measures neither eval nor holdout accuracy. A constant score has no ranking
information; it is not a meaningful independent calendar/identity control.

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

### The baseline triad - one AUC is not evidence

Before any AUC is quoted as evidence that the task teaches something, measure three references on
**exactly the same evaluation rows**:

1. **Persistence** - the most recent observed value (or last observed label) as the score. This is
a reference the model must improve on to support a headroom claim. If the model trails it,
inspect alignment, availability, uncertainty and split shift before interpreting the task.
2. **Calendar-only** - country/entity identity plus cyclical week-of-year plus a seasonal prior
   estimated only from training-era rows. This tests that particular seasonal/identity
   reference; beating it does not rule out all seasonality or prove a causal source of signal.
3. **The full model**, on the same rows and the same fit/eval boundary.

Verify each reference implements its claimed information set and evaluates predictions
against that split's labels. Training prevalence is not held-out accuracy; a supposedly
different control that always falls back to the same predictor is not independent
evidence. Record degenerate or inapplicable controls explicitly instead of relying on
the names of fields in a result dictionary.

Separate the observed difference from its uncertainty. A lower measured AUC is an
observed result even without intervals; its generality and precision remain uncertain.
Use paired differences on the same rows with an appropriate dependence-aware interval,
not overlap of two marginal intervals as the comparison test. An interval containing
zero does not establish equality or parity: report an inconclusive difference unless
a pre-specified equivalence margin and analysis support an equivalence claim.

Report the gap, not just the top-line AUC. A model below persistence is a **recorded defect**, not
an encouraging result: on a four-week-ahead exceedance task a baseline reached 0.870 while week-W
persistence reached 0.893, and that single comparison changed the dataset from "promising" to "not
yet a forecast". Write the comparison into the record next to the number, so no later reader quotes
the model AUC alone.

Two structural checks belong with it:

- **Per-year, not pooled.** A pooled eval window that contains a structural break (a pandemic, a
  policy change, a reporting-system migration) hides the break inside one number. Report AUC and
  Brier by target year as well.
- **Prevalence shift between splits.** Compare positive rates per split and per year. A training
  split at ~59% positives scored against an evaluation window at ~24% is an out-of-distribution
  test as much as a temporal one. Investigate whether conditional distributions or
  calibration changed; prevalence alone does not mathematically determine AUC. Say what
  was measured rather than letting a pooled AUC imply a clean temporal split or a cause.

When persistence dominates, a substantively useful **change** target (onset, transition or
sustained exceedance) may warrant a new task instance. It does not guarantee headroom:
persistence or another simple rule can still win. Specify the user need and protocol first,
then qualify and compare anew; do not choose a target because it improves a held-out score.

### When the task itself is the finding

Audits make artifacts correct; they do not establish task usefulness. If a simple reference
beats the tested full model, record **no demonstrated headroom under this protocol**, with both
scores on identical rows. That finding does not prove that every competent model must lose.
Check a concrete diagnosis (misaligned rows, a post-hoc reference, prevalence shift, or an
implementation defect) within a bounded repair. If validated comparisons still show no useful
headroom, preserve the negative finding and drop or explicitly re-scope the candidate. Do not
publish a benchmark claim unsupported by the comparison, or keep fitting until a score wins.

Specify metrics, split boundaries, target/threshold and comparisons before evaluation. Fit
priors and data-derived thresholds on training data only unless a fixed external domain standard
supplies the threshold. Keep holdout out of target/feature/split selection and model tuning.
For clustered data, use independent-event counts and appropriate uncertainty; label missing
intervals as a limitation. Missing historical vintages remain a limitation, never a claim of
point-in-time reconstruction. Select tasks for utility and headroom, not agent outcome variance.

Budget the repair, too: **one rebuild per structural defect**. A second and third rebuild of the same
construction usually means the defect is in the task design (a period-end instant that cannot be
verified, a population chosen with hindsight), not in the code. When the third audit returns a fourth
timing problem, the honest move is to stop and re-target or drop - the cost of continuing is paid in
audits that keep finding real defects in a task nobody should ship.

**Replicate the decisive number independently.** The comparison above is the one a reviewer will
audit, so have a second implementation compute it from the published artifact with its own code -
not a re-run of yours. Give it the same rows and forbid reading your implementation; if its
calendar-only AUC lands near yours the finding stands, and if it diverges the likely bug is in your
baseline, which is exactly what the check is for. State in the report that the full-model figure was
quoted rather than independently rerun.

### Answering an external review with measurements

A review supplies hypotheses to test. First ensure full-artifact qualification and acceptance;
then use the cheapest discriminating measurement and report its scope and uncertainty:

- **Seasonality** -> calendar-only AUC on identical rows (above). A small or large observed gap needs its rows, uncertainty and scope;
  no universal AUC difference proves usefulness.
- **Mixed populations** -> count eligible rows per provenance stream from the source itself, and
  say what fraction of the panel survives the stricter definition.
- **Leakage through the timing claim** -> check whether the publisher exposes historical vintages.
  If only the current vintage exists, the audit is **not performable**; say so and state the cutoff
  as an assumption with its justification, rather than dressing a guess as a reconstruction.

What cannot be measured must be labelled, not argued away. The output of this pass is a short record
block (the numbers, the rows they came from, and the conclusion) so a later reader cannot quote the
top-line figure without the comparison that qualifies it.

## Building a panel that does not fit in memory

A multi-year daily panel is tens of millions of rows before filtering, and the coordinator has a
couple of gigabytes. Construction must stream, not accumulate:

- **Write each batch to disk; never hold `to_dict("records")`.** A dict per row costs about a
  kilobyte, so seven million rows is several gigabytes of overhead before the values themselves.
  Emit per week (or per source file) straight into the split files, with the header written once.
  Memory then stays flat regardless of panel size.
- **Reduce each source file as it lands.** Aggregate a 45 MB monthly CSV to a weekly parquet in a
  prep pass and delete the CSV; thirty-six months of raw files will exhaust a small scratch disk
  even though the aggregate is under 100 MB.
- **Filter through the dimension table, and fail if the filter matches nothing.** A state or
  category filter silently matched zero rows because the aggregation step had dropped that column,
  so the build processed the entire country and looked merely slow. Assert the filtered row count
  is non-zero and log the before/after counts.
- **De-duplicate weeks that straddle source files.** A week appearing in two consecutive monthly
  files is emitted twice; the gate catches it as duplicate ids, which is late and confusing.
  Keep a set of processed periods.
- **One column list, in one place.** Building `ordered` from `["id", *FEATURES, TARGET]` where
  `FEATURES` already contains the identifiers writes duplicate headers, doubles those columns'
  values and breaks every per-column check downstream. A duplicate header is a construction bug,
  not a formatting quirk.
- **Unbuffered output.** Pipe-buffered logs make a running build indistinguishable from a hung one;
  run with `python3 -u` and print progress per source file.

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

**Knowable at the period is not knowable at the release.** A statistical release publishes after its
period ends - NHS England's monthly A&E data lands about ten days late, FluNet about a week - so a
feature stamped "month M" did not exist at the end of month M. If the prediction instant is the
period end, every such feature is an oracle. This defect reached `packaged` once
(`nhs-ae-four-hour-decline`, 25 features, audited 2026-10-21); the string
`features_documented_at: "prediction_time"` was true of the period and false of the release.

Every `quality.json` must carry a `timing` block, and the gate refuses the dataset without one.
A passing timing check means the declaration is coherent - it does not mean the build implements
it, which is what the counterfactual test below is for:

```json
"timing": {
  "prediction_instant": {"kind": "publication", "period": "M",
                         "days_after_period_end": 10, "citation": "<publisher release calendar>"},
  "features": {"period": "M", "published_days_after_period_end": 10,
               "source_kind": "statistical_release"},
  "row_selection": {"latest_period_used": "M", "fields": ["..."],
                    "basis": "eligibility uses only months up to M"},
  "observations": [{"period": "2026-08", "period_end": "2026-08-31", "published": "2026-09-10"}]
}
```

- **`kind`** is `publication`, `period_end` or `event_time`. `period_end` is only admissible when
  the feature lag is zero.
- **`observations`** are observed release dates, not the schedule you assumed. A
  `statistical_release` needs at least one; an `administrative_record` (a citation written at the
  event, a 911 call closed at the event) may ship none.
- **`row_selection`** must not reach past the instant. Using M+1 to decide which rows qualify
  conditions the population on the future even when every feature is clean.
- **Observed lags and margins are evidence, not a guarantee.** Publications slip; a
  sample's mean, maximum or maximum plus margin cannot prove availability for every
  row. Use actual release/snapshot evidence across the constructed periods or a
  supported conservative as-of rule, and document coverage and unresolved exceptions.
  Current revised rows cannot stand in for values available at an earlier instant.
  If historical availability cannot be established, exclude that feature or keep
  the candidate unresolved. A later instant requires a useful future outcome and
  redesigned eligibility/splits; never move it past the outcome merely to pass the
  declaration check. The gate's minimum observed-date requirement is unchanged and
  does not certify this broader scientific claim.

#### Removing the history count is not removing the future

A selection can be fixed at the top and stay broken in its loop. Counting `MIN_MONTHS` of history
`<= M` is the visible half; if the row list is built by pairing consecutive *qualifying* months,
the target month still has to clear the volume gate for the M row to exist, so a quiet month
deletes the forecast that preceded it. Two rounds of audit found this: the first fix changed the
count, the second was still failing on the pair list.

The rule: **iterate the provider's months, not pairs of qualifying months.** Eligibility reads only
`<= M`; the target month is looked up afterwards, solely to compute the label. A missing or
thinly-attended target month is *missing outcome data* - count it in its own bucket
(`unobserved_target`) and report it - never a membership decision.

Pin it with the smallest counterfactual rather than a declaration: build a panel with a full
history and one target month below the volume gate, and assert the M row is emitted. On the
pre-fix code the row vanishes, which is what makes the test worth keeping. Do the reverse too
(lower a *history* month, expect the row to disappear) so the gate is shown to still bite.

The gate checks `timing.instant_declared`, `timing.publication_lag_measured`,
`timing.features_available_at_instant`, `timing.instant_accounts_for_publication_lag` and
`timing.selection_uses_only_available_data`. `tests/test_timing_gate.py` pins each failure shape.

Then sort every column into available / post-hoc /
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
| Test contaminates the artifact | Loading code under test by path writes `__pycache__` into a bundled dir; a host that sets `PYTHONDONTWRITEBYTECODE` hides it, so CI's fresh checkout fails the no-cache check | Load by `exec(compile(...))`, and confirm in a clean clone with bytecode writing *enabled* - the local pass proves nothing if the shell disables it |
| Passes under UTC, fails elsewhere | Timezone-free timestamp parsed with `astimezone` under host TZ | Treat timestamps as UTC explicitly; run the suite under a TZ ahead of UTC too |
| A whole directory disappeared | `rmtree` on a user-supplied path | Clear generated paths through an ownership marker; name exact owned paths |
| A model AUC is quoted with no reference | Only one baseline was ever run, or the reference lives in a notes field nobody compares | Run the triad (persistence, calendar-only, full model) on identical rows; record all three beside the number |
| The gate dies with `ValueError: labels and scores must align and be non-empty` | A split has a duplicate header or a ragged row, so one column's values no longer align with the labels | Fix the build's column list; the gate now reports `leakage.every_column_could_be_scored` naming the column and split instead of aborting - keep that behaviour, a bare traceback hides which column is malformed |
| The model trails a one-line rule | The label is largely persistent, or the eval window shifts prevalence | Record it as a defect; re-target a change/onset label or report the task as persistence |
| A future row in the same shipped file reveals a row's label source | The label is the future value of a shipped feature column, so the batch join `same key, later timestamp` reconstructs the label | Run the blind cross-row join the attacker would run: for every row, look up every shipped feature row at the label's source instant and test whether thresholding it reproduces the label; any zero-mismatch recovery over more than a rounding-level fraction of rows fails the gate (nz-ea v2026.10 scored eval AUC 1.0 this way after the single-column sweep passed) |

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
