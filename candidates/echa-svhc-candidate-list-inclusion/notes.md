# echa-svhc-candidate-list-inclusion

Record dated evidence, decisions, and failed approaches here.

## 2026-11-03 discovery session (EU/EEA regional focus; discovery-only)

Task idea: predict REACH Candidate List (SVHC) inclusion events for substances, at a
fixed instant before each update, from EUR-Lex-derivable regulatory state (CLP Annex VI
ATPs, Annex XIV/XVII, POPs) + static EC Inventory identifiers. Prospective user:
chemical suppliers / compliance teams (inclusion triggers supply-chain obligations).

### Licence (decisive, read first as required)

ECHA legal notice IP 4.1.1 (chem.echa.europa.eu/legal-notice; text read 2026-11-03 from
the search index of the live page, identical clause text on three chem.echa.europa.eu
routes - the route itself is a client-rendered SPA):

- permitted: "may be downloaded, reproduced, distributed and/or used, totally or in
  part, for commercial and non-commercial purposes" with attribution;
- carve-out: "does not extend to whole or substantial parts of databases";
- prohibition: "The replication, in whole or in substantial part, of the ECHA
  databases is prohibited, unless ECHA's prior written permission is given";
- collection: "ECHA reserves the right to block systematic automated data collection
  activities (including scraping, data mining, and extraction and re-utilisation)".

Verdict: the label source IS an ECHA database and a full-population dataset replicates
the list in whole; no EUR-Lex instrument carries Art. 59(10) events. Class D for the
natural design; the written-permission channel is a class C "contact us" pattern that
standing policy closes for new leads. DROPPED.

### Access evidence (recorded; not the blocker)

- `curl -A "Mozilla/5.0 ... Chrome/131..." https://echa.europa.eu/legal-notice`
  -> 403, Azure WAF HTML (9,377 B): "One moment, we're checking you're not a bot."
- Supported browser: challenge page persists after 25 s + reload ("🐴 Azure WAF" title).
- `curl https://chem.echa.europa.eu/` -> 200 (SPA shell, JS required).
- `curl "https://chem.echa.europa.eu/api-activity-list/v1/authorisationProcess/documents?name=245b55819049e9b7e25ab9987bf9f75c_12th_axiv_recommendation_november2025_en.pdf"`
  -> 200, 458,641 B PDF (API host is anonymous-accessible).
- data.europa.eu catalogue record (id candidate-list-of-substances-of-very-high-concern-for-authorisation):
  publisher corporate-body/ECHA, license null, modified 2018-06-26, 0 distributions
  (stale portal metadata, as the geographic-coverage reference warns).

### Novelty (swept; not the blocker)

Two searches 2026-11-03:
"machine learning prediction \"substances of very high concern\" SVHC candidate list REACH";
"anticipating REACH \"candidate list\" inclusion prediction regulatory prioritisation chemicals model".
Found QSAR hazard-property studies that use the list as a data set (PMC7451722 K-REACH;
obesogen screening; organosilicon ML) and expert prioritisation schemes (PikMe ETC 2025;
RSC Sustain 2024 semi-quantitative scheme). No published ML benchmark predicting the
listing event. If the licence is ever resolved, the task is differentiated - but the
reopen condition is a licence event only.
