---
name: project-skill-authoring
description: "Author and install repo-versioned skills for a project."
version: 1.0.0
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [skills, authoring, installation, project, verification]
    category: software-development
    related_skills: [hermes-agent-skill-authoring]
---

# Project skill authoring

Shipping a reusable procedure as a skill that a *project* owns, rather than one that lives
only in Hermes's own tree. Covers where the canonical copy lives, how to make exactly one
path visible to Hermes, and how to prove a fresh session can actually use it.

## When to use

- A workflow in a working repository deserves to be a skill the project ships: a gate, a
  checklist, a domain procedure, a checker with a CLI.
- The user says some variant of "keep the skill versioned in this repo and available to
  Hermes" - that is two requirements, and they are separately verifiable.
- You need to show that a new skill is discoverable, not just that the file exists.

Not this skill: authoring skills inside the hermes-agent repository itself (that tree has
its own standards and validator - see `hermes-agent-skill-authoring`), and not one-off
personal skills with no repository home.

## Procedure

1. **Write the canonical copy in the project repo.** A stable path (`skills/<name>/SKILL.md`)
   with support files beside it: `scripts/` for anything re-runnable, `references/` for
   depth that is only sometimes needed, `templates/` for starters. Commit it. The repo copy
   is the source of truth; every other location is a view of it.
2. **Keep the re-runnable part in `scripts/`.** A checker the skill invokes is an interface:
   its flags, exit codes and `--selftest` mode get documented in SKILL.md, and changes to
   them are changes to the skill.
3. **Choose exactly one Hermes-visible path** (next section).
4. **Point the project's AGENTS.md at it** with one line saying when to invoke it, so a
   session that never opens the skill list is still routed to it.
5. **Verify from a fresh process** (see Verify), not from the session that wrote it.
6. Commit, and state in the reply which of the two requirements - versioned, available -
   the evidence covers.

## Exposure: pick one path, never two

| Route | Visible from | Notes |
|---|---|---|
| Global skills dir (`~/.hermes/skills/<category>/<name>/`) | every session, every cwd | real files; a copy, so it can drift from the repo |
| Project-local (`<repo>/.hermes/skills/<name>/`) | sessions whose cwd is inside that repo | trusted once the root is in `skills.trusted_project_dirs` (`hermes skills trust`); no warning, but invisible outside the project |
| Symlink from the global dir to the repo copy | every session, every cwd | one source of truth; logs a warning on each load |
| Config-registered external dir (`skills.external_dirs`, pointing at `<repo>/skills`) | every session, every cwd, including scheduled ones | one source of truth, repo stays canonical, and no warning - preferred when the host supports it |

- **Never install the same skill name twice.** The loader refuses a name that resolves to
  more than one candidate rather than silently picking one, so a copy *and* a link, or a
  global *and* a project install, breaks loading instead of shadowing.
- **A symlink from the global dir logs `skill file is outside the trusted skills directory`**
  on every load, because the resolved path is not under a trusted skills dir. Take it
  deliberately when drift-freedom matters more than a log line - a duplicated real directory
  only silences the warning if you also add a test that the two copies are byte-identical.
- **Prefer the external-dir route when the repository already owns a `skills/` tree.** One config
  entry registers the whole directory, entries resolve relative to `HERMES_HOME`, and everything
  under it is treated as trusted - so it reaches every session, scheduled ones included, with no
  security warning and no duplicated copy. Confirm the host supports it (the loader exposes an
  external-dirs resolver) before relying on it, and fall back to the project-local route with
  `hermes skills trust` if it does not.
- **Anything exposed from outside the managed skills dir is loadable but NOT editable by the skill
  tooling** - a symlink, and equally a directory registered through `skills.external_dirs`. Writes
  through the skill tool are refused there. The canonical repo file is the only write target: make
  the edit in the repo and commit it. An automated pass over the skill library will also skip it,
  so route edits accordingly rather than concluding the skill is broken or unprotected by accident.
- If the repo is the source of truth, prefer the link or the project-local route over a copy.
  A copy is the only option that needs a sync test, so it is the last resort.

## Verify a fresh session can use it

