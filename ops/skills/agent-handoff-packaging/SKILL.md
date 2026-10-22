---
name: agent-handoff-packaging
description: "Use when handing work to another agent, or exporting state."
version: 1.1.0
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [handoff, delegation, documentation, state, export, reproducibility, secrets, inventory]
    category: devops
    related_skills: [hosted-agent-capability-audit, multi-destination-publishing, scheduled-job-verification, ephemeral-worker-lifecycle]
---

# Agent handoff packaging

## When to use

Two shapes of the same problem - making work and state transferable without giving away secrets or
re-creating a running system:

- **Handing implementation to another agent** that will build something you then operate. "Prepare a
  handoff for the builder" is this.
- **Exporting your own setup and point-in-time state** so a successor session, a reviewer or a
  rebuilt host can resume: what is configured, where it is, and what is running.

The deliverable is a document plus a generated export. Both are read by someone who was not in the
conversation, so both must stand alone.

## The handoff document

1. **Describe the procedure that exists today, with exact commands and entry points, and label every
   step by its effect on the outside world.** Which steps create drafts, which upload, which verify,
   which create a version, and which make content public. That last distinction is where handoffs go
   wrong: the implementer assumes a build step publishes. State in the document that nothing in the
   procedure changes visibility, and that publication is a separate decision.
2. **Link to the canonical source for every fact; never restate its content.** Name the file that
   owns the version, the checksums, the partitions, the measurements and the citation, and say
   explicitly "reuse this, do not restate it". A second description of an artifact in a handoff
   document is how a site and a release come to disagree.
3. **Separate what is scheduled and running from what you are proposing.** List the live jobs with
   their schedules, modes and next run, then put proposals in their own section, in a deterministic
   shape - a release-time step or a script-only job - rather than a model-driven loop on a timer.
4. **Include a pitfalls section drawn from what actually cost time**, each as a rule with its
   mechanism, not as a story: the repository working copy that has its own nested `.git`, the version
   tag created before the data landed, the counts that must be read from the manifest rather than
   fetched, the rows that must never be served publicly.
5. **End with an acceptance exercise that runs before anything is public.** Render offline; assert
   agreement with the manifest on version, counts, labels and terms; assert the cross-links between
   the destinations; produce the build as a CI artifact (or a preview deployment) rather than a live
   deploy; then ask for the publication decision.
6. **State the boundary in the document.** Who owns which part after handoff, what still needs the
   owner's approval, and how the receiving agent proves it is done. A handoff without the boundary
   invites the other agent to publish.

## The read-only inventory

Before proposing a structure, inventory the platform - and change nothing.

- Collect: existing sites, workflows and their triggers, deployment environments, repository
  visibility, the scopes of the credential available to you, and the names already taken.
- **Check for collisions first.** An account-level root site, or a repository named like the one you
  are about to propose, changes the recommendation; a name that is free is not a name that is
  available in the sense that matters.
- **Never enable a feature or flip a visibility as part of an inventory.** Enabling a site, changing
  a repository's visibility or creating the destination are decisions with an owner; an audit that
  takes them is not an audit.
- **Report unknowns as unknowns, with how to find out.** Plan-tier restrictions, spending limits,
  organisation-level policy and the other party's access level are commonly not visible from the API.
  Naming them is the useful output; guessing at them produces a requirement the implementer builds
  against.

## Receiving a handoff: verify the claims, then run it yourself

A handoff message is a set of assertions, and the receiving side's job is to turn them into verified
facts before acting on any of them. The parts the sender could not observe live are exactly where the
defects are.

1. **Resolve every claim to a checkable artefact, at the full commit.** A cited run id, tag or build
   is verifiable in one call; fetch it and confirm the commit matches the *full* SHA the handoff is
   about. A truncated SHA in prose is easy to conflate with the commit CI actually ran, and "the
   checks were green" without a resolved SHA is not evidence about the tree you are holding.
2. **Review before integrating.** If your push is rejected because the sender's work has landed on
   the same branch, fetch and read the diff before rebasing onto it; a rejected push is information,
   and rebasing your own commits on top is the move - never a force-push, which would erase the thing
   you were asked to build on.
