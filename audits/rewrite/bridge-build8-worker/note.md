Bridge build-8 worker outcome (2026-11-08T22:40Z; recovered-proposal
run, zero new model calls). Exported: failure.json + terms-evidence.json
verbatim from staging release 438569886.

WORKER: failed, exit 1, 34.7 s, no OOM; collected/deleted normally.
TERMS/DOCUMENTATION ACCESS: PASSED (terms quote found, contiguous;
documentation SHA verified).
FAILURE: AssertionError at a source check - "2018 annual archive is a
ZIP archive":
- Direct archive URL https://www.fhwa.dot.gov/bridge/nbi/
  2018hwybronlyonefile.zip -> HTTP 404 Not Found.
- Disclaim.cfm?nbiYear=2018hwybronlyonefile&nbiZip=zip (and with
  #content) -> 8,161 bytes HTML (the disclaim page), stored as .zip but
  not a ZIP.
- Expected: valid zip archive holding the annual NBI file, from the
  direct archive URL or a zip link followed from the served HTML page;
  selected member None; observed headers None; missing names [].

READING: the recovered build-7 proposal DID restructure the check
correctly - it now tries the direct archive URL AND follows the page's
zip link with precise diagnostics (progress from build-6's raw
HTML-not-ZIP error). The empirical blocker: the publisher's own linked
ZIP URL returns 404 and the disclaim page serves HTML - the archive is
not at the URL named in the recipe. The terms_url identifies the
Socrata dataset (data.transportation.gov National-Bridge-Inventory-NBI-
uack-gist), whose export/API path is a candidate correct archive
source for the next bounded repair or a focused research task.

Worker-failure allowance: build-6 and build-8 are worker-scope failure
1 and 2 of 5; model-task failures are counted separately. No manual
edits; the ordinary repair cycle continues with this diagnostic.

ADDENDUM 22:44Z: REUSE VERIFIED (operator): build-8's build.py SHA
exactly matches the saved build-7 code - the recovered paid bytes were
reused with no model call. Direct /bridge/nbi/2018hwybronlyonefile.zip
returns HTTP 404; the disclaim page still serves the stale link.
Classification: bounded SOURCE-ACCESS RESEARCH is needed (not another
write-only repair guess) to locate the live 2018 NBI archive (the
Socrata dataset behind terms_url is a candidate source). Per operator
instruction, new tick admissions PAUSED at 22:43:5xZ at a safe
boundary; the in-flight rw-ba904118ba27-build-1 construction (source-16,
a fresh candidate - not a bridge repair) is preserved and will land on
disk; cleanup remains active. Operator is adding a small generic
access-research phase before code repair for observed HTTP access
failures; no source-specific controller, no manual candidate edits.
