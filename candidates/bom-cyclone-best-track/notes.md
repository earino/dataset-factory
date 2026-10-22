# bom-cyclone-best-track - row-level notes

Session: scheduled discovery, 2026-10-22 (Oceania tick). Verdict: **reject, licence class D**.

## Triage order

Licence triaged FIRST, per the standing policy (2026-10-21): no schema or volume probing
was spent before the licence veto.

## Commands and results

1. Publisher licence instrument (site-level):
   `web_extract http://www.bom.gov.au/other/copyright.shtml` (read 2026-10-22)
   - Default for content with no stated terms: "you can download, copy and use our content
     for personal use, or use within your organisation. **You must not supply it to any
     other person** or use it for any commercial purpose."
   - "we do not allow you to use automated or manual techniques to hack, scrape or
     otherwise extract material from our site."
   - CC BY named only as one of several permission channels, "check the terms of use for
     the content you want".

2. Dataset-level instrument:
   `web_extract https://www.bom.gov.au/cyclone/tropical-cyclone-knowledge-centre/databases/`
   (read 2026-10-22)
   - Links: best-track CSV https://www.bom.gov.au/clim_data/IDCKMSTM0S.csv (page says
     "Last updated on 2026-10-22"), specification PDF TC_Database_Structure_Oct2011.pdf,
     Objective Tropical Cyclone Reanalysis database 1981-2016 (OTCR_alldata_final_external.csv).
   - **No licence or terms text anywhere on the page** -> site default governs.

3. Access probe (measured, 2026-10-22 04:07 UTC):
   `curl -sS -I "https://www.bom.gov.au/clim_data/IDCKMSTM0S.csv"` -> `HTTP/2 403`,
   content-type text/html, akamai-cache-status "Error from child".
   `curl -sS -r 0-1023 <same URL>` -> anti-scraping block page: "Your access is blocked
   due to the detection of a potential automated access request." The block page offers
   the anonymous FTP channel ("free to access, but use is subject to the default terms
   of the Bureau's copyright notice") or the charged Registered User service
   (http://reg.bom.gov.au/other/charges.shtml) for use that does not comply with the
   default terms.
   - No file bytes retrieved via HTTP. Schema/volume were NOT measured, by design.

## Why class D and not C

The default is not "unclear" - it is explicit: redistribution (supplying to any other
person) is prohibited unless a page-level licence says otherwise, and this dataset's page
says nothing. A published derived dataset would supply the rows to other people. Under
the standing policy (only build on already-clean sources) this is a drop on sight, with
the clause quoted above.

## Task it would have supported (recorded so the lead is not re-derived)

Landfall-within-48h / rapid-intensification classification from 6-hourly best-track
fixes (Australian Tropical Cyclone Database, storms since 1969 per the Southern
Hemisphere Data Portal page). Storms cluster, so split capacity would have been counted
per storm-season, not per track fix. Never probed - the licence veto comes first.

## What would reopen it

- A redistribution-permitting licence statement on the dataset's own page, or
- A redistributor holding a verifiable rights-holder grant. NCAR RDA ds824.1 republishes
  Southern Hemisphere best tracks with a declared CC BY 4.0 legal constraint
  (data.ucar.edu) - if that grant is verifiable from the rights holder's side, the same
  task could be re-vet against that source. It would be a NEW source with its own
  licence evidence, not a licence for BoM's own copy.

## State licence note (regional texture)

The operator brief warned that several Australian states are not open; this session also
recorded ATSB (federal) limiting bulk export to 200 rows per dashboard download with
"you cannot download the whole database" (see atsb-aviation-occurrence-triage/). BoM
(federal) is the second federal AU channel closed on terms this session.