3. **Run the acceptance exercise yourself, from your own environment.** The handoff document's own
   acceptance steps are the cheapest way to find where the implementation and reality disagree.
4. **Reconcile count differences before reporting them.** Test totals commonly differ between the
   sender's clean checkout and your richer environment because environment-specific tests skip in one
   and run in the other. Work out which tests account for the gap and state the reconciliation; two
   loose numbers in a report read as a defect you did not diagnose.
5. **Treat a passing test suite as evidence about the mocks, not about the service.** Fixtures encode
   the sender's *assumed* behaviour of an external system, so the first real contact is the first real
   test. Exercise the live service in the bounded, reversible way the handoff permits (a read-only
   preflight, a dry run, a refusal path) rather than waiting for the first production run.
6. **When a defect surfaces on contact, land the test that would have caught it.** Extend the fake to
   model the real refusal - the actual error the service returns, in the sequence it returns it - and
   assert the new behaviour. A code-only fix leaves the next session to rediscover the same thing.
7. **Record the handoff result as measured, not accepted.** Note which of the sender's claims you
   verified yourself, the ones you measured differently and how they reconcile, and any defect you
   found and fixed.

## Handing a running system to an outside implementer

A second agent (or a different model) will often do the implementation work on a live system. Two
deliverables make that safe: an isolated branch that cannot disturb the running system, and a brief
that is specific enough to review.

- **Work in a linked worktree, never the live checkout.** `git worktree add <scratch>/handoff -b
  <branch> origin/main` gives a full tree on a separate branch that shares objects but has its own
  HEAD. Say in the handoff that nothing was launched from it: an executable tree beside a scheduler
  invites someone to run a job from stale code against live state.
- **Refresh the machine-generated export in the same commit as the prose.** If the project already
  has a snapshot generator, run it from the worktree so the prose and the export share one
  observation time. A handoff that quotes a runtime version while the committed export names an
  older one is two claims about now, and the reader cannot tell which to trust.
- **Hash what is outside version control, and name the gap.** Scheduler definitions, wrapper scripts
  and runtime config frequently live outside the repo; record each by path plus a short digest and a
  one-line purpose, and state plainly what is not exported (a session database, private identifiers)
  and what would be lost with the host. An inventory that lists only the tracked files describes the
  part that was never at risk.
- **Separate captured facts from recommendations.** The current state goes in the handoff; what you
  would change goes in its own section with the reason. Mixing them leaves the reader unable to tell
  an observation from an opinion.
- **Note the overlap with scheduled work, explicitly.** Name the jobs that could touch the same state
  and say why this branch cannot collide with them; "I did not change anything" is not the same
  claim as "the 20:00 tick cannot be affected".

### The brief for an outside implementer

The brief is the artifact, not a message wrapped around it. Write it in the repo
(`docs/<TOPIC>-BRIEF.md`) so it is reviewable and versioned, and structure it as: the problem with
reproductions, the target design, acceptance criteria, and constraints.

- **Enumerate the symptoms, not the smell.** "Six writers each invent a fallback" is unfalsifiable;
  a list of the six concrete inconsistencies, each with the file that carries it, is a specification.
- **State acceptance as commands and observable outputs** - the exact test invocation, the count that
  must be green, and the surfaces that must show the fixed value. A criterion nobody can run is a
  preference.
- **Name the invariants the refactor may not trade away**, in operational terms: do not weaken the
  gate, do not rewrite published artifacts to fit a new schema (normalise on read instead), do not
  fabricate a missing value, keep the licence semantics. These are the things a confident rewrite
  breaks first.
- **Say how to deliver: a branch and a pull request, not a merge; tests green on that branch; and the
  actual command output quoted in the PR body.** "It works" from an agent is a self-report, and the
  PR is where it becomes checkable.
- **Ask for the one thing you would otherwise have to reconstruct** - here, a short note listing each
  legacy shape found and how it is normalised - so the next reader inherits the map, not just the code.

Starter: `templates/refactor-brief.md`.

## The versioned export

