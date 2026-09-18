# Current state

Updated: 2026-09-18 (second entry; hosted research session).

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

Remaining prerequisites for a paid launch: worker SSH key registration in the
Hetzner project, the Actions cleanup secret/variable and enablement flag, an
allowance with allowed server types and locations, and cleanup verification.

## Research shortlist recorded 2026-09-18

Five candidates created with measured evidence in `candidates/<id>/record.json`
and `notes.md`. All numbers below were measured live on 2026-09-18 through
anonymous public APIs; none is a scored result.

| Candidate | Domain | Scale measured | Licence | Status |
|---|---|---|---|---|
| `austin-911-response` | public-safety operations | 1,049,636 calls, 2023-2026 | Public Domain | **lead** |
| `chicago-doah-adjudication` | administrative adjudication | 823,637 rows, 2008-2027 | See Terms of Use | runner-up, licence review needed |
| `noaa-tide-flooding` | coastal water levels | 302 stations, all with flood thresholds | public domain (US Gov) | shortlisted |
| `melbourne-pedestrian-counts` | urban activity sensing | 1,621,901 hourly records | unconfirmed | shortlisted |
| `md-sewer-overflow` | wastewater infrastructure | 27,479 events, 2005-2023 | Public Domain | lower priority; series may be stale |

Lead choice: `austin-911-response`, because its licence is explicitly Public Domain
while Chicago's is "See Terms of Use", and the project must publish publicly.
Remaining work on the lead is technical, not legal: confirm the `response_time`
derivation, exclude the post-hoc columns listed in its notes, measure the
`response_time` distribution, freeze threshold T from the training window, and split
temporally by `response_datetime`.

No baseline, AUC, headroom figure or acceptance verdict has been measured. Nothing
here should be read as a result.

## Still unverified or unimplemented

Local tests use fake providers. **No live Hetzner/GitHub worker cycle has been run.**
Boot, SSH, Docker, uploads, recovery, costs and scheduled deletion remain unverified.
Worker policy stays disabled at zero allowance.

The benchmark adapter (`factory/bench.py` coordination, `workers/benchmark.py`
execution), qualification tools, public exporter and website are not implemented.
`../harness_benchmark` is unmodified.

The cleanup workflow is still skipped: `FACTORY_CLEANUP_ENABLED`, `FACTORY_PROJECT`
and the `HCLOUD_TOKEN` Actions secret are unset, so no manual or scheduled run has
been observed. Notification delivery is unconfigured.

## Next actions for Scout

1. Finish the lead candidate's construction script: confirm the `response_time`
   derivation and `mental_health_flag` timing from the dataset's column docs, then
   encode the dispatch-time-only feature list and the threshold protocol.
2. Continue shortlist work that needs no credentials: confirm the Melbourne licence,
   verify the 2023+ Maryland overflow dataset, and measure NOAA per-station
   exceedance base rates from bounded samples.
3. Operator: register the worker public key with Hetzner and set the allowed
   server types and locations with an allowance. Worker credentials are already in
   place and `doctor --require-worker-credentials` passes.
4. After that: verify the primary GitHub Actions cleanup with a manual and a
   scheduled successful run, add the secondary on-host cron sweep, run the live
   smoke cycle, and only then enable paid launches.

## Inputs still needed from the operator

Worker SSH key registration, compute/inference allowance with allowed server
types and locations, cleanup secret/variable setup and a notification destination.
Both worker tokens are supplied and verified. First release date, reviewer, public
dataset namespace and website hosting can wait until the first candidate is
approved.
