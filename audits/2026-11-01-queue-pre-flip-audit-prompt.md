# Queue pre-flip audit prompt — all flip-candidate items

Written 2026-11-01T20:25Z for relay to an independent auditor (Codex).
Covers every item in the flip queue at write time. The operator's priorities
below are the standing test standard; they come from the operator's own words
across the nz-ea, unhcr and catalog audits and supersede any broader checklist.

---

INDEPENDENT PRE-PUBLICATION AUDIT — THE FLIP QUEUE
Auditor: you. You have no contact with the publisher. Nothing below is a claim
you must trust; everything is a claim you should try to break. You are
adversarial. You have read access to the private repositories named below; the
operator provides the credential. Change no repository content, publish
nothing, repair nothing. Record your environment (python, libs) and freeze your
attack code before opening any label column; hash and record everything you
freeze.

## WHAT THE OPERATOR ACTUALLY CARES ABOUT (the test standard, ranked)

P0 — Self-answering eval (label leakage). Can the eval and holdout labels be
     recovered, label-blind, from what ships? Joins across rows of the same
     entity, lookup tables, count arithmetic, date offsets, single-column
     dominance, free-text tokens. History: nz-ea shipped an eval a blind join
     recovered at AUC 1.0 and passed every internal gate; unhcr shipped a panel
     whose eval recovered at 0.97+; the catalog-wide audit found 7 of 10 early
     releases with findings. A demonstrated recovery on shipped bytes is an
     automatic DO NOT PUBLISH, whatever else is true.
P0 — False claims. Any statement in the shipped documents that is not true.
     Counts, dates, years, split ranges, exclusion numbers, licence
     descriptions, provenance. History: one package claimed an "enforced
     isolated-rows protocol" that no shipped code enforced; it was blocked and
     corrected. The operator's doctrine, verbatim from the directive: the
     benchmark framing is ILLUSTRATIVE — "the point of the benchmark was just
     illustrative so people understood what was possible with a dataset." So
     enforcement or guarantee language about scoring is itself a false claim;
     a disclosed, unenforced requirement is honest; an asserted enforcement is
     not.
P1 — Novelty. "A dataset that already exists in ML-ready form is not
     published. Mirroring is a failure mode, not a contribution." For every
     item, ask: does this exact task, on this source, already exist publicly
     in usable form (Hugging Face, Kaggle, a paper's release, the publisher's
     own ML-ready export)? If yes, name it: that is a DO NOT PUBLISH.
P1 — Licence honesty. Source terms clean, read from the source's own pages,
     preserved and carried through; publisher data never relicensed;
     attribution requirements stated; NOASSERTION stated as such. An
     unreadable or prohibited licence blocks publication; a source that would
     need a permission email is not used at all.
P1 — Data truth. Digests, source reconstruction, split disjointness,
     shipped counts matching the shipped bytes.

## WHAT IS NOT A DEFECT (do not fail an item for these)

- A weak or losing illustrative baseline. Most releases ship one that does
  not beat persistence; that is disclosed, not disqualifying. "One weak stock
  model does not establish that none can."
- The absence of an enforced scoring protocol — provided no document claims
  one. The shipped runner code is illustrative by the operator's directive;
  its shape is not the test.
- Prevalence shift, censored rows, unverified historical vintages — provided
  each is disclosed in the shipped documents.
- Process ceremony. You are auditing the artifact and its claims, not the
  factory.

## THE QUEUE

### Tier A — staged private, awaiting the operator's flip; full audit each

Each item has its own prompt file in the private factory repository, with the
digests, the publisher's claims and the frozen method; run each one, then
apply the P0/P1 checks above on your own initiative beyond it.

1. ipo-trademark-registration-outcome — repo earino/ipo-trademark-
   registration-outcome, release tag v2026.10, artifact 2c1dade2913d0a8b...
   Prompt: candidates/ipo-trademark-registration-outcome/pre-flip-audit-prompt.md
2. ns-bwa-advisory-lift-duration — repo earino/ns-bwa-advisory-lift-duration,
   GitHub release 428463645, tag v2026.10 == main == 23952346..., Hub private
   aaef1488..., artifact per its prompt.
   Prompt: candidates/ns-bwa-advisory-lift-duration/pre-flip-audit-prompt.md
3. pins-planning-appeal-outcome — repo earino/pins-planning-appeal-outcome,
   artifact c861bd8f4acd9bbe..., staged on both private destinations.
   Prompt: candidates/pins-planning-appeal-outcome/pre-flip-audit-prompt.md
4. unhcr-refugee-data-finder — RE-AUDIT. Your 2026-10-28 verdict was DO NOT
   PUBLISH in its present form as a benchmark with an enforced isolated-rows
   protocol; the corrections (illustrative framing, enforcement claims removed,
   exclusion count 377, target_date as calendar identifier, 14 declared inputs,
   label years 2002-2016) were applied, re-qualified as artifact 6bd0c307...
   and re-staged. Verify the corrections are real, complete and honest, and
   re-attack the same bytes.
   Prompt: candidates/unhcr-refugee-data-finder/pre-flip-audit-prompt.md
   (the re-audit mandate with the corrected claims is inside it).

### Tier B — constructed and gate-qualified, not yet staged; audit the bytes now

5. ocha-fts-appeal-funding-trajectory — constructed, qualified (gate 1.5.0,
   failed_checks empty), accepted as artifact e7441e1fd868522d1...; the bytes
   sit on the private staging repository (see its record for the staging
   release id). Run the P0 leakage battery and the claim-honesty checks
   against its qualification report now, so any defect is caught before
   staging spend; the formal full audit repeats when it is staged.

### Tier C — ready buffer, no artifact built; pre-construction gates only

For each: the candidate record (candidates/<id>/record.json) and notes carry
the source, the measured evidence and the declared licence posture. Bounded
to roughly a quarter hour each. Check ONLY:

- NOVELTY: does this exact task on this source already exist publicly
  in ML-ready form? Name it if so (DO NOT BUILD / not publishable).
- LICENCE: are the source's own terms clean, readable and redistributable at
  row level, with attribution carried? A licence you cannot read, or terms that
  prohibit redistribution, blocks the build.
- CHANNEL: does bulk row-level data actually exist on a public channel, or
  only aggregates/portal views? A record built on an aggregate-only claim
  wastes the build.

Items:
  acnc-charity-ais-deadline-compliance
  austender-contract-amendment-occurrence
  conagua-dam-drought-onset
  eu-transparency-register-removal
  jp-moe-pollen-exceedance
  ofsted-childrens-home-next-rating
  tw-typhoon-day-closure
  za-cct-c3-service-request-surge
  za-cct-substation-evening-peak-exceedance
  za-municipal-audit-opinion
  za-statsa-liquidations-exceedance

## REPORT

Queue summary first: one line per item — item, verdict, one-line reason.
Then per-item sections with exact numbers, freeze hashes, digest results and
an explicit NOT COVERED section per item.
Verdict vocabulary: Tier A/B use PUBLISH / DO NOT PUBLISH / PUBLISH WITH
CONDITIONS. Tier C uses READY-TO-BUILD / NOT-NOVEL / LICENCE-BLOCKED /
CHANNEL-BLOCKED / FIX-THE-RECORD.
FAIL means observed contradiction. NOT VERIFIED means you could not check.
Sign and date the report.
