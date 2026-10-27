# ted-procurement-single-bid — discovery notes

Opened 2026-10-27 by the scheduled Europe (EU/EEA) discovery tick. Status:
**dropped — mirror**. Everything below is evidence for that verdict and an
access map for any future reformulation. All times UTC; notice timestamps in
Europe/Brussels (CET/CEST) as reported by the API with explicit offsets.

## Task considered

Prospective user: procurement agencies, anti-fraud units, bidders and
researchers. Prediction instant: TED publication of a contract notice (call
for competition). Target: the linked award notice reports exactly one offer
for the lot (single bid) — the EU's headline competition/corruption-risk
indicator. Utility: screening calls for competition for single-bidder risk at
publication (bid preparation is costly; buyers can widen procedures or flag
re-tender risk).

## Worked dated example (timing contract, verified 2026-10-27)

- Feature event window / eligibility: CN 10-2023 — Instituto Superior
  Técnico (PT), CPV 90910000, 5 lots, dispatched by the buyer (DT_DISPATCH)
  2022-12-28, **published on TED (PD) 2023-01-02+01:00**, OJ S 2023/S 001-000010.
  All CN features (buyer, CPV, NUTS PT170, procedure TOP_TYPE, criteria
  CRIT_CODE/weights, estimated value, deadline DT_APPLICATIONS, lot structure)
  are published at that instant by construction.
- The CN export's `FUTURE_CAN_ID` for this notice is `2023371295` → CAN
  `371295-2023`, verified via the Search API: **published (PD)
  2023-06-21+02:00**, CY=PRT, authority code matches the CN.
- Prediction instant: 2023-01-02 (CN publication, Europe/Brussels).
- Target window: award decision/dispatch and offers received, published with
  the CAN on 2023-06-21 — entirely after the instant (no part precedes it).
- Second fixture: CN 2-2023 (ES, Consejería de Presidencia, dispatched
  2022-12-28) → CAN 181795-2023, PD 2023-03-27+02:00, CY=ESP. Matches.

## Licence (class B) — publisher's own instrument

Read 2026-10-27 via the supported browser (`goto_url
https://ted.europa.eu/en/legal-notice`): plain urllib from this host gets
HTTP 429 (rate limit), so the browser was the evidence path — the 429 is
inaccessible evidence, not absent terms. Quotes in `record.json
license_evidence`:

- "© European Union, 1998-2026 ... the procurement notices published in the
  Supplement to the Official Journal of the European Union can be freely
  reused, for commercial or non-commercial purposes." (Commission Decision of
  12 December 2011 = 2011/833/EU reuse policy)
- Editorial content CC BY 4.0; attribution required; changes indicated.
- Third-party/identifiable-private-individual caveat → strip contact-person
  fields in any construction.
- Authenticity: only electronically signed OJ S notices are authentic → a
  derived dataset must be labelled derived.

## Probes and results (commands reproduce via `probe/*.py`)

1. **Catalogue (probe/probe_catalogue.py)** — data.europa.eu hub search API:
   `ted-1` (TED public procurement notices, Publications Office of the EU) and
   `ted-csv` (TED CSV subset, 48 distributions; annual CN zips 2006-2023, CAN
   zips 2007-2023; combined packages; deprecated V1/V2.2 line; last catalogue
   update 2024-01-25; **no 2024+ CSV distribution**). access_right PUBLIC;
   distribution licence fields null. ted-csv description (quote): "A subset of
   Tenders Electronic Daily (TED) data covering public procurement for the
   European Union and beyond from 2006-01-01 to 2023-12-31 ... who bought what
   from whom, for how much, and which procedure and award criteria were used";
   eForms displayed from 14 November 2022; EC GROW asks for links to reuse
   research (GROW-D2@ec.europa.eu).
   - Zip sizes via ranged GET (HEAD → 401): CAN 2023 = **111,181,340 bytes**;
     CN 2023 = **42,882,577 bytes**. One CN+CAN year pair ≈ 154 MiB.

