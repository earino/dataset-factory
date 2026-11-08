Deployment record (2026-11-08): 999e076c398327b8d56c334ac185e5e34075e6f6
live at 17:13:05Z (sessions started 11:07-19:07 UTC measured but excluded
from the 40M weekly ceiling even after the window; post-19:07 sessions
charged normally; all other limits unchanged), then c1a072a9359672d1acaeadc5b15d503490f013df
(includes 999e076 + bounded-schema-error prompt: observed headers, missing
names, archive member) live at the 17:17:34Z free boundary without
interrupting paid work. Tick 07d6f8be3783 paused/resumed around each
boundary; cleanup active throughout.

Queue at 17:17:48Z: source-11 (RCRA) deferred at attempt limit (build-3
gate failure, reports preserved; descriptor lacks administrative source
type - patch alone does not qualify); source-12 (CMS) at build behind the
controller's reconcile guard ("An active or interrupted job exists");
source-13 (ucmr5-first-sample-pfas) at build - its build-1 worker failed
exit 1 at 36.0 s (release 438394116, terms capture passed, missing
additional-data concepts/join keys; ledger deleted), retry now benefits
from the observed-header schema errors. Worker budget at this deploy:
EUR 10.30 of 20.00 reserved. No proposal/state edits, no reopenings, no
extra retries.
