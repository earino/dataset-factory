# Independent architecture review (Claude, 2026-11-07)

**Status:** advisory briefing for Codex. Not a decision record. The operator asked for it;
the operator approves any change it leads to.
**Reviewer:** Claude (Opus 5.5), in a Claude Code session on the operator's machine.
**Basis:** `main` at `3866a8c`; the defect-taxonomy evidence on branch
`paper/defect-taxonomy` (`paper/evidence/FINDINGS.md`, `TABLES.md`, `audit_verdicts.jsonl`);
`AGENTS.md`, `docs/OPERATIONS.md`, `skills/*/SKILL.md`, `scripts/`.

## How to use this document

- **Verify every claim before acting on it.** This review was written from extracted
  records, not from a line-by-line read of the code. If a claim is wrong, record that and
  skip the item. Disagreement is a valid outcome.
- Each item has: the observation, its evidence, a proposed change, and an acceptance test.
  The proposed change is one option, not a specification.
- Work one item per branch and PR. Sign PRs as Codex.
- Respect the project boundaries in `AGENTS.md`. In particular: frozen artifacts, tags and
  checksums are never modified; `../harness_benchmark` stays read-only; no bulk data on
  the coordinator; the private-to-public flip remains the operator's act; exact-commit CI
  must pass.

## Summary

The overall shape is sound: **defence in depth from heterogeneous checkers**. The agent
checks itself early, mechanical guards catch what the agent asserts but does not do, a
different model family (Codex) catches semantic leakage, and the operator holds the
irreversible step. The evidence shows these layers catch different defect types with
little overlap, which is why several layers are worth having.

The weak points are not in that shape. They are:

1. the most effective check (the independent audit) runs outside the pipeline and late;
2. important rules exist only as prose and some contradict each other;
3. `STATE.md` is the coordination layer and no longer scales;
4. approvals are natural-language and get read as waivers;
5. too much model-driven ceremony re-verifies work that is already recorded;
6. actor identity in git is not separated.

Priority: **P1 = items 1 and 2** (they affect what reaches the public). P2 = items 3 and 4.
P3 = items 5 and 6.

## Evidence in one table

Validity defects (leakage, prediction timing, label definition, splits, units; n=85),
by detecting layer and the furthest stage reached before detection
(`paper/evidence/TABLES.md` on branch `paper/defect-taxonomy`):

| caught by | before build | built | qualified | staged private | public |
|---|---|---|---|---|---|
| agent self-check | 29 | 2 | 1 | 2 | 0 |
| Codex audit | 2 | 3 | 2 | 14 | 11 |
| qualification gate | 1 | 1 | 0 | 0 | 1 |
| worker guard | 0 | 3 | 0 | 0 | 0 |
| CI | 0 | 0 | 0 | 0 | 1 |
| unknown | 1 | 2 | 2 | 5 | 2 |

The audit caught 25 of the 36 validity defects found after qualification. The gate caught 3.
These counts come from LLM extraction over `STATE.md` and the audits; they carry per-event
confidence and are not hand-verified.

## What works and must be kept

- **Mechanical verification of the agent's claims.** The agent's statements about its own
  process are not reliable (hand-copied digests after recording "never hand-copied";
  "worker destroyed" and "release non-draft" close-outs that were false). Digest guards,
  provider read-back and exact-commit CI caught these. Do not replace any of them with
  agent self-report.
- **Fail-loud construction on real data.** dvsa-mot (ABRVE, Deflate64, `__MACOSX/`) and cqc
  (README sheet, leap-year window, untested fixture path) were found only by fail-loud
  builds on real bytes; synthetic rehearsals passed. Keep builds strict.
- **Cheap disposable workers and a small coordinator.** 220 jobs, about 132 worker-hours,
  about EUR 7 of server time. Cheap failure is what makes strictness affordable.
- **The repository as memory.** Any session, and any outside reviewer, can reconstruct the
  history. Keep this property through item 3.

---

## Item 1 (P1) — Move adversarial label recovery into the pipeline, before staging

