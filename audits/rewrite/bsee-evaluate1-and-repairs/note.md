BSEE (source-000017) build-4 review + repair chain (2026-11-09T00:05Z).
Raw evaluate-1 response/usage exported verbatim.

ANSWER to "why build-6/7": build-4's WORKER SUCCEEDED (38.7 s, exit 0,
release 438605387; full qualification receipt + 33 asset hashes
operator-verified) and the candidate advanced to evaluate - but the
fresh semantic review (evaluate-1, 5 calls, 73,646 in / 29,186 out,
170.2 s) returned verdict REPAIR with 3 material findings:
0. Row key is COMPLEX_ID_NUM, a BSEE complex/group identifier - not one
   row per structure; 102 eligible structures silently dropped.
1. Authority filter does not implement the declared AUTHORITY_TYPE='OCS
   Lease' population; uses an undecoded lease-number proxy.
2. isolated_rows/independence claim rests only on unique row IDs; the
   dedup step is a non-random selection that can remove [rows
   questionably].
The corrected routing sent it back to build. build-5's repair
construction FAILED TO PARSE ("line 42, column 23: invalid syntax";
34,898 out tokens paid, retained). build-6 also FAILED TO PARSE
("line 43, column 31: unmatched '}'", 13,797 out, retained). build-7
(third repair) is IN FLIGHT as a paid child and continues untouched.

Note: parse failures are MODEL-TASK failures, counted separately from
the five-worker-failure cap. BSEE worker failures so far: build-1/2/3
(3 of 5).

CURRENT ATTEMPTS (00:01Z): source-15 bridge DEFERRED (genuine 5-worker
bound: build-6/8/9/10/11; not forcing). source-16 FR: build-4 repair
response landed 23:45, worker admission pending (priority per
operator). source-17 BSEE: build-7 repair construction in flight.
Deployed: 54298b169a1881174f7eac56274448b71ecc62dd. Evidence-only main
0ad3e6d CI green, no deployment needed. EUR ledger: 14.30 of 15.00
reserved (0.70 before the 5.00 reserve).
