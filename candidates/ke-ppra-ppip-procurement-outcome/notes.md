# ke-ppra-ppip-procurement-outcome — probe log

## 2026-11-07 — licence-first triage (Africa tick), closed class C before task probing

Order of work (per skill): licence first. Access and content measurements were taken only
to characterise what the licence veto killed, not to advance construction.

### Channel sweep (publisher instruments)

- SPA + /ocds page rendered through the supported browser (portal is a JS app; curl gets
  an empty shell). Footer text on both:
  `Public Procurement Information Portal © 2026 All Rights Reserved | Powered by @iLabAfrica, Strathmore`
  Only links on the app surface: helpdesk, @iLabAfrica.
- `https://tenders.go.ke/helpdesk/` (browser): support center; footer
  `Copyright © 2026 PPRA. All rights reserved`. Knowledgebase = support topics; no terms page.
- `https://ppra.go.ke/` (curl): no data-licence or terms-of-use link anywhere in the menu;
  `ppra.go.ke/licensing/` = supplier/procurement licensing (licencees, permits,
  authorizations); `/terms-conditions/` and `/disclaimer/` = WordPress 404.
- OCP data registry publication 147: `License: -` (empty), last reviewed Dec 2024 by OCP.

Conclusion: no redistribution grant on any publisher instrument; bare copyright asserted
twice. Class C → closed under the 2026-10-21 standing policy. Executive Order No. 2 of
2018 (disclosure mandate) is recorded as NOT a licence.

### Access measurements (post-veto, for the record)

```
GET https://tenders.go.ke/            -> HTTP 200, 1.17 s (curl)
GET https://tenders.go.ke/api/ocds/tenders?fy=2026-2027
   attempt 1 -> HTTP 429, 6,619 B Laravel "Too Many Requests" page
   attempt 2 (after 45 s sleep) -> HTTP 429 again
GET https://data.open-contracting.org/en/publication/147/download?name=2018.jsonl.gz
   -> HTTP 200, 863,775 B, 0.39 s
```

The OCP mirror (retrieved monthly from PPRA) is the working anonymous bulk channel;
see probe_ocds_sample.py for the parse. 2018 sample: 6,727 processes,
2,074 (30.8%) with >=1 award, tender.status null throughout,
procurementMethod open 6,103 / selective 342 / direct 282.

Registry-side counts (OCP page, its monthly mirror, read 2026-11-07):
262,961 tenders / 109,607 awards / 80,309 suppliers / 818,997 parties,
Jul 2018 - Oct 2026, daily updates.

### Decision

DROPPED, class C. See record.json rejection_reason / next_action for reopen conditions.
No split counting, no novelty claim (never reached).
