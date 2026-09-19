# The website publication system

The deliverable is a repeatable release-to-website pipeline operated by Scout.
Austin exercises the first run. Another dataset uses the same commands and renderer;
it supplies its own release package and a small editorial JSON file.

The entry point is `python3 scripts/site-publish.py`. Rendering and orchestration use
Python's standard library. The existing authenticated `gh` CLI manages GitHub. A small
adapter runs in Scout's existing Hugging Face Python environment and explicitly uses
`HF_TOKEN_WRITE` or `HF_TOKEN_WRITE_FILE`. On the hosted machine its file fallback is
`/opt/data/.secrets/huggingface-write.token`, matching the established worker setup.
The inference token is removed from that adapter's child environment.

## Inputs and ownership

| Input | Owner and purpose |
| --- | --- |
| `release/<dataset>/MANIFEST.json` | Existing release procedure: versions, qualification, measurements, assets and terms |
| `release/<dataset>/DESTINATIONS.json` | Existing release procedure: both copies verified against that artifact |
| `sites/<dataset>.json` | Scout: title, summary, task type/domain, release date, short release post and limitations |
| `config/sites.json` | Shared catalogue name, copy and hosting choice |
| `sites/runtime.py`, `sites/pages.yml` | Shared renderer and deployment workflow maintained with the pipeline |

No field selects a dataset-specific Python implementation. Numeric facts come from
the manifest; Scout writes the explanation. No CSV is downloaded to build a site.
The output record is an explicit public projection, excluding staging URLs, job
records, credentials, the private factory's operational state and source code.

Hosting starts with project sites:

- Catalogue: `earino/dataset-factory-site`, at `https://earino.github.io/dataset-factory-site/`.
- Dataset: its existing dataset repository, with a Pages site under that repository's name.
- Data: existing GitHub Releases and Hugging Face, including downloadable labelled holdouts.

The account root site remains independent. Custom domains require a future hosting
configuration change; this version refuses to replace an existing custom domain.

## Normal release lifecycle

### 1. Prepare offline

After qualification, package checks and verification at both dataset destinations:

```sh
python3 scripts/site-publish.py prepare release/austin-911-response \
  --editorial sites/austin-911-response.json \
  --out .factory/sites/austin-v2026.09-1
```

This writes a self-contained `bundle.json`, `REVIEW.md`, and both rendered previews.
The output includes a `plan_sha256`, covering the projected release record, target
repositories, URLs, renderer and workflow. It performs zero network calls and does
not change the release package. Repeating identical inputs produces identical bytes.
A changed plan requires a new output folder so an earlier review or receipt survives.

Inspect `preview/dataset/index.html` and `preview/catalog/index.html`. The offline
catalogue preview shows the incoming release; the live build also reads every earlier
record already in the catalogue repository. The private factory's Website pipeline
preview workflow provides the bundle as a downloadable Actions artifact.

### 2. Inspect access and destination state

```sh
python3 scripts/site-publish.py inspect .factory/sites/austin-v2026.09-1
```

This is read-only. It checks the GitHub release, the Hub revision, their manifests
and asset digests, then reports the target repositories' Pages and Actions settings.
Use `--hf-python /path/to/python` if the existing Hub environment is elsewhere.
An unavailable dependency or credential is an actionable preflight failure, never a
reason to fall back to the inference credential.

GitHub access needs read/write contents, workflows, Pages, environment administration,
and Actions dispatch for the site repositories, plus permission to create the catalogue
if it does not exist. Existing branch and environment protection rules remain in force.
The deployed workflow uses repository-scoped `GITHUB_TOKEN`/OIDC; no PAT or Hub token is
stored in a public repository or supplied to Actions.

### 3. Obtain the existing publication approval

Public dataset releases and website publication still require the operator's approval.
Scout presents the concrete review bundle and records that approval in project state.
An agent must not invent approval just because it can read the plan digest.

The dataset release procedure remains responsible for making GitHub and Hugging Face
public, updating publication notes and verifying the data release. Website publication
refuses private dataset destinations. Approval for a website does not silently change
either dataset's visibility. The site plan explicitly includes creating a public
catalogue repository if it is absent.

### 4. Publish, with bounded recovery

After approval and the public dataset release, use the exact digest from the review:

```sh
python3 scripts/site-publish.py publish .factory/sites/austin-v2026.09-1 \
  --approved-plan <reviewed-plan-sha256> --wait-seconds 600
```

The pipeline:

