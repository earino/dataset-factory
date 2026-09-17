# Dataset Factory

A persistent research project that discovers real-world prediction tasks and
publishes fresh datasets and agent/harness evaluation findings each month.

Start with [the project specification](PROJECT.md). It describes the agreed
direction, proposed starting defaults, and the path to a first release.

A dedicated Hermes agent named **Scout** works from this repository. Start its
first session with [the handoff](docs/HANDOFF.md), [agent instructions](AGENTS.md),
and [current state](STATE.md).

The always-on agent has 1.9 GiB RAM on NousCloud for research and coordination.
It provisions temporary Hetzner workers for data processing and experiments in
Docker, collects their results and artifacts, and deletes the workers afterwards.
Scout has only **6 GB of disk**: keep bulk data, Docker images, and ML environments
on workers. The [hosted inventory](deployment/capabilities.md) confirms working
search, extraction, a remote browser and scheduling. These remain Scout's tools.

The starter kit includes the research assignment, candidate records and a worker
lifecycle using Python's standard library and SSH. It uploads directly to private
GitHub Releases and includes independent expiry cleanup. Paid launches are disabled
until configured; the live cloud smoke test is still outstanding. See
[worker operations](docs/OPERATIONS.md).

Run these with Python 3.11+; no Python dependencies are needed:

```bash
python3 -m factory doctor
python3 -m factory candidate create my-first-lead
python3 -m factory candidate list
python3 -m unittest discover -s tests -v
```

The first assignment is [discover and construct one usable task](docs/FIRST_ASSIGNMENT.md).
Missing compute credentials do not block source research.

Dataset qualification, the benchmark adapter, public release automation and the
website come after the first worker cycle and discovery. Their intended behavior
is specified in `PROJECT.md`; they are not implemented yet.

This repository is intended to be private. Each published dataset gets its own
public GitHub repository for code and documentation, with the data attached to
versioned GitHub Releases. The website collects the monthly releases and findings
and links to those dataset repositories and downloads.

[The original dataset factory spec](dataset-factory-spec.md) remains available as
technical reference material. `PROJECT.md` takes precedence where the revised
direction differs from it.

The existing benchmark is a separate dependency at `../harness_benchmark` in the
local workspace. That checkout must remain unmodified.
