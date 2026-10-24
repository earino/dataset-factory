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

The repository includes the research assignment, candidate records and a worker
lifecycle using Python's standard library and SSH. It uploads directly to private
GitHub Releases and includes independent expiry cleanup. Worker launches require
configured credentials, budget and lifetime limits. See
[worker operations](docs/OPERATIONS.md).

Run these with Python 3.11+; no Python dependencies are needed:

```bash
python3 -m factory doctor
python3 -m factory candidate create my-first-lead
python3 -m factory candidate list
python3 -m unittest discover -s tests -v
```

On hosted Scout, use `sh scripts/scout-factory doctor` to supply the documented
private token-file paths in terminal and cron shells. Add
`--require-worker-credentials` for an offline credential presence assertion.
See the [2026-09-18 builder reply](deployment/BUILDER-REPLY.md) for the current
setup decisions and next actions.

The first assignment is [discover and construct one usable task](docs/FIRST_ASSIGNMENT.md).
Missing compute credentials do not block source research.

Construction, qualification, dual-platform releases and website publication are
implemented. Read [prediction contracts and suitability](docs/PREDICTION-CONTRACT.md)
before building or evaluating a task. New artifacts must declare their intended use,
input availability, source vintage, selection rule and evaluation access. Verified
historical forecasting requires full-row availability evidence; retrospective research
may retain explicit timing assumptions.

Every release has an exact-artifact review in `suitability/`. Current notices on
dataset websites and GitHub/Hugging Face documentation come from those records;
frozen data and version tags are preserved. The chronological scoring adapter installs
only into an owned execution copy of the existing harness. Its worker integration
status is recorded in [current state](STATE.md); unit tests alone do not establish it.

This repository is intended to be private. Each published dataset gets its own
public GitHub repository for code and documentation, with the data attached to
versioned GitHub Releases. The website collects the monthly releases and findings
and links to those dataset repositories and downloads.

[The original dataset factory spec](dataset-factory-spec.md) remains available as
technical reference material. `PROJECT.md` takes precedence where the revised
direction differs from it.

The existing benchmark is a separate dependency at `../harness_benchmark` in the
local workspace. That checkout must remain unmodified.
