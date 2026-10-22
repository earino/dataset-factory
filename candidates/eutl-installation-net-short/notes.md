# eutl-installation-net-short - discovery notes

Session: 2026-10-21 scheduled discovery tick (EU/EEA regional focus). All probes below ran
from the coordinator unless stated. Scratch files under $TMPDIR/eu-catalog/ (24h-pruned).

## How the source was found

data.europa.eu catalogue API (`.factory/eu_catalog_search.py`, `.factory/eu_probe_zen_frontex.py`):
- search "Union Registry EUTL verified emissions" -> top hit "European Union Emissions Trading
  System (EU ETS) data from the Union Registry, Sep. 2026" (id 9eee3fc9-3060-4e3f-bc8d-e22e7c3f6bda,
  publisher European Environment Agency) -> distributions pointed at
  `https://sdi.eea.europa.eu/datashare/s/aZ7Ti5HkRGEbF62/download`.
- The EEA zip's own README links the Union Registry Public Website.

## Probes and their measured results

1. **EEA aggregate product** (`.factory/eu_probe_ets_zip.py`, `.factory/eu_probe_ets_grain.py`):
   - GET datashare zip -> HTTP 200, 10,794,107 B, members incl.
     `ETS_Database_September_2026.xlsx` (3,597,611 B), user manual PDF, background note PDF,
     ISO-19115 metadata XML.
   - Metadata XML licence string: "License CC-BY 4.0 (https://creativecommons.org/licenses/by/4.0/).
     Copyright holder: European Commission, European Environment Agency (EEA)."
   - xlsx grain (sharedStrings has 103 entries; sheet1.xml 30,951,176 B): header
     `version; country_code; main_activity_code; active_installation; citl_information; year; size; value; unit`;
     rows like `82; AT; 10; all entities; 1. Total allocated allowances (EUA or EUAA); 2005; All sizes; 0; units`.
     **Aggregate-only**: country x sector x year. It cannot carry the installation-level task.

2. **Union Registry Public Website** (real browser, `union-registry-data.ec.europa.eu`):
   - Angular SPA; menu: Allocations to Stationary Installations / Aircraft, Compliance, Accounts,
     Operator Accounts, Transactions, Union Registry Holdings, Data Download.
   - Data Download page exposes **stable anonymous bulk URLs on Azure blob storage**:
     `https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic_prod/extracts/_all_extracts/
     {account/accounts_daily.csv.gz, operator/operators_daily.csv.gz,
     operators_yearly_activity/operators_yearly_activity_daily.csv.gz,
     registry_holdings/registry_holdings_daily.csv.gz}` plus per-year files
     `verified_emissions_<year>_en.xlsx` and `compliance_<year>_code_en.xlsx` (2021-2025 observed)
     and `transactions_eutl_2026.zip` at climate.ec.europa.eu document-download URLs.

3. **Bulk extract measured** (`.factory/eu_probe_eutl_panel.py` background proc, 52 s wall clock
   total; then corrected stats in `.factory/eu_measure_eutl.py`):
   - HEAD: content-length 5,959,551 B, last-modified 2026-10-20 (daily refresh; SNAPSHOT_DATE
     column inside = 2026-10-20).
   - 616,408 data rows; 23 columns; 23,708 distinct (REGISTRY_CODE, INSTALLATION_IDENTIFIER) keys;
     PERIOD_YEAR 2005-2030 (26 years, rectangular panel: future years carry advance ALLOCATION,
     VERIFIED_EMISSIONS = n/a); 32 registries (EU-27 + GB, IS, LI, NO, XI).
   - Net-short (VERIFIED_EMISSIONS > ALLOCATION, both numeric) by year - measured:

     | year | net-short/eligible | rate | year | net-short/eligible | rate |
     |---|---|---|---|---|---|
     | 2005 | 2851/10165 | 28.0% | 2013 | 6099/10808 | 56.4% |
     | 2006 | 2889/10255 | 28.2% | 2014 | 5997/10597 | 56.6% |
     | 2007 | 2861/10328 | 27.7% | 2015 | 6408/10273 | 62.4% |
     | 2008 | 3471/11098 | 31.3% | 2016 | 6691/10054 | 66.6% |
     | 2009 | 2909/11120 | 26.2% | 2017 | 6870/9894 | 69.4% |
     | 2010 | 3415/11066 | 30.9% | 2018 | 6997/9784 | 71.5% |
     | 2011 | 2817/11061 | 25.5% | 2019 | 6819/9659 | 70.6% |
     | 2012 | 3168/11510 | 27.5% | 2020 | 6267/9324 | 67.2% |
     |     |            |       | 2021 | 6239/7742 | 80.6% |
     |     |            |       | 2022 | 5819/7662 | 75.9% |
     |     |            |       | 2023 | 5253/7524 | 69.8% |
     |     |            |       | 2024 | 5577/7588 | 73.5% |
     |     |            |       | 2025 | 5453/7402 | 73.7% |

   - Sample rows: (AT, 1, 'Calmit Bad Ischl', 2005) VE 41399 / ALLOC 44894 / SURR_ALL 41399
     (compliant net-long); (AT, 1, 2007) VE 51041 > ALLOC 44894 (net-short); (AT, 1, 2030)
     ALLOC 30485, VE n/a (advance allocation usable as a year-t feature).

