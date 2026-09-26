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
preserved, never edited in place. That rule is about the data: a correction that changes any asset
byte requires a new version, because the pinned tag must keep fetching the bytes it was verified
with. A correction to *documents only* - a record that overstated a check, a stale commit, a
licence note - leaves every digest identical, so it is applied to the same version and the tag is
moved onto that documentation commit as the last action; say in the record what moved and that no
data changed.

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

Prefer credential **files** over exported variables. Anything exported into the shell is written in
plaintext by the terminal backend's session snapshot (`$TMPDIR/hermes-snap-<id>.sh`) and survives
in the scratch directory, so `cat`-ing a credential file into a variable, exporting it, or expanding
a default (`${TOKEN:-none}` prints the value when the variable *is* set) leaks it into a snapshot and
into the transcript. Read the file at the point of use, pass the value inside the command, and keep
the token out of the echoed text.

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

## Publication: the one step that needs the operator

Everything above produces a **private** release. Publication is a separate, approved act, and it is
the operator's decision - never inferred from a plan digest you happen to hold. When it is approved:

1. **Flip both destinations, then prove it anonymously.** GitHub: `gh api -X PATCH repos/<owner>/<repo>
   -F private=false`. Hugging Face: `HfApi.update_repo_settings(repo_id=..., repo_type="dataset",
   private=False)` with the **write** credential (the `/settings` REST path is not the endpoint;
   asking for it returns 404). Then verify from a client with no credential at all: the repository
   page answers 200, every release asset answers a ranged GET, the Hub API reports `private: false`,
   and the data files answer ranged GETs at the **tag** revision. A successful PATCH is not
   verification.
2. **Record it before regenerating.** Set `private: false`, the note and the timestamp in
   `DESTINATIONS.json` first. The manifest derives its `visibility`, `published` and
   `publication_note` from that file, so regenerating before recording re-asserts "private".
3. **Regenerate, then re-verify.** `python3 scripts/release-manifest.py <candidate>`, then
   `check-package.py`, then the website pipeline `publish`/`verify`. Re-run `prepare` and confirm the
   plan digest is unchanged: publication is not supposed to alter the plan, and a changed digest
   means an input moved.
4. **Refresh what ships with the status.** The card, `LOADING.md`, the repository README and the
   release notes are generated or written while the release is private and will keep claiming
   "private, prepared for review" and instruct readers to pass a token. Re-upload the small files
   (`hf-publish.py --upload-small` changes no visibility) and update the public copies.
5. **Point the tag at the refresh commit, last of all.** Publication changes the documents, so the
   tag cut during staging now pins a tree that still says `private` and carries no split counts - and
   the website pipeline reads the manifest *at the pin* and refuses. Move the tag onto the commit that
   holds the refreshed documents on every destination and read back that tag and the default branch
   resolve to the same commit. Read the pinned file through the **contents API**: a CDN copy of
   `raw.githubusercontent.com` kept serving the pre-move manifest minutes after the ref had moved,
   which makes a correct pin look broken.

