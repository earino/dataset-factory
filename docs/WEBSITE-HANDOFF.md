# Website integration handoff

For the builder implementing the first complete website system. Everything here is either a
command that exists today or a fact read from the services; where something is unknown it says so.

Scope of this document: **how a release is produced and what a website must agree with**. Website
implementation is the builder's during this milestone. The factory repository stays private, and
**public release and site deployment await the operator's approval** — prepare reviewable builds
first.

## 1. The release procedure as it exists

Entry points and the exact commands. Run everything from the repository root unless stated.

| step | command | what it does |
| --- | --- | --- |
| Construct | `sh scripts/scout-factory worker plan\|launch\|status\|collect\|destroy <job.json>` | Runs the candidate's build on a temporary worker. Job specs: `candidates/<id>/source/job.json`. Output uploads to the private staging repo. |
| Qualify | `python3 skills/dataset-qualification/scripts/qualify_dataset.py <dataset-dir>` | The gate. `--accept <report.json> <dir>` re-verifies a report against the exact bytes; `--selftest` proves the checker still detects what it claims. |
| Assemble | `python3 scripts/release-manifest.py <candidate-id>` | Writes `release/<id>/MANIFEST.json` + `SHA256SUMS` from recorded evidence, including the `licenses` block. |
| Check the package | `python3 scripts/check-package.py release/<id>` | Documents present, manifest covers every file, hashes match, terms declared, `SHA256SUMS` consistent. |
| Publish data → GitHub | transfer/publish worker jobs (`candidates/<id>/publish/source/job.json`) | Moves the accepted assets into the dataset's own GitHub Release. Bulk never passes through the coordinator. |
| Publish docs → GitHub | edit the clone at `.factory/publish/<id>`, then `git commit && git push`, then `git tag -f <tag> -m … && git push -f origin <tag>` | The publication repository is a **separate clone**; the tag is moved last, after the data is present. |
| Publish → Hugging Face | `python3 scripts/hf-publish.py --create --upload-small` then the `hf_publish` worker job then `--verify` then `--tag` | Card and docs from the manifest; the CSVs move on a worker. `--tag` is idempotent and always last. |
| Verify | `python3 scripts/check-package.py release/<id>` · `python3 scripts/hf-publish.py --verify` · a clean `git clone --branch <tag>` · the consumer job `candidates/<id>/consumer/source/job.json` | Four independent checks: package integrity, Hub digests, pinned clone, and a fresh environment with no factory access. |

**Which steps do what** — the distinction that matters for a website:

- **Create drafts:** package assembly (`release/<id>/`), the generated card (`scripts/hf-publish.py --plan` writes `.factory/hf-package/`), and the publication clone.
- **Upload:** worker jobs (data), `hf-publish.py --upload-small` (docs/card).
- **Verify:** the four checks above.
- **Tag:** `hf-publish.py --tag` (Hub) and `git tag -f <tag>` + force-push (GitHub). Both **last**.
- **Make content public: nothing in this procedure does.** Visibility is a manual, deliberate act
  on both platforms and requires the operator's approval. No script flips it.

## 2. Austin: current destinations and canonical sources

| | GitHub | Hugging Face |
| --- | --- | --- |
| Location | `https://github.com/earino/austin-911-response` | `https://huggingface.co/datasets/earino/austin-911-response` |
| Visibility | private | private |
| Version reference | tag `v2026.09`, release id `391804787`, 5 assets | revision `v2026.09`, 16 files |
| Artifact version | `e4598317e406984fa590aacc5e7aff675867578c51ae1a84ebf6279bc42c3328` | same |
| Verified | clone at the tag: 20 package files hash-checked, none failing | digest-verified (`train` `6fc37e03`, `eval` `241dee5e`, `holdout` `738ff7ec`), loading path exercised: 572,180 / 285,665 / 191,791 rows |
| Licence status | code **MIT**, docs **MIT** | card `license: cc0-1.0` for our compilation rights |
| Source licence | City of Austin data: **Public Domain** (designation, attribution and citation preserved); compilation dedicated **CC0-1.0** scoped to our contribution | same |

