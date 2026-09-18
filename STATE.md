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
3. Operator: supply `/opt/data/.secrets/hetzner.token` and
   `/opt/data/.secrets/github-staging.token`, register the worker public key with
   Hetzner, configure the cleanup secret/variable, and set an allowance. Then
   re-run `doctor --require-worker-credentials`.
4. After that: verify the primary GitHub Actions cleanup with a manual and a
   scheduled successful run, add the secondary on-host cron sweep, run the live
   smoke cycle, and only then enable paid launches.

## Inputs still needed from the operator

Restricted staging token, dedicated Hetzner project token, worker SSH key
registration, compute/inference allowance, cleanup secret/variable setup and a
notification destination. First release date, reviewer, public dataset namespace
and website hosting can wait until the first candidate is approved.
