# Sites-integration inventory (read-only) — 2026-11-11

Collected by Scout (Hermes) in the main session, 2026-11-11 10:35–10:40 UTC, for the
FACTORY-SITES-INTEGRATION S1–S8 work requested by the user (Eduardo relaying Codex/root).

Method: strictly read-only. SQLite opened `mode=ro`; GitHub and Hugging Face queried for
account names and permission booleans only; the live dashboard was fetched anonymously.
No candidate state writes, no builds, no deploys. The deployed working tree was untouched —
this branch was assembled in a separate scratch worktree based on `origin/main`.

- Deployed code at collection: `2bf708a5096698fd9c2ade9978fe8646cd9dd241` (main, unchanged).
- Branch base: `29ed4f1` (carries `docs/FACTORY-SITES-INTEGRATION.md` at `70ce430` and
  `factory/site_state.py`).

## Files (each < 256 KiB; largest ≈ 85 KB)

- `modern-state.json` — `factory/site_state.py` `snapshot()` (root's canonical read-only
  projection, imported from 29ed4f1) run against the live database: status ok; counts
  deferred 25 / rejected 5 / published 5 / build 1 / discover 1; observed 10:35:28Z.
- `candidates-attempts-compact.json` — all 37 candidates and 248 attempts: ids, stages,
  statuses, timestamps, controller reasons. `data` and attempt `result` payloads excluded.
- `publication-receipts.json` — receipts for the 5 published releases; `publication_matches()` is
  True for all five. source-000013 → `factory-ucmr5-first-sample-pfas`, source-000018 →
  `factory-cfpb-bank-account-monetary-relief`, source-000020 → `factory-nhtsa-pe-recall`,
  source-000024 → `factory-fdic-bank-branch-closure`, source-000028 →
  `factory-nih-r01-competing-renewal`. GitHub + Hugging Face, anonymous consumers.
- `runtime-flags.json` — effective flags from deployed `config/local.json`
  (pipeline_enabled true, max_workers 1, monthly_budget_eur 45, release_reserve_eur 5,
  release_preempts true, allowed_locations [hel1], max_job_minutes 120, max_lifetime_minutes 180,
  cleanup_grace_minutes 60, staging_repo earino/dataset-factory-staging; ssh_private_key redacted)
  plus tracked defaults for contrast (`config/pipeline.json` `enabled: false`),
  `config/sites.json`, `config/research-budget.json`, and the current admission decision
  (allowed=false on the weekly session cap; normal tokens 35.17M of 40M).
- `dashboard-cron.json` — cron readback: factory tick `07d6f8be3783` (last 10:28:01Z ok),
  cleanup sweep `e80975eddd4a` (10:20:01Z ok), release-notify `ba4c8610edf8` (09:55:01Z ok),
  dashboard-refresh `4d8053a69ed2` (09:51:28Z ok, next 10:50Z); three legacy launchers paused;
  Dec-1 allowance reset `ca002a2e360e` scheduled. Publisher: `/opt/data/scripts/scout_dashboard.py`
  → `scripts/build-dashboard.py --publish` → `earino/dataset-factory-dashboard` main, verified
  anonymously. Dashboard repo HEAD `25e5956` (snapshot 2026-11-11T09:50:01Z); catalogue repo
  `earino/dataset-factory-site` HEAD `a91c2d5` (2026-11-03).
- `site-publisher-permissions.json` — `github-publish.token` account `earino` holds admin on
  `earino/dataset-factory`, `dataset-factory-dashboard`, `dataset-factory-site` and all five
  `factory-*` release repos (all public, default branch main); Hugging Face write account `earino`.
  Token values were never read into any output file.
- `existing-site-receipts.json` — legacy `.factory/sites/` receipt registry: 15 sites, read-only.
- `deployment-identity.json` — deployed vs origin identity at collection time.

## Facts for the adapter (S1–S2)

- The modern pipeline is fully publish-verified: 5/5 published candidates pass
  `publication_matches()` (artifact/version identity, both anonymous consumers, row counts).
- The live public `dashboard.json` (2.2 MB, generated 09:50:01Z) shows 22 legacy releases and
  149 legacy candidate records; none of the 5 modern releases appear in it, so modern
  candidates/releases are not yet connected to the dashboard/catalogue collectors. Its budget
  panel also shows the stale `allowance_usd: 30.0` display already recorded in
  FACTORY-SITES-INTEGRATION.md.
- No site-publisher permission gaps: the existing credential already has full push/admin on
  every current destination (dashboard, catalogue, and the five `factory-*` repos).
- The legacy site receipt registry (`.factory/sites/`, 15 sites) is intact for adapter reuse.

## Sanitization

No secret values, raw diagnostics, or model payloads are included. Only account names,
permission booleans, public repo URLs, public tracked configuration, and controller reason
strings. `ssh_private_key` is the only redacted field. A regex scan for token/key shapes
across all files found nothing.
