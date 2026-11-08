# First unattended controller cycle - compact evidence (2026-11-08)

Exported read-only from the live deployment at main `71a1b05` (tick
`07d6f8be3783`, resumed 12:40:00Z). No probes, no candidate-state edits;
the scheduler continued running throughout.

## build-3 (source-000001, candidate nid-dam-condition-screening, USACE NID)

- Construction model phase succeeded on the new web-only path: 3 calls,
  15,143 in / 43,831 out, 218.6 s (construction-response.json is the parsed
  record; construction-response-raw.txt the verbatim output;
  construction-usage.json the measured accounting).
- Worker `rw-4fa4bc1fda01-build-3` launched 12:48:13Z from the live ledger:
  cpx32, EUR 0.16 reservation, server 175132504 (job-record.json).
- Worker failed: exit 1, not OOM, 161.3 s, uploaded; failure artifacts
  preserved in staging release 438244578. worker-failure/ holds the
  digest-verified compact assets: failure.json (921 B - observed condition
  vocabulary including "Not Available"), container.log (1,181 B) and
  LICENSE-EVIDENCE.json (746 B).
- Controller collected 12:52:04Z, reconciled the deletion at 12:52:17Z,
  deferred the candidate at its attempt limit. Anomaly reported separately:
  the server was already absent (GET 404, zero servers/IPs) at 12:50:54Z,
  the instant the 161.3 s window ends and ~70 s before the controller's
  collect; no cron execution or log line covers that deletion.

## discover-3 (source-000002)

- Attempt ended "Model response is not JSON" -> attempt limit -> deferred.
- final-assistant-text.txt (18,768 chars) is the adapter-retained stdout,
  verified byte-identical to session `local-1e52978ab741eba3c7...`'s final
  assistant message in state.db (read-only). It opens as valid JSON selecting
  `fra-grade-crossing-fatality` (FRA Form 57 highway-rail grade-crossing
  incidents, 251,725 rows 1975-2026, public domain, binary casualty label,
  no lags/panel) - so the parse refusal is a formatting nuance in the tail,
  not a content failure. usage.json records the measured accounting.
- No failure.json was written for this attempt (the parse failure surfaced
  through the tick outcome and pipeline store only).

## Queue at export

queue-status.json: source-000001 deferred, source-000002 deferred,
source-000003 advanced to build (researched), source-000004 at discover.
The pipeline is cycling discovery -> build unattended.
