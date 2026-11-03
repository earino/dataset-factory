# oecd-ncp-specific-instance-acceptance — discovery notes

Regional tick 2026-11-03: International organisations (World Bank, OECD, UN agencies, WHO, IMF, ITU).

## Why this lead is new, not a reopened rejection

The `oecd-sdmx-aggregate-family` drop recorded this reopen condition (record.json, rejection_reason +
next_action update 2026-10-28): "Re-open only if the OECD ships a row-level product that is neither an
aggregate panel nor a mirror of national datasets (e.g. an event- or case-level release)". The Database
of specific instances IS that product:

- case-level (one record per filed grievance, with a per-case structured Overview),
- OECD-originated: the cross-NCP registry exists only at the OECD (individual NCPs publish their own
  final statements, but the registry is OECD's), so it is not a mirror of a national dataset,
- outside the 1,521-dataset Data Explorer scan that the 2026-10-28 re-check covered (the NCP database is
  a web-CMS product, not an SDMX dataflow), so it was never probed.

Other publishers in this tick were checked against existing records before any probing:
IMF closed at publisher level (event-grain reopen condition unmet; the lending-arrangements register
carries the twice-measured WB instrument-outcome defect); ITU closed (aggregate panels + WB mirror);
UNODC closed (class D terms); UNHCR occupied (packaged/parked active work); UNICEF parked on measured
split capacity (34 clustered eval positives); WHO FluNet published. No new probing was spent on any of
them.

Bench comparators (recorded in the novelty check): eu-ombudsman-inquiry-outcome (investigating) is the
same genre — complaint-mechanism outcomes — but a different institution, population (EU administrative
acts vs multinational enterprises under the OECD Guidelines) and target (settlement taxonomy after an
opened inquiry vs the intake acceptance gate at initial assessment). pins-planning-appeal-outcome and
ipo-trademark-registration-outcome are adjudication tasks in national (UK) institutions.

## 2026-11-03 probes (all commands run from the coordinator, anonymous, bounded)

### P1 — enumeration channel and total count

Command (retained as `probe_ncp_rss.py`):

    curl -sS "https://api.oecd.org/webcms/search/rss?siteName=oecd&interfaceLanguage=en&hiddenFacets=siteName%3Amne-guidelines&page=0&size=15"

Output facts (measured 2026-11-03):
- page=0..45 return 15 items each; page=46 returns 10; page=47 returns 0 → **total 700 items**,
  matching the listing page's "700 results" and the publisher's "over 700 cases" statement.
- `size` is capped at 15 (`size=100` returns 15). ~14 KB per RSS page → 47 requests (~660 KB) enumerate
  the full registry (title, case URL, DB listing date, truncated summary).
- No JSON variant exists (`https://api.oecd.org/webcms/search?...` → HTTP 404
  `{"statusCode":404,"message":"Resource not found"}`).

### P2 — case-page field structure and the JS-rendering requirement

The database and case pages are client-side rendered on the new OECD CMS (June 2025 migration):

    curl -sSL "https://www.oecd.org/en/networks/national-contact-points-for-responsible-business-conduct/database/2026/kr0029.html"
    # -> 5,759 bytes, no content (same with a Googlebot user-agent: 5,908 bytes, no content)

A JS-rendering extraction of the same page returns the full record. Sampled (2 pages, spanning eras):

- kr0029 "Hoang Gia Trading and Services & Lotte Corporation, Lotte Shopping" (Korea NCP):
  Lead NCP Korea; Supporting NCP N/A; **Date 27 February 2026** (= submission date, per the summary
  "On 27 February 2026, Hoang Gia Trading & Services ... submitted a specific instance"); Country of
  the issue Viet Nam; Source Business; Sector Wholesale and retail trade; Topics General policies,
  Disclosure, Human rights, Employment and industrial relations, Consumer interests; Subtopics Due
  diligence, Corporate governance; **Status Not accepted**; Outcomes Recommendations; Entity involved
  Local subsidiary. Summary (retrospective, NCP-authored): submitted 2026-02-27, **initial assessment
  published 2026-05-21** ("deciding not to accept the specific instance for further examination"), with
  links to the NCP's own published statement PDFs.
- pl0001 "Trade union & MNE active in accommodation and food service" (US→Poland transfer):
  Date 4 May 2006; Status Concluded; full structured fields present for the pre-2011 era too.

Gap (recorded): no structured initial-assessment decision-date field on the sampled pages; decision
timing lives in the summary prose and the linked NCP statements. The label (Status) does not need it —
eligibility is terminal-status-at-vintage.

**Access cost**: enumeration 47 requests (measured); case extraction ~700 JS-rendered page fetches,
est. 15–30 MB, est. <1 hour on a small worker VM (the rendering step is an estimate; the shell size,
item counts and page size are measured). Plain-curl bulk scraping does NOT work — a JS-rendering client
is required (measured with two user-agents).

### P3 — licence (class A) and the restricted-annex caveat

Publisher's own instrument — OECD Terms and Conditions, https://www.oecd.org/en/about/terms-conditions.html
(fetched 2026-11-03; full quotes in record.license_evidence):

- "Following implementation of the OECD Open Access Policy, most OECD written content published as of
  1 July 2024 is licensed under a Creative Commons Attribution BY 4.0 licence (CC BY 4.0)."
- "Except where additional restrictions apply as stated above, you can extract from, download, copy,
  adapt, print, distribute, share and embed Data for any purpose, even for commercial use."
- The T&C govern "oecd.org and related websites"; the NCP database is served on oecd.org.

No additional restrictive notice exists on the database or case pages (checked 2026-11-03). The 2025
Annual Report footer states "©OECD 2026, CC BY 4.0". The Annual Report **data annexes** are
cover-marked "Restricted Use - À usage restreint" — excluded from any redistributed artifact; used only
as publicly-downloadable cross-checks in these notes.

### P4 — publisher's own summary cross-check (aggregate evidence)

2025 Annual Report on NCP Activity (CC BY 4.0), fetched 2026-11-03 (full text cached at
/opt/data/cache/web/www.oecd.org-ed9536dc93.md during the session):

Filings per year (publisher table): 2011:31, 2012:27, 2013:39, 2014:39, 2015:24, 2016:31, 2017:26,
2018:49, 2019:36, 2020:57, 2021:47, 2022:41, 2023:55, 2024:56, 2025:119.
(Internal inconsistencies in the publisher's own numbers: report text says "120 case submissions" and
"58 cases in 2020" where the table says 119 and 57; the 2021 report says 48 received in 2021 where this
table says 47. Volume evidence only — exact counts come from the DB at construction.)

Closed-cohort acceptance (publisher's own figures):
- 2021 (Annual Report 2021, © OECD 2022): 43 closed, 27 concluded, 16 not accepted (37%).
- 2024 (2025 report): 58% accepted of 52 closed.
- 2025 (2025 report): 56 closed, 26 not accepted (46%), 30 concluded after acceptance (54%);
  by submitter class: individuals 11/28 (39%), NGOs 12/14 (86%), trade unions 5/8 (63%).
- 2025 cohort censoring (publisher's data annex, restricted-marked, cross-check only): at end-2025, of
  the 120 received in 2025, 99 in progress, 19 not accepted, 2 concluded → 2025–2026 filings are
  excluded from scored windows; construction re-measures this exactly from the DB.
- Concentration: top-5 NCPs received 52% of 2025 submissions; 2023–25 shares US 16%, UK 10%, DE 9%,
  FR 8%; 2025 submissions 71% by individuals (surge cohort effect).

### P5 — timing semantics and the listing-date trap

- The case-record "Date" field is the submission date (verified against the summary prose on both
  sampled pages).
- The DB **listing date is neither the filing date nor the decision date**: kr0029 listed 2026-02-27
  (= filing date, lag 0); ca0029 (United Tegaru Canada & East Africa Metals) filed 2022-09-10, listed
  **2026-05-12** (lag ~32 months). The publisher's FAQ: "all ongoing cases might not be reflected in
  the database, as NCPs have discretion as to the moment they report a case for inclusion in the
  database." → current-vintage retrospective posture; DB listing dates are never used as timing fields.

### P6 — prior art (novelty)

Web + catalog searches 2026-11-03 (queries recorded in the novelty check) found:
- No ML-ready dataset, benchmark or scored prediction task on NCP specific instances (HF/zenodo/arxiv
  searches + web search: only OECD procedural guides, annual reports and the database itself).
- Nearest prior art: Springer chapter "Understanding Remedy Outcomes at the OECD National Contact
  Points" (2025, business-and-human-rights volume): a hand-coded dataset of 81 human-rights
  specific instances concluded 2012–2021, scored on gravity/remedy factors, descriptive analysis, not
  distributed in ML-ready form; different population (HR-subset, concluded-only), different target
  (remedy degree vs intake acceptance), no splits or scored contract.
- Verdict: differentiated (prior art exists in adjacent form; our contribution is the full-population,
  all-topics intake-acceptance prediction task at the filing instant with temporal splits and a scored
  contract, built from the publisher's own structured registry).

## Dated example (Europe/Paris, publisher HQ; all dates at day grain)

Case kr0029 (Korean NCP, filed 2026-02-27, decided 2026-05-21):
- Feature event window: all specific instances with submission date < 2026-02-27 and initial
  assessment decided before the instant (trailing acceptance rates per NCP, submitter class, topic).
- First-available timestamps and version: complaint exists 2026-02-27; structured attributes as coded
  in the current DB vintage (fetched 2026-11-03; June-2025 platform migration; no historical vintages).
- Eligibility cutoff: submission date inside a scored window AND terminal status at extraction
  ("In progress" rows are excluded, not labelled negative).
- Prediction instant: 2026-02-27 00:00 Europe/Paris (day-grain convention; the NCP recorded the date, no
  time of day).
- Target start/end: 2026-02-27 → the initial-assessment publication 2026-05-21 (decision event);
  every part of the target window is strictly after the instant. The target is the NCP's published
  decision, not any DB listing event.

## Uncertainties carried to construction (recorded, not resolved here)

1. Topic/sector codification timing (ASSUMPTION: complaint-stated). Verify on a bounded sample: DB
   topic codes vs the chapters cited in the complaint text (linked initial-assessment statements). A
   material mismatch downgrades those columns to post-hoc → drop them.
2. Exact per-window counts, pending fraction of 2022–2024 filings, clustered counts (NCP / respondent
   company / submission year) — first construction measurement, worker-side; never estimated here.
3. Headroom risk (the WB-instrument-family defect): if a trailing NCP(+submitter-class) rate table
   matches the model, there is no headroom → drop at baseline. The reference triad is mandatory.
4. Self-answer coupling (same class as za-statsa): a scored row's label (acceptance decided at t) is a
   history operand for later rows — enforce the restricted prediction protocol (fixed-window feature
   matrices or stripped keys) and run the gate-1.5 reverse-history probes on the exact artifact.
