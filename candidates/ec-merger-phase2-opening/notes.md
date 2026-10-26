# ec-merger-phase2-opening - discovery notes

Tick: 2026-10-24, regional focus Europe - EU/EEA. Probes by Scout.
All probes read-only over the public bulk JSON; no bulk data retained outside
scratch (fetched copy deleted after evidence extraction; the feed is one GET).

## Source channel

data.europa.eu dataset `cc7e224e-6569-40f0-8037-d3389aa0fae7` ("EU Competition:
Merger case publications", publisher Directorate-General for Competition):
distribution download_url
`https://compcases-open-data-portal-files-prod.s3.eu-west-1.amazonaws.com/case-data-M.json`,
format JSON, updated daily. Catalogue metadata read via
`https://data.europa.eu/api/hub/search/datasets/cc7e224e-6569-40f0-8037-d3389aa0fae7`.

Fetch (2026-10-24, coordinator):

    curl -sS -o case-data-M.json \
      https://compcases-open-data-portal-files-prod.s3.eu-west-1.amazonaws.com/case-data-M.json
    # HTTP 200, 42,025,677 bytes, 0.87 s wall
    sha256sum case-data-M.json
    # 061027db232db0b57a7766eba8b43d358b20adc8c2b91ff6e1e6be4a189f0e39
    # snapshot Last-Modified 2026-10-23T00:48:26Z, ETag "f30a02f0549fbd8ec23cd8e75931f14c-9"
    # x-amz-expiration: rule DeleteOldODPLogs, expiry 2026-11-23 -> objects roll over;
    # the distribution URL is the stable channel; record fetch date + sha256 at build time.

## Probe scripts (retained in this directory)

- probe_merger_schema.py - top-level record layout (metadata/caseAttachments/decisions).
- probe_merger_agg.py / probe_merger_agg2.py - decision-type inventory and first
  (buggy, label-parsing) per-year counts; agg2 kept because its split sketch and
  lag table were the first correct baseline shape; superseded by probe_merger_label.py.
- probe_merger_label.py - the label probe: Phase II = presence of an
  'Art. 6(1)(c)' decision (opener under both Reg 4064/89 and Reg 139/2004);
  per-year counts, opener-vs-notification timing, anomaly overlap.
- probe_merger_fixtures.py - fixture records M.877 / M.4731 / M.10188 and the
  no-notification / pre-notification-decision characterisation.
- probe_merger_sectors.py - sector coverage, NACE coding eras, sector-conditional
  rates, pending-case count.
- probe_merger_anomaly.py - identifies the single opener-before-notification case
  (M.3333) and the any-intervention union.

Run pattern:

    python3 probe_merger_schema.py case-data-M.json
    python3 probe_merger_agg.py case-data-M.json
    python3 probe_merger_agg2.py case-data-M.json
    python3 probe_merger_label.py case-data-M.json
    python3 probe_merger_fixtures.py case-data-M.json
    python3 probe_merger_sectors.py case-data-M.json
    python3 probe_merger_anomaly.py case-data-M.json

## Key measured outputs (2026-10-24 snapshot, sha above)

Record layout: each case = {metadata, caseAttachments, decisions}; list-wrapped
values. metadata carries caseNumber, caseTitle, caseNotificationDate,
caseInitiationDate, caseDeadlineDate, caseLastDecisionDate, caseRegulation,
caseSectors (JSON objects {code,label}), caseSimplified, caseType,
caseInvestigationPhase, caseLinks, caseRenotificationDate, OJ publication
references. decisions[] carry decisionAdoptionDate, decisionTypes
(JSON objects {code,label}), OJ/press references.

Counts: 10,395 cases; 10,123 eligible (caseType Merger + notification date);
272 no-notification cases (decision mix: 219 Art. 4(4)-Full referral, 17
Art. 18 SO, 15 Art. 14, 6 Art. 7(3), 4 Art. 22 Refusal + singletons); 26
Additional Procedure (.AP); 2 Consultation. Notifications/year 1990: 11 ->
2018: 408 -> 2026: 317.

Label (Art. 6(1)(c) present): 309/10,123 = 3.05%; per notification year 1-22.
Phase I remedies ('Art. 6(1)(b) with conditions & obligations'): 367 = 3.63%;
union 673 = 6.65%. Decision-type inventory (occurrences): Art. 6(1)(b) 9,170,
Art. 6(1)(b) w/ cond 371, Art. 6(1)(c) 311, Art. 8(1) 46, Art. 8(2) 107+,
Art. 8(3) 33, Art. 8(4) 4, Withdrawn 263, Art. 4(4)-Full 222, Art. 4(5) 159,
Art. 9(3) 84, Art. 22 Full 38, Art. 7(3) 24, Art. 10(3) 110, purchaser
approvals 150+33, remedy-review 12+10, Art. 18 SO 79+68+17, Art. 14 17+8.

Timing: notification -> first opener lag (months): 1 mo 201, 2 mo 101, 0 mo 1,
tail 3-18. Openers dated before notification: exactly 1 - M.3333 SONY / BMG
(4064): notif 2007-01-31, opener 2004-02-12 (the original procedure's Phase II
decision carried under the re-notification after the 2006 ECJ annulment).
Post-hoc withdrawal of an adopted opener: 1 - M.10188 (2024-09-06, post-ECJ
Illumina). Pending cases (live investigation phase): 41.

Splits (Phase II label): train 1990-2013: 5,411/217; eval 2014-2018: 1,770/46;
holdout 2019-2026: 2,942/46. Post-reform alternative: 2005-2015: 3,451/101;
2016-2020: 1,876/42; 2021-2026: 2,207/30. Both classes in every window;
recent-year positives 1/4/3 (2024/25/26) are maturing procedures, not zero.

Features: caseSectors missing 79/10,123 (0.78%, concentrated 1997-2004);
sector-conditional Phase II rates: div 20 6.25% (n=256), div 61 5.23% (n=363),
div 0 4.20% (n=1,523), div 3 2.54% (n=826), div 64 0.85% (n=351), div 65
0.00% (n=230) vs base 3.05% -> sector-conditional reference is the required
baseline. caseSimplified EXCLUDED as feature (upgrade leak); current-vintage
NACE Rev 2 coding across all eras (M.877 notified 1997 coded C.30.3).

Fixtures (register vs external sources, all matched):
- M.877 BOEING / McDONNELL DOUGLAS: notif 1997-02-18, opener 1997-03-19,
  Art. 8(2) w/ cond 1997-07-30, Reg 4064/89. External: Commission decision PDF
  m877_19970730_600_fr.pdf ("Le 18 fevrier 1997, la Commission a recu ...
  notification"; "par decision du 19 mars 1997 ... engager la procedure ...
  article 6 paragraphe 1 point c"); press IP/97/729 (30 July 1997, cleared
  "UNDER CONDITIONS AND OBLIGATIONS").
- M.4731 GOOGLE / DOUBLECLICK: notif 2007-09-21, opener 2007-11-13,
  Art. 8(1) 2008-03-11. External: IP/07/1695 (in-depth investigation opened
  13 November 2007), IP/08/458 (clearance 11 March 2008).
- M.10188 ILLUMINA / GRAIL: notif 2021-06-16, Art. 22 Full referral
  2021-04-19, opener 2021-07-22, Art. 8(3) 2022-09-06, withdrawals
  2024-09-06. External: IP/22/5364 (6 September 2022 prohibition; register
  case number M.10188).

Dated example: see record.json measurements.dated_example (M.10188, Brussels
local date-only).

## Novelty check

Recorded via scripts/check-novelty.py (verdict: differentiated; 3 queries,
3 sources) on 2026-10-24. Prior art named there: EEL 2025 paper (non-public
compiled dataset; landing page shows no data release), Compass Lexecon
proprietary dataset, DG COMP ex-post study's unpublished EU Merger Database,
modernlegal/eurlex HF decision-text corpus. HF search 'merger' (2026-10-24,
30 results): no EU merger-review outcome task; nearest two recorded in
record.json. data.europa.eu hit oai-zenodo-org-15737122 resolved to Zenodo
15720643 - unrelated (noise).

## Licence

Class A. Quotes in record.json license_evidence from: DG COMP news
2025-03-18 (data released under the European Commission reuse notice,
"processed in any way ... commercial or non-commercial purposes, provided
that the source is acknowledged"); EC legal notice (CC BY 4.0 for content
owned by the EU; Commission Decision 2011/833). We ship register fields only,
not decision PDFs.

## Standing uncertainties / handoff to construction

1. Label variant: Phase II opener (recommended) vs any-intervention union
   (both measured). 2. Split partition: full-era thirds (recommended) vs
   post-reform (both measured). 3. M.3333 exclusion rule. 4. Missing sectors
   (79 cases). 5. Pending-case censoring (41 live; recent-year positives
   mature). 6. Post-hoc opener withdrawal (1 case; ever-adopted rule
   recorded). 7. Build-time fixture: verify one further pre-2008 case's
   sectors against its OJ prior notice (EUR-Lex) to strengthen the as-of
   note. 8. caseSimplified must stay out of features (upgrade leak).

## 2026-10-26 - pre-construction verification (advancement session)

Construction entrypoint authored at `source/` (build.py, score.py, run.sh,
job.json, bundle.json; job id ec-merger-001). Preflight findings, all
measured read-only on fresh coordinator fetches (probe scripts retained;
fetched copies deleted after evidence extraction; snapshot sha256
83463d0047cdf7aa0ace1a00a017fffaa5ba3eeedfd12ef104e8e02a9b81ceb1,
42,028,198 bytes - the object rolls over daily as expected):

1. **OJ prior-notice sector fixture (handoff item 7) - DONE.** M.4731
   GOOGLE/DOUBLECLICK (notified 2007-09-21, pre-2008) OJ prior notice:
   OJ C 230, 2.10.2007, p. 12 (CELEX C2007/230/08): Google "Internet search
   engine and online advertising", DoubleClick "ad serving management and
   reporting services". Register current-vintage coding: M.73.1 - Advertising
   (code NaceSectorsM_73_1) - the coding corresponds to the
   notification-documented activities. Pinned as a build fixture (exact code
   set asserted); evidence citation in build.py and quality.json.
2. **Discovery sector "division" grouping was malformed.**
   probe_merger_sectors.py derives "div" as `code.rsplit("_", 1)[-1]` - the
   LAST component of the internal code, which for 3- and 4-component codes
   is the class group or subclass digit, not the division (NaceSectorsC_20_5
   -> "5"; NaceSectorsH_51_1_0 -> "0"). The record's "div 0 n=1,523 / div 3
   n=826 / div 20 n=256" table is therefore grouped on a mixed key, and the
   recorded sector-conditional rates are not division-conditional. The build
   derives divisions from the LABEL code part (C.20.5 -> C.20; K.64 -> K.64),
   re-measures the division inventory in summary.json, and score.py's
   required comparator uses the corrected grouping. Recorded in
   quality.json limitations.
3. **M.3333 exclusion rule does not flip the label.** The register carries
   M.3333's 2004-02-12 opener AND a 2007-03-01 Art. 6(1)(c) opener for the
   re-notified procedure (notif 2007-01-31), plus Art. 8(2) decisions
   2004-07-19 and 2007-10-03. Under the rule (label decisions predating
   notification do not count) the label stays positive on the 2007-03-01
   basis; the record's split counts (train 217 positives incl. M.3333) are
   reproduced exactly. The build asserts M.3333 is positive and is the only
   pre-notification-opener case.
4. **Terminal-decision list corrected.** First maturity draft missed
   "Art. 6(1)(a)" (56 occurrences; Phase I clearance without doubts) and
   "Art. 9(3) full referral" (51; whole case referred to member states ends
   the EU procedure) - omitting them would have censored 101 concluded
   cases. Pending-censored under the final rule: 33 cases (29 with no
   decisions at all - 26 of them live 2020s filings; 3 with only Art. 9(3)
   partial referral; 1 with only Art. 4(4) partial referral). Withdrawal
   labels ("Withdrawal of Art. 6(1)(c)") are excluded from opener matching
   (the substring "Art. 6(1)(c)" appears inside them).
5. **Counts verified pre-launch** (probe_merger_buildcheck.py verdict OK):
   eligible 10,123 (= record); shipped rows 10,090 after censoring;
   positives 309; splits train 217 / eval 46 / holdout 46 positives;
   distinct positive notification dates eval 45 / holdout 44 (gate minimum
   20); fixtures M.877, M.4731, M.10188 all pass; missing sectors 79.
   Exclusions 272 no-notification (244 Merger + 2 Consultation + 26
   Additional Procedure) - matches the record.

Timing/vintage stance (gate 1.5): prediction instant is the notification
event (event_time, administrative record; features fixed at registration,
fixture-verified against the OJ notice). The register is a current snapshot
with no historical vintages (bulk feed since 2025-03-18, S3 objects expire
under a 30-day rule), so a reverse-history probe is not performable; the
evaluation contract declares retrospective_research over current_snapshot
vintage, and no point-in-time reconstruction is claimed.

## 2026-10-26 - ec-merger-001 (worker attempt 1): build OK, gate FAILED on two descriptor truths

Worker 172531049, job ec-merger-001, 10.4 s container runtime, deleted after
verified collection (assets digest-verified in staging release
tag job-ec-merger-001, draft; local result + gate report + container log
preserved under .factory/ec-merger-001/). Construction succeeded: fetch
sha256 83463d00... (42,028,198 B, Last-Modified 2026-10-26T01:00:34Z),
eligible 10,123, shipped 10,090 rows after 33 pending-censored
(train 5 / eval 0 / holdout 28), positives 309, splits train 5,406/217,
eval 1,770/46, holdout 2,914/46, distinct positive notification dates
45/44, all fixtures pass, M.3333 positive on its 2007-03-01 opener.

Gate 1.5.0 refused the artifact on exactly two checks; every other check
passed (timing, contract probes, leakage, splits, runner):

1. `contract.label_availability` - the contract lacked
   `training_label_timing: "unverified"` (the gate's required declaration
   for a retrospective_research artifact with no full-row availability
   ledger).
2. `leakage.high_cardinality_declared` - `sector_divisions` (the division
   combination string) exceeds rows/5 levels per split and was not in
   high_cardinality_columns.

Both are descriptor-truth fixes, not construction defects; no check was
weakened and the CSV bytes are unchanged. Fix applied to build.py
(declaration only), fresh attempt id ec-merger-002 per the one-rebuild rule.
The ec-merger-001 bundle and reports are preserved as the failure record.
