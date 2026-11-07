# gh-bog-treasury-auction — probe log

## 2026-11-07 — licence-first triage (Africa tick), closed class C before archive probing

### Channel sweep (publisher instruments), commands and results

```
GET https://www.bog.gov.gh/disclaimer/  -> HTTP 200 (rendered)
    Footer: "© 2026 Bank of Ghana. All rights reserved."
    Body: accuracy/non-liability disclaimer only ("The information on this site
    is provided for general reference purposes only..."); no reuse grant.
GET https://www.bog.gov.gh/terms-conditions/ -> HTTP 404 (site 404 page)
GET https://www.bog.gov.gh/robots.txt  -> nginx 404
```

Auction-results pages (read via search-index renderings of the live pages, same day):

- https://www.bog.gov.gh/gog_auction_results/ — weekly GOG T-bill tenders,
  "Results of GOG Tender 2032" (Nov 6 2026), 2031 (Oct 30), 2030, 2029, 2028, 2027,
  2026 ... earlier-page links back through 2021 and before.
- https://www.bog.gov.gh/bog_auction_results/ — BOG bill tenders,
  "Results of Tender 886 Held on 4 November 2026", 885 (Oct 26/28), 884, 883, 882,
  881, 880 — twice-weekly; consecutive numbering implies a long continuous archive.

Both carry the same "© 2026 Bank of Ghana. All rights reserved." footer.

### Decision

DROPPED, class C (bare copyright on every instrument; no reuse grant; terms page 404;
accuracy-only disclaimer). Same posture as CBK Kenya (2026-10-30) — now a pattern across
two African central banks, not an isolated case.

No archive fetch, parsing, rate extraction or split counting was done; novelty never
reached and not claimed.
