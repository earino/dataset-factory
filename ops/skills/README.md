# Custom skills — vendored

The profile skills that carry this project's operating knowledge. They live in the Hermes profile
directory (`/opt/data/skills/<category>/<name>/`), **not in the factory repository**, so this export
is their only Git copy. Copied 2026-10-22T17:50Z; use counts from `hermes curator usage`.

| Skill | Uses | SKILL.md sha256[:16] | Files |
| --- | ---: | --- | ---: |
| `open-data-source-vetting` | 38 | `ef66694f788d4ba7` | 6 |
| `scheduled-job-verification` | 36 | `2cde10e808ab939b` | 3 |
| `multi-destination-publishing` | 33 | `728bd4f33a08f848` | 4 |
| `ephemeral-worker-lifecycle` | 32 | `1d553d29d130156e` | 4 |
| `validation-gate-design` | 27 | `f7842832bcc046b1` | 5 |
| `status-dashboard` | 23 | `06bfb22434038596` | 3 |
| `post-push-verification` | 19 | `0892a5ddb0b585bf` | 1 |
| `hosted-agent-capability-audit` | 18 | `7d806ffe52953d33` | 7 |
| `agent-spend-budgeting` | 18 | `e0c9bf41aff403cb` | 4 |
| `agent-handoff-packaging` | 4 | `9b9c8d101293aba5` | 2 |
| `provider-endpoint-verification` | 4 | `63bd8b1f96304859` | 2 |
| `large-dataset-builds` | 3 | `8bbe4a9ac25937bb` | 1 |
| `project-skill-authoring` | 2 | `f0145effa0293f37` | 1 |
| `single-tenant-pipeline-generalisation` | 2 | `800d97628ebaea79` | 2 |

Not vendored: `multi-instance-generalization` (0 uses) — a judgement, not a safety decision.

Earlier captures of the first two skills were at 17:30Z and are still present inside their
directories where unchanged; the table above is the state at 17:50Z.

## How skills load, and in what order

| Source | Path | Editable how | In Git? |
| --- | --- | --- | --- |
| Profile ("agent"/"local") | `/opt/data/skills/<category>/<name>/` | `skill_manage`, or edit the files | no — this export is their only Git copy |
| Project ("external") | `dataset-factory/skills/` via `skills.external_dirs` | edit the repo files and commit | yes |
| Bundled ("upstream") | shipped with the `/opt/hermes` image | not editable; replaced on image update | no |

Observed with `hermes skills list`: the three dataset skills report `source=external`, the profile
skills report `source=local`, the bundled catalogue reports as installed. There are **no name
collisions** between the three sources today, so precedence has no practical effect yet; when a
collision occurs Hermes resolves by configured search order, so treat a duplicate name as a reason
to rename rather than as an override.

`skill_manage` can modify profile skills but refuses external-dir skills (they must be edited as
repository files), and cannot touch bundled skills.

## Sanitisation review

Every file was read, and the tree was grepped for credential-shaped strings (`ghp_`,
`github_pat_`, `hf_`, `BEGIN … PRIVATE KEY`), chat identifiers and private hostnames. One match was
inspected and cleared: `hosted-agent-capability-audit/references/github-token-scopes.md` mentions
token *prefixes* as a shape check, not a value. Everything else is method, not live state.

## Provenance and drift (important)

These copies were taken at **17:50Z**. The curator was active throughout the review and edits in
place:

| Time | Target | What happened |
| --- | --- | --- |
| 17:20Z | profile `agent-handoff-packaging` | curator wrote the refactor-brief template and patched SKILL.md |
| 17:31Z | repo `dataset-release` (external) | patched in the working tree, **uncommitted** (+17 lines) |
| 17:32Z | repo `dataset-qualification` (external) | same (+1 line) |
| 17:41Z | profile `open-data-source-vetting/references/release-packaging.md` | patched |
| 17:47Z | profile `agent-handoff-packaging/SKILL.md` | patched again |
| 17:48Z | profile `open-data-source-vetting/references/artifact-qualification.md` | patched |
| 17:48Z | profile `multi-destination-publishing/SKILL.md` | patched |

So: the curator **does** edit live external repository skills, it did **not** create profile copies
of the `dataset-*` skills (nothing shadows them), and it leaves repo edits uncommitted on `main`.

Consequence for the hashes above: they are point-in-time. `release-packaging.md`,
`artifact-qualification.md` and `agent-handoff-packaging/SKILL.md` were already newer than the
17:30Z capture when this table was written; their diffs are preserved in
`../curator-drift/profile-2026-10-22T1748/`. The gate itself is untouched: `GATE_VERSION` `1.4.0`,
`qualify_dataset.py` `4e51d2e9494fd66d`.

Anyone merging this handoff should decide what to do with those uncommitted edits first. They are
content-only, but unreviewed, and a scheduled session could commit them into an unrelated change.

## Review corrections in the runtime-audit branch

The frozen handoff at `3ec0b64` preserves captured operating knowledge; storing it does not
endorse every instruction or override project invariants. The audit pins exact file identity,
not scientific truth or operational authorization. Captured bodies are outside skills.external_dirs.

A focused review found instructions to delete/recreate tags and repair published manifests by
moving pins. `multi-destination-publishing` is corrected here to preserve existing tags and bytes;
its reference agrees. The original captured bytes remain in the handoff commit. Deploy this
explicit correction only with the reviewed rollout and a preserved live preimage. Other newly
captured skills are added to drift detection without silently replacing live versions.

Runtime paths for all 14 exports were measured by Scout and recorded in
[PR #1's path inventory](https://github.com/earino/dataset-factory/pull/1#issuecomment-6347672019).
`ops/runtime-files.json` contains complete current hashes; the earlier table is capture provenance.
