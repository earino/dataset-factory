# tc-gv-licence-application-outcome

GB lead opened 2026-11-05 (UK discovery tick). Publisher: Traffic Commissioners for
Great Britain (Office of the Traffic Commissioner, supported by DVSA). Status:
investigating - licence A, exact timing and exact reference-number linkage all
measured; the ONE unresolved contract is split capacity at national scale plus the
archive coverage ledger (named worker probe in record.next_action).

## The task

For a new goods-vehicle operator licence application, at the instant its listing is
published in the weekly "Applications and Decisions" (AD) gazette (T; the 21-day
statutory objection window opens at publication), predict the resolution it reaches:
granted without public inquiry / called to a public inquiry (ground S13) / refused /
withdrawn. Features = the listing as published. Label = outcome published in later
editions of the same area's gazette, linked by the application reference number.

Who would use it: applicants and transport consultants gauging refusal or inquiry
risk before filing; the OTC/DVSA for inquiry workload planning; regulatory-consistency
research (do identical structural applications resolve differently across areas/years).

## Why this is a genuinely good register (measured, not assumed)

- The gazette IS the dated publication record: every edition prints its publication
  date and objection deadline on page 1. As-of evidence is the record itself.
- Outcomes are NOT censored: routine grants (2.1/2.3), refusals (2.2/2.4),
  withdrawals (4.1), untaken grants (4.2), PI notices (5.1, with statutory ground
  codes) and PI decisions (5.2) are all published weekly. The advertised VOL search
  service is NXDOMAIN (2026-11-05), so the PDFs are the population record.
- Linkage is EXACT, not name-matched: the OF-number in the listing is the same
  reference in the outcome sections and the eventual licence number.

## Probes (2026-11-05, anonymous, from the coordinator; retained in probe/)

| Command | Result |
|---|---|
| `probe/probe_gazette_sample.py <pdf> --out out/*.json` | four editions parsed (east AD-5611 2026-10-28 sha256 a1e1e06e..., east AD-5598 2026-07-29 c87112a8..., east AD-5308 2021-01-06 9dd88b89... (Wayback copy), wales AD-8981 2026-10-28 247581da...); volumes in record.measurements; pypdf parses the 9-section layout identically in the 2021 and 2026 eras |
| `probe/probe_archive_coverage.py --page-url <east page> --out out/archive_coverage_east_2026_11_05.json` | live page: 43 PDF links, all 2026; old asset HEAD -> 410; Wayback: 26 monthly-collapsed 200 snapshots (2015:1, 2019:1, 2020:6, 2021:2, 2022:11, 2023:1, 2024:1, 2025:1, 2026:2); a 2022 snapshot carries 53 attachment links back to Jan 2021; archived PDF fetch proven (ad_5308, 422,289 B, 1.8 s, parses); 2015 snapshot: no PDF links (pre-2016 format) |
| Wayback CDX direct | `ad_5308_6_January_2021.pdf` asset captured 2021-08-11 and 2022-01-05 (application/pdf, 200) |
| `curl assets.../Copy_of_Result_of_hearings_-_New__1_.csv` | driver-conduct decisions: 5,303 rows ROLLING 12 MONTHS (hearing date, postcode prefix, name, birth year, LGV/PCV, decision, appeal) - no history, not a task; proves decision volume |
| data.gov.uk CKAN `package_search q=bovine tb herd` | 12 hits, all aggregates/compensation/VNTR - no herd-grain extract (bTB reopen condition still unmet; see STATE 2026-11-05) |

## Dated examples (Europe/London; all timestamps from the gazettes themselves)

- POSITIVE-path grant: OF2093311 R Brownline UK Ltd - listed in AD-5598 Section 1.1
  (published 29/07/2026, objection deadline 19/08/2026), granted in AD-5611
  Section 2.1 (published 28/10/2026). Same for OF2093050 SN ULTRA LOGIK LIMITED.
- NEGATIVE: OF2088279 SI SAGAL LOGISTICS LTD - listed in AD-5598 Section 1.1
  (published 29/07/2026), refused in AD-5611 Section 2.2 (published 28/10/2026).
- RIGHT-CENSORED live edge: OF2091916 NEIL DRURY HAULAGE LTD - PI noticed in
  AD-5611 Section 5.1 under "S13 - Consideration of new application under Section 13"
  for a hearing on 3 December 2026; outcome lies after the current archive edge.

Feature event window = everything in the listing as published at T; first availability
= the edition's publication date (the statutory notice act); eligibility = the
listing itself (Section 1.1); target = the outcome published in later editions.
No part of the target window precedes T.

## Licence (class A, from the publisher's own instrument)

GOV.UK guidance page hosting the gazettes, footer (HTML fetched 2026-11-05):
"All content is available under the Open Government Licence v3.0, except where
otherwise stated." No contrary statement on any page or in the four sampled PDFs.
Caveat carried in the record: the PDF front page's "Arrangements for copies to be
purchased" line is a print-distribution relic of Regulation 21 (Goods Vehicles
(Licensing of Operators) Regulations 1995), not a licence restriction; re-read the
OGL and any TC-specific terms at construction.

## Sibling leads recorded, NOT opened

- Operator register exit: VOL weekly per-area register CSVs (data.gov.uk, current
  state, updated Sundays) + gazette sections 7.1/7.2/8 (surrender/termination/
  revocation events) - a register-exit family task (cqc/ofsted precedents) in a new
  domain. Deferred until this candidate is decided.
- PSV "Notices and Proceedings" (bus/coach sibling gazette), unmeasured.

## What is NOT yet measured (the named next probe)

National per-year counts per outcome class, per-window split counts, repeat-applicant
clustering, refusal-grounds distribution, and the per-area per-edition coverage
ledger (which editions are actually retrievable). These need the bounded worker
aggregate; two sample editions are not counts. UKGWA's CDX endpoint served a TNA
HTML shell this session - probe it once from the worker and record either way.

## Reproduction

Probe scripts + JSON outputs live in probe/ and probe/out/ (repo). The four sample
PDFs stay out of git (scratch only, sha256-pinned above; re-fetchable from the live
pages / the named Wayback captures).
