# notes — unhcr-refugee-data-finder (opened 2026-10-20)

Verdict: PARK. Access/automation blocker, not a licence blocker. The datasets are CC BY 4.0
(granted on the methodology page, quoted below), but no machine-fetchable bulk path could
be found: the host is WAF-gated, exports are interactive-app-only, and the full series is
not mirrored anywhere with a stable URL.

## Access probes (2026-10-20, coordinator)

```
curl https://www.unhcr.org/refugee-statistics/                -> HTTP 403, 182,520 B (challenge page)
real browser, same URL                                        -> loads (title: "Refugee Data Finder - Key Indicators")
in-page same-origin fetch of ?v2url=dc36b6 deep link         -> HTTP 403, 222,964 B (fetch() is WAF-distinguished)
real-tab navigation to the deep link                         -> opens the interactive Data Finder app (view selector, not a file)
programmatic click of the app's "Download" control            -> no file landed in the browser download dir (JS-driven dialog form)
curl http://popstats.unhcr.org/en/overview                    -> HTTP 000 (host gone)
curl https://data.unhcr.org/en/index                         -> HTTP 404 (old portal path dead)
curl https://data.humdata.org/api/3/action/package_search... -> HTTP 200 (CKAN API fine; but no full-series mirror)
```

The RDF app is a Symfony/UX live-component application (turbo/stimulus bundles,
`data_finder_controller-*.js` submits a FormData via Turbo POST; no API route appears in
the controller source or the page's network entries). The homepage's export deep links:

```
population by country of origin   https://www.unhcr.org/refugee-statistics/download/?v2url=dc36b6
population by host country        https://www.unhcr.org/refugee-statistics/download/?v2url=bd1059
demographics of refugees          https://www.unhcr.org/refugee-statistics/download/?v2url=d3e49d
solutions 2015-2024               https://www.unhcr.org/refugee-statistics/download/?v2url=d63e73
new asylum applications 2024      https://www.unhcr.org/refugee-statistics/download/?v2url=1e3087
```

...are view selectors into the app, not stable file URLs.

## Licence (read 2026-10-20, real browser)

- Methodology page, "Data terms and conditions of usage": **"Except where otherwise
  indicated, the datasets made available by UNHCR on UNHCR Refugee Population Statistics
  Database are licensed under the Creative Commons Attribution 4.0 International Public
  License."** — a clear CC BY 4.0 grant for the data.
- Site-wide website terms (https://www.unhcr.org/contact-us/terms-and-conditions-use):
  extracts may be reproduced "for research or private study but not for sale"; "Any use
  other than for personal or educational purposes, including reproduction, scraping by
  artificial intelligence (AI), or translation of substantial portions of the Content of
  the UNHCR website, requires the express prior written permission of UNHCR."
- Reading: the dataset-specific CC BY 4.0 grant governs the statistics; the website ToU is
  the default for website Content. The explicit AI-scraping clause in the ToU is recorded
  because it shows this publisher's posture, and it would apply to any scraping that
  works around the WAF rather than using the granted datasets. Tension flagged for the
  operator if unparked.

## HDX check (does a mirror unblock the data?)

HDX (OCHA Centre for Humanitarian Data) hosts UNHCR datasets with CC BY / CC BY-IGO
metadata, but the full origin-year population series is NOT there — only per-country
extracts (afg/bgd "forcibly displaced population by origin", updated 2026-08-17), the
situations CSV, reference GIS layers, and yearbook archives. So no stable anonymous
mirror of the full series exists.

## Recency (the series itself is fine)

The homepage reports end-2025 global figures (117.8M forcibly displaced; charts 2000-2025),
so the annual series is maintained and current. The blocker is purely the export channel.

## Task shapes this source would support (for whoever unparks)

1. Situation growth (annual): origin-country-year refugee/IPTC population; will it grow
   >25% in D+1? Label from the D+1 row (documented process: UNHCR's compiled statistics).
2. Asylum applications (monthly): applications by origin × country of asylum; will
   applications exceed a threshold next month? Higher grain, same access problem.
   Prior art to check before building either: UNHCR Innovation Service "Project Jetson"
   (internal forecasting of new arrivals), displacement-forecasting literature, and the
   old Kaggle UNHCR mirrors.

## Unpark question

Can the RDF population/asylum CSVs be fetched by a non-interactive client from a
datacenter IP — a documented export URL, an API, or written guidance from UNHCR's data
team (RDF feedback form)? Failing that, does the operator accept a once-per-release
browser-captured export as provenance? Until one of those, the thinner annual alternative
is UNICEF's SDMX republishing of the refugee-by-origin counts (different publisher; see
unicef-sdmx-* candidate if opened).

## What NOT to redo next session

- popstats.unhcr.org and data.unhcr.org/en/index are dead; don't re-probe.
- curl/fetch of www.unhcr.org is 403 by design; only real-browser navigation passes. The
  403 is a WAF, not a missing page — this note exists so the next session doesn't misread
  the site as "down" or the terms page as unreadable.
- HDX does not mirror the full population series; that search is done.

---

# REOPENED 2026-10-23 — status ready (asylum-application corridor doubling task)

The 2026-10-20 close-out above is wrong on one decisive point, and correcting it reopens
this lead the same way it was parked: on access, with the licence already clean.

**The correction.** "HDX does not mirror the full population series; that search is done"
was a search-visibility miss, not a fact. The ranked CKAN full-text results show
per-country extracts first; the global package
[`unhcr-population-data-for-world`](https://data.humdata.org/dataset/unhcr-population-data-for-world)
(created 2020-08-27, maintained by the **UNHCR organisation account**, dataset_source
"UNHCR") carries the complete origin x asylum x year panel in five per-phenomenon CSVs
(end-year population 7,281,295 B; demographics 29,504,789 B; **asylum applications
8,669,567 B**; asylum decisions 8,833,586 B; solutions 1,016,821 B). Anonymous,
documented, stable resource URLs. The unpark question is answered by the publisher's own
distribution, not by a workaround.

**Correction to "what NOT to redo":** the HDX search IS worth redoing — as
`package_show` on the organisation's packages, not full-text search. Lesson recorded:
a missing-series conclusion drawn from ranked search results needs a package-level
enumeration before it is written down.

## Bulk path, measured (2026-10-23, coordinator, curl)

```
curl -sSL "https://data.humdata.org/dataset/74cdbe77-0a0b-441b-9535-bacc263be2a8/resource/295cd9e4-8464-43ee-ad17-47196991a1f7/download/asylum_applications_residing_world.csv"
  -> HTTP 200, 8,669,567 bytes, 2.06 s
  sha256 d5808616c3d10d33925d4df5a3182a2028dd574d111e843cc207455ba45fe950
  (identical across two fetches; resource last modified 2026-08-20T15:33:49Z)
```

(Redirects: the download URL 302s to a signed URL; `curl -L` needed. No WAF, no auth.)

## The panel (probe_hdx_asylum.py)

120,597 data rows; years 2000-2025; 215 origins; 130 hosts; **annual corridor grain only**
(no month column — the RDF's monthly grain stays browser-only behind the WAF). Categorical
mix (skill requirement — count before deciding what a row means):

```
Procedure Type: G 105,862 / U 13,955 / J 780
Data Type:      P 113,635 / C 6,962
Application Type: N 70,405 / V 18,245 / A 17,894 / R 10,339 / NR 2,260 / J 715 ...
```

The task is defined on **G/P only** (99,281 rows, 6,936 corridors, 33.7M applications).
The U stream (UNHCR-conducted RSD) is a different population, not summed in.

## The duplicate-row puzzle, resolved by publisher cross-check

20,851 of 73,051 G/P corridor-year cells (28.5%) carry multiple rows with **identical
dimension columns but different counts** (2000 AFG→DEU G/V/P: 5,380 vs 5,756; 2000
AFG→AUS G/V/C: 90 vs 1,326). Present in every year including 2025, and identical in the
per-country extracts — so it is UNHCR's own export artifact, not a merge bug.

Resolution rule: **sum all G/P rows per corridor-year.** Evidence (probe_hdx_asylum_rule.py,
cross-checked against BAMF's published tables, which are UNHCR's own source for Germany):

| host-year | sum-all | BAMF total (Erst+Folge) | diff | max-rule | BAMF first |
|---|---|---|---|---|---|
| DEU 2000 | 117,600 | 117,648 | -0.04% | — | 78,564 |
| DEU 2010 | 48,544 | 48,589 | -0.09% | 41,312 | 41,332 |
| DEU 2015 | 476,630 | 476,649 | -0.004% | 441,898 | 441,899 |
| DEU 2016 | 745,510 | 745,545 | -0.005% | 722,374 | 722,370 |

The max-rule tracks BAMF's *first* applications and sum-all tracks BAMF's *total*:
the duplicate rows are **disjoint components (first vs follow-up) exported under one
type code**, so summing reconstructs the total. BAMF figures read 2026-10-23 from
bamf.de (Asylgeschäftsstatistik / Bundesamt in Zahlen) via search; the 2015/2016 totals
are quoted verbatim in multiple BAMF publications.

Coexistence checks (probe_hdx_asylum_coexist.py): 'V' never coexists with N/R/A in a
corridor-year (0 of 73,051) — V is an unsplit total, not an additive category; N-family
coexistence that could double-count (N with NR/RA/SP/NA) is rare (646 cells differ from a
V/NR-preferring rule; 196 eligible).

## The task and its measured base rates (probe_hdx_asylum_labels.py)

**For a corridor (origin O, host H) with ≥500 government-procedure applications in year D,
will applications in D+1 be ≥2x year D?**

Eligible corridor-years (host active in D+1), all label families measured:

```
decline 57.3% | grow>25% 27.4% | grow>50% 18.5% | >=2x 9.3% | >=3x 4.2%
```

Chosen label: **≥2x** (~9% prevalence; the house family of our other exceedance tasks).
Construction must not re-tune the threshold after seeing scores.

Splits (x2 label; counts computed from the source, host-active rule applied):

```
train  label-years 2001-2016: n=3,677  pos=302  (8.2%)   origin-year clusters=198
eval   label-years 2017-2021: n=1,918  pos=166  (8.7%)   clusters=109
holdout label-years 2022-2025: n=1,994  pos=234  (11.7%)  clusters=135
positives per label-year: train 2-53, eval 6-57, holdout 26-92 (both classes every year)
surge origins differ per window: train SYR/AFG/IRQ; eval VEN/AFG/COD; holdout TUR/VEN/IND/AFG/CUB
```

For scale: the parked annual origin-grain derivative (unicef-sdmx-refugee-origin-growth)
carried 34 eval positives; this carries 166 across 109 origin-year clusters.

Censoring (skill: recorded-event vs observed-absence): missing corridor row with the
host still reporting = observed zero; host silent in D+1 = unobserved target, excluded
(33 of 7,622 eligible rows, 0.43%). Hosts reporting per year: 67 (2000) → ~110 (2020s).

Reporting-model mix (probe_hdx_asylum_modelmix.py): eval and holdout eligible rows are
**100% split-type-coded**; the unsplit-V rows live in the training era (1,238 of 3,677
train rows), where the sum rule is exactly what the BAMF cross-check validates.

## Known-event fixtures (probe_hdx_asylum_fixture.py, exit 0)

```
SYR->DEU 2014->2015: 41,100 -> 162,510  x2 label TRUE  (2015 Syrian surge into Germany)
AFG->USA 2021->2022: 533    -> 25,082   x2 label TRUE  (post-Aug-2021 Taliban takeover)
AFG->DEU 2021->2022: 37,245 -> 48,602   x2 label FALSE (large growth, sub-doubling)
UKR->POL 2021->2022: 458    -> 1,593    BELOW ELIGIBILITY (458 < 500)
```

The UKR->POL row is the definitional insight: Ukrainians in the EU mostly registered
**temporary protection**, not asylum applications — the 2022 Ukraine displacement is
largely absent from this stream, and the holdout's top surge origins (TUR, VEN, IND, CUB)
reflect that. The task measures *application* surges; it does not measure TP
registrations, and a reviewer asking "where is Ukraine?" has the answer here.

## Prediction timing — dated example (all instants UTC)

This is a **publication-lag nowcast** (the abs-visitor-arrivals-direction pattern), not a
future-event forecast — the two must not be confused, and the distinction is recorded here
deliberately because the target window does NOT follow the instant.

- Feature event window: corridor-year totals for years ≤ D. For the live edge, D=2025
  (application events 2000-01-01 .. 2025-12-31).
- First availability of year-D data on the machine-fetchable channel: at latest the
  resource update observed **2026-08-20T15:33:49Z** (file's max Year = 2025). HDX package
  activity also shows 2026-06-11/19/22 refreshes aligned with UNHCR's annual cycle
  (Global Trends ~June of D+1); without archived vintages the conservative, observable
  instant is the latest refresh known to carry year D.
- Eligibility cutoff: year-D corridor total ≥ 500, evaluated at the instant.
- **Prediction instant: 2026-08-20T15:33:49Z** (the observed update carrying year-2025
  data).
- Target: label-year D+1 = 2026, window 2026-01-01T00:00Z .. 2026-12-31T24:00Z. The
  instant lies INSIDE this window (Jan-Aug 2026 elapsed at the instant), so no part of
  the "window follows the instant" claim is made. What is claimed, and what the channel
  supports: the 2026 corridor totals are **unpublished and unavailable** at the instant
  (first published ~mid-2027 on this channel), and for most non-EU hosts no public
  monthly corridor data exists anywhere in the interim — the forecaster's information
  set is genuinely limited to years ≤ D. Eurostat's monthly data covers EU hosts only
  and is outside this channel's shipped features.
- A strictly-future variant (at the same instant, predict year D+2 ≥ 2x the last
  PUBLISHED year D) was considered and rejected: the doubling baseline must be published
  at the instant, so a strict future window forces a two-year-back comparison — a
  different label with different measured base rates, i.e. a different task.
- Vintage policy: the HDX archive is revised in place. Values are construction-time
  current-vintage, pinned by the fetched snapshot's sha256. Same documented posture as
  abs-visitor-arrivals-direction. What is NOT claimed: historical operational
  availability of today's vintages at past instants.

## Licence (read 2026-10-23)

- HDX package record: `license_id "cc-by-igo"`, org "UNHCR - The UN Refugee Agency",
  dataset_source "UNHCR" — the publisher's own channel and licence choice.
- CC BY 3.0 IGO legal code (creativecommons.org/licenses/by/3.0/igo/legalcode):
  Section 3 grants Reproduce/Distribute/Publicly Perform + **create and distribute
  Adaptations** ("provided that You clearly label, demarcate or otherwise identify that
  changes were made"); no share-alike, no NC. Section 4: attribution; **no implied
  endorsement** by the Licensor; moral-rights no-derogation; no added restrictions.
  Class A; conditions carried into LICENSE.md.
- The 2026-10-20 unhcr.org site-terms tension (AI-scraping clause) stays flagged for the
  operator: acquisition uses the HDX bulk resource (no scraping of unhcr.org), and the
  RDF methodology page independently grants CC BY 4.0 on the same datasets.
- Third parties already redistribute these exact panels under cc-by-igo (Hugging Face
  "africa-unhcr-population-data-for-*") — external confirmation the licence is read the
  same way by others.

## Novelty check (recorded via scripts/check-novelty.py, verdict: differentiated)

Searches (2026-10-23): web ("asylum applications prediction machine learning benchmark",
BAMF anchors, HF/Zenodo site-restricted queries, arXiv "asylum seeker flow forecasting
benchmark", "migration forecasting benchmark"). Prior art, none of which is an ML-ready
corridor-grain UNHCR benchmark with fixed splits and a scored contract:

1. arXiv:2505.06249 "An Early Warning Model for Forced Displacement" — origin-country
   monthly, thresholds 2k-25k/yr, gradient boosting, 2020-2024; closest in spirit, no
   released task, origin grain not corridor.
2. arXiv:2405.06857 Bayesian projections of origin-country refugee stocks (the parked
   stock-task shape).
3. J. Econ. Geography 25(1):3 (2025) — bilateral monthly Eurostat flows to EU27,
   RF+XGB beats random walk at 3-12 months; no dataset release, EU-only.
4. JRC122178 — EU 4-week-ahead forecasting system. Cambridge Data & Policy (2024) —
   Italy aggregate, Eurostat. UNHCR "Jetson" — internal nowcasting.
5. HF/Zenodo: raw-panel repackages only (no task, no splits).

UNHCR itself now publishes a curated flow dataset (RDF explainer, "Forced displacement
flow dataset", 1962-) — the publisher ships the panel, not a prediction task; expected
and fine.

## Contracts (reconciled 2026-10-23; details in record.json `review`)

1. Redistribution: SUPPORTED (CC BY 3.0 IGO grant quoted; class A).
2. Timing: SUPPORTED with documented current-vintage assumption (annual instant,
   observed refresh cadence, target year entirely after the instant).
3. Target: SUPPORTED (label source column excludable; censoring rule measured).
4. Split capacity: SUPPORTED (measured counts + clustered counts, both classes in every
   window).
5. Not a mirror: SUPPORTED (differentiated verdict, prior art named).

Remaining limitation (recorded, not blocking): annual grain only on the machine-fetchable
path; a monthly variant would need the WAF-gated RDF app or an operator decision on
browser-captured exports.

## Probes retained (all reproduce the numbers quoted here)

```
python3 candidates/unhcr-refugee-data-finder/probe_hdx_asylum.py            # shape, mixes
python3 candidates/unhcr-refugee-data-finder/probe_hdx_asylum_labels.py     # base rates, splits
python3 candidates/unhcr-refugee-data-finder/probe_hdx_asylum_dupes.py       # duplicate structure
python3 candidates/unhcr-refugee-data-finder/probe_hdx_asylum_rule.py        # BAMF cross-check
python3 candidates/unhcr-refugee-data-finder/probe_hdx_asylum_coexist.py     # type coexistence
python3 candidates/unhcr-refugee-data-finder/probe_hdx_asylum_modelmix.py    # V vs split models
python3 candidates/unhcr-refugee-data-finder/probe_hdx_asylum_fixture.py     # known events (exit 0)
```
Each probe's `--csv` defaults to the scratch download; re-fetch with the curl command
above to reproduce.
