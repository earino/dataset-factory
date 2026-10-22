# Custom skills — vendored

Two profile skills carry most of the operating knowledge for this project. They are **not in the
factory repository**: they live in the Hermes profile skills directory and would be lost with the
host. Copied verbatim on 2026-10-22T17:30Z.

| Skill | Path on the host | Files | sha256[:16] |
| --- | --- | --- | --- |
| `open-data-source-vetting` (v1.2.0) | `/opt/data/skills/research/open-data-source-vetting` | `SKILL.md` (45,388 B) + 5 references | `ef66694f788d4ba7` |
| `agent-handoff-packaging` (v1.1.0) | `/opt/data/skills/devops/agent-handoff-packaging` | `SKILL.md` (15,376 B) + 1 template | `9b9c8d101293aba5` |

Supporting files: `open-data-source-vetting/references/{api-recipes,artifact-qualification,
discovery-coverage,novelty-check,release-packaging}.md`;
`agent-handoff-packaging/templates/refactor-brief.md`.

## How skills load, and in what order

| Source | Path | Editable how | In Git? |
| --- | --- | --- | --- |
| Profile ("local") | `/opt/data/skills/<category>/<name>/` | `skill_manage`, or edit the files | no — this export is their only Git copy |
| Project ("external") | `dataset-factory/skills/` via `skills.external_dirs` | edit the repo files and commit | yes |
| Bundled ("upstream") | shipped with the `/opt/hermes` image | not editable; replaced on image update | no |

Observed with `hermes skills list`: the three dataset skills report `source=external`, the profile
skills report `source=local`, and the bundled catalogue reports as installed. There are **no name
collisions** between the three sources today, so precedence has no practical effect yet; when a
collision does occur Hermes resolves by configured search order, so treat a duplicate name as a
reason to rename rather than as an override.

The distinction matters for editing: `skill_manage` can modify profile skills but refuses
external-dir skills (they must be edited as repository files), and cannot touch bundled skills.

## Sanitisation review

Each file was read before copying, and the whole tree was grepped for:

- credential-shaped strings (`ghp_`, `github_pat_`, `hf_`, `BEGIN … PRIVATE KEY`): none;
- host paths, personal names, e-mail addresses, IP addresses, private repository names: none — the
  text is generic method, not project state;
- chat identifiers or delivery targets: none.

Nothing was excluded from these two skills. Both are method-only: how to vet a source, how to
package a handoff, with worked examples that carry no live identifiers.

## Why these two

`open-data-source-vetting` is the procedure behind the licence classes, the novelty check and the
artifact-qualification gate; `agent-handoff-packaging` is the procedure behind this very directory,
including the rule that a writer must refuse secrets rather than warn about them.
