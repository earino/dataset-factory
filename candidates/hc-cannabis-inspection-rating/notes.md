# hc-cannabis-inspection-rating

Record dated evidence, decisions, and failed approaches here.

## Row-level probes (2026-10-22)

All probes anonymous, run from the hosted coordinator; downloads under /opt/data/cache/scratch
and parsed with small scripts (since deleted).

### 1. Licence and package triage

    curl -s -o ckan_cannabis.json -w "cannabis %{http_code} %{size_download}\n" \
      "https://open.canada.ca/data/en/api/3/action/package_search?q=Cannabis+Inspection+Data&rows=5"
    -> cannabis 200 65557

Parsed: package e04d55cd-74dd-4167-a9ea-c6eb9e9ab287, org "Health Canada | Santé Canada",
license_title "Open Government Licence - Canada" -> licence_class A (attribution conditions to
carry into LICENSE.md). Package notes: "summary of cannabis inspections and compliance
verification activities ... licence holder name, province, inspection start dates, inspection
types, compliance ratings, observations, and measures initiated". Resources: four English
half-year CSVs + DOCX glossary; oldest CSV resource created 2025-01-22 (published history is
~2.5 years deep, semi-annual cadence).

### 2. Bulk reads (all four English vintages)

Each URL 302-redirects to the CDN; with -L:
    c1 (Apr 2025 - Sep 2025): 200, 45250 bytes
    c2 (Oct 2024 - Mar 2025): 200, 51318 bytes
    c3 (Apr 2024 - Sep 2024): 200, 30716 bytes
    c4 (Oct 2025 - Mar 2026): 200, 39134 bytes

Headers (verbatim first lines):
    c1: "Licence holder name,Province or territory,Inspection start date,Inspection type,
         Sampling Conducted,Observations,Inspection rating,Measures initiated by Health Canada"
    c4: BOM + "Licence Holder Name,Province or Territory,Inspection Start Date,Inspection Type,..."
c1 is not valid UTF-8 (Latin-1 fallback needed); c2-c4 are UTF-8 with BOM and capitalized
headers - per-file normalization required in any construction (cost note, not the rejection).

### 3. Measured composition

- 1,358 data rows across the four vintages (blank lines removed; a first pass counting raw
  lines reported 1,488 - corrected).
- Inspection rating: Compliant 1,291 (95.1%); Non-compliant 66 (4.9%); "Rating not assigned" 1.
- Inspection type: Regular 916, Targeted 209, CV 128, Compliance Verification 88,
  Compliance Monitoring Projects 17.
- Inspection start years: 2023: 6, 2024: 498, 2025: 728, 2026: 126 (through September).
- Licence-holder grain: 821 distinct holders; 278 holders have >=2 inspections (815 rows);
  max 15 inspections for a single holder.
- Provinces (leading): ON 502, BC 355, QC 201, AB 113, NS 48, SK 43, NB 35.

### 4. Capacity arithmetic and family comparison

- Next-inspection-outcome panel: bounded by the 278 repeat holders (815 rows; ~537 transitions
  after first inspections) and by 66 total positives. Four half-year vintages cannot yield three
  disjoint train/eval/holdout windows with both classes. Verdict on capacity alone: reject.
- Family: establishment -> next-inspection-rating is the task already live on the bench as
  candidates/fsa-fhrs-next-rating (GO to construction) and in the chicago-food-inspections
  family; a Canadian re-issue changes jurisdiction, not the task (same test that rejected
  hc-recalls-classification and jma-typhoon-rapid-intensification). Verdict on family alone:
  reject.

### 5. Sibling noted in the same pass (not separately opened)

"Vaping Compliance and Enforcement Data Summary (retail inspections)" package
c7c556dc-a4c2-4259-9f74-a1cde5e42c4b (OGL-Canada): same inspection-outcome shape, annual cadence,
single 2024-25 vintage online. Closed by the same family and capacity reasoning; recorded here
so a future tick does not open it as a fresh candidate.

### Cleanup

can_c1..c4.csv and ckan_cannabis.json remain under /opt/data/cache/scratch (auto-pruned).
Measurement scripts (.factory/parse_cannabis.py, cannabis_measure.py, cannabis_measure2.py)
deleted after use. No bulk data entered the repository.
