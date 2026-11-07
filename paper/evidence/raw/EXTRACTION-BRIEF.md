# Evidence extraction brief — Dataset Factory paper

## Context
Dataset Factory (repo: /Users/earino/research/dataset_factory, branch main content) is a
long-running (since 2026-09-17) autonomous system. "Scout", a Hermes agent hosted on Nous
cloud, discovers public real-world data sources, constructs prediction-task datasets on
temporary Hetzner workers, qualifies them with a mechanical gate
(skills/dataset-qualification), and stages releases privately on GitHub + Hugging Face.
A human operator (Eduardo) holds the private->public "flip" gate. Codex (OpenAI) has been
used as an independent auditor (audits/) and remediation coordinator (GitHub issue #17).
The operator chose to verify Codex audits himself rather than automate them (yet).

We are writing a paper whose core is: what does an autonomous dataset agent get wrong,
and WHICH LAYER catches each defect (or fails to). Your job is evidence extraction, not
interpretation. Be literal. Never invent numbers, dates or files. If unsure, say so in
`confidence`.

## What to extract: DEFECT EVENTS
A defect event = something was wrong (or was believed wrong) in a dataset, its claims, the
pipeline, or the agent's behaviour, and it was detected (or found late). Include:
leakage, prediction-timing violations, licence/attribution errors, units/reference-frame
errors, split/temporal problems, source-format/parsing breakages, label-definition errors,
runner-contract mismatches, worker/infrastructure failures, credential/security slips,
false or over-strong editorial claims, budget/ops problems, agent-process failures
(e.g. a session died mid-flight, transcription error in a digest, stale flag, scope drift,
wrong conclusion later corrected). Also include FALSE ALARMS (something flagged as a
defect that turned out not to be one — e.g. "corrupt coordinates" that were a wrong-frame
misreading) with `false_alarm: true`.

Merge repeated mentions of the SAME defect into one event (cite the first and the
resolving entry). Do not merge distinct defects that share a candidate.

## Output
Write JSON Lines (one object per line) to the output path given in your task. Fields:

```
{"candidate": "<candidate id or 'factory' for pipeline-wide>",
 "date_detected": "YYYY-MM-DD",
 "stage": "discovery|construction|qualification|baseline|packaging|release-staging|consumer-verification|publication|post-publication|infrastructure|session-ops",
 "defect_class": "leakage|prediction-timing|licence|units-frame|split-temporal|label-definition|source-format|runner-contract|infrastructure|credential-security|editorial-claim|budget-ops|agent-process|other",
 "summary": "<one sentence, literal>",
 "detected_by": "qualification-gate|ci-mechanical-check|agent-self-check|codex-audit|human-operator|consumer-verification-job|hub-loading-check|worker-guard|external-provider|post-publication-review|unknown",
 "detected_by_detail": "<e.g. 'gate check X', 'probe script', 'operator raised scope drift'>",
 "reached": "never-built|built-unqualified|qualified|private-staged|public",
 "outcome": "fixed-rebuilt|fixed-no-rebuild|dropped|parked|restricted-notice|deferred|unresolved|not-a-defect",
 "false_alarm": false,
 "human_involved": true|false,
 "quantity": "<any measured number stated, verbatim, else null>",
 "evidence": ["STATE.md heading text (first 80 chars)", "file paths cited"],
 "confidence": "high|medium|low"}
```

## Also extract: HUMAN-GATE / OPERATOR EVENTS (second file)
Any event where the operator (Eduardo) decided, approved, rejected, redirected, corrected
scope, said "ship it", requested a review, or overrode the agent. Also any place where the
agent waited on the operator (awaiting_operator) and how long. JSONL fields:

```
{"date": "YYYY-MM-DD", "candidate": "...|factory",
 "kind": "flip-approval|flip-rejection|scope-correction|directed-review|policy-change|override|wait|other",
 "summary": "<literal>", "agent_position_before": "<what the agent proposed, or null>",
 "changed_outcome": true|false|null, "evidence": ["..."], "confidence": "high|medium|low"}
```

## Rules
- Read-only. Do not modify the repository. Do not run git commands that change state.
- Do not run workers, network calls, or the factory CLI's worker commands.
- You may read any file under the repo to confirm a detail, briefly.
- Finish with a short report: counts by defect_class and detected_by, plus the 5 most
  paper-worthy events (one line each) and anything you could not classify.
