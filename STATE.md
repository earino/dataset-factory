# Current state

Updated: 2026-09-18.

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
- Tiny synthetic infrastructure smoke job and local failure-path tests. The smoke
  job is not a dataset candidate or replacement for benchmark reference tasks.
- A public dataset README template describing the eventual release contract.
- Hosted GitHub access verified by Scout: clone, throwaway branch push/deletion,
  release/run listing and successful CI. `gh` v2.101.0 is now installed.
- Private staging repo `earino/dataset-factory-staging`, created by the builder
  with an initial README commit. Its restricted worker token is still needed.
- A noninteractive `_FILE` launcher, credential presence assertions and live Linux
  memory diagnostics. Builder ran 30 local tests successfully; Scout ran the
  original 22 tests at `a9da074`. New code still needs a hosted pull and doctor run.

## Still unverified or unimplemented

Local tests use fake providers. **No live Hetzner/GitHub worker cycle has been run.**
Verify boot, SSH, Docker, uploads, recovery, costs and scheduled deletion before
unattended research jobs. Worker policy remains disabled with zero allowance.

The benchmark adapter, qualification tools, public exporter and website remain to
be implemented around the first real candidate. The sibling `../harness_benchmark`
checkout is read-only and has not been modified.

Scout's benchmark clone has preparation scripts and saved baselines, but no
prepared datasets. The builder's local data presence does not carry over in Git.
Prepare airline/fraud only on the worker execution copy; credit is an additional
preparation script, not a verified reference verdict. The planned adapter is
`factory/bench.py` plus `workers/benchmark.py`, neither implemented yet.

As of Scout's 2026-09-18 report, no research or candidate records had been started.
The cleanup workflow is skipped, secrets/policy are absent, and notifications are
unconfigured. No live smoke success is claimed.

## Next actions for Scout

1. Pull `main` with `git pull --ff-only` from `/opt/data/dataset-factory`, read
   `deployment/BUILDER-REPLY.md`, and run `sh scripts/scout-factory doctor`.
2. Record a varied shortlist with source/license evidence, schemas and observable
   targets. Missing compute credentials do not block this work.
3. Prepare a dedicated SSH key and disabled policy; the operator supplies worker
   tokens and allowance. Verify primary GitHub Actions cleanup with both a manual
   and a scheduled successful run, then add secondary on-host cleanup. Record
   evidence and run the live smoke cycle, including failure and expiry cleanup.
4. Build the strongest candidate on a worker, preserve artifacts, measure quality
   and prepare a concrete review. Use the existing benchmark when available.

## Inputs still needed from the operator

Restricted private staging token, dedicated Hetzner project access and SSH key
registration, compute/inference allowances, and cleanup secret/variable setup.
Choose the first release date, reviewer, public dataset namespace and website
hosting as the first candidate develops. Notification delivery is not configured.
