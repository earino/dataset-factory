# Protocol amendment 2026-11-15 — close export moved to 2026-11-15T17:00Z

**Authorized by Eduardo** (travels 2026-11-17..20; paper must be written and submitted
2026-11-16). Administrative only. Recorded **after partial results were observed**.

## Change

- Close export moved from **2026-11-17T17:00Z** to **2026-11-15T17:00Z (18:00 Paris)**.
- Executed by updating the existing one-shot job **d35f2e1ec147 in place** (no new job, no
  recurring trigger, no duplicate). Schedule readback: `once at 2026-11-15 17:00`,
  `next_run_at 2026-11-15T17:00:00+00:00`, `repeat 1/1`, script `scout_prospective_export.py`,
  `no_agent: true`.
- Export script `COHORT_CLOSE` updated to `2026-11-15T17:00:00+00:00`; `COHORT_START`,
  `COHORT_SIZE`, evidence branch and output path unchanged.

## Cohort definition (unchanged)

Start **2026-11-12T21:27:59.319944Z**; first **12** newly published IDs in publication order,
**including carry-in candidates** published inside the window; only the seven releases already
published before cohort start are excluded. All outcomes, failures and interventions retained.
The 2026-11-15 boundary is later than any partial-result cutoff, so the eight releases below
remain in the cohort.

## Partial results observed at amendment time (2026-11-15T09:00Z)

8 releases published in the window, all in publication order:

| # | id | dataset | published_at |
|---|---|---|---|
| 1 | source-000048 | fjc-civil-trial-36m | 2026-11-13T02:30:19Z |
| 2 | source-000053 | eia861-reliability-deterioration | 2026-11-13T05:28:19Z |
| 3 | source-000055 | phmsa-pipeline-penalty-reduction | 2026-11-13T07:53:15Z |
| 4 | source-000064 | fda-510k-five-year-recall | 2026-11-13T23:42:15Z |
| 5 | source-000068 | t100-new-route-survival | 2026-11-14T02:04:19Z |
| 6 | source-000072 | sbir-phase1-to-phase2-conversion | 2026-11-14T04:36:15Z |
| 7 | source-000079 | caa-fce-hpv-escalation | 2026-11-14T22:55:16Z |
| 8 | source-000083 | wser-effluent-exceedance | 2026-11-15T01:17:16Z |

No acceptance rule, admission threshold or cohort boundary was changed for the study.

## Study schedule (amended)

- research stops: **2026-11-16T01:00Z**
- analysis starts: **2026-11-16T02:00Z**
- draft: **2026-11-16T08:00Z**
- author review package: **2026-11-16T11:00Z**

## Related records

- Budget accounting deployment `2157157` is logged as a development intervention at
  `audits/prospective-2026-11/interventions/2026-11-14-worker-budget-accounting.md`.
- Initial and corrected snapshots (`initial/`, `initial-corrected/`) are retained untouched.
- Factory production, worker allowance (EUR50) and the 2026-11-20T23:00Z expiry are unchanged;
  the factory keeps running normally.

## Correction 2026-11-15 (later same day): close export moved to 2026-11-16T07:00Z

Eduardo corrected the premature cutoff: dataset collection continues through the morning of
2026-11-16. The single one-shot job `d35f2e1ec147` was updated in place again — `once at
2026-11-16 07:00`, `next_run_at 2026-11-16T07:00:00+00:00`, script-only. No export ran on
2026-11-15 and no 2026-11-17 trigger remains.

Study timing now: research permitted through **2026-11-16T10:00Z**; final analysis then; author
review package on the afternoon of **2026-11-16** for submission.

Cohort definition, the partial-results record above, initial/corrected snapshots and all
outcomes remain unchanged. Factory production, worker allowance and the 2026-11-20 expiry are
untouched.
