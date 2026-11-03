# wb-procurement-contract-awards — discovery notes (DROPPED)

Regional tick 2026-11-03: International organisations. The World Bank is a named publisher in the tick;
the two existing WB drops (wb-ieg-project-outcome, wb-loan-disbursement-completion) covered instrument
outcomes, so the one un-probed WB row-level family was the Finances One contract-award stream.

## Probes (bounded, coordinator-side, 2026-11-03; no bulk download)

1. Platform existence and maintenance: WBG Finances One carries "Contract Awards in Investment Project
   Financing (Since FY 2020)" (DS00005, 296,836 rows, 21 columns, "Data as of Nov 03, 2026", "Daily
   updates when new records are available", API + bulk download), plus DS04691 (FY2017-2019, 63,912 rows)
   and the retired DS01004 (FY2001-2016 prior-reviewed only, 146,802 rows, frozen 2022-03-11, CSV
   49.92 MB). Sources: the dataset pages themselves.
2. Schema: the published Column Details list only at-award attributes (project, borrower country,
   procurement category/method, supplier, supplier country, contract amount, contract signing date, WB
   contract number) plus `as_of_date` (snapshot stamp). No revision/termination/completion/end-date
   column exists in any segment. The publisher states contracts "may be modified after signature" and
   the data does not reflect it.
3. Population break: FY2001-2016 = prior-reviewed contracts only ("does not list all contracts awarded
   by the Bank"); FY2020+ = all IPF awards. A cross-segment panel mixes two inclusion rules.
4. Publisher's own quality caveats (dataset descriptions): "Data is entered by Borrowers" (STEP);
   "should be viewed only as a guide"; "does not include awards to subcontractors, nor does it account
   for cofinancing"; joint-venture amounts split equally; "The Procurement Policy and Services Group
   does not guarantee the data included in this publication".
5. Licence (class A, recorded for future sessions): dataset metadata "License: Creative Commons
   Attribution 4.0 International"; platform terms (financesone.worldbank.org/terms) default WBG-owned
   data to CC BY 4.0 IGO; Data Catalog attribution format "The World Bank: Dataset name: Data source
   (if known)."

## Why dropped (decisive evidence)

- No post-award outcome column exists, so any label is future award occurrence/composition on the same
  administrative stream - a pipeline-continuation hazard.
- The WB instrument-activity family was measured twice already with the same result: country/identity
  rate tables win (wb-loan-disbursement-completion, wb-ieg-project-outcome, both dropped with
  measurements). A project-age x country x practice hazard table is exactly the reference predicted to
  win here.
- The stream is borrower-entered and publisher-disclaimed ("only a guide", "does not guarantee the
  data"), and the FY2020 boundary changes the inclusion rule, so pre-2020 history cannot backfill
  FY2020+ rows.

## What would reopen it

Row-level post-award contract events (modifications, terminations, revised amounts, completion dates)
would create a different outcome family (implementation risk / cost growth) with documented timing -
probe the STEP/Finances One schema again then. An operator request for the pipeline-continuation task
despite the family defect also reopens it. The drop covers the contract-award streams and corporate
procurement (same shape); it does not extend to other WB products.
