# Hosted Scout inventory — 2026-09-17

Source: Scout's read-only report, supplied by the operator. This is the deployed
instance's evidence, not a claim about every Hermes installation.

Hermes **v0.21.3 (2026.9.14)**, upstream `345cd2b0`, platform-managed Docker install
at `/opt/hermes`; default profile; `HERMES_HOME=/opt/data`. Nonroot uid 10000, no
sudo, writable root `/opt/data`. Terminal backend is `local`, persistent shell.

- RAM: **1.9 GiB**, plus 1 GiB swap; about 1.1 GiB available during inspection.
- CPU: 4 vCPU. Subagents share these resources.
- Persistent disk: **5.9 GB**, about 5.0 GB free during inspection.
- Root overlay: 7.8 GB, ephemeral. Keep project state in `/opt/data`.

| Capability | Observed status |
|---|---|
| `web_search` | Working, Firecrawl through managed gateway |
| `web_extract` | Working for pages and JSON APIs; default 15k character budget |
| `browser_exec` / BrowserUse | Working remote browser; separate host/network; roughly 120s idle timeout |
| `terminal`, `process_manage` | Working local shell; no local Docker daemon |
| `cronjob_manage` | Working Chronos scheduling, including script/no-agent mode; no connected message destination |
| GitHub | Public reads work; no authenticated access, `gh`, token or connector |
| Hetzner | API reachable but unauthenticated; no token, `hcloud` or native integration |
| SSH | Client available; no keys or remote host configuration yet |
| Python | 3.13.5; stdlib works; `uv` available; our helper needs no third-party packages |
| Skills | 58 installed; GitHub skill requires absent `gh`; skills do not confer API access |
| Managed connectors | `manage_connections` returns 404; none configured |
| MCP | No consuming MCP configuration found |
| Disk cleanup | Active plugin cleans local ephemeral files, not cloud servers |
| Coordination | `delegate_task`, `todo_list`, `session_search`, `memory`, `desktop_project` available |

Deferred catalog: `cronjob_manage`, `image_generate`, `desktop_project`,
`session_search`, `process_manage`, `todo_list`. No additional cloud/storage tools.
Local Playwright usability is uncertain; use the working remote browser.

## Integration decision

Reuse native research, browsing, scheduling and memory. Fill the demonstrated
remote-compute gap with `factory/` and `workers/`: stdlib HTTP clients and SSH.
No `gh`, `jq`, `hcloud`, `paramiko`, `requests`, local Docker or ML installation
is required on Scout.

Supply GitHub access, a dedicated Hetzner project token, an SSH key, an explicit
compute allowance and independent cleanup before the live worker smoke test.
Notification delivery remains a separate setup item; local cron output does not
prove the operator received it.

Corrections to the initial suggestions: powering down a VM does not stop Hetzner
billing; GitHub has no separate release-upload-only token permission. Use
repository-scoped Contents write access for a dedicated private staging repo.
The coordinator's factory Git access should be separate from the worker token.
