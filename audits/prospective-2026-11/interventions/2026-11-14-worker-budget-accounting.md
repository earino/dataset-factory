# Intervention: worker budget accounting correction (2026-11-14)

**Type:** development intervention — accounting only. No change to cohort definition,
acceptance rules, candidate selection, or study outcomes.

## What changed

Commit `215715771b1c93f474cc7a8a223c732bf4710266` (CI Local checks 43621546533, success)
replaced reservation-summing with `factory.worker_budget.monthly_usage`:

- confirmed deleted workers are charged `max(1, ceil(lifetime hours)) x rate_ceiling_eur`
  (Hetzner bills whole hours, rounding up);
- active, unidentified and incomplete records keep their full original reservation
  (`retained_reservations_eur`);
- overruns are counted as recorded; original job records are never rewritten;
- EUR50 total / EUR5 release reserve and both expiry schedules are unchanged.

## Why

Reservations were retained forever at the worst-case ceiling. November read 44.94 EUR
reserved while the provider console billed 16.21 EUR, and the EUR45 construction cap
left EUR0.06 headroom, blocking both build candidates. The dashboard's previous
fractional estimate (4.94 EUR) also understated whole-hour billing.

## Readback at deploy (2026-11)

| figure | value |
|---|---|
| old reservation total | 44.94 EUR / 292 records |
| new charged (monthly_usage) | 23.88 EUR = 23.84 settled (291 jobs) + 0.04 retained (1 record) |
| provider-rate whole-hour estimate | 18.9913 EUR |
| dashboard month_to_date (created-at basis) | 18.92 EUR |
| construction headroom | 21.12 EUR |

Resume: the ordinary tick launched `rw-b6daec6d3aba-build-3` at 17:34:02Z
(server 176122558 running) with no manual state writes; the second candidate stayed
queued under the one-worker rule. Dashboard refreshed once (commit `5e768b2`) and
verified anonymously.

## Effect on study accounting

Candidate and attempt records are unchanged: all attempts, failures and interventions
remain exported. Future close exports include this commit in `window_commits.json`;
the admission figures in this note are the authoritative record of the correction.
No acceptance threshold, cohort boundary, or publication decision was touched for the
study.
