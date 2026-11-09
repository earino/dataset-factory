# Federal Register source-16: build-5 saved proposal, build-6 repair, deferral

Exported 2026-11-09T19:19Z from live coordinator state and retained model-task
files. No candidate state, retry bound, worker or limit was modified for this
export. Root's independent read of both staging outcomes is commit `4ee6f77`
(CI 42677769846).

## Timeline (all 2026-11-09 UTC)

- 18:54:01 build-5 worker launched from the saved build-5 proposal (server
  175344881, EUR 0.16 reservation) once the monthly allowance was 45. Failed
  gate 1.6.1 after 343.2 s: 8 declaration failures — root-verified quality
  metadata regressions (use/training_label_timing/vintage moved out of
  `evaluation_contract`; `features_documented_at`/`high_cardinality_columns`
  lost; `carry_columns` empty while publication_date ships;
  `label_source_columns` includes publication_date; instant D/0). Release
  439516409, manifest 728607727, qualification 728607354, quality 728607185.
  Closed 19:03:26; artifacts preserved; worker deleted.
- 19:05:01 build-6 repair model task started. The prompt carries the
  declaration-failure details, the saved build-5 proposal and the schema
  example (verified present: evaluation_contract, features_documented_at,
  high_cardinality_columns, carry_columns, label_source_columns,
  training_label_timing, vintage, publication_date, declaration).
- build-6 response (29,420 bytes) validated; worker launched 19:06:56
  (server 175346567, EUR 0.16): 328.6 s, failed only
  `contract.vintage_and_selection`, `contract.label_availability`,
  `timing.every_feature_documented`. Release 439529336, manifest 728649260,
  qualification 728648876. Closed 19:15:21; artifacts preserved; worker
  deleted.
- 19:15:21 source-000016 **deferred** at the five-completed-worker bound
  (builds 1, 2, 3, 5, 6). The normal deferral is preserved; nothing was reset.

## Measured model usage (requested route deepseek/deepseek-v4.1-flash-1017, provider nous)

- build-5: 2 calls, 21,782 input / 13,045 output tokens (title generation +
  write-only construction call).
- build-6 (repair): 2 calls, 24,148 input / 16,173 output tokens.

## Files

- `build5-response.json` / `build5-usage.json` — the saved proposal used by
  the 18:54Z worker.
- `build6-prompt.txt` / `build6-response.json` / `build6-usage.json` — the
  next repair (attempt build-6).

## Coordinator state and next work

- Allowance readback 19:18:53Z: `monthly_budget_eur` 45, `release_reserve_eur`
  5. November reservations including the build-5/6 workers: EUR 15.18 of the
  40.00 construction cap. Per the operator clarification, the extra EUR 25
  stays usable through the November budget; EUR 20 is restored on 2026-12-01
  via the existing deterministic one-shot scheduler, not at signoff and not
  via a new budget subsystem.
- Tick `07d6f8be3783` and cleanup `e80975eddd4a` active; legacy launchers
  paused. Bridge source-15 and BSEE source-17 remain deferred at their bounds;
  source-18 proceeds normally through the queue.
- Root is moving the existing data-independent declaration predicates into a
  shared gate helper so construction rejects this class before a paid worker
  launch, retaining paid drafts as the engine already does; same predicates,
  no new gate, waiver or acceptance claim; repair prompts keep the schema
  example to avoid blind metadata reconstruction. Deployment only at a safe
  boundary after green CI.
