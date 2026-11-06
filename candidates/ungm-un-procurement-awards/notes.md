# ungm-un-procurement-awards — discovery notes

Opened and closed 2026-11-06, discovery-only session (International organisations
region). Dropped on licence (class D) at triage, before any task probing — the
cheap veto working as intended. This record exists so no future session re-pays the
idea's discovery cost without new evidence.

## Why this lead was considered

All tick-named publishers (WB, OECD, UNHCR, UNICEF, UNODC, WHO, IMF, ITU) already carry
recorded verdicts, most re-checked within the last ten days. The one substantive
un-probed case-grain register in the UN family was the UN system's own procurement
portal, UNGM: ~40 UN organizations publish tender notices and contract award notices
there, and award pages carry org, vendor, value, award date and country (example
fetched in search results: ungm.org/Public/ContractAward/152334). Multi-agency
volume is real (ASR dashboards cite 2013-present data).

## Commands and evidence (all anonymous, 2026-11-06)

- `GET https://www.ungm.org/Public/Pages/Terms` → 200, 114,147 B. Extracted clauses:
  - Clause 1 (Definitions): "Materials include: Requests for proposals; Invitations to
    bid; ... Specific procurement notices; ... Notices of cancellation in respect of
    the above; and Notices of award."
  - Clause 5.2: "The User is permitted to download or print extracts of the Materials
    on the Site for their personal use only ... None of the material on the Site may be
    used for any commercial or public use, and no part of such material may be
    reproduced or stored in or transmitted to any other website."
  - Clause 5.3: "No material on the Site may be disseminated in any form, either
    electronic or non-electronic, or included in any retrieval system or site without
    the prior written permission of UNGM."
  - Clause 7.2: "The Materials relating to procurement opportunities from the United
    Nations organizations and its partners available on the Site is copyrighted by
    these organizations. It may not be reproduced, stored, transmitted or
    photocopied in any form or by any means without the prior written consent of the
    respective organizations."
- `GET https://www.unops.org/terms-of-use` → 200, 212,125 B. "UNOPS grants permission
  to Users to visit the Site and to download and copy the information, documents and
  materials (collectively, "Materials") from the Site for the User's personal,
  non-commercial use, without any right to resell or redistribute them or to compile or
  create derivative works therefrom..." — the standard UN-style notice.
- `GET https://data.unops.org/` → 200, 2,093 B, JS shell ("UNOPS Data Portal"), no
  licence statement. UNOPS's Procurement Manual 10.2.1 says UNOPS posts award/PO
  information at data.unops.org — but the site-wide terms above govern it, and no
  dataset-level licence exists on the channel (generic Legal / Terms of use links only).
- Administration (for the jurisdiction field): UNGM's own 2016 presentation
  (UNGM Secretariat/UNOPS) — "UNOPS is the UNGM Service Provider since 2008 as part of
  the UNOPS/IAPSO merger"; UNOPS page on the UNGM Knowledge Centre: "Based in
  Copenhagen, Marmorvej 51, 2100 Copenhagen, Denmark". UNOPS HQ → DK.
- UNGM help centre: "UNGM is the official procurement portal of the United Nations
  System"; contract awards "accessible publicly and free of charge".

## Interpretation

"Materials" is defined to include exactly what a prediction dataset would ship (tender
notices, cancellation notices, notices of award), and the grant is personal-use-only
with an explicit prohibition on dissemination "in any form" and on inclusion in "any
retrieval system". Clause 7.2 adds that the copyright sits with the individual UN
organizations — which closes the obvious sibling-channel escape for UNGM itself, but
also names the one real reopen path: a single UN organization attaching an explicit
open licence to its OWN award records channel would be a new source with its own
discovery cycle. UNOPS — the administering organization and the most transparency-
forward UN entity — carries the same prohibitive notice, so no clean channel exists
today.

## Task-shape note for any future reopen

Independent of licence: UN award records share the defect measured on
wb-procurement-contract-awards (dropped 2026-11-03) — at-award attributes with no
post-award outcomes make every derivable label a future-award-occurrence on the same
administrative stream (pipeline-continuation hazard). A reopen needs BOTH a licence
change AND a post-award outcome family with documented timing.

## Not probed (by design, licence-first)

Tender-page schemas, award volume by org/year, cancellation-notice linkage, vendor
identity joins, the ASR dashboards' data behind the interactive charts, and the
`http://dsdb/...`-style internal resource URLs. No bulk or scraping questions were
reached.
