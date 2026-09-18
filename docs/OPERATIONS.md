# Worker operations

Scout uses SSH and Python 3.11+ standard library. No new coordinator packages are
required. Workers install Docker and Python through cloud-init. No live cloud
cycle has yet been run with this implementation.

## Configure access and policy

Keep the project under `/opt/data` on Scout. Configure Git authentication for this
private factory repo using SSH or a credential helper; never embed tokens in remote
URLs. Supply environment variables or their `_FILE` variants:

- `HCLOUD_TOKEN`: read/write token for a dedicated Hetzner Cloud project.
- `FACTORY_GITHUB_TOKEN`: Contents write access to a **private staging repository**
  initialized with at least one commit. Prefer a separate repo such as
  `earino/dataset-factory-staging`, with a token restricted to that repo. The worker host
  receives this token; the job container does not. GitHub has no distinct
  release-upload-only permission. Workers do not need repository creation access.

Token files must have permissions `0600`; their directories should be `0700`.
Provision through the dashboard or private files, never chat or tracked files.
The helper reads tokens at runtime and does not load `.env` files automatically.

Scout verified that dashboard entries in `/opt/data/.env` do not reach its terminal
subprocesses on this deployment. Use these private token files:

```
/opt/data/.secrets/hetzner.token
/opt/data/.secrets/github-staging.token
```

The operator supplies the actual tokens. Scout may create the private directory
and configure paths. Do not copy its existing broad GitHub login into the staging
token file. That classic PAT has access beyond this project and must stay off
workers. Keep factory Git authentication separate. If the operator replaces it,
update both the dashboard `.env` entry and gh's stored login, verify Git access,
then revoke the old credential; do not rotate it as an incidental setup step.

