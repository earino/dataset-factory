# A4 claims replay after two prose false positives

The full worker run `resilience-a4-blocked-004` completed all nine stages for each
of the four original blocked artifacts. Codex independently fetched and verified
49 compact JSON reports (383,511 bytes) against the raw staging manifest: release
437866550, manifest asset 722050473, 36,674 bytes, SHA-256
`4285a299fba001a6a08eac70abe6eae73f8c15dcc5cdf13be992230f5a4016e6`.
Every comparison completed with unchanged inputs and `release_eligible: false`.
Collection, provider cleanup and the coordinator ledger remain Scout's closeout.

Inspection identified two prose-parser errors, distinct from the actual defects:

- ZA's sentence explicitly says “not an enforcement claim” and “nothing in this
  package enforces isolation”. The negation vocabulary missed “nothing”, so it
  flagged the later `enforces` in both `quality.json` and the builder string.
- Wildfire's correct breakdown begins “positive rate rises into the holdout
  (1.87% train ...”. Prefix matching attached the first percentage to the opening
  word `holdout`, as well as to the explicit trailing label `train`.

The negation vocabulary now recognizes “nothing” within the existing local clause.
It still flags a guarantee after “but” or in a subsequent sentence. Percentage
matching now assigns each literal once: an explicit suffix wins over a split name
that opens a parenthesized breakdown; otherwise prefix notation keeps precedence.
Incorrect values and genuine positive guarantee statements remain failures.

`audits/resilience/2026-11-07-a4-claims-replay/receipt.json` binds the replay to the
worker acceptance/facts/claims asset IDs and hashes, every compact package input,
the unchanged facts implementation and the old/new prose-check code. The original
compact files came from the retained independent audit export, and every byte was
checked against the worker's full input inventory. Only non-CSV files were copied
into an owned scratch directory; no original construction code was executed.

Before applying the correction, all original findings reproduced, independent of
list order (reading canonical JSON changes dictionary iteration order). Replaying
the corrected checker removed one wildfire finding and two ZA findings, added none,
and retained refusal for all four packages: 12 wildfire, 10 CPCB, 6 CQC and 7 ZA
findings remain. CPCB's measured min/max violations, CQC's dictionary mismatch,
wildfire's actual incorrect rates and ZA's interval claims still trigger the checks.
These counts are lint findings, not a count of independently proved semantic defects.

This is a local **prose-check replay using full-row worker facts**, not a new worker
qualification, a recomputed paired-score interval, a package correction or release
approval. It avoids repeating the costly leakage battery for a text-only parser fix.
The full A4 receipt remains evidence of its original code version; new releases use
the corrected current checker. The operating hold and all frozen bytes remain unchanged.
