# Scout operational snapshot

Observed 2026-09-19T09:06:45+00:00 on the hosted coordinator. Regenerate with `python3 scripts/scout-snapshot.py`; this file is written by that script, not by hand.

## Runtime

- Hermes Agent **v0.21.3 (2026.9.14)** (upstream `345cd2b0`), install `docker` at `/opt/hermes`, Python 3.13.5.
- Source: hermes --version. Full detail in `versions.json`.

## Schedules that exist now

| job | schedule | mode | next run | last |
| --- | --- | --- | --- | --- |
| scout-telegram-delivery-test (`1a66d6af21cc`) | `once in 2m` | agent | — | ok |
| scout-secondary-cleanup-sweep (`e80975eddd4a`) | `47 * * * *` | script-only (no model) | 2026-09-19T09:47:00+00:00 | ok |
| scout-weekly-research-digest (`10d4f73308c8`) | `every monday 8am` | script-only (no model) | 2026-09-21T08:00:00+00:00 | ok |
| scout-research-session (`69a5bc676d10`) | `0 8 * * 1,3,5` | script-only (no model) | 2026-09-21T08:00:00+00:00 | ok |
| scout-budget-checkpoint-2weeks (`22ce870ec66f`) | `once at 2026-10-03 08:00` | script-only (no model) | 2026-10-03T08:00:00+00:00 | — |

Source: /opt/data/cron/jobs.json (fields allowlisted; the delivery chat identifier is not exported). All times UTC; delivery is to the chat each job was created from.
Scheduled jobs run on the coordinator's own scheduler, independently of GitHub Actions.

## Budget (estimates, not the provider's quota)

- Research (model spend): allowance 5.0 USD per month from 2026-09-01, spend so far 0.07129 USD, sessions this week 1/3.
- Workers (compute): 20 jobs on file, 5.5 EUR reserved in total; active jobs: none.
- Provider resources live now: 0 servers, 0 primary IPs.
- Coordinator disk: `/dev/vdd        5.9G  1.3G  4.3G  23% /opt/data`.
- Sources: scripts/research-budget.py --json (Hermes usage records); jobs/*.json (the worker launch ledger; only one coordinator writes it); scripts/provider-inventory.py (live API); df -h /opt/data.

## Destinations and publication state

- **github**: `https://github.com/earino/austin-911-response`, revision `v2026.09`, private=True, verified=True at 2026-09-18T22:30:00+00:00
- **huggingface**: `earino/austin-911-response`, revision `v2026.09`, private=True, verified=True at 2026-09-19T08:57:52+00:00

Licensing: code MIT, compilation CC0-1.0, source LicenseRef-Public-Domain.
Source: release/austin-911-response/DESTINATIONS.json. **Public visibility on either platform still requires the operator's approval.**

## Queue and next action

- `austin-911-response` — packaged: Await the two review decisions: a licence for the published code (and for the three benchmark runner files, whose upstream project has no licence) and authorisation to make earino/austin-911-response 
- `chicago-doah-adjudication` — parked: Operator: review Chicago's Terms of Use for redistribution. If cleared, write the split-by-docket_number construction script.
- `md-sewer-overflow` — investigating: Reconcile the 2023 overlap between 3rgd-zjxx and stgj-u72u, test the NOAA rainfall join from this host, and measure the facility-day event rate. Currency is no longer a concern.
- `melbourne-pedestrian-counts` — parked: Operator: confirm the City of Melbourne open-data licence for the Pedestrian Counting System datasets, or drop the candidate.
- `noaa-tide-flooding` — ready: Write the construction script against the frozen 122-station list in station_list_result.json and run it on a worker: labels from 6-minute water level (datum=STND) where the budget allows, streaming t

Source: candidates/*/record.json. The newest section of `STATE.md` carries the narrative.

## Recovery notes

- Reconcile before resuming: read `jobs/*.json` for non-deleted jobs and check the provider inventory above. Do not launch a second coordinator or re-run a job whose record says `running`.
- The worker allowance is counted from `jobs/*.json`; deleting records to 'tidy up' would reset that accounting. Records are evidence, not scratch files.
- Secrets are supplied at run time (dashboard environment or mode-0600 files under `.secrets/`); nothing here references a value. See `deployment/scout/README.md`.
