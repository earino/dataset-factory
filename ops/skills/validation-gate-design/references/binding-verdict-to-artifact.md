# Binding a verdict to an artifact that stays remote

A gate report is only meaningful if it is attached to the exact bytes it was written about. The
usual acceptance step re-hashes the artifact directory beside the report, which assumes the artifact
is on the machine reading the verdict.

When the artifact is bulk data that deliberately never comes home - it lives in an artifact host, a
staging release, a bucket - that check cannot run locally. The verdict is still verifiable using only
the small files, by chaining three sources:

```
release assets  ->  the producer's own manifest  ->  the report's recorded digests
```

Why this is equivalent rather than weaker:

- The collection step already re-read every uploaded asset's size and integrity digest from the host
  and compared them against the producer's manifest, so the manifest is anchored to the uploaded
  bytes.
- If the report's recorded digests equal the manifest's for the same files, the passing verdict
  describes those bytes - not an earlier build, and not a local sample.

## Recipe

1. Read the release (or bucket) asset list; resolve the manifest and the report by name.
2. Fetch both through the authenticated API. Draft or private releases are not reachable by public
   download URL and a release-download helper typically refuses them - request the asset by id with an
   `application/octet-stream` accept header.
3. For every component the report records, find the manifest entry for the same file and compare the
   digests. Require **all** of them to match, and report each one rather than a single boolean.
4. Fail loudly on a component present in the report but absent from the manifest - that is the case
   which would otherwise pass silently.

## Pitfall: the two sides name the same file differently

The report records paths relative to the dataset directory (`public/train.csv`); the manifest records
paths as the worker saw them (`output/extract/public/train.csv`). A direct lookup across the two finds
nothing, and "not found" reads as a missing file rather than a path-format mismatch.

Match on the suffix rather than the exact string, or normalise both against a known prefix, and
assert that every component resolved to exactly one manifest entry. Treat "not found" and "digest
mismatch" as the same class of failure: in both cases the verdict cannot be tied to those bytes.

## What to keep

Keep the small binding artifact - the report - and the manifest. They are kilobytes, and together
they reconstruct "which bytes did this verdict apply to" long after the release has been archived,
which is the question a later session actually asks.
