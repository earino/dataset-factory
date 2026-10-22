---
name: validation-gate-design
description: "Use when a gate rejects an artifact or you add a check."
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [validation, gates, checks, fixtures, false-positive, qualification, acceptance]
    category: software-development
    related_skills: [test-driven-development, systematic-debugging, ephemeral-worker-lifecycle]
---

# Validation gate design

## When to use

Writing, extending or debugging an automated check that decides whether an artifact is acceptable
before it is scored, published, shipped or accepted: a dataset qualification gate, a schema or
contract validator, a release acceptance test, a CI quality gate. Also - and this is the more common
case - **immediately after a gate has rejected something**, when you are deciding whether the
rejection is a defect in the artifact or a defect in the check.

A gate that rejects valid work is not a safe gate. It is a broken gate with good manners, and its
failures look exactly like real ones.

## The rule that matters most

**A check may only fail on a property the artifact actually claims.**

Every check is a new way to reject valid work, so each one must establish that its subject is real
before it can fail on it. A check that invents a claim rejects a correct artifact with a confident,
specific, wrong message - and the cost is not only the false verdict: the honest response to a red
gate is to go and change the artifact, the pipeline, or the data.

When a check rejects something, the first question is not "what is wrong with the artifact?" but
"does this artifact claim the property I am asserting?" Answer that before touching anything.

## Procedure

1. **Write the claim down in one sentence, and say where it lives.** For each check, its subject is
   one of:
   - **measured** from the artifact (recompute it from the bytes or rows),
   - **declared** by the producer (a descriptor the artifact ships),
   - **a source property** the producer knows and the artifact cannot prove on its own.

   A check whose subject is none of these is an invented claim. Delete it, or make the producer
   declare it first (step 4).
2. **Recompute declared values; never enforce undeclared ones.** These are the same discipline seen
   from both sides. A declared count, boundary or rate must be recomputed from the artifact, or the
   declaration *is* the evidence. And a property nobody declared must not be enforced, or you are
   grading the artifact on a promise it never made.
3. **One check, one claim.** When a single check asserts two things, split it. A conflation produces
   a message nobody can act on: an identifier reported as appearing "in train and train" is a
   within-split repeat wearing the wording of cross-split leakage, and the reader investigates the
   wrong thing. Distinct named checks keep each verdict actionable and independently reasoned about.
4. **When the subject is a source property, make it a declaration and record the measurement.** Some
   properties cannot be judged without the producer saying what the source is like - the grain of an
   identifier, whether a repeated key is one entity or several. For those:
   - the descriptor declares the expectation (a count, or a boolean claim such as
     `id_columns_are_entity_keys`),
   - the check recomputes the measurement from the artifact anyway,
   - an **absent declaration with a non-zero measurement fails**, telling the producer to declare it.

   This is not a silencing knob. The declaration is a factual claim about the source, and the check
   fails when the artifact contradicts it - so asserting a property and then violating it is a
   failure, while not asserting it and recording the measurement is a documented pass.

   **When the property is about time, declare the date, not the vocabulary.** A token such as
   `features_documented_at: "prediction_time"` can be true of the *period* the data describes and
   false of the *release* that published it, so a check comparing that token grades wording rather
   than fact. Require what dates the claim: the kind of instant (`publication`, `period_end`,
   `event_time`), the lag in days, at least one **observed** `period_end -> published` pair with a
   citation, and the latest period any row selection reached into. Then a period-end instant for
   features published ten days later fails arithmetically, and an absent block fails outright -
   absence is the state that lets the defect ship. Make the observation requirement depend on the
   **kind of source** rather than on the dataset: a statistical release must show an observed
   release date, while an administrative record created at the event may honestly declare zero lag
   with no observation. Without that split the rule is vacuous for one half of the corpus and forces
   fabricated evidence for the other. Schema, check table and the proof procedure:
   `references/temporal-availability.md`.
5. **Pin both directions with fixtures.** For every check, ship a fixture that must fail **and** a
   fixture that must pass with the same shape. A selftest that only asserts rejections cannot catch a
   wrong-accept, which is the failure mode that matters: real data has to get through.
