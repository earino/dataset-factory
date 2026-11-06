# wto-dispute-panel-escalation — discovery notes

Opened 2026-11-06, discovery-only session (International organisations region).
Status: ready — handoff to construction in record.next_action. Nothing constructed, scored or gated here.

## Why this lead

The tick's named publishers (WB, OECD, UNHCR, UNICEF, UNODC, WHO, IMF, ITU) all carry
recorded verdicts, most re-checked within the last ten days; the remaining in-region
un-probed case-grain idea was a WTO one (no WTO record existed; grep over candidates/
for WTO/dispute returned only two unrelated probe JSONs). WTO dispute settlement is a
case-level register with externally observable outcomes, clean prediction timing, and —
decisively — an explicit dataset-level open licence on the WTO's own new data portal.

## Order of work actually followed

Licence first, then contribution/prior art, then aggregates — per the skill. All probes
anonymous, coordinator-side, read-only.

## 1. Licence (class A; two instruments, both the publisher's own)

- `GET https://www.wto.org/english/info_e/copyrights_permissions_e.htm` → 200, 10,183 B
  (2026-11-06). Quoted: "This site and its contents are the copyright of the World Trade
  Organization... Unrestricted official WTO documents and legal texts are free for public
  use. Other material such as official publications can be reproduced for non-commercial
  purposes provided attribution is given to the WTO and the WTO is informed. Commercial
  use of materials from the website requires written permission from the WTO."
- `GET https://data.wto.org/api/3/action/package_show?id=disputedb` → 200 (2026-11-06).
  JSON: license_id "Attribution 4.0 International", license_title "Attribution 4.0
  International" (CC BY 4.0), author "Legal Affairs Division", dsdb@wto.org,
  metadata_created 2026-10-12 (portal is BETA). Same license_id on `ds_db` (Dispute
  Settlement Documents — the package that lists the gateway pages and the stage-count
  xlsx as resources). CKAN `isopen: false` is a registry artifact (the string is not
  CKAN's canonical `cc-by` id), not a restriction — recorded, not assumed away.
- Failed probes recorded: my first guesses for a WTO "terms and conditions" page
  (`/english/forums_e/foru_terms_conditions_e.htm`, `/english/res_e/reser_e/terms_conditions_e.htm`)
  both redirect to the site's 404 shell (10,246 B, identical) — the copyright page above is
  the operative site-wide instrument on the current site.
- Note: the tariff platform ttd.wto.org carries its own stricter terms (non-commercial,
  no mass downloads, re-dissemination needs Secretariat approval) — a different,
  platform-specific instrument for a different dataset family; it does not cover the
  dispute settlement data. Not relied on either way.

## 2. Contribution / prior art (novelty)

Searches run 2026-11-06 (queries in record.novelty_check):
- The publisher's own products: the DS register itself (case pages + DS Database search
  apps), "dispute settlement activity — some figures" stats page, stage-count xlsx,
  One-Page Case Summaries 2026 edition (a publication, not a task).
- Econometric/game-theoretic escalation literature (models, not benchmarks): Bernauer et
  al., "Dispute-Escalation in the WTO" (506 dyadic disputes 1995-2003, selection models);
  Maggi & Staiger (388 disputes 1995-2009); KU Leuven MSI_1515 statistical-backwards-
  induction escalation model (panel phase 81.14% "correctly specified" on its own fit);
  Dresvyannikova MA thesis (panel-request prediction, 159 developing-complainant cases).
- Case-level coding datasets: Horn & Mavroidis "The WTO Dispute Settlement Data Set
  1995-2015" v4.0 (507 disputes, 1,272 variables, compiled from official WTO documents;
  user guide: "This data set is only to be used for research purposes, and not for
  commercial purposes"); EUI Global Governance Programme hosts a 2020 version (1995-2020);
  World Bank Data Catalog mirrors the 2006-era 351-dispute version ("Public").
  None ships an ML-ready prediction task with splits and a scored contract, and the
  coding dataset's own terms forbid commercial use — we build from the WTO's CC BY 4.0
  channels instead of redistributing it.
- Mechanical verdict recorded via scripts/check-novelty.py (see record.json): differentiated.

## 3. Aggregate measurements (all from the publisher's own artifacts, 2026-11-06)

Both files fetched anonymously and retained in probe/out/ with sha256; reproduction
script: `python3 probe/probe_wto_stage_files.py` (or `--cached` to use retained copies).

- `numbers_of_disputes_by_stage_e.xlsx` — 50,297 B, sha256 1f2f1a42f3635c56...
  Sheet "Original Panel and AB". Consultations 1995-2024 sum = **631**, exactly the stats
  page's own text ("As of 31 December 2024... 631 requests for consultations"); through
  2025 = 641. Panels established by DSB 1995-2025 = 326. "Mutually agreed solutions,
  lapse of authority" = 156 (the publisher's own count of resolved-without-ruling events).
  Recent years (consultations, establishments): 2019 20/11, 2020 5/7, 2021 9/10,
  2022 8/1, 2023 6/5, 2024 10/4, 2025 10/4.
