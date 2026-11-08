UCMR build-8 resume state (2026-11-08T20:13Z, live reads; worker-liveness
investigation stopped per operator - build-8 verified independently in
main 3578add, CI 42518627760).

Deployed SHA: 46c2794c9c52346fc023a6365940a5f74a9b26fa.

Build-8 job ledger (jobs/rw-2ce60e8ae8f7-build-8.json): status deleted;
result succeeded, exit 0, elapsed 61.0 s, staging release 438490129;
collected_at 2026-11-08T20:10:04Z; deleted_at 2026-11-08T20:10:17Z
(provider zero = cleanup completed, consistent with the ledger).

Candidate source-000013 (ucmr5-first-sample-pfas): stage evaluate,
attempt rw-2ce60e8ae8f7-build-8, reason "Full artifact constructed,
qualified, accepted and measured on worker". Fresh semantic review model
task rw-2ce60e8ae8f7-evaluate-4 RUNNING (hermes chat PID 5437, 118 s at
20:13:03Z). Tick outcome at 20:13: done/source-000013/evaluate/attempt
rw-2ce60e8ae8f7-build-8.

source-000015: discovery was NOT newly admitted ahead of UCMR review. It
was already admitted pre-cutoff (final cutoff snapshot: source-15 at
discover). At 20:05-20:09 the build-8 worker was in flight and no
review/publication work was ready (review only becomes ready after worker
collection at 20:10:04). The tick ran the only other admitted ready item
- source-15's discovery - which completed 20:09:25 ("Source researched
with access, terms and task evidence", now at build). UCMR's evaluate-4
launched immediately after collection. Deployed ordering (admitted
attempts first; publication > review > construction > discovery) was
preserved; the controller runs one internal model task at a time, so no
additional discovery can launch while evaluate-4 runs, and publication/
construction for UCMR outrank discovery afterwards. max_pending_candidates
remains 2 (no config change made).
