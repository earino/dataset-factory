# eu-ombudsman-inquiry-outcome

Opened 2026-10-31, EU/EEA regional tick (Europe focus; publisher found via the
register itself after the tick's first lead resolved negatively). Status:
investigating - four of five contracts measured; the split-count join is the
one named prerequisite (worker job, advancement). All probes reproducible from
probe/ scripts.

## Source and channel (measured 2026-10-31)

- Publisher: European Ombudsman inquiry register,
  https://www.ombudsman.europa.eu/en/search-inquiries (Angular SPA).
- The search application is backed by an anonymous REST API captured from the
  publisher's own bundle (chunk_CqcAHzvI.js / chunk_u_CkN6bh.js):
  - POST /rest/legal-documents/search/en?page=N, JSON body (verbatim from the
    app's body class): {text, languageISO, caseId, docTypes, dateMin 'dd_mm_yyyy',
    dateMax, institutionIds, settlementIds, topics, keys1, keys2, keys3, keys5,
    keys7, countryId}. Empty body = all documents, returns countDtos + listDtos
    (10 documents/page). GET returns 405 (error text read).
  - GET /rest/eoCases/byCaseId?caseId=483/2024/PVV - full per-case record
    (probe/case_483_2024_PVV_2026-10-31.json): dateOpened, dateClosed, country,
    topics, key5/key7 codings, ownInitiative/strategicInitiative/publicInterest
    flags, eoCaseInstitutionSettlements[] (institution + settlement code),
    confidentiality, caseStates (internal history).
  - Reference data: /rest/eo-settlements (22 outcome codes), /rest/documentTypes,
    /rest/topics, /rest/institutions, /rest/caseKeywords/keysN,
    /rest/geographical/countries, /rest/labels?lang=en (label decode:
    ma='Maladministration found', crr='Critical remark', nmf='No maladministration
    found', nfij='No further inquiries justified', sbi='Settled by the
    institution', sa='Solution achieved', rai='Recommendation agreed by the
    institution', dbc='Dropped by the complainant', dwc='Dealt with a Court', ...).
- Totals (probe/probe_eo_measures.py, ~130 bounded POST queries, countDtos only):
  13,069 documents; EODECISION 5,727; EOOPENINGSUMMARY 3,653 (2011+ only);
  EOCASEDESCRIPTION 1,483; EODRAFTRECOMMENDATION 343; EOSOLUTION 137;
  EOSPECIALREPORT 21. Decisions/year 106-476 since 2010 (158 in 2023, 186 in
  2024). Published openings/year 247-389 since 2020.
- Settlement mix on decisions (all time): nmf 1,629 / sbi 722 / nfij 542 /
  ma 143 / crr 134 / sa 76 / others small. Grouped by 5-year decision windows:
  adverse (ma+crr) 44 / 98 / 52 / 82 across 2008-2012 / 2013-2017 / 2018-2022 /
  2023-2026 - both classes in every window (probe/measures_2026-10-31.json).
- Publisher cross-checks (read 2026-10-31): EP resolution P10_TA(2024)0063
  (2023: 398 opened, 372 closed; nmf 26.6%, resolved 55.4%, nfij 12.4%, ma 7.3%)
  and EO Overview 2012 (424 closures: nmf 76, ma 56, nfij 197, settled 80).
  Measured published-decision counts are a DIFFERENT population (2023: nmf 90,
  ma 17 of 158 published decisions vs 99/27 of 372 closures) - the coverage gap
  (published openings ~78% of openings; published decisions ~42% of closures) is
  recorded as an eligibility boundary of the task, not a defect.

## Licence (read before task probing, 2026-10-31)

- https://www.ombudsman.europa.eu/copyright: '(c) European Union, 1995-2026.
  Reproduction is authorised, provided the source is acknowledged, save where
  otherwise stated.' Attribution-only; derivatives not explicitly addressed ->
  class B (NOT the Commission's CC BY 4.0 instrument; the Ombudsman has its own
  copyright page). No dataset-specific terms on the register; no login/ToS gate
  in the captured anonymous flow. Conditions to state in LICENSE.md at build.

## Dated example (worked timing contract, all times Europe/Brussels)

Case 483/2024/PVV (complaint against the European Commission; fetched
2026-10-31, probe/probe_eo_fixture.py + probe/case_483_2024_PVV_2026-10-31.json):

- Complaint recorded internally 2024-02-20 (caseStates, not public).
- dateOpened = 2024-03-20. Opening summary published 2024-03-20T00:00:00+01:00
  (EOOPENINGSUMMARY documentDate, verified equal to dateOpened to the day):
  'The failure by the European Commission to reply within the statutory time
  limits'. PREDICTION INSTANT: 2024-03-20 (opening-summary publication).
- Feature window (all at/before the instant): institution = European Commission
  (named in the opening title; coded on the case), complainant country = nl,
  topic = Access to documents, key5 = Justice and police cooperation,
  key7 = alleged failure types (incl. 'Failure to take a timely decision
  [Article 17 ECGAB]'), caseRef year/initials 2024/PVV, ownInitiative=false.
- Eligibility cutoff: inquiries with a published opening summary (2011+),
  complaint-based (ownInitiative=false), inMandate/admissible as coded.
- Target window: 2024-03-21 .. closure. dateClosed = 2024-12-18; decision
  published 2024-12-20T10:00:00+01:00 (EODECISION; 2 days after dateClosed).
  Settlement code: nfij ('No further inquiries justified') -> no-finding class.
  No part of the target window precedes the instant.

## Novelty (recorded 2026-10-31T12:44:22Z, verdict differentiated)

- Mechanical sweep (HF/Zenodo/arXiv, in record.json novelty_check): no hits for
  the EO task. Web sweep: no study poses outcome prediction on the European
  Ombudsman's register.
- Family comparator (named): Daswati/Wijayanto/Afendi 2025 (BAREKENG: J. Math.
  Appl.) - classifies maladministration findings on the Ombudsman of the Republic
  of Indonesia's INTERNAL, NON-PUBLIC complaint database (9,795 reports
  2023-2024; LightGBM/CatBoost/RF; no public dataset; no temporal splits).
  Different registry, jurisdiction, population, features and data availability;
  cannot be downloaded by a consumer. The EO's own annual-report percentages are
  publisher summaries, not a task.

## Five contracts (reconciled 2026-10-31)

1. Redistribution: SUPPORTED - class B (publisher's own copyright page,
   attribution-only reproduction authorisation; derivatives unstated; licence
   plan: state attribution + no-alteration practice in LICENSE.md).
2. Prediction timing: SUPPORTED with a recorded as-of policy - instant = opening
   summary publication (verified documentDate == dateOpened on the fixture);
   features fixed at/before the instant; label event strictly after (decision
   2024-12-20 for the fixture). Current-vintage coding (register serves no
   historical snapshots) stated as the as-of policy, same posture as the
   published ec-merger-phase2-opening.
3. Target: SUPPORTED - publisher-coded 22-value settlement taxonomy on the
   per-case record (eoCaseInstitutionSettlements), decoded with the publisher's
   own label store; source fields excludable from features.
4. Split capacity: PARTIALLY evidenced (aggregate: per-year decisions 106-476
   since 2010, both classes in every 5-year window, adverse class 44-98/window;
   openings 247-389/yr since 2020). UNRESOLVED at the task's own population: the
   per-opening-cohort join counts require the per-case panel (a worker build).
   This is the exact missing fact; see record.json next_action for the
   measurement job and its acceptance criteria.
5. Not a mirror: SUPPORTED - differentiated verdict recorded; no public
   ML-ready formulation anywhere; the contribution is the formulation, the
   opening-instant contract, eligibility and split design.

## Decision

investigating (active, one named measurement prerequisite). No blocker: the
channel, licence, target, timing and novelty are all resolved in the
publisher's favour. The next action is a single bounded worker job (advancement)
that computes the join-based split counts; if the cohorts hold, the candidate
flips to ready with no further probing. If they do not, it flips to parked with
the measured counts and a reopen hook.
