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
  `dataset-factory-staging`, with a token restricted to that repo. The worker host
  receives this token; the job container does not. GitHub has no distinct
  release-upload-only permission. Workers do not need repository creation access.

Token files must have permissions `0600`; their directories should be `0700`.
Provision through the dashboard or private files, never chat or tracked files.
The helper reads tokens at runtime and does not load `.env` files automatically.

Generate a dedicated SSH key in Scout's persistent home, register its public key
with Hetzner, and set `ssh_key_name` and `ssh_private_key` in the policy. First SSH
contact accepts a new host key into a job-specific known-hosts file; subsequent
connections check it. Workers use Ubuntu 24.04 with root key access.

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

The included `.github/workflows/cleanup.yml` runs independently of Scout:

1. Set this factory repo's Actions secret `HCLOUD_TOKEN` to the dedicated project token.
2. Set repository variable `FACTORY_PROJECT` to the policy's `project` value.
3. Set `FACTORY_CLEANUP_ENABLED=true` and manually dispatch the workflow once.
4. Verify it succeeds and its 15-minute schedule runs. Enable failure notifications
   or another monitored notification channel.
5. Set `cleanup_configured=true` and `enabled=true` in the local policy only after
   confirming cleanup and the operator's allowance.

Also use Scout's `cronjob_manage` script/no-agent mode to schedule:

```bash
python3 -m factory worker sweep --project earino-dataset-factory
```

Run from the repo directory with the token available. Use the actual policy project
value. Native cron is useful redundancy, but a script running on Scout does not
cover loss of Scout's whole instance. GitHub schedules can also be delayed; monitor
them. Neither cleanup invocation needs an LLM.

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
python3 -m factory worker plan candidates/infra-smoke/source/job.json
python3 -m factory worker launch candidates/infra-smoke/source/job.json
python3 -m factory worker status smoke-001
python3 -m factory worker collect smoke-001
python3 -m factory worker destroy smoke-001
```

`plan` is offline. `launch` reserves cost and records the job before creating its
worker, waits for Docker readiness, dispatches a systemd job and returns. `collect`
returns `running` until a result exists. It then checks the private release, tag,
asset membership, sizes and GitHub SHA-256 digests without downloading artifacts.
`destroy` normally requires verified collection and confirms removal of the server
and remaining job IPs. Failed data jobs can also be collected and cleaned up after
their failure artifacts upload.

Before unattended research, exercise these paths and record evidence in `STATE.md`:

- Lose the coordinator session after launch, then reconcile with `status`. Resume
  incomplete bootstrap with `worker resume ID --job-file PATH`, using identical
  source. Never bypass an unresolved creation by launching a new ID.
- Run a command that exits unsuccessfully; collect logs and verify cleanup.
- Allow a tiny worker to expire while Scout is idle; confirm independent cleanup,
  then reconcile with `status`. Record actual costs as well as functionality.

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

Checked 2026-09-17. Local fake-provider tests do not verify live credentials,
VM boot, hosted schedules or upload throughput.
