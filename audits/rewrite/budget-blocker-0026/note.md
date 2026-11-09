# Budget admission blocker — exact live figures

Measured 2026-11-09T00:25:53Z from the live coordinator (`.factory/pipeline.sqlite3`,
`jobs/*.json` ledger, tick outcome, `config/local.json`). No state was changed to
produce this export.

## The exact blocker

Every construction worker launch is refused by the conservative monthly
reservation gate in `factory/worker.py` (`launch`, spent + reservation > cap):

| Figure | Value | Source |
| --- | --- | --- |
| November reserved total | **EUR 14.86** | 110 job records with `2026-11` in `budget_months` (deleted jobs count; the accounting is conservative by design) |
| Construction boundary | **EUR 15.00** | `monthly_budget_eur` 20.00 − `release_reserve_eur` 5.00 (`config/local.json`) |
| Remaining headroom | **EUR 0.14** | 15.00 − 14.86 |
| Next FR worker reservation | **EUR 0.16** | standard recipe: `rate_ceiling_eur` 0.08/h × 2 h lifetime; every November record reserved exactly 0.16 |
| Result | **15.02 > 15.00** | over by **EUR 0.02** |

Exact last admission error (identical in the tick outcome, the candidate record
and attempt `rw-ba904118ba27-build-5`, last observed at 00:20:01Z, retried every
300 s without model cost):

> Conservative monthly cost reservations would exceed the construction allowance
> (EUR 15 after the EUR 5 release reserve)

Effect: under the unchanged boundary, **no construction worker can launch until
2026-12-01** (new budget month). Release jobs keep the full EUR 20.00 cap, so
release/publish work remains admissible; construction does not. The EUR 5
release reserve is intact and untouched.

## Live candidate state at 00:25:53Z

- **source-000016 (Federal Register, `rw-ba904118ba27`)**: attempt `build-5`
  running since 23:42:01Z, waiting on the cost gate with a **saved valid
  proposal** (response landed 23:43Z; no new model calls while waiting).
  Correction to the earlier handoff: build-4's 48 KB response failed validation
  ("Construction descriptor lacks target"); the usable saved code is build-5's.
  Workers build-1/2/3 each failed qualification (build-3: NaN agency-rate
  fallback before qualification); the build-5 proposal is the ordinary repair.
- **source-000017 (BSEE, `rw-f5c98eaf9558`)**: worker build-4 passed full
  qualification (measured, all 33 package bindings); evaluate-1 returned
  **repair** (COMPLEX_ID_NUM row keying drops 102 structures; authority filter
  wrong; split-membership/independence claim unsound). Repair builds 5–9 all
  failed Python parsing (same unmatched-`}` class); the fifth task failure at
  build-9 (00:14:49Z) reached the attempt limit and the candidate is
  **deferred**. No reset was made. Review position stands: the three material
  defects are the repair scope; unmaterialized base-rate references do not
  require new features or historical-forecast proof for this retrospective
  claim.
- **source-000015 (bridge)**: deferred at five worker failures; unchanged.

## Coordinator health

Tick `07d6f8be3783` active (every minute, exit 0); cleanup `e80975eddd4a`
active (*/10, exit 0); legacy launchers `86fe52e55ef9`, `69a5bc676d10`,
`98b45d983280` paused since 2026-11-08 12:19 UTC. No candidate state, retry
count or boundary was modified; no child was killed. BSEE build-9 was the last
paid child and completed on its own.

## Consequence for A4

The second benchmark cannot receive a construction worker in November under the
current boundary. Options are the operator's: keep the EUR 15 construction
boundary and let FR build-5 launch automatically on 2026-12-01 from its saved
proposal (no action needed; nothing is lost by waiting), or authorize a change.
Scout leaves the boundary as instructed and does not raise it.