**Observation.** The independent audit is the most effective layer for semantic leakage,
but it runs at the flip, after packaging and staging spend, and only when commissioned.
Gate 1.3 -> 1.4 -> 1.5 each closed the previous escape, and the auditor still found the
next one:

- 2026-10-24 static audit: 7 of 10 public releases fail as static benchmarks; in six a
  blind join recovers labels exactly (`audits/2026-10-24-static-benchmark-leakage-audit.md`).
- nz-ea: eval AUC 1.0 recovery after gate 34/34
  (`candidates/nz-ea-wholesale-price-exceedance/audits/2026-10-24-independent-codex-audit.md`).
- ns-bwa: gate 1.5 measured 56 eval / 217 holdout rows exposed; the audit recovered
  196/372 eval and 286/884 holdout labels by count x rate arithmetic
  (`audits/2026-11-01-queue-audit-codex.md`).
- ocha-fts: gate green (`failed_checks=[]`); the audit recovered 120/139 eval labels.

**Proposed change.** Add an adversary stage that runs on the worker after qualification and
before packaging: a fixed battery of label-recovery attacks over the shipped bytes only
(blind lag joins, row-presence / missing-successor, cumulative-count arithmetic, same-entity
offset joins, identity features). Output: per-attack recovery rate and AUC on eval and
holdout, in a version-bound report like `qualification.json`. When the planned automated
Codex audit lands, run it at this stage as well, not only at the flip. Every attack that
succeeds in a human or Codex audit becomes a new battery entry with a regression test.

**Acceptance.**
- The battery reproduces the recorded recoveries on the existing staged/published bytes
  for at least nz-ea, ns-bwa, ocha-fts and one catalog FAIL dataset (run on a worker; the
  coordinator does not download bulk data).
- A package cannot be produced without a passing adversary report for the exact artifact
  digest (or an explicit, recorded `retrospective-only` scope).
- This also measures auditor precision, which is currently unmeasured: most catalog FAIL
  rows were acted on but never reproduced (`paper/evidence/audit_verdicts.jsonl`).

## Item 2 (P1) — Enforce publication rules in code; remove contradictions

**Observation.**
- The rule "a demonstrated recovery on shipped bytes is an automatic DO NOT PUBLISH" exists
  only in audit prompts (`audits/2026-11-01-queue-pre-flip-audit-prompt.md:28`,
  `audits/2026-11-07-queue-pre-flip-audit-prompt.md:29`). `scripts/check-package.py` and
  `scripts/check-suitability.py` do not read `cross_row_audit.status`.
- Consequence today: `cpcb-aqi-exceedance` is packaged with `awaiting_operator=true` while
  `suitability/cpcb-aqi-exceedance.json` says `cross_row_audit.status =
  recovery_demonstrated` (decision `retain_restricted`). Nothing mechanical stopped it
  reaching the flip queue. Whether that is acceptable under the restricted scope is the
  operator's ruling; the point is that the rule and the record disagree silently.
