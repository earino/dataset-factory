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


**Before packaging, re-read the `timing` block against the release.** Gate 1.4.0 refuses a dataset
without one, but the numbers are your claim: the instant must match the source (publication for delayed statistical
releases, documented event time where justified); feature availability must be evidenced
and row selection must not reach past it. A packaged artifact
with a wrong timing claim is worse than an unpackaged one - it looks done.

## When to use

Once a dataset is qualified and someone else must be able to get it, verify it, and reproduce it:

- Assembling a dataset's own repository (docs, construction code, reproduction instructions).
- Moving bulk artifacts from a worker to a release without passing them through the coordinator.
- Getting a package in front of a reviewer, or preparing it for public visibility.
- Re-issuing a release after a defect (a package, tag or asset is wrong).

Second to qualification: no number from the package may be published that the gate has not
passed on the exact artifact version.

## Decide what can change

Read the candidate's current evidence, frozen release record and destination receipts.
Separate preparation, verification, editorial maintenance and public visibility. A successful
command is not a successful release: require the relevant check result at the pinned revision.

Published `release/*/MANIFEST.json`, CSVs and recorded digests are immutable. Existing version
tags are immutable too, including for documentation-only changes. Never regenerate a historical
manifest or delete/recreate a tag to fix CI, add missing fields, refresh status or bypass a
consumer error. Normalize legacy shapes through `factory.release_schema`; prepare a new reviewed
version for package changes. Website editorial revisions use their own procedure and may advance
default-branch documentation without moving the dataset tag.

Check the diff and ownership before writes. A concurrent session's package or unfinished changes
are not yours to commit. Preserve them and arrange a documented handoff. Keep reports bounded and
bulk reconstruction, consumer execution and transfers on workers.

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
- Worker/IP cleanup confirmed. Preserve staging artifacts until verified durable copies
  exist; do not delete staging merely to make a checklist look complete.

## Two destinations, one manifest

A dataset release goes to **GitHub and Hugging Face from one release manifest**. Every fact on the
Hugging Face card - version, checksums, splits, labels, provenance, licence status, measurements -
is generated from `MANIFEST.json`; the two platforms must never be described from separate notes,
or they drift into claiming different datasets.

Completion is tracked **per destination** in `DESTINATIONS.json`, written after each platform is
verified. GitHub can be done while Hugging Face is pending; a release is reported complete only
when both verify, and the package check refuses a manifest that claims `published` while any
destination is unverified. Corrections are published as a **new version**; prior versions are
preserved, never edited in place. This includes package documents: changing a hashed document changes package bytes.
Keep existing tags pinned and issue a new reviewed version where package contents change.
Editorial updates outside the frozen package follow the website revision procedure.

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

**Only build on sources whose licence is already clean.** Classify every candidate before construction: explicit open (redistribution *and* derivatives), open-with-conditions, unresolved, or prohibited. Unresolved is a **drop, not a park** - no permission emails, no dated expiry to wait on, no "probably fine"; a source that needs a written answer is a source we do not use. The reason is arithmetic: a source probed before its licence is read costs exactly as much as a usable one and returns nothing.

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
  be read is not published at all **unless the operator has recorded a risk acceptance in
  `candidates/<id>/license.json`** - written as a risk acceptance, never as a grant: our
  contribution only under our dedication, attribution to the publisher, a takedown route in the
  card, and no standard licence presented as the publisher's. Terms are chosen per dataset to be
  compatible with each source; the licence-posture notes live in `dataset-discovery`.
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

## Publication: recorded approval, then verified completion

Everything above produces a **private** release. The boundary is one event: **making a private
repository or Hub repo public** (the flip). Before it, prepare within the existing budgets, qualification and integrity rules.
Complete baseline comparisons before claiming release readiness, then privately stage and verify. The flip itself is the
operator's single approval; nothing about packaging, checks or planning is theirs to grant.

A dropped session, a gateway restart or a background-process notification is **not** a decision
point. If the task was already authorised, resume it and report the outcome; asking again for work
the operator has already scoped reads as stalling and costs a whole cycle.

