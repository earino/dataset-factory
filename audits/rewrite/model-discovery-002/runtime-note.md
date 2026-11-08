# Rewrite model-discovery live evidence (2026-11-08)

Two bounded attempts against the hosted runtime from an isolated worktree of
`codex/factory-rewrite` at `02fa610`; main checkout and worker ledger untouched.

## Attempt 001 — failed, zero model calls (evidence preserved in the worktree)

`rewrite-discovery-live-001` never reached the model. The adapter invoked
`hermes chat ... --usage-file PATH`, but `--usage-file` is a **top-level-only**
flag in the installed Hermes parser (commit `2bd378e`, `_parser.py` line 154);
placed after the `chat` subcommand, argparse exits with rc=2 before any
session exists. No session, no usage file, no token spend. The adapter then
raised `TaskFailure: Model session identity is ambiguous` — the same message
covers both zero and multiple new `oneshot` sessions, so a pure startup
failure masqueraded as an attribution ambiguity. The child's captured stderr
is discarded on that path. Artifacts kept at
`/opt/data/rewrite-eval/.factory/model-tasks/rewrite-discovery-live-001/`
(`prompt.txt`, `attempt.json`).

## Attempt 002 — succeeded after a one-line argv fix

Moving `--usage-file` before `chat` (isolated worktree edit, kept separate;
Codex owns the integrated fix and has since omitted the flag entirely,
retaining measured state.db accounting) let the task run to completion as
`rewrite-discovery-live-002` under the configured allowance gate.

- Measured route: `deepseek/deepseek-v4.1-flash-1017` via provider `nous`
  (session `local-fc93513c6cd2…`).
- 9 API calls, 38,248 input / 15,892 output tokens, 206,208 cache-read,
  12 web-tool results (toolset `web`); elapsed 153.9 s inside the
  12-turn / 300 s bounds. Recorded by the adapter from
  `state.db:session_model_usage` (`usage.json`); scope is recorded route and
  usage, not provider attestation or actual spend.
- Note: even correctly placed, the top-level `--usage-file` is not written
  for the `chat --oneshot -Q` path (it belongs to the top-level `-z`
  one-shot), which is why the file-based report is absent and state.db
  accounting is the reliable measure.

## Unqualified-candidate caveat

The discovery response (`response.json`) is model output, not verified fact.
The NASA Exoplanet Archive TOI candidate remains **unqualified**: the archive
serves current-vintage parameters, and selecting only resolved dispositions
is a filtered subsample — neither may be presented as verified
"announcement-time" features or an unbiased candidate population without
fresh per-vintage evidence. Any construction must re-verify field semantics,
row vintage and terms against the live source before use.
