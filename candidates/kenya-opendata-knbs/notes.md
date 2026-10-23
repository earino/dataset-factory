# kenya-opendata-knbs — notes

Country-infrastructure record for the Africa tick's Kenya probe. Opened 2026-10-21.
All probes anonymous from the coordinator, via `.factory/http_probe.py` (session scratch).

## Probes (2026-10-21)

- `https://open.data.go.ke` (Kenya Open Data portal) — NXDOMAIN:
  `<urlopen error [Errno -2] Name or service not known>`. The historical national CKAN
  portal is gone from DNS. (Same failure class as data.gov.za this session, measured the
  same way.)
- `https://www.knbs.or.ke/` — 200, 294,945 B, WordPress. Strict TLS fails:
  `certificate verify failed: unable to get local issuer certificate` (incomplete chain —
  probes ran with verification disabled; recorded as a consumer-side property).
- `https://www.knbs.or.ke/data-portals/` — 200, 149,772 B (`/data-portal/` 301s here;
  `/download-centre/` is 404). Grep for data-file links (.pdf/.xlsx/.csv/.zip): **zero**.
  The page links out to: kenya-sdg.github.io, kenya.opendataforafrica.org, a Google Form,
  and social media.
- `https://kenya.opendataforafrica.org/` — HTTP 403 Cloudflare challenge
  ("Just a moment...", 5,620 B) to headless clients. Third-party Knoema aggregator; its
  terms are not KNBS's licence, and the schema is the aggregator's guess — not a
  publisher channel.
- `https://kenya-sdg.github.io/` — 200, 22,502 B: static SDG dashboard, a visualisation
  not a bulk source.
- Footer measured on knbs.or.ke: "Copyright 2026 © Kenya National Bureau of Statistics |
  All Rights Reserved". No terms-of-use or open-licence page found.

## Probes (2026-10-23) — the unpark question is now answered; the answer carries an NC condition

The record's recorded unpark question was: does any KNBS-published channel offer
anonymous bulk/API access with stated licence terms? Answer as of 2026-10-23: **yes —
a new channel exists — but the stated licence is CC BY-NC 4.0.**

- `https://repository.knbs.or.ke/` — KNBS **National Statistical Repository**, DSpace
  10.0, live. REST API root `https://repository.knbs.or.ke/server/api` answers
  anonymously with full endpoint links (also advertises an OAI-PMH endpoint).
- Communities: 20 top-level (Demographic and Social; 201 Macroeconomic Accounts; 202
  Business; 203 Sectoral Statistics with 8 collections — Agriculture, Energy, Mining/
  Manufacturing/Construction, Transport, Tourism, Banking/Insurance/Financial, Wholesale/
  Retail; 3 Environmental; 408 Safety and Security with a "Crime and Criminal Justice"
  collection; 4 Governance; 511 Food Security and Nutrition; 603 Statistical Registers;
  ...).
- Discover index: `server/api/discover/search/objects` totalElements = **1,366**.
  First sample objects are dated KNBS statistical releases: "Leading Economic Indicators –
  December 2011", "Leading Economic Indicators – September 2020", "The Kenya Consumer
  Price Index and Inflation Report April 2026", "Kenya Quarterly Gross Domestic Product
  First Quarter 2019", "Economic Survey 2007", "Kenya Quarterly Balance of Payments Third
  Quarter, 2017" — i.e. a long historical run of monthly/quarterly publications.
- Item-level enumeration is restricted anonymously: `server/api/core/items` → **HTTP
  401**; `server/api/core/collections/{uuid}/items` → **HTTP 404**; discover
  `location.collection:{uuid}` queries → 0 results. So the 1,366 objects' formats,
  series and per-item licences were NOT enumerated this tick. A channel is not a task.
- Licence instrument (the publisher's own page, fetched directly 2026-10-23):
  `https://repository.knbs.or.ke/info/accessibility`, section "Open data & licensing":

  > "Unless stated otherwise on the item itself, content in this repository may be
  > reused for non-commercial purposes, with attribution. CC BY-NC 4.0"

  The page footer separately carries "Kenya National Bureau of Statistics, Copyright
  © 2026". Per the licence-posture rule this is recorded as a stated conditional
  licence (non-commercial + attribution), NOT an open-data grant, and NOT a risk
  acceptance: whether a non-commercial condition is acceptable for our public releases
  is an operator decision (record.json next_action step 1).
- `https://www.centralbank.go.ke/` — unreachable from the coordinator this tick
  (connection-level failure); the regulator probes from the original next_action (c)
  (CBK, KRA, NTSA) remain genuinely unprobed. Recorded as not-probed, not negative.

## Verdict (updated 2026-10-23)

Still PARK, but the blocker changed from "no channel with stated terms exists" to a
decision plus a census gap: (1) the stated blanket licence is CC BY-NC 4.0 — operator
decision required before any build; (2) item-level content is not anonymously
enumerable, so no series/timing evidence exists yet; (3) regulator probes still open.

## Note for the Africa rotation

The two African national open-data portals named by the tick's starting map
(data.gov.za, open.data.go.ke) are both NXDOMAIN as of 2026-10-21. The live, openly
licensed African channel found then was a sector treasury portal
(municipaldata.treasury.gov.za). As of 2026-10-23 Kenya has a NEW publisher channel
(the KNBS National Statistical Repository) whose content is real but NC-licensed and
not anonymously enumerable at item grain — lead the next Kenya tick with the operator's
NC decision and the repository UI (browser-rendered) census, then the regulators.

## Reproducing the 2026-10-23 probes

`probe_repository.py` in this directory re-runs the repository probes (API root,
communities, discover count + sample, item-endpoint 401/404, accessibility-page licence
quote). Run: `python3 probe_repository.py`.
