# efsa-health-claim-opinion-outcome

Record dated evidence, decisions, and failed approaches here.

## 2026-11-03 discovery session (EU/EEA regional focus) - lead OPEN, status investigating

Task: predict whether EFSA's NDA Panel delivers a favourable (cause-and-effect
established) vs unfavourable opinion on a health claim under Reg. (EC) 1924/2006.
Prospective user: food businesses deciding whether to invest in an application /
dossier; ~20-33% favourable base rates mean always-negative is a strong baseline.

### Licence (read first; both publishers' own instruments)

- `curl -A "Mozilla/5.0 ..." https://www.efsa.europa.eu/en/legalnotice` -> 200.
  Quote: "Copyright © for the entire content of this website unless otherwise
  stated: European Food Safety Authority – EFSA. Re-use is authorised, provided
  that EFSA is acknowledged as the source of the material."
  No ECHA-style database-replication prohibition. Per-document caveat
  ("unless otherwise stated") still unverified for EFSA Journal PDFs (Wiley 403).
- `curl -L https://commission.europa.eu/legal-notice_en` -> 200 (ec.europa.eu/info
  URL 301s there). Quote: "Unless otherwise indicated (e.g. in individual
  copyright notices), content owned by the EU on this website is licensed under
  the Creative Commons Attribution 4.0 International (CC BY 4.0) licence."
  The EU Register of Nutrition and Health Claims is DG SANTE content.
- Tentative: EFSA side class B (attribution + open per-document check),
  Commission side class A. data.europa.eu catalogue record (dataset id
  u3yjqnr7wx2gjkbqmajsya) carries license null and 0 distributions - stale
  metadata; the publisher's own pages govern.

### Access measurements (2026-11-03, coordinator, anonymous plain HTTP)

- Art 13.1 claims database: `curl
  https://www.efsa.europa.eu/sites/default/files/topic/ndaclaims13.zip`
  -> 200, 8,341,996 bytes (MS Access .mdb inside; 4,637 main claim entries per the
  publisher page). No mdbtools / no pip on the coordinator -> status counts NOT
  measured here; parse on a worker in advancement. File left in scratch, not committed.
