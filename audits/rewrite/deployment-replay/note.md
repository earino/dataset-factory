# Deployment replay receipts (2026-11-08 14:03Z, deployed 3c3c5513)

Disclosed deployment recoveries under controller_lock with the tick paused;
not claims of untouched end-to-end runs.

- source-000003 (hurdat2): reopened to build, new attempt
  rw-dfe241e4e784-build-5 via Store.begin; construction reused from the
  build-4 usage-bound session's final assistant text (30,626 chars, valid
  JSON, construction.validate PASS - exported verbatim as
  reused-construction-source-000003.json); construction_attempt set to the
  new attempt; only the old job pointer cleared. Cause: code_turns=2
  turn-limit discarded valid output. Old worker build-3 verified deleted.
  The receipt records partial_prior_run=true: the first script pass
  completed the store mutation for this candidate but failed writing its
  receipt (usage key); the idempotent re-run reused the same running
  attempt - no double ordinal.
- source-000004 (stats19): reopened to build, new attempt
  rw-17b5d37bd413-build-2; construction reused unchanged from the stored
  successful build-1 response (construction.validate PASS - exported as
  reused-construction-source-000004.json). Cause: OGL publisher-quote
  formatting false rejection. Old worker build-1 verified deleted.
- All previous attempt rows preserved; fresh queued sources untouched;
  no source/task/splits/code/quality or passing-gate edits; tick resumed
  14:0xZ to assemble and run both with fixed helpers under every check.

## Full before/after state files (added on operator request)

The replay receipts originally summarized before/after as data_keys lists.
Full state files are now exported: <cid>-before-state-reconstructed.json
and <cid>-after-state.json. Provenance of the reconstruction: all fields
the replay did not touch (source, focus, failure) are verbatim from the
current store; construction/construction_attempt are restored from the
original model-task response files and the recorded pre-replay attempt
ids; the job pointer is the one recorded in the receipts. after-state is
a verbatim dump. No store content was modified in producing these files.
