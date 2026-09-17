# Inventory Scout's actual capabilities first

The initial inventory is complete: see [Scout's report](../deployment/capabilities.md).
Use this procedure again when capabilities or deployment change.

The public documentation describes the platform. It does not prove which tools
are enabled, connected, permitted, or working on this particular hosted instance.

Before installing packages or writing cloud clients, inventory the capabilities
Scout can actually reach. Save a compact report as `deployment/capabilities.md`
with the Hermes version, date, and evidence for each finding.

## Assignment for the hosted agent

Inspect your tools, skills, plugins, managed connectors, and terminal environment.
Use read-only discovery and inspection. Do not create cloud resources, change
configuration, install plugins, or publish anything as part of this inventory.
Report connection status and missing access, never credential values.

Check these capabilities:

| Need | What to establish |
|---|---|
| Source research | Working search, page extraction, and cloud browser tools |
| GitHub | Repository access, commits, releases, and large-asset uploads |
| Hetzner | Discovery of any provision/status/delete integration or usable CLI |
| Remote jobs | SSH, Docker-on-remote-host support, process monitoring |
| Artifacts | Direct worker-to-release uploads without copying through Scout |
| Scheduling | Project-scoped recurring work and cleanup independent of a research turn |
| Persistent state | Repository location, writable persistent paths, usable disk space |

If tool search is available, search the deferred catalog and managed connectors:
try specific queries such as `Hetzner`, `GitHub releases`, `upload release asset`,
`SSH remote command`, and `cloud server`. Inspect matching tool schemas. A miss
from one query is not proof the capability is absent; inspect the available
sources and retry a simpler relevant query.

Available CLI inspection commands may include `hermes --version`, `hermes status`,
`hermes portal info`, `hermes portal tools`, and plugin/skill listing commands.
Use installed help to confirm syntax. Summarize their output without copying
secrets or dumping whole configuration files. Do not run interactive setup or
enablement commands merely to inspect the environment.

For each capability, distinguish **verified working**, **present but untested**,
**available but needs connection**, **not found**, and **unknown**. Name the tool,
plugin, connector, or client and the exact operation that is available.

Conclude with the smallest set of missing pieces we need to build. Keep Hetzner
as the planned worker provider; finding another cloud backend is useful context,
not authorization to change the deployment provider or spend money.

## What the docs establish (checked 2026-09-17)

- [Nous Tool Gateway](https://hermes-agent.nousresearch.com/docs/user-guide/features/tool-gateway)
  provides managed search/extraction and cloud browser automation. Cloud browsing
  can keep the browser workload off the small coordinator.
- [Tools and toolsets](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools)
  include terminal/file tools, scheduling, memory, and programmatic tool calls.
- [Tool Search and connectors](https://hermes-agent.nousresearch.com/docs/user-guide/features/tool-search)
  discover deferred MCP/plugin tools and managed remote tools for connected accounts.
- [Terminal configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration#ssh-backend)
  includes SSH and cloud execution backends. Hosted availability needs inspection.
- [Plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)
  and [skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)
  supply reusable integrations and procedures. Catalog presence is not the same
  as installed, enabled, and authorized access.
