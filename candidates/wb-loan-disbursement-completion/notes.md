# wb-loan-disbursement-completion

Discovery notes — dated evidence, decisions, failed approaches.

## 2026-10-28 — session tick: International organisations region (World Bank priority)

### Lead selection

Region tick priorities: World Bank, OECD, UN agencies, WHO, IMF, ITU. Prior international-organisation
records: itu-datahub-ict-panels (dropped, mirror+shape), oecd-sdmx-aggregate-family (dropped, shape;
reopen hook = a row-level product), unodc-data-portal (dropped, class D licence), wb-ieg-project-outcome
(dropped, measured no headroom on IEG outcome ratings), unicef-sdmx-refugee-origin-growth (parked, thin
clustered positives), unhcr-refugee-data-finder (packaged), who-flunet-activity-exceedance (published).

The only WB row-level products with a post-instant outcome are the Statement of Loans/Credits tables
(Finances One): per-instrument lifecycle with board approval, effective/closing dates and final
disbursement amounts. Task chosen: at Board approval, will the instrument disburse >= threshold of its
commitment? This is a different target on a different table from the dropped wb-ieg candidate (IEG
evaluation ratings); the brief forbids generalising that one failed endpoint to the publisher's whole
collection, and the target here is a cash-flow outcome, not an evaluation judgment.

### Licence (checked FIRST, before any data probe)

- DS00047 page (https://financesone.worldbank.org/d/DS00047, read 2026-10-28 via web_extract):
  "Licensing and Attribution — License: Creative Commons Attribution 4.0 International" + CC legalcode link.
- Metadata API (2026-10-28, curl): `"license": "Creative Commons Attribution 4.0 International"` for
  DS00047, DS00975, DS00001. Class A.

### Schema read (documented, all 35 columns)

From the DS00047 page + metadata API `column_details`. Key documented meanings used verbatim in the record:
- board_approval_date: "The date the World Bank approves the loan." → prediction instant.
- original_principal_amount: "The original US dollar amount of the loan that is committed and approved."
- disbursed_amount: "The amount that has been disbursed from a loan commitment..." → label numerator.
- cancelled_amount: "The portion of the undisbursed balance which has been cancelled... Cancellations include
  terminations (where approved loan agreements were never signed)." → distinguishes genuine zero-outcome rows.
- closed_date_most_recent: "The date specified in the legal agreement (or extension) after which the Bank may,
  by notice to the borrower, terminate the right to make withdrawals" → CURRENT closing date; future-dated for
  open loans (discovered in revision 2 of the probe — first draft wrongly counted future-closing-date rows as matured).
- region: "Country/Economy lending is grouped into regions based on the current World Bank administrative
  (rather than geographic) region" → current-vintage coding, disclosed in the record as a timing caveat.
- interest_rate: "Current Interest rate or service charge applied to loan" → post-hoc, excluded from features.

### Probes (all commands runnable from the candidate directory)

Probe script: `probe_statement_of_loans.py` (revision 2), output: `probe_output.json`.
Coordinator, 2026-10-28, data-as-of 2026-09-30 snapshot.

1. Full IBRD snapshot via the documented API:
   `https://datacatalogapi.worldbank.org/dexapps/fone/api/apiservice?datasetId=DS00047&resourceId=RS00049&top=1000&skip={0..9000}&type=json`
   → 10 requests, 12,797,416 bytes, 5.5 s wall; 9,538 rows = page's "Rows: 9,538" = API count. Cross-check vs
   the publisher's own summary products passes at the row-count level.
   NOTE: default Python urllib UA → HTTP 403; a descriptive User-Agent header works (recorded in the script).
2. Full IDA snapshot (DS00001/RS00001, same paging): 12 requests, 15,082,010 bytes, 9.1 s; 11,486 rows.
   IDA column names differ (credit_number, credit_status, original_principal_amount_us_, disbursed_amount_us_, ...).
3. Historical/vintage archive (DS00975/RS00905): metadata count 1,585,498 rows. Filter probe:
   `...&end_of_period=30-APR-2011` / `30-Apr-2011` / `30-Jun-2015` — server count UNCHANGED (1,585,498) and
   returned rows unsorted by end_of_period in every format → the apiservice GET silently ignores date filters;
   per-month slicing unconfirmed; bulk >300 MB is worker scope. Recorded as an access detail, not a blocker
   (v1 uses only the latest snapshot).
4. Label/base-rate measurement (IBRD, disbursement-closed instruments, original > 0, n=8,474):
   >=50%: 87.51% | >=70%: 81.10% | >=80%: 76.12% | >=90%: 68.72% | >=99%: 51.52% | ratio 0: 312 (3.7%).
5. Split windows (>=90% label): train <=1999: 6,180 rows 4,086 pos/1,855 neg (1,611 country-year pos clusters);
   eval 2000-2009: 1,166 rows 774/369 (319); holdout 2010-2017: 934 rows 614/303 (271). Both classes everywhere.
6. Censoring (per-year closed/open in probe_output.json): approvals 2010-2017 essentially fully closed
   (0-6 open/year) → labeled population censored at 2017 approvals; 2018+ increasingly open (2025: 142 open).
7. IDA extension check: disbursed+undisbursed+cancelled != original on 7,575/9,298 closed IDA rows →
   IDA label semantics unverified; excluded from v1, kept as a measured extension prerequisite.
   IBRD: 763/8,474 mismatches, concentrated in sold_3rd_party/Fully Transferred instruments — not
   label-affecting (label = disbursed/original directly).
8. Worked dated example read back from the fetched data: IBRD00010 (France, RECONSTRUCTION, P037383):
   approval 09-May-1947 (instant), effective 09-Jun-1947, closed 31-Dec-1947, disbursed 250,000,000 /
   original 250,000,000 → positive at both thresholds; status Fully Repaid, last repayment 01-May-1977.

### Novelty

Mechanical search via scripts/check-novelty.py (4 queries against HF/Zenodo/arXiv, 2026-10-28T10:23:54Z):
direct queries return 0 relevant hits ("World Bank loan disbursement prediction" — HF 0 hits; arXiv only
generic loan-default papers). Web search: the prior art is (a) Geli/Kraay/Nobakht 2014 PRWP 7001 — predicts
IEG outcome ratings (different target, different table; our own wb-ieg candidate already measured that task
as no-headroom), (b) lukesjordan/worldbank-project-documents (HF) — documents keyed by project ID, no splits,
no scored contract, (c) disbursement-delay literature (Legovini et al. 2015) — descriptive econometrics, not a
dataset. Verdict: differentiated. Task-level comparison recorded in record.json novelty_check.

### Decision

READY (status ready, verdict go). All five contracts reconciled with evidence; check-candidate.py OK.
Known open risk (stated honestly in the record): headroom is unmeasured until construction, and this source
family has one prior no-headroom failure (wb-ieg) on a DIFFERENT target. The deciding check at construction is
the qualification gate + baseline triad; a trivial-baseline match means constructed-no-headroom, not publication.

No bulk data passed through the coordinator beyond the two full snapshots (12.8 MB + 15.1 MB, 22 requests
total); the >300 MB historical archive was only metadata/sampled.