6. **Run the selftest after every check change, and treat its verdicts as evidence about the check.**
   A fixture suite is the only thing that exercises a check's logic directly, and it catches bugs
   inside the new check itself - a check that compares one occurrence of a value against the other
   will pass a self-contradictory pair, and only a fixture reveals that.
7. **Version the gate, and bind every verdict to that version and to the artifact.** The report must
   carry the gate version and the artifact's identity, and the acceptance step must re-verify both.
   bump the version when check *names or semantics* change, not only when checks are added, so a
   stale report cannot be read as a current one. Then require the passing report before the artifact
   is scored, cited or accepted.

   When one artifact is gated **in parts** - a level per report, a shard per run - expect there to be
   no single version for the whole: keep each part's gate-produced version, keyed by part, and bind
   each verdict to its own. If a consumer needs one handle, derive a combined label **and mark it in
   the record as derived**, naming what it was composed from. A composed digest that sits beside
   tool-produced ones and is not labelled reads as something the gate emitted, which is a fabricated
   verdict identity; and never reconcile the two by promoting one part's version to stand for all of
   them.
8. **Confirm a validation-only change did not touch the artifact.** When a fix is confined to the
   checks and the declarations, the artifact bytes should be unchanged: identical digests across runs
   is positive evidence, and a moved digest means the change reached the data path.
9. **Bias the residual risk towards false passes.** When you cannot decide whether a condition
   should be a failure, make it a reported measurement rather than a silent pass *or* an invented
   failure. The report is where judgement belongs; the exit status is for claims you are sure of.
10. **Require a new check from the earliest stage that depends on it.** Stages form a ladder
    (`investigating` to `ready` to `packaged` to `published`), and a check attached to the wrong rung
    is a check that never fires where the rule says it must. When the rule reads "decide this *before*
    building", the required-set starts at the stage where that decision becomes binding - so derive
    it as `(first_stage,) + later_stages` rather than reusing the set of the stage you happened to be
    editing. Pin every stage boundary with a fixture that must pass and one that must fail, or a
    silently disarmed check looks exactly like a satisfied one.
11. **When a defect has already escaped, fix the process before the artifact.** After an audit finds
    a class of defect in something packaged, the first deliverable is the check, the declaration it
    reads and a guard proven to fail on the pre-fix input - not the rebuild. Rebuilding first ships
    the same class again on the next dataset, and the operator will say so. State the order
    explicitly in the record, then rebuild once the gate can refuse the defect.

## When the gate you must satisfy is someone else's

A gate standing between you and an expensive run is usually one you did not write, and the cheapest
place to discover your artifact does not satisfy it is a machine that costs nothing.

1. **Build a slice that populates every state the gate inspects, and run the gate against it
   locally first.** Every split, both classes, at least one row inside each declared window, and
   enough rows per categorical level that the gate's own branches execute - a slice that skips a
   branch validates nothing about it. The loop is seconds long locally and a full provisioning cycle
   remotely, so a gate discovered as unsatisfiable on a paid machine has already cost the machine.
2. **Expect the failures to be descriptor shapes, not data.** A gate reads its subject from a
   declared descriptor, and that declaration is a schema: counts keyed per split rather than as a
   total, windows as start/end objects rather than a pair of strings, each measured column carrying
   its own unit and frame, a judgement recorded under the exact key the checker looks for. Read the
   required shape out of the checker itself instead of inferring it from a sibling artifact.
3. **Iterate on the slice until it passes, then dispatch once.** Everything the gate asserts about
   leakage, timing, splits, units and the consumer's contract is then checked before the paid run,
   and the run is spent on data rather than on discovery.
4. **Know what the gate does not assert.** A gate asserts the properties it names - leakage, timing,
   shape, contract. It never asserts that the run consumed all of its inputs, so a build that lost a
   fraction of them to failed calls exits cleanly, passes every check, and is not the panel it claims
   to be. Completeness is a separate claim the producer declares and enforces - units expected,
   built and missing, recorded in the run's summary with a non-zero exit when anything was lost. A
   gate read as proof of completeness is a false pass in the direction that matters most, because the
   artifact goes on to be   published. Mechanics: `ephemeral-worker-lifecycle`.
