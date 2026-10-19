# companies-house-company-exit

**Verdict: PARK (2026-10-19).** Status `parked`. The blocker is measured, not
guessed: the bulk product is the live register only, so exit labels cannot be
observed from anything published today. Do not re-probe the download page; the
shape is recorded here.

## The task (when it can be built)

For a company on the live register at snapshot month M, will it exit (dissolve)
within 12 months? Features = the register row at M; label = later snapshot.

## Probes (2026-10-19, anonymous, from the coordinator; ranged reads only)

### Download page and files

| Command | Result |
|---|---|
| `GET https://download.companieshouse.gov.uk/en_output.html` | HTTP 200, 7,442 bytes; lists `BasicCompanyDataAsOneFile-2026-10-01.zip` + 7 parts (part1_7..part7_7); page text: "snapshot containing basic company data of live companies on the register", "provided free of charge and will not be supported", updated "within 5 working days of the previous month end"; **no licence text on the page** (grep for licence/OGL: zero lines) |
| `GET https://www.gov.uk/guidance/companies-house-data-products` | HTTP 200; footer asserts "Open Government Licence v3.0"; describes fields: company type, registered office, SIC, "company status, such as 'live' or 'dissolved'", accounts/confirmation statement dates, previous names |
| CKAN package_show 7833cd0c-b322-4d23-baca-31eda0d66577 (data.gov.uk CH dataset) | license "License not specified"; org oddly recorded as london-borough-of-barnet |

### One-file snapshot shape (ranged zip reads, ~5 requests, ~7 MB)

| Measurement | Result |
|---|---|
| `BasicCompanyDataAsOneFile-2026-10-01.zip` | 493,990,184 bytes (Last-Modified Wed 07 Oct 2026 08:10:36 GMT); one CSV member `BasicCompanyDataAsOneFile-2026-10-01.csv`, **2,810,066,457 bytes uncompressed**, 55 columns |

Header (first 28 of 55 cols): CompanyName, CompanyNumber, RegAddress.CareOf,
RegAddress.POBox, RegAddress.AddressLine1/2, RegAddress.PostTown/County/Country/
PostCode, CompanyCategory, CompanyStatus, CountryOfOrigin, DissolutionDate,
IncorporationDate, Accounts.*, Returns.*, Mortgages.*, SICCode.SicText_1..4,
LimitedPartnerships.*, URI, PreviousName_1..10.* ...

### Live-only evidence (first 4 MB prefix, 8,109 rows, proper CSV parse)

- CompanyStatus: **Active 7,099 / Liquidation 575 / "Active - Proposal to Strike
  off" 403 / In Administration 17** + a handful of other live-ish statuses
- **DissolutionDate set: 0 of 8,109 rows**
- First row: company 08209948 "! LTD", Private Limited Company, Active,
  incorporated 11/09/2012, SIC 99999 - Dormant Company, accounts category DORMANT
- Incorporation years in the prefix run back to 1869; file is name-sorted
  (company numbers in prefix: 08209948 down to 01796899)
- Row-count cross-check: the 2023-11 snapshot mirrored on Kaggle
  (kaggle.com/datasets/christianhauzar/companies-house-data-11-2023, read
  2026-10-19) has ~5.45M unique company numbers - the live register, not the
  ~10M+ companies ever incorporated

Conclusion: the bulk product carries the **live register only**. Dissolution
labels require future snapshots (monthly collection), the rate-limited API, or
non-open third-party deltas. Full reasoning in record.json `rejection_reason`.

## Licence state

No licence statement on the download page (measured). OGL v3.0 asserted on the
gov.uk guidance page footer and CH's data.gov.uk presence, but the register
data's own grant must be confirmed with Companies House terms before any
construction or release. Recorded as part of the unparking decision.

## Prior art (checked 2026-10-19)

- Kaggle mirror: one raw snapshot, license "Unknown", no task attached.
- ONS business demography: aggregate survival rates (a cross-check product).
- ExitRadar (2026 blog write-up): proprietary ML on 1.9M dissolutions x its own
  scored database - commercial, not open, not a published dataset.
- Productivity Insight WP61 (2025, "Tracking the Economy through Firm
  Creation"): research census from register snapshots + API dissolution dates -
  economics, not a prediction task.
- No ML-ready company-exit task with splits found on Kaggle/HF/Zenodo/arXiv.

## Next action

Parked. Unpark = operator decision: approve a scheduled monthly snapshot pull
(~470 MB/month, staging-side, 12-month horizon) and settle the licence question
with Companies House terms. See record.json `next_action`.
