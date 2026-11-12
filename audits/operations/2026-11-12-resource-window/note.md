# Temporary resource window — deployment and readback (2026-11-12)

Scout (Hermes) executed; root authored and CI-verified `6238b7d`; Eduardo authorized the
window (fresh session epoch, 2000 weighted sessions/week, 400M normal tokens/week,
USD300 estimate, through 2026-11-20T23:00Z) and the corrected **EUR 50 total** worker
allowance (an earlier 450 instruction was corrected before anything was set).

## Deploy

- CI `43309480626` (Local checks) verified success at exactly
  `6238b7dca455b2ec87b1602dd7fa1caad8201`; fast-forward at a tick boundary, 21:24:15Z.
  Private `config/local.json` (EUR 50 worker allowance), `pipeline.sqlite3`, and
  `history.json` preserved; 0 tracked modifications; shim hash unchanged (`d8962179…`).
- Live gate decision after deploy: `allowed=true`, `session_count_reset_at
  2026-11-12T21:17:36.832062Z`, `session_admission_weighted 0`, cap 2000, 400M tokens,
  USD300; full historical 7-day counts preserved (200 weighted, 29.57M tokens).

## Expiry proof (temp-copy tests, `gate-decisions.json`)

- Window shifted to the past → caps restore automatically to **200 / 40M / USD30**,
  `temporary_resource_window.active=false`, historical weighted count (200) applies again.
- Window shifted to the future → normal caps before start; nothing activates early.

## Worker allowance chain

- Live: `monthly_budget_eur 50`, reserve 5, max_workers 1, per-task bounds unchanged.
- `dc8f49ebff51` (no-agent, one-shot 2026-11-20T23:00:00Z, catch-up on missed fire):
  50 → 45 only if still 50. `ca002a2e360e` unchanged: 45 → 20 only if still 45.
  Chain: 50 →(Nov 20) 45 →(Dec 1) 20. Script copy: `scout_worker_allowance_expiry.py`.

## Scheduler resume — no manual state advance (`scheduler-resume-proof.json`)

- Before deploy (21:23:02Z): s41 held at discover by the 200-weighted session cap,
  backoff to 22:20:01Z; s42 FRA build-2 worker running.
- After deploy, ticks alone: backoff cleared; the 21:30:00–21:35:01 tick ran the held
  `rw-080e85a65cfd-discover-3` session to done and advanced s41 **discover → build**
  (~50 minutes ahead of the old backoff); s42 build-2 was collected (retry, artifacts
  preserved, worker deleted) and re-queued normally. Zero candidate/attempt writes by me.
- Published total is now 7 (5 modern Nov 9–10, s36 on 11-11, s39 on 11-12).

## Dashboard

One post-deployment refresh triggered: commit `766cc7b`, generated 21:24:41Z, anonymous
verify ok on every page (new gate fields visible). The 21:50Z hourly refresh continues
automatically and will show the post-resume stages.