**Canonical sources — reuse these, do not restate them:**

| what a website needs | authoritative file | notes |
| --- | --- | --- |
| version, tag, artifact id, splits, labels, checksums, provenance, licence terms, measurements | `release/austin-911-response/MANIFEST.json` | single source for both platforms today; the HF card is *generated* from it by `scripts/hf-publish.py` |
| measured figures with the command that produced each | `release/austin-911-response/measurements.json` | clock offset, threshold search, extraction cost, duplicate identifiers |
| attribution, citation text, licence scope | `release/austin-911-response/LICENSE.md` | plus `LICENSE-MIT.txt`, `LICENSE-CC0-1.0.txt` |
| human-readable dataset description | `release/austin-911-response/README.md` | the GitHub landing page and the same content as the card |
| release narrative | `release/austin-911-response/RELEASE_NOTES.md` | monthly-post material |
| per-destination completion | `release/austin-911-response/DESTINATIONS.json` | written after each destination verifies; excluded from `package_files` on purpose |
| the queue and next action | `candidates/*/record.json` | candidate status and `next_action` |

Existing metadata worth reusing directly: the `configs`/`data_files` split block and `license:`
field in the generated card; `MANIFEST.json`'s `splits`, `assets`, `licenses`, `baseline`,
`qualification` and `measurements` blocks; the citation string in `LICENSE.md`.

## 3. How the routine advances a candidate, and where a website fits

