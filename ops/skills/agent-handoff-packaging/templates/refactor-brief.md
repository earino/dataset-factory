# Refactor brief: <one sentence naming the single defect class>

## The problem

<What is wrong, in one paragraph, stated as a mechanism rather than a symptom. Name the
structure that causes it: how many writers describe the same record, which consumers each invent
their own fallback, and why nothing fails at write time.>

| File | Written by | What it holds |
| --- | --- | --- |
| <path> | <producer> | <fields> |

Consumers: <list the readers that each implement their own fallback>.

### Symptoms this produced

1. **<Short name>** — <what a user saw>, caused by <which writer and which shape>.
2. ...

## Target

1. `<module>` — the single definition of the record, plus `load_<x>()` that normalises every legacy
   shape found on disk and raises a named error quoting the file and field when it cannot.
2. **Writers fail closed.** `<generator>` refuses to emit a record with a required field missing,
   rather than writing `{}` or `null`.
3. **Consumers stop reaching into raw dicts.** Every reader takes the normalised object.
4. **A conformance test in CI** over every record on disk, so drift fails on the commit that
   introduces it instead of surfacing in a rendered page.

## Acceptance criteria

- `<exact test command>` green, with the existing guards untouched: <list them>.
- The conformance test passes for every legacy artifact **without editing them** — old shapes are
  normalised on read, not rewritten on disk.
- `<grep that proves no consumer reads raw fields>` returns nothing.
- <The rendered surfaces that must show correct values, named individually.>
- `<generator>` exits non-zero on a record missing a required field instead of emitting nulls.

## Constraints

- Do not weaken or bypass `<the gate>`. <Why it exists, in one clause.>
- Do not fabricate values. Unknown is represented explicitly and rendered the same way everywhere.
- Do not rewrite published artifacts to fit the schema.
- Keep <the domain invariants> intact: <licence semantics, status vocabulary, caveats>.
- Do not change any currently passing test to make the change pass. If a test encodes the old shape,
  explain why in the pull request.

## Deliverable

A pull request against `<branch>` containing the schema module, the migrated consumers, the
conformance test, and a short note listing each legacy shape found and how it is normalised. Quote
 the actual test output in the pull request body. Do not merge, and do not force-push the default
branch.
