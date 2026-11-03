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
