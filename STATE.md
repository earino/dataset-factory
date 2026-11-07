## 2026-11-07 (19:48Z) - follow-up (worker-status runner): resilience-a1-fixtures-001 + resilience-a1-small-002 SUCCEEDED - both already collected, destroyed, recorded and independently verified; re-verified per-case and against the live provider this session; both marked handled; resilience-a1-cpcb-001 RUNNING as the standing handoff

Watcher event for the two A1 acceptance jobs. Both had already been
collected, destroyed and recorded by the earlier session (fixtures
evidence 8e7009c, small evidence 13737a6 + 58e127e, independent
verification and CPCB pin 9e61565). This follow-up verified from
committed evidence and read-only live calls only; no collect, launch,
recovery or score, nothing re-run:

- resilience-a1-fixtures-001: acceptance-summary ok (cqc, wildfire
  exit 0), both per-case acceptance.json ok:true with
  strict_gate_refused:true; receipt pins staging release 437775462
  (manifest 0b62e5a9...), worker cx23 172.9 s EUR 0.06 destroyed;
  ledger status deleted, collected 18:57:33Z, deleted 18:58:34Z
  (server 175019878).
- resilience-a1-small-002: acceptance-summary ok (nzea, unhcr, nsbwa,
  ocha exit 0), all four per-case acceptance.json ok:true with
  strict_gate_refused:true; receipt pins staging release 437762044
  (manifest 95c6da86...), worker cx23 39.9 s EUR 0.06 destroyed;
  ledger status deleted, collected 18:32:13Z, deleted 18:34:23Z
  (server 175017328).
- Cleanup re-confirmed live by this session (read-only provider GETs,
  19:48Z): GET /v1/servers/175019878 -> 404 "server not found";
  GET /v1/servers/175017328 -> 404 "server not found"; project
  inventory holds exactly ONE server, 175022272
  scout-resilience-a1-cpcb-001 (running) with its one assigned primary
  IP - the expected running handoff per the recorded next action, not
  cleanup residue.
- Exact-commit CI read: 9e61565, 8e7009c and 13737a6 push runs all
  completed/success (plus their pull_request runs).
- Both jobs marked handled (.factory/resilience-a1-fixtures-001/
  handled, .factory/resilience-a1-small-002/handled, citing the
  evidence commits). A1 acceptance progress only - NOT package
  clearance; no published byte, tag, manifest or destination changed.

Next action unchanged (top entry + docs/FACTORY-RESILIENCE-IMPLEMENTATION.md):
resilience-a1-cpcb-001 (server 175022272, launched 19:13:59Z, EUR 0.32
reservation) is running; its ledger record is live and untracked; the
next worker-status event handles its collection and cleanup. The
untracked jobs/resilience-a1-cpcb-001.json is that live record and is
preserved untouched by this follow-up.

