# Qualifying a built artifact before scoring

The vetting procedure picks a source and writes the task contract. This is the checklist for the
files that come out of construction, and it is the step that decides whether any number computed
from them means anything.

Where the project ships its own executable gate with fixtures, run that — it will be sharper than
a checklist. This is the shape such a gate should have, and the questions to ask when there is none.

## The five questions

1. **Leakage.** Can any shipped column determine the target? See the single-column AUC scan in the
   main skill. A declared feature list is not a control; only the file contents are.
2. **Prediction timing.** Is every shipped feature knowable at the stated prediction instant, and
   is each field's timing confirmed from its documentation rather than its name?
3. **Units and reference frames.** Does every value compared to an external threshold declare a
   unit and a frame, and is there a known-event fixture proving the comparison flags an event whose
   answer is already known?
4. **Splits.** Disjoint and correctly ordered *as measured from the rows*; both classes present in
   eval and holdout; enough positives and enough independent events to score.
5. **Runner compatibility.** Layout, target column, positive label and identifier declarations must
   match what the scoring harness actually reads — read the harness, do not assume.

Fail closed: a field the checker needs but the descriptor does not declare is a failure, not a
skip. "Not declared" is never "fine".

## Make the descriptor machine-readable

A prose manifest cannot be checked. Emit, beside the data:

- the target column and the positive label value;
- the prediction instant, in words;
- the time column used for split ordering, plus per-split `start`/`end`;
- the event key — the column whose distinct dates define one independent event — so clustered
  counts can be recomputed rather than believed;
- the feature list, the label sources, the post-hoc columns, and which columns are identifiers or
  free high-cardinality fields;
- measured per-split rows, positives and clustered events.

Generate those numbers from the rows that were just written, in the same code path that writes
them. A hand-maintained manifest drifts the first time the construction changes.

## Acceptance is by content hash

The gate writes a report containing every shipped file's digest plus one digest over them. The
downstream step re-verifies both before anything is scored or accepted:

```bash
<checker> --accept <report.json> <artifact-dir>
```

It must refuse a report that did not pass, a report produced by a different checker version, and
any file that changed after qualification. Without this, "we qualified it" means "we qualified
something like it at some point".

## Run it where the rows are

The check reads the data, so a bounded local sample cannot stand in for it. Run the gate on the
remote machine as part of the build job:

1. build the extract;
2. run the gate over it and capture the report;
3. exit non-zero when the gate fails, **after** writing the report, its rendered output and the
   extract to the collected output directory;
4. collect the diagnostics, then delete the worker — a failed job is still billable.

Only the compact report, the rendered checks and the manifest need to come back to the coordinator;
bulk data stays in staging. Copy a small `summary.json` to the collected root so the harness can
attach it to the job record.

## Package the gate with the code it checks

A gate that lives only on the coordinator cannot run where the rows are, and a vendored second copy
becomes stale the moment either changes. Assemble the job bundle from the canonical files at launch
time (candidate build + gate + entrypoint), generate the job descriptor from the same script, and
validate the result against the bundler's own rules — no symlinks, no hidden files, no caches,
only allowed suffixes, under the size cap. That way the bundle is byte-identical to the repository
and cannot drift.

## Fixture pairs, not one fixture

Every check that can fail needs a fixture that fails it and one that passes, asserted either way in
a self-test. Two deserve naming because they look correct in every declaration:

- evaluation rows drawn from the training period;
- an evaluation split carrying only one class.

A **conditional** check needs one more fixture: the shape that must be *accepted*. When a check
only applies against a claim the descriptor makes — an identifier declared as a unique entity key,
a tolerance declared for a known repeat — then the accepted case is a passing fixture in its own
right. Without it, the next session that sees a real failure naturally "fixes" it by making the
check unconditional again, reintroducing the exact defect the condition exists to avoid. Name each
fixture after the real case it pins, and keep a fixture per conditional branch rather than one for
the pair.

Regenerate fixtures from a script so they are deterministic, and keep the self-test asserting the
expected verdict *per fixture* — a fixture that stops being broken turns the self-test decorative.

## Loading a repository-owned gate skill

If the gate is also a skill kept in the repository, expose it through Hermes's supported external
skills directory rather than a symlink into the profile:

```bash
hermes config set skills.external_dirs <path-relative-to-HERMES_HOME>
```

Hermes resolves those entries against `HERMES_HOME` and treats them as trusted, so the skill loads
from the skill list with no security warning. A symlink from the profile's own skills directory
resolves outside it and logs a warning on every load. Verify discovery from a *fresh* session,
started from a directory outside the repository so project-local trust cannot be responsible, by
asking it to name the skill and its commands — a fresh session is the only honest test of whether
the skill is reachable. If the `hermes` launcher is not on the PATH, invoke it through the
interpreter of its own virtual environment.
