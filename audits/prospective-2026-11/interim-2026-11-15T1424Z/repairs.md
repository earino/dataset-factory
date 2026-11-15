# Defect repairs / interventions during cohort window

## Export tooling (2026-11-12, corrections to initial snapshot 9b530351)
- sanitizer redacted numeric token counts (input_tokens etc. matched a bare 'token' rule); now credential-shaped keys only - numeric usage preserved
- jobs export used nonexistent started/finished fields; now exports created_at/collected_at/deleted_at and derives duration when both ends exist
- cohort wrongly excluded all carry-in candidates; now only pre-window published releases are excluded (verified publication timestamp inside window, publication order)
- repeat close export made rerun-safe (mkdir exist_ok, earlier labels untouched)
- CI check reports all workflow runs and non-success explicitly

## Protocol amendment (2026-11-15; corrected same day)
- Close export moved from 2026-11-17T17:00Z to **2026-11-16T07:00Z (08:00 Paris)**; an
  intermediate 2026-11-15T17:00Z cutoff was superseded because dataset collection continues
  into the morning of 2026-11-16. Authorized by Eduardo (travel Nov 17-20; paper due Nov 16).
  Recorded after partial results were observed. Cohort definition unchanged: start
  2026-11-12T21:27:59.319944Z, first 12 newly published IDs in publication order including
  carry-in candidates; all outcomes and failures retained. No export ran on 2026-11-15.
  Administrative only — no factory, allowance or admission change.

## Factory workflow
- none within the cohort window so far (pre-window context: 6238b7d research-window deploy incl. b8770b3 stale-inventory fix; 8fa9fc4 catalogue README retry fix). Repo commits during the window: window_commits.json
