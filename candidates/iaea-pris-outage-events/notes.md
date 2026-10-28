# iaea-pris-outage-events

Discovery notes — dated evidence, decisions, failed approaches.

## 2026-10-28 — session tick: International organisations region (UN-agency scan)

### Why this lead

The region's named UN agencies (UNHCR done, UNICEF parked-superseded, UNODC class D) left IAEA as the one
major UN agency with genuinely event-level operational data: PRIS carries monthly production/power-loss
records since 1970 plus "outage and operational event information" (publisher's own description). A
row-level outage-duration task would avoid the aggregate-panel defect that closed the OECD/ITU leads.

### What was checked, in order (licence first, access second - both cheap)

1. IAEA Terms and Conditions of Use (nucleus.iaea.org/Pages/Others/Disclaimer.aspx, read 2026-10-28):
   content clause is permissive ("encourages the use, reproduction and dissemination of the text, multimedia
   and data presented ... for use in commercial and non-commercial products or services, provided that
   appropriate acknowledgement"), but the Digital Repositories and Databases clause reads "The data in the
   IAEA digital repositories and databases is provided free of charge for educational and informational use."
   Two clauses, two scopes -> ambiguous for publishing a derived ML dataset. No dataset-level licence found
   on PRIS pages ("(c) 1998-2026 IAEA, All rights reserved").
2. IAEA Rights and Permissions page: publications need permission; AI usage "subject to a licensing agreement".
3. Access: pris.iaea.org/about.aspx + pris-stats.iaea.org/data-browser (read 2026-10-28). The August 2026
   revamp (IAEA news, 2026-08-21: "first of two planned releases"; second due early 2027) serves data through
   embedded Microsoft Power BI dashboards ("Sign in to view this report"). The 15 listed public dashboards
   contain NO outage-events table - the event-level data the task needed is described in the PRIS blurb but
   not exposed publicly in the new browser. The old per-reactor ASPX pages redirect to the new homepage
   (verified on ReactorDetails.aspx?current=1074).

### Decision

DROPPED (class C closed under the standing policy; access undocumented on top). The licence is ambiguous
and the one public channel does not carry the event tables, so no task design was measurable. Cost: 5 web
reads, 0 data requests. Reopen triggers recorded in record.json next_action (explicit open licence, or the
2027 second release exposing a documented bulk/API with the outage tables, or a candidate-specific operator
risk acceptance - which would still leave the access question).
