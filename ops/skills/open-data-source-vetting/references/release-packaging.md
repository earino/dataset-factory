# Preparing a dataset release for review

The step between "the artifact passed its gate" and "the operator publishes it". The deliverable is
a reviewable package plus an explicit list of the decisions that are the operator's to make.

**Nothing here publishes.** A public repository and a public release are far harder to undo than a
commit, and publication is the human's call. Prepare, state plainly what is and is not published, and
hand over the decisions. When the operator *does* authorize assembling the package into a repository,
build it **private** and keep it private until a separate word says otherwise: assembling is not
publishing, and the git remote is not the audience.

## The package

Seven documents, each answering one of the questions a reader arrives with. A project usually has
its own content checklist - follow it, and follow the order it presents.

| file | answers |
|---|---|
| `README.md` | what the task is, where the data came from, how to download and verify, how to reproduce, what the limits are |
| `DATA_DICTIONARY.md` | every shipped column, its role, and whether it is knowable at prediction time |
| `LICENSE.md` | the data's licence *with its evidence quoted*, plus the code's licence status |
| `REPRODUCE.md` | exact commands, pinned commit, resolved dependencies, measured resource needs |
| `MANIFEST.json` | machine-readable identity: per-file sizes and hashes, artifact version, source, split counts, qualification and baseline results |
| `SHA256SUMS` | the same hashes in `sha256sum -c` format, for a downloader |
| `RELEASE_NOTES.md` | the release body: assets, what was checked, measured numbers, known properties, citation |

The README carries the most risk of going stale, so write the measured numbers into it from the same
source the manifest is generated from, and re-generate rather than edit by hand.

## Generate identity, never retype it

Write a small tracked script that builds `MANIFEST.json` and `SHA256SUMS` **from recorded evidence**:
the accepted artifact's per-file hashes, the candidate's own record, and the collected measurement
reports. Then the manifest cannot drift from what was measured, and regenerating after a new
measurement is one command.

A hash typed by hand from a display is a fabrication - especially a long one your tooling showed as
a prefix. Fetch the full value from the source of truth before recording it, and if you cannot,
record the prefix and label it as one.

## Decisions to surface, not to make

Put these in the handover explicitly. Each is a judgement about risk or rights that a builder should
not silently default:

- **The construction code's licence.** The data's licence says nothing about the code that derives
  it: a Public Domain source and an unlicensed script can coexist. Offer the real options (a
  permissive licence, a public-domain dedication, or "no licence; reproduction instructions only")
  and flag that leaving it unstated means all rights reserved.
- **Whether the labelled holdout ships publicly.** Permitted by most project checklists, provided it
  stays out of an evaluated agent's workspace - but it is the operator's call, and the alternative
  (holdout on request) is worth naming.
- **The repository name and the version scheme.**
- **Anything measured that a reader might read as a headline.** State the scope next to the number.

## Keeping the metric honest

A baseline produced by running a harness's contract is a *floor* for what an agent might do, not a
result about any agent. Say that in the release notes and the README, not only in the project's
internal notes - a published number travels without its context. Where a project has run no harness
comparison, say so explicitly rather than leaving the absence to be inferred.

## Plan-only publication tooling

A publish script should print exactly what it would do and stop:

- **Plan by default.** No flag, no action. Print the repository, the visibility, the version tag,
  each asset with its size and hash, the artifact version and the pinned commit, and one line saying
  nothing has been done.
- **Require an explicit, unambiguous confirmation flag** for execution, named for what it does
  (publication is irreversible), separate from the flag that merely enables execution.
- **Resolve the artifact-to-asset mapping from the producer's manifest**, not from asset names or
  their order, and fail when any file does not resolve to exactly one staged asset. That check is
  runnable immediately and is real evidence about the plan.
- **Do not ship an upload path you have not run.** Two implementations of "copy the bytes from a
  private release to a public one" are plausible and neither is free: a machine holding the bytes, or
  a publish step executed where the bytes already live. Writing out the numbered steps for the
  operator is a better deliverable than an unexercised upload pipe, which a reviewer cannot
distinguish from a working one and which will be trusted the first time it is used.

## Mechanics that cost time

- **A draft release has no tag namespace.** `GET /repos/{o}/{r}/releases/tags/{tag}` returns 404 for
  a release that plainly exists, and `gh release download` cannot fetch its assets either. Keep the
  **release id** from creation and address it by id; a staged artifact is normally a draft.
- **Release asset downloads answer 302** to a signed URL on another host. A downloader built on a raw
  HTTP connection that does not follow redirects reports the redirect as an error for every asset.
  Follow a few redirects, check the final status, and **drop the Authorization header** when you do —
  a signed URL is on a host that never asked for your token, and sending it there is a needless leak.
- **Verify an upload from the server's own digest.** The API returns `digest: "sha256:..."` on the
  created asset; compare that and the size, rather than trusting a 201 and your local hash.
- **`gh run list --commit <sha>` silently returns an empty list** for a commit that does have runs,
  which reads as "CI has not started". Address a commit's runs explicitly:
  `gh api "repos/{o}/{r}/actions/runs?head_sha=$(git rev-parse HEAD)"`.
- **A file with no suffix is refused by a bundle or source-file allowlist.** Standard names
  (`SHA256SUMS`) have none; add them by exact name rather than relaxing the rule to "any file".

## Moving the bytes without holding them

The coordinator is small and the dataset is not, so move artifacts store-to-store through an
ephemeral worker: one asset at a time — download, verify the hash on arrival, upload, verify again
from the server's digest, delete — so peak disk is one asset and never the dataset. Keep the read and
write credentials separate, and refuse the job at **plan** time when the needed one is missing: a
worker that dies from an unhandled auth error writes no report, looks permanently in flight, and has
to be recovered through the interrupted-job path rather than simply deleted. When a container has to
measure published bytes, have the host download them and mount the directory read-only — the
container stays credential-free and cannot leak what it does not hold.

## The fresh-consumer check

The only test that proves the package works is one run somewhere that has nothing but the package:
clone at the tag in a clean directory and verify every file against the manifest; download the assets
and run the checksum command the README documents; run the gate and require a pass plus the recorded
artifact version; run the baseline and require the recorded number, reproduced on the *published*
bytes rather than on a rebuild. Write the outcome into the package with its duration and exit status,
and state plainly what was not covered.

Re-run it after any change to the package. A file added after the tag was cut leaves `main` ahead of
the tag and the manifest stale; while nothing is public, re-cut the tag so tag, manifest and contents
agree.

## Pitfalls

- **Letting the package imply publication happened.** "Prepared for review" must appear in the
  handover, the manifest (`published: false`) and the release-notes draft.
- **A manifest assembled by hand from the write-up.** It will disagree with the artifact the moment
  either changes; generate both from the same recorded evidence.
- **A licence section that asserts a licence it did not read.** Quote the metadata response or the
  page text, name the date it was read, and for aggregator licence strings say plainly that they
  name no terms.
- **Publishing instructions with no pinned commit.** A reproducibility claim that resolves to
  "whatever the branch says today" is not a reproduction path.
