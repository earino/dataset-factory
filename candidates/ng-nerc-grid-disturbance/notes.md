# ng-nerc-grid-disturbance — probe log

## 2026-11-07 — licence-first triage (Africa tick), closed class C before task probing

### Channel sweep (publisher instruments), commands and results

```
GET https://nerc.gov.ng/terms-conditions/
    -> WordPress error page: "There has been a critical error on this website"
GET https://nerc.gov.ng/  (rendered homepage, curl)
    Footer: "© 2026 Nigerian Electricity Regulatory Commission. All rights reserved."
    Only "licens*" links in navigation: "Licensing, Permits & Authorizations",
    "licencees" — electricity-sector licensing, not data licensing.
```

Report front matter (published PDFs, read via search snippets the same day):

- 2025 Annual Report: "freely available to Nigerian Electricity Supply Industry
  stakeholders, government agencies and corporations. Individuals, on request,
  can also obtain any issue without a charge." — free of charge, not a reuse grant.
- 2026 Q1 Report: same front-matter pattern ("Individuals can also access any issue
  freely from the Commission's Website").

### Publisher-side event figures (quoted, not constructed)

From NERC/2023/035 Figure 2 (partial, total): 2016: 6/22, 2017: 9/15, 2018: 1/12,
2019: 1/10, 2020: 0/4, 2021: 2/2, 2022: 2/4, 2023: 0/3.
2024 Annual Report: 9 incidents in 2024. 2025 Annual Report: 2 in 2025.
2026 Q1 Report: 2 in Q1 2026 (total 23 Jan, partial 27 Jan) — with unit-level
detail (date, time, type, immediate cause, restoration) in the report tables.

Feature-grain observation: NERC operational data products are month/quarter
aggregates (e.g. "Average Daily System Frequency [Hz] 2021-2024" by month,
average hourly generation) — no published daily-resolution operational stream
was identified for day-ahead features.

### Decision

DROPPED, class C. Licence is the recorded blocker; the feature-timing defect and
sparse clustered positives are recorded as secondary so a reopen is not mistaken
for "one licence fix away". Novelty never reached, not claimed.
