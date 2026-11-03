# cra-charity-filing-exit

## 2026-11-03 discovery session (regional focus: Canada) - reconciliation to ready

Recorded the stale status (`investigating` since 2026-10-19 with a `go` verdict) as
`ready` after reconciling all five contracts; probe retained at
`probe/probe_2026_11_03.py`, output at `probe/out/probe_2026_11_03.json`. Bulk
CSVs in `/opt/data/cache/scratch/ca_charities_2026_11_03/` left to the 24h sweep.

### Reproduction (command: `python3 candidates/cra-charity-filing-exit/probe/probe_2026_11_03.py`)

- 3 GETs, 47,241,798 bytes total, ~14 s: ident_2023 (13,339,737 B,
  sha256 416c98d1...), ident_2024 (13,203,780 B, 4f214ff2...), financial 2023
  (20,665,081 B, 65c6321c...).
- 2023 list 84,519 BNs; 2024 list 83,761; exits 2,376 (2.811%); entrants 1,618 -
  IDENTICAL to the 2026-10-19 measurement. Source unchanged.

### Dated worked example (America/Toronto)

- POSITIVE: BN 101835338RR0001 FONDATION D'ANESTHESIOLOGIE ET REANIMATION DU
  QUEBEC (Montreal QC). FPE 2023-12-31 (financial 2023 file, single return).
  Feature event window: returns with FPE <= 2023-12-31. Eligibility: present in
  the 2023 list. Prediction instant T = 2024-06-30 (six months after FPE - the
  documented T3010 deadline). Target: any return with FPE in 2024 (filing
  deadlines all strictly after T; latest 2025-06-30). Label revealed with the
  2024 list product (package created 2026-03-06). Measured: absent from
  ident_2024 -> label 1.
- NEGATIVES (label 0): BN 100072586RR0001 AGA KHAN FOUNDATION CANADA (Ottawa
  ON), BN 100072933RR0001 AGASSIZ CHILD CARE CENTRE INC (Winnipeg MB); both
  FPE 2023-12-31, present in both lists.

### Publication-timing evidence (as-of)

- CKAN package enumeration (all 35 year packages): year-2023 package created
  2025-07-29, year-2024 created 2026-03-06 - both single-year creations that
  look like genuine first publication. But 1990-2008 were ALL created 2026-02-20,
  2009-2012 on 2021-11-29, 2013-2022 on 2024-12-17 - bulk re-publication, so
  portal metadata dates do NOT evidence first publication for older years.
- Consequence, recorded in record.prediction_time: at the deadline instant the
  year-Y returns are filer-known, not yet third-party published. Two honest
  framings stated; the choice is advancement's first step (cqc precedent).
- Files carry `_updated` suffixes; packages modified after creation (2024
  package modified 2026-10-04). Labels are current-vintage finalized; no
  historical-vintage claim.

### New shape measurements

- 2023 financial file: 84,342 rows, 84,171 BNs with FPE, 171 multi-return BNs
  (year-end switchers; handled by the any-FPE-in-year label).
- FPE month mix of the 2023 filing population: Dec 49,011 (58.2%), Mar 14,718,
  Jun 6,531, Aug 4,698, and every other month present. The instant is
  per-charity (six months after its own FPE).
- 2,342 of the 2,376 exiting BNs have a 2023 financial record.

### Encoding correction (supersedes the 2026-10-19 note)

- The 2023/2024 Identification and 2023 financial files decode cleanly as UTF-8
  (byte 0x8f is invalid cp1252 - a cp1252 read raises). The 2012 file measured
  cp1252 on 2026-10-19. Encoding is PER-YEAR: construction must detect it
  (UTF-8 first, cp1252 fallback). The record's earlier blanket "decode as
  cp1252" instruction is corrected in next_action.

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