1. Reads the two data destinations again; checks the pinned manifests and asset digests.
2. Creates the catalogue if absent, or verifies ownership of the existing one.
3. Commits the managed renderer, configuration, release record, edition and workflow
   to each repository. Git tree updates preserve other files and previous releases;
   ref updates are fast-forward only. A concurrent edit is a refusal to overwrite it.
4. Adds/replaces a bounded navigation block in GitHub's README and the Hub card,
   preserving the rest of each document and the card's YAML header. GitHub's current
   manifest gets hashes of the updated README and managed website files. Dataset tags
   and data files remain unchanged.
5. Creates Pages with workflow publishing, ensures the `github-pages` environment
   exists, enables HTTPS and sets the repository's homepage link. A different existing
   homepage or unmanaged Pages site is a conflict to review. Environment protections remain.
6. Dispatches a deployment for the exact committed SHA, verifies its deployment job
   actually succeeded, and reads back the dataset's public JSON and HTML links.
7. Deploys the catalogue after the dataset site verifies. Reads back the catalogue's
   release record and links, then checks GitHub and Hub navigation again.

Ordinary pushes and pull requests build review artifacts. Deployment runs only on
explicit workflow dispatch, on the default branch, with an approved full commit SHA.
The workflow does not clone the private factory or run Scout; all renderer inputs
needed for a build live in the public repository itself.

### 5. Read the outcome and resume

```sh
python3 scripts/site-publish.py status .factory/sites/austin-v2026.09-1
python3 scripts/site-publish.py verify .factory/sites/austin-v2026.09-1
```

Exit codes: `0` completed/read-only operation succeeded; `2` publication pending;
`1` failure. A pending deployment is not a completed release. `receipt.json` records
the observed steps, commits, run URLs when available, error and next action.

Re-run the same publish command to resume. Successful commits and card edits are
no-ops on retry. A recent uncertain dispatch waits before attempting another; a
single invocation polls for at most 600 seconds, with a maximum of three dispatch
attempts per commit across resumes. After investigating a failed workflow, Scout
can use `--retry-failed` to reset that small dispatch allowance. This does not reset
worker or model accounting. No new model-powered scheduler is needed.

The receipt is a recovery aid. Every run checks provider state again; deleting a
receipt cannot fabricate a successful deployment. Commit a compact receipt summary
to project state when done. Keep the review bundle with its inputs/code revision
until the release is finished; it can also be reconstructed from those exact inputs.

## Next dataset and subsequent edits

For the next dataset, supply its existing package and copy the editorial JSON shape
under a new filename. Change the text and release date, then run the same procedure.
The catalogue accumulates records by dataset and version. Adding a dataset does not
replace earlier records or require editing a shared list of hard-coded dataset names.

`site_revision` starts at 1. To correct explanation or presentation for the same
dataset version, increment it and prepare a new review bundle. The public record
advances and an immutable edition is retained at
`versions/<tag>/editions/<site_revision>/`. Earlier editions also remain in Git.
Older site revisions cannot overwrite newer ones. Changes to the artifact, splits,
source, baseline or terms require the dataset's own release/version procedure.

Website navigation changes advance default-branch documentation. The data release
tag stays pinned; it is not force-moved to keep up with website edits. Tag-last and
tag/main agreement apply when creating a data release, not forever afterwards.

Scout owns operation, recovery, release content and ordinary repairs. The builder
is not a required reviewer for each new dataset. The existing operator approval
boundary is independent of which agent wrote the implementation.

## Acceptance and remaining live verification

The lifecycle suite covers a second metadata fixture through the real preparation
command, immutable dataset identity, website editions, partial failure, lost local
receipts, repeat no-ops, missing public access, concurrent edits and incorrect live
HTML despite matching JSON. These are software tests, not claims of a second real
qualified dataset or a completed public deployment.

The initial handoff must also exercise the generated workflow on GitHub and a hosted
Scout `inspect` call. Public Pages setup/deployment and live Hub card writes can only
be verified after the corresponding publication approval. After that, Scout completes
one real publication and one editorial revision independently using these commands.
Record those observations separately from unit tests and preview builds.

Provider references checked 2026-09-19:

- [GitHub Pages API](https://docs.github.com/en/rest/pages/pages)
- [Custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [Git tree API](https://docs.github.com/en/rest/git/trees)

GitHub action versions are pinned to the commits resolved from their official
repositories. Repository privacy does not imply Pages privacy, so a preview uses
Actions artifacts rather than enabling an unapproved live site.