4. **Licence** (`.factory/eu_eutl_facts.py`): commission.europa.eu/legal-notice_en reuse clause
   quoted verbatim in record.json license_evidence (CC BY 4.0, credit + changes indicated).
   climate.ec.europa.eu/legal-notice_en 404s; the Commission-level notice applies.

5. **Cross-check against the publisher's own summary product** (`.factory/eu_crosscheck_1.py`,
   `eu_crosscheck_2.py`, `eu_crosscheck_3.py`): Germany 2023, panel vs EEA aggregate -
   - panel: 3,802 DE rows; sum VERIFIED_EMISSIONS = 296,989,213 t;
     EEA '2.1 EU-ETS Verified Emission' (act 10 + 20-99, all entities) = 296,989,209 t
     -> **difference 4 t (1.3e-6 %)**.
   - panel: sum ALLOCATION = 127,923,163; EEA '1.1 Freely allocated allowances' = 127,958,123
     -> difference 34,960 (0.027 %); the EEA's broader '1. Total allocated allowances'
     (219,474,123) is a different concept - so ALLOCATION in the extract is **free allocation**,
     exactly the quantity the net-short target should compare against.
   - citl_information labels observed in the EEA product: 1. Total allocated, 1.1 Freely
     allocated, 2. Verified emissions, 2.1 EU-ETS Verified Emission, 2.2 Swiss Verified
     Emissions (aircraft), 4.x surrendered-unit breakdowns.


## Judgements made at discovery

- The EEA product is a dead end for the *task* (aggregate-only) but is exactly the right
  **cross-check product** for construction (installation sums vs country-year totals), and it
  independently confirms the CC-BY 4.0 licence for Union Registry-derived data.
- The task's comparison (verified emissions vs free allocation) uses only in-source columns in
  the same frame - no external threshold, so no known-event fixture is required by the skill;
  the phase-drift of the base rate (28% -> 74%) is a phenomenon property to document, not a bug.
- Prediction timing is clean: at 30 April of year t, all of t-1 is settled (measured in the
  registry data: SURR_ALL for t-1 recorded; VE for t absent everywhere - reported 31 March t+1),
  and year-t ALLOCATION is published in advance (measured: allocation rows exist through 2030).
- Entities recur across windows by construction (panel); the composite row id
  (registry, installation, year) keeps the qualification gate's identity checks meaningful, and
  the recurring-entity property must be declared rather than read as split leakage.

## Construction (2026-10-22 advancement tick)

Pre-build probes (scratch scripts `.factory/eutl_probe.py`, `.factory/eutl_crosscheck*.py`,
deleted after use; extract cached in session scratch, removed afterwards):

- Today's snapshot (2026-10-22, Last-Modified 10:08 GMT): 617,448 rows, 23,748 keys,
  32 registries, years 2005-2030, gz sha256 1c7db5527c7c9b9a... (5,965,780 B).