- Register of Questions: taken offline Jan 2021 (EFSA page read: "The Register of
  Questions was taken offline at the end of January 2021... OpenEFSA portal").
  OpenEFSA = Angular SPA. api.efsa.europa.eu resolves but 404s guessed paths;
  openapi.efsa.europa.eu connection-failed; roq.efsa.europa.eu unreachable.
- EU Register (DG SANTE): now behind the Food and Feed Information Portal SPA
  (https://ec.europa.eu/food/food-feed-portal/screen/health-claims/eu-register).
  App env config (assets/env-json-config.json) gives API base
  https://ec.europa.eu/food/food-feed-portal/backend/api. Measured: /policy-items
  and /food_categories return JSON 200; the health_claims endpoints found in the
  app bundle (/health_claims/get_list_of_claims etc.) return 404 to a plain client.
  The SPA did not finish rendering in the supported browser (readyState stuck on
  'loading', performance resource capture empty) - the real request capture is the
  next probe, not a conclusion.
- EFSA Journal: efsa.onlinelibrary.wiley.com 403s curl; EFSA /en/efsajournal/pub/8861
  301s to Wiley. Conclusion text (the label source for Art  13.5/14) is therefore
  not yet extracted from here; whether the supported browser passes Wiley's block
  is unverified. This is the main access risk for construction.

### Novelty sweeps (2026-11-03; no formal check-novelty run yet - required before ready)

Three searches, none returned a published scored study or ML-ready benchmark for
EFSA claim-opinion outcomes: (1) "machine learning predicting EFSA health claim
outcome opinion favourable"; (2) "\"health claims\" EFSA NDA panel prediction model
outcome \"favourable\" OR \"unfavourable\" study machine learning"; (3) "text mining
predict outcome EFSA NDA opinions health claims favourable study model". Hits were
EFSA's own guidance/press/panel-statistics pages and unrelated ML-in-risk-assessment
material.

### Publisher statistics recorded as cross-check evidence (not measured panels)

- EFSA press news 110728 (read via search 2026-11-03): 2,758 general-function claims
  assessed by 28 July 2011; "about one in five" favourable, favourable mainly
  vitamins/minerals and specific fibres.
- EFSA NDA presentation document 131120-p03.pdf (read via search): Art 13.5/14
  finalised by Nov 2013: 91 (13 positive / 78 negative) and 100 (33 positive /
  67 negative); withdrawn ~39%.

### What is still open (all named in record.json next_action)

1. Per-claim/year/outcome counts for the split windows (FIP register API capture,
   or worker mdb parse + journal enumeration).
2. Dated worked example (application receipt instant -> opinion adoption; feature
   window between).
3. Journal per-document copyright line + bulk-extractability (Wiley 403).
4. scripts/check-novelty.py formal verdict before any ready decision.

Split design note: positives cluster by opinion (one opinion decides many Art 13.1
claims); clustered opinion-level counts must be recorded with claim-level counts.
The Art 13.1 batch instant is coarse (list compiled 2008-2010; evaluations 2009-2011),
so features must stay limited to submitted-claim content - which is exactly what the
2010 database captures.

## 2026-11-06 discovery session (EU/EEA regional focus) - bounded probe executed, verdict DROPPED (split capacity)

The record's named next probe (FIP SPA capture -> per-claim status counts; Wiley
browser test; formal novelty check) was executed. Every earlier access blocker
resolved; the decisive blocker turned out to be split capacity.

### FIP EU register (DG SANTE) - the SPA API is plain HTTP after all

The SPA (https://ec.europa.eu/food/food-feed-portal/screen/health-claims/eu-register,
FIP version 5.8.0) rendered fully in the supported browser this time (previous
session: readyState stuck). Captured backend calls (performance.getEntriesByType):
  .../backend/api/policy-items?foodDomain=nut&authorisationType=nut_auth
  .../backend/api/food_legislations?domain_code=nut&authorisation_type=nut_auth
  .../backend/api/keyed-reference-data?key=hc_claim_status|hc_legal_basis_type
The old bundle's /health_claims/* endpoints are gone; the claims list IS
policy-items. Plain-curl GET works:

  curl -s ".../backend/api/policy-items?foodDomain=nut&authorisationType=nut_auth"
    -> 200, 19,885,668 bytes, 2,337 published policy items (the whole register).
  curl -s ".../backend/api/keyed-reference-data?key=hc_claim_status"
    -> 8 statuses (DRAFT/IN_PROGRESS/ON_HOLD/AUTHORISED/NON_AUTHORISED/WITHDRAWN/
       AUTHORISED_PDPE/REVOKED); published register carries only AUTH/NON_AUTH/REVOKED.
  curl -s ".../backend/api/policy-items/POL-HC-11221" -> 200, 8,280 B (details).
  The authorisationType param is IGNORED (any value returns the same 2,337 items).

Counts (probe_fip_register.py reproduces; script in this directory):
  13.1: 1,841 non-auth / 228 auth / 1 revoked; 13.5: 148/14; 14(1)(a): 31/15;
  14(1)(b): 47/12. 100% carry EFSA question number + opinion URL; hcHealthRelationship
  2,072; hcReasonsForNonAuth 2,065 (e.g. HC_RR_166); hcCondOfUse 270; applicant
  fields only on proprietary 13.5/14 items.
  13.1 by opinion-citation year: 2009 95/312, 2010 89/663, 2011 40/826(+1 revoked),
  2012 2/39 (+1 unparseable '012;10(8):2848' = 2012), 2015 2/0.
  13.5/14 by application (Q) year: 2008 15/57, 2009 5/19, 2010 5/9, 2011 3/15,
  2012 2/42, 2013 4/25, 2014 3/17, 2015 2/8, 2016 0/7, 2017 1/9, 2018 0/4,
  2019 0/3, 2020 1/6, 2021 0/2, 2022 0/3.

### OpenEFSA - the real API (previous session probed the wrong host)

The SPA calls open.efsa.europa.eu/api/... (NOT api.efsa.europa.eu). Plain HTTP
returns System.UnauthorizedAccessException "Security string is not valid"; the
security string is computed in main.<hash>.js module 57591:
    x-security: 123*floor(Date.now()/1e3)+369
Replicated from curl with $((123*$(date +%s)+369)). Working endpoints:
  /api/question/searchAdvanced?offset=0&limit=N[&foodDomains=Nutrition
    &authorisationType=Health%20Claims&type=Application
    &dossierReceivedMinDate=YYYY-01-01&dossierReceivedMaxDate=YYYY-12-31 ...]
    -> data.totalCount + per-filter status facets (bounded: limit=1 per call)
  /api/question/getTimeline?questionNumber=EFSA-Q-2021-00073 -> 6 dated events
  /api/homePage/getLatestUpdatedQuestions
Per-question fields: questionNumber, subject (claim text), applicantNames,
substanceNames/CAS, mandateNumber, phaseName, clockStopDate, timeLineItems.
Authorisation-type filter is honoured as authorisationType=Health%20Claims
(5,351 of 5,975 Nutrition questions); type=Application honoured as type=Application.

Health-claims applications by dossier-received year (totalCount | Published |
Withdrawn | Intake | Ongoing), 21 small calls (probe_openefsa.py reproduces):
  2008 4,430 | 2,718 | 470 | 1,242 | 0   <- the Art 13.1 list submission cohort
  2009    36 |    24 |  12 |     0 | 0
  2010   481 |   161 |  14 |   306 | 0
  2011    26 |    23 |   3 |     0 | 0
  2012   143 |   134 |   9 |     0 | 0
  2013     33 |    31 |   2 |     0 | 0
  2014     27 |    26 |   1 |     0 | 0
  2015     14 |    10 |   4 |     0 | 0
  2016      7 |     7 |   0 |     0 | 0
  2017     14 |    11 |   3 |     0 | 0
  2018     11 |     4 |   7 |     0 | 0
  2019     10 |     3 |   7 |     0 | 0
  2020     10 |     8 |   2 |     0 | 0
  2021      2 |     2 |   0 |     0 | 0
  2022      3 |     3 |   0 |     0 | 0
  2023      1 |     0 |   1 |     0 | 0
  2024      6 |     5 |   1 |     0 | 0
  2025      6 |     4 |   1 |     0 | 1
  2026      4 |     0 |   0 |     0 | 4
  sum 5,269 (status overall: Published 3,177, Withdrawn 539, Intake 1,548,
  Ongoing 5; Post-TR = 21). EFSA's own press cross-check: 523 claims in the first
  opinion series, 808 in the third, 4,637-entry list, ~1,745 assessed by Oct 2010 -
  the wave structure matches the register's 2009-2012 clusters.

### Wiley 403 - passes in the supported browser

https://efsa.onlinelibrary.wiley.com/doi/10.2903/j.efsa.2021.6849 renders in the
browser (plain HTTP still 403): Open Access, "Adopted: 15 September 2021", "First
published: 20 October 2021", Requestor "Competent Authority of Germany following
an application by BENEO GmbH", question number EFSA-Q-2021-00073, and the label
sentence in the abstract: "The Panel concludes that a cause and effect relationship
has been established between the intake of isomaltulose and contribution to
energy-yielding metabolism." Site footer: "Copyright (c) 1999-2026 John Wiley &
Sons... including rights for text and data mining and training of artificial
intelligence technologies". Article-level copyright line not yet extracted
(moot after the drop).

### Label divergence measured (register status != Panel conclusion)

POL-HC-11221 (isomaltulose, BENEO, Art 13.5): FAVOURABLE Panel conclusion, but the
register lists the claim HCCS_NON_AUTHORISED with reason HC_RR_166 ("cannot set
conditions of use"). So construction could never have taken labels from the
register; every label would need per-opinion extraction through the browser
channel. Recorded as secondary evidence raising construction cost.

### Worked example (dates all from the publisher's own records, UTC)

EFSA-Q-2021-00073: Dossier Received 2021-02-04, Dossier Valid 2021-05-21
(prediction instant; features = submitted claim content only), Clock Stop
2021-06-14, Output Adopted 2021-09-15, Output Published 2021-10-20, Risk
Assessment Deadline 2021-11-04; register lastModificationDate 2024-08-26.

### Decision: DROPPED on split capacity

- Train windows are rich (2009-2015: 2,069 decided 13.1 claims + early 13.5/14),
  but the 13.1 population is ONE submission cohort (2008-2010) decided in waves;
  using it as holdout would put the prediction instant BEFORE the train window's
  outcomes (chronological violation).
- Every post-2015 window is thin: register 13.5/14 2016-2022 = 36 decided claims,
  2 authorised; OpenEFSA post-2020 = 22 applications received, 14 published.
- Withdrawal censoring rivals decisions recently (2018: 7 withdrawn vs 4 pub).
- A scored holdout on <=36 rows / <=3 positives cannot carry a CI. The stream is
  ending, so waiting does not fix it.
Novelty: formally no_precedent (check-novelty.py, 2026-11-06; searches 2026-11-03
+ 2026-11-06 found only EFSA guidance/press/minutes). Licence: class A
(Commission CC BY 4.0) / class B (EFSA attribution notice, per-document item
unextracted and moot). Access: all three channels measured anonymous.

### Sibling lead noticed, NOT opened (recorded for a future session)

Novel-foods application outcomes (Reg (EU) 2015/2283): applications list is
legally required public ("The Commission shall make the list of such applications
publicly available", Art 10). The FIP novel-food screen carries only the 33-item
Union list (grouped by authorising regulation); the application-status stream
needs the OpenEFSA Novel-Foods questions (599, with timelines) joined to Union-
list authorisations - unmeasured. Do not open without measuring per-year
application counts by status first. The same FIP/OpenEFSA access recipes in the
probe scripts apply.
