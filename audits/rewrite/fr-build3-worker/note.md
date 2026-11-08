FR (source-000016) build-3 worker outcome (2026-11-08T23:31Z). Failure
verbatim from staging release 438597150 (asset 725537260).

WORKER: failed, exit 1, 325.3 s - a FULL build run (16,813 rows; Federal
Register API pages for PRORULE 1994-2022-06-30 and RULE 1994-2026-11-07).
The label-leak repair and the canonicalized timing passed their checks;
no known-hash block (new build_py accepted).

FAILURE - narrow late-stage data-quality check only:
"agency prior rate coverage. observed {'rows': 16813, 'rows_with_agency':
16550, 'rows_with_rate': 16525}. expected every row carrying a top-level
agency value receives a numeric rate, and rows without an agency stay
missing."

READING: 25 rows carry a top-level agency value but no numeric prior
rate (16,550 - 16,525). A small edge case in the repaired grouped-rate
logic - likely agencies without matured earlier labels whose exemption
is not yet encoded consistently with the coverage rule. Next bounded
repair: make the 25-row case explicit (populate or properly mark the
rate absent per the declaration) while keeping the leak fix and
timing canonicalization intact.

Ordinary retry cycle continues; artifacts preserved; worker deleted;
no manual edits. Bridge build-10 and source-17 build-3 remain queued
behind the single worker slot.
