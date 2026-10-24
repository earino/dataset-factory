# Curator skill drift — 2026-10-22

Preserved as an exact patch. **Not applied, not discarded.** The two edits still sit uncommitted in
the live working tree of `/opt/data/dataset-factory`; this branch carries only their patch and the
evidence needed to review or replay them.

## Base

| Field | Value |
| --- | --- |
| Base commit | `beab726` (branch `main` when captured) |
| Patch | `ops/curator-drift/2026-10-22-skills.patch` (47 lines, `git diff` output) |
| Applies cleanly | `git apply --check` on `beab726` → clean |
| Captured | 2026-10-22T17:45Z |

## Files

| File | sha256 before (HEAD) | sha256 after (working tree) | Change |
| --- | --- | --- | --- |
| `skills/dataset-release/SKILL.md` | `204be38a00f94ff4…` | `f5f9d5e477718c21…` | +17 lines |
| `skills/dataset-qualification/SKILL.md` | `b66da17ecd7c4c5d…` | `7aa3b85fe8bb06f7…` | +1 line |

## What changed

- **dataset-release**: a new section, *"A reproducible claim is not a true claim"* — reproduce the
  bytes proves the pipeline, not the story; check every performance claim against a domain baseline
  computed on the published bytes; state claims at the resolution the split supports. Two rows were
  added to the failure table (a published claim no baseline supports; a horizon claim the split
  cannot support).
- **dataset-qualification**: one row added to the failure table — "the document promises a horizon
  the evaluation never measured" (metric computed on daily/weekly rows while the prose claims an
  end-of-month or longer-range outcome).

## Provenance

`/opt/data/skills/.curator_ledger.jsonl` records three relevant actions by `actor: curator`:

| Time (UTC) | Target | Action |
| --- | --- | --- |
| 17:20:05 | profile skill `agent-handoff-packaging` | `write_file` `templates/refactor-brief.md` |
| 17:20:15 | profile skill `agent-handoff-packaging` | `patch` |
| 17:31:42 | `dataset-release` (external, in-repo) | `patch` |
| 17:31:42 | `dataset-release` (external, in-repo) | `patch` |
| 17:32:16 | `dataset-qualification` (external, in-repo) | `patch` |

No profile copies of the `dataset-*` skills exist, so nothing shadows them. The gate is untouched:
`GATE_VERSION` is `1.4.0` and `skills/dataset-qualification/scripts/qualify_dataset.py` still hashes
`4e51d2e9494fd66d`.

## Later profile-skill drift (17:48Z)

The curator made three further edits to profile skills after this capture; their diffs are preserved
in `profile-2026-10-22T1748/` with before/after hashes and mtimes. They are file diffs, not a Git
patch, because those skills have no Git baseline.

## How to use this branch

Review the patch on its own. To replay it on a checkout of `beab726`:

```bash
git checkout beab726
git apply ops/curator-drift/2026-10-22-skills.patch
```

Do not apply it to `main` as part of an unrelated change: these are unreviewed, content-only edits
and the live working tree already contains them. This branch exists so they can be evaluated,
committed deliberately, or reverted deliberately — not lost by a checkout.
