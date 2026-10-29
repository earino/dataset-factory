# fwc-enterprise-agreement-approval-duration

Opened and closed 2026-10-29 (Oceania discovery tick). All probes anonymous
(supported browser + plain-client fetches), coordinator only.

## Task shape (recorded for reopening)

Enterprise agreement approval latency: FWC publishes each approval application in
'Agreements in progress' ~2 business days after lodgement (title, industry, application
type visible); the approval decision (and its date) follows later. Publisher-quoted
timelines: standard 20 days (simple) / 45 days (complex); measured median 15 days for
2021-22 approvals; ~199 and ~238 applications lodged in successive fortnights of
December 2022 (FWC statistical report). Bulk channel: direct Excel downloads under
/documents/agreements/resources/ - agreementsfrom1994.xlsx, agreements2017..2026.xlsx
(2026 updated weekly), terminated_agreements_list.xlsx (monthly).

## Licence chain (decisive, class D)

- Plain-client GET https://www.fwc.gov.au/footer/copyright -> HTTP 403 (site blocks
  scripted clients; one bounded attempt). All further reads in the supported browser.
- Footer 'Copyright' link -> https://www.fwc.gov.au/about-us/legal-and-freedom-information/about-website/copyright
  (read 2026-10-29): 'You may download, display, print and reproduce this material in
  unaltered form only (retaining this notice) for your personal, non-commercial use or
  use within your organisation. Apart from any use as permitted under the Copyright Act
  1968, or unless otherwise explicitly indicated on particular material, all other
  rights are reserved.' and 'The Commission is progressively reviewing its website
  material to license it for public reuse under a Creative Commons (CC) licence.'
- Dataset page (find-enterprise-agreement, read 2026-10-29): searched the rendered text
  for 'creative commons', 'cc by', 'licence', 'license', 'attribution', 'open data' -
  all absent. No 'otherwise explicitly indicated' instrument for the agreement lists.
- data.gov.au sweep 2026-10-29 (working CKAN endpoint
  https://data.gov.au/data/api/3/action/package_search): no FWC per-agreement dataset;
  'Workplace Agreements Database: Trends in Enterprise Bargaining' (DEWR) carries
  licence 'Other (unpublished)' and an aggregate HTML resource only.
- Verdict: class D; the register cannot ship as a derived public dataset. Reopen
  conditions in record.json (open licence for these materials, open channel, or written
  authorisation).

## Population caveat (for any reopening)

Bulk lists = approved-agreements register; in-progress list is live-only;
refused/withdrawn applications surface only via decision records. A duration task from
bulk lists alone is conditioned on eventual approval (survivorship). Recovering
non-approved applications from decisions is an unmeasured per-case cost.

Scratch: /opt/data/cache/scratch/fwc/ (24h-pruned; recipes above reproduce all fetches).
