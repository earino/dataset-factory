# Budget restore to normal limits (2026-11-16)

Eduardo authorized ending the temporary 10x research window and restoring normal budgets.
Applied 2026-11-16T18:30:55Z. Read-only state inspection before and after; no candidate,
dataset, acceptance-rule or study-evidence change.

## Effective budgets

| budget | before | after |
|---|---|---|
| model allowance | USD 300.00/month | **USD 30.00/month** |
| weighted sessions | 2,000/week (fresh epoch) | **200/week** (historical count) |
| normal tokens | 400,000,000/week | **40,000,000/week** |
| worker allowance | EUR 50/month (reserve 5) | **EUR 20/month** (reserve 5) |

Temporary window: `from 2026-11-12T21:17:36Z`, `until 2026-11-16T18:30:55Z` (planned
2026-11-20T23:00Z superseded). The record and all measured usage are preserved; effective caps
resolve to normal immediately.

Tracked change: `04f26c0` (`config/research-budget.json`), CI Local checks `43930068809` success.
Worker allowance is private (`config/local.json`), changed 50 -> 20.

## Gate state after change

`allowed: false` — 762 normal-operation sessions > 200/week; 75,969,194 normal tokens >= 40,000,000.
Normal admission therefore holds new work. In-flight work continues.

## Charged usage (2026-11)

`monthly_usage`: completed 40.88 EUR (504 jobs) + retained 0.20 EUR (2 records) = **41.08 EUR**;
construction cap 15 EUR (20 - 5), headroom **-26.08 EUR** — no new construction admitted.

## Cron

- Retired `dc8f49ebff51` (Nov-20 23:00 expiry) so it cannot restore EUR45.
- Preserved `ca002a2e360e` Dec-1 00:00Z reset; tick, cleanup sweep, dashboard refresh and
  release-notify remain enabled.

## Active work

`rw-3eb6f2fd6f71-build-3` running (server 176373406) — allowed to finish; cleanup sweep enabled.
