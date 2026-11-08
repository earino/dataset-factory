Compact read-only snapshot 2026-11-08T18:16:27Z (+follow-up 18:18Z). No
queue-state alterations, no launches outside the normal tick.

UCMR5 source-000013: the 75137d7 routing correction IS ACTIVE - queue stage
build with reason "Corrected repair verdict routing; fresh construction and
review required". The misrouted evaluate repair verdict was auto-reconciled
by seed; attempts/history preserved; the next fresh construction attempt
(rw-2ce60e8ae8f7 build-6) has not yet started its model task. The prior
attempts' artifacts (build-2/build-3 parse failures with retained
response.txt/usage.json) are intact.

CMS source-000012: build-4 worker ledger RUNNING at snapshot (model task
rw-b519336e6481-build-4 completed; worker launched; result pending).
Earlier build-3 worker had failed construction/qualification with artifacts
preserved (retry backoff observed at 18:16).

source-000014: clinicaltrials-gov-early-termination - researched (discovery
retry succeeded on attempt 2) and advanced to build.

Live local identity: tick process PID 29599 (172 s elapsed at snapshot).
Provider servers: zero at both the 18:16:27Z readback and the 18:18Z
follow-up (the build-4 worker was in its launch/provision window; ledger
running).

Next checkpoint: first live semantic-repair outcome under the corrected
routing.
