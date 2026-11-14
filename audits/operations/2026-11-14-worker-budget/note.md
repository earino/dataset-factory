# Worker budget accounting correction (2026-11-14)

Deployed `2157157` after exact-commit CI success (Local checks 43621546533), fast-forward at a tick
boundary. Private config (EUR50/EUR5 reserve/expiry) and pipeline state preserved; no candidate or
attempt writes.

## Accounting change (readback)

- Old reservation total for 2026-11: **EUR44.94 / 292 records** — full reservations were summed
  regardless of job status.
- New `factory.worker_budget.monthly_usage` at deploy: completed estimate **EUR23.84** (291 jobs,
  `max(1, ceil(lifetime hours)) x rate_ceiling_eur`), retained reservations **EUR0.04** (1 uncertain
  record), charged **EUR23.88**; construction headroom **EUR21.12**.
- Provider-rate whole-hour estimate: **EUR18.9913**; dashboard `month_to_date` (created-at basis):
  **EUR18.92**.
- Overruns would exceed a reservation only if a confirmed lifetime exceeds it; no rewrite of
  original job records occurs.

## Resume proof

Both build candidates were blocked before deploy by the construction cap. The ordinary tick at
17:34:02Z launched `rw-b6daec6d3aba-build-3` (candidate `epa-biosolids-part503-violation`,
server 176122558 **running**), reservation 0.16 at the 0.08 ceiling, 60-minute lifetime. No manual
state writes, no second coordinator. `source-000074` (`us-house-bill-house-passage`) stays queued
under the one-worker rule. Post-launch charge 24.04, headroom 20.96.

## Dashboard

One refresh published (commit `5e768b2`, generated 17:34:35Z) and verified anonymously over HTTPS:
month_to_date 18.92, admission accounting 24.04 (23.84 completed + 0.20 retained for 2 jobs),
construction headroom 20.96; resources page shows the admission line. Estimates, not invoices.
