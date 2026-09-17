# Dataset Factory — project specification

**Status:** working draft, 2026-09-17. The project direction comes from the operator's
conversation; the starting defaults and deployment choices below remain proposals.

## Purpose

Produce a monthly public release of fresh, real-world prediction tasks and findings
from using them to evaluate coding agents, models, and harnesses.

A dedicated Hermes agent, running persistently through the operator's NousCloud
setup, does the ongoing searching, investigation, data construction, and drafting.
This repository gives it instructions, durable project state, and reliable tools.
The deployed agent has 1.9 GiB RAM and coordinates temporary Hetzner workers
for substantial data processing and benchmark experiments, using Docker for jobs.

The first audience is the operator and collaborators. They run experiments with
the existing benchmark. Other researchers can download the published tasks and
reproduce the work.

## What a release contains

Each release includes one or more new tasks, each with:

- A clear prediction question, target definition, and description of the data.
- Train, eval, and holdout files, or reproducible acquisition instructions where
  source permissions require that form of distribution.
- Construction scripts, source references, recorded input checksums, and versions.
- Baseline results, task checks, and the group's completed harness experiments.
- A readable account of what was discovered and what the experiments showed.
- Instructions for using the task with the existing runner.

The holdout may be published. During an evaluation run, it must stay outside the
evaluated agent's workspace and be used only for scoring. Public availability and
visibility inside a run are separate concerns.

The website presents the latest monthly release, a browsable archive, downloads,
findings, and reproduction instructions. A monthly release points to specific
versions of its datasets. The initial product does not require a submission
service or hosted evaluations for visitors.

## Repositories and dataset downloads

Use this private repository for the agent's instructions, ongoing research,
candidate drafts, shared tools, and monthly publication planning. Give each
published dataset its own public GitHub repository.

Each dataset repository contains its description, construction code, dependencies,
metadata, source and license information, and reproduction instructions. It must
be usable without access to the private factory repository or the agent's memory.

Attach the data to tagged GitHub Releases in that dataset's repository. A release
can contain a compressed archive of the prepared task, including train, eval,
holdout, and metadata, plus a checksum manifest. Unpacking it should produce the
layout the existing runner consumes. Split the download into multiple assets when
needed; keep large data files out of Git history.

