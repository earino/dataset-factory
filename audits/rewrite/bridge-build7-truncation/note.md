Bridge build-7 truncation-class failure export (2026-11-08T22:15Z).
Raw response.txt (59,101 B), usage.json, and prompt.txt (80,796 B)
exported verbatim for operator EOF inspection.

ATTEMPT/RECOVERY SNAPSHOT:
- 21:47:01Z: build-7 first admission attempt hit the session-cap
  BudgetWait; Driver.execute recorded waiting/delay=3600 (next_run
  22:47:01Z).
- 22:05:17Z: 20ba073 deployed (seed() rechecks the admission gate for
  future-waiting model tasks with an empty pre-call directory; clears
  only next_run, preserving attempt/stage/history).
- 22:05:31Z: build-7 ADMITTED under its SAME attempt identity
  (rw-b702d47ad634-build-7) - 14 s after tick resume. No manual edit.
- Generation: 2 calls, 21,602 in / 36,783 out, tool_results 0,
  216.1 s. response.txt is 59,101 bytes; NO response.json.
- Parse failure: "Expecting ',' delimiter at line 1, column 59102" -
  one past EOF: the top-level JSON object never closes. The visible
  tail ends ...ignoring N where that field is present."}' - nested
  structures appear closed; the outermost object is one brace short.
  Truncation-class failure #3 for this candidate (build-4 col 52783;
  build-5 col 1; build-7 col 59102).
- Consequence: source-15 task-failure allowance exhausted ->
  DEFERRED again at ~22:10Z ("Attempt limit reached"). State preserved;
  no manual reopen, no allowance reset, no new gates.

RECOVERY HYPOTHESIS (operator): if appending the final top-level brace
yields a valid construction proposal, deterministic parsing/
reconciliation can reuse these paid bytes with zero fresh model calls.
Current state at export: source-15 deferred (untouched); source-16's
discover-4 research child live and preserved; tick running normally.