- **Export by allowlist, never by copying the configuration and redacting.** Name each field you
  will export, record the ones that were not set, and refuse any field whose name looks like a
  credential even if someone allowlists it. "Copy it all and redact" is a promise you cannot keep as
  the configuration grows.
- **Make the writer refuse secrets rather than warn.** Scan the assembled payload for credential
  shapes and abort; keep an explicit list of file types that must never be committed; and take a
  second line of defence at the version-control boundary so an accidental copy is never staged.
- **Make the verification mode read only what is committed**, so it means the same thing in CI as on
  the host and does not depend on a runtime a clean checkout does not have.
- **Split the export by kind**: an identity file (runtime version, upstream revision, install method,
  local customizations), a configuration export (the allowlisted fields), and a state snapshot.
- **Record, for every summary figure, the observation time and the command that produced it.** The
  snapshot is a point-in-time claim: a budget figure, a queue position or a live-resource count
  without its source and timestamp will be read as current forever.
- **Generate it; never hand-edit it.** A generator that reads the live sources makes refreshing one
  command, which is what keeps a snapshot from rotting. Refresh it when configuration changes, not on
  a schedule of its own.
- **Keep secrets by reference.** Names, roles and file paths only - never a value, never a signed
  URL, never a private messaging identifier. Distinguish credentials that look alike by role: the
  publishing credential is not the inference credential, and the export should say which is which.

## Recovery instructions

Write the resume path so that following it cannot duplicate a running system:

- Say what lives in version control and what the platform manages (managed runtime, machine
  lifecycle, billing), so nobody tries to reconstruct the platform's part.
- Say how secrets are supplied (which store, which mechanism), by reference.
- Say which ledger or record is the accounting, and that it is evidence rather than scratch -
  deleting records to "start clean" silently resets the accounting a budget is computed from.
- Add an explicit **must not** list: do not start a second coordinator, do not re-create scheduled
  jobs that already exist, do not reset the allowance accounting, do not change inference
  authentication to fix a publishing problem.
- Frame it as a description of a running system, not a bootstrap kit.

## Pitfalls

- **A draft step that reads as a deploy.** Any pipeline whose later steps publish must mark which
  step crosses the boundary, or the reader will cross it for you.
- **Restating a fact the manifest owns** - in the handoff, in a slide of the procedure, in the
  receiving agent's notes. It will drift, and the disagreement will be found by a consumer.
- **Enabling as part of an inventory.** It converts an audit into a decision.
- **A handoff with no acceptance exercise.** Without one, "done" is a matter of opinion, and the
  first real test is publication.
- **Exporting a field because it is convenient.** An allowlist is only meaningful if adding to it is
  a deliberate act recorded in the diff.
- **A snapshot without timestamps or sources.** Every figure in it is a claim about a moment; a claim
  with no moment is taken as permanent.
- **A recovery document that reads as a bootstrap kit.** Restoring must not duplicate the scheduler,
  start a second coordinator, or reset the ledger the spend accounting is summed from.
- **Taking a handoff's claims as verified because they are specific.** A run id, a test count and a
  digest are checkable, which is exactly why an unchecked one is a liability: it is quoted onward as
  fact. Verify the cheap ones and say which you did not.
- **Reading two environments' test counts as a discrepancy.** Skips are environment-specific by
  design; reconcile the arithmetic before reporting a difference, and name the tests responsible.
- **Reporting a handoff complete without exercising its live path.** A demo, a unit suite and a mock
  of the provider are all compatible with a first real run failing at a state transition nobody
  modelled.
- **Inviting an outside agent into a repository whose visibility you assumed.** Read the visibility
  flag back from the host before pointing anyone at the repo, and scan the tracked files for
  credential shapes: a repo that was private when the convention was written can be public now, and
  the operational notes it carries (spend, internal reasoning, host paths) are then already visible.
  Confirm no value-shaped strings are committed, and if the visibility is not what the operator
  expects, raise it as a question rather than changing it - the owner may have made it public on
  purpose.
- **Version-controlling a copy of your own working tree.** A directory-replacing copy can drop a
  nested repository, after which version control silently walks up to the parent and reports a clean
  tree - commit from inside the copy and confirm with a status call on that path.