For routine factory research commits a fine-grained factory-repo token needs
Contents read/write; Administration write is unnecessary. Add Workflows write only
if Scout will edit workflow files, and Actions write only if it will dispatch
workflows. Configuring Actions secrets/variables requires their corresponding
permissions or operator setup. The staging token needs only that staging repo's
Contents read/write (plus GitHub's automatic Metadata read access). See
[repository contents permissions](https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents),
[release permissions](https://docs.github.com/en/rest/releases/releases#create-a-release), and
[workflow dispatch permissions](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event).

Use the provided launcher for **both terminal and cron**, so no shell startup file
or Hermes restart is required to export the file paths:

```bash
cd /opt/data/dataset-factory
sh scripts/scout-factory doctor
sh scripts/scout-factory doctor --require-worker-credentials
```

`scripts/scout-factory` exports the two `_FILE` defaults on every invocation,
preserving explicit overrides. A nonempty direct token environment variable still
takes precedence. It does not source `.env`, display credentials or install tools.
`doctor` shows missing/empty/unreadable/insecure token files without disclosing
their contents or paths. The assertion exits nonzero if either worker credential
is unusable. It checks local presence/readability, **not API validity**. Missing
credentials also make worker commands fail explicitly; they do not silently pass.

`doctor.memory` measures Linux `MemAvailable`, total RAM and swap; it caps the
available estimate by visible cgroup-v2 headroom when available. Use this live
available figure when choosing research concurrency. The 1.9 GiB field under
`coordinator_constraints` records the hosted capacity, not free RAM. Unknown memory
on other systems stays unknown. These observations do not start a scheduler or
authorize local ML jobs.

Generate a dedicated SSH key in Scout's persistent home, register its public key
with Hetzner, and set `ssh_key_name` and `ssh_private_key` in the policy. First SSH
contact accepts a new host key into a job-specific known-hosts file; subsequent
connections check it. Workers use Ubuntu 24.04 with root key access.

Scout may generate a new ed25519 keypair under `/opt/data/.ssh` now, without
overwriting an existing key. Share only the public key for registration in the
dedicated Hetzner project. Keep the private key on Scout; registration and API
credentials remain prerequisites to launch.

Copy `config/worker.example.json` to ignored `config/local.json`. Set the operator's
monthly EUR allowance, allowed locations/types, lifetime, staging repo and SSH
paths. `server_types` maps each allowed type to its **hourly EUR ceiling including
VAT and primary IPv4**, for example `{"an-allowed-type": "0.10"}`. That is a policy
example, not a current price quotation. Launch checks live prices and refuses
unknown prices/currency. Only one active worker and one launching coordinator are
supported.

Reservation: `ceil((lifetime + cleanup grace) / 60) × hourly ceiling`. Completed
and failed jobs retain their reservation. Jobs crossing month boundaries reserve
in both months. Preserve `jobs/` and push it after operations; never launch from a
second checkout with a stale ledger.

This is a conservative admission policy, not a provider billing hard cap. Cleanup
can be delayed; transfer overages and other account charges are not included.
Review actual provider costs during the smoke cycle. Model inference has a
separate allowance that these helpers do not enforce.

## Configure cleanup before enabling launches

The included `.github/workflows/cleanup.yml` is the **primary expiry sweeper**,
because it runs independently of Scout. On-host no-agent cron is secondary:

1. Set this factory repo's Actions secret `HCLOUD_TOKEN` to the dedicated project token.
2. Set repository variable `FACTORY_PROJECT` to the policy's `project` value.
3. Set `FACTORY_CLEANUP_ENABLED=true` and manually dispatch the workflow once.
4. Scout checks the manual run, then observes a later successful run whose event
   is `schedule`. A skipped run or manual-only success is insufficient. Record
   both run URLs and UTC times in `STATE.md`. The operator checks Actions failure
   notifications reach a monitored channel; local Hermes output is not delivery.
5. Add the secondary no-agent cron, using the command below. Scout records its
   job identifier and first successful run. Keep the working directory fixed.
6. Set `cleanup_configured=true` and `enabled=true` only after the primary schedule
   is verified and the operator has set an allowance. Then run the smoke cycle.

### Sweep cadence and cleanup grace

The workflow runs **hourly at minute 17** (`17 * * * *`), with `workflow_dispatch`
retained for manual runs. Minute 17 is deliberately off the hour: GitHub documents
that the `schedule` event can be delayed during high load, and that the start of
every hour is a high-load period.

The daily deletion path is not this workflow. **Scout deletes each worker as part of
finishing the job, immediately after collecting its results.** The sweep exists to
catch leftovers: an interrupted session, a failed collection, a coordinator that
never came back. That distinction matters when reading a sweep's output, because
`deleted_servers` is normally empty when the normal path is working.

Because GitHub can delay scheduled runs - and may drop queued jobs entirely under
load - the hourly interval is **not a strict deletion deadline**. An expired worker
can therefore remain billable for longer than an hour.

`cleanup_grace_minutes: 60` makes the cost reservation account for that: a job is
reserved as `ceil((lifetime + grace) / 60)` hours, so a worker is charged up to an
extra hour of post-expiry billing in the admission check. The policy also uses
expiry plus grace as the window before an ambiguous ledger entry can be closed. This
remains a **conservative estimate, not a provider billing cap** - transfer overages
and charges outside the reservation are not covered.

Also use Scout's `cronjob_manage` script/no-agent mode to schedule:

```bash
sh /opt/data/dataset-factory/scripts/scout-factory worker sweep --project earino-dataset-factory
```

Run from the repo directory with the token available. Use the actual policy project
value. Native cron is useful redundancy, but a script running on Scout does not
cover loss of Scout's whole instance. GitHub schedules can also be delayed and
queued jobs can be dropped, so treat either sweep as a backstop rather than a
deadline. Neither cleanup invocation needs an LLM.

GitHub runs use the Actions secret directly; `_FILE` paths on Scout do not configure
GitHub. Research can proceed manually before notification delivery is connected.

The sweeper deletes expired servers with matching project/job labels and their
labeled, unassigned primary IPs. It rechecks server ownership before deletion and
refuses unexpected attached volumes. **Shutdown does not stop billing; deletion
is required.** Workers never receive the Hetzner token. Expiry may discard artifacts
if uploading failed; it takes precedence over keeping paid workers indefinitely.
Launch does not create volumes, snapshots or backups.

## First live smoke cycle

Copy `examples/smoke/` into a dedicated source-only directory under `candidates/`.
Set an allowed server type/location and a new job ID for each attempt. Hidden
files, caches, symlinks and bulk files are rejected; source is capped at 2 MiB and
content-hashed. Keep candidate notes/records outside this source directory.

```bash
sh scripts/scout-factory worker plan candidates/infra-smoke/source/job.json
sh scripts/scout-factory worker launch candidates/infra-smoke/source/job.json
sh scripts/scout-factory worker status smoke-001
sh scripts/scout-factory worker collect smoke-001
sh scripts/scout-factory worker destroy smoke-001
```

`plan` is offline. `launch` reserves cost and records the job before creating its
worker, waits for Docker readiness, dispatches a systemd job and returns. `collect`
returns `running` until a result exists. It then checks the private release, tag,
asset membership, sizes and GitHub SHA-256 digests without downloading artifacts.
`destroy` normally requires verified collection and confirms removal of the server
and remaining job IPs. Failed data jobs can also be collected and cleaned up after
their failure artifacts upload.

**Order matters: the first smoke cycle proves the normal path, which is
collect-then-delete-immediately.** Expiry cleanup is a *later, separate* test. Do not
gate the first launch on evidence that only an expired worker can produce - the only way
to create an expired worker is to launch one, so requiring that first would make the
cycle unreachable.

The first smoke job therefore exercises, in order: provisioning, Docker readiness, the
data job, a direct upload to the private staging release, **verified collection**, then
**immediate deletion of the server and its job-owned primary IP**. Nothing is left
running and nothing is left to expire. Record the artifact links, the reservation, the
estimated cost and the confirmed deletion.

Before unattended research, exercise these paths in this order and record evidence in
`STATE.md`:

1. **The normal path** - the smoke cycle above: collection followed by immediate
   deletion, with deletion confirmed by reading the server and IP back.
2. **Expiry cleanup, separately** - allow a tiny worker to expire while Scout is idle;
   confirm the independent sweeper deletes it, then reconcile with `status`. This is a
   distinct test with its own job, run only after the normal path has been proven.
3. **Interrupted session recovery** - lose the coordinator session after launch, then
   reconcile with `status`. Resume incomplete bootstrap with `worker resume ID
   --job-file PATH`, using identical source. Never bypass an unresolved creation by
   launching a new ID.
4. **A failing job** - run a command that exits unsuccessfully; collect logs and verify
   cleanup.

Record actual costs as well as functionality.

## Qualify the extract on the worker

Qualification reads the rows, so it runs **where the rows are**: on the worker, against the
full artifact, before anything is scored. `scripts/assemble-job.py` is the single assembly
point - it copies the candidate's `build.py` and `run.sh` plus the repository's
`qualify_dataset.py` into an ignored staging directory, generates `job.json`, and checks the
result against the bundle rules:

```bash
python3 scripts/assemble-job.py austin-911-response   # job id comes from source/job.json
sh scripts/scout-factory worker plan .factory/jobs/austin-002/job.json
sh scripts/scout-factory worker launch .factory/jobs/austin-002/job.json
sh scripts/scout-factory worker collect austin-002
sh scripts/scout-factory worker destroy austin-002
```

Each attempt gets a new job id in the candidate's `source/job.json` before assembling; the
assembler reads it from there rather than pinning one, so a re-run is a new ledger entry
instead of a reused one.

The entrypoint builds the extract, then qualifies it, and exits non-zero when the gate fails.
**A failed qualification still preserves diagnostics**: the gate report, its rendered output
and the extract itself are written under `/output`, which the worker uploads even on a
non-zero exit. Collect that evidence and then delete the worker as usual - a failed job is
still a job that must not stay billable.

**Require a passing report for the exact artifact version before scoring or acceptance.** The
gate writes `/output/qualification.json`, which records the SHA-256 of every shipped file and
a single `artifact_version` digest over them. Verify it against the collected extract:

```bash
python3 skills/dataset-qualification/scripts/qualify_dataset.py \
    --accept /path/to/qualification.json /path/to/extract
```

This fails on a report that did not pass, on a report written by a different gate version, and
on any file that changed after qualification. **Nothing may be scored, and no candidate may be
accepted, without it.** Only compact evidence comes back to Scout: the report, the rendered
checks and the manifest. The bulk extract stays in private staging.

## Cleanup cadence: what the two schedules actually guarantee

Two independent schedulers run the same command,
`python3 -m factory worker sweep --project "$FACTORY_PROJECT"`:

| scheduler | cadence | observed |
|---|---|---|
| On-host Hermes cron (`47 * * * *`) | **scheduled hourly** | fired every hour while this instance was up |
| GitHub Actions `schedule` | irregular, mean 4.24 h, max 6.63 h | 2.96, 2.19, 4.65, 4.77, 6.63 h |

**Neither is a guaranteed deletion deadline.** Both are best-effort sweepers:

- The on-host sweep is **scheduled hourly**. That is a schedule, not a promise. It only runs
  while this instance is alive, it can be missed, and it says nothing about how long an expired
  worker survives if the coordinator is down. Do not write "expired workers are deleted within
  an hour" anywhere - write "the on-host sweep is scheduled hourly".
- The GitHub trigger cannot be described even as hourly: measured gaps are 2.2-6.6 hours
  against a `17 * * * *` cron, and GitHub documents scheduled workflows as delayed on
  low-activity repositories, so it is a **multi-hour** path.

The two exist together because they fail differently: the cron is frequent but dies with this
instance; GitHub is slow but survives the instance being gone entirely. Deleting an expired
worker is therefore bounded by whichever runs first after expiry, and by nothing at all if both
stop - which is why the ledger, not the sweeper, is the record of what was created.

Observed scheduled execution (2026-09-18T16:31:37Z, run 35368993679, commit `3ba6988`): the
trigger fired, the cleanup step ran and succeeded, and `sweep` returned
`deleted_servers: []`, `deleted_primary_ips: []` - correct, as the smoke worker had already been
destroyed at 14:59. So the scheduled path is proven to **execute**; it had nothing to delete,
and deleting through it has not yet been observed.

## Transfer and fetch jobs: moving an artifact between repositories

Two optional job fields exist for moving already-built artifacts rather than building them:

```json
"fetch":    {"repo": "owner/name", "release": 123, "assets": [
                {"asset_id": 4, "dest": "task/public/train.csv", "size": 71546966, "sha256": "..."}]}
"transfer": {"source_repo": "owner/staging", "source_release": 123,
             "target_repo": "owner/dataset", "target_release": 456,
             "assets": [{"source_asset_id": 4, "target_name": "train.csv",
                         "size": 71546966, "sha256": "..."}]}
```

- Both run **host-side on the worker**; a transfer job starts no container, so it needs no
  `command` and no `image`.
- `fetch` downloads into `/opt/scout/cache`, which is mounted read-only at `/data` for the
  container. That is how a job measures the *released* bytes without the container ever holding a
  credential.
- `transfer` verifies each asset twice - on arrival against the recorded SHA-256, and after
  upload against the server's own digest - and deletes it locally, so peak disk is one asset, not
  the dataset.
- A **public** target repository is refused unless the job sets `allow_public: true`. Publishing
  is reviewed, so this is the last guard before something irreversible.

### The two credentials are separate on purpose

`FACTORY_GITHUB_TOKEN` (staging) is scoped to the staging repository and returns 404 on any other.
A transfer therefore needs `FACTORY_PUBLISH_TOKEN`, which is used **only** for the target write;
source reads still use the staging token. `plan` refuses a transfer job when that credential is
missing, so the failure happens before provisioning instead of on a paid worker.

Widening a worker's reach for the duration of a transfer is a real cost. A fine-grained token
limited to the target repository would be narrower than the account-wide one currently in use and
is the recommended replacement.

## Exception: the on-host sweep as the cleanup prerequisite (2026-09-18)

At the time this exception was granted, the `schedule` trigger had not fired for this
repository since enablement. Between the gate opening at 11:04Z and 14:04Z there were
**eleven consecutive hourly slots with no `schedule`-event run**, and 4.2 hours since the last
actual fire - longer than any gap observed before enablement. The workflow itself was verified
correct and active, and the manual `workflow_dispatch` still executed, so the gap was in
GitHub's scheduled trigger, not in our configuration. It subsequently fired at 16:31:37Z (see
the cadence section above); the exception below was written before that and its limits still
stand for the cycle it covered.

**For the supervised infrastructure smoke test only, the verified on-host sweep satisfies the
cleanup prerequisite.** The exception is narrow and stated as such:

- It applies to **one supervised smoke job**, run with an operator watching it through
  confirmed cleanup. It is not a general relaxation.
- The on-host sweep runs the **same command** as the GitHub workflow
  (`factory worker sweep --project earino-dataset-factory`) and has been observed executing
  successfully on an hourly cadence. Its weakness is that it dies with this instance, which is
  why the GitHub workflow remains the intended primary.
- **GitHub scheduled execution remains unverified.** Nothing below changes step 4's
  requirement; it is now recorded as an open verification item rather than a satisfied one.
- Launches are enabled for the duration of the smoke cycle and **disabled again immediately
  afterwards**, while cleanup stays active.

The next paid job after the smoke cycle needs either an observed `schedule` event or a fresh
operator decision. Do not treat this exception as standing.

## Recovery and data flow

Containers receive read-only `/workspace` and writable `/output`. Write a small
`/output/summary.json` for metrics. CPU, memory, process and runtime limits apply.
Disk usage is polled every three seconds with a low-space stop: this is a monitored
limit, not a filesystem quota. Images and the OS need additional room. Use public
images, preferably pinned by digest; the resolved image identity is recorded.
Containers receive neither the Docker socket nor cloud credentials.

After execution, the host uploads outputs, bounded logs and the source bundle
directly to a private draft release tagged `job-ID`. Files over 1 GiB stream as
numbered parts without making another full copy. `manifest.json` records original
paths, offsets, sizes, SHA-256 hashes and URLs. Concatenate parts in offset order
to reconstruct each file. Upload retries reconcile ambiguous responses and never
overwrite a different completed asset.

Scout accepts reports up to 256 KiB and keeps at most 20 MiB of collected reports
in `.factory/`. Job records also retain compact results. Archive local report
copies after their durable records are committed. Bulk data never passes through
Scout. Up to 399 data parts plus the manifest fit in a release; archive many small
files on the worker first.

For failed transfers while time remains, `worker retry-upload ID` reuses the
preserved execution result and never reruns the data job. Then check `collect`.
After expiry, inspect the staging repo's `job-ID` draft release for preserved
assets; a partial upload is not a verified result. If creation stayed ambiguous
but no server exists after expiry plus grace, `status` closes the ledger entry
while retaining its reservation.

These helpers target private staging only. Public dataset publishing is a later
reviewed step; see `templates/dataset/README.md` for the content checklist.

## Reference contracts

- [Hetzner API](https://docs.hetzner.cloud/reference/cloud): pricing, servers, IPs and actions.
- [Hetzner billing](https://docs.hetzner.com/cloud/billing/faq/): powered-off servers remain billable.
- [GitHub release assets](https://docs.github.com/en/rest/releases/assets): uploads, digests and permissions.
- [Release limits](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases#storage-and-bandwidth-quotas): each asset must be under 2 GiB.

Checked 2026-09-18. Local fake-provider tests do not verify live credentials,
VM boot, hosted schedules or upload throughput.
