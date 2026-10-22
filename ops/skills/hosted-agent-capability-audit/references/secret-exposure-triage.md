# Secret exposure triage

For the question "where exactly could this be seen?" - asked after a token has appeared in tool
output, a log, an env export, or a commit. The output is an inventory with a verdict per carrier,
not a reassurance.

## 0. Handle the value without re-exposing it

- Load the live value from its file into a Python variable; compare candidates by exact match or by
  hash, and print only booleans and lengths. Never `grep` for the literal with the token on the
  command line (it lands in the shell's own history and in any env snapshot), and never echo the
  value to prove it is right.
- Search for a **distinctive substring** rather than the whole secret: a 12-char prefix plus length
  catches truncations and partial prints that a full-value search misses.
- A `grep` that finds nothing is weak evidence. Enumerate the carriers (below) and say which ones you
  actually opened; "not found" in three files is not "not present".

## 1. Carriers, in the order that matters

| Carrier | Why it holds the value | How to check |
|---|---|---|
| Transcript DB (`state.db`) | Tool results are stored verbatim, including any value the tool printed | `SELECT id, session_id FROM messages WHERE content LIKE ?`; then repeat on the FTS tables |
| Shell env snapshots | The terminal backend rewrites `$TMPDIR/hermes-snap-*.sh` on every call with the session env | `grep -l` the substring across the snapshot dir |
| `.env` and its backups | Delivery writes the variable in clear; migration/backup copies keep old generations | `grep -rl` under the home and any `backups/` tree |
| Logs and cron output | Job stdout is persisted, and a concatenation bug prints the value | search the log and cron output dirs |
| Git history and objects | A credential committed once stays in the object store after deletion | `git log -S` / `git grep` over `git rev-list --all`, plus packed objects |
| Public surfaces | Release assets, workflow logs, pages, gists | re-download and search the published bytes |
| Delivered messages | Anything sent to chat is out of your control | check the outbound record, then treat it as permanent |
| Model-provider payload | Every tool result travels to the provider with the request | decide from the provider's retention policy; you cannot search it |

Classify each hit: **full value**, **prefix / partial** (record the length shown), or **at-rest copy**
(a file that legitimately holds the secret). A prefix is still an exposure - it narrows a guess - but
it does not authenticate on its own; say which it is instead of lumping them together.

## 2. Redact, then state the residue

- `UPDATE` the row to a placeholder, then check the FTS tables - they hold their own copy and are not
  updated by the base-table write in every schema.
- `PRAGMA wal_checkpoint(TRUNCATE)` after the write, then re-count occurrences in the file.
- Deleted content survives in freelist pages until `VACUUM`. Do not vacuum a large live database for
  one page; report the count and say you left it, because "0 occurrences" would be false.
- `PRAGMA integrity_check` after a direct write, and re-open through the normal API to prove the
  database still serves.

## 3. Decide rotation from egress, not from alarm

Rotation is forced by **off-box retention**, not by the exposure itself:

- Value reached a public surface, a third party, or a provider that retains request payloads -> rotate
  now; assume it is already copied.
- Value existed only in 0600 files on a single-tenant container, and the provider is logless -> rotation
  is hygiene. Record the decision, and if it is deferred, schedule a dated reminder job so it is not
  re-litigated every session.
- Partial value only (a prefix, a length) -> not a working credential; note it and move on.

Write the reasoning into the state file, per carrier, so the next session does not redo the audit or,
worse, re-open a closed question.

## 4. Stop the source before cleaning the copies

Deleting the snapshot files alone fixes nothing: the backend rewrites them on the next call. Unset the
export, delete the stale files, then trigger a new call and verify the **fresh** snapshot contains none
of the names. Confirm the consumers read from credential files (`*_FILE`) so removing the exports
breaks nothing, and check every consumer, not just the one you were debugging.

Exports are the defect. A secret that is only ever read from a mode-0600 file at the point of use has
no disk copy to clean up, and `env | grep -c '^NAME='` returning 0 is the check that says so.
