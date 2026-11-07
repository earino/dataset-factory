# Briefing — fix the dataset factory: catch audit-class defects at build time, run the audit autonomously

Written 2026-11-07 by the publisher session at the operator's direction, for relay
to Codex as the factory's builder. This is a system-engineering task, not a data
task. Read the audit reports named below first; they contain the full attack
taxonomies and measured numbers this task must automate.

## The situation, with receipts

14 datasets are published. Since late October the independent pre-flip audits
have rejected every defective staged package before publication — the audit
works — but the yield is unacceptable. Rejected at the audit boundary, after
full construction + staging spend:

- nz-ea: blind join recovered eval labels at AUC 1.0
- unhcr (2026-10-28, re-audited 2026-11-01): successor-row join + count
  arithmetic, eval AUC 0.975325 / holdout 0.983034, exact on covered rows
- ns-bwa: cumulative count x rounded-rate subtraction, 196/372 eval and
  286/884 holdout recovered exactly, zero errors
- ocha-fts v2026.10: country-history count/rate arithmetic, 120/139 eval and
  128/182 holdout exactly
- 2026-11-07, all four staged packages at once: ab-wildfire (shipped fixture
  answer table: 3 eval + 4 holdout labels recovered exactly), cpcb (next-day
  mean shipped as later-row lags/recency: 99.37% eval and 99.08% holdout
  recovered exactly, single-split donors still 99%+), cqc (builder ships the
  pseudonym salt + fixture answers: 4 eval labels recovered exactly from
  shipped code), za-cct (README worked example prints a declared holdout
  row's label; plus false digest-enforcement and reversed interval claims)

The factory's own gates passed every one of these: gate 1.5.0's two-phase
qualification (with builder-DECLARED cross-row probes), check-package,
check-suitability. The declared-probe design is the core failure: builders
probe what they thought of; the auditors attack what the builder did not.

Reports to read (all in audits/):
2026-10-27-ec-merger-pre-flip-audit.md, 2026-10-28-unhcr-pre-flip-audit.md,
2026-11-01-queue-audit-codex.md, 2026-11-03-ocha-fts-re-audit-codex.md,
2026-11-07-queue-audit-codex.md.

## The defect classes to catch at build time

Class A — label-blind exact recovery from shipped bytes (the killer; 6+ of the
failures). Any shipped column that is a function of another row's outcome, or
of this row's own future, makes the panel self-answer: successor-row joins on
entity keys and (entity, date offsets); count/rate arithmetic over adjacent
same-entity rows (cumulative counts, covered rates, count-delta +/-1
deductions, N x M reconstructions); lag/recency columns that carry the next
row's answer operand; fixture answer tables and salts shipped in package
bytes.

Class B — shipped answer artifacts: fixture IDs with expected answers, hash
salts, README worked examples naming scored rows.

Class C — false claims in shipped documents: enforcement/guarantee language
about scoring; grain claims (assert what the id columns actually make unique);
unlinkability claims; digest-enforcement claims that the code does not
implement; interval-direction claims reversed; wrong dictionaries, wrong
prevalence, wrong column semantics (min/max swap); stale embedded digests
(get_dataset.py EXPECTED, three times now); unresolved @@PLACEHOLDER@@ tokens.

Class D — licence-chain defects: licence sentences written by hand instead of
from the source's own text (the false OGL same-licence sentences, twice);
unreadable or conflicting licence pages adopted by interpretation instead of
refused (Alberta 403; datasus cc-by metadata vs BY-ND footer; CPCB upstream
chain).

## What to build (ordered by demonstrated kill-rate)

R1 — Deterministic label-blind leakage battery as a HARD gate at
construction/qualification time (gate 1.6), run by the construction worker
in-pipeline BEFORE any staging spend. Versioned, deterministic code in the
repo — no model judgment in the critical path. At minimum, the frozen attack
families the auditors used:
  - later-row joins on entity keys, quasi-identifier combinations, and
    (entity, date offsets): does a later row ship this row's answer or its
    operands (copy, lag, recency-zero, mean identities)?
  - count/rate arithmetic between adjacent same-entity rows: cumulative
    counts x rounded rates, count-delta extremes, N x M reconstructions with
    rounding-bounded abstention;
  - lookup tables: train-donor single/pair rate tables with unanimity
    coverage; fixture/answer-table scans over every shipped file;
  - single-column and simple-transform dominance (rank AUC > 0.95 flags,
    both orientations); token/n-gram probes over text columns;
  - same-split AND all-shipped-row donor scopes (cpcb proved single-split
    donors still recover 99%+).
  Verdict rule: any zero-error exact recovery on >= 1 eval or holdout row =
  hard FAIL. Results recorded in quality.json. Builder-declared probes are no
  longer the only cross-row checks; the battery always runs.

R2 — Scaffold and answer-artifact scrubber (build-time + check-package
guard): refuse shipped bytes containing fixture answers, salts, raw fixture
IDs, worked examples naming scored rows, or unresolved placeholders. Worked
examples reference train rows or abstract values only; builder fixtures
assert counts and exclusions, never labels.

R3 — Claims-from-bytes verifier: at packaging, every measurable claim in the
docs is recomputed against the bytes: prevalence/positive rates, dictionary
bins vs actual values (with min<=max invariants), grain uniqueness (assert the
declared id columns unique; assert any claimed non-uniqueness), split year
ranges, exclusion counts vs summary.json, interval directions (recompute the
paired intervals, assert the prose matches the sign), embedded digests in
get_dataset.py vs the accepted report. Enforcement/guarantee language about
scoring is a lint failure (illustrative-only doctrine).

R4 — Licence verifier: at packaging, fetch the source's own licence page
(browser-capable probe path), store the fetched text as evidence, and
generate every licence statement in LICENSE.md and the card from that
recorded text. Refuse on unreadable pages or metadata/footer conflicts;
never adopt an interpretation.

R5 — Autonomous adversarial audit orchestration: after packaging and private
staging, the factory runs the full battery plus a model-driven adversarial
pass (an auditor session with the programmatically-generated pre-flip prompt,
mandated to go beyond the deterministic classes), records a machine-verifiable
verdict in the candidate record, and only then sets awaiting_operator. The
operator-relayed independent audit remains the final gate before any flip —
but it should become rare, because the self-audit already caught what the
builder missed.

R6 — The operating hold, implemented in config: an admission hold that stops
new discovery collection and new package construction until R1-R4 exist, pass
the acceptance tests below, and the four currently-blocked 2026-11-07 packages
have been re-run through the new gates with recorded outcomes. Config-driven,
reversible by the operator in one step.

## Acceptance tests (the definition of done)

A1 — The battery reproduces, on the pinned historical artifacts, every exact
recovery listed in the five audit reports, and hard-fails each artifact at
construction time: nz-ea, unhcr 6bd0c307, ns-bwa v2026.10, ocha e7441e1f,
cpcb a749f0df, cqc afe9ee20 (fixture lookup), ab-wildfire c2c8ceb5 (fixture
lookup). The bytes are in the private repos and staging releases named in
the reports and STATE.md.
A2 — False-positive line: the 14 published packages' shipped bytes are NOT
hard-failed by the exact-recovery rule (several carry disclosed exposures;
disclosure is honest, exact recovery is the kill line). Where the battery
flags them, the flag is recorded, not fatal.
A3 — The scrubber catches the shipped fixture/salt/example defects of
ab-wildfire, cqc and za-cct; the claims verifier catches the cpcb min/max
swap, the cqc dictionary, the za-cct interval directions, the ab-wildfire
placeholders and prevalence, and the stale-digest defect class; the licence
verifier refuses the datasus conflict and the unreadable Alberta page.
A4 — End to end: re-run the four blocked 2026-11-07 packages through the new
pipeline and record what each gate says. The operator then decides per
package: correct-and-rebuild, or drop.
A5 — The existing test suite stays green; new gates ship with tests.

## Constraints

- The operator's test standard is the spec, verbatim: P0 self-answering eval
  (label-blind exact recovery on shipped bytes = automatic block, disclosure
  does not waive it); P0 false claims; P1 novelty, licence honesty, data
  truth. NOT defects: weak/losing illustrative baselines, absence of an
  enforced scoring protocol when nothing claims one, disclosed prevalence
  shift/censoring/vintage limits.
- The 14 published datasets are frozen: no bytes, tags or manifests change.
  New gates apply to staged packages going forward.
- Frozen-manifest doctrine, tag immutability post-publication, digests never
  hand-copied, illustrative-benchmark doctrine — all documented in
  skills/dataset-release/SKILL.md and docs/REFACTOR-NOTES.md.
- Workers are ephemeral Hetzner boxes, one at a time, EUR 20/month ceiling;
  bulk bytes never pass through the coordinator; bundle rules (allowed
  extensions) and the files-beside-the-spec transport rule apply.
- Repo: /opt/data/dataset-factory. Gate: skills/dataset-qualification/scripts/
  qualify_dataset.py (gate 1.5.0). Packaging: scripts/release-manifest.py,
  scripts/check-package.py. Schema/read contract: factory/release_schema.py.
  Candidate records: candidates/<id>/record.json. Worker ledger: jobs/.
  Scheduled session machinery: scripts/scout_research_schedule.py and the
  deployed shims. STATE.md is the operational ledger — every session writes
  its entry there.

Out of scope for this task: new discovery, new construction, correcting the
four blocked packages (their disposition follows A4), anything public.