- All three record sample-row fixtures verified in-panel: (AT,1) 2005 VE 41,399 < ALLOC
  44,894 (net-long); 2007 VE 51,041 > 44,894 (net-short); 2030 ALLOC 30,485, VE n/a.
- `SURR_ALL(t-1)` missing on 10,647 of 188,205 eligible rows -> the surrender-history
  feature is dropped rather than shipped partially defined (the gate scores a column with
  empty cells as a categorical, so a partially-defined numeric column cannot ship; and
  train.py would drop it anyway at >1000 string levels). Decision recorded in
  summary.json `dropped_feature_note`.
- `EXCLUDED(t)=YES` among in-frame rows: 81 / 204,914 (0.04%), label mix 53 long / 28
  short -> kept, mix recorded; the flag is a year-t property and cannot condition
  membership at the instant.
- Status persistence: P(short t | short t-1) = 0.8571, P(short t | long t-1) = 0.1759.
- EEA cross-check subset pinned by measurement: the EEA sheet carries BOTH per-activity
  detail rows (20, 21, 22, ...) AND aggregate rows ('10', '20-99'); summing all codes
  double-counts (184% off). With exactly {10, 20-99}, all entities, all sizes:
  DE 2022 VE = 361,145,695 = panel sum exactly; DE 2023 VE diff 4 t (1.3e-8);
  free allocation diff 55,521 (4.3e-4) / 34,960 (2.7e-4). These four cells are asserted
  in-build with tolerances 1e-5 (VE) and 1e-3 (alloc).
- Pre-launch dry run on the coordinator (full extract + full assertions + gate 1.4.0
  over the full artifact): 38/38 PASS, 11 s. The three CSVs came out byte-identical to
  the later worker build (train c7f23c55..., eval 0d9f35d5..., holdout 1c694e5e...),
  so the worker build passed first try with no descriptor defect (the abs session's
  dry-run discipline, applied).

Build (eutl-001, worker 171845011, cx23): 40.7 s job elapsed, exit 0. Fetch cost
measured on the worker: panel 5,965,780 B in 1.0 s + EEA zip 10,794,107 B in 9.3 s.
Shipped: train 141,732 rows / 64,528 positives (45.53%) 2006-2019; eval 24,322 /
18,002 (74.02%) 2020-2022; holdout 22,151 / 15,993 (72.20%) 2023-2025;
16,709 insufficient_history (all of 2005: the extract starts 2005, so t-1 does not
exist, plus each installation's first active year); 4,224 ties -> label 0;
6,449 live 2026 rows (alloc published, VE due 31 March 2027).

Gate 1.4.0 on the worker: 38/38 (artifact 3540ad2180d8df8a...), staging release
420810883 (tag job-eutl-001). Coordinator re-verification: all six assets re-downloaded,
digests matched the manifest, `qualify_dataset.py --accept` -> ACCEPTED. Worker
destroyed and confirmed deleted 2026-10-22T14:18:34Z.

Reference baselines (train-estimated tables, measured on the written rows):
persistence margin_l1 0.8671 eval / 0.8789 holdout; status rule 0.8197 / 0.8289
(accuracy 0.8587 / 0.8686); identity-only registry 0.5719 / 0.5708; calendar-only
registry x phase 0.527 / 0.5708. margin_t (ve_l1 - alloc_t) alone: 0.8988 / 0.8881 -
the announced-allocation rule beats persistence, so the level target stands; every
model number must still be quoted beside persistence.

Baseline (eutl-baseline-001, worker 171847046): runner files bundled verbatim
(hash-matched), artifact re-ACCEPTed before scoring. **Eval AUC 0.9199**
(train.py) = **0.9199** (validate.py independent recompute), CONTRACT OK.
Triad on identical eval rows: calendar-only 0.527 < identity-only 0.5719 <
persistence margin 0.8671 < full model 0.9199 (+0.0532 over persistence - the
level target stands). Per-year eval texture (written rows): 2020 rate 0.6713 /
persistence 0.9046; 2021 rate 0.8075 / 0.8269; 2022 rate 0.7582 / 0.8723. No
holdout AUC quoted (never enters a workdir). Report at staging 420818845;
worker destroyed and confirmed deleted 2026-10-22T14:24:17Z.
