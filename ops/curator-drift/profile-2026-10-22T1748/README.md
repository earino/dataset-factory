# Profile skill drift — 2026-10-22T17:48Z

The curator kept editing profile skills **during this review**. These are the diffs between the
copies vendored in `ops/skills/` (captured 17:30Z) and the live files at 17:48Z. Preserved here so
none of that work is lost when the vendored copies are next refreshed.

Patches are plain `diff -u` (the live files are not in Git, so there is no commit to diff against).
Paths in the headers are the local paths used at capture time.

| File | Before (vendored) | After (live, 17:48Z) | Patch |
| --- | --- | --- | --- |
| `open-data-source-vetting/references/release-packaging.md` | `7de40888…` (8,668 B) | `3ca5e706…` (10,939 B) | `open-data-source-vetting_references_release-packaging.md.patch` (42 lines) |
| `open-data-source-vetting/references/artifact-qualification.md` | `86d9fad1…` (6,112 B) | `0cbe4798…` (7,822 B) | `open-data-source-vetting_references_artifact-qualification.md.patch` (40 lines) |
| `agent-handoff-packaging/SKILL.md` | `9b9c8d10…` (15,376 B) | `fccd7ed5…` (18,651 B) | `agent-handoff-packaging_SKILL.md.patch` (72 lines) |

Live mtimes: 17:41:28Z (release-packaging), 17:47:48Z (agent-handoff SKILL), 17:48:08Z
(artifact-qualification). Curator ledger entries exist for each.

## Why these are separate from the 17:31–17:32 patch

`../2026-10-22-skills.patch` is the **repository** skill drift (`dataset-release`,
`dataset-qualification`) against base `beab726`. These three are **profile** skills with no Git
baseline, so they are captured as file diffs and cannot be replayed with `git apply`.

## Status

Not applied, not blessed, not discarded. The live files still hold these edits. The vendored copies
in `ops/skills/` remain the 17:30Z versions on purpose: refreshing them would make the runtime audit
green and hide the change. A refresh should be its own review commit that shows the diff.
