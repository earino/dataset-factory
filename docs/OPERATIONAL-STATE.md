# Operational observations and the current view

`STATE.md` is generated from candidate records, job ledgers, admission configuration
and recent structured observations. It is below 20 KB and carries an input digest.
It reports repository state, not a provider query or an approval. A stale view
cannot authorize work. Run `python3 scripts/operational-state.py --check` on resume;
if records advanced, run `--render` and inspect the refreshed view.

Keep the next action in the affected candidate record. Record meaningful observations
in an append-only monthly JSONL log with the following JSON schema:

```json
{
  "id": "stable-observation-id",
  "actor": "Scout (Hermes)",
  "time": "2026-11-07T20:00:00Z",
  "candidate": null,
  "job": null,
  "kind": "cleanup-readback",
  "outcome": "Describe the observed result, limitations and next action.",
  "evidence": [{"path": "audits/path-to-real-report.json", "sha256": "<computed digest>"}],
  "commit": "<full existing commit containing the source or evidence>"
}
```

The example is a schema illustration, not a recorded cleanup result. Use current UTC
observation time, a stable unique ID, the actual actor and an existing commit. Evidence
is an exact repository path with a computed digest; files must be compact, regular,
nonhidden and present when appended. Never include credentials or raw dataset rows.

```sh
python3 scripts/operational-state.py --append /path/to/event.json
python3 scripts/operational-state.py --render
python3 scripts/operational-state.py --check
```

An identical observation ID and content is a no-op. Reusing the ID with different
content, backdating an append, missing/changed evidence, symlinks and partial log
lines refuse. A filesystem lock serializes local appenders. Every event binds the
previous chain digest; CI also verifies that pre-existing log bytes remain a prefix,
so rewriting a whole valid chain does not pass. If concurrent branches append from
the same chain head, preserve both observations and serialize the merge; never
silently drop one or rewrite history already on the target branch.

Historical event references remain historical when candidate files later change.
The event is an observation, not proof that its content is true, not an operator
approval and not a current passing qualification receipt. Those checks remain at
their existing boundaries. Correct a mistaken claim with a new evidence-backed
event naming the earlier ID; do not edit the old event.

The existing narrative was partitioned by heading month under `docs/state-archive/`
without editing its bytes. Unheaded text and duplicate/out-of-order entries are
preserved. The archive manifest records source ordering and per-part offsets,
lengths and hashes, allowing exact reconstruction of the original file. `--check`
verifies reconstruction; CI refuses changes or removal of archived files.

This addresses a measured failure: follow-up commit 451516f replaced 17,771 old
STATE lines with its own entry. Codex restored the previous bytes in 528154a while
preserving that follow-up. Keeping the narrative unchanged in an archive and
generating the active view prevents another successful close-out from silently
discarding prior context. The generator caps each displayed section and names
omitted counts and source directories; detailed records remain available.

After a worker status/collection/cleanup change, refresh the view before committing.
Only the sole worker coordinator launches jobs; changing branches must never hide
reservation ledgers. The generated view does not solve that ledger boundary by
itself. Mechanical watcher reconciliation is a separate implementation item.
