---
name: dataset-release
description: "Use when a qualified dataset is being packaged for review, transferred, or published. Package layout, private staging, verification, publication gates."
version: 1.0.0
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [datasets, releases, packaging, github-releases, verification, publication, provenance]
    category: research
    related_skills: [dataset-qualification, dataset-discovery]
---

# Dataset release

## When to use

Once a dataset is qualified and someone else must be able to get it, verify it, and reproduce it:

- Assembling a dataset's own repository (docs, construction code, reproduction instructions).
- Moving bulk artifacts from a worker to a release without passing them through the coordinator.
- Getting a package in front of a reviewer, or preparing it for public visibility.
- Re-issuing a release after a defect (a package, tag or asset is wrong).

Second to qualification: no number from the package may be published that the gate has not
passed on the exact artifact version.

## Layout: what goes where

**In Git** (small, reviewable, diffable): README and dataset card, data dictionary, licence,
reproduction instructions, release notes, verification record, construction and qualification
code, `MANIFEST.json`, `SHA256SUMS`.

**In release assets** (bulk, binary or row data): the CSVs, `meta.json`, `quality.json`,
extracted artifacts. Release assets are **flat** - GitHub rejects `/` in asset names - so the
download helper restores the runner layout the consumer expects.

The package must be reproducible **without the private source repository**: self-referencing pins
only, and any runner code the benchmark needs shipped verbatim with its provenance recorded.

## Commands

```bash
# build the manifest and checksums from recorded evidence
python3 scripts/release-manifest.py <package-dir>

# mechanical completeness check over an assembled package
python3 scripts/check-package.py <package-dir>

# publication: dry-run by default, executes only with an explicit flag
python3 scripts/publish-dataset.py <candidate-id> --repo <owner>/<name>
python3 scripts/publish-dataset.py <candidate-id> --repo <owner>/<name> --execute

# verify a written qualification report still matches staged bytes
python3 scripts/verify-staged-report.py --accept <report.json> <dir>

# transfer/fetch between releases (runs host-side, no container)
sh scripts/scout-factory worker plan <job.json>     # always plan first
sh scripts/scout-factory worker run  <job.json>
```

## Required evidence

- `MANIFEST.json` covering **every** file in the package, with sizes and hashes.
- `SHA256SUMS` over the assets, in a form `sha256sum -c` accepts.
- A reverse pin: the package names its own tag/release, not a commit in a private repository.
- A recorded `VERIFICATION.md`: what was run, on what, and what it does **not** cover.
- Measured figures with the command that produced each one, and estimates labelled as estimates.
- For any baseline: the exact command, the expected value, and the value actually obtained on
  the *published* bytes.
- Cleanup confirmed: no worker, IP or staging release left behind.

## Common failure modes

| Symptom | Cause | Action |
| --- | --- | --- |
| Download fails, token not leaked | API answers 302 to a signed URL on another host | Follow the redirect; never send the auth header to the new host |
| Bundle rejected: "unexpected suffix" | Bare name without an allowed extension | Add it to the explicit allowed-names list rather than loosening the rule |
| Rebuild differs only in a timestamp | Build embeds wall-clock time in a metadata file | Pin the timestamp as an input (`--built-at`) so rebuilds are byte-identical |
| Transfer fails 404 | Token scoped to staging only | Use the publish credential for non-staging targets; record the scope widening |
| Consumer fails on a read-only mount | Job already lays out paths; the container's `/data` is read-only | Prepare inputs read-only; write only to the output path |
| A worker dies with no report | An exception escapes the handler | Validate before dispatch so it fails at plan time, not mid-run |
| Package reviewed against the wrong bytes | Manifest built before the last edit | Rebuild the manifest last, then re-tag |
| Reviewer cannot reproduce | Instructions depend on the private repo | Ship the code, pin to the package's own tag, verify from a clean clone |

## Completion criteria

A package is **ready for review** when:

- [ ] `check-package.py` reports no missing document and no manifest/hash mismatch.
- [ ] Every command in the reproduction instructions was executed on the published bytes, in a
      fresh environment with no access to the private repository.
- [ ] The consumer check exercised: download, checksum verification, qualification re-run, and
      baseline reproduction - with the results recorded.
- [ ] `VERIFICATION.md` states what was **not** covered and why.
- [ ] Private by default. Public visibility, and any licence choice, are decisions for the
      reviewer, never a step in the procedure.
- [ ] Worker, IP and staging resources confirmed deleted, with provider-side evidence.

## References

- `scripts/check-package.py` - mechanical completeness check over a package directory.
- `scripts/release-manifest.py`, `scripts/publish-dataset.py`, `scripts/verify-staged-report.py`.
- `docs/OPERATIONS.md` - worker lifecycle, credentials, cleanup and the allowance.
