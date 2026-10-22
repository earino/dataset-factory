# Descriptor extraction recipe

Depth for `single-tenant-pipeline-generalisation` steps 2-3. Use when a generator carries the first
instance's facts as literals and further instances are coming.

## What belongs in the descriptor

Move exactly the facts that differ *per instance*, and nothing that is derived:

| Fact | Descriptor | Why not derived |
| --- | --- | --- |
| Instance id, version, tag | yes | The version is a human decision, not a hash |
| Repository / destination owner+name | yes | Cannot be inferred from a directory name safely |
| Source attribution, landing page, API, access date | yes | Provenance is a claim that must be recorded |
| Per-file target names where output is already public | yes | Stability of published URLs outranks elegance |
| Commands the operator copies (gate, baseline, fetch) | yes | They are documented, so they are a contract |
| Digests, sizes, row counts, check counts | no | Derived from the artifact and its reports |
| Visibility / published status | no | Derived from the recorded destination state |
| Locations of generated sections inside a template | no | Owned by the template |

## Self-declaring per-instance files

For lists that are not facts *about* an instance but *inputs to* one job — which files a bundle
stages, which runners it copies, which trees it mounts — prefer a declaration that lives beside the
thing it describes over a central table:

```
<instance-dir>/<job-dir>/job.json      # the job
<instance-dir>/<job-dir>/bundle.json   # what that job needs staged
```

1. Dump the existing table into one declaration per entry, including the entry's own name, before
   changing any code — the table is already correct, so it is the migration's source of truth.
2. Replace the table with a discovery pass over the declarations. Refuse a duplicate name, a
   declaration with no companion job file, and an empty discovery result: each of those assembles
   nothing and otherwise reports success.
3. Regression-prove by **producing a spec, migrating, producing it again, and requiring equality**.
   Capture at least two entries covering different shapes (one with copied runner files, one with
   mounted trees). Equality of the produced spec is a stronger check than equality of documents,
   because it exercises the assembler itself.
4. Keep a way to list what exists (`--list`) so the operator can see the discovery result without
   running a build.

## Removing a default or a fallback

Deleting the instance name that a script defaulted to, or turning a fallback into a refusal, changes
behaviour for the instance that relied on it. Treat it as a migration:

1. Remove the default and make the unnamed case refuse with the list of candidates.
2. Run the *incumbent's* path, not only the new instance's — this is where it breaks, because the
   incumbent is the thing that had no explicit file or flag.
3. Supply whatever the incumbent was silently receiving from the fallback, taking it from the
   published copy of that output so the content still matches what was released.
4. Re-run both instances' plan paths and require exit 0.

## Self-check before declaring the generalisation done

1. The first instance's generated output is byte-identical (`git diff --stat` empty).
2. Every remaining literal of the first instance's name is either a fallback path or lives inside
   its own descriptor — grep again and read each hit.
3. With one instance present the pipeline still works unnamed; with several it refuses and lists
   them.
4. The new instance runs end to end once on real inputs — a plan that prints is not a run.
5. Tests assert invariants over the real generated output of the new instance, not over a fixture
   that shares the old shape.
6. Each remaining literal of the first instance's name is either an illustrative docstring example or
   dead code you have scheduled for deletion — a fallback that a new instance can reach is neither.
7. Each instance's *own* path still runs after a default was removed, and a declaration whose
   companion file is missing is refused rather than skipped.
