75137d7202456ef6e5b9c9b37a1a66344ff53b40 deployed 2026-11-08 18:13:06Z
(exact CI green; 941 clean-checkout tests/13 skips per operator). Fixes
Driver.evaluate's reject-for-every-non-accept-verdict defect: bounded
evaluate->build repairs now retain findings; fresh artifact
qualification/review still required; seed auto-reconciles only exact
misrouted repair verdicts, preserving attempts/history. No manual
candidate-state edits.

19:07 UTC cutoff arrangement (concrete, existing scheduler/config only):
one-shot no-agent cron job f0852e8c6392
"scout-pipeline-cutoff-1907" fires at 2026-11-08T19:07:00 UTC (catch_up
enabled so a missed fire runs once on return) running
/opt/data/scripts/scout_pipeline_cutoff.py, which sets
pipeline_enabled=false in /opt/data/dataset-factory/config/local.json -
stopping NEW pipeline admissions while preserving all resumable state
(candidates, attempts, ledgers, pipeline.sqlite3, model-task artifacts).
In-flight work at the cutoff completes normally; the minute tick keeps
running but the driver refuses new work with pipeline_enabled=false. The
independent cleanup sweep (e80975eddd4a) remains active and untouched.
The 999e076 development-token exemption lapses automatically at 19:07
(sessions started in the window stay measured-but-excluded; new sessions
charge normally). No budget/limit/credential changes.
