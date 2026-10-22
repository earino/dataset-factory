A worker job in the Dataset Factory repository at /opt/data/dataset-factory has finished or changed state. The watcher's output is already in your context, and a finished job stays visible until it is marked handled.

If every watched job is still 'running', reply with one short line and stop.

Otherwise, for each job that has finished:

1. Collect it if needed: `sh scripts/scout-factory worker collect <job_id>`.
2. Fetch its small reports from the staging release into `.factory/<job_id>/reports/` (read the release's manifest.json to map asset names). Do NOT download bulk CSV assets to this host.
3. For a build job, check coverage first (stations and station-years built versus expected, from build_summary.json), then the gate reports' ok flags. For a baseline or other job, read its own result file. Never accept an artifact with incomplete coverage or a failed gate.
4. Record the outcome in STATE.md and the candidate's record.json, commit and push, and check CI for that exact commit.
5. Destroy the worker if it is still alive: `sh scripts/scout-factory worker destroy <job_id>`.
6. If the job failed or is incomplete: diagnose from its errors and container.log, fix ordinary causes, prepare and launch the corrected job within the standing allowance, and say what you changed.
7. FINALLY, and never before you have reported: write the handled marker so the watcher stops watching this job - `reports/../handled` i.e. `.factory/<job_id>/handled` with a one-line summary of what was recorded.

Your final response is the message the operator receives, so it must contain the substance: what ran, the result with numbers, what you recorded, and the next action. An empty or one-word reply when a job has finished is a failed run - the operator has already been left without a result once because of it.