After the flip, publication is automatic: GitHub and Hugging Face, the site page, and the anonymous
verification all run without another yes, and the operator is told the link. Do not re-ask for a
per-release approval you already have, and do not infer a flip from a plan digest you happen to hold.

Record the boundary in the candidate record so both humans and the scheduler can see it:

- `packaged_at` - ISO timestamp, set when the package is verified.
- `awaiting_operator: true` - set **only** while the flip is the sole remaining step; clear it after.

### Shipping outranks building

Once a candidate is packaged and that state is still actionable (not `awaiting_operator`), it takes
priority over all construction: no new construction job launches while it exists, and the scheduled
session spends its tick on it. Two mechanisms, both needed:

- **Preemption.** The worker launcher refuses a construction job while an actionable packaged
  candidate exists, and names the candidate. Release jobs - or a job flagged `release: true` - may
  launch.
- **A reserve.** Hold part of the monthly worker allowance back from construction so a release can
  always afford its own job. Construction may spend `budget - reserve`; release work may spend the
  whole budget. Refuse a reserve that is not smaller than the allowance.

**Exempt the human wait, or the queue starves.** A packaged candidate waiting on the operator must
not block anything - otherwise a slow approval freezes every build behind it. That is exactly why
the record carries `awaiting_operator`: preemption applies to work *you* can do, never to work waiting
on a person. Surface the wait as an ageing item on the dashboard instead, and alarm when actionable
release work sits for hours. A human wait is not only the flip: a release blocked on an operator
**decision** - a DO-NOT-PUBLISH audit verdict whose reopen path (repair, re-describe or drop) is the
operator's to choose - carries `operator_decision_pending: true`, which preemption exempts the same
way. Keep the two markers distinct: `awaiting_operator` still means "the flip is the sole remaining
step" (the notifier tells the operator they can reply `flip ...`), while `operator_decision_pending`
means "the next step is the operator's choice among recorded paths" and must never trigger a
flip-ready notification.

When it is approved:

0. **Offer the independent pre-flip audit.** Before the flip, generate the
   adversarial audit prompt from
   `templates/pre-flip-audit-prompt.md` (placeholders filled programmatically
   from the frozen manifest and candidate record — digests never hand-copied)
   and hand it to the operator for an independent agent. This is the standing
   practice since the operator endorsed it on 2026-10-27: it exists because
   blind-join label recovery has repeatedly passed every internal gate
   (nz-ea at AUC 1.0; 7 of 10 in the catalog-wide audit). The flip waits for
   the auditor's verdict unless the operator waves it. The auditor must be
   independent of the sessions that built and staged the release.

