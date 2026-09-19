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

## Two destinations, one manifest

A dataset release goes to **GitHub and Hugging Face from one release manifest**. Every fact on the
Hugging Face card - version, checksums, splits, labels, provenance, licence status, measurements -
is generated from `MANIFEST.json`; the two platforms must never be described from separate notes,
or they drift into claiming different datasets.

Completion is tracked **per destination** in `DESTINATIONS.json`, written after each platform is
verified. GitHub can be done while Hugging Face is pending; a release is reported complete only
when both verify, and the package check refuses a manifest that claims `published` while any
destination is unverified. Corrections are published as a **new version**; prior versions are
preserved, never edited in place.

Order matters in two places:

- **Tag last.** A version tag created before the data lands pins a commit without the files, and
  the version-pinned load then fetches nothing. Verify the content, then tag, then confirm the tag
  and `main` resolve to the same commit.
- **Bulk moves on a worker, never through the coordinator.** The Hugging Face upload is a
  `hf_publish` worker job: it downloads each asset from the GitHub release, verifies the digest,
  pushes it, verifies the digest the Hub reports, and deletes the local copy. The bytes never pass
  through the coordinator and the coordinator holds no bulk data.

### Credentials

The **write** credential and the **inference** credential are different, and only the write one
may publish. It is read from the environment or a mode-0600 credential file, used in-process, and
never appears in a bundle, a dataset-job input mount, a container, a log, a manifest, a release
asset or a command-line argument. A job is refused at **plan** time when the publishing credential
is missing - not on a paid worker.

### Deterministic, not model-driven

Synchronisation is release work, not a research loop: it runs as part of the release, with bounded
retries (three attempts, exponential backoff) and idempotent per-file uploads that skip anything
already at the manifest digest. Re-running a part-finished release is safe and cheap; the two
copies are never edited independently by a model on a schedule.

## Licensing: two grants, two scopes

Every release declares its terms. The standing policy is `config/licensing-policy.json`; the
per-dataset decision is `candidates/<id>/license.json`, and the release manifest carries both, so
the manifest cannot drift from the decision.

| What | Default | Why |
| --- | --- | --- |
| Our code and documentation | **MIT** | Ours to license; permits reuse and redistribution |
| Our rights in the derived compilation | **CC0-1.0** | Dedicates our contribution: row selection, the derived label, the partition, the packaging |
| The source's own terms | **preserved** | We never relicense someone else's data |

Rules that are not negotiable:

- **CC0 is not a blanket override of upstream terms.** A source requiring attribution, share-alike
  or non-commercial use keeps those terms, carried through unchanged. A source whose licence cannot
  be read is not published at all. Terms are chosen per dataset to be compatible with each source.
- **State the scope.** The dedication covers our contribution and not the source, which keeps its
  own designation, attribution and suggested citation.
- **Label derived data as derived**, and never present it as the source agency's official product.
- **Preserve contributor credits** on redistributed third-party files, and record the permission
  for them. A file copied from a project we own still carries that project's credits.
- **A release with no declared terms is refused** by `check-package.py`, as is one naming a licence
  file it does not ship. Licensing is not an afterthought before publication; it is part of the
  package.
- Terms are recorded in the manifest, **generated from the declaration** rather than edited in
  afterwards - a hand-edited block is lost the next time the manifest is regenerated.

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
| Version-pinned load returns nothing | Tag created before the data landed | Tag last, and confirm the tag and `main` point at the same commit |
| `load_dataset` works but the splits are wrong | Card `data_files` disagree with the manifest's split names | Generate the `configs` block from the manifest; verify split names, rows, schema and label values against it |
| A release reported complete, one platform empty | Completion tracked per release instead of per destination | `DESTINATIONS.json` per destination; the package check refuses `published` with an unverified destination |
| Publishing credential reached a container/mount | Token passed as a path into the job source or a mount | Use the credential-file mechanism read by the worker host, outside every mount |
| Licence block disappears from the manifest | It was hand-edited into `MANIFEST.json` and then regenerated | Declare terms in `candidates/<id>/license.json`; the generator writes them |
| A release ships with no declared terms | Licensing treated as a separate, later step | `check-package.py` refuses it; declare terms before verification |
| Third-party files redistributed without permission or credit | Provenance tracked but permission assumed | Record the permission and preserve existing contributor credits, or leave the files out |
| Re-run re-uploaded 131 MB | No digest check before sending | Skip any file already at the manifest digest on the destination |
| Inference token used to publish | Same variable name assumed for both roles | Separate variables (`FACTORY_HF_WRITE_TOKEN` vs the inference credential), refused at plan time |

## Completion criteria

### Website publication

Use the existing release package as input to the deterministic website pipeline;
read `docs/WEBSITE-SYSTEM.md` for setup, access and recovery. A new dataset needs an
editorial JSON file under `sites/`, not a new renderer or hand-configured Pages site.

```bash
python3 scripts/site-publish.py prepare release/<id> --editorial sites/<id>.json --out .factory/sites/<release-id>
python3 scripts/site-publish.py inspect .factory/sites/<release-id>
# Only after the operator approves this plan and the data destinations are public:
python3 scripts/site-publish.py publish .factory/sites/<release-id> --approved-plan <reviewed-sha> --wait-seconds 600
python3 scripts/site-publish.py verify .factory/sites/<release-id>
```

Exit 2 means pending; read the receipt and resume the same command. Completion needs
successful deployment and matching live JSON and HTML links, not merely an uploaded
preview artifact. Update STATE.md with the final receipt summary. A failed step is
Scout's normal diagnostic work; builder review is not required on each release.

For editorial corrections, increment `site_revision`, prepare and review the new
plan. Existing data identity is immutable. Website navigation updates default-branch
documentation and never force-moves dataset tags. The labelled holdout is downloadable
on both data platforms and stays outside evaluated agents' workspaces.

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
