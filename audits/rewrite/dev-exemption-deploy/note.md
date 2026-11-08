Development-exemption deploy confirmation (2026-11-08 15:54:23Z).
Deployed SHA d29c11a7b90c178e86056c7acc278765a343267b (exact-commit CI
42496565927 success per operator; clean checkout 930 tests / 13 skipped).
config/research-budget.json confirmed live on the deployed checkout:
weekly_token_budget 40000000 retained, plus
development_token_exemption_until 2026-11-08T19:07:00Z with the recorded
operator authorization ("Eduardo authorized development without the
normal-operation 40M token ceiling on 2026-11-08. Expires at the current
rewrite timebox; measured usage is retained."). The gate measures usage and
ignores the weekly ceiling until expiry; normal enforcement returns
automatically. All other limits unchanged (worker EUR/resource caps, task
turns/seconds, session caps). No state reset; queue continues.

Observed in the same window (read-only): source-000009 build-1 exhausted
the wall clock mid main-generation (partial usage: title call only,
446 in / 11 out, 330.1 s); build-2 completed the generation (2 calls,
5,842 in / 47,718 out, 317.7 s, 17,889-byte build_py) but the controller
rejected the construction at validation - "Construction Python does not
parse" - a substantive defect now queued for bounded repair. source-000010
build-1 worker launched and running at export time.
