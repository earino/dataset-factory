# Second-round diagnostics (2026-11-08 13:25-13:32Z, pre-0ddaeae runtime)

Exported read-only. source-000001 (nid-dam-condition-screening) build-4 and
source-000003 (hurdat2-atlantic-ts-to-hurricane-72h) build-2 failed with
"Model invocation failed: exit_code 1, parser_error: [], diagnostic:
session_id: [opaque-value]" - the child created a session then exited 1;
partial measured usage retained by the 71a1b05 runtime on these failures.
source-000003 build-1 hit the wall-clock limit (its own attempt).
source-000004 (stats19-collision-ksi) discovery succeeded (response.json
here) and advanced to build. Source titles in this cycle:
nid-dam-condition-screening (USACE NID), fra-grade-crossing-fatality
(FRA Form 57), hurdat2-atlantic-ts-to-hurricane-72h (NHC HURDAT2),
stats19-collision-ksi (GB road collisions). Deployed 0ddaeae at the
13:31:25Z free boundary (partial usage + redacted stdout retention for
failed/timed-out tasks). Effective reasoning effort for the factory's
DeepSeek tasks: config.yaml reasoning_effort: medium (no per-model override,
no --reasoning flag in the adapter argv).

## Turn-cap diagnosis (confirmed) and source-4 outcome

Both failed construction sessions show the code_turns=2 cap consumed by two
web_extract field-doc reads, then the iteration-cap nudge:
- nid-dam build-4 (local-80e14163...): final assistant text is an explicit
  gave-up message (170 B) with NO construction JSON - retained verbatim in
  nid-dam-build-4-final-assistant.txt.
- hurdat2 build-2 (local-0250b247...): despite the cap, the wrap-up DID emit a
  complete 33,567-char construction JSON (build_py + source URL) - retained
  verbatim in hurdat2-build-2-final-assistant.txt. The content exists; the
  attempt failed on the exit-1/accounting path, not missing output. Reusable
  without new inference.
- source-000004 (stats19-collision-ksi) build-1: construction task succeeded
  (build_py produced for DFT road-casualty data), but the controller rejected
  the source at 13:3xZ - "Publisher terms evidence could not support the
  source claim". A policy rejection, not a failure; no worker launched.

Integration correction (Codex, direct staging inspection): the final sentence
above is incorrect. Job `rw-17b5d37bd413-build-1` ran and exited 1 after 30.0 s;
its manifest and digest-verified TermsEvidenceError are in
`../third-worker-outcomes/stats19-*`, staging release 438266894. The mismatch
was reproducible against the real OGL page: HTML extraction introduced spaces
before punctuation and the quote used explicit omissions. The revised matcher
checks every verbatim span in order and records that matching mode; it does not
approve source licence applicability. The source remains rejected in live state.

HURDAT2 build-3 also ran (staging release 438271506, 32.9 s, exit 1). It wrote
three CSVs but failed before qualification because the declared target
`reaches_hurricane_72h` was absent from the CSV schema. The full failure and
manifest are in `../third-worker-outcomes/hurdat2-*`. No metrics or dataset
acceptance follow from those unqualified files.
