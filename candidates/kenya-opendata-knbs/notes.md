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

## Verdict

PARK — infrastructure blockers, not a task defect; nothing about Kenyan statistical
products was disqualified because nothing could be read. Unpark path recorded in
record.json next_action (NADA microdata catalogue → successor portal → sector regulators).

## Note for the Africa rotation

The two African national open-data portals named by the tick's starting map
(data.gov.za, open.data.go.ke) are both NXDOMAIN as of 2026-10-21. The live, openly
licensed African channel found this tick was a sector treasury portal
(municipaldata.treasury.gov.za) — for the next Africa tick, lead with treasury/audit/
procurement-style sector infrastructure rather than the national portals.
