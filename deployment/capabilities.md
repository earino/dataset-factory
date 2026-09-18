# Hosted Scout inventory — updated 2026-09-18

Source: Scout's initial read-only inventory and 2026-09-18 execution report,
supplied by the operator. This is deployed-instance evidence, not a claim about
every Hermes installation. Repository setup observations by the builder are
identified separately below.

Hermes **v0.21.3 (2026.9.14)**, upstream `345cd2b0`, platform-managed Docker install
at `/opt/hermes`; default profile; `HERMES_HOME=/opt/data`. Nonroot uid 10000, no
sudo, writable root `/opt/data`. Terminal backend is `local`, persistent shell.

- RAM: **1.9 GiB**, plus 1 GiB swap; about **895 MiB available** in the latest report.
- CPU: 4 vCPU. Subagents share these resources.
- Persistent disk: **5.9 GB**; doctor reported **4.48 GiB free** on 2026-09-18.
- Root overlay: 7.8 GB, ephemeral. Keep project state in `/opt/data`.

| Capability | Observed status |
|---|---|
| `web_search` | Working, Firecrawl through managed gateway |
| `web_extract` | Working for pages and JSON APIs; default 15k character budget |
| `browser_exec` / BrowserUse | Working remote browser; separate host/network; roughly 120s idle timeout |
| `terminal`, `process_manage` | Working local shell; no local Docker daemon |
| `cronjob_manage` | Working Chronos scheduling, including script/no-agent mode; no connected message destination |
| GitHub | Authenticated as `earino`; clone, push, remote branch deletion, repo/release/run listing verified; `gh` v2.101.0 installed |
| Hetzner | API reachable but unauthenticated; no token, `hcloud` or native integration |
| SSH | Client available; no keys or remote host configuration yet |
| Python | 3.13.5; stdlib works; `uv` available; our helper needs no third-party packages |
| Skills | 58 installed; GitHub skill's `gh` prerequisite now present; specific skill workflows not all exercised |
| Managed connectors | `manage_connections` returns 404; none configured |
| MCP | No consuming MCP configuration found |
| Disk cleanup | Active plugin cleans local ephemeral files, not cloud servers |
| Coordination | `delegate_task`, `todo_list`, `session_search`, `memory`, `desktop_project` available |

Deferred catalog: `cronjob_manage`, `image_generate`, `desktop_project`,
`session_search`, `process_manage`, `todo_list`. No additional cloud/storage tools.
Local Playwright usability is uncertain; use the working remote browser.

## Verified hosted setup changes

- `gh` is at `/opt/data/.local/bin/gh`, about 41 MB; Scout verified its published
  SHA-256 before installation. Fresh shells resolve it through configured PATH.
- `gh auth setup-git` supplies Git credentials. Login is stored in
  `~/.config/gh/hosts.yml` (0600); the existing dashboard token also remains in
  `/opt/data/.env`. It is a broad classic PAT including repo, workflow and org
  administration scopes. Any deliberate rotation must handle both copies.
- `/opt/data/dataset-factory` was clean on `main` at `a9da074`; Scout pushed and
  deleted a throwaway branch and observed successful CI. No candidate records or
  source investigations had been started as of the report.
- `/opt/data/harness_benchmark` is a read-only, unmodified clone (108 MB). It has
  preparation scripts for airline/fraud/credit and saved baselines, but no prepared
  datasets. Build those only on workers. This differs from the builder's local data.
- Scout ran all 22 original unit tests successfully under Python 3.13.5. `uv`
  0.11.6 and OpenSSH 10.0p2 are present; `.ssh` and local worker policy are absent.
- Dashboard `.env` entries do not appear in terminal subprocesses. Use the explicit
  `_FILE` launcher documented in `docs/OPERATIONS.md`; don't rely on shell startup.
- Worker credentials, SSH registration, budget and cleanup configuration remain
  missing. Cleanup workflow runs are skipped because its enablement variable is
  unset. Notification delivery remains unconfigured.

Builder follow-up: created private `earino/dataset-factory-staging` with an initial
README commit. No staging token, Hetzner token or paid worker has been created by
the builder. The new doctor/launcher changes must still be pulled and run on Scout.

## Integration decision

Reuse native research, browsing, scheduling and memory. Fill the demonstrated
remote-compute gap with `factory/` and `workers/`: stdlib HTTP clients and SSH.
No `gh`, `jq`, `hcloud`, `paramiko`, `requests`, local Docker or ML installation
is required on Scout.

Factory GitHub access is resolved. Supply a separate staging token, a dedicated
Hetzner project token, an SSH key, an explicit compute allowance and independent
cleanup before the live worker smoke test.
Notification delivery remains a separate setup item; local cron output does not
prove the operator received it.

Corrections to the initial suggestions: powering down a VM does not stop Hetzner
billing; GitHub has no separate release-upload-only token permission. Use
repository-scoped Contents write access for a dedicated private staging repo.
The coordinator's factory Git access should be separate from the worker token.