1. **Flip both destinations, then prove it anonymously.** GitHub: `gh api -X PATCH repos/<owner>/<repo>`
   -F private=false`. Hugging Face: `HfApi.update_repo_settings(repo_id=..., repo_type="dataset",
   private=False)` with the **write** credential (the `/settings` REST path is not the endpoint;
   asking for it returns 404). Then verify from a client with no credential at all: the repository
   page answers 200, every release asset answers a ranged GET, the Hub API reports `private: false`,
   and the data files answer ranged GETs at the **tag** revision. A successful PATCH is not
   verification.
2. **Record visibility separately from frozen package bytes.** Record verified visibility, note and timestamp in
   `DESTINATIONS.json`. Preserve the historical manifest; do not regenerate it to update status.
   The website planner reads two more fields from the same file and refuses without them: a
   top-level `artifact_version` equal to the manifest's, and `files_verified` as **lists**, not
   counts - every logical manifest path for GitHub, and the Hub target path for each asset
   (`data/<name>.csv` for CSVs, the basename otherwise). A count or a missing field fails with
   "Destination evidence describes a different release or artifact" / "verification omits an
   asset" after the flip, when the release is already public.
3. **Re-verify the pinned package and reviewed site plan.** Run `check-package.py`,
   then the approved website pipeline `publish`/`verify`. If inputs or plan digest changed,
   inspect and review the new plan; never assert an old approval covers changed contents.
4. **Refresh what ships with the status.** The card, `LOADING.md`, the repository README and the
   release notes are generated or written while the release is private and will keep claiming
   "private, prepared for review" and instruct readers to pass a token. Re-upload the small files
   (`hf-publish.py --upload-small` changes no visibility) and update the public copies.
5. **Verify the existing tag without moving it.** New tags are created only after content
   verification, and initially resolve to the verified main commit. Later editorial main commits
   may differ. Verify the pinned files and destination receipts, not an assumed current branch.
   An existing conflicting tag is a refusal: prepare a new reviewed version.

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
| Worker dies seconds in: `can't open file '/workspace/qualify_dataset.py'` | The job was launched straight from the candidate's `baseline/job.json`, so the bundle was that one directory and the gate script plus runner files were never packed | Assemble first (`scripts/assemble-job.py`), confirm the bundle carries `qualify_dataset.py`, `train.py`, `validate.py`, `validate.sh` and `runner_files.json`, then launch the assembled job |
| Every digest matches but the shipped code is wrong | Hashing proves integrity, not correctness: a wrong file that was hashed into the manifest is consistently wrong everywhere | The fresh-environment consumer must **execute** the artifact (materialise, gate, train), not only `sha256sum -c`; that is how a foreign `materialize.py` with the wrong arity is caught before publication |
| Package reviewed against the wrong bytes | Manifest built before the last edit | For a new untagged package build the manifest last; preserve all existing tags |
| Reviewer cannot reproduce | Instructions depend on the private repo | Ship the code, pin to the package's own tag, verify from a clean clone |
| Version-pinned load returns nothing | Tag created before the data landed | Tag last, and confirm the tag and `main` point at the same commit |
| `verify`: "Destination navigation is missing" | A document refresh overwrote the README and card the pipeline had linked | Derive the navigation block where documents are generated, then re-hash the manifest |
| Pinned manifest still says `private` and lists no splits | Tag cut before the publication refresh; the pipeline reads the manifest at the pin | Preserve the tag; read the frozen manifest through the schema adapter or prepare a new reviewed version |
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
| The card still claims "private" after a flip made under the manifest freeze | The manifest froze at staging and the generator refuses to rewrite published bytes, so `release.published` reads False forever while the release is public | Publication state is derived in `factory.release_schema`: every destination recorded verified, timestamped, located and public in `DESTINATIONS.json` IS publication; card, LOADING and site read that derivation. Never regenerate the manifest for status |
| `PUT .../pages` answered 404 "The certificate does not exist yet" | HTTPS enforcement precedes the first deployment, and only a deployment issues the certificate | Tolerate it before a deployment, retry after one succeeds, and read the enforced state back in `verify` |
| Website publication refuses with "dataset is private" | Correct refusal, not a defect: a public page must not link to a private destination | Complete the approved public data release first |
| Prose says a check passed while the job record says it failed | The job's overall status was read as the check's outcome; the result carried `ok: false` | Read the specific check's field in the job result - a job can upload every file correctly and still fail the verification written beside it |
| A card fix that was never exercised | The corrected card was uploaded and the documented path never re-run against the published revision | Re-run the documented load anonymously after any card or split change; a fix is not a verification |
| A recorded commit hash that does not exist | The hash was transcribed by hand instead of read back | Read the pin from the API and confirm the commit resolves; a 422 is the only thing that catches a corrupted tail |
| The card's loading example promises row counts the manifest does not have | Counts are typed into the template, so they drift silently when the build changes | Derive the `configs` block and the counts from the manifest in a test (`tests/test_hf_card.py`); show the test fails on the pre-fix card |
| The dataset page prints a command that raises "Config name is missing" | The page's "Use this version" snippet was hardcoded into the template instead of generated from the record | Derive it from one rule (`factory.site_model.config_names`) shared with the Hub card, and assert both; a page is a documentation surface too |
| A documents-only Hub refresh makes a recorded revision or tag claim false | The refresh moves the Hub revision, and re-tagging moves the tag, but the `DESTINATIONS.json` claim was written before it | Keep the tag fixed; record editorial main separately from verification of pinned data |
| Re-syncing the public tree drops the website's file entries from `MANIFEST.json` | The release package's manifest overwrote the public one, which also declares the site scaffolding | Use the website pipeline and its separate site revision; do not overwrite or extend a frozen dataset manifest |
| A guard that has never been seen to fail | The test was written against the fixed input only | Revert the code or data path (`git stash push -- <file>`, or check out the pre-fix document), watch the guard fail, restore, and record which defect it caught |
| An older staged release can still be flipped by a later session | A rebuild creates a new tag but the superseded staged release keeps its private artifacts and its record | Rename the superseded releases as `SUPERSEDED - DO NOT PUBLISH` at the destination, list them under `superseded` in `DESTINATIONS.json`, and point the record's `next_action` at the current tag |
| The Hub card carries no licence metadata | The card was uploaded without YAML front matter - the upload succeeds and the licence field simply disappears | Keep the front matter in the card source, upload the card as `README.md`, and read `cardData.license` back from the API; a release README is not a dataset card |
| The documented loader cannot find a released file | Assets were uploaded under bare names (`train.csv`) while the manifest and loader expect `public-train.csv` | Read the asset names back after upload and rename them (`PATCH /releases/assets/<id>`), then re-check sizes and digests; never assume the uploader used the manifest's names |
| The website planner dies with a bare `TypeError` (`'NoneType' object is not iterable`) | `MANIFEST.json` has `splits: null`; the planner's `flatten_splits` iterates it | For new packages require canonical fields; for a published package normalize its legacy shape on read without modifying bytes |
| Manifest and qualification name different artifact versions | The manifest computed its own packaging hash while `qualification.artifact_version` came from the gate, and the candidate record can lag a rebuild | One identity: `artifact_version` is the gate digest, taken from the qualification report beside the artifact; record the packaging hash separately as `package_digest`. Never read qualification from the candidate record when a report file exists |
**A re-tagged Hub release still serves the old manifest** | `create_tag(..., exist_ok=True)` keeps an existing tag pointing at its old commit instead of moving it | Preserve the existing tag. A different commit requires a new reviewed version; verify the pinned content before creating any missing tag |
| A document refresh cannot be pushed to the dataset repo | The website pipeline commits navigation and edition files into that same repo, so the local clone is behind | Inspect and reconcile the remote changes; preserve frozen manifests and tags. Resolve new-package conflicts from authoritative inputs in a separate reviewed version |
| The artifact exists only as opaque staged parts (`file-0003-part-0000`) | The build job uploaded its output as numbered parts, so there is no local extract to package | Read `manifest.json` from the staging release: each entry names the logical `file` path, its `name`, `size` and `sha256`. Rebuild the tree by writing each part to its logical path and checking every digest - never guess the mapping from part order or size |

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
      current destination visibility recorded separately, existing manifest/tag preserved, and
      current editorial documents accurately distinguish historical staging from live visibility.
