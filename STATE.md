# Current state

Updated: 2026-09-25 (latest entry: watcher run on `noaa-consumer-003` - the clean-room consumer check
re-ran against the re-issued NOAA bytes and passed every stage, so the published-bytes pass now belongs to
the bytes the release holds rather than to the superseded noaa-003 artifact. The package prose pass and the
Hub's small files and version tag are still owed before publication; both destinations remain private.)

## 2026-09-25 16:06 UTC - noaa-consumer-003: the consumer check now belongs to the bytes the release holds

The re-run the record has owed since noaa-publish-002 - noaa-consumer-002's PASSED described the superseded
noaa-003 artifact - was launched from an interactive session at 15:57 and finished under the watcher in 74 s
of worker time. This entry records the measured result and what it closes.

**Measured** (`.factory/noaa-consumer-003/reports/`, `result.json`, `jobs/noaa-consumer-003.json`):

| step | result |
| --- | --- |
| fetched | 10/10 files from the dataset release 396698120 (`earino/noaa-tide-flooding`, tag `v2026.09`), **196,018,020 bytes**, `failures: []`, every digest equal to `artifacts[0].levels` |
| package vs `MANIFEST.json` | every listed file matched its recorded hash |
| `sha256sum -c SHA256SUMS` | OK |
| gate, temporal / station_disjoint | exit 0, `QUALIFICATION PASSED`, artifacts `bb051dc304a4ee63` / `92297a5b62f86b29` - both equal the accepted artifact's versions |
| baseline, temporal / station_disjoint | `CONTRACT OK`, eval AUC **0.8633** / **0.8690** |

The two baseline AUCs are the recorded pair itself, not a spread around it: noaa-baseline-002 measured
0.8633/0.8690 on the same corrected bytes and this independent clean-room run reproduces both to the digit,
where the superseded bytes gave 0.8651/0.8687 against a recorded 0.8638/0.8688. No run scored the holdout.

**One residual, recorded rather than fixed here.** The bundled harness and the shipped
`baseline/reproduce_baseline.sh` both print a hardcoded expectation line carrying the superseded pair, so the
last line of `output_consumer.txt` reads "expected: temporal 0.8638, station_disjoint 0.8688" while the
package's own `MANIFEST.json` carries 0.8633/0.8690. The printed line is a constant, not a read of the
manifest, and no check failed. It belongs to the package-prose pass (item 1 below), which still owes the
`late` label row in `DATA_DICTIONARY.md`, the job-`noaa-003` qualification row in `VERIFICATION.md`, and the
superseded figures in `README.md`/`RELEASE_NOTES.md`/`REPRODUCE.md`/`baseline/README.md`/
`code/persistence_baseline.py`.

**Changed here, with the outcome.** `release/noaa-tide-flooding/VERIFICATION.md` said the consumer check
"must be re-run on these bytes"; it now records the pass above with the step table, keeps the superseded pass
beside it, and names the job in its summary row. `MANIFEST.json` was regenerated with
`scripts/release-manifest.py`: the only change is `package_files["VERIFICATION.md"]` (399 keys otherwise
identical). `check-package.py release/noaa-tide-flooding` passes. `release/noaa-tide-flooding/
DESTINATIONS.json` - untracked until now - was written by `scripts/hf-publish.py --verify` at 15:57 under the
tool's convention that `revision` carries the package tag label: its `verified: true` means the Hub's
*default branch* (`main`, `3116c306`) matched every file, **not** that the Hub tag does. `v2026.09` on the
Hub still resolves to `ee6ba847`, the noaa-003 commit, so the tag item stays open and item (1) is still its
gate.

**Recorded**: `candidates/noaa-tide-flooding/record.json` (a `noaa-consumer-003` entry in `jobs`;
`consumer_verification` re-pointed at this run with the superseded pass kept under `previous`; `next_action`
rewritten so the consumer item reads closed), `jobs/noaa-consumer-003.json`, `release/noaa-tide-flooding/
{VERIFICATION.md,MANIFEST.json,DESTINATIONS.json}`, this file. Worker `167442487` destroyed after collection
and confirmed gone from the provider (`GET /v1/servers/167442487` -> 404, and no factory-labelled servers
remain).

**Next action**: (1) the package-prose pass, then `scripts/hf-publish.py --create --upload-small`, `--verify`,
and `--tag` **last** so the Hub's `v2026.09` and `main` agree; (2) the persistence-floor decision - carry the
noaa-003 figures with the recorded note or re-measure on the corrected eval split; (3) the publication act
the operator approves, on both destinations, from one manifest. Both destinations stay private until then.

## 2026-09-25 15:27 UTC - noaa-hf-003: the Hub carries the corrected NOAA bytes; its tag and docs do not

The worker job that moves the bulk of a dataset release was launched from an interactive session at 15:20
and finished under the watcher in under a minute of worker time. It published the corrected noaa-004 files
to `earino/noaa-tide-flooding` revision `main`. This entry records what was verified from the service and
what the Hub half of the re-issue still owes.

**Measured** (`.factory/noaa-hf-003/result.json`, `reports/manifest.json`, `jobs/noaa-hf-003.json`):

| item | value |
| --- | --- |
| staged | private staging release 396718146 (`job-noaa-hf-003`), report assets collected and digests matched |
| transferred | **10 of 10** target files, **196,018,020 bytes**, `failures: []`, `skipped: []` - a real upload, not a digest-skip |
| loading check | `ok: true`, `problems: []`, all six splits matched the accepted counts |
| rows train/eval/holdout | temporal 697,373 / 89,038 / 88,841; station_disjoint 461,580 / 29,930 / 29,930 |
| positives | temporal 11,774 / 1,815 / 2,850; station_disjoint 7,513 / 788 / 1,090 |

The six loading-check splits are identical to `noaa-baseline-002`'s counts on the accepted artifact, so the
Hub copy is the same panel and not a neighbouring revision.

**Verified by reading the Hub, not the job's claim.** Revision `main` moved to `3116c306`, and every one of
the ten file paths was checked against `release/noaa-tide-flooding/MANIFEST.json` and the accepted
`artifact_version fb49f932...`: six small files were downloaded and re-hashed here (meta.json 867,
quality.json 3,793/3,795, station_disjoint holdout 4,228,360 and eval 4,229,477, temporal/meta.json 750) and
four large LFS objects were read from the Hub's own `sha256` (station_disjoint/public/train.csv `d7d2bff2`,
temporal/private/holdout.csv `89db2e79`, temporal/public/eval.csv `a2d733a8`, temporal/public/train.csv
`60854702`). **10 of 10 sizes and digests match.** The superseded numbers recorded on 2026-09-25 15:06
(12,475,942 / 4,228,351, label column `late`) no longer describe `main`.

**What has not moved, measured rather than assumed.** `v2026.09` on the Hub still resolves to `ee6ba847`,
the noaa-003 commit, while `main` is `3116c306` - so a version-pinned Hub reader still gets the superseded
bytes, and re-tagging (`scripts/hf-publish.py --tag`, which replaces the existing tag) has not been run. The
Hub's `MANIFEST.json` and `SHA256SUMS` on `main` also still list the noaa-003 digests, i.e. `--upload-small`
has not been re-run either. That hold is deliberate and it is the reason this job is a partial re-issue
rather than a complete one: `release/noaa-tide-flooding/DATA_DICTIONARY.md` still names the shipped label
column `late` and `VERIFICATION.md` still cites job `noaa-003`, so uploading the small files today would
publish prose contradicting the `temporal/meta.json` (label `minor_flood`) now on the Hub. Exposure is zero
- every stale digest is the superseded version's own and both destinations are private - but the Hub package
does not yet describe the bytes it holds. **The package prose must be re-pointed at noaa-004 before the
small files and the tag are pushed.**

**Recorded**: `candidates/noaa-tide-flooding/record.json` (a `noaa-hf-003` entry in `jobs`; the
`artifacts[0].huggingface` block re-measured - `main_commit 3116c306`, `tag_commit ee6ba847`,
`tag_matches_main false` with a note that the old `true` described the 2026-09-20 upload, and a new
`reissue` block carrying the per-file verification, the loading check and the `still_lagging` items;
`next_action` rewritten), `jobs/noaa-hf-003.json` and `candidates/noaa-tide-flooding/hf/job-003.json`
committed. Worker `167437889` destroyed and confirmed gone from the provider (no factory-labelled servers
remain; a direct `GET` on the id returns 404). `check-candidate.py --all` and `check-package.py
release/noaa-tide-flooding` both pass on this state.

**Next action**: (1) re-point the release package prose at noaa-004 - the label row in `DATA_DICTIONARY.md`,
the job references in `VERIFICATION.md`, the README/RELEASE_NOTES/measurements pass - regenerate
`MANIFEST.json`/`SHA256SUMS` with `scripts/release-manifest.py`, then run `scripts/hf-publish.py --create
--upload-small`, `--verify`, and `--tag` **last** so the Hub's `v2026.09` and `main` agree; (2) re-run the
clean-room consumer check against the re-issued bytes; (3) decide the persistence-floor question; (4) then
the publication act the operator approves, on both destinations, from one manifest. Both destinations stay
private until then.

## 2026-09-25 15:10 UTC - noaa-publish-002: the corrected artifact is in the GitHub release, the Hub half still lags

The re-issue of the NOAA release was launched from an interactive session at 14:54 and finished under the
watcher (succeeded, under a minute of worker time). This entry records what was verified and what the
authorised sequence still owes.

**Measured** (`.factory/noaa-publish-002/reports/manifest.json`, `result.json`, `jobs/noaa-publish-002.json`):

| item | value |
| --- | --- |
| source | private staging release 392410743 (`job-noaa-004`), the ten corrected `minor_flood` files |
| target | `earino/noaa-tide-flooding` release 396698120, tag `v2026.09` |
| transferred | 10/10 assets, **196,018,020 bytes**, `failures: []`, artifact version `fb49f932...` |
| verified | every target asset re-read from the GitHub API: size and sha256 equal the job's transferred values, 10 of 10, and equal `release/noaa-tide-flooding/MANIFEST.json`'s `files`/`assets` digests |

The check was made against the service rather than against the job's own claim. The ten `source_asset_id`s
in the spec are `file-0002`..`file-0011` of staging release 392410743 and carry exactly the digests that
were transferred, so the source was the corrected artifact and not a neighbouring release. The superseded
release is gone: `gh release list` returns one release, `v2026.09` -> 396698120, and 392387511 with the
noaa-003 bytes is no longer listed - its digests are kept in `record.json`
(`artifacts[0].previous_issue`) so the old version stays checkable. The job's own manifest records
`uploaded: false` because the transfer path uploads per file instead of one bulk archive; the `transfer`
block is the report that matters.

**The tag divergence is closed - measured, and not by the route that was planned.** `v2026.09` and `main`
now resolve to the same commit `bef3a412` (`compare main...v2026.09` -> `identical`, ahead/behind 0/0).
That commit is itself a **root commit** (`parents: []`) carrying the re-issue message, and the release was
created from it with `target_commitish: main`. So the state recorded on 2026-09-20 - tag -> `9bcbf2c6`,
`main` -> `f384889f`, unrelated roots, compare 404 - was removed by replacing the history rather than by
the single fast-forward the record had planned. What the release rule asks for (a version-pinned reader
and a main-branch reader see one commit) now holds; the one-commit fast-forward is therefore not owed. The
superseded tag commit `9bcbf2c6` still exists as an object with no ref pointing at it.

**What did not move: the Hub half.** Verified from the API today, not assumed: the Hugging Face revision
`v2026.09` still carries the superseded bytes - `temporal/private/holdout.csv` 12,475,942 against the
corrected 12,475,947, `station_disjoint/private/holdout.csv` 4,228,351 against 4,228,360,
`temporal/meta.json` still naming the label column `late`, and its `MANIFEST.json` hashing `55791180...`
against the package's `60ffed39...`. `artifacts[0].huggingface.verified: true` describes the noaa-003
upload of 2026-09-20 and does not carry over to these bytes. The clean-room consumer check has likewise
not been re-run: noaa-consumer-002's PASSED belongs to the superseded bytes.

**Recorded**: `candidates/noaa-tide-flooding/record.json` (job `noaa-publish-002`; `artifacts[0]`
re-pointed at release 396698120 with the corrected per-level digests and the superseded issue kept under
`previous_issue`; `github_tag_state` re-measured; a `huggingface.superseded` block carrying the file-level
evidence and the ten source asset ids for the Hub job; `next_action` rewritten), this file. Worker
`167435107` destroyed after collection. `check-candidate.py --all` and `check-package.py
release/noaa-tide-flooding` both pass on this state. **CI for the commit that records this is not verified**: the workflow run for `be83b1d` failed before any step ran, with the check-run annotation "The job was not started because recent account payments have failed or your spending limit needs to be increased" - a GitHub billing condition outside this repository, not a test failure. The suite was run here instead with the same command the workflow uses (`python3 -m unittest discover -s tests`): **283 tests, OK**, and `check-candidate.py --all` / `check-package.py` pass. Re-running CI is pointless until the account's Actions billing is restored; the change itself is docs-and-records only.

**Next action**: (1) prepare and launch the hf_publish job for the corrected files from release 396698120
(the ten source asset ids and new digests are in `record.json`
`artifacts[0].huggingface.superseded.next`), then the loading check and `hf-publish.py --verify`; (2)
re-run the clean-room consumer check against the re-issued bytes; (3) decide the recorded persistence-floor
question (carry the noaa-003 figures with the note, or re-measure on the corrected eval split); (4) then the
publication act - flip both destinations, prove the read from an anonymous client, record it in
`DESTINATIONS.json` **before** regenerating the manifest, refresh card/LOADING.md/README/release notes, and
publish the site. Both destinations stay private until then.

## 2026-09-25 10:45 UTC - noaa-baseline-002: the baseline on the corrected artifact, and what adoption does not yet mean

The corrected artifact was adopted at 10:33 and its baseline was measured by `noaa-baseline-002`, launched
from an interactive session at 10:35 and collected by the worker watcher. This entry records the result and
the state it leaves; the release work itself is listed as the next action rather than half-done.

**Measured** (`.factory/noaa-baseline-002/reports/baseline.json`, `container.log`, four runner logs):

| level | eval AUC | validate AUC | contract | rows train/eval/holdout |
| --- | --- | --- | --- | --- |
| temporal | **0.8633** | 0.8633 | OK | 697,373 / 89,038 / 88,841 |
| station_disjoint | **0.8690** | 0.8690 | OK | 461,580 / 29,930 / 29,930 |

