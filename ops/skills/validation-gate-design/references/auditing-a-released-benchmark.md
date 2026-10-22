# Commissioning an independent audit of a released artifact

Use when a dataset, model card or benchmark is about to be flipped public and you want a verdict you
did not write yourself. The audit is a gate performed by someone whose incentives and code are not
yours; scope it so that a pass means something.

## Scope the auditor away from your pipeline

State explicitly: **do not read the repository that produced the artifact**. An auditor who reads the
generator inherits its assumptions, and the defects that matter are exactly the ones baked into the
generator. Give them the artifact, the release tag, and the claims to test - nothing else.

Give them the claims anyway, as falsifiable statements. "Baseline AUC 0.55", "splits are temporally
disjoint", "every feature is known at the prediction instant". A claim they can refute is worth more
than an open-ended "check it over".

## The checklist, in dependency order

Each item can invalidate the ones before it, so run them in this order and never report a later pass
as if it rescued an earlier failure.

1. **Integrity.** Re-hash every downloaded file against the manifest and the sums file. Report a file
   present in one and not the other, and confirm the release tag resolves to the same commit as the
   default branch.
2. **Label reconstruction.** Recompute the label from the released columns alone, row by row, and
   report disagreements with row identifiers. If it cannot be recomputed, name the missing column -
   that absence is itself the finding.
3. **Temporal safety.** For every feature, decide whether it existed at the declared prediction
   instant. Flag late-published period statistics, label-derived columns, and any value whose
   availability depends on a later revision. Name columns; never generalise.
4. **Population selection.** Ask what decided which rows exist. A rule that reads a later period, or
   a whole-snapshot count, conditions the sample on the future even when every feature is clean.
5. **Split boundaries.** No entity in two splits, ordered in time, and no training row whose target
   falls inside the evaluation window.
6. **Baseline reproduction, plus naive references.** Reproduce the shipped number, then compute
   persistence, an entity mean and a calendar prior on identical rows. A reproduced baseline that
   loses to a one-line rule is a finding about the task, not about the model.
7. **Holdout exposure.** Whether the holdout ships with labels, and whether blind scoring needs
   anything absent from the package.
8. **Licence and documentation.** Whether the stated licence matches the publisher's terms, and every
   README statement that conflicts with what was measured.

## What to demand in the report

- A table of the checks with PASS / FAIL / UNCERTAIN and one line of evidence each. `UNCERTAIN` is a
  legitimate verdict and is more useful than a guess.
- The three findings most likely to invalidate the artifact, each with the row or column that proves
  it.
- The numbers they computed, with enough detail to re-run them, and the file digests they audited.
- No remedy. An auditor who proposes fixes starts designing around the defect; you want the defect
  located, then you decide what to rebuild.

## Reading the verdict

`The bytes reproduce` and `the benchmark is valid` are different claims. An audit can pass integrity,
labels and splits and still fail the task, because the description and the construction disagree.
Treat a partial verdict as a failure of the strongest check that failed, not as an average.

When the auditor finds a defect, three things follow in this order: stop the release (pull the
candidate back from any approval queue and say plainly that the staged artifacts must not be
published), record the finding verbatim with its evidence, and only then decide whether the fix is a
rebuild or a relabel. A relabel is legitimate only when the bytes are right and the words are wrong;
when the construction is what failed, the bytes are wrong too.