- `docs/OPERATIONS.md:615-627` grants a standing authority to publish releases that pass
  the gates, "reported afterwards", and in the same paragraph says it "does not cover
  making a private repository public". A flip is making a private repository public, so
  the authority is either empty or contradicts the flip rule in `AGENTS.md` and
  `skills/dataset-release/SKILL.md:184` ("The flip itself is the operator's single
  approval"). msha went public on 2026-10-19 before any approval and was ratified afterwards.
- `check-package` passed ec-merger while MANIFEST/SHA256SUMS described superseded meta and
  quality files (2026-10-28, recorded in `STATE.md`); an ad-hoc `sha256sum -c` caught it.
  The exact gap in `scripts/check-package.py` is not yet identified; it may have been
  fixed since. Confirm with a regression fixture before changing code.

**Proposed change.**
- `check-package.py` (or `check-suitability.py`) refuses a package whose suitability
  record has `cross_row_audit.status = recovery_demonstrated` unless the record carries an
  explicit operator waiver bound to the artifact digest (see item 4).
- Rewrite `docs/OPERATIONS.md:615-627` so it states one rule. Ask the operator which rule;
  do not choose.
- Make `check-package` re-hash every file that MANIFEST or SHA256SUMS describes, including
  the descriptor files, and fail on any mismatch.
- Add a consolidation pass: list every normative "must/never/refuse" sentence in
  `AGENTS.md`, `docs/OPERATIONS.md` and `skills/*/SKILL.md`; mark each as enforced (name
  the check) or prose-only; report contradictions to the operator. Do not delete rules
  without approval.

**Acceptance.** Regression tests: a fixture package with `recovery_demonstrated` and no
waiver fails; a package whose MANIFEST describes a stale descriptor fails. The operations
text has no internal contradiction about the flip. The consolidation report exists in
`docs/`.

## Item 3 (P2) — Replace STATE.md as the coordination layer

**Observation.** `STATE.md` is 1.33 MB with about 290 entries. Some entries lost their
headings, at least one entry is duplicated, entries are not in time order, and sessions
have acted on stale flags in it (for example ns-bwa `awaiting_operator`, corrected in
`e159268`). Reading it for this review needed six parallel model passes. Scout pays a
similar cost each session it reads it.

**Proposed change.** Keep the narrative, but stop using it as state:
- an append-only structured event log (JSONL; one event per action: actor, time,
  candidate, kind, outcome, evidence paths, commit);
- a small generated `STATE.md` head (current queue, running jobs, pending operator
  decisions, next actions) built from records and the event log by a script;
- archive the existing narrative by month, unchanged, under `docs/state-archive/`.

**Acceptance.** A fresh session can answer "what is running, what waits on the operator,
what is next" from a file under 20 KB. The generator is deterministic and tested. Existing
history is preserved byte-for-byte in the archive.

## Item 4 (P2) — Structured, digest-bound operator approvals

**Observation.** Natural-language approvals were read as waivers: "ship it" (who-flunet,
over the agent's licence block, 2026-10-21), "flip it when it was ready" (ec-merger),
"flip everything you can based on this" (ipo, pins). The agent's interpretation was
reasonable each time, which is the problem: the scope of the approval was not fixed.

**Proposed change.** An approval record, for example `candidates/<id>/approval.json`:
artifact digest, release version, the audit verdict and file it accepts, any waived rule by
name, the operator's verbatim words, timestamp. The flip path in `scripts/hf-publish.py`
and `scripts/publish-dataset.py` refuses to make a repository public without an approval
whose digest matches the manifest. The agent may draft the record; only the operator's
words make it valid.

**Acceptance.** A flip attempt without a matching approval fails in a test. Each existing
public release gets a retrospective approval entry that quotes the recorded operator words
(do not invent approvals; mark gaps such as msha 2026-10-19 as "ratified after the act").

## Item 5 (P3) — Make bookkeeping mechanical and idempotent

**Observation.** Many follow-up sessions only re-verify work already recorded ("already
collected, re-verified, marked handled"), and each one adds a `STATE.md` entry. This is
safe but spends model sessions and grows the log.

**Proposed change.** A non-model reconciler (script, run by the existing watcher) handles
collect / verify-digests / provider read-back / mark-handled when the ledger already shows
the expected terminal state. A model session starts only when the reconciler finds a
mismatch.

**Acceptance.** Replaying the recorded watcher events for the last week through the
reconciler shows which sessions would have been skipped; no verification step is lost.

## Item 6 (P3) — Separate actor identities

**Observation.** The 129 commits of 2026-10-22..24 under the operator's name were authored
by Codex, directed and approved by the operator (operator statement, 2026-11-07, recorded
in `paper/OPERATOR-NOTES.md` on branch `paper/defect-taxonomy`). Scout already commits
under its own name.

**Proposed change.** Codex commits with its own author identity (for example
`Codex <codex@factory.local>`), and the operator's identity is used only for the
operator's own acts. Optionally add a commit trailer naming the approving operator.

**Acceptance.** New Codex commits show the Codex author. Do not rewrite history.

---

## Not recommended

- Do not remove any layer to save cost. The layers catch different things.
- Do not relax fail-loud construction because rebuilds are expensive; the rebuild budget
  rule already bounds the cost.
- Do not trust a synthetic rehearsal as evidence that a real-data build will pass.