- `dates_of_key_stages_e.xlsx` — 117,180 B, sha256 9cb85ce6bba5dc4c...
  HTTP Last-Modified: 2025-11-03. **Vintage finding**: 543 rows, 542 distinct DS numbers,
  coverage ENDS at DS543 (newest consultations 04.04.2018) — the 2019-2025 tail exists
  only on the case pages. Columns: complainant, title, request for consultations,
  request for establishment, panel established, panel composed, panel report circulated,
  appeal notified, AB report, adoption, Art 21.5 compliance stages, arbitrations,
  MAS/other, lapse of authority (60 columns; headers read, all stage columns are
  outcome-side).
- Lags consultations→panel establishment (n=273): median 155 d, p10 96, p75 248, p90 387;
  89.0% ≤ 12 months, 94.5% ≤ 18, 97.1% ≤ 24 → the 24-month eligibility cutoff.
- Windows (label = panel establishment for the DS): 1995-2008 = 383 rows / 169 pos
  (44.1%); 2009-2014 = 100 / 67 (67.0%); 2015-2018 = 55 / 37 (67.3%). Distinct positive
  complainant-respondent pairs: 89 / 48 / 28. 247 distinct pairs overall; top pairs
  (EC,US) 30, (US,China) 21, (Canada,US) 17 — heavy clustering, pair-clustered stats
  mandatory.
- Data quirks measured (construction must handle, not hide): 5 Textiles Monitoring Body
  rows (no DS consultations date — exclude and count); 1 negative lag; 2 malformed dates;
  58 titles that don't yield a respondent by regex (respondents are explicit on case
  pages); 1 "MAS or Other" date in the whole file (settlement is mostly unnotified —
  the negative class means not-established-by-cutoff, documented).

## 4. Per-case channel (features at the instant)

`python3 probe/probe_wto_case_pages.py` → probe/out/case_pages_2026_11_06.json:
21/21 sample pages HTTP 200 across DS1→DS631 (1995→2025), mean 33,296 B, 0.06 s/page.
DS600 full page read this session confirms the per-case schema: complainant, respondent(s)
(EU+France+Lithuania), agreements cited with articles at the filing instant, measure
description, and every dated stage (consultations 15 Jan 2021 → panel requested 15 Apr
2021 → DSB established 28 May 2021 → composed → report). Probe extraction is a LOWER
bound (complainant regex 16/21, agreements 12/21 — phrase variants; the probe's
"unstable" threshold line is my regex, not the channel). DS620 (2023) and DS631 (2024)
show no establishment — censoring behaves as expected. Full enumeration ≈ 641 requests
≈ 21 MB — worker-side, minutes.

## 5. Dated example (one worked case, all times Geneva local; WTO dates are Geneva circulation dates)

- Prediction instant: 2021-01-15, the circulation date of Malaysia's DS600 request for
  consultations with the EU, France and Lithuania (palm-oil biofuels).
- Feature event window (≤ instant): complainant Malaysia; respondents EU/FR/LT;
  agreements cited in the request itself — TBT Arts 2.1/2.2/2.4/2.5/2.8/2.9/5.1.1/5.1.2/
  5.2/5.6/5.8/12.1/12.3, GATT 1994 Arts I:1, III:4, X:3(a), XI:1, SCM Arts 3, 3.1(b),
  3.2, 5, 5(c); measure family (renewable-energy target, ILUC criteria); trailing
  strictly-prior Malaysia-EU dispute history; calendar.
- Label window: DSB panel establishment for DS600 within 24 months of the instant
  (i.e. by 2023-01-15 under the eligibility rule).
- Observed outcome: panel established 2021-05-28 (4.5 months after the instant) → TRUE.
- Censoring contrast: DS620, consultations 2023-09-18 → 26 months before the 2026-11-06
  cutoff, no establishment → eligible negative (declared ~3% residual risk); DS631,
  consultations 2024-11-25 → inside the 24-month tail → excluded and counted.

## Open items for construction (recorded in record.next_action)

- Case-page enumeration incl. the modern tail; reconcile against the 631/326 stage-file
  cross-check; pin digests + vintage timestamp.
- The DS Database search apps (dsdb/*.aspx) are listed with internal URLs
  (`http://dsdb/...`) in the CKAN resources — not probed; case pages + aggregate files
  already carry what construction needs.
- The afdb/wb-loan identity-prior family defect is the standing risk: the pre-registered
  triad must include the trailing pair/pair-year escalation rate and era priors, with
  pair-clustered bootstrap; reference dominance → drop per the standing rule.
