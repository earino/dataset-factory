# 65de530 deployment record — shared declaration preflight

Recorded 2026-11-09T19:41Z. Deployed commit
`65de53070c46503307572aaa25ee262d0741facb` ("Reject existing declaration
failures before worker admission", exact CI 42682772672 green: 961
clean-checkout tests, 13 skipped, 53 focused).

- Deployed 2026-11-09T19:25:30Z at a safe paid-task boundary: no tick process
  running (previous tick exited 19:25:20Z), no model task in flight (source-19
  discover-1 had closed at 19:22:43Z). The running source-18 worker executes
  remotely and was untouched; attempts, retry bounds and cleanup preserved.
- Readback after deploy: HEAD exactly `65de530`; `config/local.json`
  `monthly_budget_eur` 45 / `release_reserve_eur` 5 (temporary development
  allowance; the extra EUR 25 stays usable through the November budget; EUR 20
  is restored 2026-12-01 by the existing deterministic one-shot scheduler);
  `python3 -m factory status` OK. Ticks on the new code advanced work normally
  (source-19 discover-2 completed 19:31:14Z; CFPB build-2 model task and worker
  launch; source-19 build-1 construction task started 19:36:05Z).

## Observed preflight outcome

The new shared declaration predicates ran as part of CFPB
`cfpb-bank-account-monetary-relief` build-2 construction validation (repair
proposal landed 19:34:58Z): **no rejection** — its declarations were valid,
and the proposal went on to a worker launch. No false-positive blocking was
observed. No proposal with bad declarations has been submitted since
deployment, so a live cheap rejection has not yet been demonstrated; the
recorded FR build-5/6 failure classes are the expected trigger.

## CFPB source-18 state at record time

- build-1 worker: 32.7 s, TermsEvidenceError 403 (manifest 728683595).
- build-2 worker: terms capture repaired normally (LICENSE-EVIDENCE 728719097);
  45.2 s, failed on data-endpoint HTTP 403 at build.py line 73
  (`fetch(_url(year, offset))`); release 439553885, manifest 728719432.
- Handling: the existing bounded access-research/code repair path; no custom
  CFPB orchestration, no worker-bound resets. Worker failures used: 2 of 5.

## Other live work

source-19 (FAA NWSD bird strikes, `rw-95d877b91529`): discover-1 failed
(model invocation, 397.2 s, retained); discover-2 succeeded
(19:26:01–19:31:14Z); build-1 write-only construction task started 19:36:05Z
(paid child, preserved).