1. Run a real one-shot session from inside the project:

   ```bash
   "<hermes-install>/.venv/bin/python3" "<hermes-install>/hermes" chat -q "<a request that needs the skill, without naming it>"
   ```

   A bare `hermes` is frequently not on `PATH`, and the system interpreter usually lacks its
   dependencies, so invoke it with the install's own interpreter. Locate the install from the
   running process when unsure.
2. **Phrase the probe so the answer requires the skill.** "What should I check before
   reporting a number from this artefact, and is there tooling here for that?" tests
   discovery. "Does the <name> skill exist?" tests nothing.

   **Add an isolation clause naming the repo** - "answer only from the skill system; do not read
   files under <repo>" - whenever the claim under test is that the *registered* path works. Without
   it a project-context answer cannot be told apart from the skill being loaded. Then make the
   probe **quote** something only the skill contains - the first command in its Commands section,
   its completion criteria - so the evidence covers the content rather than the name appearing in a
   list. A probe that returns descriptions and commands proves the body survived, not just that the
   file resolved.
3. **Confirm from the logs, not from the transcript.** The run prints its session id at the
   end; `~/.hermes/logs/agent.log` then shows the `skill_view` call attributed to that id.
   That line is the evidence a fresh context loaded the skill; the agent's own summary of
   what it did is a self-report.
4. **Run the probe from outside the repository as well as inside it.** A discovery that could be
   explained by project-local trust is not evidence for a route that claims to work everywhere; a
   probe started from an unrelated directory separates the two.
5. **Confirm a warning is gone by counting, not by eyeballing one load.** After changing route,
   grep the agent log for the warning across the period since the change: zero occurrences is the
   claim, one clean load is not.
6. **Do not verify from your own session.** A session's skill loader is cached at startup, so
   a skill added mid-session will not appear in `skills_list` for you. That is expected
   behaviour, not a failed install.

## Make the trigger do the work

- The description is what the index shows and what decides loading: keep it to one sentence,
  self-contained in the first ~57 characters, and lead with "Use when <trigger>".
- State the capability, not the implementation, and do not restate the skill's own name.
- Always-on rules belong in SKILL.md whole. Depth that is only sometimes needed goes in
  `references/<topic>.md` - named by topic, extended rather than multiplied, and pointed to
  from SKILL.md so a future session knows it exists.
- Include the pitfalls that cost time, each as a rule plus one clause of why. A skill that is
  only a happy-path procedure gets followed once and then abandoned.
- **Section shape this user expects in a project skill:** *when to use* (including what it is
  not for), *commands*, *required evidence*, the rules themselves, *common failure modes*, and
  *completion criteria* as a checklist. The reader should be able to tell when the work is
  finished without asking, and a claim the skill makes should be traceable to the evidence the
  skill demands.
- **Keep current state and historical incident narrative out of the instructions.** The procedure
  and the generalizable rule belong in the skill; dates, session findings and "what went wrong
  last time" belong in the project's state file. Write the rule so it stands without the incident
  behind it, and point at the state file instead of retelling the story in the skill.

## Pitfalls

- **Verifying with the session that wrote the skill.** The loader cache makes it look
  absent; a fresh process is the only real check.
- **Editing the copy instead of the source.** When the repo is canonical, edits through the
  skill tooling hit the wrong file (or are refused) and the next sync silently reverts one
  side. Know which file is canonical before editing.
- **Leaving the skill's own fixtures uncommitted.** A repo that ignores data files
  (`*.csv`, `*.parquet`) will silently drop a fixture the skill's tests need; add an explicit
  negation for that fixture path and confirm the file is tracked.
- **A skill whose command block has drifted from its script.** The documented invocation is
  part of the interface - when flags or exit codes change, update SKILL.md in the same change.
- **Claiming 'available to Hermes' from a file path.** Availability is proven by a fresh
  session loading it, which is a different and stronger claim.

## Verification checklist

- [ ] Canonical copy committed in the repo, with any `scripts/`/`references/` it needs
- [ ] Exactly one Hermes-visible path; the name resolves to a single candidate
- [ ] `skills_list` shows the skill with its intended trigger text
- [ ] A fresh one-shot session, given a request that needs the skill, loads or runs it -
      evidenced by the `skill_view` line for that session id in the log
- [ ] The project's AGENTS.md (or equivalent) says when to invoke it
- [ ] The reply distinguishes "versioned in the repo" from "a fresh session used it"