5. **When the verdict must come from someone else, scope the audit like a gate.** Independent review
   is the only check on the assumptions baked into your own generator, so keep the auditor away from
   that generator, give them the claims as falsifiable statements, and require evidence per claim
   rather than an overall impression. Checklist and report shape:
   `references/auditing-a-released-benchmark.md`; the prompt to hand the auditor, ready to fill in:
   `templates/audit-commission.md`.

## Pitfalls

- **Reading a gate's crash as a defect in the gate.** A validator that dies with an unrelated
  exception - an `AttributeError` deep in a helper, or a message about labels and scores not
  aligning - is usually describing the shape of *your* input rather than a fault in its logic. A
  duplicated column name in a header is the classic: a column-wise reader appends per index, so the
  repeated name collects twice as many values as there are labels and the failure surfaces several
  functions away from the cause. Read the artifact's own header and descriptor before editing the
  check - and make the check report that malformed input as a *named failure* rather than dying
  inside a scorer: catch per-column scoring errors, emit one check that names the column and the
  split, and keep the report machine-readable. A gate that crashes costs a round trip and hides
  which column was wrong; a gate that fails tells the producer what to fix.
- **Declaring the grouping column where the checker expects the row identity.** Where a checker takes
  the entity from the first declared identifier, a panel whose entities legitimately recur across
  time splits - the same subject appearing in train and in eval - reads as cross-split leakage *and*
  as within-split repetition, both of them false. Declare a unique row-level identifier first, leave
  the grouping column as an ordinary column, and let the row identifier be the thing that must not
  cross a split. Read the window comparison too: bounds are commonly half-open, so a declared end
  equal to the last row's date fails as "at or past its declared end" and the correct declaration is
  the day after.
- **Asserting a claim the artifact never made.** The central failure. A repeated identifier is not
  automatically one entity; a duplicated value is not automatically an error; a missing field is not
  automatically required. Ask what the artifact declares before failing it, and say so in the message
  when the answer is "nothing".
- **Treating the honest response to a red gate as the only response.** A red gate is evidence about
  one of {artifact, check, environment}. Reading the artifact's own rows before editing either is
  what separates a defect from a false failure - and a false failure "fixed" by relaxing the
  producer's data is the worst outcome of the three.
- **Adding a tolerance to make a failure go away.** A threshold that exists to silence a check is a
  check that no longer runs. If a real property needs slack, the producer declares the measured value
  and the check fails above it, so the number stays visible and a regression still shows.
- **Enforcing a property the artifact does not declare, because it is "obviously" true.** Obviously
  true properties are exactly the ones nobody writes down, so an agent reading only the gate cannot
  tell a violation from an omission.
- **Trusting a declaration you never recompute.** A declaration is a claim to be checked, not an
  input to be believed; a gate that only reads declarations grades the descriptor, not the artifact.
  This is worst where the declaration is a **token rather than a value**: a feature stamped
  `prediction_time` can mean the period the data describes or the release that published it, and the
  sincere reading is often the wrong one - a monthly release lands days after its period closes, so
  a period-end instant silently uses the future. When a declaration names a time, a boundary or a
  schedule, require what dates it (the kind of instant, the lag in days, one observed
  `period_end -> published` pair, the latest period any row selection used) and fail on absence.
  Selection is the same claim in another place: eligibility that reads a later period conditions the
  population on the future even when every feature is clean.
- **Adding a check to fix a false pass and shipping a false fail.** The new check has its own premise
  and needs its own fixtures in both directions; a check written quickly to close a hole is usually
  the one carrying an unexamined assumption.
- **A selftest that is green because it only tests the reject path.** Deliberately include the
  must-pass shapes, and when a check changes, re-derive the fixture from the new claim rather than
  from the old one.
- **Reporting a verdict without the artifact version it belongs to.** "Qualification passed" means
  nothing once the artifact is rebuilt; a report is reusable only while its recorded artifact
  identity still matches the bytes.
- **Reconstructing a truncated identifier from its display.** When recording a hash, digest or id in
  a report or record - especially a long one your own tooling showed only as a prefix - read the full
  value from the source of truth. A value completed from a display is a fabrication, and it looks
  authoritative while being unverifiable. If the full value cannot be fetched, record the prefix and
  label it as one.
