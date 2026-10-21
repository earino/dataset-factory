# bvl-zoom-sample-positivity - discovery notes

Session: 2026-10-21 scheduled discovery tick (EU/EEA regional focus).

## How the source was found

data.europa.eu catalogue search "food-borne outbreaks zoonoses" (`.factory/eu_catalog_search.py`)
surfaced "Individual data set from zoonoses monitoring (ZooM)" per reporting year (BVL publisher),
with direct opendata.bvl.bund.de CSV zip distributions.

## Probes and their measured results

1. **Catalogue records** (`.factory/eu_probe_zen_frontex.py`, `.factory/eu_probe_zoom2.py`):
   reporting years 2021, 2022, 2023 exist (dataset ids cd6d88c5 / aa0f900d / 22ceaf62);
   the 2020 dataset id 3ed1ba49 returns HTTP 404. Distributions include the CSV zips, the
   Datensatzbeschreibung PDF (BJ2020_2023), the BVL ZooM page, the AVV Zoonosen Lebensmittelkette
   regulation, Directive 2003/99/EC, the national annual ZooM report PDF, and the EFSA One Health
   Zoonoses Report (the summary products a construction cross-check can use).
   Distribution licence: `http://dcat-ap.de/def/licenses/dl-by-de/2.0` (dl-de/by-2.0).

2. **Year zips** (`.factory/eu_probe_ur_zoom.py`, `.factory/eu_probe_zoom3.py`):
   - HEAD/GET: 2021 zip 418,430 B; 2022 zip 532,407 B; 2023 zip 330,490 B; all HTTP 200.
   - URL-pattern probes for 2020/2024/2025: HTTP 404. Newest published reporting year = 2023
     (file names dated 20250108).
   - Format: one cp1252 semicolon CSV per zip, 49 columns, quoted fields with embedded
     semicolons. A naive `split(';')` parse misreads rows (first attempt mis-parsed quoted
     German text like "Mastkalber; Blinddarminhalt" and under-counted Campylobacter positives
     at 0 - the csv-module parse below is the correct one).

3. **Grain and frame** (`.factory/eu_probe_zoom3.py`, full output in
   `$TMPDIR/eu-catalog/zoom3-full.txt`):
   - (sample x parameter) rows: 2021: 22,224 / 5,373 distinct ProbenNrPseud;
     2022: 27,347 / 5,969; 2023: 22,349 / **0** - the ProbenNrPseud column is blank in the
     2023 file (data-quality defect; 2023 clustering must use matrix x month proxies).
   - 'Genus Campylobacter' rows: 1,394 (443 positive, 31.8%) in 2021; 2,364 (613, 25.9%) in
     2022; 1,312 (390, 29.7%) in 2023. Both classes in all three reporting years.
   - Species-level parameters (C. jejuni 71.7%/66.6%/78.8%, C. coli 76.0%/67.4%/78.8%) are
     follow-up confirmations on different sample subpopulations - never pooled with genus rows.
   - Other parameters measured for alternative frames: Listeria monocytogenes 7.0%/10.2%/3.9%;
     Salmonella genus 2.2%/7.4%/2.1%; E. coli ESBL/AmpC 32.3%/19.8%/26.4%; MRSA-verdaechtig
     5.3%/11.4%/15.5%; STEC 4.3%/.../9.4%.
   - Matrix-level structure (2021 examples): Campylobacter genus on chicken-family parts 41.8%
     (871 rows), breast meat 15.7% (248), E. coli in minced beef 25.4% (426), Listeria in minced
     beef 12.5% (722) - matrix dominates, but season/stage/origin/production-type variation
     leaves measurable structure beyond a single base rate.
   - PNDat carries SAS-style dates (30MAY23:00:00:00) - month features derivable.

4. **Licence** (`.factory/eu_fetch_dlde.py`): dl-de/by-2.0 text read at
   https://www.govdata.de/dl-de/by-2-0 - commercial and non-commercial use, redistribution,
   merging into new datasets permitted with the attribution notice (provider, licence mark,
   dataset URI, change notice). Quoted in record.json license_evidence.

## Judgements made at discovery

- Verdict `go`: clean prediction timing (every feature is decided at sampling; the label is the
  lab result), documented column dictionary (Datensatzbeschreibung PDF, to be read
  column-by-column at construction), dl-de/by-2.0 redistribution, stable anonymous URLs, and a
  measured three-year frame with both classes in every year.
- Carried risks (in next_action): only 3 reporting years (one per split window); 2024/2025
  files 404 (refresh lagging two reporting years at probe time); 2023 blank sample IDs; matrix
  dominance means the reference baseline is a matrix-stratified rate.
- Not a mirror of chicago-food-inspections: different label process (standardised laboratory
  detection vs inspector judgement), different entity (a physical sample vs an establishment
  inspection), different unit and time index; novelty check recorded mechanically.
