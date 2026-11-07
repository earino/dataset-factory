# Queue pre-flip audit prompt — the 2026-11-07 flip queue

Written 2026-11-07T10:25Z for relay to an independent auditor (Codex). Covers
every staged-but-unaudited package in the flip queue, plus the ready-buffer
additions that postdate the 2026-11-01 clearance. The operator's ranked test
standard below is the standing one; it supersedes any broader checklist.

---

INDEPENDENT PRE-PUBLICATION AUDIT — THE FLIP QUEUE (2026-11-07)
Auditor: you. You have no contact with the publisher. Nothing below is a claim
you must trust; everything is a claim you should try to break. You are
adversarial. You have read access to the private repositories named below; the
operator provides the credential. Change no repository content, publish
nothing, repair nothing. Record your environment (python, libs) and freeze your
attack code before opening any label column; hash and record everything you
freeze. Read-only remote acquisition; work products stay in your local audit
directory.

## WHAT THE OPERATOR ACTUALLY CARES ABOUT (the test standard, ranked)

P0 — Self-answering eval (label leakage). Can the eval and holdout labels be
     recovered, label-blind, from what ships? Joins across rows of the same
     entity (the panel/registry class of defect: a later row carrying an
     earlier row's answer), lookup tables, COUNT ARITHMETIC on shipped counts
     and rates (the unhcr, ns-bwa and ocha-fts lessons: cumulative counts,
     covered rates, last-prior chains), date offsets, single-column dominance,
     free-text tokens. A demonstrated recovery on shipped bytes is an
     automatic DO NOT PUBLISH, whatever else is true. Disclosing an exposure
     honestly makes the disclosure honest; it does not waive this prohibition.
P0 — False claims. Any statement in the shipped documents that is not true:
     counts, dates, years, split ranges, exclusion numbers, licence
     descriptions, grain claims (the ocha-fts lesson: a country-year grain
     claim was false; the grain is whatever the id columns make unique),
     provenance. The benchmark framing is ILLUSTRATIVE by the operator's
     directive; any enforcement or guarantee language about scoring is itself
     a false claim.
P1 — Novelty. A dataset that already exists in ML-ready form is not
     published. Does this exact task, on this source, already exist publicly
     in usable form (Hugging Face, Kaggle, a paper's release, the publisher's
     own ML-ready export)? If yes, name it.
P1 — Licence honesty. Source terms read from the source's own pages, clean,
     preserved, carried through; publisher data never relicensed; attribution
     requirements stated; NOASSERTION stated as such. An unreadable or
     prohibited licence blocks publication.
P1 — Data truth. Digests, source reconstruction where the builder permits,
     split disjointness, shipped counts matching the shipped bytes.

## WHAT IS NOT A DEFECT (do not fail an item for these)

- A weak or losing illustrative baseline; no demonstrated headroom over
  persistence is a disclosure, not a disqualifier.
- The absence of an enforced scoring protocol — provided no document claims
  one. The shipped runner is illustrative; its shape is not the test.
- Prevalence shift, censored rows, unverified historical vintages — provided
  each is disclosed in the shipped documents.
- Process ceremony. You are auditing the artifact and its claims, not the
  factory.

## TIER A — staged private, awaiting the operator's flip; full audit each

Each item has its own prompt file in the private factory repository (every one
programmatically filled from the frozen manifest; digests verified against it).
Run each item's own prompt, then apply the P0/P1 checks above on your own
initiative BEYOND it — your 2026-11-01 and 2026-11-03 attack batteries are the
baseline; try harder than them, especially count/rate arithmetic and any
history-derived column.

1. ab-wildfire-ia-escape — repo earino/ab-wildfire-ia-escape, GitHub release
   437179999, tag v2026.11, artifact c2c8ceb56c7ff52a...
   Prompt: candidates/ab-wildfire-ia-escape/pre-flip-audit-prompt.md
2. cpcb-aqi-exceedance — repo earino/cpcb-aqi-exceedance, GitHub release
   436366305, tag v2026.11, artifact a749f0df2f9dd010...
   Prompt: candidates/cpcb-aqi-exceedance/pre-flip-audit-prompt.md
3. cqc-care-home-deregistration — repo earino/cqc-care-home-deregistration,
   GitHub release 433767120, tag v2026.11, artifact afe9ee203f302f3c...
   Prompt: candidates/cqc-care-home-deregistration/pre-flip-audit-prompt.md
4. za-cct-substation-evening-peak-exceedance — repo
   earino/za-cct-substation-evening-peak-exceedance, GitHub release 434422204,
   tag v2026.11, artifact 9f2e10ce485635f6...
   Prompt: candidates/za-cct-substation-evening-peak-exceedance/pre-flip-audit-prompt.md

Each repository ships MANIFEST.json and SHA256SUMS — recompute and match every
digest before you use any byte. All three CSVs are labeled in each package; the
holdout files ship by design. Download them; work locally.

## EXCLUDED, WITH REASONS (do not spend effort here)

- ns-bwa-advisory-lift-duration: the staged v2026.10 bytes carry your DO NOT
  PUBLISH verdict (196/372 eval, 286/884 holdout recovered exactly). The
  rebuild is queued; it gets its own fresh audit when staged. A stale
  flip-ready flag was corrected this session; the package is not flip-ready.
- unhcr-refugee-data-finder: dropped in this form by operator decision (two
  DO NOT PUBLISH verdicts; the panel self-answers by construction). Parked.
- austender-contract-amendment-occurrence: licence-blocked (current source
  terms unreadable; rescope to the licensed historical archive is a separate
  review). Not staged, nothing to audit.

## TIER C — ready buffer additions since the 2026-11-01 clearance

The 2026-11-01 READY-TO-BUILD clearances stand and are not re-opened. Check
ONLY the additions (and any member added after this prompt was written - the
candidate records carry status): for each, bounded to roughly a quarter hour:
NOVELTY (does this exact task on this source already exist publicly in
ML-ready form? name it), LICENCE (source's own terms clean, readable,
redistributable at row level, attribution carried), CHANNEL (bulk row-level
data actually exists on a public channel, not aggregates/portal views).

Items:
  cra-charity-filing-exit
  datasus-sinasc-cesarean-share-decline
  ibama-auto-infracao-recidivism
  npri-facility-reporting-exit
  oecd-ncp-specific-instance-acceptance
  tw-typhoon-day-closure (re-check the CORRECTED novelty record against the
  public kxykxyou/TyphoonDayoffPrediction repository - the mirror question was
  resolved by the publisher; verify the differentiation actually holds)

## REPORT

Queue summary first: one line per item — item, verdict, one-line reason.
Then per-item sections with exact numbers, freeze hashes, digest results and
an explicit NOT COVERED section per item.
Verdict vocabulary: Tier A uses PUBLISH / DO NOT PUBLISH / PUBLISH WITH
CONDITIONS. Tier C uses READY-TO-BUILD / NOT-NOVEL / LICENCE-BLOCKED /
CHANNEL-BLOCKED / FIX-THE-RECORD.
FAIL means observed contradiction. NOT VERIFIED means you could not check.
Sign and date the report.