GitHub currently requires each release asset to be **under 2 GiB**. This is a
per-file limit, so train, eval, and holdout can be separate compressed assets if
necessary. See [GitHub's release limits](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases#storage-and-bandwidth-quotas)
(checked 2026-09-17). GitHub Releases is the default distribution storage for the
first version.

The monthly website links to these repositories and their versioned downloads.
Record the dataset repository, release tag, construction commit, asset URLs, and
checksums in the monthly manifest. Publish corrections as new versions and retain
the earlier artifacts so published findings remain reproducible.

## The research agent's job

Hermes maintains an ongoing queue of investigations:

1. Explore unfamiliar sources such as city portals, event calendars, parking
   observations, transport data, environmental measurements, and public records.
2. Identify a prediction question with observable outcomes and usable inputs.
   Combine sources when that makes a worthwhile task: for example, past parking
   occupancy and local events to predict whether a garage will be full tomorrow.
3. Acquire the data and write a reproducible construction script.
4. Build splits, run common checks and baselines, and investigate failures.
5. Run promising candidates through the existing benchmark when compute is available.
6. Prepare finished candidates and publication drafts for human review.

Discovery should lead to working artifacts. Record abandoned ideas and their
reasons as well as successful ones. Some sources may need observations collected
over time; keep those investigations in the backlog while pursuing others.

Freshness means a new source, prediction question, or meaningful construction.
Repeating last month's task with a different random split is not a new discovery.
Novelty is evidence to document, not a guarantee of zero model contamination.

## Research coordinator and temporary workers

Hermes does web research, writes and reviews code, decides which investigations to
advance, and interprets results. Downloading large inputs, joins, dataset builds,
model fitting, and benchmark runs happen on temporary Hetzner Cloud servers.

Inventory the hosted instance's tools, skills, plugins, managed connectors, and
remote execution backends before choosing the worker integration. Reuse suitable
capabilities and existing clients. Add tested project-specific commands where
needed to enforce the configured limits and save job state independently of the
agent's current conversation. Do not rebuild Hermes's search, browser, scheduling,
memory, or generic tool orchestration.

The lifecycle is:

1. Record a job ID, candidate, code revision, container image, input references,
   requested resources, runtime limit, and expected outputs.
2. Create a worker within the configured server-size and spending limits. Record
   the server ID and expiration, and wait for provisioning and Docker readiness.
3. Run the job in a container with explicit CPU, memory, disk, and time limits.
   Persist progress and logs so Hermes can reconnect after a session restart.
4. Return a compact report: status, measurements, resource usage, failures, and an
   artifact manifest. Hermes retrieves relevant log excerpts or samples as needed.
5. Transfer required artifacts off the worker and verify their checksums before
   normal cleanup. Keep bulk data transfers off the 1.9 GiB coordinator where practical.
6. Delete the worker and its job-owned billable resources; record confirmed cleanup.

Use private staging storage for unpublished artifacts; private factory-repository
release assets are the proposed initial option for files that fit GitHub's limits.
Approved datasets are uploaded to their own public repositories' releases.
Records and small reports return to the factory repository. A worker's local disk
must not be the only copy of a completed candidate or experimental result.

Jobs need bounded retries, a maximum lifetime, and cleanup that runs independently
of the research conversation. A stalled transfer gets a bounded recovery period;
an expired worker must not stay billable indefinitely. On restart, reconcile
recorded jobs with project-labeled Hetzner resources before launching replacements.
Cleanup is restricted to resources belonging to this project's jobs.

The operator sets allowed server types/locations, maximum concurrent workers,
maximum lifetime, and a spending allowance. Worker commands enforce these limits,
including reservations for active jobs. Once configured and authorized, ordinary
jobs within that allowance run without asking for approval each time. Start with
one worker at a time. Benchmark resource budgets remain fixed and recorded even
when dataset-construction jobs use different worker sizes.

Deletion is part of finishing a job: Hetzner bills servers even while powered off.
See [Hetzner billing](https://docs.hetzner.com/cloud/billing/faq/). Its
[API](https://docs.hetzner.cloud/reference/cloud) supports asynchronous server
operations and resource labels for tracking these jobs.

## How work persists

Use a private GitHub repository as the shared working record. The agent's memory
can help it work, but instructions, findings, decisions, and next actions belong
in files that collaborators and fresh agent sessions can read.

The intended structure is:

| Path | Responsibility |
|---|---|
| `README.md` | Entry point and setup instructions |
| `PROJECT.md` | Purpose, scope, and intended behavior |
| `AGENTS.md` | Standing assignment and instructions for working in the project |
| `STATE.md` | Current priorities, unfinished work, and next actions |
| `candidates/` | Candidate records, evidence, construction scripts, and results |
| `jobs/` | Durable job records, worker identities, results, and cleanup status |
| `factory/`, `workers/` | Worker management, preparation, checking, and runner integration tools |
| `releases/` | Reviewed monthly manifests, dataset version links, and website content |

Working data stays outside Git, primarily on workers during execution and in
staging storage after collection. Published data lives in each dataset repository's
GitHub Releases, with locations and checksums recorded in the manifests.
Infrastructure credentials stay with the coordinator; workers receive only the
access needed for their jobs.

Each work session reads the current state, advances a concrete investigation,
records the result, and leaves a next action. Configure scheduled sessions to run
in the repository directory. Hermes supports repository `AGENTS.md` instructions
and project working directories for scheduled tasks:
[context files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files),
[scheduled work](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron#running-a-job-inside-a-project-directory).

The operator and collaborators review finished candidates and publication drafts.
Ordinary research and construction proceed within the configured resource budget.
The agent records blockers and raises those that need human input.

## What makes a useful task

A task needs a meaningful outcome, features available at the stated prediction
time, defensible splits, usable source permissions, reproducible construction,
and enough evaluation data to support the claims made about its scores.

Measure a simple baseline and whether a competent solution can improve it.
Investigate leakage, duplicate observations, saturation, instability, and cost.
Select tasks for their usefulness and headroom, never for high variance among
agent outcomes. Report that variance afterwards as an experimental result.

Set and record measurement protocols before applying them. The original spec's
million-row holdout, fixed AUC window, and eight-task launch requirement are not
binding requirements for this revised project. Smaller, unusual datasets are
welcome when their measured properties support useful evaluation.

## Use the existing benchmark

The benchmark lives locally at `../harness_benchmark`. Treat that checkout as
read-only. Reuse its runner through an adapter; do not build a replacement runner.

Both prepared reference tasks, `airline` and `fraud`, are available there. Use them
to verify integration and baseline behavior before trusting new measurements.
Keep factory data, configurations, caches, and run outputs outside that checkout;
an execution copy or container arrangement may be needed because some runner paths
are currently fixed relative to its source tree.

The runner currently scores binary classification. Its saved fraud baseline is
about 0.863 AUC; the roughly 0.997 result described in the earlier spec came from a
separate model using selected features. Resolve baseline definitions and resource
settings explicitly when implementing the checks.

## Build in small, complete steps

1. **Prepare the handoff.** Write the agent instructions, initial state, setup
   instructions, and first assignment. Have Scout inventory its actual hosted
   capabilities before choosing additional tooling. A fresh Hermes session should
   know what to do next after reading the repository.
2. **Verify a worker cycle.** Exercise provisioning, a small Docker job, result and
   artifact collection, and confirmed deletion. Check recovery after an interrupted
   session and a failed job before relying on unattended compute.
3. **Produce one release candidate.** Have Hermes discover a source we have not
   selected in advance, construct a task, check it, run it through the benchmark,
   and prepare the data and write-up for review.
4. **Publish the first release.** Prepare the dataset's own repository and tagged
   release assets. Build a simple site from the reviewed monthly manifest and
   write-up, linking to that dataset version.
5. **Repeat on another source.** Improve instructions and shared tools based on
   observed difficulties. Verify that a fresh session can resume unfinished work.
6. **Establish the monthly cadence.** Schedule ongoing research and maintain a
   reserve of ready tasks so collection failures do not dictate release dates.

Proposed starting defaults are one good task per month and binary classification
for the first release, matching the existing runner. Increase scope based on what
the first complete attempts teach us.

## Deployment choices still to make

- GitHub owner or organization and naming conventions for the private factory
  repository and public dataset repositories.
- Hermes workspace access and schedule on the 1.9 GiB NousCloud instance.
- Hetzner project access, allowed server types/locations, concurrency, maximum
  lifetime, and compute budget; model inference has a separate spending allowance.
- Configuration for harness experiments, including model, harness, and resource budget.
- Private artifact staging and website hosting. Published dataset downloads use
  GitHub Releases.
- First release date and the person responsible for its final review.

These choices should not block preparing the repository and the first assignment.

## Relationship to the earlier spec

Keep `dataset-factory-spec.md` as the original technical proposal. Its layout,
provenance, checking, and runner-integration details are useful references.
This document captures the revised project direction and takes precedence where
they differ: ongoing discovery by Hermes, monthly publication, public holdouts,
and a small first release built for the research group.