**Scheduled work that exists today** (all on the coordinator's own scheduler, UTC):

| job | id | schedule | mode |
| --- | --- | --- | --- |
| research session | `69a5bc676d10` | `0 8 * * 1,3,5` | script-only: allowance gate, then one bounded agent run (`--max-turns` 60, `--run-budget` 2400 s) |
| weekly research digest | `10d4f73308c8` | Mondays 08:00 | script-only |
| secondary cleanup sweep | `e80975eddd4a` | hourly at :47 | script-only |
| two-week budget checkpoint | `22ce870ec66f` | 2026-10-03 08:00, once | script-only |

The research session resumes from `STATE.md`, advances **one** step — discovery, construction,
qualification or packaging — and commits it. Source: `deployment/scout/STATE-SNAPSHOT.md`,
regenerated by `scripts/scout-snapshot.py`.

**Proposed, not built:** website generation and catalogue updates should be **deterministic
release-time work**, not a recurring model job. Concretely: a script that reads
`release/<id>/MANIFEST.json` (plus `DESTINATIONS.json`) and emits the dataset site and the catalogue
entry, run as the last step of the release, and re-run whenever the manifest changes. It should be
idempotent like `hf-publish.py`, so a finished release can be re-rendered without side effects. If
a scheduled refresh is wanted later, it should be a script-only cron job — the same shape as the
digest — not an agent session.

## 4. Read-only inventory: Pages, Actions, access

Read on 2026-09-19 with the `gh` CLI. **Nothing was enabled or changed.**

| | `earino/dataset-factory` | `earino/austin-911-response` |
| --- | --- | --- |
| Visibility | private | private |
| Pages site | **none** (`has_pages: false`, API 404) | **none** (`has_pages: false`, API 404) |
| Workflows | `Local checks` (`.github/workflows/check.yml`, active, `on: [push, pull_request, workflow_dispatch]`, `permissions: contents: read`); `Expired worker cleanup` (`.github/workflows/cleanup.yml`, active, `schedule: 17 * * * *` + `workflow_dispatch`, `permissions: contents: read`, `concurrency: hetzner-expiry-cleanup`) | none |
| Deployment environments | none configured (API 404) | none reported |

Account-level facts that affect the design:

- **`earino.github.io` exists, is public, and already has Pages enabled** — the account's root site
  path is taken. A central presentation repository would therefore be a *project* site
  (`https://earino.github.io/<repo>/`) unless a custom domain is chosen.
- Other Pages-enabled repositories on the account: `applied-deep-learning` (public), `CueGraph`
  (public). Both are public repositories.
- Free names at the time of writing: `dataset-factory-site`, `dataset-factory-website`,
  `dataset-website` (all 404).
- The `gh` credential available here carries scopes `repo`, `workflow`, `admin:org`, `gist`,
  `write:discussion` — enough to create repositories, push workflows and enable Pages.

**Unknowns, reported as unknowns:** whether the account's plan permits Pages on a *private*
repository, and what visibility a Pages site published from a private repository would have (private
Pages is a paid-tier feature; a public site from a private repository is not guaranteed); whether an
Actions spending limit is configured (not exposed by the API here); the repository-level default
`GITHUB_TOKEN` permission setting; and the builder's own access level. The builder should confirm
these before choosing a repository visibility, and must not enable Pages or change visibility as part
of this inventory.

## 5. Constraints and likely integration pitfalls

1. **A private repository may not be able to serve a Pages site on this plan.** If the presentation
   repository must be public to serve, that is a publication decision for the operator — prepare the
   build and ask, do not flip it.
2. **The root site path is taken** by `earino.github.io`. Decide explicitly: project site under
   `/dataset-factory-site/`, or a custom domain the operator owns.
3. **Bulk data never goes in a site repository.** It lives on GitHub Releases and Hugging Face; the
   site links to it. Don't mirror CSVs into Git, and don't fetch them at build time to render
   counts — read the counts from `MANIFEST.json`.
4. **Public holdouts are permitted.** Keep holdout labels outside the evaluated agent's
   workspace during a run. The website links to versioned holdout downloads. It embeds
   no dataset rows, following the same bulk-data rule as train/eval; public availability
   itself does not defeat the evaluation protocol.
5. **Version agreement is the thing to test.** The site, the catalogue, the GitHub tag and the Hub
   revision must all state the same `release_tag` and `artifact_version`. A stale site claiming an
   older version is the failure mode.
6. **`.factory/publish/<dataset>` is a git clone.** Overwriting it with `cp -a` (or any copy that
   drops the nested `.git`) leaves a directory where git silently walks up to the parent repository
   and reports "nothing to commit" — that already happened once here. Mirror files into it, commit
   from inside it, and verify with `git -C .factory/publish/<id> status`.
7. **Tag last, on both platforms.** A tag that precedes the data pins a commit without the files,
   and a version-pinned load then fetches nothing. `hf-publish.py --tag` and the GitHub
   force-pushed tag both move last, and both are safe to re-run.
8. **Do not add a model-powered recurring job for site updates.** Release-time, deterministic,
   idempotent — see §3.
9. **Licence rendering comes from the manifest.** The card's terms are generated from
   `MANIFEST.json`'s `licenses` block; a website must do the same rather than restating them, or the
   three surfaces will drift.
10. **CI is the gate, and it is checked per commit.** The factory repo runs the suite and
    `factory doctor` on every push; read the result for the exact commit SHA (the `head_sha` API,
    not `gh run list --commit`, which silently returns nothing).

## 6. Proposed end-to-end acceptance exercise (Austin)

Reviewable before anything is deployed:

1. **Render locally, offline.** Generate the dataset site and the catalogue entry from
   `release/austin-911-response/MANIFEST.json`. No network access required.
2. **Assert agreement** — the site must state:
   - version `v2026.09` and artifact `e4598317e406984f…` identically to the manifest;
   - split counts and positives: train 572,180 / 231,025, eval 285,665 / 109,860, holdout
     191,791 / 72,450;
   - the licence table as generated: code MIT, compilation CC0-1.0, source Public Domain preserved,
     with the City of Austin attribution and the suggested citation from `LICENSE.md`;
   - links to `https://github.com/earino/austin-911-response` and
     `https://huggingface.co/datasets/earino/austin-911-response`.
3. **Assert cross-linking:** dataset site → GitHub repo → Hub dataset → catalogue, each identifying
   the same version tag, and the catalogue listing Austin with that version.
4. **Run it in CI on a branch**, producing the rendered output as a build artifact (or a Pages
   preview deployment) — not a live deploy. The existing checks must still pass, and any new site
   check should be added to the repo's suite so it runs per commit like the others.
5. **Then** the operator approves publication, and only then are Pages enabled and the site
   deployed, on both the dataset site and the catalogue.
