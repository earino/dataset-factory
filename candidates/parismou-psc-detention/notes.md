# parismou-psc-detention - discovery notes

Tick: 2026-10-24, regional focus Europe - EU/EEA. Closed at licence/access
triage; no bulk data requested or downloaded.

## Evidence trail

1. Web search (2026-10-24): Paris MoU announcement "Increased availability to
   Paris MoU Data" - bulk inspection data sharing exists; access requires an
   account via a "Paris MoU Data Request Application Form". The 2021/2023
   announcement URLs now 404, both to the web extractor and in a real
   browser (verified).
2. parismou.org serves a Dutch 404 page ("Deze pagina bestaat niet") to the
   plain web extractor; the live site loads in the supported browser.
3. Live page read in the supported browser (2026-10-24):
   https://parismou.org/datasharing-public/ - "The Paris Memorandum of
   Understanding on Port State Control (Paris MoU) is now sharing its
   inspection data with the public in bulk form... Once you've received an
   account for the page, you'll have full access to the inspection results."
   "Any interested party can request an account by completing the Paris MoU
   Data Request Application Form below, to gain access to the data on offer."
   The form collects first/last name, email, organisation type (branch
   organisation, charterer, flag state, news organisation, student...),
   address, and API interest. The page's only terms and conditions are:
   (1) no liability for errors; (2) no support on interpretation/download;
   (3) "The Paris MoU can retract accounts at her own discretion if the use
   of an account is evaluated as impairing the data sharing system as such."
   NO redistribution/redistribution-permission terms are stated anywhere.
4. Public anonymous channel: monthly detention lists. Independent
   compilation (Webb-Institute/psc-inspection-dataset, GitHub, read
   2026-10-24): 115 monthly Paris MoU detention-list PDFs 2015-2024 parse to
   5,079 detention rows; "Detention-only: no clean inspections, so no
   negative class"; the project also states "Paris MOU and Tokyo MOU records
   are not redistributed - their source terms restrict reproduction, or
   leave it unclear."

## Decision

Class C (unstated redistribution terms) on a gated channel (account
application with personal/organisation details; discretionary retraction).
Standing policy: we only build on sources that are already clean; no
unsolicited permission request was sent. DROPPED.

Reopen conditions (record.json rejection_reason): publisher states open
redistribution terms, or publishes outcomes with clean inspections
anonymously, or the operator records a candidate-specific decision to apply.
Note for a future non-EU tick: USCG PSIX (CC0) is the open source for the
same task family - start there, not here.
