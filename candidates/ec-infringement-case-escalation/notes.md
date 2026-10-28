# ec-infringement-case-escalation

Opened 2026-10-28, EU/EEA regional tick. Channel search only - no row-level data
obtained yet.

## What was probed

- The Commission's infringement register is a public web application at
  https://ec.europa.eu/implementing-eu-law/home_en with per-case search by
  "decision, status, type, number, Member State, policy area or title" (publisher's
  page text, read 2026-10-28) plus interactive maps/graphs at
  https://ec.europa.eu/implementing-eu-law/member-state-infringement-cases_en.
- Monthly infringement packages are PDF presscorner publications (read 2026-10-28:
  INF_25_2077 of 2025-10-08, INF_25_2745 of 2025-12-11, INF_26_1084 of 2026-06-04);
  a typical package opens several procedures and closes ~59 cases; case numbers look
  like INFR(2025)2129.
- No documented bulk export or API on the publisher's pages in this tick's bounded
  search. A third-party scraping API (brubru.beresol.eu /api/v2/commission/infringements)
  exists but is NOT the publisher's channel and is not evidence that one exists.
- data.europa.eu search surfaced no EC-level infringement dataset (only national
  registers and unrelated "commission" datasets).

## Next probe (recorded in record.json next_action)

One bounded browser probe of the register application for a documented JSON/XHR
endpoint or export control. If none: park on the access blocker (ec-tdi-case-outcome
precedent - promising shape, missing channel, park not drop), reopen hook = a
documented export/API appearing on the implementing-eu-law register.

## Decision

investigating (hold), unclassified licence (deferred with the access question).
