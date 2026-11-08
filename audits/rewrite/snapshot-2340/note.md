CORRECTED SNAPSHOT 2026-11-08T23:39Z (actual latest attempt/job states;
previous export's "build-10 queued" and "timing passed" were stale/wrong).

CORRECTIONS (operator-verified staged bytes):
- FR build-3 stopped INSIDE the builder, before quality/meta/
  qualification output - the canonicalized timing has NOT been tested
  by the full gate on that artifact. Root cause of the coverage
  failure (hash-verified c7796642 builder): _training_rates excludes
  every non-train label and retains bisect_left maturity; entry=None
  for agencies absent from training yields NaN while the coverage
  check requires a value. To fix/declare through normal repair, no
  waiver.
- Bridge build-10 FAILED (manifest 725515915, failure 725515698;
  job release 438591605, 38.8 s, collected 23:21:03): KeyError
  poor_at_next_inspection in _make_row values[name] for COLUMNS - the
  header-name issue was fixed but the target placeholder is missing.

ACTUAL STATES (23:39:03Z):
- source-000015 (bridge): DEFERRED - build-11 (worker-scope failure,
  38.8 s class) exhausted the five-worker-failure bound (build-6, 8,
  9, 10, 11). Genuine bound exhaustion: normal discovered candidates
  proceed; no forcing.
- source-000016 (FR): build-4 attempt RUNNING (the NaN coverage
  repair in flight).
- source-000017: build-3 attempt waiting on the single worker slot
  (reconcile guard, 300 s delay).

NARROW LEDGER ACCOUNTING (existing records only):
- Current-month (November) jobs: 107; reserved EUR total: 14.30.
- Monthly worker budget: EUR 20; release reserve: EUR 5; remaining
  after reservations: EUR 5.70.
- Construction cap: max_attempts 5 per stage (task and worker failure
  counters separate).