Row counts and positive rates are identical to `noaa-baseline-001` in all six splits (0.016883 / 0.020385 /
0.03208 and 0.016277 / 0.026328 / 0.036418). The job **fetched** the ten files from private staging
(10/10, 196,018,020 bytes, zero failures, each against the builder's digest) instead of rebuilding, so the
number belongs to the bytes that will be published. It also records the dependency versions the first
baseline omitted (pandas 2.3.3, numpy 2.5.3, xgboost 3.4.1, scikit-learn 1.9.1). The earlier measurement
(0.8638 / 0.8688) was taken on the superseded artifact and is kept beside this one; the two agree to about
0.0005, the label column's name being the only schema difference.

**Adopted, not re-issued.** `candidates/noaa-tide-flooding/baseline/expected_artifact.json` now names
noaa-004 (temporal `bb051dc3...`, station_disjoint `92297a5b...`, both gated 32/32 on gate 1.3.0), and the
record's `qualification` and `baseline` blocks now carry that artifact. What did **not** change: the private
GitHub release `v2026.09` in `earino/noaa-tide-flooding` and the Hugging Face revision still hold the
noaa-003 bytes labelled `late`. Both destinations are private, so the exposure is zero, but the publication
the operator authorised must ship noaa-004.

I left the release package matching the bytes it actually holds rather than renaming it ahead of the
artifact: `release/noaa-tide-flooding/DATA_DICTIONARY.md` keeps the shipped label name, and `MANIFEST.json`,
`README.md`, `VERIFICATION.md`, `REPRODUCE.md`, `RELEASE_NOTES.md`, `measurements.json` and the `code/`
copies still describe noaa-003. A doc renamed before the artifact it sits beside would describe bytes that
are not in the package, and `VERIFICATION.md`'s consumer-check rows cannot be rewritten until the new
consumer check has actually run. `check-candidate.py --all` and `check-package.py release/noaa-tide-flooding`
both pass on this state.

**One hygiene fix, in the same commit.** Tracking the fetch bundle made CI's job-id uniqueness
check fail: the older rebuild-and-measure baseline bundle under `baseline/source/` had been bumped to
`noaa-baseline-002` on 2026-09-20 for a rerun that was never launched, so the id collided with the fetch
variant that actually ran. That stale bundle is renamed `noaa-baseline-rebuild-001` with a note explaining
why; the fetch variant keeps 002, which is the job the record describes.

**Recorded**: `candidates/noaa-tide-flooding/record.json` (job `noaa-baseline-002`; `baseline` and
`qualification` re-pointed at noaa-004 with the superseded values kept; `noaa-004.adopted` with the
decision, what changed and what did not; `artifacts[0].superseded_by`; `next_action` rewritten),
`candidates/noaa-tide-flooding/baseline/baseline_result.json`, this file. Worker `167401677` destroyed.

**Next action** (in order, from `record.json.next_action`): apply
`candidates/noaa-tide-flooding/noaa-004-label-rename.diff` to `build.py`/`persistence_baseline.py` and their
package copies; re-point the package prose and numbers at the corrected artifact and regenerate
`MANIFEST.json`/`SHA256SUMS` with `scripts/release-manifest.py`; decide whether to re-measure the
persistence floor on the corrected eval split or carry the superseded figures with the note now recorded;
transfer the ten files from staging release 392410743 on a worker; re-run the clean-room consumer check
(noaa-consumer-002's pass belongs to the superseded bytes); then flip both destinations, prove anonymous
read, record it in `DESTINATIONS.json` before regenerating the manifest, refresh the card/README/release
notes and publish the site. The GitHub tag item is unchanged: `v2026.09` and `main` are unrelated root
commits and the tag needs the one-commit fast-forward fix.

## 2026-09-21 08:45 UTC - md-sewer-overflow discovery: currency closed, target contract blocked

The only lead with **no verdict** was `md-sewer-overflow` (`investigating`), so this session
spent itself on the cheapest-first discovery path and ended with a verdict rather than a link.

**Measured** (`python3 .factory/probe_md_series.py`, Socrata `date_trunc_ym` group-by with
Cloudflare retries):

| series | total rows | boundary |
| --- | --- | --- |
| `3rgd-zjxx` | 27,479 | 2022-12: 122, 2023-01: 30, 2023-02: **7** - ends 2023-02-10 |
| `stgj-u72u` | 3,439 | 2023-01: **1**, 2023-02: 46, 2023-03: 64 ... 2026-09: 39 |

The series **abut** rather than duplicate: the historical one runs out in February 2023 and the
current one starts in January 2023 with a single row. The current series grew 3,434 -> 3,439
since 2026-09-18, a second independent confirmation that it is live. Row-level confirmation is
still unmeasured - both `$where ... between` range queries answered **HTTP 403** on every
attempt (five on the first run, four on the second; the first run's traceback arrived after
this session had already written up) while the `$select`/`$group` queries in the same runs all
succeeded, so the refusal tracks the quoted-literal `$where` URL shape, not the host.

**The rainfall join is proven feasible without a token** (`probe_md_rainfall2/3.py`):
`ncei.noaa.gov/data/global-historical-climatology-network-daily/access/<ID>.csv` answers 200
with PRCP populated on 877/1055, 1291/1296 and 1242/1266 days since 2023-01-01 for three
stations tested; CDO API v2 without a token is HTTP 400. `ghcnd-inventory.txt` supplies the
per-element first/last year that `ghcnd-stations.txt` lacks. **Not measured:** the Maryland
active-station count - my station filter read the wrong column, so the 6,873 in
`probe_md_rainfall_result3.json` is US-wide and must not be quoted as a Maryland figure.

**Parked, with the blocker named.** Contracts 1 (Public Domain, read directly), 2 (prediction
instant = start of the target day) and 4 (positives across 2005-2026) look satisfiable.
Contract 3 does not: only facilities that *reported* ever appear, so a facility-day grid built
from these tables alone has a survivorship-biased negative class, and no Maryland
collection-system registry has been identified or tested. The novelty check is also unrun.
Spending construction on a denominator that may not exist is exactly what the discovery skill
exists to prevent, so the verdict is `parked` rather than `ready`.

**Recorded**: `candidates/md-sewer-overflow/record.json` (`status`/`verdict` = parked,
`parked_reason`, `open_questions`, `next_action`, and the measurements above),
`candidates/md-sewer-overflow/notes.md`, and the four probes plus their JSON results in
`.factory/`. Nothing was built, no worker was launched, no credential was touched.



## Objective

Prepare the first discovered prediction task for a monthly public release. Scout
runs on NousCloud with **1.9 GiB RAM and about 6 GB persistent disk**, coordinating
Docker jobs on temporary Hetzner workers. Each published dataset gets its own
public repository and versioned GitHub Release assets.

## Ready in this repository

- Revised project specification, agent instructions, handoff and first assignment.
- Completed hosted inventory; reuse native research, browsing and scheduling.
- Candidate tracking and stdlib worker lifecycle: cost reservations, interrupted
  creation recovery, SSH dispatch, direct private uploads, verified collection
  and confirmed cloud cleanup.
- Independent GitHub Actions expiry sweeper, disabled until configured.
- Tiny synthetic infrastructure smoke job and local failure-path tests.
- A public dataset README template describing the eventual release contract.
- Hosted GitHub access verified: clone, branch push/deletion, release and run
  listing, successful CI. `gh` v2.101.0 installed after checksum verification.
- Private staging repo `earino/dataset-factory-staging` (builder-created). Its
  restricted worker token is still needed.
- `scripts/scout-factory` launcher with `_FILE` credential paths, `doctor`
  credential presence assertions and live memory reporting.

## Completed on the hosted instance, 2026-09-18 (second session)

- Pulled `01a84a1` and read `deployment/BUILDER-REPLY.md`.
- `sh scripts/scout-factory doctor` runs and reports memory, GitHub CLI, benchmark
  and credential state. `doctor --require-worker-credentials` exits 1 with both
  credentials reported missing or unusable, as expected before provisioning.
- All **30** tests pass locally under Python 3.13.5 (the builder reported 30 on
  GitHub Actions as well).
- SSH: generated ed25519 keypair `/opt/data/.ssh/scout_worker_ed25519`
  (fingerprint `SHA256:k4Uk+aJCEV28M7xvwsIzE3v0agPBXNrPXN/GGRFusms`, comment
  `scout-dataset-factory-worker`). No key existed before; nothing was overwritten.
  The public key is recorded in `deployment/ssh-worker-public-key.md` for Hetzner
  registration. Not yet registered.
- Secrets: created `/opt/data/.secrets` (0700). Both token files are still absent;
  only the operator can supply them, and only into those paths.
- Policy: `config/local.json` created from the example with `enabled: false`,
  `monthly_budget_eur: 0`, empty `allowed_locations` and `server_types`, staging
  repo set, SSH key paths set. Ignored by Git. Paid launches remain impossible.
- Benchmark checkout re-inspected: `data/prepared/` is absent, all three
  preparation scripts and saved baselines are present. Preparation must happen on a
  worker.

## Worker credentials verified 2026-09-18 (third session)

Both worker credentials now exist and have been tested against their real APIs.

**Hetzner.** `HCLOUD_TOKEN` stored at `/opt/data/.secrets/hetzner.token` (0600, in
a 0700 directory). Tested with the token file only — the environment variable was
removed from the test subprocess, which asserted its absence first. A single
read-only `GET /v1/servers` returned **HTTP 200**, so authentication succeeds and
the dedicated project currently contains **0 servers**. No create, modify or
delete call was made.

**GitHub staging.** `FACTORY_GITHUB_TOKEN` stored at
`/opt/data/.secrets/github-staging.token` (0600, same 0700 directory), 93
characters, a fine-grained token. Tested with the file explicitly and
`FACTORY_GITHUB_TOKEN` removed from the environment:

- `earino/dataset-factory-staging` is reachable and **private** (default branch
  `main`).
- Scope is genuinely restricted: the token sees exactly **one** private repository
  across the account — `earino/dataset-factory-staging` — while a probe of
  `earino/dataset-factory` returns **HTTP 404**. It is not the broad classic PAT
  used for coordinator git access, and the coordinator login was left untouched.
- A uniquely named **draft** release was created (`verify-staging-1789728610`),
  a 125-byte test file uploaded, and the server-reported size (125) and digest
  (`sha256:d50a3893513699526aea43828dfc2a633411b310a80f97259e36f2abbf0e07a5`)
  matched the locally computed values. The release stayed unpublished throughout.
- Cleanup succeeded: asset delete 204, release delete 204, subsequent reads of both
  returned 404, zero releases remain, no leftover tag. The draft-releases path
  workers depend on is therefore verified end to end.

`sh scripts/scout-factory doctor --require-worker-credentials` now exits **0** with
both credentials reported ready and an empty error list.

**Worker SSH key registered 2026-09-18 (fourth session).** The existing dedicated
ed25519 pair at `/opt/data/.ssh/scout_worker_ed25519` (0600, directory 0700, no
passphrase) was reused rather than regenerated; its public key derives cleanly from
the private key, so it is suitable for unattended use. Hetzner held no SSH keys
before this, so the public key was registered as **`scout-worker`**:

| Field | Value |
|---|---|
| Name | `scout-worker` |
| ID | `130171155` |
| Fingerprint (MD5) | `9d:80:95:90:cc:4c:c8:65:83:59:9f:8c:2b:d6:ae:30` |
| Verification | read back via `GET /v1/ssh_keys/{id}`; public key matches the local pair |

The read-back fingerprint equals the locally computed MD5 fingerprint, so the
registration is confirmed rather than assumed. `config/local.json` now carries
`ssh_key_name: scout-worker` and `ssh_private_key:
/opt/data/.ssh/scout_worker_ed25519`. Launches stay disabled and the allowance
stays at zero.

Remaining prerequisite for a paid launch: one observed successful **scheduled** cleanup
run. Notification delivery and the secondary on-host sweep are now configured and
verified (eighth session). The allowance is configured (seventh session), the cleanup
secret and variables are configured, and the manual dispatch executes successfully.

**Deletion of an expired server is verified during the smoke sequence, not before it.**
The project has never held a server, so there is nothing for the deleter to act on
until a worker exists. The first smoke job proves collect-then-delete-immediately;
expiry cleanup is a separate later test. See the eighth-session note under "Remaining
prerequisites before the live smoke cycle" and `docs/OPERATIONS.md`.

## Primary expiry cleanup configured 2026-09-18 (fifth session)

Actions secret `HCLOUD_TOKEN` set from `/opt/data/.secrets/hetzner.token` using file
input, so the value never appeared on a command line or in output. Repository
variables set: `FACTORY_PROJECT` = `earino-dataset-factory` (the exact `project`
value in `config/local.json`) and `FACTORY_CLEANUP_ENABLED` = `true`. The local
policy was left untouched: `enabled` false, `cleanup_configured` false,
`monthly_budget_eur` 0, empty `server_types`.

### Manual dispatch - verified executing, not skipped

| Field | Value |
|---|---|
| URL | https://github.com/earino/dataset-factory/actions/runs/35337787612 |
| Event | `workflow_dispatch` |
| Status | completed / success |
| Created (UTC) | 2026-09-18T11:04:09Z |
| Updated (UTC) | 2026-09-18T11:04:19Z |
| Job | `cleanup` - success, started 11:04:13Z |
| Step | "Delete only expired project workers and orphaned job IPs" - success |

The job's own output:

```json
{"deleted_servers": [], "deleted_primary_ips": [], "errors": []}
```

**What that proves, and what it does not.** Proven: the secret and variable wiring,
the workflow's enablement gate (`vars.FACTORY_CLEANUP_ENABLED == 'true'` now
passes), execution on a GitHub runner, and a successful authenticated Hetzner query
issued from GitHub's infrastructure. An empty `errors` list is meaningful here: a
bad or missing token would have surfaced there.

**Not proven: deletion of an actually expired server.** This project has never
contained a server, so the deletion path - non-empty `deleted_servers`, the
ownership re-check before delete, and labeled primary-IP cleanup - is entirely
untested. Verifying it is a smoke-cycle step, not a cleanup-scheduler step.

### Scheduled run - pending at time of writing

No `schedule`-event run appeared between enablement (2026-09-18T11:04Z) and
2026-09-18T11:15Z, despite cron minutes 7, 22, 37 and 52. GitHub documents that the
`schedule` event "can be delayed during periods of high loads of GitHub Actions
workflow runs", that high load includes the start of every hour, and that queued
jobs "may be dropped" under sufficient load
(<https://docs.github.com/en/actions/reference/events-that-trigger-workflows#schedule>).
Scheduled workflows run in UTC on the default branch, and here the workflow file is
already on `main`.

Observed cadence is also much looser than configured. Before enablement the
workflow produced `schedule` runs at 2026-09-17T19:19Z, 22:16Z, 2026-09-18T00:28Z,
05:07Z and 09:53Z - roughly every two to four hours, not every fifteen minutes.
Those runs were correctly `skipped` by the gate.

Scheduler fire time, and therefore the first genuinely scheduled execution, remains
**unverified**. The manual dispatch above stands on its own as execution evidence.
The interval was changed to hourly at minute 17 later the same session; see the
sixth-session section.

### Open item for the operator

With the gate open, each run executes and bills a minimum of one Actions minute. At
the configured 96 runs/day that is roughly 2,880 minutes per month, against GitHub
Free's 2,000 minutes per month for private repositories. Widening the interval to 30
or 60 minutes, or confirming a paid allowance, should be decided before this is
relied on.

## Cleanup cadence changed to hourly 2026-09-18 (sixth session)

Deletion on collection stays the normal path; the scheduled sweep is the backstop.
Because GitHub can delay scheduled runs - and can drop queued jobs under load - the
interval is **not a strict deletion deadline**.

- `.github/workflows/cleanup.yml` now runs `17 * * * *` (hourly at minute 17), with
  `workflow_dispatch` retained for manual runs. Minute 17 is deliberately off the
  hour, which GitHub documents as a high-load period for scheduled workflows.
- `cleanup_grace_minutes` raised from 30 to 60 in `config/worker.example.json`
  (tracked) and `config/local.json` (ignored, so not committed).
- The policy accepts the value: the check is `15 <= cleanup_grace_minutes <= 60`, so
  60 is the maximum permitted. Verified offline that 60 passes and that 90 is
  rejected with "Cleanup grace must be 15-60 minutes"; an offline `worker plan`
  under a stand-in policy completes with `cloud_calls: 0`.
- Measured effect on reservations, which are `ceil((lifetime + grace) / 60)` hours:
  unchanged for 45, 60 and 120-minute lifetimes; the reserved hours rise for
  short jobs (15 and 30-minute lifetimes go 1 -> 2) and for a 90-minute job (2 -> 3).
  The extra hour is therefore charged only where it crosses an hour boundary. It is
  a conservative reservation, not a provider billing cap.
- `docs/OPERATIONS.md` gained a "Sweep cadence and cleanup grace" subsection. It
  records that an empty `deleted_servers` list is the expected sweep result while
  the normal delete-on-collect path is working, and that Scout deletes a worker as
  part of finishing its job rather than waiting for the sweep.
- Launches remain disabled and the allowance unchanged: `enabled` false,
  `cleanup_configured` false, `monthly_budget_eur` 0, empty `server_types`. No cloud
  resource was created or modified.

**No scheduled run has executed yet, and the scheduler is heavily throttled.**

A watcher covered the period from enablement (2026-09-18T11:04Z) to
2026-09-18T12:27Z without observing a single `schedule`-event run - that spans the
configured 11:07/11:22/11:37/11:52/12:07/12:17 fires under both the old 15-minute
and the new hourly cron.

Measured gaps between the scheduled runs that did occur before enablement:

| From | To | Gap |
|---|---|---|
| 2026-09-17T19:19Z | 2026-09-17T22:16Z | 3.0 h |
| 2026-09-17T22:16Z | 2026-09-18T00:28Z | 2.2 h |
| 2026-09-18T00:28Z | 2026-09-18T05:07Z | 4.7 h |
| 2026-09-18T05:07Z | 2026-09-18T09:53Z | 4.8 h |

So this workflow's `schedule` trigger fires every **2 to 5 hours**, not every 15
minutes, and the wait since 09:53Z is still inside that observed range. The
configuration is otherwise verified: the workflow state is `active` on the default
branch, the committed cron reads `17 * * * *`, and `FACTORY_CLEANUP_ENABLED` is
`true`. Nothing here indicates a misconfiguration; it indicates that GitHub's
scheduled runs on this repository are irregular.

**Consequence for the grace estimate.** The 60-minute `cleanup_grace_minutes`
covers one hour of post-expiry billing in the reservation, but the worst observed
gap suggests a leftover worker could survive several hours before a sweep catches
it. Deletion on collection remains the normal path, so this is a cost exposure for
abnormal endings only - but the grace is an estimate, not a bound on the leftover
time, and the on-host secondary sweep gains importance for that reason.

A longer watcher now covers the next scheduled fire; the first genuinely scheduled
execution remains unverified and is reported as pending rather than assumed.

## Compute allowance configured 2026-09-18 (seventh session)

`config/local.json` (ignored, so not committed) now carries the operator's initial
allowance: `monthly_budget_eur` 20, `allowed_locations` `["hel1"]`, `server_types`
`{"cx23": 0.02, "cpx32": 0.08, "cpx42": 0.15}`, `max_workers` 1,
`max_lifetime_minutes` 120, `cleanup_grace_minutes` 60. Values are **maximum
all-in hourly EUR prices including VAT and the primary IPv4**. Working guidance:
CPX32 by default, CX23 for light jobs, CPX42 when a job needs more memory.
`enabled` and `cleanup_configured` remain false, so launches are still impossible.

### Ceilings verified against live prices

Checked through the real launch-time code path (`factory.worker.check_price`) against
the live `/pricing` payload for `hel1`, where the comparison is
`server_gross_hourly + ipv4_gross_hourly > ceiling -> refuse`:

| Type | Ceiling EUR/h | Live server + IPv4 gross/h | Result | Headroom |
|---|---|---|---|---|
| `cx23` | 0.02 | 0.011520 | pass | 0.008480 |
| `cpx32` | 0.08 | 0.069240 | pass | 0.010760 |
| `cpx42` | 0.15 | 0.134640 | pass | 0.015360 |

Primary IPv4 is 0.00096 EUR/h gross. Prices are identical in `fsn1` and `hel1`. A
future price rise larger than the headroom makes `launch` refuse rather than
overspend, which is the intended fail-closed behaviour.

### Offline smoke-job plan

A copy of `examples/smoke/job.json` with `server_type: cpx32` and `location: hel1`
was planned under the proposed allowance (temporary files under `.factory/`, which
is ignored). Result: `reserved_hours` 2, `reservation_eur` **0.16**, `cloud_calls`
0, `enabled` false. Across the allowed types for that 45-minute job: `cx23` 0.04,
`cpx32` 0.16, `cpx42` 0.30.

At the maximum 120-minute lifetime the reservation becomes 3 hours: `cx23` 0.06,
`cpx32` 0.24, `cpx42` 0.45. The EUR 20 allowance therefore admits roughly 333
max-lifetime `cx23` jobs, 83 `cpx32` jobs or 44 `cpx42` jobs.

This is an admission estimate, not a billing cap. Note that a single continuously
running `cpx32` bills about 42.59 EUR/month gross, so the allowance only protects
while jobs stay bounded and are deleted on collection.

### Remaining prerequisites before the live smoke cycle

1. ~~Notification delivery, so a failed or dropped scheduled run is visible.~~
   **Done** - see the eighth-session section. This Telegram chat is the destination.
2. An observed `schedule`-event cleanup run that executes rather than skips.
3. `cleanup_configured: true` and `enabled: true`, set once 1-2 hold.

**Deletion of an actually expired server is a smoke-sequence step, not a
precondition.** This project has never held a server, so the deletion path has
nothing to act on yet. It is exercised later in the sequence: the first smoke job
proves the normal path - provision, Docker, upload, verified collection, then
**immediate deletion** of the server and its job-owned IP - and expiry cleanup gets
its own separate test afterward, when a worker is deliberately allowed to expire and
the sweeper is observed reclaiming it. Requiring expiry evidence before any worker can
be launched would make it unreachable, because the only way to produce an expired
server is to launch one.

## Notification delivery and secondary sweep configured 2026-09-18 (eighth session)

Two of the three remaining prerequisites were closed. Launches stay disabled: the
`schedule`-event cleanup run is still pending, so the smoke cycle did not run.

### Notification delivery - configured and verified delivered

Destination: **this Telegram chat** (platform `telegram`, chat `7600588577`, "Eddie").
A one-off scheduled job was created, fired and its delivery read back from the gateway
log rather than assumed from a success response.

| Field | Value |
|---|---|
| Cron job ID | `1a66d6af21cc` (`scout-telegram-delivery-test`) |
| Schedule | once, `run_at` 2026-09-18T11:48:19Z |
| Fired (UTC) | 2026-09-18T11:48:23.060190Z |
| Job status | `ok` |
| Delivery (UTC) | 2026-09-18T11:48:22.840Z |
| Delivery log line | `Job '1a66d6af21cc': delivered to telegram:7600588577 via live adapter thread=- message_id=9` |
| Delivery error | none (`last_delivery_error`, `last_delivery_unverified`, `last_fire_error` all null) |

The job completed and was retired (`state: completed`, `repeat.completed: 1`), so it
does not recur. Both jobs created in this session captured `origin` from this chat, so
future scheduled reports address it without an explicit target. A failed or dropped
scheduled run is therefore visible here, which was prerequisite 1.

### Secondary no-agent cleanup sweep - was missing, now configured and verified

`docs/OPERATIONS.md` asks for a second, on-host sweep as redundancy for the GitHub
schedule. No such cron job existed before this session.

| Field | Value |
|---|---|
| Cron job ID | `e80975eddd4a` (`scout-secondary-cleanup-sweep`) |
| Schedule | `47 * * * *` (hourly at minute 47, offset from the primary's minute 17) |
| Mode | `no_agent` - no LLM; the scheduler runs the script and delivers stdout verbatim |
| Script | `scout_cleanup_sweep.py` in `~/.hermes/scripts/` (Hermes requires cron scripts there) |
| Real implementation | `scripts/cleanup-sweep-cron.py` in this repo, tracked and versioned |
| Command run | `sh scripts/scout-factory worker sweep --project earino-dataset-factory` |
| Deliver | this chat (`origin`) |
| First run (UTC) | 2026-09-18T11:49:09Z, status `ok`, silent empty output |
| Next fire | 2026-09-18T12:47Z |

The repository copy is the real implementation; the file in `~/.hermes/scripts/` is a
short shim that exists only because Hermes resolves cron scripts relative to
`~/.hermes/scripts/`. Behaviour, both branches exercised directly rather than assumed:

- **Normal path** - an empty sweep prints nothing, so no message is sent. This is the
  watchdog pattern and matters because `deleted_servers` is normally empty while
  delete-on-collect is working. Verified: exit 0, zero output lines.
- **Failure path** - verified by forcing an invalid project value:
  `Scout sweep FAILED (exit 1) for bad project!: factory: IDs must be 1-48 lowercase
  letters, digits, or hyphens`, exit 1. A bad token or unreachable API therefore
  produces one alert line rather than silence.

The script's exit status is the sweep's own, so a failure also shows in cron history.

### GitHub scheduled cleanup run - still pending, launches stay disabled

As of 2026-09-18T12:18Z no `schedule`-event run has appeared since the gate was opened
at 11:04Z. The most recent scheduled run remains 09:53:53Z, which was correctly
`skipped`. **Two consecutive hourly slots have now been missed** - 11:17Z and 12:17Z -
under a `17 * * * *` cron that was already on `main` before either was due. A polling
watcher checked `gh run list --event schedule` every 20 seconds from 11:49Z to 12:19Z
and found nothing. This matches the fifth-session observation that this repository's
scheduled runs are sparse (roughly every two to four hours, against a configured
fifteen-minute interval at the time).

That is now the single outstanding blocker, and it is worth being precise about what it
means: the workflow is correct and its manual dispatch executes, but **the scheduler is
not delivering on its configured cadence for this repository**, so the primary sweeper
cannot yet be relied on as the backstop it is meant to be. The secondary on-host sweep
added this session is hourly and independent of GitHub, which is exactly the redundancy
that gap calls for.

Consequence, per instruction: **`enabled` and `cleanup_configured` stay false and no
paid launch was made.** No CPX32/hel1 smoke cycle, therefore no artifact links, no
reservation, no cost and no deletion to report. The manual `workflow_dispatch` from
the fifth session remains the only evidence that the cleanup step executes.

## Still unverified or unimplemented

Local tests use fake providers. **No live Hetzner/GitHub worker cycle has been run.**
Boot, SSH, Docker, uploads, recovery, costs and scheduled deletion remain unverified.

The worker policy is **configured but disabled**: an allowance of EUR 20,
`allowed_locations ["hel1"]`, the three priced server types and the SSH key are set in
`config/local.json`, while `enabled` and `cleanup_configured` remain false, which is
what keeps paid launches impossible. No cloud resource exists.

The primary cleanup workflow is no longer skipped - `FACTORY_CLEANUP_ENABLED`,
`FACTORY_PROJECT` and the `HCLOUD_TOKEN` Actions secret are set and a manual dispatch
executed successfully (fifth session). What is still missing is an observed
`schedule`-event run.

The benchmark adapter (`factory/bench.py` coordination, `workers/benchmark.py`
execution), qualification tools, public exporter and website are not implemented.
`../harness_benchmark` is unmodified.

## Next actions for Scout

1. **Launch worker job `austin-001`** as soon as paid launches are enabled (the only
   remaining gate is an observed scheduled GitHub cleanup run). It is planned and ready:
   `worker plan candidates/austin-911-response/source/job.json`. Then collect the private
   staging release, verify checksums, delete the worker immediately, and report the measured
   base rates, the full-sample baseline AUC and the headroom.
2. Continue shortlist work that needs no credentials. Maryland's stale-series concern is
   resolved and NOAA's exceedance base rates are measured (1.37% pooled); Melbourne's
   licence is the open item, and both remaining candidates need their target thresholds
   chosen before a construction script can be written.
3. Operator: none - allowance, locations, server types, SSH key and both worker tokens
   are in place. The only outstanding gate is GitHub's scheduler.
4. Once a `schedule`-event run is observed executing: set `cleanup_configured: true`
   and `enabled: true`, run the live smoke cycle, verify deletion by letting the worker
   expire, then disable paid launches again and move on to recovery and expiry tests.

## Inputs still needed from the operator

Nothing blocking on the worker side. Both worker tokens and the worker SSH key are supplied and
verified, the allowance and allowed locations/types are configured, and notification delivery is
working. First release date, reviewer, public dataset namespace and website hosting can
wait until the first candidate is approved.

**Blocking the research routine: the model-spend allowance.** Asked 2026-09-18 and unanswered.
Until it arrives, `config/research-budget.json` keeps `allowance_usd: null` and the gate wakes
no research session - fail-closed, by design. Four questions, answerable in one line:

1. **Monthly allowance**, measured as Hermes-estimated USD (a bounded session measures
   0.07-0.37 USD, so 3/week is roughly 1-4 USD/month). Suggested: 5 USD/month.
2. **Reset period**: 1st of the month 00:00 UTC, a different day, weekly, or a rolling window.
3. **Portal reconciliation**: the NousCloud quota and reset period are not visible from this
   instance. Estimates-only reporting, or will the operator relay the portal figure?
4. **Enable the schedule**: Mon/Wed/Fri 08:00 UTC, 3 sessions/week, <= 45 min and <= 600k tokens
   each, stopping at 95% of the allowance.

Also open, from the publication milestone: the **licence choice** for the published code and for
the three benchmark runner files shipped in `austin-911-response` (that upstream project carries
no licence), and **public visibility**, withheld as instructed.

## Construction script written and worker job prepared (2026-09-18, ninth session)

`candidates/austin-911-response/source/build.py`, stdlib only, built for a worker. The
source directory holds `build.py` and `job.json` and nothing else; the candidate's notes
and record stay outside it, as required.

**Threshold is frozen from the training window by rule, not by hand.** `build.py`
binary-searches the Socrata aggregate - COUNT queries only, no rows fetched - until
`P(response_time > T)` in the training window is just at or above a target rate of 0.40,
then snaps T to a whole minute and re-measures. Run against the live API it selects
**T = 1200 s (20 minutes)** with a training rate of **0.4038** over **572,180 rows**. That
row count is exactly the sum of the measured 2023 (286,145) and 2024 (286,035) counts, so
the split boundaries and the counts agree.

Ten probes were recorded in the manifest, so the choice is auditable rather than asserted.

**Splits** are temporal by `response_datetime`: train `< 2025-01-01`, eval `2025`,
holdout `>= 2026-01-01`. Rows are paged in `incident_number` order (unique, so paging
cannot skip rows that share a timestamp) and each file gets a SHA-256 checksum, byte
count, row count and positive rate into `manifest.json`. `summary.json` is written for the
worker's compact-report contract.

**A bounded exercise has been run locally** (`.factory/austin-smoke`, `--limit 400`), so
the script is known to execute end to end: threshold freeze, three splits with checksums,
and the baseline. Its per-split rates are not meaningful - the limit takes the first 400
rows of each split by incident number, which is roughly January only - but the pipeline is
proven. The single-feature baseline scored **AUC 0.5999** on that sample; the real figure
must come from the full extract.

**Worker job `austin-001` is prepared and planned, not launched.** `worker plan` reports
`reservation_eur 0.24`, `reserved_hours 3`, `source_bytes 40960`, `source_sha256
ee37eec...`, `cloud_calls 0`, `enabled false`. It targets `cpx32` in `hel1`, a 45-minute
timeout inside a 90-minute lifetime, `max_artifact_mb 400` (the three CSVs are expected
near 136 MB in total at roughly 130 bytes per row). Paid launches remain disabled, so it
waits.

**Tests**: `tests/test_austin_build.py` adds 20 offline tests, including the structural
guarantees that matter here - no feature may overlap the post-hoc exclusions,
`response_time` / `priority_level` / `mental_health_flag` may not be features, the split
windows must be disjoint, and the job directory must satisfy the worker's own
`source_bundle` rules (no symlinks, no hidden files, only allowed suffixes, under 2 MiB).
Test count is now **59**, all passing.

## Operations correction: smoke order (2026-09-18)

`docs/OPERATIONS.md` and this file now state that the **first smoke cycle proves the normal
path - provision, Docker, upload, verified collection, then immediate deletion of the
server and its job-owned IP**. Expiry cleanup is a separate later test with its own job.
The earlier wording allowed the sequence to read as if an expired-server deletion had to be
observed before any worker could launch, which is unreachable: the only way to create an
expired worker is to launch one.

## Builder review fixes re-implemented, and the qualification gate added (tenth session)

`main` was pulled through `0c8eb7a`. The builder's fix (`37f36c2`) had been reverted by
`0c8eb7a`, so the defects it described are re-diagnosed, fixed and validated here. All three
were reproduced before anything was changed.

### 1. Austin's CSVs contained `response_time`, which determines `late`

Reproduced by reading the emitted file rather than the declared lists: the header of
`.factory/austin-smoke/train.csv` was
`incident_number,response_datetime,response_time,...`. The column was absent from `FEATURES`
and present in `CARRY_COLUMNS`, and every declared list still looked correct.

`response_time` is now `LABEL_SOURCE`, is **not** in `CARRY_COLUMNS`, is listed in
`EXCLUDED_POST_HOC`, and is recorded in the manifest as `label_source_column` for
provenance while being excluded from `shipped_columns`. It is still selected from the API -
without it the label cannot be derived - and never written.

### 2. A host-timezone-dependent helper

`parse_iso` was dead code, used only by its own test, and did
`datetime.fromisoformat(value).astimezone(timezone.utc)` on a timezone-free string, which
interprets it in the **host** timezone. Reproduced: the test passes under `TZ=UTC` and
`TZ=America/Los_Angeles` and fails under `TZ=Asia/Tokyo`, where
`2025-01-01T00:00:38.000` becomes `2024-12-31T15:00:38Z` and the year assertion fails.

Removed, with a test asserting it stays removed and that the construction contains no
`fromisoformat`, `astimezone` or `datetime.now()`. The construction itself is timezone-free:
splits are Socrata predicates on literal timestamps and the source strings are written
through unchanged.

### 3. Test imports created caches inside the worker source directory

Reproduced by running the suite with bytecode writing enabled (this host sets
`PYTHONDONTWRITEBYTECODE=1`, which hid it): the test loader's `exec_module` created
`candidates/austin-911-response/source/__pycache__`, which then made
`test_job_directory_contains_only_bundleable_source` fail and made the worker refuse the
job outright - `factory: Job directory must contain only explicit source files, no hidden
files/caches`. Both test modules now load their subject with `exec(compile(...))`, and
`tests/test_repo_hygiene.py` guards every candidate job directory against caches, symlinks,
disallowed suffixes and the 2 MiB bundle cap.

### Test coverage added

- `tests/test_austin_build.py` rewritten: the writer is executed and the **actual generated
  files** are inspected - runner layout, exact column set, the label source absent from every
  header, labels at 1200 s and 1201 s, checksums that match, and a rebuild that clears stale
  output.
- A runner-contract class encodes how `../harness_benchmark` really reads the extract
  (`feature_cols = every column except id_columns and the target`; `validate.py` drops only
  the target) and asserts that the runner's own feature selection exposes no answer source
  and that no shipped column reconstructs the label.
- `tests/test_qualification_gate.py` runs the gate against those generated files, and
  replays the original bug by re-shipping `response_time` to prove the gate rejects it.
- **89 tests pass** with bytecode writing **enabled** and under `TZ=Asia/Tokyo`, `TZ=UTC`
  and `TZ=America/Los_Angeles`.

### The dataset-qualification gate

`skills/dataset-qualification/` is versioned in this repository and symlinked into Hermes at
`~/.hermes/skills/research/dataset-qualification`, so it also loads from the skill list. It
gates five things across 25 named checks: leakage, prediction timing, units and reference
frames, temporal split capacity, and runner compatibility. Run it with

```bash
python3 skills/dataset-qualification/scripts/qualify_dataset.py <dataset-dir>
python3 skills/dataset-qualification/scripts/qualify_dataset.py --selftest
```

**Demonstrated:** the broken fixture is rejected with 9 named failures - including
`leakage.answer_source_absent`, `leakage.no_single_column_determines_the_target`,
`timing.no_post_hoc_feature`, `units.known_event_fixture_recorded`,
`splits.windows_distinct` and `runner.layout` - and the corrected fixture passes all 24
checks. `--selftest` asserts both verdicts, so the demonstration is reproducible rather
than a pasted transcript. Austin is used as the leakage and runner worked example; NOAA as
the units/datums worked example, including the requirement for a known-event fixture.

`AGENTS.md` gained a short section telling a session when to invoke the gate.
`open-data-source-vetting` (the Hermes-side skill) gained a handoff paragraph pointing at
it when construction completes.

**Fresh-session verification.** A brand-new CLI session (`20260918_130358_725a40`, zero
prior history, no access to this conversation) was asked what to check before reporting an
AUC from a directory of `public/train.csv`, `public/eval.csv`, `private/holdout.csv` and
`meta.json`. It discovered the skill from the skill list, loaded it with `skill_view`,
named it, gave the exact command, ran `--selftest` itself, and volunteered the
necessary-but-not-sufficient caveat. Evidence: `agent.log` records the `skill_view` call
against that session id. A cosmetic `Skill security warning: skill file is outside the
trusted skills directory` is logged on load, because the Hermes-visible path is a symlink
whose target resolves outside `~/.hermes/skills`; the link is deliberate, since a second
real copy would be able to diverge. `tests/test_repo_hygiene.py` asserts the link resolves
to this repository's copy.

### One self-inflicted incident, recorded

While clearing bytecode caches, an over-broad `rm -rf candidates tests ...` deleted the
`candidates/` and `tests/` directories. Everything tracked was restored with
`git checkout -- candidates tests`; two uncommitted files (`source/build.py` and
`tests/test_austin_build.py`) were re-written. No measured evidence was lost, because every
result of the prior session was already committed. The lesson is recorded in the report:
scope deletion commands to exact paths.

## Worker qualification, gate hardening and safe cleanup (eleventh session)

Five follow-ups from the builder review, all implemented and verified here.

### 1. The skills directory is registered with Hermes properly

The symlink into `~/.hermes/skills` is **gone**. Hermes's supported mechanism,
`skills.external_dirs`, is now configured:

```bash
hermes config set skills.external_dirs dataset-factory/skills
```

Entries are resolved relative to `HERMES_HOME`, and Hermes treats the result as a trusted
directory, so the `skill file is outside the trusted skills directory` warning no longer
appears. Verified in `agent.log`: the last such warning is timestamped 13:11, from the symlink
era; the skill loads cleanly afterwards.

**Fresh-session verification.** A CLI session started from `/tmp` - outside the repository, so
project-local trust could not be responsible - discovered and loaded the skill unprompted:
`tool skill_view completed`, session `20260918_132856_3a3f34`, and it reported the correct
name, version 1.1.0, the self-test command and the `--accept` command. A scheduled cron
session (`scout-skill-discovery-check-2`, `492d8a95e56e`) was also fired as the
scheduled-surface check.

### 2. Qualification runs on workers, and gates scoring

`candidates/austin-911-response/source/run.sh` builds the extract and then qualifies the exact
artifact it just wrote, exiting non-zero when the gate fails. `scripts/assemble-job.py` is the
single assembly point: it copies `build.py`, `run.sh` and the repository's `qualify_dataset.py`
into an ignored staging directory, generates `job.json`, and validates the result against the
worker's own bundle rules. The assembled bundle is 58,372 bytes and plans offline at
`reservation_eur 0.24`, `cloud_calls 0`, `enabled false`.

**A failed qualification still preserves diagnostics.** The gate report, its rendered output
and the extract are written under `/output`, which the worker uploads even on a non-zero exit;
only the compact report, the rendered checks and the manifest come back to Scout.

**Scoring and acceptance now require a passing report for the exact artifact version.** The
gate records the SHA-256 of every shipped file plus an `artifact_version` digest over them, and
`--accept` re-verifies both. Verified end to end:

```
accept /tmp/q.json fixtures/corrected   -> ACCEPTED ... matches the qualified artifact 7a7a91a508b0a298
append one byte to public/eval.csv      -> ACCEPT FAILED: public/eval.csv has changed
                                           since qualification (e09eb53aeca7 != ffded9dac29e)
```

It also refuses a failed report and a report written by a different gate version. `docs/OPERATIONS.md`
documents the sequence; the run itself is still gated on the scheduled GitHub cleanup run.

### 3. Regression cases for the two false passes

Both are now fixtures with named expectations, and both are replayed against real generated
output rather than only against the fixtures:

- `fixtures/broken-overlap/` - **evaluation rows inside the training period**, with every
  declaration clean and disjoint. Caught by `splits.actual_ranges_disjoint` and
  `splits.rows_within_declared_windows`, both computed from the row timestamps.
- `fixtures/broken-single-class/` - **an evaluation split with no negatives**. Caught by
  `splits.eval_and_holdout_have_both_classes`.

The gate now recomputes split windows, boundaries, positive counts and clustered event counts
from the rows and refuses when they disagree with `quality.json`: `time_column` and
machine-readable `split_windows` are required, so an undeclared split fails rather than passing
silently. Identity overlap between splits is checked too.

### 4. The categorical scan is linear

`group_rates()` builds the per-level table once and scores the rows in a second pass; the old
shape re-summed each row's entire level (`rows x group-size`). Splits are also read
**column-wise** rather than as a list of dictionaries - a dict per row is roughly 1 KiB, which
is hundreds of megabytes on a 1,050,000-row extract. `tests/test_qualification_gate.py`
asserts the level table is built exactly once per column and runs a 200,000-row column to
prove the old quadratic path is gone.

### 5. Destructive cleanup, addressed in procedure and in code

`build.py` no longer calls `shutil.rmtree` on `--out`. `prepare_output()` refuses a path that
is protected, contains a `.git`, is a file, or is a non-empty directory without the
`.dataset-factory-extract` ownership marker the script writes; an owned directory is cleared
entry by entry through an explicit list, leaving anything else in place. Tests cover each
refusal, including that an unrelated file inside an owned directory survives. `AGENTS.md`
gained a short "Deleting things" rule, and the skill documents the destructive default as a
pitfall.

### Checks

**115 tests pass** with bytecode writing enabled and under `TZ=Asia/Tokyo` and `TZ=UTC`. The
gate's self-test rejects all three broken fixtures with their expected named checks and accepts
the corrected one. `tests/test_worker_qualification_job.py` assembles the job bundle, verifies
it against `factory.worker.source_bundle`, and runs `worker plan`.

**Still blocked, and the evidence is now much stronger.** No `schedule`-event GitHub cleanup
run has fired at all. A watcher polled `gh run list --event schedule` every 20 seconds from
12:20Z to 14:04Z and found nothing; combined with the earlier watcher, that covers
**11:04Z to 14:04Z with no fire** - eleven consecutive hourly slots under the `17 * * * *`
cron applied at 11:26Z, and 4.2 hours since the last actual fire at 09:53Z. That already
exceeds every gap observed before the gate was opened (3.0, 2.2, 4.7, 4.8 hours), so this is
no longer explained by the documented 2-5 hour irregularity alone.

Configuration is verified correct and unchanged: the workflow is `active` on the default
branch, the committed cron reads `17 * * * *`, `FACTORY_CLEANUP_ENABLED` is `true`, and the
manual dispatch still executes. The gap is in GitHub's scheduled trigger for this repository,
not in the workflow.

Consequence: the worker job is assembled, planned and tested but **not launched**, and no
Austin extract exists. The on-host secondary sweep is unaffected and healthy - it ran at
12:47:01Z with status `ok` and fires hourly - which is exactly the redundancy this gap calls
for. If the scheduled trigger cannot be made to fire, the operator should decide whether the
on-host sweep is sufficient to enable launches, since it performs the same sweep command.

### CI failures on `a182ff2`, diagnosed and fixed (twelfth session)

Both failures shared one cause: tests depending on the hosted instance's private
configuration, which a clean checkout does not have.

1. `test_refuses_a_protected_path` asserted `/opt/data` was refused. That path exists here and
   not on CI, and `prepare_output` only consulted the protected list when the path existed, so
   nothing was raised. **The protected-path check now runs before the existence check** - a
   protected path is refused whether or not it exists, which is the correct behaviour on its
   own terms and no longer host-dependent. The test covers every entry in `FORBIDDEN_OUT`.
2. `test_plan_is_offline_and_reports_the_reservation` ran `worker plan` against
   `config/local.json`, which is gitignored, so a clean checkout has no policy at all. Adds
   `tests/policy.ci.json` - a committed policy of the same shape and values - and runs the plan
   against it. A companion test compares the committed policy with the hosted one whenever the
   hosted one is present, so the two cannot drift unnoticed on the coordinator.

**Verified in a clean copy** with `config/local.json` removed: 117 tests pass with bytecode
writing enabled under `TZ=UTC` and `TZ=Asia/Tokyo`, with the 2 host-only checks skipped, and
`python3 -m factory doctor` exits 0 - both of CI's steps.

**Completion procedure added to `AGENTS.md`**, deliberately short rather than a new skill:
after pushing, check CI for that exact commit and fix failures before reporting the change
complete; say so explicitly when CI is pending or blocked; verify suite changes in a clean
clone. The first draft of that instruction told the next session to use
`gh run list --commit <sha>`, which silently returns an empty list even when a run exists - it
reported nothing for a green commit. Corrected to the API form
(`gh api "repos/<owner>/<repo>/actions/runs?head_sha=..."`), with the broken flag named so it
is not reached for again.

CI is green for `d1104f4` and `5848c7e` (the check job's `unittest` and `factory doctor` steps
both succeeded).

### Limited cleanup exception for the smoke test (2026-09-18)

The operator authorized one supervised infrastructure smoke test, and for that test only the
verified on-host sweep satisfies the cleanup prerequisite; GitHub scheduled execution remains
**unverified** and is recorded as an open item rather than a satisfied one. The exception and
its limits are written into `docs/OPERATIONS.md` so a later session cannot read it as a
standing relaxation. Launches are enabled for the smoke cycle and disabled again immediately
after it, leaving cleanup active.

### Infrastructure smoke cycle: completed 2026-09-18

The first paid worker cycle ran under the operator's authorization and the documented
exception. It verifies infrastructure, not task quality.

| step | result |
|---|---|
| job / server / IP | `infra-smoke-001` / `166466571` / `150355427` (`46.62.136.146`) |
| provisioned | 14:55:32Z, CPX32 in `hel1`, `lifetime_minutes` 45, expires 15:40:31Z |
| Docker executed | yes - `python@sha256:9d2e5553...c00285`, `elapsed_seconds` 7.5, `oom_killed` false, exit 0 |
| uploaded | release `job-infra-smoke-001` (id 391560852, draft) in `earino/dataset-factory-staging`, 5 assets |
| collection verified | every asset size and digest matched the worker manifest |
| destroyed | 14:59:41Z - server and job-owned IP deleted |
| provider-confirmed | `scripts/provider-inventory.py`: **0 servers, 0 primary IPs in the whole account** |
| reservation | EUR 0.16 (2 reserved hours at the 0.08 ceiling) |
| estimated cost | about EUR 0.07 - the machine lived 4.2 minutes, and the provider bills server-hours |

Timeline: launched 14:55:31Z, collected 14:59:07Z, destroyed 14:59:41Z. The account held zero
servers and zero IPs before the launch, so nothing else could account for either resource, and
the sweep afterwards returned `deleted_servers: []` with no errors - there was nothing left to
clean.

Launches are **disabled again** (`enabled: false`) and cleanup stays **active**
(`cleanup_configured: true`); a further launch is refused with `Worker launch disabled;
configure policy and independent cleanup first`. The GitHub `schedule` trigger remains
unverified, and the full Austin build and unattended operation are subsequent steps.

`scripts/provider-inventory.py` is new and tracked: it reads the token from the `_FILE` path
and queries the provider directly, so a before/after comparison does not rest on this
project's own bookkeeping claiming success. The recovery and failed-job paths were then
exercised on 2026-09-18; expiry cleanup is covered below.

### GitHub scheduled cleanup: observed executing (2026-09-18)

Run 35368993679, event `schedule`, created 16:31:37Z, commit `3ba6988`, conclusion `success`.
The step `Delete only expired project workers and orphaned job IPs` ran
`python3 -m factory worker sweep --project "$FACTORY_PROJECT"` at 16:31:46Z and printed
`deleted_servers: []`, `deleted_primary_ips: []` - correct, because the smoke worker had been
destroyed at 14:59. So the scheduled trigger **executes**; it has not yet been observed
deleting, because there was nothing expired at the time.

Cadence measured across six fires: gaps of 2.96, 2.19, 4.65, 4.77 and 6.63 hours (mean 4.24 h,
max 6.63 h) against a `17 * * * *` cron. **The GitHub trigger is not an hourly deadline.** The
hourly bound is the on-host sweep's; GitHub's contribution is durability across this instance
being gone. Both are recorded in `docs/OPERATIONS.md` in those terms, and both schedules stay
active.

### Cleanup path tests: expiry, recovery, failed job (2026-09-18)

Each ran one worker at a time, with deletion confirmed against the provider rather than our
ledger, and the acting cleanup path recorded.

**Failed job** - `infra-smoke-fail-01`, server 166481719. The container exited 7 on purpose.
The executor recorded `status: failed`, `exit_code: 7`, `uploaded: true` and preserved the
diagnostics: `output/partial.txt` (the line written before the failure) and `container.log`
(both stdout and stderr) were recovered from draft release 391674310 with digests matching the
manifest. **Path: normal `destroy` after collection** - a failed job is still collectable, so
its evidence survives. Deleted 17:58:28Z; provider then showed 0 servers, 0 IPs.

**Upload recovery** (not "session recovery" - this exercises the artifact transfer, not the
coordinator's session) - `infra-smoke-recov-01`, server 166481920. The lost-transfer condition
was reproduced honestly by deleting the staging release (391676527) after a successful run:
`collect` then failed with `HTTP 404` and exit 1. `worker retry-upload` re-dispatched the upload
unit and `collect` succeeded against a **new** release (391678046) with `exit_code 0`,
`elapsed_seconds 7.2` and `image_id` identical to the first run - the data job was reused, not
rerun, which is the documented guarantee. **Path: normal `destroy` after collection.** Deleted
18:03:28Z; provider then showed 0 servers, 0 IPs.

A first attempt to launch the expiry job was refused by validation
(`Lifetime must include at least 15 minutes for boot/upload and fit policy`) because
`timeout_minutes 5` with `lifetime_minutes 16` violates `timeout + 15 <= lifetime`. Nothing was
provisioned - the refusal happens before any cloud call - and the provider was checked to
confirm no server had been created. Lifetime raised to 20.

**Expiry cleanup** - `infra-smoke-expiry-01`, server 166482592, launched 18:05:00Z with
`lifetime_minutes 20` and deliberately **never collected**, so `destroy` refused it
(`Collect and verify artifacts before normal deletion; expired jobs are cleaned by sweep`) and
the expiry path was the only thing that could remove it.

| measurement | value |
|---|---|
| expired | 18:25:00Z |
| gone from the provider | 18:47:12Z (watcher poll) |
| **deletion lag past expiry** | **22.2 minutes** |
| acting sweeper | **on-host Hermes cron** `e80975eddd4a`, scheduled hourly |
| its own record | `Scout sweep for earino-dataset-factory: {"deleted_primary_ips": [], "deleted_servers": [166482592], "errors": []}` at 18:47:17Z |
| GitHub scheduled run in that window | none - newest remains 16:31:37Z |
| provider after | 0 servers, 0 primary IPs |

The job-owned IP went with the server; the sweep's IP pass had nothing left to remove, and the
provider confirms zero IPs. The ledger was then closed by `worker status`: `status: deleted`,
`deleted_at 18:50:29Z`, reservation `EUR 0.16` retained. **Path: on-host scheduled sweep, not
manual `destroy`.**

### Session recovery: a fresh session reconciled the worker (2026-09-18)

Separate from upload recovery: this tests that a **new coordinator session** can pick up
persisted state and reconcile a live worker without any of this conversation.

Fresh Hermes CLI session `20260918_183816_f11a63`, started from `/tmp` (outside the repo) with
no prior context, told to prefer the ledger and `docs/OPERATIONS.md` over `STATE.md`:

- found `jobs/infra-smoke-expiry-01.json` on its own and read the entry;
- ran exactly `sh scripts/scout-factory worker status infra-smoke-expiry-01` from the repo root,
  exit 0, and reported the output verbatim;
- concluded the ledger still read `status: running`, `server_id 166482592`, `ipv4 46.62.136.146`,
  reservation EUR 0.16, with `deleted_at` absent - verified here by diffing the record before and
  after, which was content-identical;
- inferred from `reconcile` that the provider still held exactly one labelled match, and said so
  as an inference rather than as output it had seen.

33 messages, 19 tool calls, 2m 9s, zero launches or other paid operations. The instruction not to
launch anything was honoured: no replacement worker was created and both cleanup schedules were
left untouched. **Path verified: coordinator-session recovery via the persisted ledger.**

### Austin: full-data extract built and qualified (2026-09-18)

`austin-003` ran the complete construction and qualification on a worker and **passed**.

| | |
|---|---|
| job / server | `austin-003` / `166489302` (CPX32, `hel1`) |
| reservation | EUR 0.24 (3 reserved hours); machine lived 5.9 minutes |
| elapsed | 353.7 s build + qualify, exit 0 |
| qualification | **PASSED - 33 checks, 0 failed**, gate 1.3.0, over the full artifact |
| artifact version | `e4598317e406984fa590aacc5e7aff675867578c51ae1a84ebf6279bc42c3328` |
| staging | draft release `job-austin-003` (id 391742263) in `earino/dataset-factory-staging` |
| acceptance | `scripts/verify-staged-report.py 391742263` - the report's digests equal the uploaded bytes for all five components |
| destroyed | 19:46:23Z; provider then 0 servers, 0 IPs; sweep clean |

**Real split counts, measured on the full data** (threshold T = 1200 s, frozen from the training
window):

| split | rows | positives | positive rate |
|---|---|---|---|
| train (< 2025-01-01) | 572,180 | 231,025 | 0.403763 |
| eval (2025) | 285,665 | 109,860 | 0.384576 |
| holdout (>= 2026-01-01) | 191,791 | 72,450 | 0.377755 |
| **total** | **1,049,636** | | |

The row counts equal the source's per-year counts exactly, so paging lost and duplicated
nothing. The gate's own evidence on the full rows: no `incident_number` appears in more than
one split; 24 repeated-identifier rows within splits, at the declared 24; 4 of 24 repeated
identifiers carry more than one label, recorded as a source property because the descriptor
makes no entity-key claim.

**Baseline: AUC 0.627031** on the eval split from `initial_problem_category` alone, shipped
with the extract. This is a measured floor, not a headline result - no model comparison has
been run, and the gate's passing report is what licenses quoting it at all.

Three runs were needed. `austin-001` failed a conflated entity check; `austin-002` failed an
entity-key claim the source does not make; each failure was diagnosed from the rows and fixed
in the gate or the declaration, and neither was a data defect. The extract bytes for
`austin-002` and `austin-003` are identical, which confirms the last round of changes was
gate-and-declaration only.

Not done, and not implied by any of the above: no model comparison, no headroom figure, and
**nothing published** - a public release still requires human review.

### Publication package prepared for review (2026-09-18)

`release/austin-911-response/` holds the dataset card, data dictionary, licence and attribution
notes, reproduction instructions, the release manifest and checksums, and the release-notes
draft - written to the checklist in `templates/dataset/README.md`. **Nothing has been
published**; no public repository or release exists.

Generated from recorded evidence rather than retyped: `scripts/release-manifest.py` builds
`MANIFEST.json` and `SHA256SUMS` from the accepted artifact's hashes and the candidate record, so
the manifest cannot drift from what was measured.

**Three decisions a reviewer needs to make:**

1. **The construction code licence.** The source data is Public Domain, which says nothing about
   the code that derives it. `LICENSE.md` flags this as an open choice (MIT / Apache-2.0 / CC0 /
   reproduction instructions only) rather than defaulting silently, because it is a legal
   decision.
2. **Shipping the labelled holdout publicly.** The project template permits it; it must simply
   stay outside an evaluated agent's workspace. Alternative: ship the holdout only on request.
3. **The repository name.** The plan assumes `earino/austin-911-response`.

**Publication is not automated past the plan.** `scripts/publish-dataset.py` prints exactly what
would happen and does nothing else; `--stream-test` verifies that all five artifact files resolve
to concrete staged assets (through the worker's own `manifest.json`, not assumed ordering). The
**upload step is deliberately not implemented**: moving ~131 MB from a private release to a
public one needs either a machine that can hold those bytes or a worker-side publish path, and
shipping an unverified pipe that claims to publish would be worse than shipping none. The five
steps are written out in the module docs for when the decision is made.

Two facts learned the hard way and recorded in the tooling: `gh release download` cannot fetch
**draft** release assets, and `releases/tags/<tag>` returns 404 for a draft even though the
release exists - so the staging release is referenced by its **id**.

### Baseline through the runner's contract: eval AUC 0.7691 (2026-09-18)

`austin-baseline-002` ran the harness benchmark's own training and validation contract against
the **verified accepted artifact**. Contract only - no coding agent, no harness comparison.

| | |
|---|---|
| job / server | `austin-baseline-002` / `166494335` (CPX32, `hel1`) |
| reservation | EUR 0.24; elapsed 386.0 s; exit 0 |
| eval AUC, `train.py` | **0.7691** |
| eval AUC, `validate.py` via `predict_proba` | **0.7691** (agrees) |
| `[validate] CONTRACT OK` | yes |
| train / score time | 2.6 s / 0.3 s |
| runner files | `train.py`, `validate.py`, `validate.sh` bundled verbatim from the read-only clone; hashes in the report match the expected ones - `unmodified: true` |
| dependencies | Python 3.13.15, pandas 2.3.3, numpy 2.5.3, xgboost 3.4.1, scikit-learn 1.9.1 |
| destroyed | 21:19:26Z; provider 0 servers / 0 IPs; sweep clean |

The job **rebuilds** the artifact rather than downloading it (the worker has no credential for
the private staging release, and bulk data is not meant to travel), then refuses to measure
anything unless all five files match the accepted hashes - so the number is attached to the
qualified artifact and not to a near-copy.

`austin-baseline-001` failed that verification and was right to: all three split files matched
byte-for-byte, but `meta.json` differed because it embeds `built_at_utc`. Fixed by making the
timestamp an input (`build.py --built-at`), which also makes published artifacts reproducible -
a claim `REPRODUCE.md` makes and now supports. Regression test added.

For context, not comparison: the extract's own single-feature baseline is 0.627031 on the same
eval split, so the runner's model adds ~0.14 AUC over `initial_problem_category` alone. **No
agent or harness result exists**, and 0.7691 is a floor for one rather than a finding about one.

### Publication package assembled in its own private repository (2026-09-18)

`earino/austin-911-response` now exists as a **private** repository with the finished package, and
`v2026.09` carries the dataset as release assets. Nothing is public.

The package carries the construction script, the qualification gate, the materialize and
clock-offset tools, the benchmark's own runner files copied verbatim with provenance, a download
tool that restores the runner layout from flat asset names, `measurements.json` holding every
quoted number with the command that produced it, and the dataset card, data dictionary, licence
notes and reproduction instructions. `MANIFEST.json` records hashes for **every published file**,
so a consumer can check what they cloned, not just what they downloaded.

**The transport is new infrastructure.** A worker job with a `transfer` spec moves artifacts
between releases: each asset is downloaded, verified against its recorded SHA-256, re-uploaded,
verified again from the server's own digest, then deleted, so peak disk on the worker is one
asset rather than the dataset. A `fetch` spec downloads published assets into a read-only mount
at `/data`, which is how a container can measure the *released* bytes without ever holding a
credential. Both run host-side; the container is never given a token.

**A scope decision, recorded rather than buried.** The staging token is scoped to
`earino/dataset-factory-staging` alone - it returns 404 on every other repository - so a transfer
into the dataset repository needs its own credential, now at
`/opt/data/.secrets/github-publish.token` (0600, from the account's `repo`-scoped token). Source
reads still use the staging token and **only the target write uses the broader one**. This widens
what a worker can reach for the duration of a transfer job, so it is stated here and in
`docs/OPERATIONS.md`; a fine-grained token limited to `earino/austin-911-response` would be
narrower and is the recommended replacement.

**Two defects found and fixed on the way**, both by running the real thing rather than reasoning
about it:

1. Writing to a repository the staging token cannot see surfaced as `UploadError`, which
   `execute()` did not catch - so the worker died with `started` touched and no `execution.json`,
   and the job looked like it was still running. The credential requirement is now checked at
   *plan* time, before provisioning, and `UploadError` is caught so a failure still produces a
   report.
2. That stuck worker also exercised the interrupted-job guard for real: `retry-upload` produced
   `failure: "executor-interrupted; job was not rerun"` and the transfer was **not** silently
   re-run.

### Publication package finished, transferred and verified (2026-09-18)

`earino/austin-911-response` (private) carries the finished package; tag **`v2026.09`** and
`main` both point at `acf683ebf7ff14230bf7b7242cad2050980761f4`, and `v2026.09` holds the dataset
as five release assets. Nothing is public.

**What the package contains now:** the construction script, the qualification gate, the
materialize and clock-offset tools, the benchmark's own runner files copied verbatim with
provenance, `get_dataset.py` (restores the runner layout from flat asset names, since GitHub
rejects `/` in asset names), a 19-file document set, `measurements.json` holding every quoted
number with the command that produced it, and `VERIFICATION.md`. `MANIFEST.json` records the
SHA-256 of **every published file**, so a clone can be checked file by file.

**Transport:** `austin-publish-003` moved all five assets from private staging into the dataset
release - 131,429,379 bytes, `failures: []` - verifying each on arrival and again from the
server's own digest after upload, deleting it locally in between. The bytes never touched this
host.

**Fresh-consumer verification: `austin-consumer-002`, 56.9 s, exit 0.** In a container with no
factory access and no GitHub credential:

| step | result |
|---|---|
| cloned package vs `MANIFEST.json` | 18 files, every hash matched |
| assets fetched (host-side, credential never in the container) | 5 files, 131,429,379 bytes, all verified |
| `sha256sum -c SHA256SUMS` | all five OK |
| `python3 code/qualify_dataset.py ./task` | QUALIFICATION PASSED, artifact `e4598317e406984f` |
| `sh baseline/reproduce_baseline.sh ./task` | **Eval AUC 0.7691**, CONTRACT OK |

The baseline reproduces exactly, on the *published* bytes rather than a rebuild.

**What that run does not cover, stated rather than implied:** the container cannot run the network
half of `get_dataset.py` (no credential by design), so the download is done by the worker host
and mounted read-only; and step 5 of `REPRODUCE.md` - a rebuild from the source API - needs ~136 MB
of scratch and was verified during construction, not in the consumer check.

**Decisions still open for review:** a licence for the published code and for the three benchmark
runner files (the benchmark project itself carries no licence file, so including them is the
maintainer's call to confirm), and public visibility. Two earlier decisions are settled: the
labelled holdout ships publicly, and the repository stays private until authorised.

**Three defects the transfer work exposed and fixed**, all found by running it rather than
reasoning about it: a credential that could not see the target repository surfaced as an
unhandled `UploadError` and killed a worker with no report; the asset API answers **302** to a
signed URL on another host, which the downloader did not follow (and must not follow with the
token attached); and the bundle rules rejected the extension-less `SHA256SUMS` by which the
published verification command is named.

## Research shortlist recorded 2026-09-18

Five candidates created with measured evidence in `candidates/<id>/record.json`
and `notes.md`. All numbers below were measured live on 2026-09-18 through
anonymous public APIs; none is a scored result.

| Candidate | Domain | Scale measured | Licence | Status |
|---|---|---|---|---|
| `austin-911-response` | public-safety operations | 1,049,636 calls, 2023-2026 | Public Domain | **lead** |
| `chicago-doah-adjudication` | administrative adjudication | 823,637 rows, 2008-2027 | See Terms of Use | runner-up, licence review needed |
| `noaa-tide-flooding` | coastal water levels | 302 stations; 1.37% pooled station-day exceedance measured | public domain (US Gov) | shortlisted, base rates now measured |
| `melbourne-pedestrian-counts` | urban activity sensing | 1,621,901 hourly records | **still unconfirmed** | shortlisted |
| `md-sewer-overflow` | wastewater infrastructure | 27,479 events 2005-2023 **plus a current series** | Public Domain | promoted from "lower priority" |

Lead choice: `austin-911-response`, because its licence is explicitly Public Domain
while Chicago's is "See Terms of Use", and the project must publish publicly.

### Lead candidate advanced (eighth session)

The column documentation was read and both open questions closed against the earlier
plan, in `candidates/austin-911-response/notes.md`:

- `mental_health_flag` is post-hoc (final problem description, call disposition, a
  responding officer's assessment) - excluded.
- `priority_level` is documented as assigned *at the time of the first officer's
  arrival* - also post-hoc, and it had been listed as a dispatch-time feature.
- `response_time` starts when the 911 call was **answered**, earlier than
  `response_datetime`; no column records that instant. Measured offset on 2,000 rows:
  median -58 s, range -561 s to +6,287 s, only 48/2000 within one second. The target
  must be the portal column, never a recomputed difference.
- `initial_problem_description` and `initial_problem_category` are genuine
  dispatch-time fields and were missing from the feature list.
- The table has **25 columns, not 42** (view metadata and a resource row agree exactly).
- Threshold T = 20 min is measured rather than guessed: positive rate 0.4008 in the
  training window (`response_datetime < 2025-07-01`, 714,314 rows) against 0.3938 over
  the full series.

### Maryland stale-series concern resolved (eighth session)

`stgj-u72u` ("Reported Sewer Overflows (New for 2023)") now returns **HTTP 200** where
an earlier session recorded HTTP 403. It is Public Domain, reports 3,434 rows, and its
`rowsUpdatedAt` timestamp is current (2026-09-18), so a live series exists alongside the
27,479-row historical one (`3rgd-zjxx`, last updated 2023-02). The candidate is no
longer "historical only"; the remaining work is the facility-day event rate and the
rainfall join, not currency.

### NOAA per-station exceedance base rates measured (eighth session)

The shortlist's open measurement is done, and it produced a trap worth recording. Twelve
stations spread across four coasts were measured for station-year 2025 from hourly
observed water levels, daily maxima compared to each station's `nos_minor` threshold.

**The published `nos_minor` threshold is expressed in the station datum (STND), and the
metadata API does not say so.** Comparing `datum=MLLW` heights against it gives **zero
exceedance at all 12 stations across 4,380 station-days** - a convincing-looking "this
task has no positive class" that is purely a datum error. The decisive check is the
2018-01-04 Boston bomb-cyclone tide: MLLW peak 15.022 ft (below the 15.85 threshold,
"no flood") versus STND peak 18.547 ft at the same timestamp (correctly above). NOAA's
own `htb.json` flood-status product was tried as a shortcut and returns nothing usable
from this host.

Measured result at `datum=STND`: **60 minor-flood days across 4,380 station-days, 1.37%
pooled**, per-station rates from 0.00% (Portland ME, Key West, San Francisco, Seattle) to
4.66% (Sewells Point VA). Four stations have an annual maximum within 0.2 ft below
threshold, so their zeros are offset-sensitive.

**Cross-checked against NOAA's own product (ninth session): VALIDATED.** NOAA's
`htf/annual.json` reports, per station-year, the authoritative flood-day counts. For 2025 my
`STND` reconstruction matches NOAA's `minCount` at **12 of 12 stations, 60 days against
NOAA's 60**; the rejected MLLW reconstruction gives 0. Sewells Point also had 3
moderate-or-worse days, the only station in the set with any.

**Hourly sampling undercounts, measured (ninth session).** Comparing daily maxima from
6-minute and hourly data for the busiest station-months: 1 flood day missed out of 17 caught
(Honolulu, 2025-10-07). The pooled hourly rate is therefore a **lower bound**; labels should
come from 6-minute data where the budget allows.

**The physical threshold is kept, by decision.** `nos_minor` is externally defined, has
physical meaning and is now externally validated. It is not replaced with a per-station
quantile merely to balance the classes; the imbalance is documented and handled with
precision/recall-style metrics and an explicit base-rate baseline.

**Split capacity is measured and sufficient.** train 2006-2021: 1,279 positives (1.83%);
eval 2022-2023: 234 (2.67%); holdout 2024-2025: 256 (2.92%). Positives cluster at about two
stations per flood day, so the effective independent counts are **118** and **126** distinct
flood days - ample for scoring, but confidence intervals must use that clustered count. The
rate is not stationary across the series (it rises with sea level), so a temporal split
carries systematic base-rate shift.

### Melbourne licence still unconfirmed (eighth session)

Re-checked through every channel that should carry it and **none declares a licence**:

- `GET /api/explore/v2.1/catalog/datasets/<id>` - no `license`/`licence`/`terms` key.
- The dataset information page HTML - no licence text node and no
  `creativecommons.org` link.
- DataVic's CKAN harvest of the same three Pedestrian Counting System datasets reports
  only the generic `licence_id: "other-open"` with `license_url: null`, which names no
  terms and is not a publishable licence.
- The portal's terms pages return 404 and `melbourne.vic.gov.au/open-data` returns 403
  from this host.

The City of Melbourne commonly publishes under CC BY 4.0, but that remains an
assumption and is recorded as such. **Do not make a release claim for this candidate
until a licence is actually read.**

No baseline, AUC, headroom figure or acceptance verdict has been measured. Nothing
here should be read as a result.

## Lessons consolidated and the research routine prepared (2026-09-18, thirteenth session)

**Where the time and quota went, measured.** 11 recorded sessions, 11.36M input / 0.70M output
tokens, ≈$4.07 estimated, of which 88% was the single long interactive Telegram session
($3.578, 962 messages). Scheduled work was cheap by comparison: three cron sessions cost
$0.034 in total. Useful research was not the expensive part - **waiting and rework were**:
infrastructure smoke tests, three failed worker jobs (`austin-001`, `austin-002`,
`austin-publish-002`), and one failed consumer job, each caught by running the thing rather than
reading it. The avoidable rework clustered in exactly two places: a claim trusted without
recomputation, and a runtime path never exercised before dispatch.

**One consolidation pass, three skills.** `dataset-qualification` rewritten at v2.0.0 around
the shape a skill is actually used with - when to use, commands, required evidence, the checks
as rules, failure modes, completion criteria - with the incident narrative removed (it lives
here) and the stale figure corrected to the measured one (clock offset median −57 s, range
−468…+6,041 s; T = 1200 s at a training rate 0.4038). Two new skills: **`dataset-discovery`**
(vetting before construction: the four contracts, cheapest-first order of work, per-candidate
required evidence, the verdict requirement) and **`dataset-release`** (package layout, staging
transfer, verification, publication gates). All three load through `skills.external_dirs`.

**Verified by a fresh session:** session `20260918_225732_aab19a`, given only the skill system
and told not to read this repository, listed all three skills with their descriptions, quoted
the first command from each, and restated the qualification completion criteria. Registration
is real, not assumed.

**Two mechanical checks, both in CI.** `scripts/check-candidate.py` is stage-aware: a record
claiming `ready`/`constructed`/`qualified`/`packaged` must carry the evidence that claim
implies, a terminal status must carry a reason, and a licence *name* is refused as evidence.
`scripts/check-package.py` requires the documents a reviewer needs, that `MANIFEST.json` covers
every file, that recorded hashes match the bytes, that `SHA256SUMS` agrees with the manifest,
and that an unpublished package says so. 180 tests pass under `TZ=Asia/Tokyo` and `TZ=UTC`.

**Research spend is now gated, and it fails closed.** `scripts/research-budget.py` measures
usage from `state.db:session_model_usage` (split into research / interactive / auxiliary /
scheduled-other by joining `sessions.source` and the `task` column), per-fire tokens from
`cron/usage_audit.jsonl`, and run history from `cron/executions.db`. Attached as a job's
pre-check script it prints a resume block and, when a limit binds, emits `{"wakeAgent": false}`
so the tick is skipped **without spending a token**. `config/research-budget.json` ships with
`allowance_usd: null`, which holds every session: an unconfigured budget is not an unlimited
one. `cron.catch_up_missed` is now `false`, and a tick beyond the late window is skipped rather
than caught up.

**Every cost figure is an estimate.** `cost_status` is `estimated` and `actual_cost_usd` is 0
across the board: Hermes estimates from its own records and no provider-reported actual exists.
The gate therefore bounds planned work and **cannot** reconcile against the portal's
subscription quota, usage reporting or reset period, none of which this instance can see. That
number and its allocation have been asked for before any recurring model work is enabled.

**Independent of the quota:** the weekly digest (`scout-weekly-research-digest`, job
`10d4f73308c8`, Mondays 08:00 UTC) and the hourly cleanup sweep are both `no_agent` scripts, so
monitoring and cleanup keep working when the allowance is spent or unset. The digest fired once
to verify delivery; next scheduled run 2026-09-21T08:00:00Z.

## Research allowance set, per-session limits enforced and verified (2026-09-19, fourteenth session)

**Allowance: 5 USD/month of Hermes-estimated spend, resetting on the 1st at 00:00 UTC.**
`config/research-budget.json`. Every figure is an estimate - `cost_status='estimated'`,
`actual_cost_usd=0` throughout - so this bounds planned work and is **not** enforcement of the
NousCloud subscription quota, which this instance cannot read. Separate from the 20 EUR/month
worker allowance. A **0.40 USD reserve** is held back, so a session starts only while
`spend + reserve <= allowance` and cannot consume the next one's budget.

### The per-session limit is enforced, not just accounted

Counting an oversized session double after the fact was accounting. Two supported runtime
controls are now applied **per run** on `hermes chat`, so they bound a scheduled session without
changing the ceiling on interactive work:

- `--max-turns 60` - **verified stopped**: the runtime injected "You've reached the maximum
  number of tool-calling iterations allowed. Please provide a final response..." and took the
  final answer (session `20260919_060228_2003f8`, 51.6 s).
- `--run-budget 2400` (40 min) - **verified stopped**: at 80% the wrap-up notice arrived ("run
  time budget nearly exhausted... stop new discovery/verification work now") and the session
  ended with its third planned step unfinished (session `20260919_061511_1a35c2`, 108.9 s at a
  test budget of 120 s).

The **600k-token limit is advisory** - the runtime exposes no token control - and its only
mechanical consequence is that an overshoot counts double against the weekly cap.

### What a scheduled session may run (measured)

Flagged commands are **refused** rather than approved, because nobody is present: `python3 -c`,
interpreter heredocs and the `execute_code` tool are all refused, while ordinary commands and
**script files** (`python3 .factory/<name>.py`) work normally. The prompt now tells the session
to compute via script files.

The documented escape hatch does **not** work on this build. `command_allowlist` is documented as
honouring dangerous-pattern *rule keys* on unattended surfaces; `_command_matches_permanent_allowlist`
matches only exact command text or a glob and refuses any command containing a shell operator, so
adding the two script-execution rule keys changed nothing - both commands were refused anyway.
`approvals.single_query_mode: approve` would lift it and was **not** taken: it would let a
scheduled session run dangerous commands. The global `agent.max_turns`/`agent.run_budget_seconds`
were likewise not used, since they would bound the operator's own chat too.

### The scheduled path was observed end to end

`scout-schedule-probe` (job `05411377338b`, one-shot, fired **by the scheduler** at
2026-09-19T06:20:04Z and started 06:20:05Z): status `completed`, delivery `delivered`, wrapper
elapsed 51.6 s, and session `20260919_062008_7b6775` tagged `scout-research` with a usage record
($0.00530, 8 tool calls). The probe also re-ran the gate mid-session and was refused with "lock
held for 32s by scout-research", which is the overlap guard working. The probe job was then
removed.

### What is live now

- `scout-research-session` (`69a5bc676d10`) - `0 8 * * 1,3,5`, `no_agent`, gate then one bounded
  session. **Next run 2026-09-21T08:00:00Z**; its own first scheduled fire is therefore still to
  be observed.
- `scout-weekly-research-digest` (`10d4f73308c8`) - Mondays 08:00 UTC, `no_agent`. Now reports
  usage *and* completed work (commits in the last 7 days plus the candidate queue).
- `scout-budget-checkpoint-2weeks` (`22ce870ec66f`) - one-shot 2026-10-03T08:00:00Z, recommends
  whether Mon/Wed/Fri inside 5 USD/month fits, and explicitly does **not** adjust anything.
- `scout-secondary-cleanup-sweep` (`e80975eddd4a`) - hourly, unchanged and independent of the
  research quota.

The five verification sessions are listed by id in `excluded_sessions` (with the reason) so they
count against neither the weekly cap nor the allowance: they measured the mechanism rather than
doing research. Cost of the whole enforcement verification: **0.0150 USD estimated**.

## A ready candidate in the buffer: NOAA tide flooding, measured to the bar (2026-09-19, fifteenth session)

**What advanced.** `noaa-tide-flooding` moved `investigating` -> **`ready`**, closing the three
items the previous session listed as open. The buffer the `dataset-discovery` skill asks for - one
ready candidate behind whatever is being built - now holds one, and `austin-911-response` (packaged,
awaiting two operator decisions) is no longer the only thing in the pipeline.

**A wrong claim in the record, caught by one request.** The record said all 302 water-level
stations carry flood thresholds. `mdapi/.../stations.json?type=waterlevels&expand=floodlevels`
returns either a bare number or an object whose `nos_minor` is `null`: **132 of 302 publish a
numeric threshold**, 170 do not. "The expand is present" was mistaken for "a threshold exists".

**The station list is now computed from the source, not hand-picked:** numeric `nos_minor` **and**
at least 18 of the 20 target years present in NOAA's own HTF annual product (1 request per station,
132 fetched, 0 errors, 18.6 s) -> **122 stations**, listed with per-station positives in
`candidates/noaa-tide-flooding/station_list_result.json`.

**Split capacity, recomputed over the frozen list** (`htf/annual` `minCount`): train 2006-2021
708,830 station-days / 11,886 positives (1.68%); eval 2022-2023 89,060 / 1,828 (2.05%); holdout
2024-2025 89,060 / 2,850 (3.20%). The daily product reproduced both evaluation counts exactly, so
the two NOAA products cross-check each other. Independent events, from distinct calendar days:
**332 (eval)** and **427 (holdout)** - mean 5.5 and 6.7 stations per flood day, busiest day 52 and
54 stations. Train clustering is recorded as unmeasured, not guessed.

**Extraction cost is measured, which was the last `ready` blocker.** Per request, on this host:
6-minute water level for one month 560,602 bytes in 1.61 s; hourly height for one year 545,427
bytes in 2.219 s; the inventory 777,394 bytes in 1.338 s. Over 122 stations x 20 years: **6-minute
labels 29,160 requests / 15.2 GiB / ~782 min single-threaded** (a worker backfill), hourly 2,430
requests / 1.2 GiB / ~90 min with a measured ~6% undercount of positive days. `product=daily_max`
**does not exist** (HTTP 400), so daily maxima must be derived from observations. Concurrency is
not measured and is labelled as such.

**Two API traps, both silent.** `htf/daily.json`'s array is `DailyFloodCount` with `minFlag` as
the string `"1"` - the wrong key returns "no flood days" with no error, which is how the first
clustering run produced a confident zero. And the datum trap from the ninth session still binds:
`nos_minor` is in the station datum, so `datum=STND` is required. Silent-zero shapes are the
failure mode of this source; anything reading 0 here is a claim to verify, not a result.

**The scheduled routine's own fire no longer holds itself.** The overlap fix landed while this
session was reading (commits `017c293`, `e0ece51` in the shared repository, written by the
operator's concurrent session - this session did not author them). Evidence observed here rather
than assumed: the ledger holds the pre-fix skip
`research job 69a5bc676d10 is already running` at 06:39:37Z, and the wrapper then started **this**
session at 06:42:04Z with a pid-bearing lock and a gate that held only for `lock held for 97s by
scout-research` - i.e. its own lock, which is the correct overlap signal.


## Hugging Face publishing integrated and verified (2026-09-19, fifteenth session)

**Both destinations now carry the same accepted artifact, from one release manifest.**

- GitHub: `github.com/earino/austin-911-response`, release `391804787`, tag `v2026.09` - private.
- Hugging Face: `huggingface.co/datasets/earino/austin-911-response`, revision `v2026.09` - private.
  Version-pinned load, exercised by job `austin-hf-006`:

  ```python
  from datasets import load_dataset
  ds = load_dataset("earino/austin-911-response", revision="v2026.09", token=True)
  ```

  Split counts, positive counts, label values and the 12-column schema all match the accepted
  artifact: train 572,180 / 231,025 positives, eval 285,665 / 109,860, holdout 191,791 / 72,450,
  labels `[0, 1]`. The same call **without** a credential raises `DatasetNotFoundError`, which is
  how privacy is demonstrated rather than asserted. CSV digests are verified against
  `MANIFEST.json` at both destinations.

**Credentials.** `HF_TOKEN_WRITE` (write role, account `earino`) publishes;
`/opt/data/.secrets/huggingface-write.token` (0600) is the file form the worker path uses, exported
by `scripts/scout-factory` as `FACTORY_HF_WRITE_TOKEN_FILE`. It reaches the worker as a root-only
`/opt/scout/credentials.json` entry and is passed to the client through the child environment -
never an argument, never a container, mount, log, manifest or asset. The **inference** credential
is a different token, was never read, and its configuration is unchanged. A job with no publishing
credential is refused at plan time.

**The path, reusable.** `scripts/hf-publish.py --plan|--create|--upload-small|--verify|--tag`, plus
an `hf_publish` worker job that moves the bulk (131 MB never touches this host). Tag last and
idempotently: a tag created before the data landed pins a commit without the files. Re-running is
safe - job `austin-hf-006` skipped all five files as already at the manifest digest and re-sent 0
bytes. Per-destination completion lives in `release/<dataset>/DESTINATIONS.json`; `check-package.py`
refuses a manifest claiming published while a destination is unverified.

**Four defects were found by running it, not reading it** (all fixed, three of them mine):
no `uv` and no pip in the worker venv; the small files' digest check compared a git `blob_id` to a
sha256; the loading check never passed a credential; and the label check assumed a ClassLabel
feature where a CSV yields an integer column. Two of these cost a job each to discover, which is
why `tests/test_hf_helpers.py` now statically checks every helper body's imports.

**Cost:** six `cpx42` jobs, EUR 2.70 reserved against the EUR 20/month worker allowance; every
worker destroyed with the provider confirming 0 servers and 0 IPs. The research allowance is
untouched by publishing.

**Still the operator's decision:** public visibility on either platform, and the licence for the
derived compilation (`LICENSE.md` records the options). Private until then, with the labelled
holdout included on both when approved.

## Licensing resolved and applied to both destinations (2026-09-19, sixteenth session)

The open licence decision is closed, and the terms are now part of the package rather than a
question recorded in it.

- **MIT** (`LICENSE-MIT.txt`) for the construction, qualification and measurement code, the docs,
  and the three baseline runner files copied verbatim from `earino/harness_benchmark`, file set
  `task_template/`. That project is the copyright holder's own work, developed with Claude and
  Szilard; permission to release the copies under MIT is confirmed and contributor credits are
  preserved (Copyright (c) 2026 E. Arino de la Rubia (earino), with contributors Claude and
  Szilard). Upstream credits are preserved too - `szilard/xgboost-autoresearch`, itself in the
  tradition of `karpathy/autoresearch`. `../harness_benchmark` was **not** edited: the permission
  covers the distributed copies.
- **CC0-1.0** (`LICENSE-CC0-1.0.txt`) for **our rights in the derived compilation**, scoped to our
  contribution - row selection, the derived binary label, the temporal partition and the
  packaging. It does not cover or relicense the City of Austin's data, which keeps its **Public
  Domain** designation, attribution and suggested citation, and the dataset is labelled as derived
  and not an official City product.
- The statements that the baseline copies lacked permission, and the all-rights-reserved default,
  are removed from `LICENSE.md`, `README.md`, `RELEASE_NOTES.md`, `baseline/README.md` and the Hugging
  Face card.

**Mechanically enforced, not remembered.** `config/licensing-policy.json` holds the standing
policy; `candidates/<id>/license.json` holds the per-dataset decision; `release-manifest.py` writes
both into the manifest's `licenses` block; `check-package.py` refuses a release with no declared
terms, one naming a licence file it does not ship, or a publication claim with undeclared terms.
The policy carries the rule that matters for the next dataset: **CC0 is not a blanket override of
upstream terms** - terms are chosen per dataset to be compatible with each source, attribution and
share-alike requirements carry through, and a source whose licence cannot be read is not published.

Regenerating the manifest exposed a real defect: `DESTINATIONS.json` was being swept into
`package_files`, so every re-verification invalidated the manifest it helped complete. It is a
post-verification record and is now excluded, which is what `check-package.py` had documented.

**Verified at both destinations, from the pinned revision:** GitHub `v2026.09` clone - 20 package
files hash-checked, none failing, three licence files present; Hugging Face `v2026.09` - private, 16
files including the licence texts, `license: cc0-1.0` in the card. **The accepted dataset bytes are
unchanged**: train `6fc37e03`, eval `241dee5e`, holdout `738ff7ec`, artifact `e4598317e406984f`, and
the GitHub release still carries the same five assets. Both repositories remain **private**;
publication still requires the operator's separate approval.

## Builder: repeatable website publication pipeline (2026-09-19)

The operator clarified the deliverable: a system Scout can operate without a builder
in the monthly loop. The implementation is `scripts/site-publish.py` with
`prepare`, `inspect`, `publish`, `verify` and `status`. Read `docs/WEBSITE-SYSTEM.md`.

Inputs are the existing verified release package, `sites/<dataset>.json` for editorial
content, and `config/sites.json`. Preparation validates and projects metadata, writes
an exact review plan and renders both previews offline. Publication reconciles GitHub
repository ownership, atomic file commits, Pages settings, deployment environments,
workflow dispatch and live verification; it updates GitHub/Hub navigation. Receipts
support bounded retries and recovery. Public deployment remains approval-gated.

The standalone renderer and pinned workflow travel with each site repository. The
catalogue preserves earlier dataset/version records. Website corrections increment
`site_revision` and retain earlier editions; they do not rebuild data or move data
tags. The second-dataset lifecycle test uses a metadata fixture and the same preparation
code; it is not a claim that another real dataset has been constructed.

**Observed on GitHub:** transport wrote the generated site to the temporary branch
`builder/site-runtime-smoke-20260919` of this private repository, at
`138347f4fca232c17d16d333bcf67bb4dea1a196`. Repeating the atomic commit returned the same SHA.
[Generated workflow run](https://github.com/earino/dataset-factory/actions/runs/35436121641)
completed successfully: build/upload executed, public artifact/deploy steps were skipped.
The downloaded preview's JSON matched the prepared record, review mode was true, and
version/edition pages existed. The provider reported this factory private and
`has_pages: false`. The accompanying existing test workflow also passed.

The builder independently read Austin's pinned GitHub manifest and release 391804787;
all five provider asset digests/sizes matched the site record. No data file was downloaded.
The local suite initially found one pre-existing bytecode file dated 2026-09-18 in
the NOAA candidate directory. Only that generated file and its empty cache directory
were removed; no candidate source or benchmark file was changed.

**Not yet observed:** the Hub adapter against Scout's hosted write credential, public
Pages provisioning/deployment, and Scout independently completing a real site update.
The builder has GitHub access, not Scout's Hub publishing credential. Unit/provider
simulations and a real private preview build do not satisfy those live checks.

**Next action for Scout:** pull the implementation, run offline preparation and
`inspect` from the hosted environment, and report the plan SHA, credential/access
readiness and any real defect. Keep both data repositories private and leave Pages
disabled until the operator approves publication. After approval, finish the dataset
release and run `publish`/`verify`, then independently exercise an editorial revision.
Ordinary operation and repairs belong to Scout; builder review is not a standing gate.

**Implementation verification:** commit `8444c46383539934dff13b798504822f4a466067`
passed [Local checks](https://github.com/earino/dataset-factory/actions/runs/35436380363)
and [Website pipeline preview](https://github.com/earino/dataset-factory/actions/runs/35436380409).
The latter contains the review bundle as an Actions artifact. A clean export of the
staged tree, with no private configuration, passed 240 tests (4 environment-specific
skips) and factory doctor. The prepared Austin plan SHA is
`87b1fd5a9bcf920c0396b0e6c08c52f89de1ba991df70e57245e59abb7a88db6`.

## 2026-09-19 - Hosted handoff check (bounded, no public deployment)

Ran the exact steps the operator specified, from the hosted environment, against the builder's
implementation at `83c1d683a6519f7386b0504666a8f75b31f82999`. No blocking defect and no missing
permission was found. Both data destinations stay private and Pages stays disabled.

**Plan SHA: `87b1fd5a9bcf920c0396b0e6c08c52f89de1ba991df70e57245e59abb7a88db6`** - identical to the
expected value, so **no implementation input changed**. `prepare` made zero network calls and did not
modify the release package. An earlier bundle prepared into a different output directory produced
the same digest, confirming the plan SHA covers the inputs rather than the output path. Repeated
preparation is byte-identical across `bundle.json`, `REVIEW.md` and both previews. The reviewed
bundle is `.factory/sites/austin-website-1`.

**Preflight (`inspect`, exit 0, empty stderr), using the default HF environment** - the default
resolved without `--hf-python`:

- GitHub release `391804787` verified against its pinned manifest and asset digests; `private: true`.
- Hub revision `542382ae6d3e48175b6938f5df4f91e087cfd2ee` verified, equal to the Hub main commit;
  `private: true`; navigation links not yet present, as expected before publication.
- `ready_for_publication: false` - correct, because both destinations remain private.
- Dataset repository `earino/austin-911-response` accessible, Actions enabled (`all`, no SHA
  pinning), no Pages site (`pages: null`).
- Catalogue `earino/dataset-factory-site` not accessible - it does not exist yet and the plan creates
  it at publication. Expected state, not a missing permission.

**Content agreement** - the dataset preview matches `MANIFEST.json` fact by fact: the version tag,
the full artifact hash `e4598317e406984fa590aacc5e7aff675867578c51ae1a84ebf6279bc42c3328`, all three
split row counts (572,180 / 285,665 / 191,791), MIT, CC0-1.0, the source's Public Domain
designation and both destination links. Nothing from the holdout is inlined. The catalogue preview
carries the tag and both links, which is its role.

**Public-projection leak check** - across all 19 projected files: no credentials, staging URLs, job
or worker records, host paths, provider identifiers or internal release/asset ids. Two initial hits
were my own over-broad patterns matching the public catalogue name `earino/dataset-factory-site` and
the intentional `artifact_version` field; both were read in context and dismissed.

**Two safety properties tested rather than assumed.**

1. A wrong `--approved-plan` digest is refused with exit 1 and
   `Approval does not match this prepared plan` - observed live and now locked by a new test that
   also asserts nothing is written: no commits, no deployment dispatch, no receipt.
2. The Hub adapter genuinely does not depend on the inference credential: with a deliberately
   poisoned `HF_TOKEN`, `inspect` still verified the Hub revision. Confirmed in `scripts/site-hf.py`,
   which resolves `HF_TOKEN_WRITE` (or its credential file) and calls `env.pop("HF_TOKEN", None)` on
   the child environment, exactly as the handoff states.

**One ordering observation, not a defect.** `GitHub()` and `Hub()` are constructed just before the
approval digest is compared, so a stale digest still builds the client objects. No write, dispatch
or receipt follows the refusal, and the live run showed no network latency, so the refusal still
precedes every mutation.

**Builder's CI claims independently verified:** Local checks run `35436461305` and Website pipeline
preview run `35436461283` both exist at the full SHA `83c1d683a651` and both succeeded.

**Test count reconciled:** the builder measured 240 tests with 4 environment-specific skips in a
clean checkout; this environment reports **246 with no skips** - the builder's 240, plus the 5 added
with the novelty gate, plus this check's new approval test, with those 4 tests running here because
`gh` and the Hub environment are present.

**After operator approval:** finish the public dataset release, then
`publish --approved-plan 87b1fd5a... --wait-seconds 600` and `verify`. A pending run is not
completion.

## 2026-09-19 - Austin is public, and its website is live

Operator approved public visibility for the dataset and its infrastructure. Publication ran on the
same reviewed plan (`87b1fd5a...`), unmodified; the approved digest was never applied to changed
inputs.

**Both destinations are public and anonymously readable.** GitHub `earino/austin-911-response`
(release `391804787`, tag `v2026.09`) and Hugging Face `earino/austin-911-response`
(`542382ae6d3e`, not gated). With no credential at all: the repository page answers 200, all five
GitHub release assets answer ranged GET 206, the Hub dataset API reports `private: false`, and the
Hub data files answer ranged GET 206. Data files, tag and artifact version are unchanged by
publication - `e4598317e406984fa590aacc5e7aff675867578c51ae1a84ebf6279bc42c3328`.

**Live sites**, both deployed and verified, cross-links verified, receipt `complete`:

- Dataset: https://earino.github.io/austin-911-response/ (deployment run `35453081771`)
- Catalogue: https://earino.github.io/dataset-factory-site/ (deployment run `35453120375`)
- Live records read back and matched: `.../versions/v2026.09/release.json` and `.../catalog.json`
- `verify` exit 0, `status: verified`, HTTPS enforced on both sites.

The catalogue repository was created by this run and carries its ownership marker; both repositories
keep their previous releases.

**Two real defects found on first live contact, both fixed here.**

1. **HTTPS was enforced before the certificate existed.** `setup_pages` called
   `PUT /pages {"https_enforced": true}` before dispatching any deployment, and GitHub answers
   **HTTP 404 "The certificate does not exist yet"** until the *first successful deployment* has
   provisioned it. The first live publication aborted at exactly this step - the area the builder's
   own notes flagged as never observed against GitHub. The certificate only appears after a
   deployment, so enforcement now tolerates that answer, records it as deferred, and is retried
   automatically once a deployment reports `deployed`. `verify` reads back the enforced state on
   both sites rather than assuming it. New test models GitHub's refusal.
2. **The homepage guard was undiagnosable.** The dataset repository's homepage pointed at the
   upstream source portal (`datahub.austintexas.gov/d/e687-fx2y`), so the pipeline refused to
   replace it - correct, but the message did not say what the existing value was. The message now
   names both values.

**One reviewed judgement call.** After checking, the rendered dataset site links the City of Austin
portal prominently and carries the attribution, Public Domain designation and suggested citation, so
replacing the repository homepage with the site URL loses nothing. The homepage was cleared once, as
a reviewed transition, so the pipeline itself set it - the approved plan was not modified to achieve
this.

**Noted, deliberately left alone:** `MANIFEST.json` (public) records the private staging repository's
*name* (`staging_repo`), and `VERIFICATION.md` names the job that performed the transfer. No
credentials, URLs or download paths are exposed, and the manifest is a frozen, hashed artifact of an
accepted release - editing it would change the release identity and invalidate the reviewed plan, so
removing those names, if wanted, is a new version rather than an edit.

**Site publication deferred nothing else:** the Hub card and the GitHub README carry the cross-links,
and the labelled holdout is downloadable on both platforms.

## 2026-09-19 - The published card and docs still said "private": three defects fixed

The operator noticed the Hugging Face card still read "Status: private. Public visibility requires
explicit human approval" after the approved publication. It was right, and fixing it exposed two
more defects of the same shape - a claim asserted in a generator instead of derived from the state.

1. **The card's status was a literal.** `scripts/hf-publish.py` hard-coded the private wording, and
   the loading instructions told readers to pass a token "for a private repository". The card's
   status line and its loading note now follow `published` in the manifest. The card also demanded
   `token=True` in the version-pinned example, which would fail for an anonymous reader of a public
   dataset; it is emitted only while the release is private.
2. **The manifest asserted its own publication state.** `scripts/release-manifest.py` held
   `visibility`, `published` and `publication_note` as literals, so the *documented*
   post-publication regeneration step - "regenerate MANIFEST.json and SHA256SUMS from recorded
   evidence" - would have re-asserted "private" forever. All three are now derived from
   `DESTINATIONS.json`, which records what was checked per destination. The manifest now reads
   `visibility: "public"`, `published: true`.
3. **The card shipped a literal placeholder.** The template wrote the repository id as a
   doubled-brace placeholder inside an f-string, which renders to a single-brace string, so the
   replacement never matched. The published card carried `load_dataset("{repo_id}", ...)` and
   `hf download {repo_id}` - commands that cannot run. An unambiguous token (`__REPO_ID__`) is used
   now, and the built card was checked to contain the real id four times and the placeholder zero
   times.

**What was corrected and where.** `DESTINATIONS.json` records both destinations as public with the
anonymous-read evidence and the authorisation; the package README, RELEASE_NOTES and the public
repository copies state "public since 2026-09-19"; the Hugging Face card, `LOADING.md` and manifest
were re-uploaded. The public repository received one atomic commit (`fa852cdd0274`) that carries the
README digest its manifest pins, so the website pipeline's own invariant still holds. The dataset
tag, the five assets and `artifact_version` are untouched, and the approved site plan digest is
unchanged - verified by re-running `prepare`, which reproduced `87b1fd5a...` exactly.

**Verified after the repair:** the website pipeline re-ran and reports `complete`, `verify` returns
`status: verified` with HTTPS enforced on both sites, the Hub revision is still `542382ae6d3e`, the
card reads "Status: public", and an anonymous client - implicit token use disabled - fetches all
three revision-pinned data files (HTTP 206) and the Hub API reports `private: false`. The library
level `load_dataset` call needs the `datasets` package, which lives in the worker image rather than
the Hub venv here, so the version-pinned path is verified at the HTTP level here and its library
form was exercised by the worker job before publication.

**Suite:** 255 tests, including new guards for the placeholder and for the derived publication
state.

## 2026-09-20 - NOAA build accepted: complete panel, both levels gated

`noaa-003` produced the artifact. **Coverage is complete**: 122 of 122 frozen stations, 2,440 of
2,440 station-years, 4,880 requests, **zero errors**. Both levels pass the qualification gate on the
full artifact - 32 checks each, no failures - including the leakage, prediction-timing, split,
unit-frame and runner-contract claims.

| level | split | rows | positives | stations |
| --- | --- | --- | --- | --- |
| temporal | train | 697,373 | 11,774 | 122 |
| temporal | eval | 89,038 | 1,815 | 122 |
| temporal | holdout | 88,841 | 2,850 | 122 |
| station_disjoint | train | 461,580 | 7,513 | 81 |
| station_disjoint | eval | 29,930 | 788 | 41 |
| station_disjoint | holdout | 29,930 | 1,090 | 41 |

Positives match the capacity measured before the build to within 1%: holdout is exact on both
levels (2,850 and 1,090). The residual difference is the year-boundary effect that was predicted -
the label is next-day, so a flood day on the first date of a window has no previous row to be
labelled from.

**Acceptance without moving bulk data.** The gate report records the sha256 of every file it gated;
the staging manifest records the sha256 of every uploaded file. All ten files across both levels
compare equal, so the report describes exactly the bytes in staging. The local `--accept` path was
not used because it would mean downloading ~180 MB to the coordinator.

**The three attempts, and what the failures taught.** Run 1 lost 594 station-years and 13 stations
to rate limiting, and passed both gates anyway - the gates check leakage, timing, splits and units,
not coverage. Run 2 built all 122 stations but lost 60 station-years to HTTP 403, which the retry
classified as permanent and retried immediately; the new coverage gate refused it and skipped
qualification rather than gating an incomplete artifact. Run 3 fixed the 403 handling and added
paced requests, and lost nothing.

**A worker watchdog now runs every five minutes.** Three jobs ran and the operator had to ask twice
what was happening: a remote job outlives the turn that launched it, `notify` fires when the launch
exits rather than when the job does, and `worker status` reports the *server*, which idles until its
lifetime expires. `scripts/scout-job-watch.py` polls with `worker collect` (the only cheap signal),
emits one deterministic line per job so a scheduler change detector can gate the agent, and treats
anything that is not an explicit `running` answer as terminal - including the sweep having taken the
worker first.

**Cost:** three worker runs at EUR 0.24 / 0.32 / 0.32. Project total about EUR 4.96 of the EUR 20
monthly allowance.

**Next:** a baseline through the runner's contract on both levels - the question of whether
observations-only, station-normalised features carry signal on held-out stations - then packaging.

## 2026-09-20 - NOAA baseline: the task is learnable, and it transfers

`noaa-baseline-001` succeeded in 27.5 minutes (exit 0). The benchmark's own `train.py` and
`validate.py` ran unmodified against both levels, with their sha256s recorded in the report and
`validate.py` re-running training and printing `CONTRACT OK` on both.

| level | eval AUC | train rows | eval positive rate |
| --- | --- | --- | --- |
| temporal | **0.8638** | 697,373 | 2.04% |
| station_disjoint | **0.8688** | 461,580 | 2.63% |

The station-disjoint level scores the same as the temporal one on **stations the model never saw**,
so the signal is not station-specific memorisation - which is the whole basis of the novelty verdict
and the reason that level exists.

**Not yet calibrated, and this matters.** The strongest feature is yesterday's maximum against the
station's own threshold, and consecutive flood days are common, so part of that AUC may be
autocorrelation rather than prediction. A single-feature persistence baseline is the next
measurement, before any headroom claim is made or published.

**Why the operator heard nothing about it.** The job finished at 05:56 and was collected, but not
reported. The watcher dropped the job from its output the moment the job record went terminal, so
the agent woke to an empty diff and had nothing to say: a watchdog that reports "nothing" the
instant there is something is worse than no watchdog. It now keeps a finished job visible until it
has been handled, marked by a `handled` file beside the result, and the report is not considered
delivered until that marker exists.

**Cost:** EUR 0.32 for this job; about EUR 2.20 of the EUR 20 monthly allowance across all runs.

### Persistence calibration - the honest floor (same day)

`.factory` evidence before any headroom claim. No training, no worker, no dependency: rank-based AUC
of each single feature on the eval split.

| level | best single feature | that alone | full model | model's actual headroom |
| --- | --- | --- | --- | --- |
| temporal | `margin_ft` (yesterday's max vs threshold) | 0.8265 | 0.8638 | **+0.0373** |
| station_disjoint | `margin_ft` | 0.8454 | 0.8688 | **+0.0234** |

**Persistence is most of the signal.** The trained model adds 0.023-0.037 over a stock feature it did
not have to learn anything to use. The task transfers across stations and is genuinely real, but its
headroom is narrow: a one-feature rule gets ~96% of the way.

The plain rule "yesterday exceeded" agrees with the label **96% of the time** while carrying almost no
ranking signal (AUC 0.63), because only ~2% of days are positive. That is why the contract scores AUC
and why accuracy is not reported as a headline anywhere.

**Consequence:** the release card must carry the single-feature reference beside the model baseline,
as Austin does (0.627 single feature, 0.769 full model). Widening the headroom would mean a harder
variant - onset after a dry spell, or a longer horizon - not a threshold change. The physical
threshold stays. Operator decision pending; research is not blocked by it.

## 2026-09-20 - NOAA release package assembled, and the accepted bytes are in the dataset repository

The packaging commit `b93a5cb` turned the manifest generator into a dataset-driven one (its
repository, source block, layout, asset names and commands moved from literals in the script into
`candidates/<id>/release.json`; Austin's `MANIFEST.json` regenerates byte-for-byte identical, which
is what proves the refactor changed nothing already published). `release/noaa-tide-flooding/` now
carries `MANIFEST.json`, `SHA256SUMS`, `DATA_DICTIONARY.md`, `README.md`, `VERIFICATION.md`,
`REPRODUCE.md`, the licence texts, the runner baseline and the construction, qualification and
measurement code: 28 package files listed in the manifest, `check-package.py release/noaa-tide-flooding` OK.

**`noaa-publish-001` succeeded** (exit 0, 0 minutes of container time - it only moves bytes).
The `transfer` spec copied all ten accepted artifact files, **196,017,925 bytes**, from private
staging release 392230750 into `earino/noaa-tide-flooding` release `392387511`, tag `v2026.09`,
on a worker host, so the ~187 MB never passed through the coordinator. `failures: []`.

**Verified from the service, not from the job's own report.** Every one of the ten assets re-read
from the GitHub API matches the job's transferred size and sha256 exactly, 10 of 10, and the
repository is `private`. The tag `v2026.09` and `main` resolve to the same commit
`9bcbf2c69e04e7e3d92191a3cfe86ed066cc422c`, which carries the docs, so GitHub is the complete
destination: docs, code and release assets in one place. All ten documentation files at that commit
are byte-identical to the package's own copies - compared by Git blob hash, `MANIFEST.json`,
`SHA256SUMS` and both licence texts included - so the repository is not describing a different
dataset from the one `check-package.py` validates.

| level | split | rows | eval file bytes | sha256 (first 8) |
| --- | --- | --- | --- | --- |
| temporal | train / eval / holdout | 697,373 / 89,038 / 88,841 | 97,931,036 / 12,507,806 / 12,475,942 | `939efaf4` / `cbc3bd54` / `cceb5a93` |
| station_disjoint | train / eval / holdout | 461,580 / 29,930 / 29,930 | 64,636,157 / 4,229,470 / 4,228,351 | `c18ca880` / `e790547b` / `79968550` |

Recorded in `candidates/noaa-tide-flooding/record.json`: status `packaged`, the job, the
destination with the per-level artifact versions and every file digest, and the local research
artifacts moved to `artifact_evidence`. `scripts/check-candidate.py noaa-tide-flooding` OK.

**The worker was destroyed** (server 166609889, `deleted_at` recorded in `jobs/noaa-publish-001.json`)
and the job's small reports were fetched into `.factory/noaa-publish-001/reports/`. The staging
release's own manifest shows `uploaded: false`, which is the job's snapshot written before its
result upload completed - not a failed transfer: the collected `result.json` carries
`uploaded: true` with the ten transferred entries and an empty failure list.

**Nothing is public.** Both repositories are private and no `DESTINATIONS.json` exists for this
dataset, so the manifest still derives `visibility: private`, `published: false`.

**The next step found a real defect.** `scripts/hf-publish.py` is still Austin-shaped: its package
path is the literal `release/austin-911-response` (only the repo id takes an argument), so running
it for NOAA would upload Austin's files under NOAA's card and tag. It needs the same treatment the
manifest generator just got - read the dataset from its argument or the manifest - before the
Hugging Face half of this release can be attempted.

**Cost:** EUR 0.16 reserved for this job at the EUR 0.08/h cpx32 rate; it ran for minutes, so the
charge is a fraction of that. No new research spend.

**Operational note, cost this session one failed push.** `git push` from a shell that has exported
`GH_TOKEN` uses *that* token, because `gh`'s credential helper prefers the environment: exporting
the restricted staging token for a read-only API call made the next push fail with
`Write access to repository not granted`. `unset GH_TOKEN GITHUB_TOKEN` in the same shell restores
the working helper. Scope such exports to the command (`GH_TOKEN=$(cat ...) git ...` or a
subshell) rather than leaving them in the session environment.


## 2026-09-20 - The published NOAA release passes an independent consumer check (noaa-consumer-001/002)

The published bytes were checked the way a consumer receives them: a worker container with **no access
to this repository and no GitHub credential**, cloning `earino/noaa-tide-flooding` at `v2026.09`,
hashing every file against `MANIFEST.json`, verifying the ten release assets with `sha256sum -c`,
running the published gate and reproducing the published baseline on **both** levels.

**`noaa-consumer-001` failed** (staging release 392392211, 51.4 s, 5 report assets, worker 166610817
destroyed). It died in the baseline step and left nothing in the log to diagnose it, because that
step sent its output to a file under `/output` and the container died before the file was uploaded -
`container.log` ends at the step header. Everything before it had passed: 28 package files matched
`MANIFEST.json`, `sha256sum -c` was OK on all ten assets, and both gate runs reported
`QUALIFICATION PASSED` (temporal `8896c4423c53cb14`, station_disjoint `e6aff23f394ddfe4`), matching
the artifact versions recorded at build time. Recorded in `jobs/noaa-consumer-001.json` and
`.factory/noaa-consumer-001/`; the failure was an unlogged step, not evidence about the data.

**The fix was to make the step visible, not to change the check.** `run.sh` now installs the
benchmark's declared dependency ranges (`pandas>=2.2,<3`, `numpy>=1.26`, `xgboost>=3.0`,
`scikit-learn>=1.5`) as an explicit step and tees the baseline output into the log, so a failure
cannot be silent; the corrected script is what `noaa-consumer-002` ran.

**`noaa-consumer-002` succeeded** (staging release 392395671, 72.0 s, worker 166611532 destroyed).
Result, on the published bytes:

| step | result |
| --- | --- |
| package vs `MANIFEST.json` | 28 files checked, every one matched |
| `sha256sum -c SHA256SUMS` | OK on all ten assets |
| published gate, temporal | exit 0, `QUALIFICATION PASSED`, artifact `8896c4423c53cb14` |
| published gate, station_disjoint | exit 0, `QUALIFICATION PASSED`, artifact `e6aff23f394ddfe4` |
| baseline, temporal | `CONTRACT OK`, eval AUC **0.8651** against the recorded 0.8638 |
| baseline, station_disjoint | `CONTRACT OK`, eval AUC **0.8687** against the recorded 0.8688 |

**The reproduction is within about 0.002, not exact, and that is now recorded as a property of the
measurement.** The artifact digests are identical and the dependencies resolved to the same versions
(pandas 2.3.3, numpy 2.5.3, xgboost 3.4.1, scikit-learn 1.9.1), so the difference is the runner's
training rather than a version or byte change: xgboost with default threading is not
bit-reproducible. The recorded baseline is one measurement, not a constant, and the reproduction
guide and consumer check now say so (the check compares values, not only exit codes). Both gate
artifact versions match the build-time ones, so the published bytes are the gated bytes. Neither
check scored the holdout.

Recorded in `candidates/noaa-tide-flooding/record.json` (`jobs` for both runs plus a
`consumer_verification` block) and in the release's own `VERIFICATION.md`;
`scripts/check-candidate.py noaa-tide-flooding` OK.

**CI.** `d925039` (the dataset-driven Hugging Face publisher and NOAA's card) and `23d745d` (per-config
Hugging Face loading verification, the reproduction record and the run-script fix) each have a
completed, **successful** GitHub Actions run for their own pushed SHA: runs 35505322723 and
35505729541 / 35505729555.

**Nothing is public.** Both repositories stay private and no `DESTINATIONS.json` exists, so the
manifest still derives `visibility: private`, `published: false`.

**Cost.** Two cpx32 runs, 51 s and 72 s: well under EUR 0.01 each at the EUR 0.08/h rate, inside the
EUR 20 monthly allowance.

**Operational observation.** A second coordinator session was already acting on this same job when
this run started (it collected `noaa-consumer-002`, wrote the `handled` markers, and had begun the
Hugging Face work). Its committed work is the two CI-green commits above; this entry adds the
consumer results it had not yet recorded in `record.json` and `STATE.md`. Two coordinators on one job
ledger is the situation `AGENTS.md` forbids, so the remaining work below is left to whichever session
is currently driving it - this run launched and destroyed nothing.

**Next action.** The Hugging Face half is in flight: `jobs/noaa-hf-001.json` was launched on worker
166611959 (10:38) to move the bulk files to the private Hugging Face repository under the generated
card, with `candidates/noaa-tide-flooding/hf/` holding the plan. Finish it with
`python3 scripts/hf-publish.py --verify --candidate noaa-tide-flooding`, confirm every config loads,
then `--tag` last and check the tag and `main` resolve to the same commit. Operator approval is
required before either destination leaves private, and the open decision on shipping the narrow
headroom (persistence floor 0.8265/0.8454 against 0.8638/0.8688) or building a harder variant is
still pending.

## 2026-09-20 11:20 UTC - noaa-hf-001: the upload was fine, the verifier was not

**`noaa-hf-001` failed, and the failure was in our code rather than in the dataset.** The job
moved all ten accepted files to the private Hugging Face repository (10 uploads, 196,017,925 bytes,
0 failures, 0 skips, each checked against the digest the Hub reports) and then died in the loading
check with `KeyError: 'splits'`.

The verify helper has two branches - a job declaring `configs` and a job declaring a single set of
`splits` - and only the first was inside the `if`. The single-config code ran unconditionally after
it, reading `expected["splits"]` on a job that has `configs` instead. `load_dataset` had already
read all six splits of both configs (temporal 697,373/89,038/88,841; station_disjoint
461,580/29,930/29,930) before the crash, so the report said "the documented loading path did not
reproduce the artifact" about an artifact that was in fact loading. The coordinator-side read-only
listing of the private repository agrees with the upload: all ten paths present at the manifest's
byte sizes.

**Fix.** `workers/hf_publish.py`: the single-config path is inside the `else` branch and the report
is printed once. The old source reproduces the exact `KeyError: 'splits'` against a stub `datasets`,
and `tests/test_hf_helpers.py::VerifyHelperBranchTests` now runs the real helper source for both
job shapes - per-config checking, comparison rather than mere loading, and the original single-config
path. 283 tests pass.

**The corrected job is prepared and its plan is clean** (`candidates/noaa-tide-flooding/hf/job-002.json`,
id `noaa-hf-002`, same ten assets, HF credential present, reservation EUR 0.45). **It could not be
launched: another coordinator started `jobs/noaa-004.json` at 11:04:32** - a cpx32 rebuild of this
same candidate, untracked in git, 120-minute timeout - and the policy allows one worker at a time.
Waiting for a NOAA build (noaa-003 ran overnight) is not something a watchdog tick can do, so the
launch is left to the next session or to the wait loop started here, which retries for fourteen
minutes and then gives up cleanly.

**Next action.** When the worker slot is free: `sh scripts/scout-factory worker launch
candidates/noaa-tide-flooding/hf/job-002.json`, then `worker collect noaa-hf-002` and read
`hf_loading.ok` together with every per-config row count and positive count in
`.factory/noaa-hf-002/reports/`. Only then `python3 scripts/hf-publish.py --verify --candidate
noaa-tide-flooding` (its `DESTINATIONS.json` entry claims the loading check was run by the worker,
so it must not be written before that report exists), then `--tag` last, then
`python3 scripts/check-package.py release/noaa-tide-flooding`. Nothing is public: both repositories
remain private, and no `release/noaa-tide-flooding/DESTINATIONS.json` exists yet, so the
manifest still derives `visibility: private`, `published: false`. Recorded in `candidates/noaa-tide-flooding/record.json` (`jobs` for
`noaa-hf-001`) and `.factory/noaa-hf-001/`.

## 2026-09-20 11:55 UTC - noaa-004: a gate-passing rebuild that was not adopted, and the HF half relaunched

**`noaa-004` succeeded** (staging release 392410743, 19 assets, 27.9 minutes, exit 0, worker 166613240
destroyed at 11:53:09Z). It was launched at 11:04:32 by a concurrent coordinator session that also
renamed the target column `late` -> `minor_flood` in `build.py` and `persistence_baseline.py`, left the
edit uncommitted, recorded no reason for it, and then ended (its session closed at 11:05, so the intent
could not be recovered from anywhere). The rebuild is complete and gate-clean:

| check | noaa-004 |
| --- | --- |
| coverage | 122/122 stations, 2440/2440 station-years, 0 missing, 0 errors |
| rows / positives | temporal 697,373/11,774, 89,038/1,815, 88,841/2,850 - station_disjoint 461,580/7,513, 29,930/788, 29,930/1,090 |
| gates | both levels `ok`, 32/32 checks, `failed_checks: 0`, gate 1.3.0, `QUALIFICATION PASSED` |
| artifact versions | temporal `bb051dc304a4ee63`, station_disjoint `92297a5b62f86b29`, combined `fb49f932c7b4ea5a` |

**Its artifact is not the released one, and was not adopted.** Two differences from the shipped
artifact (noaa-003, artifact versions `8896c4423c53cb14` / `e6aff23f394ddfe4`, combined `a5a5ac5b41db1978`):

1. **The target column is renamed.** The released artifact, `release/noaa-tide-flooding/code/build.py`,
   `DATA_DICTIONARY.md`, `card.md` and `hf/job-002.json` all name it `late`. Adopting the rename means
   re-doing a release that is already gate-passed, consumer-verified on the published bytes and uploaded
   to Hugging Face, so the change was **reverted** and its diff kept at
   `candidates/noaa-tide-flooding/noaa-004-label-rename.diff`. Candidate sources now hash identically to
   the released package copies (`build.py` `5058314226d1e005`, `persistence_baseline.py`
   `d5ff90a15e77bd4c`) and to what noaa-003 bundled.
2. **NOAA revised the observations between the two pulls.** The rebuild is not byte-identical even
   though the code is: temporal/train offset 43912723, station 8661070 (Springmaid Pier) 2008-10-12
   `observed_max_ft` 35.427 -> 35.426 and 2008-10-13 -1.323 -> -1.324 with `trailing7_mean` 34.722 ->
   34.7219 and `trailing30_mean` 35.4425 -> 35.4424. Every file's byte size moved by more or less than
   the 7-byte header change (+12, +11, +9, +7, +5, +9), so each of the six carries at least one revised
   row; 200-byte needles at 250 KB intervals found nothing else in 135 sampled windows, so the revisions
   are sparse. Compared through byte-range reads of the staging assets - no bulk download on the
   coordinator. Recorded as `measurements.rebuild_not_byte_reproducible`: the release pins an artifact
   version, and a re-pull is a **new** artifact needing its own gate report and its own release.

**The worker slot is now used.** `noaa-hf-002` was planned (clean, EUR 0.45 reservation) and launched at
11:53:15Z (worker 166615899, cpx42, hel1) - the Hugging Face bulk move plus the per-config loading check
that `noaa-hf-001` died before performing. It is running; the watcher will report it.

**One hygiene fix, in the same commit.** Tracking the fetch bundle made CI's job-id uniqueness
check fail: the older rebuild-and-measure baseline bundle under `baseline/source/` had been bumped to
`noaa-baseline-002` on 2026-09-20 for a rerun that was never launched, so the id collided with the fetch
variant that actually ran. That stale bundle is renamed `noaa-baseline-rebuild-001` with a note explaining
why; the fetch variant keeps 002, which is the job the record describes.

**Recorded**: `candidates/noaa-tide-flooding/record.json` (`jobs` -> `noaa-004`, the
`rebuild_not_byte_reproducible` measurement, a rewritten `next_action`), the rename diff, `jobs/noaa-004.json`,
and `.factory/noaa-004/` (result plus the hash-checked reports). Next action: collect `noaa-hf-002`, read
`hf_loading.ok` and every per-config count, then `scripts/hf-publish.py --verify --candidate noaa-tide-flooding`,
then `--tag` last, then `check-package.py`. Both destinations remain private; no `DESTINATIONS.json` exists.
Still the operator's: whether to take the `minor_flood` rename and re-release at all.

## 2026-09-20 12:00 UTC - noaa-hf-002: the Hugging Face half is done, verified and tagged

**`noaa-hf-002` succeeded** (staging release 392416227, worker 166615899, launched 11:53:15Z, collected
11:59Z) and the release now exists on **both** destinations, verified on both.

| step | result |
| --- | --- |
| bulk move | 0 uploaded, **10 skipped** - every file already at the manifest digest, which independently confirms that `noaa-hf-001`'s upload had landed before its verifier crashed |
| loading check | `ok: true`, `problems: []`, both configs loaded **by name** and every split compared: temporal 697,373/11,774, 89,038/1,815, 88,841/2,850; station_disjoint 461,580/7,513, 29,930/788, 29,930/1,090 - the counts the manifest declares |
| `hf-publish.py --verify` (here) | `ok: true`, ten of ten paths at the manifest sizes, four large CSVs digest-verified by the Hub, eight small files present, no missing, no size mismatch |
| `--tag` (last) | `v2026.09` created **after** verification; tag commit `ee6ba8477e2be021a4000d88c03bd58d038e9a5f` == `main`, `tag_matches_main: true` |
| `check-package.py` | OK (its `DESTINATIONS.json` note is the same informational one Austin carries) |

`release/noaa-tide-flooding/DESTINATIONS.json` now records the Hugging Face destination: repo
`earino/noaa-tide-flooding`, revision `v2026.09`, `private: true`, `verified: true` at
2026-09-20T12:00:16Z, ten files, loading check attributed to the worker report. The manifest still
derives `visibility: private`, `published: false` - regenerating it belongs to the publication act, not
to verification. **Nothing is public.**

**Mechanically the release is complete on both destinations.** What is left is the operator's, and it is
now spelled out in `candidates/noaa-tide-flooding/record.json.next_action`:
(1) authorise publication on both destinations - flip visibility, prove it from an anonymous client,
record it in `DESTINATIONS.json` *before* regenerating the manifest, refresh card/LOADING.md/README/release
notes, then the website step; (2) the `late` -> `minor_flood` rename decision (noaa-004's artifact is kept
in staging 392410743 and its diff at `candidates/noaa-tide-flooding/noaa-004-label-rename.diff`); (3) the
persistence-floor question (0.8265/0.8454 against 0.8638/0.8688); (4) the fact that two coordinator
sessions drive this one ledger - `noaa-004` was launched by one while another was mid-step.

**Recorded**: `record.json` (`jobs` -> `noaa-hf-002`, and an `artifacts[0].huggingface` block with the tag,
its commit, the verified file list and the loading-check counts), `release/noaa-tide-flooding/DESTINATIONS.json`,
`jobs/noaa-hf-002.json`, `.factory/noaa-hf-002/` (result, hash-checked report manifest, source bundle). Worker
166615899 destroyed; the noaa-004 worker was already destroyed and 404s at the provider.

### The GitHub side's tag and main are separate histories - found while checking the release

Finishing the Hugging Face half meant checking the rule on the GitHub side too, and it does not hold
there. In `earino/noaa-tide-flooding`, `v2026.09` -> `9bcbf2c6` (parents 0) and `main` -> `f384889f`
(parents 0): two unrelated root commits, and a compare of them answers *404 "No common ancestor"*. Both
trees carry the same 14 package paths, but six blobs differ (`MANIFEST.json`, `README.md`,
`RELEASE_NOTES.md`, `REPRODUCE.md`, `VERIFICATION.md`, `measurements.json`) - and each of those six on
`main` is byte-identical to `release/noaa-tide-flooding/` (`main` MANIFEST.json blob
`ad66967155fdf860`), so `main` is the verified document set while the tagged commit still carries the
pre-consumer-check versions. Austin's repository has the intended shape (its tag is an ancestor of
`main`: `behind_by 0`, `ahead_by 3`), so this is specific to the order in which this repository's first
docs commit was created after its tag.

**The released data is unaffected**: the ten assets hang off release 392387511 and were re-verified from
the API against the transferred digests; the tag's tree holds documents, not CSVs. `check-package.py` is
OK and the consumer check ran against those assets.

**No ref was changed here.** The clean repair is one fast-forward commit with parents
`[f384889f, 9bcbf2c6]` and `f384889f`'s tree, then moving `main` to it: `main`'s content is unchanged
byte for byte, `v2026.09` becomes an ancestor of `main`, no force-push and no asset move. It belongs with
the publication decision, because that act already regenerates `MANIFEST.json` and refreshes the
documents - this should be settled before it, not during it. Evidence in
`candidates/noaa-tide-flooding/record.json` (`artifacts[0].github_tag_state`); it also corrects this file
at line 1755, which assumed the tagged commit carried the current docs.


## 2026-09-23 08:10 UTC - md-sewer-overflow: the registry blocker is answered, the rosters are partial

The only candidate whose blocker was Scout's own work rather than the operator's was
`md-sewer-overflow`, so this session spent itself on its recorded next action: does a facility
registry exist that is independent of the overflow reports? **Yes - measured three ways, none of
them exhaustive.**

| source | measured | covers the reports' keys |
| --- | --- | --- |
| EPA `npdes_downloads.zip` -> `ICIS_FACILITIES.csv` | 352,268,538 bytes, anonymous, `Range` -> **206**, 15 members, member 193,927,778 bytes uncompressed | filterable to `STATE_CODE=MD`; coverage unmeasured (336 MB pull = worker work) |
| MDE "Significant Wastewater Treatment Plants" (`2h5v-duyx`, `ct9h-nxwr`) | 76 rows, 76 distinct `npdes_id`, all Major POTWs | **40 of 322**; 36 roster facilities never report |
| MDE "Point Source Discharges" (`wdtu-5pbn`, `rwxr-95kt`) | 863 rows, 829 distinct `npdesid`, incl. 184 Waste Water Treatment Plant, 63 POTW, 2 CSO | **129 of 322** |

Also measured: the two series carry **126** and **247** distinct NPDES keys (**322** union); the
76-facility roster accounts for **1,024** reports (907 + 117) via `$where npdes in('MD...')`. That
`in(...)` form works, which **explains the 2026-09-21 HTTP 403s**: they tracked the quoted-literal
`between` form, not the host - so the outstanding 2023 reconciliation is a retry, not a blocked
route. Column names differ per dataset (`npdes`, `npdes_no`, `npdes_id`, `npdesid`) and a wrong one
returns `query.soql.no-such-column`, which reads like an empty dataset - the trap that compounded
those 403s. The EPA zip was inspected by **byte-range reads only** (EOCD + central directory); no
bulk data touched the coordinator, no worker was launched, no credential was used.

**The novelty check is now recorded**: `python3 scripts/check-novelty.py md-sewer-overflow ... 
--verdict differentiated` -> `ok: true` at 2026-09-23T08:08:06Z. Prior art models citywide CSO from
internal telemetry (DeepCSO), classifies pipe defects (Sewer-ML), or ships loose code
(tbep-tech/sso-dash, HamedGhodsi90/CSO_Real-Time_Prediction, AlexLipp/cso_scaling); Hugging Face
returns 0 datasets for both overflow queries.

**Still `parked`, with the blocker narrowed rather than cleared.** The roster exists, but its
coverage of the 322 reporting IDs is unmeasured, and split windows and base rates are unmeasured.
Dropping was wrong (a route exists) and `ready` would be a claim without coverage evidence.

**Recorded**: `candidates/md-sewer-overflow/record.json` (rewritten `rejection_reason`,
`next_action`, `open_questions`, three added sources, `measurements.registry_probe_2026_09_23`, the
novelty check), `notes.md`, and the six probes with their JSON results in `.factory/`.

**Next action.** Run the roster pull as a worker job - download `npdes_downloads.zip`, extract
`ICIS_FACILITIES.csv`, keep `STATE_CODE=MD`, stage the filtered roster - and measure how many of the
322 reporting NPDES IDs it covers. If it covers them, write the facility-day construction with the
GHCN-Daily rainfall features; if not, drop the candidate rather than construct a biased denominator.
Then redo the 2023 reconciliation with `$where npdes in(...)` and compute the split windows and base
rates. Nothing public, nothing released, no worker spend of any kind this session.
