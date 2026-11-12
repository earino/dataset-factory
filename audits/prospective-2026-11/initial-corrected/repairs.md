# Defect repairs / interventions during cohort window

## Export tooling (2026-11-12, corrections to initial snapshot 9b530351)
- sanitizer redacted numeric token counts (input_tokens etc. matched a bare 'token' rule); now credential-shaped keys only - numeric usage preserved
- jobs export used nonexistent started/finished fields; now exports created_at/collected_at/deleted_at and derives duration when both ends exist
- cohort wrongly excluded all carry-in candidates; now only pre-window published releases are excluded (verified publication timestamp inside window, publication order)
- repeat close export made rerun-safe (mkdir exist_ok, earlier labels untouched)
- CI check reports all workflow runs and non-success explicitly

## Factory workflow
- none within the cohort window so far (pre-window context: 6238b7d research-window deploy incl. b8770b3 stale-inventory fix; 8fa9fc4 catalogue README retry fix). Repo commits during the window: window_commits.json
