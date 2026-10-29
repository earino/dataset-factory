# imf-statistical-catalogue — discovery notes

Session: scheduled discovery tick 2026-10-29, regional focus International
organisations. Probes anonymous (search + plain HTTP reads; no bulk download).

## Why this record exists

The IMF was the one publisher named in the tick's regional focus with no
candidate record. This is a bounded publisher-coverage probe, not a task
probe: licence read first, then catalogue character, then the single
row-level register measured for scale against the bench's existing family
evidence.

## Evidence (2026-10-29, UTC)

1. Licence (publisher's own instrument):
   https://www.imf.org/en/about/copyright-and-terms — "Special Terms for
   Statistical Data": "Users may download, extract, copy, create derivative
   works, publish, distribute, and use Data obtained from IMF Sites" with
   attribution + integrity conditions. Class A for statistical Data. The
   GENERAL site terms remain restrictive (personal/non-commercial, no
   redistribution of Content) — classification must always come from the
   dataset-level instrument.
2. Catalogue character: https://data.imf.org/datasets — 108 datasets;
   flagship products are country-year/quarter macro panels (IFS, BOP, DOT,
   GFS, WEO, commodity prices, exchange rates, Financial Data). This is the
   aggregate-panel family closed on measured evidence at
   oecd-sdmx-aggregate-family (class A) and itu-datahub-ict-panels (class B):
   persistence-dominated levels, shock-clustered changes, national/WDI/FRED/
   Eurostat mirrors.
3. Row-level register: IMF History of Lending Commitments
   (https://www.imf.org/external/np/fin/Tad/extarr2.aspx) — per-member tables
   with facility, Date of Arrangement, Expiration Date, Amount Agreed/Drawn/
   Outstanding, TSV download per member page. Example read (Jamaica page):
   EFF May 01, 2013 - Apr 30, 2017, agreed 615,380k SDR, drawn 445,450k.
   Scale (via the IMF-derived third-party compilation imfmonitor.org/programs,
   cited for the count only): 1,693 arrangements 1952-2025, 162 members
   (~23/year). A program-outcome task here is the third sibling of the
   WB instrument-outcome family — built and dropped twice on this bench
   (wb-ieg-project-outcome: model AUC 0.5301 vs country rate-table 0.4909,
   interval contains zero; wb-loan-disbursement-completion: 68-69% positive
   in every split, country identity carries the signal, no headroom over the
   identity prior) — at a thinner, country-clustered population, with an
   existing econometric literature on program completion/interruption.

## Decision

DROPPED (licence class A; task shape decisive). Publisher-level coverage
decision over the scanned catalogue — not a per-dataset rejection of all
108 datasets, and not a licence rejection. Reopen triggers recorded in
record.json.
