# Operator notes for the paper

Primary-source statements from the operator (Eduardo), recorded verbatim with date.
These are inputs for the paper, not measurements.

## Cost (2026-11-07)

> "hermes is a fixed cost of 20 a month on nous cloud right now. it's gonna be hard to
> detangle because i have other agents on the same interface."

- Hermes/Nous: flat 20/month subscription, shared with the operator's other agents.
  Report as an upper bound for the agent's model cost, not a per-dataset figure.
- Workers (Hetzner): measured from jobs/*.json ledgers - see paper/evidence/.
- Codex usage: not yet stated.

## Why the Codex audit gate stayed manual (2026-11-07)

> "Learning, honestly? I felt it was important for me to understand where things were
> failing, so that i could help fix the agent."

Earlier the same day:

> "i could have automated the codex checks, which is coming soon, but i wanted to verify
> them myself for a while."

Implication for the paper: the manual gate was primarily a diagnostic instrument for the
operator (learning where the agent fails, to improve it), not only a safety control.
Automation of Codex checks is planned; record the switch-over date when it happens, so the
manual period and the automated period can be compared.