2. **CSV schema + base rates (probe/probe_csv_prefix.py)** — ranged 256 KiB
   read of each zip prefix, partial inflate (~1.5-3 MB CSV), csv.DictReader:
   - CN 2023 header (64 cols): `ID_NOTICE_CN, TED_NOTICE_URL, YEAR, ID_TYPE,
     DT_DISPATCH, ..., FUTURE_CAN_ID, FUTURE_CAN_ID_ESTIMATED, ..., TOP_TYPE,
     B_ACCELERATED, CRIT_CODE, CRIT_PRICE_WEIGHT, DT_APPLICATIONS,
     B_RECURRENT_PROCUREMENT` — the CN export carries the **official
     pre-computed CN→CAN link** (`FUTURE_CAN_ID`, e.g. CN 10-2023 →
     2023371295 = CAN 371295-2023; CN 2-2023 → 2023181795).
   - CN 2019 prefix: 10/10 complete rows have FUTURE_CAN_ID populated,
     FUTURE_CAN_ID_ESTIMATED=0 in all (pre-eForms years work too).
   - CAN 2023 header (74 cols): includes `NUMBER_OFFERS`,
     `NUMBER_TENDERS_SME`, `NUMBER_TENDERS_OTHER_EU`, `NUMBER_TENDERS_NON_EU`,
     `NUMBER_OFFERS_ELECTR`, `INFO_ON_NON_AWARD`, `AWARD_VALUE_EURO`,
     `DT_AWARD`, buyer/CPV/NUTS/procedure/criteria fields.
   - Base-rate prefix samples (first ~256 KiB per year file = early-January
     notices, **not year-representative**):
     - 2019: 3,343 rows / 706 notices; NUMBER_OFFERS populated 64.4%;
       single-bid 704 = 32.7% of populated; multi 1,450; zero 0;
       INFO_ON_NON_AWARD 9.5%; DT_AWARD 64.8%.
     - 2021: 4,049 rows / 568 notices; populated 58.2%; single 749 = 31.8%.
     - 2023: 2,361 rows / 722 notices; populated 72.3%; single 731 = 42.8%.
   - Cross-check vs publisher's own summary products: single-bidding ~30-40%
     is the headline indicator in ECA Special Report 28/2023 and the Single
     Market Scoreboard; the sampled shares sit in that band.

3. **Search API (probe/probe_api_counts.py)** — anonymous POST
   `https://api.ted.europa.eu/v3/notices/search`; a `fields` list is REQUIRED
   (400 without it); count-only via `totalNoticeCount` (~0.1 s/query);
   full-notice GET `/v3/notices/{id}` demands an Authorization header (API
   key) despite published-notice retrieval, but search responses already
   carry converted full text.
   - Form-type vocabulary measured: `FT=3` = legacy standard-form award
     notices (**38,898** in June 2019 alone); `FT="CAN"` = eForms result
     notices (June 2015: **0**; Jan 2023: 640; 2023-01-10: 35; full 2023:
     34,699; June 2024: 28,676; June 2025: 33,463; Sept 2026: 35,853).
   - Link fixtures verified (section above).

## Why it is a mirror (novelty)

The exact task exists in reproducible form: Acikalin, Gorgun, Kutlu & Tas,
"How you describe procurement calls matters: Predicting outcome of public
procurement using call descriptions", Natural Language Engineering 30(6)
1255-1276 (2024) — **four prediction tasks on this same TED CSV subset**:
number of offers (PNumOffers), single offer (PSingleOffer), foreign-firm
award, price overrun vs estimate; 333,832 notices; 80/20 train/test; scored
multilingual transformer models; **released code**
(github.com/utkuumur/HowYouDescribeProcurementCallsMatters), which the paper
says includes the data extraction pipeline "to maintain the reproducibility
of our results".

Adjacent prior art that closes neighbouring targets on this source:

- Demiray, Ozbayoglu & Tas 2015 — bidder counts on TED (cited by the paper).
- "Intensifying Competition in Public Procurement" (Springer GIQ 2023) — TED
  2017-2020 offers modelling.
- ECA Special Report 28/2023 — single-bidding dashboard over DG GROW TED CSV +
  DigiWhist opentender, with logistic-regression prediction of country-year
  single-bidding rates.
- MDPI Algorithms 2025 — SME-winner and buyer-main-activity classification on
  TED CSV 2015-2023.
- Spanish bidder-recommender (Wiley 2020) — winner prediction (33% of Spanish
  tenders single-bid in their data).
- Public data compilations: PleIAs/TEDEUTenders (HF, parquet by year),
  EUROPROCURE-10 (HF, 2016-2025), zalizedata global-public-procurement-ted-ocds
  (HF/Kaggle, 6.3M notices; CC BY-NC so unusable for us, but it shows the
  data is already compiled ML-ready by third parties).

What we would have added — temporal splits instead of random, structured CN
features plus text, the official FUTURE_CAN_ID link, our qualification gate
and published artifact — is engineering refinement of an existing, scored
task, not genuinely novel work. Zero-offer/no-award variants are thresholds of
PNumOffers and do not clear the mirror either.

## Reuse map for any future TED formulation

- CSV subset ends at 2023; eForms era (2024+) needs the Search API (anonymous,
  slow paging) or XML bulk ("for registered users" per the ted-1 catalogue
  description — an access constraint to record if ever used).
- The CSV subset has no publication-date column (DT_DISPATCH + YEAR only);
  per-notice PD comes from the Search API.
- FT vocabulary splits legacy form families from eForms; count the award
  population from both, or from the CSV subset directly.
- `FUTURE_CAN_ID` is the official link; verify ESTIMATED-flag semantics
  (observed 0 everywhere in the 2019/2023 prefix samples) before relying on
  it wholesale.
- Corrections arrive as separate notices (CORRECTIONS flag exists); an as-of
  policy for labels needs explicit vintage evidence per docs/PREDICTION-CONTRACT.md.
