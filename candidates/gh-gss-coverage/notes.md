# gh-gss-coverage — probe log

## 2026-11-07 — Ghana sweep (Africa tick), closed at triage

### Channel sweep, commands and results

```
GET https://statsghana.gov.gh/  (rendered)
  Footer: "© 2026 | Ghana ..." (bare copyright, no licence/terms link)
  Links found matching legal/licence patterns: "Legal Mandate" (/about/legal-mandate),
  "Privacy & Confidentiality" (/about/privacy-confidentiality),
  "Open Data" -> https://dataportals.org/portal/ghana_opendataforafrica/
  Home surface: headline aggregates (CPI inflation 5.5% Oct 2026, PPI 4.8% Sep 2026,
  IIP 3.0% 2026Q2, PBCI 5.1% Sep 2026, GDP growth) and census products (PHC/IBES).
```

- "Legal Mandate" and "Privacy & Confidentiality" are statutory/privacy pages,
  not data licences (Legal Mandate = the Service's statutory basis).
- The "Open Data" link is an aggregator record (dataportals.org) for the AfDB
  Open Data Platform instance for Ghana - country/indicator aggregate series owned
  by third-party datasources: same family defect as uneca-ecastats-coverage
  (aggregate-only + mirror risk).

### Decision

DROPPED. Bare copyright (class C posture) on the publisher's own site, plus
aggregate-only visible content. No task was formulated; nothing was counted.
Together with gh-opendata-coverage (portal TCP-refused, 2026-10-27) and
gh-bog-treasury-auction (bare copyright, 2026-11-07), this completes the
Ghana sweep of the three most obvious publishers.
