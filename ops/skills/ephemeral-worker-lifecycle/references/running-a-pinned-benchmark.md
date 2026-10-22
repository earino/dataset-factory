# Running a pinned harness's contract against an accepted artifact

How to measure against an artifact that was **already accepted** when the machine doing the
measuring cannot read the artifact store, and how to prove the thing you measured is the accepted
artifact rather than a near-copy.

Use when: a downstream job (baseline, benchmark, scoring, evaluation) must consume an artifact that
lives in a private or credentialed store, and the job runs on an ephemeral worker.

## Why not just download the artifact

Container jobs are usually designed to hold **no credentials** - that is a security property worth
keeping, not an obstacle to route around. Handing the container a token so it can fetch its own
input trades that property away for convenience. And pulling the artifact through the coordinator
violates the reason the coordinator is small: bulk data stays where it was built.

The workable path is: **rebuild it on the worker, then prove the rebuild is the artifact.**

## Procedure

1. **Record the artifact's identity as per-file hashes in a small tracked file** beside the job's
   source (not in ignored scratch), together with the digest the producer gave the whole artifact.
   That file is the contract the job verifies against, and it is reviewable in a diff.
2. **Rebuild into scratch on the worker**, not into the collected output directory. A rebuild of a
   large extract must not be re-uploaded; only the compact evidence should reach the artifact store.
3. **Verify every file before measuring anything**, and exit non-zero on the first mismatch with a
   message naming the file. Refusing to measure is the correct behaviour: a number attached to an
   unverified copy is worse than no number, because it looks like a result about the accepted
   artifact.
4. **Only then materialize the task directory and run the harness.**

## The volatile-field rule

**Any field the build derives from the clock must become an explicit input before a rebuild can
match.** Metadata commonly embeds a build timestamp; a rebuild then differs from the accepted
artifact in exactly that field while every data file matches perfectly. The comparison fails, and
it reads like data drift when it is a clock.

Fix it at the producer, not at the checker: add a flag that pins the timestamp (`--built-at <iso>`),
record the pinned value next to the hashes, and pass it on the rebuild. Do not weaken verification to
ignore the field - if the artifact's identity is computed over that file, ignoring it means the
verified object is no longer the artifact anyone accepted.

This also has to reach the reproduction instructions: a documented "run the script to reproduce
this version" that omits the timestamp flag does not reproduce the version, and the next reader
will discover it by failing verification.

## Running an existing harness's contract unmodified

When the measurement is "how does this dataset do under the project's existing runner", the runner's
own files are the contract and nothing about them should be re-implemented:

- **Copy the runner's entrypoints verbatim from the project into the job bundle** and record their
  SHA-256 in the job record. Then the job's own report can state that the runner was unmodified by
  hashing the bundled copies and comparing - evidence rather than assertion. Never vendor a second
  copy into your repository: two copies drift, and a stale copy of someone else's harness is worse
  than none.
- **Follow the harness's own materializer for the task directory.** Read the function that builds a
  workdir and reproduce its key list and file placement exactly; do not invent a layout, and do not
  assume a task metadata file needs fewer keys than the harness reads.
- **Never copy the private holdout into a workdir**, even when it is downloadable. That is the
  harness's rule and it is the difference between an evaluation and a leak.
- **Report every number the contract produces.** A trainer that scores its own in-memory model and a
  validator that re-runs the file and scores through the exported prediction function are two
  independent checks; agreement between them is the evidence that the contract is satisfied, not
  just that training succeeded.
- **Record the resolved dependency versions** in the report, not the ranges. The ranges are the
  harness's compatibility statement; the versions are what actually ran.
- **Label the result's scope in the same message**: a baseline run through a contract is a floor for
  what an agent might do, not a result about any agent. Say that where the number is reported, not
  only in the project's notes.

## Referencing a draft release

Artifact stores often stage outputs as **draft** releases, and drafts behave differently from
published ones:

- A draft has no tag namespace: looking it up as `releases/tags/<tag>` returns 404 even though the
  release plainly exists.
- Bulk download helpers aimed at humans (`gh release download` and friends) cannot fetch a draft's
  assets either.

So address a staged release **by its numeric id**, captured when the artifact was accepted
(or by listing releases and matching), and read its assets through the API. When mapping assets back
to original file paths, take the mapping from the **manifest the producer wrote** rather than from
the asset names or their order - the names are usually positional (`file-NNNN-part-0000`) and carry
no path information.
