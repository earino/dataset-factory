# ec-infringement-case-escalation

Opened 2026-10-28, EU/EEA regional tick. Channel search only - no row-level data
obtained yet. DROPPED 2026-10-31 on a recorded mirror verdict (novelty), after the
recorded access probe resolved the channel and licence in the publisher's favour.
All 2026-10-31 probes are reproducible from probe/ scripts.

## What was probed on 2026-10-28

- The Commission's infringement register is a public web application at
  https://ec.europa.eu/implementing-eu-law/home_en with per-case search by
  "decision, status, type, number, Member State, policy area or title" (publisher's
  page text, read 2026-10-28) plus interactive maps/graphs at
  https://ec.europa.eu/implementing-eu-law/member-state-infringement-cases_en.
- Monthly infringement packages are PDF presscorner publications (read 2026-10-28:
  INF_25_2077 of 2025-10-08, INF_25_2745 of 2025-12-11, INF_26_1084 of 2026-06-04);
  a typical package opens several procedures and closes ~59 cases; case numbers look
  like INFR(2025)2129.
- No documented bulk export or API on the publisher's pages in that tick's bounded
  search. A third-party scraping API (brubru.beresol.eu /api/v2/commission/infringements)
  exists but is NOT the publisher's channel and is not evidence that one exists.
- data.europa.eu search surfaced no EC-level infringement dataset (only national
  registers and unrelated "commission" datasets).

## What was probed on 2026-10-31 (this session, EU/EEA tick)

### 1. Access - the recorded next probe, run exactly as specified

- The 2026-10-28 URLs with `_en` now return HTTP 500 (curl: bare 500, Content-Length 0,
  Server: Europa). Current paths use `/en`:
  - landing/register: https://ec.europa.eu/implementing-eu-law/member-state-infringement-cases/en
  - search app: https://ec.europa.eu/implementing-eu-law/search-infringement-decisions/?typeOfSearch=byCase&activeCase=true&langCode=EN
  (browser page titles: "Infringement cases in the EU", "Themis infringement")
- The search app is an Angular application backed by a JSON API. Captured in the
  supported browser by patching XHR/fetch and clicking Search (body verbatim):
  POST /implementing-eu-law/search-infringement-decisions/api/decisions with
  {"refId":null,"relatedPetition":null,"petition":null,"decisionDateFrom":<DD/MM/YYYY|null>,
  "decisionDateTo":...,"langCode":"EN","memberState":...,"decisionCategory":<key|null>,
  "infringementType":null,"activeCase":...,"pressRelease":null,"page":0,"size":10,
  "title":...,"legalBasis":...,"dg":...,"policyArea":...,"courtFinancialSanctions":null,
  "order":"desc","sortColumns":"decisionDate"}
- Date format: the app sends DD/MM/YYYY. YYYY-MM-DD is REJECTED (HTTP 500) - error
  text read, not guessed.
- Row schema (decisions): activeInfringementCase, caseType, decisionDate,
  decisionType, infringementNumber, leadDg, memberState, memo(+URL),
  nonCommunicationCase, normalCuriaReference(+URL), policyAreas[], pressRelease(+URL),
  title. Sample: probe/api_decisions_sample_2026-10-31.json.
- Case-level endpoint found by probing sibling paths of the captured API:
  POST /api/infringements returns one record per case with the complete dated
  decisions[] history embedded. Reproduce: probe/probe_cases_endpoint.py,
  probe/probe_cases_totals.py. /api/cases and /api/case return 404; /api/infringements
  GET returns 405 (POST only), all error texts read.
- Reference data: GET /api/referencedata/decision-type/mapping (raw code ->
  category), GET /api/referencedata/loadAll (category labels per language),
  GET /api/referencedata/environment.
- The app also exposes "Export Search Url" / "Export to Excel" controls (page text
  observed 2026-10-31). No login, key or ToS gate anywhere in the captured flow.

### 2. Totals and per-year counts (bounded aggregate queries, no bulk transfer)

- Decisions: totalRows 62,957. Cases: totalRows 25,838. Active cases: 2,006.
- Earliest observed decision 18/10/1995 (INFR(1994)5095); newest 21/10/2026.
- Per-year ALL/LFN/RO/RTC/CLOSURES counts for every year 1996-2026:
  probe/yearly_totals_2026-10-31.json (script probe/probe_yearly_totals.py;
  31 years x 5 aggregate queries, each response <=4 KB, ~3 min wall clock on the
  coordinator).
- Publisher cross-check (2023 Annual Report on monitoring the application of EU law,
  read 2026-10-31): 1,038 cases closed in 2023 vs measured CLOSURES 1,037; 82 CJEU
  referrals decided vs measured RTC 37 in-year (referral decisions land in later
  years); stage-of-closure mix 680/300/20/25/13 consistent with the category taxonomy.

### 3. Licence (read after the channel settled)

- Commission legal notice (https://commission.europa.eu/legal-notice_en, read
  2026-10-31): Commission Decision 2011/833/EU; CC BY 4.0 for EU-owned content
  unless individually noticed; no individual copyright notice on the subsite.
  Class A. Same instrument family as the published ec-merger-phase2-opening.

### 4. Novelty - the decisive finding

- Web search (queries recorded in record.json novelty_check) found a 2026
  peer-reviewed study posing EXACTLY the candidate's primary label on this exact
  register: "National, partisan or ideological biases? How EU officials'
  characteristics can influence infringement proceeding outcomes",
  https://doi.org/10.1080/13501763.2026.2739423 - DV = Reasoned Opinion issued
  (1/0) after a formal notice, ~19,600 unique cases 2002-2020, escalation base rate
  ~34%, multilevel logit.
- Its replication data is public: Harvard Dataverse doi:10.7910/DVN/LGADVE,
  verified 2026-10-31 via the Dataverse API from the terminal:
  curl -sS -L "https://dataverse.harvard.edu/api/datasets/:persistentId?persistentId=doi:10.7910/DVN/LGADVE"
  -> status OK, versionState RELEASED, license "CC0 1.0", file replication_PP.zip
  71,421,134 bytes, restricted: None. A consumer can already download the assembled
  case-level task data.
- Adjacent formulations covered by older prior art: Boerzel & Knoll 1978-1999
  infringement database (stage histories to ECJ judgment, public download at
  infringement-db.jmce.org); Fjelstul & Carrubba stage-history models incl. CJEU
  referrals; duration and Art. 260 compliance/sanctions literature.
- check-novelty.py run with --verdict mirror (2026-10-31T12:23:24Z): the mechanical
  catalog sweep (HF/Zenodo/arXiv) found no ML-ready benchmark; the decisive prior art
  came from the web search and the Dataverse verification above, both recorded with
  their exact commands. The verdict is mirror for the procedural-escalation family.

## Decision

DROPPED 2026-10-31 (decision_date in record.json) - mirror, precedent named. The
2026-10-28 access blocker is RESOLVED in the publisher's favour (public anonymous
JSON API + case-level endpoint + class A licence) - the source is buildable, the
natural task is not ours to publish: the primary label's assembled dataset is
already publicly downloadable under CC0. Reopen conditions in record.json
next_action. The access/licence/population measurements in this record stand and
must not be re-probed on any reopen.

