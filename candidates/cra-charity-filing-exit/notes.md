# cra-charity-filing-exit

## 2026-10-19 discovery session (regional focus: Canada)

All probes anonymous, run from the coordinator. Probe scripts (`.factory/probe_ca_*.py`)
were deleted after use; downloaded CSVs lived in `/opt/data/cache/scratch/ca_charities/`
and were deleted after measurement.

### Catalog and licence

- `python3 .factory/probe_ca_ckan.py` - open.canada.ca CKAN package_search: `q=charities`
  returns the per-year "List of charities" products; `python3 .factory/probe_ca_show.py`
  enumerated **every year 1990-2024** (35 packages, org `cra-arc`).
- package_show measured for 2012/2013/2014/2023/2024: `license_title='Open Government
  Licence - Canada'`, `license_url=https://open.canada.ca/en/open-government-licence-canada`.
  OGL-Canada-2.0 requires attribution (title, source, licence link) - carried verbatim per
  policy; no share-alike/NC restriction.
- Data dictionary PDF (data_en.pdf, 1,275,518 B) downloaded and read: Identification has
  NO status/revocation column - the files are pure T3010 filings; "The list only includes
  charities that have filed a T3010 ... for the period concerned." This kills the
  revocation-reason label idea and forces the presence/absence label, which is mechanical.

### Shape and exit rates (full files, not samples)

`python3 .factory/probe_ca_exit.py` downloaded five Identification CSVs and compared
full BN sets:

| year | bytes | rows | distinct BN |
|---|---|---|---|
| 2012 | 12,232,993 | 85,113 | 85,113 (BN unique in-year) |
| 2013 | 12,683,006 | 84,729 | 84,729 |
| 2014 | 12,696,669 | 84,855 | 84,855 |
| 2023 | 13,339,737 | 84,519 | 84,519 |
| 2024 | 13,203,780 | 83,761 | 83,761 |

- exit 2012->2013: 2,305 absent (2.708%), 1,921 entrants
- exit 2013->2014: 1,498 absent (1.768%), 1,624 entrants
- exit 2023->2024: 2,376 absent (2.811%), 1,618 entrants
- late-filing artifact: 109 of the 2,305 absent-from-2013 (4.73%) reappear in 2014 ->
  label wording frozen as "absent in Y+1", not "never files again".
- 2012 file decodes as cp1252 (accents garble under UTF-8); 2013+ add a `Sub Category`
  column absent in 2012 - construction must handle both headers.

### Financial schema and cost

- `python3 .factory/probe_ca_rows.py` ranged GETs: financial_d_and_schedule_6_2024 header =
  `BN,FPE,Form ID,Section Used,` + line codes 4020..5910 (Section D + Schedule 6, meanings
  in the dictionary: assets, liabilities, revenue by source, expenditures, compensation,
  political-activity spend; `Section Used` D vs 6; guide T4033 pins line semantics).
- `python3 .factory/probe_ca_charities2.py`: one 20,969,638 B financial CSV downloaded in
  4.3 s (4.83 MB/s) on the coordinator. Per-year full feature set ~80 MB (sum of measured
  per-file sizes = estimate); 2005-2023 window ~1.5 GB, worker-scale.

### Failed paths (recorded so they are not retried)

- canada.ca direct page fetches time out from this host (curl: HTTP/2 INTERNAL_ERROR, then
  a 90 s timeout with 0 bytes). CKAN/open.canada.ca works fine - use it.
- The CRA live "Charities Listings" (status + revocation reasons) is not on open.canada.ca
  (CKAN searches `revoked charity` / `charity status` return nothing relevant), so the
  revocation label is not reachable from open data; the filing-exit label is.

### Novelty (recorded by scripts/check-novelty.py, verdict differentiated)

Prior art found by web search: US IRS Form 990 nonprofit-failure literature - "Predicting
the downfall of non-profit organizations" (990-EZ ML, Polytechnic UPR), ODU dissertation
"Why Do Nonprofits Fail?" (logit on 990s), Rutgers "Predicting Discontinued Operations in
Nonprofit Institutions" (990 e-file 2011-2018, Random Forest), Wang/Lee/Dull ML
discontinuity study. Nothing on Canadian T3010, and no ML-ready task with splits anywhere.
Ours: Canadian jurisdiction + mechanical filing-exit label + temporal splits + leak-free
panel; theirs: US 990 datasets, academic results, no shared task artifact.
