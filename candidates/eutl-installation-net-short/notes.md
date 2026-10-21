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
