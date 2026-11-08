Bridge (source-000015) deferral state at 21:25Z. Deployed SHA
2963e1f62eae96df6d5e1f3441aa32ea456fd3d0 (21:13:06Z).

ATTEMPT LEDGER: discover-1 success; build-1 retry (naming rule);
build-2 retry (naming rule, concrete-columns direction); build-3 retry
(naming rule AGAIN - third burn, 18,818 in / 30,402 out, 184 s, raw
response exported); build-4 retry (non-JSON: "Expecting ',' delimiter at
line 1, column 52783"; response.txt exported); build-5 retry ->
FIVE-FAILURE DEFERRAL at ~21:12:44Z (non-JSON: "Expecting value at
line 1, column 1"; response.txt exported). All five build failures
occurred under the PRE-fix code; build-3/4/5 ran 21:03-21:12 while the
naming fix was still in CI.

MISMATCH: the 2963e1f reuse path targets the next ordinary attempt when
the former naming-rule failure is recorded - but the candidate
deferred BEFORE the fix deployed, the deferral's recorded reason is the
build-5 JSON-parse failure (not the naming rule), and a deferred
candidate receives no next ordinary attempt. The paid build-2 proposal
therefore did NOT run; no reuse record, no worker launch, no
qualification result.

CONSEQUENCE: the tick proceeded to source-000016 discovery
(rw-ba904118ba27-discover-1), whose first attempt failed with a model
invocation error (Hermes-side exit 1); it retries under normal
allowances. UCMR publish-3: collected 21:10:04Z, deleted 21:10:17Z,
release 438522894 - cleanup complete.

DECISION NEEDED (operator): reopen source-000015 from deferral, or add
a reconcile path for attempt-limit deferrals whose earlier failures
include the superseded naming rule. Saved paid proposals (build-2 and
build-3) are on disk and exported; no candidate state was edited by me.
