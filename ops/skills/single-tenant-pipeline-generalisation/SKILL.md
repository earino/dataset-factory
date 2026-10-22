---
name: single-tenant-pipeline-generalisation
description: "Use when a 2nd instance joins a pipeline built for one."
version: 1.0.0
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [refactoring, releases, publishing, pipelines, verification]
    category: software-development
---

# Generalising a single-tenant pipeline

Adding a second dataset, repository, tenant or artifact to automation whose scripts, defaults,
templates and file lists were written for the first one. Symptoms that mean "generalise", not
"special-case": `--plan` for the new instance prints the old instance's files; a required-file list
names only the old instance's scripts; a generated document hardcodes the old instance's narrative;
a summary line reads a field that only the single-instance shape has.

Repeating a release is not a one-off: the *second* instance is where every hidden assumption
surfaces, and it is cheaper to fix the generator than to fork it.

## Procedure

1. **Audit for literals before writing anything.** Grep the pipeline for the instance's name, ids,
   repository, paths and file list:

   ```bash
   grep -rn "<first-instance-name>" --include="*.py" --include="*.sh" scripts/ factory/ workers/
   ```

   Each hit is a defect, not a default. Expect the same class in every sibling generator, and treat
   "this generator has literals" as the finding rather than an exception.
2. **Move per-instance facts into a per-instance descriptor**, beside that instance's other decision
   files — *not* inside the generated package. A new file inside the package changes the package's
   own file-hash list, which is a content change to something already published.
3. **Choose between derivation and declaration deliberately.** Derive names and paths generically
   when nothing published depends on them; declare them explicitly in the descriptor when a
   published URL, tag or asset name already exists, because a cleverer rule silently relocates a
   live link. Keep the legacy rule as a fallback so the first instance's output does not move.
4. **Prove the refactor on the existing instance**: regenerate its output and require byte-identical
   bytes.

   ```bash
   cp -a <existing-output> /tmp/before
   python3 scripts/<generator> <first-instance>
   diff -r /tmp/before <existing-output> && echo identical
   git diff --stat <that path>        # must be empty
   ```

   A refactor that changes a published artifact is an unreviewed content change, not a refactor.
5. **Refuse to guess.** Once several instances exist, require the instance to be named and error
   with the list of candidates. Silently defaulting publishes instance A's bytes under instance B's
   name.
6. **Handle the multi-instance shapes** the single-instance code assumed: per-level or per-tenant
   rollups instead of a flat dict, a derived label instead of a single gate-produced value (label
   it as derived and keep the gate's own values in the record), and a summary print that does not
   crash on the new shape.
7. **Guard it with tests over the real generated output** — not over a mock: no separator characters
   in asset names, the layout maps every asset, each instance's checks are present, and the
   generated document does not claim the wrong status.

## Pitfalls

- **Resolve which instance first, then read its inputs.** Reading the manifest before the instance
  is chosen reads the default instance even when the flag says otherwise, and the run looks correct.
- **A generator's own summary print is part of the surface.** It often reads a field only the old
  shape provides; derive the label and iterate the per-instance values instead of indexing one.
- **Long prose belongs to the instance, facts belong to the generator.** A narrative document cannot
  be generated from a manifest — which task, which splits, why it exists. Let the instance ship a
  template and have the generator fill only what it owns (versions, tag, status, counts, licence),
  and refuse unresolved placeholders rather than shipping them as literals. Match UPPER_CASE tokens
  only: example output legitimately contains braces, and a naive scan fails correct prose.
- **Job ledgers gate the next launch on full cleanup.** A launcher commonly refuses while any prior
  record is not fully deleted, so release the previous job's worker first; and a recorded job id can
  never be reused, so a failed attempt's retry needs a new id.
- **Confirm you hold the mutation ledger before refactoring or launching.** A concurrent session in
  the same repository can launch work mid-step and leave uncommitted edits; an artifact produced by a
  run whose inputs differ from yours is not yours to adopt even when its digests verify, and
  byte-identity is not value-identity — the same source re-fetched can carry revised rows.
- **A step that redirects its output into a directory only uploaded on success leaves no diagnostics
  when it dies.** Tee to stdout as well as the file, and make dependency installs print an explicit
  status plus the versions they resolved — otherwise the only evidence is an exception class name.
- **Verify external state by reading it back from the destination**, not from the job's success
  status: list the destination's assets and compare digests.
- **Cross-check a gate's reported digests against the bytes preserved in staging before packaging.**
  It is the only thing that makes "the report describes what was uploaded" a fact.
- **Scores from ML training are not bit-reproducible** with default threading. Record the recorded
  and the reproduced values, name the cause, compare with a tolerance, and never print a single
  expected number as a constant — a reviewer who reruns will see a different last decimal.
- **Prefer self-declaration to a table.** A hardcoded table of per-instance paths is the largest
  single blocker to a third instance; moving it into per-instance files discovered by glob makes
  adding one a data change instead of a code change. Refuse duplicate names and a declaration whose
  companion file is missing — a silently skipped entry assembles nothing and looks like success.
  Prove the migration by re-assembling a produced spec before and after and requiring the two specs
  to be equal: that covers the assembler's own output, where diffing generated documents does not.
- **Removing a default or fallback is a behaviour change for the instance it served.** After deleting
  the default, run the incumbent's path as well as the new one. When a fallback becomes a refusal,
  migrate the incumbent in the same change, and take its file from the *published* copy of its output
  rather than retyping an equivalent — the published text is the thing that must keep matching.
- **Locate text by structure before replacing it by index.** An end bound taken from an assumed
  layout can swallow a file's CLI when the assumption is wrong; parse the file or read the region to
  get real anchors, and restore from version control and redo rather than patching around the damage.
- **A persistent interpreter caches imported modules.** After fixing a module, a re-import in the
  same session can still run the old code, so the fix looks absent; confirm in a fresh process before
  concluding anything.
- **A check that cannot pass for a legitimate shape is a defect in the check.** Widen what it accepts
  while keeping the comparison — never delete the comparison to go green. A digest only one storage
  class reports, or a size guard sized for one file kind, needs a bound that admits the legitimate
  case. When something genuinely cannot be verified, announce the gap in the machine-readable output,
  not as a printed line: a diagnostic print in an adapter whose stdout is a protocol breaks its caller.
- **State what verification does not cover.** A section listing the gaps is what makes the rest of
  the verification credible.

## Working with the operator

- **At most one question, in chat.** Batch question forms are experienced as interrogation; prefer
  deciding and saying what was decided, and ask only when the answer changes what you do.
- **When told to drop a proposed scope, drop it** and execute the minimal existing path. Do not
  re-raise the dropped work, and do not relitigate it on the next turn.
- **Report at each milestone with the numbers**, including the ones that are unflattering to the
  work, plus what is still pending and what is still being paid for. A finished job nobody hears
  about reads as nothing happening.

## References

- `references/descriptor-extraction.md` — what belongs in a per-instance descriptor, and the
  self-check list before calling the generalisation done.