**Documents generated after publication must re-derive the managed navigation.** The pipeline writes a
navigation block (links to the dataset's page, the catalog, both destinations) into the repository
README and the Hub card; the package README does not carry it. So a later "regenerate and push the
documents" step silently overwrote both with copies that had no link to the dataset's own page, and
`verify` failed with `Destination navigation is missing` while the site itself was healthy. Apply the
block wherever a document is generated, gated on `DESTINATIONS.json` recording a verified site so a
staged package never advertises a page that does not exist: `scripts/apply-navigation.py` for the
package README (before the manifest is re-hashed), and the card builder for the Hub copy. Both are
idempotent.

**State is derived from recorded evidence, never asserted in a generator.** Three defects of this
exact shape shipped at once: a card whose status was a string literal, a manifest whose
`published`/`visibility` fields were literals (so the documented post-publication regeneration
re-asserted "private" forever), and a loading example that demanded a token. When you write a
status, version, digest or path into a generated document, ask what it is derived from; if the
answer is "nothing", it will go stale silently and nothing will fail to tell you.

**Anything a human reads or runs must be executed once before it ships.** The card carried the
repository id as a doubled-brace placeholder inside an f-string, which renders to a single brace -
so the replacement never matched and the published card printed `load_dataset("{repo_id}", ...)`.
The command could not run, for either platform, and every check passed. Open the generated artefact
and run its commands.

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
| `verify`: "Destination navigation is missing" | A document refresh overwrote the README and card the pipeline had linked | Derive the navigation block where documents are generated, then re-hash the manifest |
| Pinned manifest still says `private` and lists no splits | Tag cut before the publication refresh; the pipeline reads the manifest at the pin | Move the tag onto the refresh commit as the last action, and read the pin through the contents API |
| Hub copy is missing a licence file | The small-file list hardcoded licence names | Ship every `LICENSE*` file the package carries |
| Re-verifying erased publication history | The verify path replaced the destination record wholesale | Merge into the record; verification must not delete what publishing recorded |
| `load_dataset` works but the splits are wrong | Card `data_files` disagree with the manifest's split names | Generate the `configs` block from the manifest; verify split names, rows, schema and label values against it |
| A release reported complete, one platform empty | Completion tracked per release instead of per destination | `DESTINATIONS.json` per destination; the package check refuses `published` with an unverified destination |
| Publishing credential reached a container/mount | Token passed as a path into the job source or a mount | Use the credential-file mechanism read by the worker host, outside every mount |
| Licence block disappears from the manifest | It was hand-edited into `MANIFEST.json` and then regenerated | Declare terms in `candidates/<id>/license.json`; the generator writes them |
| A release ships with no declared terms | Licensing treated as a separate, later step | `check-package.py` refuses it; declare terms before verification |
| Third-party files redistributed without permission or credit | Provenance tracked but permission assumed | Record the permission and preserve existing contributor credits, or leave the files out |
| Re-run re-uploaded 131 MB | No digest check before sending | Skip any file already at the manifest digest on the destination |
| Inference token used to publish | Same variable name assumed for both roles | Separate variables (`FACTORY_HF_WRITE_TOKEN` vs the inference credential), refused at plan time |

| A generated document still claims "private" after publication | The status was a literal in the generator, not derived from recorded state | Derive it from `DESTINATIONS.json`/the manifest; assert nothing about a state you can read |
| A printed command contains a placeholder | A doubled-brace placeholder inside an f-string renders to a single brace, so the replacement no-ops | Use an unambiguous token; execute the artifact you generate before shipping it |
| `PUT .../pages` answered 404 "The certificate does not exist yet" | HTTPS enforcement precedes the first deployment, and only a deployment issues the certificate | Tolerate it before a deployment, retry after one succeeds, and read the enforced state back in `verify` |
| Website publication refuses with "dataset is private" | Correct refusal, not a defect: a public page must not link to a private destination | Complete the approved public data release first |
| Prose says a check passed while the job record says it failed | The job's overall status was read as the check's outcome; the result carried `ok: false` | Read the specific check's field in the job result - a job can upload every file correctly and still fail the verification written beside it |
| A card fix that was never exercised | The corrected card was uploaded and the documented path never re-run against the published revision | Re-run the documented load anonymously after any card or split change; a fix is not a verification |
| A recorded commit hash that does not exist | The hash was transcribed by hand instead of read back | Read the pin from the API and confirm the commit resolves; a 422 is the only thing that catches a corrupted tail |
| The card's loading example promises row counts the manifest does not have | Counts are typed into the template, so they drift silently when the build changes | Derive the `configs` block and the counts from the manifest in a test (`tests/test_hf_card.py`); show the test fails on the pre-fix card |
| The dataset page prints a command that raises "Config name is missing" | The page's "Use this version" snippet was hardcoded into the template instead of generated from the record | Derive it from one rule (`factory.site_model.config_names`) shared with the Hub card, and assert both; a page is a documentation surface too |
| A documents-only Hub refresh makes a recorded revision or tag claim false | The refresh moves the Hub revision, and re-tagging moves the tag, but the `DESTINATIONS.json` claim was written before it | Re-read the revision and tag after the refresh and correct the claim; the evidence block must name what the destination now serves |
| Re-syncing the public tree drops the website's file entries from `MANIFEST.json` | The release package's manifest overwrote the public one, which also declares the site scaffolding | Overlay, then restore the entries for the files the website step placed, reading them back from disk so the step is idempotent |
| A guard that has never been seen to fail | The test was written against the fixed input only | Revert the code or data path (`git stash push -- <file>`, or check out the pre-fix document), watch the guard fail, restore, and record which defect it caught |

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
- [ ] If publication was approved: both destinations verified from an **anonymous** client, the
      recorded state updated before the manifest was regenerated, and no shipped document still
      claims the release is private.
- [ ] Worker, IP and staging resources confirmed deleted, with provider-side evidence.

## References

- `scripts/check-package.py` - mechanical completeness check over a package directory.
- `scripts/release-manifest.py`, `scripts/publish-dataset.py`, `scripts/verify-staged-report.py`.
- `docs/OPERATIONS.md` - worker lifecycle, credentials, cleanup and the allowance.
