# Current state

Updated: 2026-09-17.

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

## Still unverified or unimplemented

Local tests use fake providers. **No live Hetzner/GitHub worker cycle has been run.**
Verify boot, SSH, Docker, uploads, recovery, costs and scheduled deletion before
unattended research jobs. Worker policy remains disabled with zero allowance.

The benchmark adapter, qualification tools, public exporter and website remain to
be implemented around the first real candidate. The sibling `../harness_benchmark`
checkout is read-only and has not been modified.

## Next actions for Scout

1. Read `docs/HANDOFF.md`, run `python3 -m factory doctor` and start the research
   assignment. The initial capability inventory is already complete.
2. Record a varied shortlist with source/license evidence, schemas and observable
   targets. Missing compute credentials do not block this work.
3. Once the operator provisions the inputs in `docs/OPERATIONS.md`, run and document
   the live smoke cycle, including failure and expiry cleanup.
4. Build the strongest candidate on a worker, preserve artifacts, measure quality
   and prepare a concrete review. Use the existing benchmark when available.

## Inputs still needed from the operator

GitHub access for Scout, a private staging repo/token, dedicated Hetzner project
access and SSH key, compute/inference allowances, and cleanup configuration.
Choose the first release date, reviewer, public dataset namespace and website
hosting as the first candidate develops. Notification delivery is not configured.
