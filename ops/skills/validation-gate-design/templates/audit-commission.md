# Audit commission prompt (copy, fill the placeholders, send)

Give this to an agent with `gh` authenticated and read access to the repository. Replace every
`<...>`. Keep the rules block verbatim - it is what makes the report usable.

---

You are performing an independent audit of a packaged research artifact. Read-only: download,
inspect, recompute, report. Do not modify, push, tag, or "fix" anything. Do not read the repository
that produced it (`<pipeline-repo>`) - audit this artifact on its own terms.

## What it is
Artifact: `<owner>/<name>` (private; `gh` is authenticated)
Release: `<tag>`
Claimed artifact version: `<digest prefix>`
Source: `<publisher, url, licence>`
Task: `<one paragraph: unit of prediction, prediction instant, label rule, splits>`
Claimed numbers: `<rows per split, baseline AUC/Brier, positive rates>`

## Get the data
```
gh release download <tag> -R <owner>/<name> --dir audit
gh api repos/<owner>/<name>/contents --jq '.[].name'
```
Fetch `MANIFEST.json`, `SHA256SUMS`, `DATA_DICTIONARY.md`, `README.md`, `VERIFICATION.md`, the
runner `code/`, and the split files.

## Audit, in this order
1. INTEGRITY. Re-hash every file against `MANIFEST.json` and `SHA256SUMS`; report files present in
   one and not the other; confirm the tag resolves to the same commit as the default branch.
2. LABELS. Recompute the label from the released columns alone, row by row. Report the number of
   disagreements with row ids, or name the column that makes recomputation impossible.
3. TEMPORAL SAFETY. For every feature, decide whether it existed at the declared prediction
   instant. Name any column that carries period statistics published later, any label-derived
   leak, and any value whose availability depends on a later revision.
4. POPULATION SELECTION. What decided which rows exist? Flag eligibility that reads a later period
   or a whole-snapshot count - that conditions the sample on the future even with clean features.
5. SPLITS. No entity in two splits, ordered in time, no training target inside the eval window.
6. BASELINE. Reproduce the shipped number, then compute persistence, an entity mean, and a
   calendar prior on identical rows. Say plainly whether the model beats each one.
7. HOLDOUT. Whether it ships labelled, and whether blind scoring needs anything absent.
8. LICENCE AND DOCS. Whether the stated licence matches the publisher's terms, and every README
   statement that conflicts with what you measured.

## Report format (under 900 words)
A table of the eight checks with PASS / FAIL / UNCERTAIN and one line of evidence each. Then, in
severity order, the three things most likely to invalidate the artifact as a benchmark, each with
the row or column that proves it. Then the numbers you computed, in enough detail to re-run you, and
file digests with the paths they belong to.

Rules: report what you measured, not what you expected. `UNCERTAIN` is a legitimate verdict - if a
check cannot be performed, say what would be needed instead of substituting an assumption. Quote
file paths and hashes for anything you claim. Do not propose fixes; locate the defect.

---

## Re-auditing a fix (use when a previous audit failed the artifact)

A first audit tells you whether the artifact is sound. A re-audit after a fix answers one narrower
and harder question: **was the mechanism changed, or only the description?** Open with that framing,
and keep the prompt short - the numbered checks above are mostly settled and re-running them burns
the budget on numbers you have already agreed on.

```
This is a RE-AUDIT. Both previous audits found real defects that the publisher had already
called fixed, so treat every claim below as unproven until you reproduce it. This pass is
narrow: confirm the two fixes, then check that the documents no longer say anything untrue.

## The decisive check
The publisher claims <the rule, stated as a mechanism: "a row's eligibility is decided by period
M alone; a period-M+1 volume below the gate must not remove it">.
- Read `<build script>`, quote the selection loop with line numbers, and say which periods feed
every condition that decides membership.
- Reproduce the counterfactual from the released data: take a shipped row, change ONLY the later
  period's value, rerun the selection in memory, and report whether the row survives. Repeat for
  one row in each split.
- Then the reverse: lower a history-period value and confirm the row disappears, so the gate still
  bites where it should.
If a single later-period edit removes a row, the fix has failed again.
```

Then require the rest in a fixed order: a verdict line (are the defects fixed, yes or no, with the
evidence), the counterfactual result as a count of rows changed (expect zero), a check table, every
false or unsupported sentence quoted with file and line, and anything that would stop publication.

Notes that make a re-audit sharper:

- **Name the failure pattern in the prompt.** An auditor told "a fix asserted in documentation and
  absent from the code is a failed fix" reads the build script instead of the README.
- **Give the previous audit's numbers as targets to confirm or refute**, not as facts. A value that
  reproduces exactly is evidence of stability; one that drifts is a finding either way.
- **A pass on documentation alone is not a pass.** Say so in the rules block, or a tidy README will
  read as a fixed build.

## Notes for the commissioner

- Send the claimed numbers with the prompt. An auditor who has to guess your baseline spends the
  budget rediscovering it, and one who cannot see the claim cannot refute it.
- Say separately which claim you already doubt. "The publisher states the baseline loses to mean
  reversion, so that is not the finding I need" focuses the audit on the construction.
- The most valuable output is usually a **count**: rows that could not be reconstructed, features
  with a late publication date, disagreements between a declared rule and the code that ran. Counts
  survive being wrong; adjectives do not.
- Do not run your own audit and call it independent. If the auditor's checkout shares your working
  tree, the isolation is gone.
