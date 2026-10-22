# unodc-data-portal — discovery notes (2026-10-22)

Licence-first triage of UNODC's data portal. Closed as class D before any task probing.

## Channels probed (all 2026-10-22)

```
curl -sL 'https://data.unodc.org/'                       -> 200, 44,350 B
curl -sL 'https://data.unodc.org/datasearch'             -> 200, 61,728 B
curl -s  -o /dev/null -w '%{http_code}' 'https://data.unodc.org/about'         -> 404
curl -s  -o /dev/null -w '%{http_code}' 'https://data.unodc.org/help'          -> 404
curl -s  -o /dev/null -w '%{http_code}' 'https://data.unod.org/api'            -> 404
curl -s  -o /dev/null -w '%{http_code}' 'https://data.unodc.org/documentation' -> 404
curl -s  -o /dev/null -w '%{http_code}' 'https://data.unodc.org/faq'           -> 404
curl -s  -o /dev/null -w '%{http_code}' 'https://dataunodc.un.org/'           -> 302
```

## Licence search (the decisive probe)

- grep for `creative commons|cc-by|cc by|open data|public domain` on the home and datasearch
  HTML: **0 matches** on both pages.
- The footer of both pages carries `United Nations Copyright © 2025 UNODC - Data Portal` and links
  only to:
  - https://www.un.org/en/about-us/copyright (standing UN copyright notice)
  - https://www.unodc.org/unodc/en/legal.html (the portal's "Terms and Conditions" href)
- Legal notice fetched (28,672 B), clause (a) verbatim:

> "The United Nations grants permission to Users to visit the Site and to download and copy the
> information, documents and materials (collectively, "Materials") from the Site for the User's
> personal, non-commercial use, without any right to resell or redistribute them or to compile or
> create derivative works therefrom, subject to the terms and conditions outlined below, and also
> subject to more specific restrictions that may apply to specific Material within this Site."

- Consistent posture on the publisher's other data service (EWA on New Psychoactive Substances,
  unodc.org/LSS/Page/NPS/Guide): "Data, whether in aggregated or disaggregated form, cannot be
> published without prior written authorization by UNODC" plus an explicit prohibition on feeding
  the data to any AI/automated processing service.

## Verdict

reject (licence class D). Under the 2026-10-21 standing policy ("we only build on sources that are
already clean"), an unclear or prohibitive licence is a closed door, not a queue: no permission
email, no dated path out. Total cost of this verdict: six HTTP fetches — the licence triage did its
job before any schema or volume work was spent. No US source substituted; publisher jurisdiction
Vienna, Austria (AT).
