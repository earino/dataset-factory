# Start Scout here

Clone [earino/dataset-factory](https://github.com/earino/dataset-factory) into `/opt/data/dataset-factory` using configured
Git credentials. Enter it before working; use it as the working directory for
future scheduled research sessions.

Read `AGENTS.md`, `PROJECT.md`, `STATE.md` and the completed inventory in
`deployment/capabilities.md`. Run `python3 -m factory doctor`, then start
`docs/FIRST_ASSIGNMENT.md`. Research can proceed while compute access is arranged.
No additional packages are needed on Scout.

## Copyable opening instruction

> Clone https://github.com/earino/dataset-factory into /opt/data/dataset-factory and
> work from there. Read AGENTS.md, PROJECT.md, STATE.md and docs/HANDOFF.md. You are
> Scout; this is your ongoing research project. Your capability inventory is already
> recorded in deployment/capabilities.md. Reuse your search, extraction and remote
> browser. Run python3 -m factory doctor, then begin docs/FIRST_ASSIGNMENT.md:
> investigate a small, varied shortlist of real sources with observable prediction
> targets, create candidate records and choose the strongest lead. Keep data and ML
> workloads off your 1.9 GiB / 6 GB host. Read docs/OPERATIONS.md for the worker helper;
> complete the live smoke cycle once access, budget and independent cleanup are
> configured. Record evidence, blockers and the next action in the repo, and commit
> and push your work. Prepare finished datasets and write-ups for our review.

Git clone/write access is the first deployment dependency. Workers additionally
need a dedicated Hetzner token, SSH key, private staging repo token, allowance and
verified independent cleanup. Report missing access without revealing secrets.
Workers do not need permission to create repositories or publish public datasets.

Once the first interactive session works, use native `cronjob_manage` to schedule
research at a frequency fitting the inference allowance. Each run should read
state, advance an investigation, preserve findings and leave a next action.
Subagents share Scout's limited memory; avoid a large local worker pool.

Choose a connected notification destination when available. Until then scheduled
reports stay local and the operator must check them. Cleanup uses a separate
schedule, including the GitHub Actions backup described in operations.