- [ ] Worker/IP cleanup confirmed with provider-side evidence; durable artifacts retained
      and staging removed only when its preservation obligation is satisfied.

## References

- `scripts/check-package.py` - mechanical completeness check over a package directory.
- `scripts/release-manifest.py`, `scripts/publish-dataset.py`, `scripts/verify-staged-report.py`.
- `docs/OPERATIONS.md` - worker lifecycle, credentials, cleanup and the allowance.

## Prediction contract and suitability (gate 1.5)

Follow `docs/PREDICTION-CONTRACT.md` in the project before new construction or release.
Read observation time, actual feature availability, label availability and revision/vintage
separately. Labeled eval is development/validation, never an untouched final test.
Declare every solver-visible file, including joint label matrices; exclude holdout outcomes
from agent development. Run source-specific reverse-history probes on every full configuration
on the worker and record coverage/mismatches. A demonstrated cross-row exposure requires an
enforced restricted prediction protocol; it does not automatically make retrospective research
data worthless. No historical forecasting certification without a full-row availability ledger
and reviewed as-of evidence; unverified assumptions must remain unverified.

New artifacts require `quality.json.evaluation_contract` and the current gate. Older reports
remain historical evidence only. Never fill fields with invented evidence to obtain a pass.
Before recommending or publishing, create/update the exact-artifact suitability record, run
`python3 scripts/check-suitability.py`, and carry its public notice to GitHub, Hub and website.
Current editorial corrections preserve frozen data/tags/checksums. A bounded audit PASS does
not establish operational validity. See `docs/PREDICTION-CONTRACT.md` for the schema and probes.