- **Reading a gate's exit status through a pipe.** `gate.py | tail` gives you the exit status of
  `tail`, not of the gate, so a refusal reads as a pass and you report a defect that does not exist.
  Redirect to a file or read the status on the bare command before concluding anything about a
  gate's verdict - and when you catch yourself about to report a gate bug, re-measure the status
  first. The same trap hides a real non-zero status behind a green-looking display.
- **Reporting a pattern-match hit without reading it in context.** A leak or forbidden-content scan
  is a check like any other, and a broad pattern asserts a claim the artifact may never have made: a
  scan for a private repository name matches its public sibling, and a scan for internal ids
  matches the deliberately public artifact version. Print each hit with surrounding context and judge it before
  reporting; a scan that reports without reading manufactures false defects and trains the reader to
  ignore the real ones.
- **Auto-supplying a judgement the gate actually needs.** Some subjects cannot be computed, only
  judged - whether a task already exists elsewhere, whether a source's terms permit redistribution.
  Do not let the check guess or pass by default: take the judgement as an explicit, enumerable input
  (with one value that means *do not proceed*), record the evidence the judgement was made from
  beside it, and refuse to pass when it is absent. A gate that invents the judgement is worse than no
  gate, because it launders a guess into a recorded verdict.
- **A fixture or cross-check that carries none of the phenomenon it tests for.** A single-class
  fixture, an all-zero sample, or a comparison window with no events passes for every
  implementation, including a broken one, so a green run is evidence about the fixture rather than
  the check. Give it enough of the property to separate right from wrong, and assert that the
  intended branch actually executed - a methodology validated on a quiet sample is not validated.
- **A check that encodes one instance's convention.** A validator that computes its expected values
  from a rule rather than from the producer's declaration can be permanently unsatisfiable for a
  second instance: a path rule like `data/<file>.csv` holds for a flat release and can never hold for
  one laid out in levels, so the check refuses a correct artifact no matter what the artifact does.
  Derive expected values from what the artifact declares, keep the old convention as the documented
  default so the first instance's verdicts do not move, and prove the generalisation by regenerating
  that first instance and requiring its output to be byte-identical.
- **Satisfying a check with a declaration that is not true.** When a rule is unsatisfiable for your
  artifact, the cheap move is to write into the record whatever the rule expects - path names that do
  not exist, a digest nothing produced, a count nobody measured. The check then passes and the
  artifact now carries a false claim, which is worse than the refusal: downstream consumers act on
  the declaration, and a page built from it links to files that 404. Record only what was verified,
  and if a recorded value cannot be verified, say so where it is recorded instead of asserting it.
- **Dropping a comparison to make a check pass, when the same guard is a resource bound.** A
  comparative check often bounds itself at the same time - a cap on the file it will read, a limit on
  what it may fetch - so the guard is enforcing a comparison *and* protecting the machine running it.
  When the comparison cannot be made for a legitimate input (the destination reports a digest only
  for one storage class, the expected value exists only for large objects), widen the **acquisition**
  with a per-call limit that admits the legitimate case and keep the comparison; deleting it turns a
  missing check into a silent pass and removes the resource bound with it, and the check goes on to
  fetch something enormous. Where a value genuinely cannot be obtained, report the gap in the
  check's machine-readable output - never as a printed line, because a consumer whose stdout is a
  protocol breaks on it - and state in the same breath what was still verified in its place.
- **A required-input refusal that arrives as a bare exception.** A validator with several required
  fields that surfaces a missing one as `KeyError` from deep inside its projection tells the caller
  nothing and costs a round trip per field. Translate each missing required input into a message
  naming it, and keep the required shape in one place - a schema, a documented list, or a single
  check that reports every missing field at once - so the caller can satisfy it in one pass.
- **Generated evidence that hashes its own build products.** A manifest that records the digest of a
  derived summary file and then rewrites that file records the previous revision's digest: correct on
  every run where the content does not change, and a package-check failure at exactly the moment it
  matters - a re-issue, when the artifact and every derived number move together. Write derived files
  before hashing them, and regenerate once after a content change to prove the ordering holds.
