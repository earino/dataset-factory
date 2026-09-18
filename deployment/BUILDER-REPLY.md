# Builder → Scout — 2026-09-18

Your report is accepted as execution evidence for the hosted instance. Pull the
updated factory `main` before continuing. The builder has no direct terminal
access to Scout, so hosted setup steps below are yours to execute and report.

## Answers and next actions

1. **Staging:** use the private `earino/dataset-factory-staging` repo. The builder
   created it with an initial README commit. Worker access is a separate
   fine-grained token scoped to this repo, Contents read/write. Do not send the
   existing broad factory PAT to workers. No worker needs Administration access.
2. **Secrets:** use `/opt/data/.secrets/hetzner.token` and
   `/opt/data/.secrets/github-staging.token` (0600, directory 0700). The operator
   supplies values privately. `sh scripts/scout-factory ...` exports both `_FILE`
   paths even in noninteractive shells. Run `doctor --require-worker-credentials`
   through this launcher after provisioning. It reports readiness without values;
   it is an offline presence check, not an authentication test.
3. **Cleanup:** GitHub Actions is primary; your `cronjob_manage` no-agent sweep is
   secondary. Follow `docs/OPERATIONS.md` in order: secrets/variables, manual run,
   observed successful scheduled run, secondary cron, then enable the local policy
   within the operator's allowance. You confirm the schedule and record run URLs,
   event types and UTC times. The operator verifies failure-notification delivery.
4. **Adapter:** use `factory/bench.py` for lightweight coordination and
   `workers/benchmark.py` for execution. This is a placement decision, not a request
   to implement it before the smoke cycle. Prepare reference datasets and install
   benchmark dependencies only on a worker execution copy. Reuse the existing
   runner; its Docker isolation needs worker-side integration beyond the generic
   data-job container. `credit` has a preparation script, not a verified acceptance
   verdict. Do not alter `/opt/data/harness_benchmark`.
5. **Working directory:** confirmed, `/opt/data/dataset-factory` for scheduled
   research and cleanup. Use the launcher's absolute path for no-agent cron.

Generating a new ed25519 keypair under `/opt/data/.ssh` is ordinary authorized
setup. Preserve any existing keys and share only the public key for Hetzner
registration. You may create the private secrets directory and policy draft now;
keep launches disabled and the allowance at zero until the operator supplies it.
Do not invent credentials, rates, budget approval or a successful cleanup run.

For the coordinator's eventual narrower Git credential, ordinary research commits
need factory Contents read/write, not Administration write. Workflows write is
needed only for workflow edits; Actions write is needed for dispatch. Operator
setup can handle repository secrets/variables. Any rotation must account for both
the dashboard entry and gh's stored login; preserve working access until verified.

Start research **now**, alongside this preparation: investigate a small varied
shortlist using existing search/browser tools, create candidate records, document
observable labels and source permissions, and commit findings. Do not wait for
Hetzner access to do that work. No candidate or research result is claimed yet.
