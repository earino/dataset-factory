# Current state

Updated: 2026-09-18 (builder review after Scout's ninth entry; Austin CSV leakage
fix and portable offline checks).

## Objective

Prepare the first discovered prediction task for a monthly public release. Scout
runs on NousCloud with **1.9 GiB RAM and about 6 GB persistent disk**, coordinating
Docker jobs on temporary Hetzner workers. Each published dataset gets its own
public repository and versioned GitHub Release assets.

## Builder review of Austin construction (2026-09-18)

Reviewed Scout's `4f6d977` and ran its 59 tests locally. One failed outside UTC:
the unused `parse_iso` helper interpreted timezone-free source values in the host
timezone before converting them to UTC, moving a January 1 timestamp into the
previous year on the builder's machine. Removed the unused helper and its test;
the actual construction uses Socrata split predicates and preserves source
timestamp strings, so this changes no split boundaries or label values.

The review also found an answer leak in the emitted CSVs: `response_time` was in
`CARRY_COLUMNS`, even though it was absent from `FEATURES`. The existing benchmark
passes every non-target column to prediction code, so merely listing safe features
does not prevent an agent from reconstructing `late` from the raw response time.
The build now fetches `response_time` only to derive `late`, excludes it from all
three CSVs, and records the source column name in the manifest for provenance.
The opening task description now correctly starts the response interval when the
call was answered, rather than at dispatch.

Added an offline construction test that executes the CSV writer for all three
splits, checks the exact allowed columns, checks labels at 1200 and 1201 seconds,
and verifies the resulting manifests/checksums and category baseline. All **59
tests pass** on the builder's local timezone; the 20 Austin tests also pass under
`TZ=UTC`. This validation uses fixtures, not a full download or live worker.
The test loader also avoids writing bytecode into Austin's source directory, so a
normal test run cannot contaminate the worker bundle with `__pycache__`.

**Scout's next action:** pull the fix before the full Austin build and regenerate
any earlier sample CSVs intended for benchmark use. Continue the existing smoke
sequence once scheduled GitHub cleanup is verified. As checked at 12:40 UTC, the
last successful cleanup was still the manual dispatch; no enabled scheduled run
was present. No worker launch or policy change was made by the builder.

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

Nothing blocking. Both worker tokens and the worker SSH key are supplied and verified,
the allowance and allowed locations/types are configured, and notification delivery is
working. First release date, reviewer, public dataset namespace and website hosting can
wait until the first candidate is approved.

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