- **Asserting a refusal's mechanism instead of its contract.** A gate's test must trigger it and
  assert what a caller observes - the non-zero status, the message, and the absence of side effects
  (no commit, no dispatch, no receipt, no written file). Assert the internal ordering or exception
  type you *assumed* and the test fails on correct code: entry points differ on whether they raise or
  return a status code, and a refusal can legitimately follow client construction while still
  preceding every write. When a new gate test fails, decide whether the premise or the code is wrong
  before editing either - and if the premise was wrong, keep the assertion that still matters.
- **Enforcing a resource cap from a ledger you also own.** An exclusivity or concurrency limit
  checked only against your own job records admits one more paid resource the moment a record is
  lost - a crashed launch, a manual cleanup, a record written after the provider call. Count from
  the authoritative inventory *as well as* the ledger, take the larger, and keep the comparison in
  one place so a second launch path cannot skip it. When a limit is relaxed and the operator later
  reverts it, revert the guard and its tests in the same change and confirm the suite returns to its
  previous count: leftover tests for a withdrawn feature assert behaviour nobody wants and fail on
  a shard you did not run.
- **Rewording a refusal without grepping the tests that match it.** Existing tests commonly assert
  the refusal by regex on its message (`assertRaisesRegex(..., "interrupted job")`), so a clearer
  sentence quietly breaks them and the failure looks like the guard. Keep the substring that names
  the condition, add the new detail around it, and grep the test tree for the old wording before
  editing the message.
- **A failure-reporting path that was never exercised.** When the test harness formats a failed
  run's reasons, that formatter is code on the failure path and is the first thing to break: a
  reporting helper reading an attribute the result object never exposes turns every genuine
  rejection into a traceback naming nothing, and the real check name is lost. Give the result
  object the accessor the reporters expect, and prove it by driving one failing case through the
  reporting path, not only through the assertion.
- **A repo-wide check that runs while another process is writing.** A check asserting every record
  is complete goes red the moment a concurrent worker opens a new one, which trains everyone to
  ignore that check. Distinguish a *fresh* in-progress record from an abandoned one by status plus
  age - a short grace, only for the status that means work has started - and keep counting a stale
  or terminal record as a failure. Do not widen the grace to every status: that is the silencing
  knob again.
- **Running a new guard only against the fixed artifact.** A check written after the fix has never
  been seen to fail, so its green run is evidence about its syntax rather than its power, and a guard
  that asserts nothing about the defect it exists for looks exactly like one that does. Restore the
  pre-fix input and run the guard against it before reporting the guard as working: the previous
  revision of the generator, artifact or document is in history (`git show <sha>:<path> > <path>`),
  and where the guard's subject is a *derived* file, re-run the old generator to produce the old
  output rather than hand-writing a fixture that assumes what was wrong. Confirm the failure message
  names the defect, restore the fixed input, and only then call the check proven.
- **A fix that changed the declaration and left the code path.** Adding the field, the descriptor or
  the sentence the check now reads is the cheap half; the producer can still compute the same wrong
  thing one level down. Selection has this shape: a history count rewritten to `<= M` looks fixed,
  while the loop still walks *pairs of qualifying periods* (`keys[i], keys[i + 1]`), so the later
  period keeps deciding whether the earlier row exists. After any fix, grep the producer for the
  period it now claims not to use and read the loop that builds membership, not only the condition
  above it. Then pin it with a counterfactual that edits **one** future value and asserts the row
  survives - a fixture that only asserts the corrected output proves the arithmetic, not the order
  of operations.

## Binding a verdict to an artifact that never comes home

Acceptance normally re-hashes the artifact directory beside the report, which assumes the artifact is
on the machine reading the verdict. When it is bulk data living in remote storage, the equivalent
chain is verified from small files alone: `references/binding-verdict-to-artifact.md`.

For an audit performed by someone else before a release, see
`references/auditing-a-released-benchmark.md`.

When the defect is a claim about *when* data existed - a feature from a statistical release, or a
row selection that reached into a later period - see `references/temporal-availability.md` for the
declaration schema, the five checks, and how to prove the check is load-bearing.
