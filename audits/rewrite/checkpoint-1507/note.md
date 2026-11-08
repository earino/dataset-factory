15:07Z checkpoint export (measured 2026-11-08T15:00:01Z, tick 07d6f8be3783
paused 14:59:57Z for the import-shadow fix; cleanup sweep active; all
attempt records preserved; no source resurrection).

Queue: sources 1-4 and 6 deferred (1/3/4/6 on model-invocation/startup
failures incl. the factory/http.py import shadow; 2 on non-JSON response),
source-5 rejected (publisher terms HTTP 403), source-7 researched and at
build, source-8 in discover. Also flagged for the operator: source-4's
build-4 repair was refused pre-model with "Task context exceeds 64 KiB" -
the stats19 repair context crossed the adapter cap before the import
crashes consumed the allowance.

Inference (binding measured budget): 36,766,514 / 40,000,000 tokens in the
rolling 7-day window (~1.23M before the 0.95x admission stop at 38M);
sessions 131/200; research 6,497 calls / 32.38M in; interactive 753 calls
/ 25.75M in; auxiliary 23 calls. USD spend unknown (no pricing).

Worker allowance: 76 job reservations in 2026-11, EUR 9.18 of 20.00
(EUR 10.82 remaining). Provider holds zero servers; cleanup verified active.

Codex correction, 15:17 UTC: the 0.95 fraction above was an interpretation error;
research-budget.py applies it to dollar spend only. The weekly token gate is
40,000,000, so this unchanged measured observation leaves 3,233,486 tokens. Both
input and output count. No configured allowance or admission code was changed.
