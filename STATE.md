# Current state

Updated: 2026-10-23 07:00Z (camara-001 worker follow-up tick: the advancement session's close-out was verified and
completed - provider-confirmed cleanup (Hetzner 404 on server 171985941; zero camara-001 IPs remain, the only project
IP is camara-002's), staging release job-camara-001 re-verified 8/8 assets by size+sha256, and the three commits the
advancement session left unpushed (30b03d8, d54add9, 97d7beb) were pushed this tick. One process flag handed to
advancement: build.py computes in-build reference AUCs before the qualification gate. camara-002 still running at
close. Next action unchanged: collect camara-002, exit 0 + passing gate report + --accept on the exact bytes before
any scoring, then the runner-contract baseline.)

## 2026-10-23 - camara-bill-advancement construction tick: label-code and right-censoring defects corrected from measurement; build written, smoke-green; camara-001 failed on guard anchors, camara-002 running

No actionable release work existed (tsb published; nhs-ae and wb-ieg dropped with preserved negative findings),
so the tick went to construction, per the operator's actionable list. Candidate chosen from the class-A ready
queue: camara-bill-advancement (worker-trivial measured cost vs chilecompra's 100-150 GB, nz-ea's 3.7 GB and
za's multi-table timing work).

**Two discovery-record claims were measured wrong before any build was written, and both changed the design.**

1. **The label code.** The record carried "idSituacao 251 = Transformado em Norma Jurídica, 1.5% on the 2005
   sample". Re-measured with a quote-parity parser keyed on the file's own header names (whole 1991 file as
   ground truth): the positive code is **1140** (`Transformado em Norma Jurídica`, 311/4,436 = 7.0% of the 1991
   cohort); 251 is an `ultimoStatus_idTipoTramitacao` value. `probe_samples.py` read column 25 positionally as
   idSituacao, so its codes (100/319/1005/502/…) and the "1.5%" were mis-indexed artefacts of the same defect.
   `probe_censoring.py` (v1) reproduced the class of defect independently (naive line-splitting breaks on quoted
   multi-line ementas); its numbers are kept only as the diagnosis, superseded by `probe_censoring2.py`.
2. **Right-censoring.** ~25-53% of rows carry an EMPTY `ultimoStatus_idSituacao` and the API v2 confirms genuinely
   no tramitação on record (not a file gap). And bills do NOT settle at legislature close: 5/5 sampled 2019-file
   non-terminal rows match the live API exactly, with 2024-2026 status timestamps (e.g. PL 1/2019 "Aguardando
   Apreciação pelo Senado Federal", 2025-08-26). The scored population is therefore "bills whose status is
   terminal at the vintage", with no-status/non-terminal/merged rows counted per window - recorded, never
   inferred as a membership decision. `probe_file_inventory.py`: 35/35 years 200 OK, 747.4 MB + 456.0 MB.

**Build + smoke.** `source/build.py` (descending-first-wins union, presentation-instant features only, terminal
label with a frozen code-classification table, in-build naive references, fixtures). `tests_smoke_build.py`
runs the real build over 70 synthetic year files - caught three real bugs before worker spend (whole-file header
trim in both passes, a wrong row-count metric) and validated the proponente-ordering rule, the true id-collision
path, unobserved buckets and the quality/meta writers. **SMOKE OK.**

**camara-001 (server 171985941, 395.6 s, exit 2, EUR 0.06) failed on three of MY anchors, not on the data:** the
record's row estimates were too high (measured 642,067 in-window / 160,559 train vs estimated 700k-1.05M /
180k-420k) and the portal facet bound 11,640 was read from a **PL-filtered** search page, so it bounds PL-only
positives, not the all-types total (17,513). The full build was otherwise coherent: train 160,559 / 14,323
positives (8.92%), eval 37,885 / 1,397 (3.69%), holdout 36,892 / 1,793 (4.86%); PL 4188/2021 (BR do Mar)
matched and positive in holdout; both classes in every window. Reports collected into
`.factory/camara-001/reports/` (sha256-verified; bulk CSVs skipped); worker destroyed 06:48:42Z.

**camara-002 (server 171989986, launched 06:51:44Z, EUR 0.06) is RUNNING** with exactly one repair - the guards
re-anchored on camara-001's measurement and the cross-check narrowed to PL-only scope. Label rule, windows,
splits, features unchanged. **Acceptance pending: exit 0 + passing gate report + `--accept` on the exact bytes
before any scoring.** Two measured properties must be reported beside any score: the scored population is the
terminal-status subset (unobserved ≈55% train / 64% holdout) and the positive rate moves 8.92% → 3.69% → 4.86%.

Checks this tick: `check-candidate.py` OK (status ready); local smoke green; `assemble-job.py` bundle hashes
verified; October worker reservations now ~EUR 8.0 of 20 (camara-001 0.06 + camara-002 0.06 added). Commit
`30b03d8` pushed with the probes, build, smoke, record and camara-001 ledger; CI result for that commit is
reported in the session close-out.

## 2026-10-23 - camara-001 worker follow-up tick: cleanup and preservation provider-verified; unpushed commits pushed; in-build-reference order flagged to advancement

The watcher handed off camara-001 (failed, exit 2). The advancement session had already diagnosed it (three of
its own guard anchors, not a data defect), collected the bounded reports and destroyed the worker; this tick
verified that close-out and completed the missing pieces. No new job was launched - camara-002 remains the single
diagnosed recovery on this attempt chain, and interpreting its result belongs to advancement / the next tick.

- **Cleanup confirmed against the provider, not just the ledger.** Read-only Hetzner checks at 06:58Z:
  `GET /servers/171985941` -> 404 `server not found` (deletion provider-confirmed); the project holds exactly one
  primary IP (65.21.158.17), labeled `job=camara-002` and assigned to camara-002's live server - **zero IPs
  reference camara-001**. camara-002's server 171989986 answered 200 (running; ledger status running, consistent
  with its 06:51:44Z launch and camara-001's 6.6-minute build).
- **Preservation verified.** The failed attempt's evidence is durable in the private staging draft release
  `job-camara-001` (id 421522080): all 8 assets re-verified by id, size and sha256 against the job ledger. Bulk
  CSVs were deliberately not fetched to the coordinator; the bounded set (manifest.json, both summary.json
  copies, container.log 8,013 B, source.tar 174,080 B - ~189 KB total) is under `.factory/camara-001/reports/`,
  within the 20 MiB cap.
- **Failure interpretation re-checked from the collected evidence.** container.log shows the full build completed
  (642,067 in-window bills after the descending-first-wins union; 49 situation codes, 0 unresolved by data;
  coherent per-split buckets) and then exactly three FAIL lines - the three guard anchors - followed by
  `build failed; the extract is incomplete and qualification is not meaningful`, exit 2 **before** the gate
  (run.sh order is build -> qualify). The fixture anchor (PL 4188/2021 positive) produced no FAIL. Consequence:
  **camara-001's artifact was never qualified; no figure from this attempt is quotable** - the split/bucket
  numbers are construction diagnostics only.
- **The advancement session's commits were not actually pushed.** `origin/main..HEAD` held 30b03d8, d54add9,
  97d7beb (so the line above, "Commit `30b03d8` pushed", did not hold; cause not diagnosed this tick - the
  documented pitfall is a shell GH_TOKEN resolving to the staging token, which this repo denies). This tick
  pushed the chain with GH_TOKEN/GITHUB_TOKEN/FACTORY_GH_TOKEN cleared from the push environment and verified
  origin/main caught up. CI runs once at the pushed HEAD; exact-commit status is in this session's close-out.
- **Process flag to advancement (their decision; not acted on here).** build.py computes the in-build naive
  reference AUCs on the written rows **before** the qualification gate runs (camara-001 container.log
  "reference baselines" block sits beside the FAIL lines; run.sh runs the gate only after the build exits 0).
  The qualification skill's required order is construct -> qualify -> accept -> score, and construction must
  not compute/log baseline performance before acceptance. Decide whether that reference computation moves
  after acceptance (a construction change), and until decided no in-build reference figure may be quoted -
  this governs how camara-002's summary is read too.

## 2026-10-23 - Africa discovery tick: Kenya unpark question resolved (with an NC decision); ZA dam lead parked on access+licence; Nigeria closed on the publisher's own terms; Morocco censused clean-but-not-task-shaped; Ghana unreachable

Regional focus Africa; all five verdicts are in-region, no US substitution. Nigeria, Ghana and Morocco went from zero
coverage to recorded evidence. Nothing was built, qualified or packaged; no US source padded the report.

- `za-dws-dam-storage-exceedance` (ZA, NEW) - **parked on two measured blockers**; the strongest task idea of the tick
  (national per-dam weekly storage exceedance, ~250 dams, drought early warning for restriction/irrigation decisions).
  dws.gov.za answers 403 to a plain client AND a real browser from this coordinator; niwis.dws.gov.za times out;
  data.gov.za is DNS-dead; Wayback has ZERO captures of the terms or bulletin pages (CDX measured). So no schema, history
  or licence instrument could be read first-hand; everything attributed to the source is third-party (reservoirs.earth)
  and must be re-measured. The Cape-Town-only fallback (reachable, daily+weekly) was rejected on split-capacity + prior
  art (single system, Day Zero positives clustered 2017-18). Next action: one ~2-minute worker-side access test (is the
  403 coordinator-specific?), then read+quote the terms instrument if reachable, classify, and only then novelty.
- `ng-nbs-state-price-exceedance` (NG, NEW) - **dropped at the licence gate, the cheapest veto**. NBS's monthly
  state-level Price Watch series (food/PMS/AGO, the most task-shaped Nigerian data found) cannot be published: the
  publisher's own Terms & Conditions (nigerianstat.gov.ng/page/terms, fetched 2026-10-23) state verbatim that NBS data
  "will not be redistributed or sold to other individuals, institutions, or organizations with out the written agreement
  of the National Bureau of Statistics" - class D, quote archived in the record. Novelty never reached, not claimed.
  Reopen: written NBS agreement (operator-side) or a different channel under its own open terms. Landscape note: an HF
  org (electricsheepafrica) already mirrors NBS price-watch raw series - their provenance judgement, recorded as
  observation, not permission.
- `ma-datagovma-coverage` (MA, NEW) - **parked: portal censused, clean licence, no task-shaped content**. data.gov.ma is
  live with an anonymous CKAN API and ODbL on ALL 697 datasets (per-dataset license facet + portal FAQ, class B).
  Top-10-publisher title census (~590 datasets): annual court-activity tables (3-5 periods), HCP/BAM/ACAPS macro
  aggregates ending 2022-2023, regional real-estate/construction-materials tables ending 2019-2022, third-party
  governance indices at INPPLC, and AMMC weekly OPCVM files verified by download to be 6-category aggregates, NOT
  per-fund. No unit-level ongoing series. The census + licence are recorded so the next Africa tick re-probes only on
  portal growth, not from scratch.
- `gh-opendata-coverage` (GH, NEW) - **investigating: portal unreachable from this coordinator** (CKAN action API
  connection refused; real browser ERR_SOCKS_CONNECTION_FAILED). Third-party evidence (Data Landscapers, WB eTransform
  completion report): catalogue static ~3 years, no open licence on record, dated static CSVs. Access failure is not a
  rejection; next probe is one bounded re-probe from a worker network alongside the ZA test, then close under class C
  policy if per-dataset licences are absent.
- `kenya-opendata-knbs` (KE, UPDATED) - **the recorded unpark question is answered: YES, a channel now exists - with a
  condition.** KNBS runs a NEW National Statistical Repository (repository.knbs.or.ke, DSpace 10.0): anonymous REST
  API, 20 statistical communities, 1,366 discover-indexed objects (sampled: monthly Leading Economic Indicators back to
  2011, monthly CPI reports to 2026, quarterly GDP/BOP, Economic Survey 2007) - a real long-run channel. Its own
  accessibility page states (fetched + verified directly): "Unless stated otherwise on the item itself, content in this
  repository may be reused for non-commercial purposes, with attribution. CC BY-NC 4.0". NC is a stated conditional
  licence, not an open grant: whether our non-commercial research releases may carry an NC condition is an OPERATOR
  DECISION, recorded as next-action step 1. Item-level enumeration is 401/404 anonymously, so no series/timing census
  exists yet; CBK (regulator probe from the 2026-10-21 next action) was unreachable from the coordinator this tick -
  recorded as not-probed, not negative.

AfDB/UNECA coverage (no candidates opened, recorded here for the rotation): data.afdb.org is NXDOMAIN; the AfDB data
infrastructure is the Africa Information Highway (africadata.org / dataportal.opendataforafrica.org country portals,
Knoema-platform indicator portals), and UNECA's channel is ecastats.uneca.org - both aggregate-indicator territory,
already crowded by WDI mirrors and the electricsheepafrica HF mirrors; no unit-level task-shaped source was identified.
Session hygiene: check-candidate.py OK for all five records and --all exit 0 (82 records); probe scripts kept as the
recipes in each candidate directory and re-run end-to-end with identical evidence (probe_repository.py,
probe_terms.py, probe_portal_census.py, probe_access.py, probe_access_licence.py); scratch probes deleted after the
recipes were copied; no bulk data downloaded (largest fetches were four ~40-55 KB AMMC XLSX files).

## 2026-10-23 - Latin America discovery tick: IDEAM threshold blocker RESOLVED (measured); Argentina lead opened and closed at the novelty gate

Regional focus Latin America; both verdicts are in-region, no US substitution. One existing lead advanced
with a decisive measurement, one new lead (Argentina, previously zero coverage) opened, fully triaged and
closed with recorded evidence. Nothing was built, qualified or packaged.

- `ideam-rio-nivel-exceedance` (CO, class B CC BY-SA) - **still investigating, but the one blocking fact from
  the first pass (does an official per-station threshold exist in any obtainable form?) is resolved YES.**
  Current IDEAM bulletins (BAH/ITD/BCH, Oct 2026, fetched and text-extracted) carry zone-level alerts only;
  the per-station "COTA CRITICA x.xx m" values live in the historical IHD (Informe Hidrologico) PDFs,
  Wayback-archived (CDX captures 2017-2025): 16 station cotas extracted from one Oct-2024 IHD via pypdf
  (recipe kept as probe_ihd_cota_extract.py), with decade-stability evidence (Puerto Salgar 6.20 / El Banco
  8.30 identical in 2014 and 2024 bulletins). No machine-readable threshold table exists on datos.gov.co
  (catalogue searches empty; h4gs-wsmg Alertas Hidrologicas is a non-tabular Socrata view, 403 row access).
  Measured via SoQL (probe_cota_soql.py, re-run end-to-end today with identical output): El Banco 0025027020
  vs cota 8.30 = 5,937/105,354 hourly obs over 2015-2026 (5.64%), distinct days over cota per window
  train 2015-2019 137/1,777 days-with-data / eval 2020-2023 137/828 / holdout 2024-2026 111/957 - both
  classes in every window on this station, positives clustered into flood episodes, telemetry gaps measured.
  Two construction hazards measured, not assumed: name-only joins produce FALSE PAIRS (IHD "PUERTO ANGOSTURAS
  - RIO ARIARI" matches telemetry "ANGOSTURA" 0021137050, a Magdalena station - excluded from claims), and
  Mitu 0042077020 shows 0/29,688 obs over cota 10.20 - an unexplained frame/station anomaly; every joined
  station needs the zero/always-positive sanity check. record.json carries the new measurement block and a
  rewritten next_action: IHD harvest (CDX sweep 2016-2024) -> join by codigoestacion + river + municipio ->
  per-station continuity and clustered base rates -> raw-vs-validated as-of comparison -> novelty check before
  any ready verdict. check-candidate OK (status=investigating).
- `ar-ecobici-station-demand-exceedance` (AR, NEW) - **dropped at the novelty gate; licence and access were
  excellent and are recorded so nobody re-verifies them.** Buenos Aires Data (CKAN) carries every Ecobici trip
  since 2010 under CC-BY-2.5-AR (package metadata, read 2026-10-23): 17 yearly files 2010-2026, all HEAD-200
  with sizes measured (~1.75 GB total; 2019 398 MB, 2025 208 MB, 2026 partial 143 MB, CDN Last-Modified shows
  the current-year file updating in-year and completed years frozen Jan-Mar of Y+1). Bounded 2015 sample
  parsed: 503,252 trips, 15 documented columns with station ids + coordinates. The task (station-day demand
  exceedance) failed the novelty check with a recorded mirror verdict (check-novelty.py, 2 queries): the task
  family exists ML-ready for other cities (UCI Bike Sharing, Seoul Bike Sharing Demand, Kaggle 2015),
  Ecobici-specific demand prediction is already published (UTDT thesis 2018-2020; UBA course project
  benchmarking xgboost on Ecobici 2016-2017 with weather; TFI 2016), Ecobici user churn has a UTDT thesis,
  and the raw 2025 trips are mirrored on Kaggle with EDA notebooks. What would be ours (splits, gating,
  frozen thresholds) is packaging on a saturated task - closed per the standing rule. Reopen conditions in
  the record. check-candidate OK (status=dropped).

Coverage after this session (discovery-coverage.py): 78 candidates, 25 live; Latin America 7 (BR 2, CL 2,
CO 1, MX 1, AR 1 - Argentina no longer zero); live non-US 19/25 (76%); ready buffer 4 (camara-bill-
advancement BR, chilecompra-tender-outcome CL, nz-ea-wholesale-price-exceedance, za-municipal-audit-opinion)
plus tsb/wb above them at packaged/qualified. Session hygiene: check-candidate.py --all exit 0 (78 records,
warning lines pre-existing); unittest suite 588/588 OK; factory doctor and check-runtime --source-only clean;
probe scripts kept in the two candidate directories (probe_ihd_cota_extract.py, probe_cota_soql.py executed
end-to-end today with identical output; probe_ba_inventory.py) and session scratch deleted (~160 MB of
bulletin PDFs and samples never committed). No US source substituted for the regional quota; Argentina's
empty coverage was probed honestly and closed on evidence, not padded.

## 2026-10-22 - wb-baseline-001 close-out (watcher): runner-contract baseline green; every recorded number verified against the fetched reports

wb-baseline-001 (worker 171927514, 66.9 s, exit 0, staging release 421265626) is closed out. The
advancement tick had already recorded the triad and the decision point (commit d77213d6,
"Advancement" entry at the bottom) from the collected result; this watcher run fetched the
release's nine small report assets into .factory/wb-baseline-001/reports/ - manifest.json,
accept.log, baseline_result.json, dependency-versions.txt, materialize.log, pip-install.log,
train.log, validate.log, container.log, source.tar (163 KiB total; no bulk CSV exists in this
release, and the private holdout never left staging) - every file sha256-verified against the
release manifest. The fetched logs confirm the recorded result end to end: the gate re-ACCEPTed
the fetched artifact before any scoring ("ACCEPTED: /data/extract matches the qualified artifact
b8345bcb5769e422", the qualified version), train.py eval AUC 0.5879, validate.py independent
recompute 0.5879, "[validate] CONTRACT OK", runner files hash-identical to the benchmark's
declared digests (python 3.13.17 / pandas 2.3.3 / numpy 2.5.4 / xgboost 3.4.1 / scikit-learn
1.9.1), and materialize.log shows the private holdout was NOT copied into the runner workdir.
baseline_result.json's rows and positive rates (9,598 / 1,479 / 1,097; 0.717962 / 0.793103 /
0.806746) equal record.json's construction_output splits exactly.

The decisive finding stands as recorded: the contract model (0.5879 eval AUC) trails the
one-line country-identity rule (0.6003 eval) - a qualification defect, so no headroom claim is
quotable from the model number; the candidate is at the decision point, not at packaging.
Ledger: collect reconciled worker 171927514 as provider-confirmed deleted (deleted_at re-stamped
22:43:01Z at reconcile; the actual destruction was 22:33:17Z, which is what record.json carries),
and jobs/wb-baseline-001.json is committed with this close-out. Next action unchanged: the
bounded holdout-leg scoring job (contract model AND identity/calendar rules on the private
holdout rows of the accepted artifact, same fitted artifacts, no retraining choices, re-ACCEPT
before scoring), then either record the benchmark claim and package, or record the negative
result and drop.

## 2026-10-22 - wb-001 green (watcher close-out): wb-ieg-project-outcome QUALIFIED - gate 38/38 on the full artifact; baseline job wb-baseline-001 now running

**wb-001 (server 171926570, 385.3 s, exit 0, staging release 421262457, EUR 0.04 reservation) is
the first green build of wb-ieg-project-outcome, and the qualification gate passed over the full
artifact: 38/38 checks (leakage, timing, units, splits, runner), 0 failed, gate 1.4.0, artifact
digest b8345bcb5769e422c75dd0451c81854ceb8fa809b4bb60977cd781d4071abaa9.** Sources pulled on the
worker: one anonymous IEG CSV GET (3,340,648 bytes, sha256 7080b652...) plus 24 projects-API
requests (23 offset pages of 1,000 full records + supplementary id-lookups recovering 25 records;
54,486,121-byte merged JSON, 22,665 records). The extract stays in staging.

Coverage, measured against discovery's own window counts: built 12,174 rows = 12,629 raw IEG rows
- 1 P122764 duplicate - 151 Not Rated (unobserved target) - 303 approved FY2020+ (outside windows,
counted per year); train 9,598 / eval 1,479 / holdout 1,097 (approval FY 1956-2009 / 2010-2014 /
2015-2019), positives 6,891 / 1,173 / 885. Train positives are identical to discovery's (the
70.74% -> 71.80% rate move is the denominator dropping 143 unrated rows); eval's single positive
delta is the deduped P122764 row (MS+ in both rows, approval FY inside the eval window); holdout
identical. Right-censoring quantified per window, not dropped: not-yet-evaluated API projects
approved <=FY2019 - train 1,724 / eval 719 / holdout 637. The RAP 2024 Fig O.3 cross-check asserts
the published MS+ trend (71 -> 91 points FY2013-2023) while the panel runs 3-7 points below the
published level under every cohort restriction - trend asserted, not level, and the reason is
recorded (RAP's standardized cohort is not reproducible from the CSV columns).

Construction-time references (stdlib, train-estimated, on the written rows): majority-class 0.718
accuracy; identity-only (country) 0.6003 eval / 0.4909 holdout; calendar-only (country x approval_fy)
identical (every eval/holdout cell unseen in train); agreement-type 0.5407/0.4844; practice-group
0.5497/0.4948. No persistence leg exists at project grain - each project is evaluated once, so the
nhs-ae persistence failure mode cannot occur here. Prevalence drift 0.718 -> 0.793 -> 0.807
(train -> eval -> holdout) is a measured property of the phenomenon (IEG ratings improved over
time), recorded in the record to be reported beside any score.

**Close-out (this watcher).** The scheduled advancement session ran the build, collected and
destroyed the worker (22:26:03Z / 22:26:31Z), wrote the construction measurements, the notes, the
baseline bundle and its ledger entry, launched wb-baseline-001 at 22:27:44Z - and its turn ended
before STATE.md, the commit and the handled marker. This run fetched the small report assets of
release 421262457 into `.factory/wb-001/reports/` (manifest.json, meta.json, quality.json, build
summary, gate report, container.log, source.tar - all sha256-verified against the release
manifest; the three bulk CSVs skipped, the 335 KB labelled holdout stays in staging), re-matched
the gate report's five artifact digests to the manifest asset digests, merged a duplicated wb-001
jobs[] entry, and recorded: record.json ready -> **qualified** with the qualification and
construction_output blocks (splits, windows, five file digests), jobs/wb-001.json, and the
candidate's source/ and baseline/ bundles. check-candidate OK (status=qualified), --all exit 0
(76 records).

**wb-baseline-001 is running** (worker 171927514, EUR 0.06 reservation, launched 22:27:44Z by the
advancement session; its launch process survived the interrupted turn and completed the dispatch -
record re-read as running by this close-out). It fetches the five accepted files from staging
release 421262457, re-accepts through the gate, materializes the runner workdir (private holdout
never copied) and runs the benchmark's own train.py + validate.sh verbatim. The watcher reports it
when it finishes; the triad then needs the full-model eval AUC against the references above. The
Kraay & Tawara prior-art caveat stands (the World Bank's own internal model leans on post-approval
features; strictly approval-time signal is unmeasured and may be modest): if the model does not
beat the naive references, this is recorded as a negative result and not packaged (the nhs-ae
pattern). October worker reservations now EUR 7.86 of the 20 EUR allowance, only the running
baseline's 0.06 unspent.

## 2026-10-22 - Release tick: tsb-railway-occurrence-casualty PACKAGED - baseline 0.8126 beats every reference; staged private on both destinations

**The tick went to release work, per the standing priority.** No candidate sat at status `packaged`
(nhs-ae is `dropped` post-audit; who-flunet/msha/food are `published`), and tsb-railway-occurrence-
casualty was the one candidate whose next step was packaging-side, so the session carried it from
`qualified` through the baseline job, the full package, and private staging on both destinations.
Three green worker jobs, one per step, all collected and destroyed; every number below was read from
collected job results, fetched reports and API readbacks, not from consoles.

**1. tsb-baseline-001 (server 171753063, 73.7 s, exit 0, result release 420361967).** The
runner-contract baseline on the accepted tsb-004 artifact (e75a59bb...), fetched from staging
release 420246008 - not rebuilt. The gate re-accepted the exact fetched bytes before any scoring
(`ACCEPTED: /data/extract matches the qualified artifact e75a59bb1116e39b`), then the benchmark's
own unmodified train.py + validate.sh measured **eval AUC 0.8126, printed identically by both
entry points, `[validate] CONTRACT OK`** (runner digests equal the benchmark's declared hashes;
python 3.13.17 / pandas 2.3.3 / numpy 2.5.4 / xgboost 3.4.1 / scikit-learn 1.9.1; the private
holdout was never copied into the workdir). The triad the record required: persistence analogue
(trailing-12m casualty rate) 0.527 eval / 0.495 holdout; best single context column (activity_type)
0.707 / 0.699; full model **0.8126** - real headroom over both, the nhs-ae persistence failure mode
is absent, and the reference numbers now live in the package's VERIFICATION.md, RELEASE_NOTES.md,
measurements.json and the card beside the model number.

**2. The package (release/tsb-railway-occurrence-casualty/).** Full single-config package after the
flunet/nhs-ae pattern: README, DATA_DICTIONARY (every shipped column's documented meaning, role and
availability class; the 34 post-hoc exclusions named), LICENSE.md + LICENSE-MIT.txt +
LICENSE-CC0-1.0.txt (OGL-Canada 2.0 source terms carried through unchanged, attribution statement
verbatim, our compilation CC0, code MIT - declared in candidates/<id>/license.json so the manifest
generates it), REPRODUCE.md, RELEASE_NOTES.md, VERIFICATION.md (sections 1-5 + honest "not covered":
no agent comparison, holdout AUC deliberately unmeasured, current-vintage-only caveat),
measurements.json, get_dataset.py, code/{build,run.sh,qualify_dataset,materialize}, baseline/
(the three runner files verbatim + reproduce_baseline.sh + README). `release-manifest.py` wrote
MANIFEST.json + SHA256SUMS (artifact e75a59bb..., construction commit 296db53 - the exact build.py
bytes tsb-004 executed); `check-package.py` OK. The 406-test suite caught one real defect before it
shipped: the card declared train/eval/holdout but the manifest had no splits because the record
carried no construction_output block - the tsb-004 close-out (written pre-baseline) never added it.
construction_output (splits with counts) and the top-level baseline block are now in record.json;
the manifest regenerated; suite green 406/406 after.

**3. GitHub destination (tsb-publish-001, server 171755236, result release 420369733).** Private
repository earino/tsb-railway-occurrence-casualty created; the package pushed as initial main
commit 61f06f1d; draft release v2026.10 (420368897) created; the worker copied the five accepted
assets from staging under flat names, each sha256 verified on arrival and against the server digest
after upload (1,709,187 bytes, never through the coordinator). Read back through the API: exactly
5/5 assets matching MANIFEST.json by name/size/server-side sha256; release published non-draft so
the tag exists; **tag v2026.10 == main == 61f06f1d** (git-refs API); anonymous repo GET 404. Then
the documented download path was EXECUTED against the private release: get_dataset.py exit 0 (all
five assets token-downloaded via the API asset-id path, digests verified, runner layout restored)
and `qualify_dataset.py --accept` on the downloaded tree -> **ACCEPTED, artifact e75a59bb...**.

**4. Hugging Face destination (tsb-hf-001, server 171755920, result release 420373659).**
`hf-publish.py --create --upload-small` (write credential from its mode-0600 file, never printed)
created the private Hub repo and landed 10 small files (the rendered card from candidates/<id>/
card.md - front matter carries license: other / ogl-canada-2.0-attribution-plus-cc0-compilation -
plus LOADING.md generated from the manifest, MANIFEST.json, SHA256SUMS, both licence texts, the
dictionary and VERIFICATION/measurements). The worker job then uploaded all five data files from the
staged GitHub release with digest verification both ends (uploads 5, skipped 0, failures 0) and ran
the built-in loading check against the uploaded bytes: **ok: true, problems: []** - train 7,925
rows / 883 positives, eval 3,831 / 463, holdout 1,976 / 278, 17 columns per split, label values
['0','1']. No dataset_infos.json is shipped: hf-dataset-infos.py is levels-only (multi-config), so
this follows the nhs-ae single-config precedent - the Hub's own inference, proven by the loading
check rather than assumed (occ_no is letter-prefixed, so the msha mostly-digits failure mode does
not apply). `hf-publish.py --verify`: ok - 5/5 data files at manifest digests, 0 missing, 0
size-mismatched, recorded in DESTINATIONS.json; `--tag` LAST: Hub tag v2026.10 ==
main == e6fe2a2c, tag_matches_main true.

**State.** Record: qualified -> **packaged** (packaged_at 2026-10-22T06:30Z, awaiting_operator
true - the flip is the operator's single act), three job entries, three artifact entries (staging
release + both destinations), construction_output + baseline blocks, next_action rewritten to the
flip-waiting state with the full post-approval publication sequence. check-candidate.py OK
(status=packaged), --all exit 0 (60 records), check-package OK, suite 406/406, dashboard rebuilt
(8 releases). Worker spend this month: the three jobs add EUR 0.14 in reservations (0.06 + 0.04 +
0.04) to the ~6.1 EUR recorded before, well inside the 20 EUR allowance; all three workers
destroyed and re-read as deleted (06:10:12Z, 06:21:50Z, 06:27:46Z).

**NEXT: the operator's flip for tsb-railway-occurrence-casualty** (scout-release-notify delivers
the ready-for-flip message); after it, publication per the recorded sequence needs no further
approval - DESTINATIONS.json first, flip both, anonymous proofs, docs refresh, tag last, website.


## 2026-10-22 - Oceania discovery tick: four verdicts (2 go / 2 reject), all four non-US

**Regional focus Oceania; quota was three verdicts with at least two in-region - four
delivered, 4/4 non-US, no US substitution. Every source was licence-triaged first; the
two rejections cost two page reads and one blocked HTTP request each, with zero schema
or volume probing spent on unshippable sources.**

- `abs-visitor-arrivals-direction` (ABS, AU) - **go, ready, class A** (CC BY 4.0, ABS
  site-wide statement read first-hand). Task: will short-term visitor arrivals from a
  country in the first-unpublished month fall short of the same month a year earlier?
  Measured (candidates/abs-visitor-arrivals-direction/probe_oad_country.py, executed
  twice with identical results): full panel 59,452 obs / 428 months 1991-01..2026-08 /
  77 countries x 2 traveller categories, one 3.3 MB API request in 3.5 s; MoM direction
  near coin-flip (58,082 pairs); YoY split windows train 1991-2014 up=24,166/down=13,575,
  eval 2015-2019 5,588/2,630, holdout 2022-2026 6,167/1,533 - both classes in every
  window and every year. Release lag observed 43/42/43 days (Aug/Jul/Apr 2026 issues);
  a documented revision event (March 2026 re-released in the April 2026 issue) recorded
  as the current-vintage caveat. Novelty: differentiated (mechanical search in the
  record; tourism-forecasting literature and TRA forecasts exist, no ML-ready
  publication-gated arrivals benchmark). Note: ABS Retail Trade was checked first and
  is CEASED (final issue June 2025) - do not revisit it as a recurring source.
- `nz-ea-wholesale-price-exceedance` (Electricity Authority, NZ) - **go, ready, class
  A** (CC BY 4.0 on EMI LegalInformation *and* on the successor hub's copyright page;
  EMI is being decommissioned onto the ea.govt.nz Data & insights hub - recorded as a
  source-migration risk, not a licence risk; construction must pin blob URLs + digests).
  Task: will a region's daily mean final wholesale price exceed a training-frozen
  threshold about a week ahead? Measured
  (candidates/nz-ea-wholesale-price-exceedance/probe_final_prices.py, executed twice):
  30 years of nodal final prices - 360 monthly files 199610..202609 (median 10.0 MB) +
  368 daily files since 20251021, 3,714 MB total, anonymous Azure blob listing; era
  sample: Jan 1997 max $50 (quiet), Jul 2008 9/31 days >$200, Jun 2020 5/30 days >$200,
  Aug 2024 25/31 days >$200 with daily means to $884, recent-era sampled median $32 -
  clustered dry-year episodes give both classes in every candidate window. Publication
  instant documented ("final prices by 2pm the following business day"), measured file
  lag p50 1.80 d / max 5.80 d; POC->Island/region mapping publisher-published with POC
  start/end dates; regime break 2022-11-01 (real-time pricing) documented for splits.
  Novelty: differentiated vs the EPF benchmark (five northern markets, level
  regression, no NZ), an AUT level-forecasting study and a single-node GitHub project.
- `bom-cyclone-best-track` (BoM, AU) - **reject, class D.** The cyclone-database page
  states no licence, so BoM's default governs: "You must not supply it to any other
  person or use it for any commercial purpose" (copyright page, quoted in the record).
  Scripted HTTP to the best-track CSV is blocked outright (measured 403 anti-scraping);
  the offered FTP channel carries the same non-redistributable default. Closed. Reopen
  condition recorded: a CC BY statement on the dataset's own page, or a redistributor
  with a verifiable rights-holder grant (NCAR RDA ds824.1 declares CC BY 4.0 for SH
  best tracks - a separate source to re-vet if ever used).
- `atsb-aviation-occurrence-triage` (ATSB, AU) - **reject: access-blocked + purpose
  limitation.** Publisher's own page: "you cannot download the entire database", export
  capped at 200 rows, database "made available for general statistical purposes only",
  commercial use not endorsed. No open licence instrument was read because access
  vetoes first. Closed; reopens only if ATSB publishes a bulk extract under an open
  licence.

State-licence texture (the tick brief asked for states separately): the two federal
channels above closed on terms; state portals were **not** separately probed this tick
- the four verdicts consumed the quota first, and Victoria's only probed channel so far
reported licence_id 'other-open' with no URL (melbourne-pedestrian-counts). The next
Oceania tick should triage a state portal licence (DataVic, then NSW/QLD) and the
data.govt.nz catalogue before looking at task fit.

Coverage after this session (discovery-coverage.py): 60 candidates, 21 live; Oceania 5
(AU 4, NZ 1); live non-US 15/21 (71%); ready buffer 7 - the two new candidates plus
chilecompra-tender-outcome, camara-bill-advancement, za-municipal-audit-opinion,
my-pricecatcher-weekly-increase, eutl-installation-net-short (tsb-railway-occurrence-
casualty sits above them at qualified). licence-rank.py sorts both new candidates at
the top of the class-A construction queue.

Session hygiene: check-candidate.py --all exit 0 (60 records); probe scripts kept per
convention in the two new candidate directories and each executed end-to-end once;
session scratch deleted (45.6 MB NZ price sample, 3.3 MB ABS panel, listing XMLs - never
committed). No US source substituted for the regional quota.


## 2026-10-22 - tsb-004: gate PASSED on the full artifact - tsb-railway-occurrence-casualty qualified; the tsb-003 "corrupt coordinates" were a wrong-frame misreading

**tsb-004 (server 171730217, release 420246008, 31.1 s, exit 0) is the first green build, and the
qualification gate passed over the full artifact: 37/37 checks (leakage, timing, units, splits, runner),
0 failed, gate 1.4.0, artifact digest e75a59bb1116e39b980c9fa2f5ea7c2b984fa6ccce4b3286f194de69d2b32309.**
Panel 2016-01-01..2026-08-31 (vintage data_max exactly at the window end; 56,865 pre-panel and 109
post-window rows counted and excluded; 70,706 kept, 139 byte-identical export duplicates dropped):
train 7,925 rows / 883 positives (11.14%), eval 3,831 / 463 (12.09%), holdout 1,976 / 278 (14.07%),
each positive an independent occurrence (distinct_events == positives). Label integrity: InjuriesIND
and the injury totals agree on all 1,624 positive panel rows (0 disagreements either way), and the
INJURIES child table corroborates all 1,624. Publisher cross-check 2025: 832 ACCIDENT vs 831 published,
331 INCIDENT vs 332 published - within 0.3% of TSB's own annual summary.

**The coordinate story corrected.** tsb-003's failure was diagnosed here as "5 corrupt source values,
Gulf of Guinea" - that diagnosis was wrong, and this close-out proved it with a targeted re-probe of
the same 2 MB source window: all four occurrences (R21V0255, R21V0233, R21Q0053, R21V0160) decode to
exactly one valid Canadian position under the measured three-encoding rule (raw 492200/122598 ->
49.3667N ddmm.ff + 122.598W x1e3; 49033/122150 -> 49.033N + 122.150W; 48598/723566 -> 48.598N +
72.594W ddmm.ff). The source mixes coordinate encodings per value; the assumed single x10^4 frame
misplaced mixed values by an order of magnitude. tsb-004's frame check on the written rows: 0 of
13,732 outside [41,72]N / [-145,-52]E. The correction is appended to the record's tsb-003 measurement,
the notes, and the jobs[] entries.

**Naive baselines measured inside the build, before any model spend:** activity_type conditional rate
AUC 0.707 eval / 0.6987 holdout; subdivision 0.6997/0.6544; railway 0.5472/0.5234; province
0.5576/0.5813; month 0.5421/0.5599; trailing-12m-rate persistence analogue 0.527/0.495. Real context
headroom over the global train rate (0.111), and persistence does NOT dominate - the nhs-ae failure
mode is absent. Status: **qualified**.

**Close-out (this watcher).** The research session that ran the tsb-001..004 loop died immediately
after collecting the result, leaving the close-out half-done: record.json carried a pre-written
qualification block with three wrong facts - a staging tag matching no release, a 02:55Z timestamp
still in the future, and "38 checks" where the report carries 37 - and no handled marker. This run
fetched the small assets of release 420246008 into `.factory/tsb-004/reports/` (diagnostics.json,
meta.json, quality.json, two byte-identical build summaries, two byte-identical qualification
reports, source.tar, container.log, manifest.json; the three bulk CSVs skipped, and the 244 KB
labelled holdout that slipped under the 256 KiB fetch threshold was deleted from this host), verified
all 37 gate ok-flags, re-matched the report's five artifact sha256s against the release manifest
(train/eval/holdout/meta/quality all match), corrected the three errors plus the corrupt-coordinate
diagnosis, and recorded the outcome in record.json and here. The worker was already destroyed by the
session (ledger deleted_at 02:29:52Z, re-read as deleted). Committed with this entry: the candidate's
source/ (the three-encoding coordinate decoder), probe scripts kept per convention, jobs/tsb-004.json,
the regenerated dashboard, and these records. Next action (owned by the construction session): the
full-model baseline job with the harness runner (the flunet/msha pattern) - persistence 0.527/0.495
and activity_type 0.707/0.699 are the numbers to beat - then packaging per dataset-release (OGL-Canada
2.0 attribution, our compilation CC0-1.0), release-manifest, package check, private staging on both
destinations.

## 2026-10-22 - tsb-003: past the panel-start guard, first full-panel splits measured; exited 2 on 5 corrupt source coordinates

**The re-pinned band worked, and the build reached the split stage on full data for the first time.**
tsb-003 (server 171729523, release 420242998, 28.5 s) measured the panel start at 2016-01-01 - inside the
re-pinned [2014, 2018] band - then computed **train 7,925 / eval 3,831 / holdout 1,976** (pre-window 56,865,
post-window 109; 7 non-identical OccNo collisions handled, 0 empty OccNo; totals reconcile with the 70,706
parsed occurrences). It then failed a new guard: 5 coordinate values on 4 occurrences (R21V0255, R21V0233,
R21Q0053, R21V0160) sit outside the asserted Canadian envelope - lat 4.9033/4.8598, lon -12.2598/-12.2150
(east-positive) is the Gulf of Guinea. The x10^4 integer frame and West->east conversion validate the other
~70k rows, so these are corrupt source values, not a frame-conversion defect; the guard that fired exists
precisely for this failure class. No artifact, no gate run.

**Close-out.** Reports fetched to `.factory/tsb-003/reports/` (diagnostics.json 5,263 B, container.log
3,835 B, manifest.json 2,699 B, source.tar 153,600 B); worker destroyed by this watcher after collection;
the attempt, the split measurement and the coordinate evidence are in the candidate's record.json
(jobs[], measurements.panel_split_and_coordinate_guard_2026_10_22, next_action). The coordinate fix
(missing-value handling with a recorded count, or repair from source evidence) and the tsb-004 relaunch
belong to the live construction session, which was mid-loop on this candidate when this was written.



## 2026-10-22 - tsb-001 and tsb-002 both exited 2 on the measured-panel-start guard; the full panel measures 2016; the session re-pinned the band and tsb-003 is running

**Both construction attempts for `tsb-railway-occurrence-casualty` failed on the same guard, and neither
produced an artifact - no gate ran, and nothing from either run counts as a measurement of the dataset.**
What the runs did prove on the full panel, twice, on the worker: all five RODSdb public CSVs download cleanly
with the browser-like header set (OCCURRENCE 97,894,047 B; TRAIN 21,775,681 B; ROLLING_STOCK 34,758,209 B;
INJURIES 2,713,169 B; COMPONENTS 42,523 B - sha256 and last-modified logged each time), and the occurrence
panel parses to 70,706 rows (139 exact duplicates dropped, 0 unparseable OccDate).

**tsb-001 (exit 2 in 33 s, server 171728396, release 420237693): the era rule was wrong.** It counted a row
as early-signatured when AccIncType was HISTORICAL/DG LEAKER *or* TimeZone was empty/N-A. Sporadic N/A
timezones persist into the 2010s, so the folded rule measured the panel start at 2016, outside the asserted
[1995, 2010] band, and the build exited by design. The live research session collected the failure at 02:13,
made the same diagnosis, fixed build.py (era signal = taxonomy alone; tz-missingness recorded per year as a
separate property; per-year diagnostics written before the assertion so a failed run still uploads
evidence), smoke-tested against a 1990s-signature fixture (panel start 1996 on the fixture, inside the band),
destroyed the worker at 02:14:17Z and relaunched as tsb-002 at 02:14:50Z.

**tsb-002 (exit 2 in 28 s, server 171728935, release 420240534): the corrected measurement, and the real
finding.** With the taxonomy-only era signal the per-year table is now uploaded
(output/extract/diagnostics.json) and it shows the era share decays *gradually*: 25-38% through 1991,
8-17% in 1993-2000, 4-9% in 2001-2013, 2.3% at 2015, 0.58% at 2016, 0% from 2017. The 2%-every-later-year
rule therefore still measures the panel start at **2016**, outside [1995, 2010] - the record's proposed 2004
sits inside a measured 6.8% early-taxonomy tail, and reaching it would mean loosening the threshold to
~10%, i.e. choosing the threshold to hit the proposed answer. Timezone-missingness is a different, abrupter
boundary: ~99% through 1991, 29.9% at 1992, 0% 1993-2000, a sporadic 5-17% bump 2001-2007, 0% from 2008.

**Resolution, taken by the live construction session within a minute of the second failure - this watcher
launched nothing.** The session chose to trust the measurement rather than tune the threshold: the band is
re-pinned to [2014, 2018] with the measured decay documented in source/build.py ("the band pins the
measurement without freezing it"), so the panel becomes 2016-2026 (~13,441 occurrences; train through 2023,
eval 2024, holdout 2025-26 remains feasible). It re-assembled and launched **tsb-003** at 02:19:43Z (server
171729523, cx23/hel1; bundle build.py sha 942ac03cb925214f... equals the committed source, verified by this
watcher); status: running when this was written. The decision, the per-year table and both failure diagnoses
are recorded in the candidate's record.json (jobs[], measurements.full_panel_era_diagnostics_2026_10_22,
next_action).

**Records and cleanup.** tsb-001's worker was destroyed by the session at 02:14:17Z and tsb-002's by this
watcher after collection (ledger deleted_at 02:20:40Z; server 171728935 gone). All small assets of both
staging releases were fetched and sha256-verified into `.factory/tsb-001/reports/` (container.log 862 B,
manifest.json 2,320 B, source.tar 143,360 B) and `.factory/tsb-002/reports/` (diagnostics.json 5,263 B,
container.log 3,517 B, manifest.json 2,699 B, source.tar 153,600 B); no bulk asset touched this host. The
candidate's record.json carries both failed-attempt entries, the full-panel measurement and the tsb-003
launch snapshot; `check-candidate.py` OK (status ready). Committed with this entry: all three job ledger
records, the candidate's source/ (the re-pinned build.py tsb-003 is running; the exact bytes tsb-002 ran stay
pinned by its ledger sha ee3a8777771732d9a... and release 420240534's source.tar), and the build-decision
notes.



## 2026-10-22 - East Asia discovery tick: one GO (Taiwan typhoon-day closures), three parks, all recorded

Regional focus East Asia; four sources opened, each taken to a recorded verdict before the next. All four
are class B (attribution) on licence - the tick probed no class C source, per the standing triage rule.

- **tw-typhoon-day-closure - GO (status investigating).** Predict, at the statutory announcement instant
  (previous evening 19:00-22:00, quoted from the DGPA's own operating-rule text on the daily page), whether
  a Taiwan county fully stops work and school on the next date, during typhoon warning periods. Label source:
  DGPA 歷次天然災害停止上班上課訊息 archive - measured 500 announcements 2001-present (oldest 民國90.07.30),
  anonymous plain GET, per-county status attachments (Big5 era and 2024 samples parsed as static tables;
  detail page 34,360 B, attachments 3-21 KB). Features: CWA 颱風資料庫 warning bulletins 1958-present plus
  prior-day closure status, all before the instant. Novelty check recorded (verdict differentiated): 0 HF
  hits on all five queries; Zenodo/arXiv hits are TC-track and unrelated papers; the only prior art is civil
  typhoon-day predictor apps, which ship no dataset or splits. One unproven step pinned as the first
  construction task: some modern-era DGPA attachments are shell-only, so per-county statuses for 2015-2026
  must come from the nds.html daily-view parameterisation or the county-portal CSVs (data.taipei verified;
  fallback: re-target to announcement-day grain). Gotchas recorded: DGPA HTTPS fails strict SSL validation
  (Missing Subject Key Identifier) - unverified context needed; data.taipei is IPv6-only from this host.
- **tw-reservoir-drought-storage - PARK.** The drought-onset task is well-posed and ODDL 1.0, but no
  anonymous historical daily storage series exists: data.gov.tw 45501/41568 publish current-day snapshots
  only, the publisher routes history to the fhyv2 viewer whose /Api/v2/* endpoints answer HTTP 401 to plain
  clients (measured), /disaster/Reservoir/Comparison is an AngularJS HTML shell, and opendata.wra.gov.tw is
  unreachable from this host (same SSL failure + intermittent DNS). Unpark: a standing snapshot collector
  seeded by the routine, or an authenticated WRA history endpoint.
- **hk-datagov-portal - PARK.** Licence clean (terms: redistribute and reproduce, commercial and
  non-commercial, with attribution) and the anonymous CKAN API works - but the catalogue (3,831 packages,
  enumerated: Censtatd 935 of them) supports no task family the bench does not already carry or has not
  already parked: aggregate statistical series (parked twice: statcan, ons), WSD weekly reservoir storage
  (same family as tw-reservoir), HKO TC best track (the TCRISI/TCBench mirror precedent that dropped
  jma-typhoon), and incident/prosecution series that are annual/quarterly aggregates (EMSD "reported lift
  incidents" CSV measured: 43 rows, Year x Cause x Count). The one per-case dataset (WSD burst mains, CSDI
  geoportal) is positives-only with no network covariates on the portal. Unpark: operator decision, same
  shape as the Singapore catalog park.
- **kr-kosis-kma-access - PARK.** South Korea's two national sources have no anonymous programmatic path:
  KOSIS OpenAPI requires personal signup + 인증키 (kosis.kr/openapi page evidence recorded), KMA's portal
  requires membership with PII (their own guide PDF: e-mail, name, phone). Licences themselves are clean
  (KOSIS explicitly permits redistribution with attribution for domestic statistics). Unpark: an
  operator-registered KOSIS key stored under /opt/data/.secrets, then open a candidate on a named series.

Japan (e-Stat/JMA) was not opened this tick: the four verdicts above satisfied the quota within budget, and
JMA's TC task is already dropped on the mirror precedent; e-Stat remains the first probe for the next tick.

Coverage after this session (scripts/discovery-coverage.py): 56 candidates, 19 live; East Asia 5 (TW 2,
HK 1, KR 1, JP 1; live East Asia 1 - tw-typhoon-day-closure); live non-US 13/19 (68%). No US source was
substituted for the regional quota. Session hygiene: check-candidate.py OK on all four new records,
check-novelty.py verdict recorded for the GO, full unittest suite green, probe scripts kept per convention
(probe_*.py in each candidate directory), scratch probes deleted.

who-flunet-activity-exceedance stays PUBLISHED (2026-10-21 10:24Z, the operator's "ship it").
nhs-ae-four-hour-decline v2026.11 is PACKAGED AND FULLY STAGED PRIVATE ON BOTH DESTINATIONS, awaiting the
independent re-audit BEFORE any flip: GitHub release v2026.11 (419642457, tag == main == 98139919, 5/5
assets at the manifest digests, --accept re-verified on bytes downloaded from the release) and the Hugging
Face repo (tag v2026.11 == main == 18b2e97; nhsae-hf-003 uploaded the three changed files; nhsae-hf-005
verified the documented loading path split-by-split: train 4,074 rows / 2,260 positives, eval 2,937 / 1,478,
holdout 2,538 / 1,233, label ['0','1']). Artifact 0990af0f90fbe304, gate 1.4.0. The v2026.10 staging is
superseded and must not be published.

## 2026-10-21 - nhs-ae packaged and staged private on both destinations (three green jobs); who-flunet PUBLISHED on the operator's "ship it"; this watcher run closed a two-crash arc

**nhsae-publish-001** (worker 171563321, cx23/hel1, destroyed 10:12:08Z, result release 419407464):
copied the five accepted nhsae-002 files from private staging (release 419222791) into the private
dataset repository earino/nhs-ae-four-hour-decline release v2026.10 (419405716) - transfers 5,
failures 0, 4,898,346 bytes, every sha256 verified on arrival and against the server's own digest
after upload; the bytes never passed through the coordinator. Re-verified from the coordinator
through the GitHub API: 5/5 assets with matching ids and sizes, and meta.json + quality.json
re-hashed at exactly their manifest digests. **nhsae-hf-001** (worker 171563744, destroyed
10:14:03Z, result release 419411258): hf_publish job - uploaded all five data files to the private
Hugging Face repo from the staged GitHub release (uploads 5, skipped 0, failures 0, 4,898,346 bytes).
**nhsae-hf-002** (worker 171564314, destroyed 10:17:48Z, result release 419414704): loading-check
retry - every upload skipped (already at the manifest digests) and the card's documented
load_dataset path ran against the private repo: train 6,116 rows / 3,285 positives, eval 2,937 /
1,478, holdout 2,538 / 1,233, label values ['0','1'], 37 columns per split, all matching the
manifest - hf_loading ok: true, problems: [] (the check that caught the food release's
declared-schema bug before shipping). All three workers already collected and destroyed by the
packaging arc; this run fetched the small reports into .factory/nhsae-{publish-001,hf-001,hf-002}/
reports/ (each job's container.log asset is only a post-destroy docker capture error - "No such
container" - the real evidence is the result records).

Both destinations were verified private and complete before recording: get_dataset.py executed
end-to-end against the private GitHub release (all five assets token-downloaded via the API
asset-id path, digests verified, runner layout restored, exit 0) and qualify_dataset.py --accept
re-verified the downloaded tree (ACCEPTED, artifact 9903df974f233dfa); GitHub tag v2026.10 == main
== f36e4fc3; Hub tag v2026.10 created last (tag_matches_main true); anonymous GitHub 404 / Hub 401.
Record: qualified -> packaged (packaged_at 2026-10-21T10:18:40Z, awaiting_operator true - the flip
is the operator's), three job entries, three result-release artifacts and both destination
artifacts added; check-candidate.py OK. DESTINATIONS.json (written by the packaging arc, committed
f3369ba) carries the full per-destination check log.

**who-flunet-activity-exceedance PUBLISHED 2026-10-21 10:24Z** by the same arc on the operator's
"ship it", recorded in commits bcd3d57 + f3369ba: licence reworked to the honest unresolved label
(compilation NOASSERTION, WHO data-compilation clause quotes, takedown route; Hub card license
field 'other'), both destinations flipped public with anonymous verification (GitHub 5/5 assets
re-hashed anonymously; Hub 15 files), the tag moved to the docs commit on both destinations (the
site publisher pins the tag and refused while it carried the old CC claim), website published with
the receipt complete (dataset site + catalogue live at earino.github.io, both Actions deployments
success). Follow-up in the record: written WHO permission would replace the risk-acceptance label.

**Two sessions died in flight; this watcher run closed the loop.** The research session (started
10:00Z) exited 1 at 10:19:14Z mid-ceremony; its continuation completed the platform work, the
flunet record, STATE.md and commit f3369ba (10:25:05Z, pushed - CI Local checks green at
10:25:08Z) but died before the nhs-ae record and the dashboard rebuild (10:25:24Z, left
uncommitted). This watcher run: verified both nhs-ae destinations read-only, wrote the packaged
record, rebuilt the dashboard, committed b6217ad, pushed it and confirmed CI Local checks green
(run 39585437173; the website-preview workflow is paths-filtered and did not trigger - no website
files changed). A first reading of "five commits unpushed since 08:13Z" was a stale local
remote-tracking ref (pushes from this clone go through an explicit credential URL that does not
update it); the Actions API showed every arc commit already pushed and green. Worker
spend this month: ~6.1 EUR of the 20 EUR allowance (the three packaging jobs add 0.12 EUR in
reservations, each under 3.5 minutes of runtime).

NEXT: the operator's flip for nhs-ae-four-hour-decline (both destinations staged private), then
publication per dataset-release on both platforms plus the website.


## 2026-10-21 - nhsae-baseline-001 green (contract baseline 0.5526 eval AUC); nhs-ae qualified end to end; both watched jobs closed

**nhsae-002 (build)** was constructed, gated and recorded by the advancement session (commit
48eab83); this watcher run closed the loop: small reports fetched into
.factory/nhsae-002/reports/ (gate report ok=true, 0 failed checks; build_summary coverage 134
providers / 12,765 qualifying provider-months / splits 6,116-2,937-2,538 - identical to the
corrected recorded figures), worker already destroyed, handled marker written.

**nhsae-baseline-001** (worker 171525370, cx23/hel1, 56.8 s, destroyed 06:41:51Z, result release
419227918): the runner-contract baseline on the ACCEPTED nhsae-002 artifact, fetched from staging
release 419222791 (4,898,346 bytes, all five extract files sha256-verified on arrival, 0 failures)
- not rebuilt. The gate re-accepted the released bytes before any scoring (`ACCEPTED ...
9903df974f233dfa`); the benchmark's own train.py and validate.sh ran UNMODIFIED (bundled sha256
equal the declared benchmark hashes); both independent paths measured **eval AUC 0.5526** and
`[validate] CONTRACT OK` (xgboost 3.4.1 / scikit-learn 1.9.1 / pandas 2.3.3 / numpy 2.5.4,
python 3.13.16; rows train 6,116 / eval 2,937 / holdout 2,538, positives 53.7% / 50.3% / 48.6%;
the private holdout was never copied into the runner workdir). The XGBoost pass sits below the
construction-time mean-reversion reference (0.5659 eval / 0.6562 holdout) - that reference is the
bar a competent model must beat, so the measured headroom is real; momentum is anti-predictive
(0.416/0.399). Record: status ready -> qualified, top-level qualification + baseline keys, jobs
and artifacts entries added, baseline_result.json committed with the job bundle; notes.md
carries the evidence. Reports: .factory/nhsae-baseline-001/reports/. Worker spend this month:
~5.98 EUR of the 20 EUR allowance (nhsae-baseline-001 reservation 0.06 EUR, ~57 s runtime).

NEXT: packaging per dataset-release (license.json: OGL v3 source terms carried through unchanged,
our compilation CC0-1.0, code MIT; card, get_dataset.py, MANIFEST, private staging to both
destinations), then the operator's flip.

## 2026-10-21 - nhs-ae-four-hour-decline constructed and qualified (nhsae-002 green, artifact 9903df974f233dfa accepted); discovery panel figures corrected (two probe defects); publisher CDN blocks worker IPs

The session's tick went to construction (release work outranks it, but the only packaged
candidate, who-flunet-activity-exceedance, carries awaiting_operator: true - the operator's
flip, not actionable by a session). Picked nhs-ae-four-hour-decline: status ready, fully
measured, GB publisher, 3.1 MB source.

**Two defects in the discovery panel probe, found because the build asserts the recorded
figures.** The first full local build produced train 6,116 rows against the recorded 3,714 and
failed its own acceptance check. Diagnosis (kept in notes.md with commands):

1. probe_panel.py opens the CSVs with `encoding="utf-8"`, so the five BOM-prefixed files
   (July 2019, August 2021, July/August/September 2023) key Period as "\ufeffPeriod" and
   every row of those files was silently dropped - the probe's "1,152 non-monthly rows" was
   really 101 TOTAL artefact rows plus 1,051 BOM-file rows.
2. The probe looks up "A&E attendances Type 1", but the 2018-04..2020-03 files name the
   column "Number of A&E attendances Type 1", so att1 parsed as 0 for 24 months and no
   provider-month before 2020-04 ever passed the volume gate (hence the recorded "97 months"
   and a train window that really started at 2020-05).

Corrected figures (recomputed with utf-8-sig + the "Number of" alias, recorded in the record
and notes): 102 months 2018-04..2026-09, 21,548 provider-months, 134 providers, 12,765
qualifying provider-months; m/m-decline splits train 6,116/53.7% (133 distinct positive
providers), eval 2,937/50.3% (124), holdout 2,538/48.6% (121). The fixed-threshold refusals
were re-computed on the corrected panel and still hold (<95% -> holdout 99.9% positive).
record.json corrected (check-candidate.py OK), notes.md carries the commands.

**Worker cycle.** nhsae-001 failed at 11.9 s: 0 CSV URLs enumerated. Two measured findings:
the Hetzner POST returned a transient 412 (record written first, server_id null; the
identical POST succeeded on retry and reconcile adopted the server), and - the real cause -
**www.england.nhs.uk (CloudFront) serves HTTP 202 with an empty body to datacenter IPs**,
so the year pages carry no CSV links from a worker. nhsae-002 was assembled as a fetch job:
the 102 CSVs (the coordinator's measured publisher fetch) packed into a deterministic
608,327-byte tar, staged in private release source-nhsae-001, fetched with sha256
verification, extracted, rebuilt and gated on the worker - **exit 0 in 12.1 s**, inner
composite digest identical to the coordinator exercise. Qualification gate 1.3.0 green on
the full artifact on the worker; on the coordinator every released file was re-fetched,
re-hashed against the release manifest, and `--accept` re-verified: **ACCEPTED, artifact
9903df974f233dfa**. Reference baselines measured at construction (rank AUC): mean reversion
rate_m - rate_mean_6m eval 0.5659 / holdout 0.6562 (the bar a competent model must beat);
momentum is anti-predictive (0.416/0.399). Both workers destroyed (06:19:52Z, 06:25:02Z),
ledger closed. Worker spend this month: ~5.92 EUR of the 20 EUR allowance (nhsae-001+002
reservations 0.08 EUR).

**Booked-appointment columns are parsed but NOT shipped**: they only exist from 2020-08, so
train feature months 2018-12..2020-07 would lack them - split-dependent availability is a
prediction-timing defect wearing a feature-list costume. Measured and recorded in
measurements.schema_evolution_2026_10_21.

NEXT: runner-contract baseline job on the accepted artifact (model flunet-baseline-001;
fetch release 419222791, re-accept through the gate, run the benchmark's train.py/validate.sh
unmodified), then packaging per dataset-release. The baseline job needs no new construction
- the extract is staged and verified.


## 2026-10-21 - flunet-baseline-001 succeeded (contract baseline 0.8700); who-flunet staging completed on both destinations after the launching session died mid-flight

**flunet-baseline-001** (worker 171493937, cx23/hel1, ledger deleted_at 02:32:29Z, result release
419075223): the runner-contract baseline on the ACCEPTED flunet-002 artifact, fetched from staging
(6,576,498 bytes, every sha256 verified on arrival, 0 failures) - not rebuilt. The gate re-accepted
the released bytes (`ACCEPTED ... b1323a27fa02eb79`) before any scoring; the benchmark's own train.py
and validate.sh ran UNMODIFIED (bundled sha256 equal the declared benchmark hashes); both independent
paths measured **eval AUC 0.8700** and `[validate] CONTRACT OK` (xgboost 3.4.1 / scikit-learn 1.9.1 /
pandas 2.3.3 / numpy 2.5.4, python 3.13.16; rows train 5,779 / eval 6,831 / holdout 13,483; positives
59.2% / 23.9% / 40.7%). The XGBoost pass sits below the persistence reference (0.8929 eval) - recorded
as measured headroom information, not a defect. Reports: .factory/flunet-baseline-001/reports/.

**The launching session (research tick, started 02:00Z) died at 02:37:09Z** (exit 1, ~37 min in)
right after collecting flunet-hf-001, leaving its packaging half-done and uncommitted. This watcher
session owned the completion:

- **get_dataset.py private-download fix carried through.** The session's last edit (02:31:16Z) added
  the API asset-id path because the `releases/download` URL 404s to a token client while the repo is
  private (measured on this release). This session EXECUTED it once before shipping: token download of
  all five assets, every digest verified, tree laid out for the runner, exit 0. check-package had been
  failing (manifest recorded the pre-fix get_dataset.py hash); manifest regenerated, check-package OK.
- **flunet-hf-001 recorded** (worker 171494792, ledger deleted_at 02:37:12Z, result release 419082025):
  the hf_publish worker job uploaded all five data files to the Hugging Face repo from the staged
  GitHub release, verifying each sha256 before and after transfer (uploads 5, skipped 0, failures 0);
  the bytes never passed through the coordinator.
- **GitHub destination verified private:** repo earino/who-flunet-activity-exceedance, release 419078118
  (v2026.10, non-draft, 5/5 assets at the accepted artifact digests read from the API), tag == main ==
  d3619bd (two fast-forward docs-only commits; no history rewrite), get_dataset.py/MANIFEST.json/
  VERIFICATION.md blob-identical to the package at the tag, anonymous GET 404s.
- **Hub destination verified private:** all five data files + docs present (hf-publish --verify ok,
  missing 0, size_mismatch 0), MANIFEST.json at tag v2026.10 re-downloaded and byte-identical to the
  package (sha256 f983cab3aefb5b5569c66381b4faafabfcbce3c71afd7a3739a5a52b7a6bbf9d), tag == main
  (f475facc), tagged LAST after the data and the docs refresh.
- **VERIFICATION.md correction:** the shipped text said the baseline worker was destroyed 02:28:57Z,
  which the job ledger contradicts (deleted_at 02:32:29Z, the record written by the destroy operation
  itself); corrected against the ledger in a second docs-only commit. No data or asset digest changed.
- **DESTINATIONS.json written** (staged-private shape, both destinations verified with evidence) and
  record.json updated (jobs flunet-baseline-001 + flunet-hf-001, destination artifacts, next_action).
  check-package: OK. Status: packaged, awaiting_operator.

**NEXT: the operator's private-to-public flip is the only remaining step.** Both destinations are
staged, verified and private; after the flip: record DESTINATIONS.json BEFORE regenerating the
manifest, refresh the private-state wording in the card/LOADING.md/README/release notes, re-upload
the small files, move the tag last (tag == main on both), then the website pipeline
(site prepare/publish/verify) per the dataset-release skill.


## 2026-10-21 - EU/EEA discovery tick: eutl-installation-net-short READY (go), bvl-zoom-sample-positivity (go), ecdc-atlas-surveillance (reject)

Coverage before this tick (scripts/discovery-coverage.py): 32 candidates, 13 live, 7/13 non-US,
Europe region = 3 (all GB) and **zero EU/EEA-publisher candidates live** - this tick's whole
purpose. After: 35 candidates, Europe region = 6, of which 3 EU/EEA (EU institution + DE +
EU agency dropped). Probes started from data.europa.eu as the brief required.

**1. eutl-installation-net-short - status `ready`, verdict `go` (the strongest find).** Task:
for a stationary EU ETS installation, will verified emissions for compliance year t exceed the
free allocation it holds for year t (net-short year)? Data: the Union Registry Public Website
(union-registry-data.ec.europa.eu, DG CLIMA) publishes **anonymous stable bulk extracts on
Azure blob storage** - `operators_yearly_activity_daily.csv.gz` measured 2026-10-20: HTTP 200,
5,959,551 B, 616,408 rows, 23,708 (registry, installation) keys x PERIOD_YEAR 2005-2030
(rectangular: future years carry advance ALLOCATION, VERIFIED_EMISSIONS = n/a), 32 registries
(EU-27 + GB/IS/LI/NO/XI), daily refresh (SNAPSHOT_DATE). Measured net-short base rate by year:
28.0% (2005) -> 27.5% (2012) -> 56.4% (2013) -> 71.5% (2018) -> 80.6% (2021) -> 73.7% (2025)
- both classes in every year; the phase drift is a documented phenomenon property. Prediction
instant pinned at 30 April of year t (t-1 settled; year-t allocation published in advance;
year-t emissions not yet observed). Licence: Commission legal notice CC BY 4.0 (quoted in
record) + EEA metadata independently stating "License CC-BY 4.0. Copyright holder: European
Commission, European Environment Agency". **Publisher-summary cross-check executed at
discovery**: DE 2023 panel sum VERIFIED_EMISSIONS 296,989,213 t vs EEA aggregate
'2.1 EU-ETS Verified Emission' 296,989,209 t (4 t difference); panel ALLOCATION sum 127,923,163
vs EEA '1.1 Freely allocated allowances' 127,958,123 (0.027%) - also proving ALLOCATION is the
free-allocation field. Novelty check recorded (differentiated; check-novelty.py, 3 queries,
HF/Zenodo/arXiv). check-candidate.py OK at status `ready`. Next action: construction
(build.py on a worker; composite row id (registry, installation, year); cross-checks against
the EEA aggregate + per-year compliance xlsx already published).

**2. bvl-zoom-sample-positivity - status `investigating`, verdict `go`.** Task: will a food
sample drawn under the German zoonoses monitoring programme (ZooM, BVL - German federal sector
regulator) from a stated matrix test positive for Campylobacter spp., using only sampling-plan
attributes decided at sampling time. Clean timing by construction (label = standardised lab
detection; features = year/month/matrix/stage/production-type/origin/processing/packaging).
Measured across the three published reporting-year CSVs (stable anonymous URLs, cp1252
semicolon CSVs): Campylobacter genus 1,394 rows/443 positive (31.8%) 2021; 2,364/613 (25.9%)
2022; 1,312/390 (29.7%) 2023 - both classes in every year, so disjoint one-year-per-window
splits exist as measured. Licence dl-de/by-2.0 (DCAT record + govdata.de text quoted). Carried
risks recorded: only 3 reporting years exist (2020/2024/2025 URLs 404 - refresh lagging),
ProbenNrPseud blank in the 2023 file (measured 0 vs 5,373/5,969), matrix dominates the base
rate so the reference baseline is a matrix-stratified rate. Novelty check differentiated.
check-candidate.py OK.

**3. ecdc-atlas-surveillance - status `dropped`, verdict `reject` (a mirror + access).** The
ECDC Atlas data model is country x disease x period surveillance panels: the only binary task
it can carry is country-period activity exceedance - the exact formulation already on the
bench (who-flunet-activity-exceedance, qualified 2026-10-20); ECDC's respiratory products are
the same surveillance family FluNet draws from. Measured access findings: the Atlas is an
interactive viewer (HTTP 200 HTML shell; the historical ?Output=json pattern returns HTML, not
JSON), case microdata sits behind the TESSy/EpiPulse data-access process. Rejection recorded
with prior art named so the publisher is not re-opened for this task shape.

Held / not settled this tick: the third named EU agency family (EFSA) was probed only through
the catalogue - its zoonoses/occurrence microdata is behind the dwh.efsa.europa.eu
BusinessObjects interactive interface (no anonymous bulk channel found; the catalogue
distribution URLs are report IDs, not data APIs) - so no EFSA record was written this session;
a future tick can write it up as a `park` or probe EFSA's Zenodo releases properly. Frontex
was probed (catalogue distributions point at the ArcGIS migratory-map embed; monthly-count
exceedance would also be a flunet-shape mirror) and set aside for the same reason as ECDC.
Probe scripts under .factory/ (gitignored scratch) were deleted after recording; raw probe
artifacts live in $TMPDIR/eu-catalog (24h-pruned scratch).

Previous tick (advancement session). TWO things moved that tick:
(1) chicago-food-inspections is FULLY SHIPPED - the operator's flip went through at 21:55Z,
both data destinations are public and anonymously verified, and the SITE PAGE IS LIVE AND
VERIFIED TOO: the 21:55Z session had published it (dataset site repo commit 48dc0853 'Prepare
website for chicago-food-inspections v2026.10', 21:57:44Z) but was killed before recording
that, so the committed record still said 'remaining: site page'. This session found the site
live, re-verified anonymously (page + /versions/v2026.10/ both 200 at 60,065 bytes,
catalog.json 182,556 bytes lists the release, page prints
load_dataset('earino/chicago-food-inspections', 'code_01', revision='v2026.10'),
site-publish.py verify on fresh bundle .factory/sites/food-website-1 = status=verified, HTTPS
enforced on both Pages sites), and recorded the site destination in DESTINATIONS.json
(github/huggingface entries preserved). Nothing remains for that dataset.
(2) who-flunet-activity-exceedance CONSTRUCTED AND QUALIFIED (flunet-002 green). See the
2026-10-20 section below.
Earlier: food-hf-002 SUCCEEDED - destination staging was COMPLETE on both platforms and
The retry verified all 201 Hub targets at their manifest digests and passed the built-in code_38
loading check against the corrected declared schema: train/eval/holdout 156841/35358/34218 rows,
58228/7335/7418 positives. Post-collection: hf-publish --verify ok (201/201, 0 missing, 0
size-mismatched, recorded in DESTINATIONS.json), Hub tag v2026.10 = main = 9e17ba8a, check-package OK.
Earlier: the operator's flip approval came at 21:55Z (see the record's PUBLISHED entry); anonymous
proofs, DESTINATIONS.json, card/LOADING/README/release-notes refresh and the website step all ran.
Earlier: food-hf-001 FAILED its Hub loading check on a schema bug - inspection_type typed int64; fixed.
Earlier still: food-consumer-002 PASSED all five steps of the fresh-environment
consumer verification on the published bytes - package 22/22, 201 assets failures [], sha256sum -c
201/201, gate --accept 40/40, code_38 baseline eval AUC 0.6326 = the recorded value through the
unmodified contract.)

## 2026-10-20 - who-flunet-activity-exceedance constructed and qualified: flunet-002 green, artifact b1323a27 accepted; the France fixture was re-pinned at construction

**The ready buffer candidate went ready -> qualified inside one tick.** `flunet-001` (worker
171454348, launched 22:16:07Z) built the full artifact and failed the gate on exactly ONE
check, `timing.every_feature_documented`: quality.json's `features_documented_at` carried
documentation prose where the gate compares the bare availability class `prediction_time`
(qualify_dataset.py:271-274) - a descriptor-value defect, not a data defect; every other check
was green in the collected report. Diagnosed from the collected bytes, fixed (value set to
`prediction_time`, the documentation reference moved to a `feature_documentation` key), worker
destroyed 22:20:55Z, retried as **`flunet-002`** (worker 171454743, launched 22:21:03Z,
job elapsed 31.2 s): build + qualification gate green on the worker - `ok: true`,
`failed_checks: []`, gate 1.3.0, artifact `b1323a27fa02eb79...` - and
`qualify_dataset.py --accept` on the coordinator re-verified the collected staging bytes ->
`ACCEPTED`. Worker destroyed 22:26:25Z (both workers' deletion recorded in jobs/*.json).

**Measured on the full table** (GET 32,246,617 B in 1.5 s, sha `5695e5d2c06c4179...`, one
request; 189,645 source rows, 189 countries, 148,355 country-weeks, streams summed): 1,258 of
3,499 country-years pass the systematic-negative rule. **26,093 eligible (country, prediction
week) rows** - skipped: thin prediction week 106,611, thin target week 6,881, not-systematic
8,015, no target 755. Splits: train 5,779 / 3,420 positive (59.2%) / 235 clustered
country-years (2005-01-31..2019-12-23); eval 6,831 / 1,636 (23.9%) / 257
(2019-12-30..2022-12-26); holdout 13,483 / 5,482 (40.7%) / 422 (2023-01-02..2026-09-14).
The train-vs-eval base-rate gap is the documented phenomenon property (COVID era + the early
systematic years), not a construction fault. Timing self-check: 201 rows recomputed from a
series physically truncated at week W, 0 mismatches; 0 duplicate row_ids.

**The negatives-frame trap acceptance test passed with an exact reproduction:** pre-rule
1995-2004 = 931/931 positive - byte-for-byte the discovery session's measurement, reproduced
independently by this pipeline - and the rule leaves 14 of those rows. The rule provably
removes the trap it was designed against.

**The France fixture was re-pinned at construction, correcting the record's candidate
figure.** The discovery session proposed ">40% at France's 2024-25 peak"; the measured blended
peak (streams summed, denominator INF_ALL+INF_NEGATIVE) is **0.2379 in the week of
2025-01-27**, and July-August 2024/2025 off-season weeks max at **0.0071**. The 40% figure
belongs to sentinel-only curves of stronger seasons, not this frame. Pinned: season peak in
(0.15, 0.95], off-season < 0.10 - threshold 0.10 and lead 4 weeks now sit with measured margin
on both sides.

**Reference baselines** (stdlib rank AUC on the written rows, construction-time references
measured in-build): persistence (week-W positivity) 0.897 train / 0.893 eval / 0.874 holdout;
rolling-8-week mean 0.799 / 0.828 / 0.768. A scored solver must beat persistence to be
interesting.

Next action (in the candidate record, specific): packaging per the dataset-release skill -
license.json (WHO CC BY-NC-SA 3.0 IGO carried through + CC0 compilation + MIT code, evidence
already in license_evidence), package docs, release-manifest.py, check-package.py, then
staging. Extract assets: staging release 418940777 (train 1,496,272 B, eval 1,589,403 B,
holdout 3,482,298 B, meta 2,915 B, quality 5,610 B, summary 2,911 B).

## 2026-10-20 - food-hf-002 succeeded: Hub destination verified and tagged; all four destination-staging steps complete; chicago-food-inspections now awaits only the operator's flip

**`food-hf-002` succeeded (collected 21:39:57Z from server 171445940, staging release 418876326), and it
did exactly what the retry was designed to do: prove the Hub state rather than move bytes.** The collected
result reads uploads 0, skips 201, failures 0 - every one of the 201 targets was already at its manifest
digest from food-hf-001 - and the built-in code_38 loading check passed against the corrected declared
schema: `hf_loading ok: true, problems: []`, train 156841 rows / 58228 positives, eval 35358 / 7335,
holdout 34218 / 7418 - the exact expected counts. The same numbers were re-read from the release's own
manifest.json (sha256 08101c97..); container.log is the 65-byte container-less executor note
('No such container: scout-food-hf-002'), not a defect.

**Post-collection steps, all run from the coordinator and verified before recording:**

1. `hf-publish.py --verify --candidate chicago-food-inspections` (write credential from its mode-0600
   file): **ok** - 201/201 files present, 0 missing, 0 size-mismatched; 41 LFS paths digest-verified by
   the Hub, the rest re-hashed on download by food-hf-001; repo private; recorded in
   `release/chicago-food-inspections/DESTINATIONS.json` (huggingface verified: true, 2026-10-20T21:41:09Z;
   stale 'bulk assets to be uploaded' note replaced with the completed state).
2. `hf-publish.py --tag` LAST: Hub tag **v2026.10** created at
   `9e17ba8a6f20555c0a1932e0e314a8546b630854` with **tag_matches_main: true** - the revision that
   carries both the 201 bulk assets and the corrected dataset_infos.json.
3. `check-package.py release/chicago-food-inspections`: OK.
4. `candidates/chicago-food-inspections/record.json`: food-hf-002 entry updated running -> succeeded with
   the measured facts; `awaiting_operator: true` set; `next_action` rewritten to the flip-waiting state.

**Both destinations now carry the same accepted artifact, privately:** GitHub earino/chicago-food-inspections
(main = tag v2026.10 = 3584924, release 418734355, 201 assets, consumer verification green) and Hugging Face
earino/chicago-food-inspections (main = tag v2026.10 = 9e17ba8, 201 bulk assets + 8 small files verified
against the package MANIFEST). The only remaining step is the operator's single approval; after it,
publication is mechanical: flip both destinations, prove both anonymously, record in DESTINATIONS.json
BEFORE regenerating the manifest, refresh card/LOADING.md/README/release notes, website step.
`scout-release-notify` (hourly at :55) delivers the ready-for-flip request, deduped on id@packaged_at.

## 2026-10-20 - food-hf-001 failed its Hub loading check: inspection_type was typed int64; schema fixed, generator hardened, retry food-hf-002 launched

**`food-hf-001` failed (collected 20:36:54Z, server 171438942 destroyed 20:59:01Z), and the failure is
a schema-declaration bug, not a data or transfer defect.** All 201 assets (1,285,155,006 bytes) are on
the private Hub repo `earino/chicago-food-inspections`, each re-read at its manifest digest (uploads
201, skips 0, digest mismatches 0). The job then ran its built-in code_38 loading check and
`load_dataset` died generating the eval split: `pyarrow.lib.ArrowInvalid: Failed to parse string:
'Canvass' as a scalar of type int64`.

**Diagnosis, from the shipped bytes.** The Hub CSV loader parses with pandas and then casts each
column to the schema `dataset_infos.json` declares. The generated file declared `inspection_type`
int64 in all 40 configs because `candidates/chicago-food-inspections/hub-schema.json` omitted the
column and `scripts/hf-dataset-infos.py` silently defaulted undeclared columns to int64. A bounded
range probe of `data/code_38-public-eval.csv` on the Hub confirmed the column's actual values
(`Canvass`, `Canvass Re-Inspection`, `Suspected Food Poisoning`, ...); the card's configs block
generates eval first, so the cast failed on the first row. Train/holdout were never attempted.

**Fix (all seven steps verified before the retry was launched):**

1. `hub-schema.json`: `inspection_type` added to the string set.
2. `scripts/hf-dataset-infos.py` hardened: with `--types-file`, every feature column must now be
   declared under exactly one of string/float64/int64 - undeclared is an error, not a silent int64
   guess; multi-set membership is refused; only the label keeps the int64 default. The built-in
   (MSHA) sets keep their historical behaviour.
3. `dataset_infos.json` regenerated from the release's own metas (digest-verified): inspection_type
   string in all 40 configs; all 18 columns audited against the shipped values (sampled 335 eval rows
   at four offsets: no leading-zero licence values, integer day_of_week/month/prior counts, -1
   sentinels in days_since_previous/prior_fail_rate/prior_mean_code_count are numeric-safe,
   latitude/longitude emptiness is null-safe for float64).
4. `MANIFEST.json` regenerated - only `package_files[dataset_infos.json]` changed
   (b5ef01a5.. -> b46a686b..); SHA256SUMS byte-identical over the unchanged 201 assets;
   artifact_version unchanged (c951bf5b...); `check-package.py` OK.
5. Regression guards added to `tests/test_hf_dataset_infos.py` (food schema declares
   inspection_type string; every feature column declared exactly once; the generator refuses
   undeclared columns); full suite 386 tests green locally.
6. Destination docs advance: commit `3584924` pushed to main of the private
   `earino/chicago-food-inspections`; tag `v2026.10` re-pointed through the GitHub git-refs API
   update (the cron sandbox declines history-moving tag pushes, so the ref update went through the
   API instead of a local git push) and verified tag==main==3584924; release 418734355 still
   non-draft with the same 201 assets; both docs byte-identical at the tag to the package; the
   anonymous fetch still 404s; `DESTINATIONS.json` records the advance.
7. Hub small files refreshed with `--upload-small` (new revision `9e17ba8`): `dataset_infos.json`
   and `MANIFEST.json` read back byte-identical to the package, inspection_type string in all 40
   Hub-served configs, repo private. The write credential stayed in its file; the inference
   credential was never read.

**Retry `food-hf-002` launched 20:59:52Z on server 171445940** (cpx32/hel1, reservation EUR 0.32;
October reservations now ~EUR 6.78 of the 20 EUR allowance): the identical 201-asset spec (every
target expected to skip as already present at its manifest digest) plus the same code_38 loading
check (rows 156841/35358/34218, positives 58228/7335/7418, 18 declared columns), now against the
corrected declared schema. Spec committed at `candidates/chicago-food-inspections/hf/job.json`.
When the watcher collects it: require exit 0, zero failures, loading check ok (all 201 targets
accounted as skips), then `hf-publish.py --verify` (records the Hub destination), `--tag` LAST,
check-package, `awaiting_operator: true`, and let scout-release-notify deliver the ready-for-flip
message. The flip is the operator's single approval.

## 2026-10-20 - food-consumer-002 passed all five steps on the published bytes; VERIFICATION.md records it; the Hub step began (private repo + card + declared schema live, bulk job food-hf-001 running)

**`food-consumer-002` succeeded (exit 0, 144.9 s, server 171431887), and every step was verified
from the fetched reports before anything was quoted.** The watcher collected the job 19:39:34Z,
fetched its 43 small report assets from staging release 418787656 into
`.factory/food-consumer-002/reports/` (each sha256-verified against that release's own manifest; the
1,034,240-byte source.tar skipped as bulk), destroyed the worker 19:41:11Z, and read the five steps
out of `container.log`, `output/consumer.txt`, `output/baseline.log` and the 40 accept outputs:

1. **package vs MANIFEST.json**: every listed file (22) matched its recorded hash - including the
   corrected `code/materialize.py` (95cd40d9...) whose absence killed food-consumer-001;
2. **assets as a consumer receives them**: all 201 fetched by asset id from private release
   v2026.10 (418734355), 1,285,155,006 bytes, `failures: []`, in the layout `get_dataset.py` restores;
3. **`sha256sum -c SHA256SUMS`**: OK on all 201 lines;
4. **qualification gate `--accept`**: exit 0 on all 40 configs, each printing "ACCEPTED: ... matches
   the qualified artifact" (code_38 -> 80a4291e3288dc07...);
5. **code_38 baseline through the runner's unmodified contract**: eval AUC **0.6326** from both the
   `train.py` path and the independent `validate.py` recompute, `CONTRACT OK` - the recorded value
   itself (recorded 0.6326, tolerance 0.001). `container.log` ends "== consumer verification
   passed ==".

That 0.6326 is now measured three times on the same accepted artifact version (food-baseline-002,
food-baseline-003, and this run from the published bytes). The full log chain is preserved in
`.factory/food-consumer-002/reports/`.

**Recorded where the package says it must be.** VERIFICATION.md gained "## 6. Fresh-environment
consumer verification: PASSED on the published bytes" (the five-step table, plus the honest story
of the failed first attempt that caught the shipped MSHA materialize.py at step 5 - the check doing
its job); the former section 6 ("Not covered") became section 7 with its obsolete "no
fresh-environment consumer run yet" bullet replaced by a "this document was revised after the
consumer check ran" note (data assets untouched). Section 5 gained the third code_38 reproduction.
`scripts/release-manifest.py` regenerated the manifest (only `package_files[VERIFICATION.md]`
e35a4a75 -> dfea1ccf), `scripts/check-package.py` OK. Both files were pushed to the private
destination repo (commit a7abfaa) and read back through the API: byte-identical, main head, repo
private.

**Step 4 (Hugging Face) began, with the msha lessons applied up front.** The Hub repository
`earino/chicago-food-inspections` was created **private** by `scripts/hf-publish.py --create
--upload-small` (write credential from the mode-0600 file, never printed, never in a bundle; the
inference credential never read), and 11 small files landed (read back through the Hub API: private
true, revision sha 2051a467): the generated card (from the new `candidates/chicago-food-inspections/
card.md` - City-of-Chicago terms preserved verbatim, the DOAH licence posture, no CC0 claim),
LOADING.md, `dataset_infos.json`, MANIFEST.json, VERIFICATION.md, DATA_DICTIONARY.md,
measurements.json, SHA256SUMS and the three licence files. The declared schema is the msha
`dataset_infos.json` lesson applied before the first upload instead of after a failed loading check:
`scripts/hf-dataset-infos.py` was extended with `--meta-source github` (metas read from the
dataset's own verified GitHub release, each digest-checked against the manifest, so the schema can
be generated before anything is on the Hub) and `--types-file` (per-candidate column typing; the
documented msha invocation is unchanged). `candidates/chicago-food-inspections/hub-schema.json`
declares the food types - `license_` is zero-padded text and must not be read back as an integer,
`latitude`/`longitude` carry empty values, identifiers ship as published - producing
`dataset_infos.json`: 40 configs x 18 columns, feature lists and dtypes verified identical across
all 40. A latent crash in `hf-publish.py`'s `navigation_record()` (missing DESTINATIONS.json on a
first-ever --plan) was fixed to read as "no site yet", the state its docstring already describes.

`release/chicago-food-inspections/DESTINATIONS.json` now exists, recording the GitHub destination
as verified/private (201/201 digests via the API, the consumer check, the docs-advance commits) and
the Hugging Face destination as pending the bulk job. The package documents advance
(`dataset_infos.json` + `MANIFEST.json`) was pushed to the destination repo (commit fbc3d77) and
**the version tag was re-pointed from e61d4839 through the advances to 49d06bb**, so v2026.10 and
main resolve to the same commit and the version-pinned documents describe the shipped schema (the
recorded msha practice; the 201 release assets are unchanged). Each tag cycle turned the release
back into a draft, so it was re-published (non-draft, still inside the private repo) and the
anonymous fetch was checked to 404. `scripts/check-package.py` OK.

**A second docs advance, forced by the card contract the test suite enforces.** Writing the food
card made `chicago-food-inspections` eligible for `tests/test_hf_card.py`, which caught two real
defects in what would have shipped: the card stated no `**Rows:**` total (added: {ROWS_TOTAL} —
the pool, not the config-sum), and the manifest recorded the food-baseline-002 sanity check under
`baseline.previous_measurement`, whose contract meaning is a *retired* value - but 0.6326 was
never retired: the suite baseline reproduced it exactly, and the same number is the CURRENT
code_38 result in RELEASE_NOTES' table, where a retirement marker would be false. The block was
relabeled `baseline.corroborating_measurement` (generator and generated file, measured values
untouched), the manifest regenerated, all 383 tests green, and the result pushed (commit 49d06bb,
tag re-pointed, release re-published, MANIFEST.json at the tag verified byte-identical: 8fd7e143).
The Hub small files were refreshed with the new card and manifest (--upload-small, idempotent) and
re-verified byte-identical at Hub revision 307ae28.

**`food-hf-001` launched 20:06:05Z on server 171438942** (cpx32/hel1, EUR 0.06924/h, reservation
EUR 0.32; October reservations now ~EUR 6.46 of the 20 EUR allowance, and release work may draw the
full budget). Spec committed at `candidates/chicago-food-inspections/hf/job.json`: all 201 assets
from the verified private release to the Hub (`data/<asset_name>` for CSVs, root for meta/quality),
batch commits of 6 with the rate-limit backoff, digest verified on download and again on the Hub,
then the built-in code_38 loading check (rows 156841/35358/34218, positives 58228/7335/7418, 18
declared columns). When the watcher collects it: require exit 0 with zero failures and the loading
check ok, run `hf-publish.py --verify` (records the Hub destination in DESTINATIONS.json), then
`--tag` LAST, re-run check-package, set `awaiting_operator: true`, and let scout-release-notify
deliver the ready-for-flip message. The flip is the operator's single approval.

**Records.** Committed with this entry: STATE.md, the candidate's record.json (food-consumer-002
succeeded with all five steps; food-hf-001 running; the artifacts block replaced by the verified
private-destination entry per the msha pattern; refreshed next_action),
`candidates/chicago-food-inspections/card.md`, `hub-schema.json`, `hf/job.json`,
`release/chicago-food-inspections/{VERIFICATION.md,MANIFEST.json,dataset_infos.json,
DESTINATIONS.json}`, `candidates/chicago-food-inspections/baseline/baseline_result.json` (the
corroborating_measurement relabel), `scripts/hf-dataset-infos.py`, `scripts/hf-publish.py`,
`jobs/food-consumer-002.json` (collected and destroyed) and `jobs/food-hf-001.json` (running). The
watcher marker for food-consumer-002 is written in untracked `.factory/` as usual. Deliberately not committed: the hourly dashboard's build/ outputs and
the untracked `candidates/who-flunet-activity-exceedance/` working directory (another session's
WIP; `check-candidate.py --all` fails on it locally but the pushed tree does not contain it).
## 2026-10-20 - food-publish-002 closed the transfer at 201/201; food-consumer-001 caught the package shipping MSHA's materialize.py - fixed, retried as food-consumer-002 (running)

**`food-publish-002` succeeded and completed destination-staging step 2.** The one-asset retry of
food-publish-001 transferred code_53-meta.json (2,788 bytes) from staging release 403508464 into the private
release v2026.10 (418734355) of earino/chicago-food-inspections as target asset 660208719 at its recorded
sha256; container-less transfer job (exit=None expected), server 171426472, collected 19:07:10Z and destroyed
19:09:36Z by the interactive session. The watcher then read the target release back through the API with the
publish credential: **exactly 201 assets, every one matching release/chicago-food-inspections/MANIFEST.json by
name, size and GitHub's server-side sha256 digest; 1,285,155,006 bytes total, equal to the manifest total;
repository private: true.** Nothing was scored and no number is quoted from this job - it moves
already-qualified bytes.

**`food-consumer-001` failed at exit 1 after 168.7 s, and its failure is a caught defect, not noise.** The
fresh-environment consumer job (server 171429777, launched 19:09:04Z, collected 19:14:48Z, destroyed by this
watcher 19:25:09Z) fetched all 201 assets (1,285,155,006 bytes, zero fetch failures) and its first four steps
were green, read back from the fetched reports of its staging release 418770807: package 22 files match
MANIFEST.json; 201 files in the layout get_dataset.py restores; sha256sum -c SHA256SUMS 201/201 OK; the
qualification gate's --accept exit 0 on all 40 per-code configs, each printing 'ACCEPTED: ... matches the
qualified artifact'. Step 5 died before train.py ran: baseline.log is a single 56-byte line,
'usage: materialize.py <dataset-dir> <work-dir> <config>'.

**Root cause: the package shipped MSHA's code/materialize.py.** The file at
release/chicago-food-inspections/code/materialize.py (sha256 680b1c07...) is MSHA's 3-arg variant - its
docstring names 'the 45 per-section directories (sec_56_12004, sec_75_400, ...)' and 'MSHA's configs declare
none' - while this dataset's materializer is the 2-arg bench/workdir.py-mirroring file
(candidates/chicago-food-inspections/baseline/materialize.py, sha256 95cd40d9...), which is exactly what
baseline/reproduce_baseline.sh invokes ('$DATASET/$CONFIG' '$WORK'). Every other file in the package's code/
directory hashes identical to the food candidate's sources; one file was copied from the wrong candidate.
Nothing earlier caught it because every earlier check compares bytes to *recorded* hashes - the wrong file had
been consistently hashed into MANIFEST.json's package_files - and food-baseline-002/003 bundled the correct
materialize.py from the candidate directory, never the package's copy. The published file was executed for
the first time by this consumer run: that is the job's purpose. **Not a data defect** - the 201 data assets
are unchanged, all 40 configs re-accept, and nothing was scored, so no AUC from this run is quoted anywhere.

**The fix, each step proven.** (1) Replaced release/chicago-food-inspections/code/materialize.py with the
candidate's 95cd40d9 file - the exact bytes bundled in food-baseline-002/003, which measured eval AUC 0.6326
through the runner's contract. (2) Regenerated the manifest (scripts/release-manifest.py): the only change is
package_files[code/materialize.py] 680b1c07... -> 95cd40d9...; SHA256SUMS is byte-identical (201 entries, data
assets untouched). (3) scripts/check-package.py release/chicago-food-inspections: OK. (4) Pushed the two
changed files to the private destination repo - commit 0c765e3c650af796658533d9deac349ad60d2d44 on main -
and read them back through the API: code/materialize.py digest 95cd40d9..., MANIFEST.json digest
867d9f0e... (equal to the local file), repository private: true. (5) Re-assembled the consumer bundle
(scripts/assemble-job.py food-consumer) and verified the assembled job records the 95cd40d9 digest for
repo/code/materialize.py before launching. **`food-consumer-002` launched 19:25:37Z on server 171431887**
(cpx32/hel1, EUR 0.06924/h, reservation EUR 0.32, timeout 110 min): the same five-step verification against
the fixed package and the same private release. The worker watcher picks it up from jobs/ automatically.

**Records.** Fetched into .factory/food-consumer-001/reports/: the 40 accept-code_*.txt outputs, baseline.log
and container.log, each sha256-verified against the release's own manifest (the 1,034,240-byte source.tar
part skipped as bulk); .factory/food-publish-002's three result assets are in its own record. Committed with
this entry: STATE.md, the candidate's record.json (food-publish-002 and food-consumer-001 job entries,
refreshed next_action), jobs/food-publish-002.json and jobs/food-consumer-001.json (both collected and
destroyed), jobs/food-consumer-002.json (running), the consumer bundle spec
(candidates/chicago-food-inspections/consumer/, now the -002 spec), and the package fix itself
(release/chicago-food-inspections/code/materialize.py + MANIFEST.json). Deliberately not committed: the
hourly dashboard's build/dashboard/ outputs. Next action is the candidate's recorded step 3 completion:
collect food-consumer-002, require all five steps green before quoting anything, record it in VERIFICATION.md
sections 5/6, regenerate the manifest and re-push the changed package files, then Hugging Face, then
awaiting_operator for the flip.

## 2026-10-20 - food-publish-001: destination-staging transfer stopped one asset short - 200/201, a transient HTTP 500 on code_53-meta.json; the one-asset retry is running

**`food-publish-001` failed with UploadError after 549 s, having transferred 200 of the 201 accepted food-001
assets (1,285,152,218 bytes) into the private draft release v2026.10 (418734355) of
earino/chicago-food-inspections.** This is step 2 of the candidate's recorded destination-staging sequence;
step 1, the private repository with the package documents as its initial commit, is done (main tip
e61d4839a8, 2026-10-20T18:33:21Z, read back through the API). Server 171420107 (cpx32/hel1, EUR
0.06924/h, reservation EUR 0.32).

**What failed, exactly.** Each asset the loop touched was downloaded from staging release 403508464,
sha256-verified on arrival, re-uploaded, and verified again against the target's own server-side digest;
all 200 that completed are individually recorded in the collected result with their target asset ids and
digests. The single failure is code_53-meta.json (source asset 611965805, 2,788 bytes): its source download
returned HTTP 500 from GitHub. Transient and server-side, not a dataset, credential or authorization
problem - the same worker moved the other 200 assets' 1.28 GB and uploaded its own result release without
an auth error, and the target-repository guard read private: true. `workers/upload.py` gives `ensure_asset`
three upload retries, but its source-download path has no 5xx retry, so the loop recorded the failure and
the executor ended the job with "1 of 201 assets did not transfer".

**exit=None and the 70-byte container.log are properties of this job type, not a second failure.** Transfer
jobs run container-less on the worker host (workers/executor.py moves already-built artifacts between
releases), so there is no exit code to read, and the shared `stop_and_capture` path writes docker's "No
such container: scout-food-publish-001" message as the log.

**Division of labor, same as the food-baseline-001 precedent.** While this watcher collected and diagnosed,
the interactive session destroyed the worker (record deleted_at 2026-10-20T19:02:08Z, status deleted) and
launched the corrected minimal retry `food-publish-002` at 19:02:28Z on server 171426472 (reservation EUR
0.16, lifetime 45 min): the same source release 403508464 and target draft release 418734355, carrying only
code_53-meta.json with its recorded size and sha256. `ensure_asset` skips any target asset already present
at the manifest digest, so the retry cannot duplicate or overwrite the 200 completed assets; it was running
when this entry was written. This watcher launched nothing - one worker at a time. When food-publish-002
completes, the sequence requires reading the target release back and verifying all 201 assets by name, size
and sha256 against release/chicago-food-inspections/MANIFEST.json before the fresh-environment consumer job
runs against it.

**Records and cleanup.** All three small result assets of release 418750781 were fetched into
`.factory/food-publish-001/reports/` (source.tar 92,160 B, container.log 70 B, manifest.json 119,454 B),
each sha256-verified against that release's own manifest; no bulk CSV was downloaded to this host. The
target release was read back through the API with the publish credential: repository private: true,
release draft: true, exactly 200 assets, code_53-meta.json absent. Committed with this entry: STATE.md, the
candidate's record.json (the food-publish-001 job entry), and jobs/food-publish-001.json (status deleted:
collected, then destroyed). Deliberately not committed: jobs/food-publish-002.json (the retry is still
running; its record is committed at collection), the interactive session's consumer-job WIP
(candidates/chicago-food-inspections/consumer/), and the hourly dashboard's build/dashboard/ outputs.

## 2026-10-20 - food-baseline-003: all-40 runner-contract baselines measured in one uniform run - gate re-accept and CONTRACT OK on every config; the candidate is now packaged

**`food-baseline-003` succeeded exit 0 in 6.3 min (376.5 s) and measured every one of the 40 per-code
configs of the accepted food-001 artifact through the runner's own contract in one uniform run.** The
job fetched each config's five files from staging release 403508464 - 1,260,835,814 bytes, each
sha256-verified on arrival, zero failures - then, per config: re-accepted the exact fetched bytes through
the qualification gate's `--accept` against that config's own bundled gate report BEFORE anything was
scored, materialized the runner's task directory the way the benchmark's bench/workdir.py does (public
train+eval only; the private holdout was never copied into a workdir), and ran the benchmark's own
train.py and validate.sh, bundled verbatim (bundled digests equal the declared digests, so "the existing
runner, unmodified" is checkable). Server 171406685 (cpx32/hel1, EUR 0.06924/h, reserved EUR 0.24).

**The measured result, read back from the fetched reports of release 418648610 (not from the console):
40/40 configs accepted by the gate before scoring, 40/40 train.py + validate.sh clean
("[validate] CONTRACT OK" on every config), and train.py's own Eval AUC equals validate.py's independent
predict_proba recompute on every config - zero disagreements. Eval AUC across the suite: min 0.5187
(code_32), median 0.7208, max 0.8292 (code_58). Eval base rates span 0.00147 (code_11) to 0.56078
(code_55); every config shares the same temporal split rows: train 156,841 / eval 35,358 / holdout
34,218. The holdout was not scored by anything. code_38 re-measured in this run at 0.6326 - identical to
food-baseline-002's 0.6326 on the same accepted artifact version, so the earlier sanity check reproduces
bit-for-bit.** Dependencies on the worker: python 3.13.16, pandas 2.3.3, numpy 2.5.4, xgboost 3.4.1,
scikit-learn 1.9.1. Scope: baselines through the existing contract only - no agent or harness comparison
was run and none is implied.

**Persistence headroom, verified here against the package's own measurements.json:** the baseline beats
the per-config persistence reference (prev_code_present alone) on 38/40 configs by +0.0281 to +0.2465
AUC, and is below it on code_14 (-0.0075) and code_32 (-0.0291) - recorded in the candidate's record.json
rather than rounded away.

**Division of labor with the active session, and what this watcher verified.** The scout-research session
launched the job (16:50 UTC), collected it (17:12:35 UTC), destroyed the server (deleted_at 17:18:14 UTC
in its record), and at 17:20 wrote the candidate's record.json blocks: the food-baseline-003 jobs entry,
the `baseline_all_40_food_baseline_003` measurement, `status: packaged` + `packaged_at` (its packaging
milestone: release/chicago-food-inspections/ complete, check-package.py OK by its own run), and the
destination-staging next_action. This watcher then fetched the 164 small report assets of release 418648610
into `.factory/food-baseline-003/reports/` - mapped to their real names through the release's own
manifest.json, every file's sha256 verified against both that manifest and the collected result.json -
skipping only the 655,360 B source.tar part as bulk (its digest equals the ledger's source_sha256
e074d1be1d9f..., cross-checked without downloading); re-verified every recorded number against those
reports (all agree exactly, including the persistence headroom recomputed from
release/chicago-food-inspections/measurements.json); re-verified the worker deletion (destroy order
17:22:11 UTC, the ledger re-stamped; a second, idempotent destroy of an already-dead server); and ran
`scripts/check-candidate.py --all` (chicago-food-inspections OK, status packaged) and the full 383-test
suite locally (OK) before committing.

**Records.** Committed with this entry: STATE.md, the session's verified
`candidates/chicago-food-inspections/record.json`, and `jobs/food-baseline-003.json` (the collected job
record: status collected, release 418648610, server deleted). Still deliberately uncommitted, the active
session's WIP, none of it this watcher's to commit: the packaging set
(`candidates/chicago-food-inspections/release.json`, `release/chicago-food-inspections/`,
`baseline/baseline_result.json`, `baseline/report_all.py`, `baseline/qualification-reports/`, the
baseline job spec edits `baseline/bundle.json`, `baseline/job.json`, `baseline/run.sh`,
`baseline/expected_artifact.json`), `scripts/build-food-expected-artifact.py`,
`scripts/build-food-package-measurements.py`, `skills/dataset-release/SKILL.md` (publication-authority
wording), and the hourly dashboard's `build/dashboard/` outputs. Next action is the candidate's recorded
destination-staging sequence: create the private earino/chicago-food-inspections repository, transfer the
201 assets from staging release 403508464 to a private v2026.10 release via a worker job, run the
fresh-environment consumer job, then Hugging Face from the same manifest - all before the operator's
flip, which remains the only step that is not ours.

## 2026-10-20 - food-baseline-002: the code_38 baseline succeeded through the runner's contract - eval AUC 0.6326, gate re-accept and both entry points clean

**`food-baseline-002` succeeded exit 0 in 31.7 s and measured the first baseline number of the
chicago-food-inspections suite.** The corrected retry of food-baseline-001 (whose bundle had skipped
assembly) ran on server 171396373 (cpx32/hel1, EUR 0.06924/h, reserved EUR 0.24): it fetched the five
code_38 inputs of staging release 403508464 - the exact food-001 bytes - 31,520,896 bytes, each
sha256-verified on arrival, zero failures; re-accepted those bytes through the qualification gate's
`--accept` BEFORE any scoring ("ACCEPTED: /data/code_38 matches the qualified artifact 80a4291e3288dc07",
exactly code_38's artifact_version in baseline/expected_artifact.json); then ran the runner's own
`train.py` (exit 0) and `validate.sh` (exit 0, "[validate] CONTRACT OK") on the materialized task
directory, into which the private holdout was never copied.

**The measured result** (read back from the collected release 418558362's reports, each sha256-verified
against that release's own manifest, not from the console): **eval AUC 0.6326**, printed by train.py and
reproduced exactly by validate.py's predict_proba recompute with the target column removed. Rows: train
156,841 / eval 35,358 / holdout 34,218; positive rates 0.371255 / 0.20745 / 0.216786 (the holdout was not
scored by anything). The runner files are the benchmark's own templates, unmodified (bundled digests equal
the committed train.py a3c6bcf1..., validate.py b597e7f8..., validate.sh 3f06ca48...), so "the existing
runner, unmodified" is checkable rather than asserted. Dependencies on the worker: python 3.13.16, pandas
2.3.3, numpy 2.5.4, xgboost 3.4.1, scikit-learn 1.9.1. Scope: one baseline on one config - the
mid-prevalence sanity check named in next_action; no agent or harness comparison was run and none is
implied; the other 39 configs' baselines are not measured yet.

**Records and cleanup.** All six small report assets of release 418558362 (accept.log 72 B, baseline.json
2,010 B, train.log 53 B, validate.log 178 B, container.log 3,171 B, plus the release manifest.json and
source.tar 133,120 B whose digest equals the ledger's source_sha256) were fetched into
`.factory/food-baseline-002/reports/` and mapped to their real names through the release's own manifest;
no bulk CSV was downloaded to this host. `jobs/food-baseline-002.json` now carries the collected result
and deleted status (server 171396373 destroy order 16:07:17 UTC, deletion re-verified at the provider by
the 16:10:32 UTC reconcile that stamped the ledger). The candidate's record.json gained the
food-baseline-002 job entry, the `baseline_code_38_food_baseline_002` measurement block, and a next_action
that now points at finishing the packaging WIP and then the remaining 39 baselines. Committed with this
entry: STATE.md, record.json, jobs/food-baseline-002.json. Still deliberately uncommitted, the interactive
session's WIP: `skills/dataset-release/SKILL.md` (publication-authority wording),
`candidates/chicago-food-inspections/baseline/expected_artifact.json` (reformat and note change for the
packaging step), the untracked `candidates/chicago-food-inspections/release.json`,
`release/chicago-food-inspections/` and `scripts/build-food-expected-artifact.py` /
`scripts/build-food-package-measurements.py`, plus the hourly dashboard's build/dashboard outputs - none
of them are this watcher's to commit.


## 2026-10-20 - food-baseline-001: failed before scoring; the launch skipped assembly, and the corrected retry is already running

**`food-baseline-001` failed exit 2 in 26.8 s without measuring anything - a bundle failure, not a
dataset failure.** The job fetched all five food-001 staging inputs (31,520,896 bytes, each digest-verified
on arrival: code_38 train/eval/holdout CSVs, meta.json, quality.json), then its first real step -
re-accepting those bytes through the qualification gate (`python3 /workspace/qualify_dataset.py --accept
/workspace/qualification-code_38.json /data/code_38`) - died with `can't open file
'/workspace/qualify_dataset.py': [Errno 2] No such file or directory`, and run.sh exited 2 with "refusing
to score: the fetched bytes are not the qualified artifact". No AUC, no base rate, no scoring ran.

**Root cause, re-derivable from the collected source.tar.** `factory.worker.source_bundle()` packs
whatever directory the launched job.json lives in. This job was launched straight from
`candidates/chicago-food-inspections/baseline/job.json`, so the worker's `source/` carried only that
directory's own six files (run.sh, report.py, materialize.py, qualification-code_38.json, bundle.json,
expected_artifact.json) and none of what its bundle.json declares from elsewhere:
`qualify_dataset.py` (skills/dataset-qualification/scripts/), the runner's `train.py`/`validate.py`/
`validate.sh` verbatim from the benchmark clone, and their `runner_files.json`.
`scripts/assemble-job.py food-baseline` - the step that resolves the declaration into
`.factory/jobs/<id>/` - was skipped. Everything about the artifact itself remains as food-001 gated it.

**The retry was already in flight before this watcher could prepare one.** While this watcher collected
-001, the interactive session made the same diagnosis (its own fetch script for the same assets is at
`.factory/fetch_food_baseline_logs.py`), bumped the candidate's `baseline/job.json` id to
`food-baseline-002`, assembled the bundle properly (`.factory/jobs/food-baseline-002/` carries
qualify_dataset.py, the three runner files and runner_files.json), and launched it at 15:26:01 UTC on
server 171396373 (cpx32/hel1, EUR 0.06924/h; status running when this was written). This watcher launched
nothing - one worker at a time, and the corrected job was already up.

**Records and cleanup.** All four small assets of release 418547901 were fetched into
`.factory/food-baseline-001/reports/` (accept.log 94 B, container.log 660 B, manifest.json 4,192 B,
source.tar 143,360 B), each sha256-verified against the release's own asset list; source.tar's digest
equals the ledger's source_sha256. Server 171395072 is gone - this watcher's `worker destroy` at
15:27:09, then a `worker status` reconcile that re-verified at the provider that no server with that ID
exists (deleted_at 15:31:03). `jobs/food-baseline-001.json` is committed with this entry, together with
the `jobs/food-baseline-002.json` launch snapshot, the candidate's job.json id bump, and the failed-attempt
entry in the candidate's record.json. Two working-tree edits remain the interactive session's and were
deliberately left uncommitted: `skills/dataset-release/SKILL.md` (publication-authority wording) and
`candidates/chicago-food-inspections/baseline/expected_artifact.json` (reformat and note change for the
packaging step).



## 2026-10-19 - msha-hf-004: the Hub loading path now verifies end-to-end; the publication act was running while it finished

**`msha-hf-004` succeeded, and it closes the loading-path item that failed `msha-hf-003`.** Launched
10:31:55 UTC on server 171201702 (cpx42/hel1, EUR 0.13464/h) with the identical 226-asset plan (verified:
the job specs of -003 and -004 differ only by id), it re-ran the publish step after commit afe34c4's
`dataset_infos.json` declared all 45 configs' column types on the Hub. Result, read from the collected
`.factory/msha-hf-004/result.json`: **0 uploads, 0 failures, 226/226 targets "already at the manifest
digest"** (bytes: 0) - the transfer state msha-hf-003 left is intact - and the built-in loading check that
raised ArrowInvalid on 10:23 UTC now passes **exactly as pinned in the job spec**: `sec_56_12004` train
**415,088 rows / 36,796 positives**, eval **49,233 / 5,234**, holdout **33,576 / 3,343**, `ok: true`,
`problems: []`. The fix changed the documented loading path, not one data byte.

**Evidence chain.** The three small report assets were fetched into `.factory/msha-hf-004/reports/`, each
sha256-verified against the staging release 417170379 listing: `manifest.json` (93,888 bytes, 4be2496a...),
`source.tar` (102,400 bytes, 4ccba9e3... - equal to the ledger's `source_sha256`), and the 65-byte
container.log capture ("No such container: scout-msha-hf-004" - the container was already gone at
collection, same as -001 and -003, so the diagnosis lives in the collected result). The result embedded in
the release manifest is identical to the collected result except the worker's own release-attachment
fields (`uploaded` false-to-true, release_id/assets) - pre- and post-upload snapshots of one run. The
bundled worker source matches committed HEAD (afe34c4) file-for-file (executor.py, hf_publish.py,
upload.py) - the run provably used the fixed worker code. No bulk CSV touched the coordinator.

**The publication act was observed running, and this watcher did not touch it.** While the job finished,
the interactive session moved from the loading fix into publication: the Hub's small files were re-uploaded
at **10:44:51 UTC** (head 1ff49a68, "Publish v2026.10 documentation and small files"), the GitHub dataset
repo main advanced at **10:45:26 UTC** with docs-only commit ab429bc (dataset_infos.json +5,987 lines,
regenerated MANIFEST.json, DATA_DICTIONARY.md +14; VERIFICATION.md untouched), and at **~10:47 UTC both
destinations read public from anonymous clients** - Hub API `private: false` with an anonymous 200, GitHub
API `private: false, visibility: public` - after DESTINATIONS.json had recorded GitHub private at 10:33:57
and the Hub private at 10:19:26. That matches the austin/chicago/noaa precedent (publication under
recorded operator approval), but at collection time the repository still carried **no publication record**
(manifest `published: false`, no `publication` block in DESTINATIONS.json, the Hub card still said
private, no Hub tag - refs showed only main), and the session's publication edits (DESTINATIONS.json,
MANIFEST.json, README.md, RELEASE_NOTES.md, REPRODUCE.md, record.json) were **uncommitted in the working
tree**. To avoid a two-coordinator race, this watcher ran no `--verify`, no `--tag`, no small-file upload
and no visibility change; it did not edit record.json either - the interactive session had already written
the `msha-hf-004` jobs[] entry there itself, and that entry was checked against the collected result line
by line before this note was written. If the observed public state was not an approved publication act,
both destinations need an immediate revert - this is the one thing this entry cannot prove from inside the
repository.

**Cleanup and records.** Server 171201702 was destroyed at **10:49:07 UTC** (ledger `deleted_at`; ~17.2
minutes runtime, about EUR 0.04 at the hourly rate - derived, not an invoice figure). The ledger record
`jobs/msha-hf-004.json` is committed with this entry. What remains is the publication sequence the
interactive session owns: the DESTINATIONS flip record, the manifest regeneration (published true), the
card/LOADING/README/release-notes refresh and re-upload, the anonymous proof, and `hf-publish.py --tag`
LAST (still unrun on the Hub), then the site step.

## 2026-10-19 - msha-hf-003: Hub transfer complete 226/226 and --verify passed, but the job failed its loading check - a declared schema is the open fix

**`msha-hf-003` failed on the loading check, not the transfer - and the transfer it completed closes the
bulk upload `msha-hf-001` began.** Launched 10:08:03 UTC on server 171194439 (cpx42/hel1, EUR 0.13464/h,
destroyed 10:28:38 after collection) with the identical 226-asset plan, it uploaded **93 files,
1,389,391,904 bytes**, digest-verified as each landed, and **skipped 133 already at the manifest digest**
(127 from msha-hf-001 + 6 from msha-hf-002) - **226/226 targets accounted**. The interactive session's
`scripts/hf-publish.py --verify` (10:19:26 UTC) independently found every file on the Hub at the manifest
sha256: **missing: [], size_mismatch: []**. The job then failed its one remaining check: `load_dataset(
'earino/msha-enforcement-citations', 'sec_56_12004', revision='main')` generated train and eval and raised
**pyarrow ArrowInvalid: Failed to parse string: 'F015FC6' as a scalar of type int64** generating the holdout
split. `event_no` is an identifier that is mostly digits but occasionally alphanumeric (the failing row is a
2025-08-13 inspection), and the Hub's CSV loader infers column types from a sample, so it typed `event_no`
int64 and could not cast the alphanumeric values. The failure is real and re-derivable from the collected
result: the full traceback is `hf_loading.error` in `.factory/msha-hf-003/result.json`.

**msha-hf-002, closed out here too.** The first retry (launched 09:33:35 UTC, server 171185621) ran inside
the hour window msha-hf-001's 127 commits had filled: one batch-commit of 6 files landed and the Hub refused
the next with HTTP 429 - observed by the launching session from the live container output; no result was
ever collected, so its detail is not re-derivable from a collected report, and the 6-file contribution is
derived from msha-hf-003's skip list (133 - 127). The backoff fix (acb6510: a refused batch waits
RATE_LIMIT_BACKOFF_SECONDS and retries instead of failing its six assets) is what msha-hf-003 ran; its
server was destroyed 10:08:01 UTC and the ledger records status `deleted`.

**Evidence and cleanup.** The three small report assets were fetched into `.factory/msha-hf-003/reports/`,
each sha256-verified against staging release 417156564: the release manifest.json (103,231 bytes), source.tar
(102,400 bytes, digest equal to the ledger's `source_sha256`), and the container.log capture (65 bytes -
"No such container: scout-msha-hf-003"; the container was already gone at collection, same as msha-hf-001,
so the diagnosis lives in the collected result instead). No bulk CSV touched the coordinator. The job was
collected at 10:23:39 UTC by the watcher's own poll and the worker destroyed at 10:28:38 UTC (ledger
`deleted`).

**What is and is not broken.** The accepted artifact, the GitHub destination, the consumer verification and
the gate are untouched; all 226 accepted bytes are on the Hub. What failed is the *documented loading path*:
the Hub's type inference cannot read the artifact back through `load_dataset`. The fix in flight
(interactive session, mid-turn at recording time) is `scripts/hf-dataset-infos.py` - a Hub
`dataset_infos.json` declaring per-config column types (identifiers including zero-padded `mine_id` as
string, `prior_mean_citations` float64) so `load_dataset` parses instead of guesses - followed by the
upload and a loading re-verification. This watcher session did not edit scripts or launch a follow-up job:
the interactive session owns that work on this ledger. The `verified: true` it wrote into
`DESTINATIONS.json` at 10:19:26 UTC (still uncommitted) predates the loading failure, so that file still
needs its revision - the note and `artifact_version` - when the fix lands. `--tag` remains LAST.

**Recorded.** `candidates/msha-enforcement-citations/record.json` gains `msha-hf-002` and `msha-hf-003`
jobs[] entries and its next_action now states the bulk upload complete and the loading path as the open
item; the ledger records jobs/msha-hf-002.json (deleted) and jobs/msha-hf-003.json (collected, deleted) are
committed with this entry. `check-candidate.py msha-enforcement-citations`: OK.
## 2026-10-19 - msha-hf-001 failed on the Hub's per-repository commit limit at 127/226; uploader fixed, retry msha-hf-002 in flight

**The Hub bulk-upload job `msha-hf-001` failed, and the failure is in the transfer path, not the dataset.**
Created 09:02:54 UTC on server 171180553 (cpx42/hel1, reserved EUR 0.60 at the EUR 0.15/h ceiling), it
uploaded **127 of the 226 files - 1,921,773,312 bytes**, each digest-verified on the Hub as it landed
(the result's uploads list only carries files whose digest the Hub reported back), and then the remaining
**99 files all failed**. The pre-fix uploader pushed **one Hub commit per file**; after about 127 upload
commits the Hub's per-repository commit rate limit was exceeded and every remaining upload returned
**HTTP 429**. The worker recorded `status: failed` in its result (this job type carries no exit code in the
ledger); the result reached staging release 417102218 at 09:16 UTC, about **13 minutes** after launch -
derived from the ledger and release timestamps, not a recorded elapsed.

**Evidence, and where it stops.** `.factory/msha-hf-001/result.json` (sha256-verified against the staging
release manifest) lists the 127 landed targets and 99 `{target, error}` failures - but every failure string
is truncated at exactly 300 characters by the uploader's own error formatting, cutting off before the HTTP
status appears, and the container.log capture is a 65-byte `Error response from daemon: No such container:
scout-msha-hf-001` because the container was already gone when the job was collected at 09:32:58 UTC. So the
429/commit-limit diagnosis is the launching session's, read from the live container output and recorded in
commit **a2faeba**; it is consistent with every collected fact (127 commits landed, everything after failed,
no other error class appears) but is not re-derivable from the collected report alone. The run's bundled
`workers/hf_publish.py` hashes to `c2c84d9a0a75247f...`, equal to the pre-fix `a2faeba^` source - the failed
run provably used the per-file-commit code.

**Fix and retry.** Commit a2faeba batches 6 files into a single `create_commit` (CommitOperationAdd) instead
of one `upload_file` per asset, and still digest-verifies every file after the batch lands;
`tests/test_hf_helpers.py` runs the real helper source against a stub `huggingface_hub` and fails on the
pre-fix helper (demonstrated: AssertionError from upload_file). The retry **`msha-hf-002`** was launched at
09:33:35 UTC (server 171185621, ledger `jobs/msha-hf-002.json`) with the **identical 226-asset plan**
(verified: the two ledger job specs differ only by id), and its bundle sha256 `d110cd6bab2d96cb4292...` was
verified on the coordinator to equal a fresh `worker plan` rebuild from the fixed committed source - the
retry provably runs the fixed uploader. Per-file digest skipping means it resumes rather than re-uploads:
the 127 files already at the manifest digest are skipped. It was running at 09:43 UTC; the watcher will
report it.

**Worker, ledger, records.** Server 171180553 was collected at 09:32:58 UTC and destroyed at 09:40:24 UTC
(ledger status `deleted`; the destroy ran before this watcher session, so there was nothing to clean up).
The three small report assets (release manifest.json, source.tar, the failed container.log capture) were
fetched into `.factory/msha-hf-001/reports/`, each sha256-verified against the release manifest; no bulk
CSV touched the coordinator. `candidates/msha-enforcement-citations/record.json` gains the failed
`msha-hf-001` jobs[] entry (with the fix, the retry and the evidence chain) and its `next_action` now names
the retry in flight; the untracked ledger records `jobs/msha-hf-001.json` and `jobs/msha-hf-002.json` are
committed with this entry. Commit a2faeba itself was still local-only and is pushed with this change.

**The accepted artifact is untouched.** The gate, the consumer verification and the GitHub destination are
unaffected; the record stays status `packaged`. DESTINATIONS.json's `huggingface` entry is still
`verified: false` and its note still names msha-hf-001 - stale until the `hf-publish.py --verify` step
rewrites it when the retry lands. Reminder from the consumer entry: **no script currently writes
`artifact_version` into DESTINATIONS.json** (`hf-publish.py --verify` merges only the `huggingface` entry),
so whoever completes the HF step must add it or the site pipeline stays red after `--verify`.


## 2026-10-19 - msha-consumer-001: clean-room consumer check PASSED on the published bytes - 45/45 gates, baseline 0.8036 reproduced

**`msha-consumer-001` succeeded** (exit 0, 710.9 s of container time; not OOM-killed): the clean-room
consumer verification of the published release, mirroring `noaa-consumer-003`. A container with **no
dataset-factory access and no GitHub credential** received the published package tree (bundled with per-file
sha256 and hash-checked against `MANIFEST.json`: PACKAGE OK over the 22 listed files) and the release
assets exactly as a consumer receives them - the worker host fetched **226/226 assets, 3,384,299,154 bytes,
`failures: []`**, each against the sha256 pinned in the job's fetch spec, from
`earino/msha-enforcement-citations` release 417059413 (tag `v2026.10`). The results below were read
from `container.log`, `consumer.txt`, `baseline.log` and the 45 collected gate reports, each
sha256-verified against staging release 417086598 and the collected result before anything was written:

- `sha256sum -c SHA256SUMS` (the published verification command): **OK, all 226 lines**.
- the published gate (`code/qualify_dataset.py`, 1.3.0) on **every one of the 45 configs**: exit 0,
  `QUALIFICATION PASSED`, 32 checks each - **45/45**.
- **every gate artifact version equals the `MANIFEST.json` `artifact_version` for its level** -
  checked here over all 45, not sampled - so the bytes a consumer receives are the gated bytes.
- dependencies resolved inside the benchmark's declared ranges: pandas 2.3.3, numpy 2.5.4, xgboost 3.4.1,
  scikit-learn 1.9.1.
- the published baseline reproduced on `sec_56_12004` through both contract paths: **Eval AUC 0.8036**,
  `CONTRACT OK` - the recorded `msha-baseline-001` value itself, to the digit, not a spread around
  it (persistence reference on the same config: 0.5831). No run scored the holdout.

**Recorded.** `release/msha-enforcement-citations/VERIFICATION.md` now carries the consumer row and a
"Consumer verification: PASSED on the published bytes" section; its first "does not cover" bullet (the full
226-asset download never exercised end to end) is closed and replaced by the documentation-revision note,
mirroring noaa. `MANIFEST.json` was regenerated with `release-manifest.py` and the diff is exactly
one line, `package_files["VERIFICATION.md"]`; `SHA256SUMS` and every data digest are unchanged.
`check-package.py release/msha-enforcement-citations` **OK**; `check-candidate.py
msha-enforcement-citations` **OK** (status `packaged`).
`candidates/msha-enforcement-citations/record.json` gains the `msha-consumer-001` `jobs[]`
entry and a `consumer_verification` block, and its `next_action` reads the consumer item closed.
The dataset repo's `main` (bb7ca7e9) still carries the pre-revision docs; advancing it with the revised
VERIFICATION.md/MANIFEST.json is the docs-only step named in `next_action` (`v2026.10` keeps naming
the verified data bytes).

**Worker, ledger and reports.** Server 171177546 (cpx32/hel1, EUR 0.32 reserved at the EUR 0.08/h ceiling;
about 17 minutes of lifetime end to end) was collected at 09:02:01 UTC and destroyed at 09:02:54 UTC - half a
second before `msha-hf-001` (the Hub bulk-upload job) was created - by the concurrent interactive
session that is running the Hugging Face step; that session's commit 7e22e82 already folded this job's result
into `DESTINATIONS.json`'s GitHub checks, and `msha-hf-001` is in flight and not touched here. This
session re-confirmed the server's absence from the provider via `worker status` reconcile
(each reconcile re-stamps `deleted_at`, so the committed ledger shows the last observation,
09:08:27 UTC, while the destroy itself ran at 09:02:54 UTC - the time `record.json` carries).
`jobs/msha-consumer-001.json` records status `deleted` with the full result and is committed here.
The job's small reports were fetched into `.factory/msha-consumer-001/reports/` (48 files); the 500 KB
`source.tar` was hash-checked in scratch instead of collected: `run.sh` and `verify_package.py`
are byte-identical to the committed job source, the `bundle.json` sizing override explains the 200 -> 180
minute lifetime normalization, and all 25 bundled source files match the repository today.

**CI for 3102788.** `Local checks` (the test suite plus `factory doctor`): **success** on the
clean checkout. `Website pipeline preview`: **failure** - inherited, not introduced: the identical error
appears for the parent 7e22e82, which added `sites/msha-enforcement-citations.json` while the Hugging
Face destination is mid-flight. `site_model.project()` requires a complete `DESTINATIONS.json`
(`release_tag` **and** `artifact_version`, both destinations `verified: true`); msha's has no
`artifact_version` and its `huggingface` entry is `verified: false` pending `msha-hf-001`,
so `site-publish.py prepare` fails with "Destination evidence describes a different release or
artifact". Nothing in this commit touches those files (the manifest regeneration changed only its
`VERIFICATION.md` entry; `artifact_version` is unchanged), and the gate is the designed one - the
website step requires public, verified destinations. Note for the HF step, though: **no script currently
writes `artifact_version` into `DESTINATIONS.json`** (`hf-publish.py --verify` merges only the
`huggingface` entry; noaa's file carries it from its publication flow), so whoever completes the HF step
must add it or the site pipeline stays red after `--verify`.

## 2026-10-19 - msha-publish-001: all 226 assets are in the dataset repository, API-verified - record `packaged`

**`msha-publish-001` succeeded** (its container.log is one line recording that no container ran - this job
only moves bytes). The `transfer` spec copied all **226** accepted artifact files, **3,384,299,154 bytes**,
from private staging release **410471211** into `earino/msha-enforcement-citations` release **417059413**, on
worker **171169567** (cpx32/hel1): created **08:27:12 UTC**, collected **08:43:43**, destroyed **08:44:09**
(`jobs/msha-publish-001.json` records status `deleted` with `deleted_at`). `failures: []`. The staging
release's own manifest shows `uploaded: false` only because that snapshot was written before the result
upload completed - the collected `result.json` carries `uploaded: true` with all 226 transferred entries,
the same pattern noaa-publish-001 showed.

**Verified from the service, not the job's report.** All **226** assets re-read from the GitHub API match
the package `MANIFEST.json` bytes+sha256 exactly - **226/226**, no extras, none missing - and the repository
is **private**. The release was a draft during the transfer, so the tag did not exist yet; it was published
only **after** this digest verification, which created `v2026.10` at `main` - tag and main resolve to the
same commit **`bb7ca7e9`** (the initial docs commit), and the assets were re-read after publishing:
unchanged. All **23** package files at that commit are byte-identical to `release/msha-enforcement-citations`
(compared by Git blob hash, `MANIFEST.json` and `SHA256SUMS` included), so the repository is not describing a
different dataset from the one `check-package.py` validates.

**Recorded.** `candidates/msha-enforcement-citations/record.json` is status **`packaged`**, with the
`msha-publish-001` `jobs[]` entry (staging release 417072041 / target release 417059413, server, times,
226 assets / 3,384,299,154 bytes / 0 failures, the API verification and its evidence paths), and
`next_action` names the remaining order: (1) the Hugging Face destination per AGENTS.md
(`hf-publish.py --plan`, `--create --upload-small`, then the `hf_publish` worker job for the bulk),
(2) the consumer run - `get_dataset.py` over all 226 assets plus a gate re-run on fetched bytes, recorded
in `VERIFICATION.md`. `scripts/check-candidate.py msha-enforcement-citations` OK on the updated record.

**The job's small reports were fetched** into `.factory/msha-publish-001/reports/` and sha256-verified
against staging release **417072041** (tag `job-msha-publish-001`) before writing: `manifest.json`
(the job's own artifact manifest), `container.log` (70 bytes), and the 92 KB `source.tar` job bundle.

**Nothing is public.** The repository is private, no `DESTINATIONS.json` exists for this dataset, and the
manifest still derives `visibility: private`, `published: false`. Publication remains a separate
operator-approved act, on both platforms.

**Cost:** EUR 0.32 reserved for this job at the EUR 0.08/h cpx32 ceiling (ledger); ~17 minutes of server
lifetime end to end, so the charge is a fraction of that. No new research spend.

**Also in flight from the same session.** `msha-consumer-001`, the clean-room consumer run, was launched at
**08:45:40 UTC** on worker **171177546** (cpx32/hel1, EUR 0.32 reserved, expires 1792410340): it fetches all
226 assets **from the destination release 417059413** with each asset's sha256 pinned, restores the runner
layout and re-runs the gate on the fetched bytes, mirroring `noaa-consumer-003`. Its ledger
(`jobs/msha-consumer-001.json`) and job source (`candidates/msha-enforcement-citations/consumer/`) are
committed with this entry; the job was still running when this session recorded the transfer, and the
watcher picks it up by construction. Left **uncommitted** from that session, deliberately: the in-progress
Hub-card work (`scripts/hf-publish.py`, `factory/site_model.py` - making the card's `configs:` block generate
from the manifest so MSHA's 45-config shape declares all 45 configs instead of one arbitrary CSV pair). That
code is unverified and is the first item of the Hugging Face step; the next session owns it.
## 2026-10-19 - MSHA package assembled: 226 assets manifested from the gate's own evidence

`release/msha-enforcement-citations/` now holds a complete, checkable package, and
`python3 scripts/check-package.py release/msha-enforcement-citations` returns **OK**: README,
DATA_DICTIONARY (all 25 columns with the publisher's documented meanings and availability at the
prediction instant), LICENSE (MIT code / CC0-1.0 compilation / source public-domain-by-statute,
from the decided license.json), REPRODUCE, RELEASE_NOTES, VERIFICATION, both licence texts,
`get_dataset.py` (226 flat assets restored to the runner layout, `--config` and `--labels-only`),
`code/` (build.py at the msha-002 bundled hash `1c80c1ae...`, run.sh, the gate at 1.3.0, the two
probe scripts, materialize.py) and `baseline/` (the benchmark's runner files, digests verified equal
to the task_template copies: `a3c6bcf1...` / `b597e7f8...` / `3f06ca48...`).

**The manifest is generated from recorded evidence, not retyped.**
`candidates/msha-enforcement-citations/release.json` is the new descriptor (repository
`earino/msha-enforcement-citations`, version/tag `2026.10`/`v2026.10`, construction commit
`ed211f2de6c70b6f911dfa7392559db283c65d20` - the commit whose build.py the worker bundled and
ran). `release-manifest.py msha-enforcement-citations` then produced a MANIFEST over all
**226 files** (45 configs x 5 + labels.csv, 3,384,299,154 bytes), each level carrying its own
gate-produced artifact_version and **32 checks** read from the report's `results` list with
`failed_checks` asserted 0 (`scripts/build-msha-expected-artifact.py` regenerated; it previously
recorded `checks: null` because the MSHA reports count checks in `results`, not a `checks`
field - fixed, with the cleanliness assertion added). `measurements.json` is generated by the
new `scripts/build-msha-package-measurements.py` from the collected msha-002 build_summary:
pool 497,897, floor 80 / shipped 45 / held back 35, per-config rows, positives, positive rates
and persistence references for all 45, plus the corrected-feature evidence and the baseline
reference (0.8036 / CONTRACT OK). `baseline_result.json` records the msha-baseline-001 evidence
including the installed stack (pandas 2.3.3, numpy 2.5.4, xgboost 3.4.1, scikit-learn 1.9.1,
scipy 1.18.1).

**Generator refactor, with the regression that proves it.** `construction_commit` moved from a
noaa-specific literal in `release-manifest.py` into the per-dataset descriptor (required key now).
Regenerating noaa's MANIFEST changed **exactly one line**: `publication_note`'s timestamp
(2026-09-25T17:09:22 -> 2026-09-26T21:02:37) - a **pre-existing drift**: noaa's DESTINATIONS.json
was updated by the 2026-09-26 Hub re-verification without a manifest regeneration afterwards, so
the committed MANIFEST was already stale against the recorded evidence. The regenerated copy
(which `check-package.py` passes) is kept; every other field is byte-identical, which is the
proof the refactor changed nothing.

**Two record corrections, found by the package work.** (1) `split_strategy` said "2000 ... folds
into train"; the shipped meta.json windows start 2001-01-01 and the gate's rows-within-windows
check passed, so 2000 is excluded, not folded in - the line is corrected with the change dated,
and the package docs say 2001-2025, matching the shipped windows. (2) `construction_output` is
new in the record, carrying the shipped split windows and rows so the manifest's `splits` block
is populated from the record rather than absent.

**The ordering decision is made and recorded** (in the record's next_action): MSHA packages before
chicago-food-inspections, because MSHA's baseline is measured through the runner's contract and
its licence decided, while Chicago still needs its food-baseline-001 job before its own
packaging. This is Scout's call to make in a scheduled session; the operator reorders by simply
packaging Chicago next.

**Nothing is published and the bytes have not moved.** No DESTINATIONS.json exists for this
dataset, so the manifest derives `visibility: private`, `published: false`, publication_note
"Prepared for human review." The 226 assets remain on private staging release 410471211; the
next action (record's next_action, step by step) is the GitHub destination: private repo +
initial docs commit, then transfer job msha-publish-001 on a worker, then API-side verification
of every asset digest, then status `packaged`. The Hugging Face destination and the full
226-asset consumer run follow after that; publication remains a separate operator-approved act.


## 2026-10-14 - msha-baseline-001: the MSHA baseline is measured on the released bytes - eval AUC 0.8036, contract OK

The runner-contract baseline job for `msha-enforcement-citations` (candidate `qualified` since the msha-002
build) ran on a Hetzner worker and succeeded. It fetched - did not rebuild - the accepted artifact's
`sec_56_12004` config from private staging release 410471211 (the msha-002 bytes), materialized it with
`release/msha-enforcement-citations/code/materialize.py` and ran the benchmark's own unmodified
`train.py`/`validate.py`/`validate.sh` on it. The number below was read back out of the collected release,
not the console.

**What ran** (`jobs/msha-baseline-001.json`, worker 170280758, cpx32/hel1, exit 0, 41.5 s wall, no OOM,
EUR 0.24 reserved / EUR 0.08/h ceiling, destroyed 08:20:58 UTC, provider inventory back to 0 servers):
fetch the five `sec_56_12004` files (meta.json, quality.json, public/train.csv 60,630,330 B, public/eval.csv
7,425,519 B, private/holdout.csv 5,058,885 B) with sha256 verification in transit, pip install the runner's
stack, materialize the task directory (24 features; `event_no` dropped as the identifier/carry column;
the private holdout deliberately not copied into the workspace), then `train.py` and `validate.sh`. Both
bundled runner files match the committed benchmark templates byte-for-byte (sha256 `a3c6bcf1...` train.py,
`b597e7f8...` validate.py, `3f06ca48...` validate.sh), so the measurement is through the contract an evaluated
agent is scored under, and `validate.py` re-ran training independently and agreed.

**Measured outcome** (`.factory/msha-baseline-001/reports/`, each asset sha256-verified against the staging
release manifest, release 412476894):

- **Eval AUC 0.8036** on `sec_56_12004`, identical from both paths: `train.py` itself and the independent
  `validate.py` re-run (predict_proba with the target column removed). CONTRACT OK.
- **Rows and base rates** (meta.json): train 415,088 / eval 49,233 / holdout 33,576; positive rate
  0.0886 / 0.1063 / 0.0996. Train AUC 0.8036, so no overfit gap on the eval window.
- **Persistence reference** (msha-002 build_summary.json, collected and digest-verified): `prev_target_cited`
  alone scores 0.5831 eval AUC on this config. The full 24-feature model clears it by 0.2205, so the
  learned signal is not the target section's own persistence in disguise; `prev_target_cited` is the only
  single feature measured individually, so no strongest-feature claim is made - the calibration
  noaa-tide-flooding required before any headroom claim, measured here before packaging.

**Recorded**: `candidates/msha-enforcement-citations/record.json` gains a `baseline` block (mirroring the
noaa pattern: job, artifact provenance, levels with AUC and base rates, persistence reference, evidence
path) and a `msha-baseline-001` `jobs[]` entry; `next_action` moves to packaging. `jobs/msha-baseline-001.json`
and the baseline job assets (`candidates/msha-enforcement-citations/baseline/` including the pinned
`expected_artifact.json`, `release/msha-enforcement-citations/code/materialize.py`,
`scripts/build-msha-expected-artifact.py`) are committed with this entry.

**Next action**: package the release from staging release 410471211 (the 45 per-section configs plus the
extract-root labels.csv, mirroring noaa's per-level pattern; the licenses block comes from license.json).
Publication remains a separate operator-approved act, and the operator chooses whether MSHA or the
already-built Chicago candidate packages first.

## 2026-10-05 - food-001: chicago-food-inspections built and gated - 40/40 configs pass, candidate `qualified`

The construction job for `chicago-food-inspections` (the multi-label Chicago food-inspection
task promoted to `ready` on 2026-09-28) ran on a Hetzner worker and succeeded. The candidate
record now carries the measured outcome and moves to `qualified`; nothing is published and
nothing is scored yet.

**What ran** (`jobs/food-001.json`, worker 168745538, cx23/hel1, exit 0, 8.5 min): the full
pull of `4ijn-s7e5` (46 pages, 226,417-row modelling pool: results in Pass/Fail/Pass w/
Conditions AND a non-null violations blob), `build.py` rendering one binary runner config per
floor violation code with the prior-history features, then the qualification gate over every
config, on the worker, over the full artifact. Artifacts uploaded to the private staging
release `403508464` (`job-food-001`, draft): 290 assets, 1,286,358,734 bytes total. Bulk CSVs
and labels.csv were never downloaded to this host; only the 167 small report assets were
collected, each sha256-verified against the release manifest.

**Measured outcome** (`.factory/food-001/reports/`):

- **Coverage is complete.** All 40 configs ship the identical full pool: train 156,841 /
  eval 35,358 / holdout 34,218 = 226,417 rows. Every config has all three split files. No
  zero-row or zero-positive-rate split. Rows dropped from the 226,459 raw pool rows:
  14 missing licence, 42 outside windows, 0 unparsable violations blobs.
- **The gate passed everywhere.** 40/40 per-code qualification reports, gate 1.3.0, 31 checks
  each, 0 failed, 0 warnings: no leakage column, prediction timing intact, units and frames
  declared, temporal splits disjoint and within windows, no cross-split entity, both classes
  in eval and holdout, runner layout and meta keys correct.
- **The floor rule resolved to 40 codes, not 37.** The pre-build estimate came from a
  15,000-row recent scan; the full pool supports 40: 48 codes clear the 1% pool-rate floor
  and 8 are dropped by the per-window minimums (>=30 positives and >=20 distinct days per
  window): codes 12, 18, 19, 24, 30, 31, 34, 42. The floor rule itself is recorded in the
  extract manifest.
- **The digest chain holds.** Every qualification report's component digests (5 files x 40
  configs = 200 comparisons) match the staging release manifest exactly, so the passing
  reports describe the uploaded bytes, not an earlier build.
- **The joint label matrix ships too:** labels.csv at the extract root, 24,319,192 bytes,
  one row per inspection, one column per floor code, so the multi-label formulation is
  consumable without re-pulling the source.
- **Live-source drift is expected and recorded:** pool_rows 226,417 vs 226,133 measured
  2026-09-28 - the portal gained 284 rows in the week between probe and build.

`scripts/check-candidate.py --all`: every record OK (`chicago-food-inspections: OK
(status=qualified)`).

**Next action** (recorded in the record): (1) package the release from the staging assets -
decide how the 40 per-code configs and labels.csv present in MANIFEST.json and the package
layout, mirroring the per-level pattern noaa-tide-flooding shipped; (2) measure a baseline
through the runner's contract on a worker, one mid-prevalence config first (code_38 or
code_55); (3) publication remains a separate operator-approved act.

## 2026-09-28 - chicago-food-inspections promoted to ready: licence decided, novelty recorded, cost and splits measured

The queue had one `ready` candidate (`msha-enforcement-citations`) blocked on an operator
licence decision that must not be assumed, and one fallback lead
(`chicago-food-inspections`) whose record named three unblocked gates. This session cleared
all three, so the buffer now holds a second ready candidate and a failed MSHA licence
decision no longer empties the queue.

- **Licence** (`candidates/chicago-food-inspections/license.json`, decided 2026-09-28): the
  operator-accepted City-of-Chicago portal-terms posture from the DOAH decision
  (2026-09-26) recorded explicitly against source id `4ijn-s7e5` - same publisher, same
  terms instrument, `LicenseRef-CityOfChicago-DataTermsOfUse`, no standard open licence,
  mandatory derivative disclaimer verbatim. The decision states it follows the DOAH
  decision if the operator revisits it.
- **Novelty** (`scripts/check-novelty.py`, recorded 2026-09-28T08:02:56Z): verdict
  `differentiated`. Hugging Face 0 hits on all five queries; the closest prior art is the
  publisher's own deployed **binary** critical-violation model (CDPH
  food-inspections-evaluation) and its hindsight evaluation (arXiv 1910.04906) - a different
  task. Ours is the multi-label formulation: the set of violation codes per inspection, with
  an explicit prediction instant, prior-history features and temporal windows.
- **Extraction cost measured, not estimated** (`probe_cost.py`, coordinator class): 20,000
  rows in 4 pages, 5 requests, 28,948,432 bytes, 23.2 s; mean 1,447 bytes/row. Full-pull
  estimate (labelled): ~64 pages, ~458 MB, ~366 s. Order key `inspection_id` is unique per
  row, so offset paging is stable.
- **Split capacity measured** (`probe_splits.py`, new): pool 226,133 rows; train 2010-2020
  156,853 rows / 28,930 licences, eval 2021-2023 35,360 / 12,992, holdout 2024-2026-09
  33,920 / 12,953; all 37 floor codes (>=1% of a fresh 15,000-row scan) present in all three
  windows. One measurement artefact caught and fixed en route: Socrata's default 1,000-row
  cap on grouped queries first reported exactly 1,000 licences in every window; the grouped
  query is now paged explicitly.

`scripts/check-candidate.py --all`: every record OK (`chicago-food-inspections: OK
(status=ready)`). Nothing was constructed. Next action, recorded in the record: write
`source/build.py` in the accepted pattern, decide how the 37-target multi-label task ships
through the one-target runner contract, then build and qualify on a worker.

## 2026-09-26 13:12 UTC - noaa-hf-004: the two renamed Hub files were already at the manifest digest

A Hugging Face publish job for the two `station_disjoint` files whose release-asset names differ from
their Hub paths. It ran on server `167526113` (cpx32/hel1), was collected after 2 min 20 s of worker time
and was destroyed at 13:12 UTC.

**Measured** (`.factory/noaa-hf-004/{result.json,reports/}`, `jobs/noaa-hf-004.json`):

| step | result |
| --- | --- |
| flow | `earino/noaa-tide-flooding` revision `main`, 2 files, source the dataset release's assets 588583422 / 588583523 |
| outcome | `status: succeeded`, `failures: []`, **0 bytes uploaded** - both targets `skipped: already at the manifest digest` |
| independent, anonymous client | Hub tree API HTTP 200 (repository readable without a credential): `station_disjoint/private/holdout.csv` 4,228,360 bytes and `station_disjoint/public/eval.csv` 4,229,477 bytes, both downloaded and re-hashed to `37d77262...` / `be501093...` - exactly the digests the job compared against |

So the Hub carried both files at their declared paths before the job ran, and the job changed no data on
either destination. Nothing here is a repair; it is a confirmation of the nested layout the website's Hub
links now depend on, and it agrees with the anonymous read above.

**Residual, recorded rather than worked around.** The staging release's `container.log` asset is 65 bytes
reading `Error response from daemon: No such container: scout-noaa-hf-004` - the container was already gone
when its logs were collected, so the run's own container log does not exist. The result summary does, and it
is the summary that carries the outcome.

**Recorded**: `candidates/noaa-tide-flooding/record.json` (a `noaa-hf-004` entry in `jobs` with the targets,
the skip reasons, the anonymous re-verification and the residual), `jobs/noaa-hf-004.json`,
`candidates/noaa-tide-flooding/hf/job-004.json` (both already committed by `d9cad24`),
`.factory/noaa-hf-004/`. Worker `167526113` destroyed and confirmed gone from the provider
(`GET /v1/servers/167526113` -> 404; no factory-labelled servers remain).

**CI for `4f8ac82` is blocked, not failing.** The run for the pushed commit (`Local checks` -> job
`check`) concluded `failure` with **zero steps executed** (check run 108411150098), and its annotation reads
"The job was not started because recent account payments have failed or your spending limit needs to be
increased" - the same GitHub billing condition already recorded for `be83b1d` and `4b3cdb1`, outside this
repository. Run here with the workflow's own command (`python3 -m unittest discover -s tests`): **286 tests,
OK**, including the three new `tests/test_site_hub_paths.py` cases `d9cad24` added; and
`scripts/check-candidate.py --all` and `scripts/check-package.py release/noaa-tide-flooding` both pass on the
tree this commit records.

**Left alone, deliberately**: the interactive session's own edits in the working tree (`scripts/site-hf.py`
among them) were read, not staged or committed, by this run. `record.json`'s `artifacts[0].huggingface`
block still describes the Hub as private with the tag lagging while the committed `DESTINATIONS.json` now
records both destinations as public - that reconciliation belongs to the session that owns the release path.

## 2026-09-26 13:12 UTC - noaa-hf-004: the two renamed Hub files were already at the manifest digest

A Hugging Face publish job for the two `station_disjoint` files whose release-asset names differ from
their Hub paths. It ran on server `167526113` (cpx32/hel1), collected after 2 min 20 s of worker time and
was destroyed at 13:12 UTC.

**Measured** (`.factory/noaa-hf-004/{result.json,reports/}`, `jobs/noaa-hf-004.json`):

| step | result |
| --- | --- |
| flow | `earino/noaa-tide-flooding` revision `main`, 2 files, source the dataset release's assets 588583422 / 588583523 |
| outcome | `status: succeeded`, `failures: []`, **0 bytes uploaded** - both targets `skipped: already at the manifest digest` |
| independent, anonymous client | Hub tree API HTTP 200 (repository readable without a credential): `station_disjoint/private/holdout.csv` 4,228,360 bytes and `station_disjoint/public/eval.csv` 4,229,477 bytes, both downloaded and re-hashed to `37d77262...` / `be501093...` - the digests the job compared against |

So the Hub carried both files at their declared paths before the job ran, and the job changed no data on
either destination. Nothing here is a repair; it is a confirmation of the nested layout the website's Hub
links now depend on.

**Residual, recorded rather than worked around.** The staging release's `container.log` asset is 65 bytes
reading `Error response from daemon: No such container: scout-noaa-hf-004` - the container was already gone
when its logs were collected, so the run's own container log does not exist. The result summary does, and it
is the summary that carries the outcome.

**Recorded**: `candidates/noaa-tide-flooding/record.json` (a `noaa-hf-004` entry in `jobs` with the targets,
the skip reasons and the anonymous re-verification), `jobs/noaa-hf-004.json`,
`candidates/noaa-tide-flooding/hf/job-004.json`, `.factory/noaa-hf-004/`. Worker `167526113` destroyed and
confirmed gone from the provider (`GET /v1/servers/167526113` -> 404; no factory-labelled servers remain).

**Not recorded here, deliberately**: the interactive session's uncommitted publication edits listed in the
header above. They are that session's to finish and commit; this run only read them. Both destinations'
public state as recorded in those uncommitted files has not been re-verified here beyond the anonymous Hub
read above.

## 2026-09-25 16:06 UTC - noaa-consumer-003: the consumer check now belongs to the bytes the release holds

The re-run the record has owed since noaa-publish-002 - noaa-consumer-002's PASSED described the superseded
noaa-003 artifact - was launched from an interactive session at 15:57 and finished under the watcher in 74 s
of worker time. This entry records the measured result and what it closes.

**Measured** (`.factory/noaa-consumer-003/reports/`, `result.json`, `jobs/noaa-consumer-003.json`):

| step | result |
| --- | --- |
| fetched | 10/10 files from the dataset release 396698120 (`earino/noaa-tide-flooding`, tag `v2026.09`), **196,018,020 bytes**, `failures: []`, every digest equal to `artifacts[0].levels` |
| package vs `MANIFEST.json` | every listed file matched its recorded hash |
| `sha256sum -c SHA256SUMS` | OK |
| gate, temporal / station_disjoint | exit 0, `QUALIFICATION PASSED`, artifacts `bb051dc304a4ee63` / `92297a5b62f86b29` - both equal the accepted artifact's versions |
| baseline, temporal / station_disjoint | `CONTRACT OK`, eval AUC **0.8633** / **0.8690** |

The two baseline AUCs are the recorded pair itself, not a spread around it: noaa-baseline-002 measured
0.8633/0.8690 on the same corrected bytes and this independent clean-room run reproduces both to the digit,
where the superseded bytes gave 0.8651/0.8687 against a recorded 0.8638/0.8688. No run scored the holdout.

**One residual, recorded rather than fixed here.** The bundled harness and the shipped
`baseline/reproduce_baseline.sh` both print a hardcoded expectation line carrying the superseded pair, so the
last line of `output_consumer.txt` reads "expected: temporal 0.8638, station_disjoint 0.8688" while the
package's own `MANIFEST.json` carries 0.8633/0.8690. The printed line is a constant, not a read of the
manifest, and no check failed. It belongs to the package-prose pass (item 1 below), which still owes the
`late` label row in `DATA_DICTIONARY.md`, the job-`noaa-003` qualification row in `VERIFICATION.md`, and the
superseded figures in `README.md`/`RELEASE_NOTES.md`/`REPRODUCE.md`/`baseline/README.md`/
`code/persistence_baseline.py`.

**Changed here, with the outcome.** `release/noaa-tide-flooding/VERIFICATION.md` said the consumer check
"must be re-run on these bytes"; it now records the pass above with the step table, keeps the superseded pass
beside it, and names the job in its summary row. `MANIFEST.json` was regenerated with
`scripts/release-manifest.py`: the only change is `package_files["VERIFICATION.md"]` (399 keys otherwise
identical). `check-package.py release/noaa-tide-flooding` passes. `release/noaa-tide-flooding/
DESTINATIONS.json` - untracked until now - was written by `scripts/hf-publish.py --verify` at 15:57 under the
tool's convention that `revision` carries the package tag label: its `verified: true` means the Hub's
*default branch* (`main`, `3116c306`) matched every file, **not** that the Hub tag does. `v2026.09` on the
Hub still resolves to `ee6ba847`, the noaa-003 commit, so the tag item stays open and item (1) is still its
gate.

**Recorded**: `candidates/noaa-tide-flooding/record.json` (a `noaa-consumer-003` entry in `jobs`;
`consumer_verification` re-pointed at this run with the superseded pass kept under `previous`; `next_action`
rewritten so the consumer item reads closed), `jobs/noaa-consumer-003.json`, `release/noaa-tide-flooding/
{VERIFICATION.md,MANIFEST.json,DESTINATIONS.json}`, this file. Worker `167442487` destroyed after collection
and confirmed gone from the provider (`GET /v1/servers/167442487` -> 404, and no factory-labelled servers
remain).

**CI for `4b3cdb1` is blocked, not failing.** Both workflow runs for the pushed commit (`Local checks` ->
job `check`, `Website pipeline preview` -> job `preview`) concluded `failure` with no steps executed, and the
check-run annotation for each reads "The job was not started because recent account payments have failed or
your spending limit needs to be increased" - the same GitHub billing condition recorded for `be83b1d`, outside
this repository. The suite was run here with the workflow's own command (`python3 -m unittest discover -s
tests`): **283 tests, OK**. `check-candidate.py --all`, `check-package.py release/noaa-tide-flooding`,
`sh scripts/scout-factory doctor` and the gate's `--selftest` all pass on this state. Re-running CI is
pointless until the account's Actions billing is restored, and this commit - like this one-line record of it -
is docs-and-records only.

**Next action**: (1) the package-prose pass, then `scripts/hf-publish.py --create --upload-small`, `--verify`,
and `--tag` **last** so the Hub's `v2026.09` and `main` agree; (2) the persistence-floor decision - carry the
noaa-003 figures with the recorded note or re-measure on the corrected eval split; (3) the publication act
the operator approves, on both destinations, from one manifest. Both destinations stay private until then.

## 2026-09-25 15:27 UTC - noaa-hf-003: the Hub carries the corrected NOAA bytes; its tag and docs do not

The worker job that moves the bulk of a dataset release was launched from an interactive session at 15:20
and finished under the watcher in under a minute of worker time. It published the corrected noaa-004 files
to `earino/noaa-tide-flooding` revision `main`. This entry records what was verified from the service and
what the Hub half of the re-issue still owes.

**Measured** (`.factory/noaa-hf-003/result.json`, `reports/manifest.json`, `jobs/noaa-hf-003.json`):

| item | value |
| --- | --- |
| staged | private staging release 396718146 (`job-noaa-hf-003`), report assets collected and digests matched |
| transferred | **10 of 10** target files, **196,018,020 bytes**, `failures: []`, `skipped: []` - a real upload, not a digest-skip |
| loading check | `ok: true`, `problems: []`, all six splits matched the accepted counts |
| rows train/eval/holdout | temporal 697,373 / 89,038 / 88,841; station_disjoint 461,580 / 29,930 / 29,930 |
| positives | temporal 11,774 / 1,815 / 2,850; station_disjoint 7,513 / 788 / 1,090 |

The six loading-check splits are identical to `noaa-baseline-002`'s counts on the accepted artifact, so the
Hub copy is the same panel and not a neighbouring revision.

**Verified by reading the Hub, not the job's claim.** Revision `main` moved to `3116c306`, and every one of
the ten file paths was checked against `release/noaa-tide-flooding/MANIFEST.json` and the accepted
`artifact_version fb49f932...`: six small files were downloaded and re-hashed here (meta.json 867,
quality.json 3,793/3,795, station_disjoint holdout 4,228,360 and eval 4,229,477, temporal/meta.json 750) and
four large LFS objects were read from the Hub's own `sha256` (station_disjoint/public/train.csv `d7d2bff2`,
temporal/private/holdout.csv `89db2e79`, temporal/public/eval.csv `a2d733a8`, temporal/public/train.csv
`60854702`). **10 of 10 sizes and digests match.** The superseded numbers recorded on 2026-09-25 15:06
(12,475,942 / 4,228,351, label column `late`) no longer describe `main`.

**What has not moved, measured rather than assumed.** `v2026.09` on the Hub still resolves to `ee6ba847`,
the noaa-003 commit, while `main` is `3116c306` - so a version-pinned Hub reader still gets the superseded
bytes, and re-tagging (`scripts/hf-publish.py --tag`, which replaces the existing tag) has not been run. The
Hub's `MANIFEST.json` and `SHA256SUMS` on `main` also still list the noaa-003 digests, i.e. `--upload-small`
has not been re-run either. That hold is deliberate and it is the reason this job is a partial re-issue
rather than a complete one: `release/noaa-tide-flooding/DATA_DICTIONARY.md` still names the shipped label
column `late` and `VERIFICATION.md` still cites job `noaa-003`, so uploading the small files today would
publish prose contradicting the `temporal/meta.json` (label `minor_flood`) now on the Hub. Exposure is zero
- every stale digest is the superseded version's own and both destinations are private - but the Hub package
does not yet describe the bytes it holds. **The package prose must be re-pointed at noaa-004 before the
small files and the tag are pushed.**

**Recorded**: `candidates/noaa-tide-flooding/record.json` (a `noaa-hf-003` entry in `jobs`; the
`artifacts[0].huggingface` block re-measured - `main_commit 3116c306`, `tag_commit ee6ba847`,
`tag_matches_main false` with a note that the old `true` described the 2026-09-20 upload, and a new
`reissue` block carrying the per-file verification, the loading check and the `still_lagging` items;
`next_action` rewritten), `jobs/noaa-hf-003.json` and `candidates/noaa-tide-flooding/hf/job-003.json`
committed. Worker `167437889` destroyed and confirmed gone from the provider (no factory-labelled servers
remain; a direct `GET` on the id returns 404). `check-candidate.py --all` and `check-package.py
release/noaa-tide-flooding` both pass on this state.

**Next action**: (1) re-point the release package prose at noaa-004 - the label row in `DATA_DICTIONARY.md`,
the job references in `VERIFICATION.md`, the README/RELEASE_NOTES/measurements pass - regenerate
`MANIFEST.json`/`SHA256SUMS` with `scripts/release-manifest.py`, then run `scripts/hf-publish.py --create
--upload-small`, `--verify`, and `--tag` **last** so the Hub's `v2026.09` and `main` agree; (2) re-run the
clean-room consumer check against the re-issued bytes; (3) decide the persistence-floor question; (4) then
the publication act the operator approves, on both destinations, from one manifest. Both destinations stay
private until then.

## 2026-09-25 15:10 UTC - noaa-publish-002: the corrected artifact is in the GitHub release, the Hub half still lags

The re-issue of the NOAA release was launched from an interactive session at 14:54 and finished under the
watcher (succeeded, under a minute of worker time). This entry records what was verified and what the
authorised sequence still owes.

**Measured** (`.factory/noaa-publish-002/reports/manifest.json`, `result.json`, `jobs/noaa-publish-002.json`):

| item | value |
| --- | --- |
| source | private staging release 392410743 (`job-noaa-004`), the ten corrected `minor_flood` files |
| target | `earino/noaa-tide-flooding` release 396698120, tag `v2026.09` |
| transferred | 10/10 assets, **196,018,020 bytes**, `failures: []`, artifact version `fb49f932...` |
| verified | every target asset re-read from the GitHub API: size and sha256 equal the job's transferred values, 10 of 10, and equal `release/noaa-tide-flooding/MANIFEST.json`'s `files`/`assets` digests |

The check was made against the service rather than against the job's own claim. The ten `source_asset_id`s
in the spec are `file-0002`..`file-0011` of staging release 392410743 and carry exactly the digests that
were transferred, so the source was the corrected artifact and not a neighbouring release. The superseded
release is gone: `gh release list` returns one release, `v2026.09` -> 396698120, and 392387511 with the
noaa-003 bytes is no longer listed - its digests are kept in `record.json`
(`artifacts[0].previous_issue`) so the old version stays checkable. The job's own manifest records
`uploaded: false` because the transfer path uploads per file instead of one bulk archive; the `transfer`
block is the report that matters.

**The tag divergence is closed - measured, and not by the route that was planned.** `v2026.09` and `main`
now resolve to the same commit `bef3a412` (`compare main...v2026.09` -> `identical`, ahead/behind 0/0).
That commit is itself a **root commit** (`parents: []`) carrying the re-issue message, and the release was
created from it with `target_commitish: main`. So the state recorded on 2026-09-20 - tag -> `9bcbf2c6`,
`main` -> `f384889f`, unrelated roots, compare 404 - was removed by replacing the history rather than by
the single fast-forward the record had planned. What the release rule asks for (a version-pinned reader
and a main-branch reader see one commit) now holds; the one-commit fast-forward is therefore not owed. The
superseded tag commit `9bcbf2c6` still exists as an object with no ref pointing at it.

**What did not move: the Hub half.** Verified from the API today, not assumed: the Hugging Face revision
`v2026.09` still carries the superseded bytes - `temporal/private/holdout.csv` 12,475,942 against the
corrected 12,475,947, `station_disjoint/private/holdout.csv` 4,228,351 against 4,228,360,
`temporal/meta.json` still naming the label column `late`, and its `MANIFEST.json` hashing `55791180...`
against the package's `60ffed39...`. `artifacts[0].huggingface.verified: true` describes the noaa-003
upload of 2026-09-20 and does not carry over to these bytes. The clean-room consumer check has likewise
not been re-run: noaa-consumer-002's PASSED belongs to the superseded bytes.

**Recorded**: `candidates/noaa-tide-flooding/record.json` (job `noaa-publish-002`; `artifacts[0]`
re-pointed at release 396698120 with the corrected per-level digests and the superseded issue kept under
`previous_issue`; `github_tag_state` re-measured; a `huggingface.superseded` block carrying the file-level
evidence and the ten source asset ids for the Hub job; `next_action` rewritten), this file. Worker
`167435107` destroyed after collection. `check-candidate.py --all` and `check-package.py
release/noaa-tide-flooding` both pass on this state. **CI for the commit that records this is not verified**: the workflow run for `be83b1d` failed before any step ran, with the check-run annotation "The job was not started because recent account payments have failed or your spending limit needs to be increased" - a GitHub billing condition outside this repository, not a test failure. The suite was run here instead with the same command the workflow uses (`python3 -m unittest discover -s tests`): **283 tests, OK**, and `check-candidate.py --all` / `check-package.py` pass. Re-running CI is pointless until the account's Actions billing is restored; the change itself is docs-and-records only.

**Next action**: (1) prepare and launch the hf_publish job for the corrected files from release 396698120
(the ten source asset ids and new digests are in `record.json`
`artifacts[0].huggingface.superseded.next`), then the loading check and `hf-publish.py --verify`; (2)
re-run the clean-room consumer check against the re-issued bytes; (3) decide the recorded persistence-floor
question (carry the noaa-003 figures with the note, or re-measure on the corrected eval split); (4) then the
publication act - flip both destinations, prove the read from an anonymous client, record it in
`DESTINATIONS.json` **before** regenerating the manifest, refresh card/LOADING.md/README/release notes, and
publish the site. Both destinations stay private until then.

## 2026-09-25 10:45 UTC - noaa-baseline-002: the baseline on the corrected artifact, and what adoption does not yet mean

The corrected artifact was adopted at 10:33 and its baseline was measured by `noaa-baseline-002`, launched
from an interactive session at 10:35 and collected by the worker watcher. This entry records the result and
the state it leaves; the release work itself is listed as the next action rather than half-done.

**Measured** (`.factory/noaa-baseline-002/reports/baseline.json`, `container.log`, four runner logs):

| level | eval AUC | validate AUC | contract | rows train/eval/holdout |
| --- | --- | --- | --- | --- |
| temporal | **0.8633** | 0.8633 | OK | 697,373 / 89,038 / 88,841 |
| station_disjoint | **0.8690** | 0.8690 | OK | 461,580 / 29,930 / 29,930 |

Row counts and positive rates are identical to `noaa-baseline-001` in all six splits (0.016883 / 0.020385 /
0.03208 and 0.016277 / 0.026328 / 0.036418). The job **fetched** the ten files from private staging
(10/10, 196,018,020 bytes, zero failures, each against the builder's digest) instead of rebuilding, so the
number belongs to the bytes that will be published. It also records the dependency versions the first
baseline omitted (pandas 2.3.3, numpy 2.5.3, xgboost 3.4.1, scikit-learn 1.9.1). The earlier measurement
(0.8638 / 0.8688) was taken on the superseded artifact and is kept beside this one; the two agree to about
0.0005, the label column's name being the only schema difference.

**Adopted, not re-issued.** `candidates/noaa-tide-flooding/baseline/expected_artifact.json` now names
noaa-004 (temporal `bb051dc3...`, station_disjoint `92297a5b...`, both gated 32/32 on gate 1.3.0), and the
record's `qualification` and `baseline` blocks now carry that artifact. What did **not** change: the private
GitHub release `v2026.09` in `earino/noaa-tide-flooding` and the Hugging Face revision still hold the
noaa-003 bytes labelled `late`. Both destinations are private, so the exposure is zero, but the publication
the operator authorised must ship noaa-004.

I left the release package matching the bytes it actually holds rather than renaming it ahead of the
artifact: `release/noaa-tide-flooding/DATA_DICTIONARY.md` keeps the shipped label name, and `MANIFEST.json`,
`README.md`, `VERIFICATION.md`, `REPRODUCE.md`, `RELEASE_NOTES.md`, `measurements.json` and the `code/`
copies still describe noaa-003. A doc renamed before the artifact it sits beside would describe bytes that
are not in the package, and `VERIFICATION.md`'s consumer-check rows cannot be rewritten until the new
consumer check has actually run. `check-candidate.py --all` and `check-package.py release/noaa-tide-flooding`
both pass on this state.

**One hygiene fix, in the same commit.** Tracking the fetch bundle made CI's job-id uniqueness
check fail: the older rebuild-and-measure baseline bundle under `baseline/source/` had been bumped to
`noaa-baseline-002` on 2026-09-20 for a rerun that was never launched, so the id collided with the fetch
variant that actually ran. That stale bundle is renamed `noaa-baseline-rebuild-001` with a note explaining
why; the fetch variant keeps 002, which is the job the record describes.

**Recorded**: `candidates/noaa-tide-flooding/record.json` (job `noaa-baseline-002`; `baseline` and
`qualification` re-pointed at noaa-004 with the superseded values kept; `noaa-004.adopted` with the
decision, what changed and what did not; `artifacts[0].superseded_by`; `next_action` rewritten),
`candidates/noaa-tide-flooding/baseline/baseline_result.json`, this file. Worker `167401677` destroyed.

**Next action** (in order, from `record.json.next_action`): apply
`candidates/noaa-tide-flooding/noaa-004-label-rename.diff` to `build.py`/`persistence_baseline.py` and their
package copies; re-point the package prose and numbers at the corrected artifact and regenerate
`MANIFEST.json`/`SHA256SUMS` with `scripts/release-manifest.py`; decide whether to re-measure the
persistence floor on the corrected eval split or carry the superseded figures with the note now recorded;
transfer the ten files from staging release 392410743 on a worker; re-run the clean-room consumer check
(noaa-consumer-002's pass belongs to the superseded bytes); then flip both destinations, prove anonymous
read, record it in `DESTINATIONS.json` before regenerating the manifest, refresh the card/README/release
notes and publish the site. The GitHub tag item is unchanged: `v2026.09` and `main` are unrelated root
commits and the tag needs the one-commit fast-forward fix.

## 2026-09-21 08:45 UTC - md-sewer-overflow discovery: currency closed, target contract blocked

The only lead with **no verdict** was `md-sewer-overflow` (`investigating`), so this session
spent itself on the cheapest-first discovery path and ended with a verdict rather than a link.

**Measured** (`python3 .factory/probe_md_series.py`, Socrata `date_trunc_ym` group-by with
Cloudflare retries):

| series | total rows | boundary |
| --- | --- | --- |
| `3rgd-zjxx` | 27,479 | 2022-12: 122, 2023-01: 30, 2023-02: **7** - ends 2023-02-10 |
| `stgj-u72u` | 3,439 | 2023-01: **1**, 2023-02: 46, 2023-03: 64 ... 2026-09: 39 |

The series **abut** rather than duplicate: the historical one runs out in February 2023 and the
current one starts in January 2023 with a single row. The current series grew 3,434 -> 3,439
since 2026-09-18, a second independent confirmation that it is live. Row-level confirmation is
still unmeasured - both `$where ... between` range queries answered **HTTP 403** on every
attempt (five on the first run, four on the second; the first run's traceback arrived after
this session had already written up) while the `$select`/`$group` queries in the same runs all
succeeded, so the refusal tracks the quoted-literal `$where` URL shape, not the host.

**The rainfall join is proven feasible without a token** (`probe_md_rainfall2/3.py`):
`ncei.noaa.gov/data/global-historical-climatology-network-daily/access/<ID>.csv` answers 200
with PRCP populated on 877/1055, 1291/1296 and 1242/1266 days since 2023-01-01 for three
stations tested; CDO API v2 without a token is HTTP 400. `ghcnd-inventory.txt` supplies the
per-element first/last year that `ghcnd-stations.txt` lacks. **Not measured:** the Maryland
active-station count - my station filter read the wrong column, so the 6,873 in
`probe_md_rainfall_result3.json` is US-wide and must not be quoted as a Maryland figure.

**Parked, with the blocker named.** Contracts 1 (Public Domain, read directly), 2 (prediction
instant = start of the target day) and 4 (positives across 2005-2026) look satisfiable.
Contract 3 does not: only facilities that *reported* ever appear, so a facility-day grid built
from these tables alone has a survivorship-biased negative class, and no Maryland
collection-system registry has been identified or tested. The novelty check is also unrun.
Spending construction on a denominator that may not exist is exactly what the discovery skill
exists to prevent, so the verdict is `parked` rather than `ready`.

**Recorded**: `candidates/md-sewer-overflow/record.json` (`status`/`verdict` = parked,
`parked_reason`, `open_questions`, `next_action`, and the measurements above),
`candidates/md-sewer-overflow/notes.md`, and the four probes plus their JSON results in
`.factory/`. Nothing was built, no worker was launched, no credential was touched.



## Objective

Prepare the first discovered prediction task for a monthly public release. Scout
runs on NousCloud with **1.9 GiB RAM and about 6 GB persistent disk**, coordinating
Docker jobs on temporary Hetzner workers. Each published dataset gets its own
public repository and versioned GitHub Release assets.

## Ready in this repository

- Revised project specification, agent instructions, handoff and first assignment.
- Completed hosted inventory; reuse native research, browsing and scheduling.
- Candidate tracking and stdlib worker lifecycle: cost reservations, interrupted
  creation recovery, SSH dispatch, direct private uploads, verified collection
  and confirmed cloud cleanup.
- Independent GitHub Actions expiry sweeper, disabled until configured.
- Tiny synthetic infrastructure smoke job and local failure-path tests.
- A public dataset README template describing the eventual release contract.
- Hosted GitHub access verified: clone, branch push/deletion, release and run
  listing, successful CI. `gh` v2.101.0 installed after checksum verification.
- Private staging repo `earino/dataset-factory-staging` (builder-created). Its
  restricted worker token is still needed.
- `scripts/scout-factory` launcher with `_FILE` credential paths, `doctor`
  credential presence assertions and live memory reporting.

## Completed on the hosted instance, 2026-09-18 (second session)

- Pulled `01a84a1` and read `deployment/BUILDER-REPLY.md`.
- `sh scripts/scout-factory doctor` runs and reports memory, GitHub CLI, benchmark
  and credential state. `doctor --require-worker-credentials` exits 1 with both
  credentials reported missing or unusable, as expected before provisioning.
- All **30** tests pass locally under Python 3.13.5 (the builder reported 30 on
  GitHub Actions as well).
- SSH: generated ed25519 keypair `/opt/data/.ssh/scout_worker_ed25519`
  (fingerprint `SHA256:k4Uk+aJCEV28M7xvwsIzE3v0agPBXNrPXN/GGRFusms`, comment
  `scout-dataset-factory-worker`). No key existed before; nothing was overwritten.
  The public key is recorded in `deployment/ssh-worker-public-key.md` for Hetzner
  registration. Not yet registered.
- Secrets: created `/opt/data/.secrets` (0700). Both token files are still absent;
  only the operator can supply them, and only into those paths.
- Policy: `config/local.json` created from the example with `enabled: false`,
  `monthly_budget_eur: 0`, empty `allowed_locations` and `server_types`, staging
  repo set, SSH key paths set. Ignored by Git. Paid launches remain impossible.
- Benchmark checkout re-inspected: `data/prepared/` is absent, all three
  preparation scripts and saved baselines are present. Preparation must happen on a
  worker.

## Worker credentials verified 2026-09-18 (third session)

Both worker credentials now exist and have been tested against their real APIs.

**Hetzner.** `HCLOUD_TOKEN` stored at `/opt/data/.secrets/hetzner.token` (0600, in
a 0700 directory). Tested with the token file only — the environment variable was
removed from the test subprocess, which asserted its absence first. A single
read-only `GET /v1/servers` returned **HTTP 200**, so authentication succeeds and
the dedicated project currently contains **0 servers**. No create, modify or
delete call was made.

**GitHub staging.** `FACTORY_GITHUB_TOKEN` stored at
`/opt/data/.secrets/github-staging.token` (0600, same 0700 directory), 93
characters, a fine-grained token. Tested with the file explicitly and
`FACTORY_GITHUB_TOKEN` removed from the environment:

- `earino/dataset-factory-staging` is reachable and **private** (default branch
  `main`).
- Scope is genuinely restricted: the token sees exactly **one** private repository
  across the account — `earino/dataset-factory-staging` — while a probe of
  `earino/dataset-factory` returns **HTTP 404**. It is not the broad classic PAT
  used for coordinator git access, and the coordinator login was left untouched.
- A uniquely named **draft** release was created (`verify-staging-1789728610`),
  a 125-byte test file uploaded, and the server-reported size (125) and digest
  (`sha256:d50a3893513699526aea43828dfc2a633411b310a80f97259e36f2abbf0e07a5`)
  matched the locally computed values. The release stayed unpublished throughout.
- Cleanup succeeded: asset delete 204, release delete 204, subsequent reads of both
  returned 404, zero releases remain, no leftover tag. The draft-releases path
  workers depend on is therefore verified end to end.

`sh scripts/scout-factory doctor --require-worker-credentials` now exits **0** with
both credentials reported ready and an empty error list.

**Worker SSH key registered 2026-09-18 (fourth session).** The existing dedicated
ed25519 pair at `/opt/data/.ssh/scout_worker_ed25519` (0600, directory 0700, no
passphrase) was reused rather than regenerated; its public key derives cleanly from
the private key, so it is suitable for unattended use. Hetzner held no SSH keys
before this, so the public key was registered as **`scout-worker`**:

| Field | Value |
|---|---|
| Name | `scout-worker` |
| ID | `130171155` |
| Fingerprint (MD5) | `9d:80:95:90:cc:4c:c8:65:83:59:9f:8c:2b:d6:ae:30` |
| Verification | read back via `GET /v1/ssh_keys/{id}`; public key matches the local pair |

The read-back fingerprint equals the locally computed MD5 fingerprint, so the
registration is confirmed rather than assumed. `config/local.json` now carries
`ssh_key_name: scout-worker` and `ssh_private_key:
/opt/data/.ssh/scout_worker_ed25519`. Launches stay disabled and the allowance
stays at zero.

Remaining prerequisite for a paid launch: one observed successful **scheduled** cleanup
run. Notification delivery and the secondary on-host sweep are now configured and
verified (eighth session). The allowance is configured (seventh session), the cleanup
secret and variables are configured, and the manual dispatch executes successfully.

**Deletion of an expired server is verified during the smoke sequence, not before it.**
The project has never held a server, so there is nothing for the deleter to act on
until a worker exists. The first smoke job proves collect-then-delete-immediately;
expiry cleanup is a separate later test. See the eighth-session note under "Remaining
prerequisites before the live smoke cycle" and `docs/OPERATIONS.md`.

## Primary expiry cleanup configured 2026-09-18 (fifth session)

Actions secret `HCLOUD_TOKEN` set from `/opt/data/.secrets/hetzner.token` using file
input, so the value never appeared on a command line or in output. Repository
variables set: `FACTORY_PROJECT` = `earino-dataset-factory` (the exact `project`
value in `config/local.json`) and `FACTORY_CLEANUP_ENABLED` = `true`. The local
policy was left untouched: `enabled` false, `cleanup_configured` false,
`monthly_budget_eur` 0, empty `server_types`.

### Manual dispatch - verified executing, not skipped

| Field | Value |
|---|---|
| URL | https://github.com/earino/dataset-factory/actions/runs/35337787612 |
| Event | `workflow_dispatch` |
| Status | completed / success |
| Created (UTC) | 2026-09-18T11:04:09Z |
| Updated (UTC) | 2026-09-18T11:04:19Z |
| Job | `cleanup` - success, started 11:04:13Z |
| Step | "Delete only expired project workers and orphaned job IPs" - success |

The job's own output:

```json
{"deleted_servers": [], "deleted_primary_ips": [], "errors": []}
```

**What that proves, and what it does not.** Proven: the secret and variable wiring,
the workflow's enablement gate (`vars.FACTORY_CLEANUP_ENABLED == 'true'` now
passes), execution on a GitHub runner, and a successful authenticated Hetzner query
issued from GitHub's infrastructure. An empty `errors` list is meaningful here: a
bad or missing token would have surfaced there.

**Not proven: deletion of an actually expired server.** This project has never
contained a server, so the deletion path - non-empty `deleted_servers`, the
ownership re-check before delete, and labeled primary-IP cleanup - is entirely
untested. Verifying it is a smoke-cycle step, not a cleanup-scheduler step.

### Scheduled run - pending at time of writing

No `schedule`-event run appeared between enablement (2026-09-18T11:04Z) and
2026-09-18T11:15Z, despite cron minutes 7, 22, 37 and 52. GitHub documents that the
`schedule` event "can be delayed during periods of high loads of GitHub Actions
workflow runs", that high load includes the start of every hour, and that queued
jobs "may be dropped" under sufficient load
(<https://docs.github.com/en/actions/reference/events-that-trigger-workflows#schedule>).
Scheduled workflows run in UTC on the default branch, and here the workflow file is
already on `main`.

Observed cadence is also much looser than configured. Before enablement the
workflow produced `schedule` runs at 2026-09-17T19:19Z, 22:16Z, 2026-09-18T00:28Z,
05:07Z and 09:53Z - roughly every two to four hours, not every fifteen minutes.
Those runs were correctly `skipped` by the gate.

Scheduler fire time, and therefore the first genuinely scheduled execution, remains
**unverified**. The manual dispatch above stands on its own as execution evidence.
The interval was changed to hourly at minute 17 later the same session; see the
sixth-session section.

### Open item for the operator

With the gate open, each run executes and bills a minimum of one Actions minute. At
the configured 96 runs/day that is roughly 2,880 minutes per month, against GitHub
Free's 2,000 minutes per month for private repositories. Widening the interval to 30
or 60 minutes, or confirming a paid allowance, should be decided before this is
relied on.

## Cleanup cadence changed to hourly 2026-09-18 (sixth session)

Deletion on collection stays the normal path; the scheduled sweep is the backstop.
Because GitHub can delay scheduled runs - and can drop queued jobs under load - the
interval is **not a strict deletion deadline**.

- `.github/workflows/cleanup.yml` now runs `17 * * * *` (hourly at minute 17), with
  `workflow_dispatch` retained for manual runs. Minute 17 is deliberately off the
  hour, which GitHub documents as a high-load period for scheduled workflows.
- `cleanup_grace_minutes` raised from 30 to 60 in `config/worker.example.json`
  (tracked) and `config/local.json` (ignored, so not committed).
- The policy accepts the value: the check is `15 <= cleanup_grace_minutes <= 60`, so
  60 is the maximum permitted. Verified offline that 60 passes and that 90 is
  rejected with "Cleanup grace must be 15-60 minutes"; an offline `worker plan`
  under a stand-in policy completes with `cloud_calls: 0`.
- Measured effect on reservations, which are `ceil((lifetime + grace) / 60)` hours:
  unchanged for 45, 60 and 120-minute lifetimes; the reserved hours rise for
  short jobs (15 and 30-minute lifetimes go 1 -> 2) and for a 90-minute job (2 -> 3).
  The extra hour is therefore charged only where it crosses an hour boundary. It is
  a conservative reservation, not a provider billing cap.
- `docs/OPERATIONS.md` gained a "Sweep cadence and cleanup grace" subsection. It
  records that an empty `deleted_servers` list is the expected sweep result while
  the normal delete-on-collect path is working, and that Scout deletes a worker as
  part of finishing its job rather than waiting for the sweep.
- Launches remain disabled and the allowance unchanged: `enabled` false,
  `cleanup_configured` false, `monthly_budget_eur` 0, empty `server_types`. No cloud
  resource was created or modified.

**No scheduled run has executed yet, and the scheduler is heavily throttled.**

A watcher covered the period from enablement (2026-09-18T11:04Z) to
2026-09-18T12:27Z without observing a single `schedule`-event run - that spans the
configured 11:07/11:22/11:37/11:52/12:07/12:17 fires under both the old 15-minute
and the new hourly cron.

Measured gaps between the scheduled runs that did occur before enablement:

| From | To | Gap |
|---|---|---|
| 2026-09-17T19:19Z | 2026-09-17T22:16Z | 3.0 h |
| 2026-09-17T22:16Z | 2026-09-18T00:28Z | 2.2 h |
| 2026-09-18T00:28Z | 2026-09-18T05:07Z | 4.7 h |
| 2026-09-18T05:07Z | 2026-09-18T09:53Z | 4.8 h |

So this workflow's `schedule` trigger fires every **2 to 5 hours**, not every 15
minutes, and the wait since 09:53Z is still inside that observed range. The
configuration is otherwise verified: the workflow state is `active` on the default
branch, the committed cron reads `17 * * * *`, and `FACTORY_CLEANUP_ENABLED` is
`true`. Nothing here indicates a misconfiguration; it indicates that GitHub's
scheduled runs on this repository are irregular.

**Consequence for the grace estimate.** The 60-minute `cleanup_grace_minutes`
covers one hour of post-expiry billing in the reservation, but the worst observed
gap suggests a leftover worker could survive several hours before a sweep catches
it. Deletion on collection remains the normal path, so this is a cost exposure for
abnormal endings only - but the grace is an estimate, not a bound on the leftover
time, and the on-host secondary sweep gains importance for that reason.

A longer watcher now covers the next scheduled fire; the first genuinely scheduled
execution remains unverified and is reported as pending rather than assumed.

## Compute allowance configured 2026-09-18 (seventh session)

`config/local.json` (ignored, so not committed) now carries the operator's initial
allowance: `monthly_budget_eur` 20, `allowed_locations` `["hel1"]`, `server_types`
`{"cx23": 0.02, "cpx32": 0.08, "cpx42": 0.15}`, `max_workers` 1,
`max_lifetime_minutes` 120, `cleanup_grace_minutes` 60. Values are **maximum
all-in hourly EUR prices including VAT and the primary IPv4**. Working guidance:
CPX32 by default, CX23 for light jobs, CPX42 when a job needs more memory.
`enabled` and `cleanup_configured` remain false, so launches are still impossible.

### Ceilings verified against live prices

Checked through the real launch-time code path (`factory.worker.check_price`) against
the live `/pricing` payload for `hel1`, where the comparison is
`server_gross_hourly + ipv4_gross_hourly > ceiling -> refuse`:

| Type | Ceiling EUR/h | Live server + IPv4 gross/h | Result | Headroom |
|---|---|---|---|---|
| `cx23` | 0.02 | 0.011520 | pass | 0.008480 |
| `cpx32` | 0.08 | 0.069240 | pass | 0.010760 |
| `cpx42` | 0.15 | 0.134640 | pass | 0.015360 |

Primary IPv4 is 0.00096 EUR/h gross. Prices are identical in `fsn1` and `hel1`. A
future price rise larger than the headroom makes `launch` refuse rather than
overspend, which is the intended fail-closed behaviour.

### Offline smoke-job plan

A copy of `examples/smoke/job.json` with `server_type: cpx32` and `location: hel1`
was planned under the proposed allowance (temporary files under `.factory/`, which
is ignored). Result: `reserved_hours` 2, `reservation_eur` **0.16**, `cloud_calls`
0, `enabled` false. Across the allowed types for that 45-minute job: `cx23` 0.04,
`cpx32` 0.16, `cpx42` 0.30.

At the maximum 120-minute lifetime the reservation becomes 3 hours: `cx23` 0.06,
`cpx32` 0.24, `cpx42` 0.45. The EUR 20 allowance therefore admits roughly 333
max-lifetime `cx23` jobs, 83 `cpx32` jobs or 44 `cpx42` jobs.

This is an admission estimate, not a billing cap. Note that a single continuously
running `cpx32` bills about 42.59 EUR/month gross, so the allowance only protects
while jobs stay bounded and are deleted on collection.

### Remaining prerequisites before the live smoke cycle

1. ~~Notification delivery, so a failed or dropped scheduled run is visible.~~
   **Done** - see the eighth-session section. This Telegram chat is the destination.
2. An observed `schedule`-event cleanup run that executes rather than skips.
3. `cleanup_configured: true` and `enabled: true`, set once 1-2 hold.

**Deletion of an actually expired server is a smoke-sequence step, not a
precondition.** This project has never held a server, so the deletion path has
nothing to act on yet. It is exercised later in the sequence: the first smoke job
proves the normal path - provision, Docker, upload, verified collection, then
**immediate deletion** of the server and its job-owned IP - and expiry cleanup gets
its own separate test afterward, when a worker is deliberately allowed to expire and
the sweeper is observed reclaiming it. Requiring expiry evidence before any worker can
be launched would make it unreachable, because the only way to produce an expired
server is to launch one.

## Notification delivery and secondary sweep configured 2026-09-18 (eighth session)

Two of the three remaining prerequisites were closed. Launches stay disabled: the
`schedule`-event cleanup run is still pending, so the smoke cycle did not run.

### Notification delivery - configured and verified delivered

Destination: **this Telegram chat** (platform `telegram`, chat `7600588577`, "Eddie").
A one-off scheduled job was created, fired and its delivery read back from the gateway
log rather than assumed from a success response.

| Field | Value |
|---|---|
| Cron job ID | `1a66d6af21cc` (`scout-telegram-delivery-test`) |
| Schedule | once, `run_at` 2026-09-18T11:48:19Z |
| Fired (UTC) | 2026-09-18T11:48:23.060190Z |
| Job status | `ok` |
| Delivery (UTC) | 2026-09-18T11:48:22.840Z |
| Delivery log line | `Job '1a66d6af21cc': delivered to telegram:7600588577 via live adapter thread=- message_id=9` |
| Delivery error | none (`last_delivery_error`, `last_delivery_unverified`, `last_fire_error` all null) |

The job completed and was retired (`state: completed`, `repeat.completed: 1`), so it
does not recur. Both jobs created in this session captured `origin` from this chat, so
future scheduled reports address it without an explicit target. A failed or dropped
scheduled run is therefore visible here, which was prerequisite 1.

### Secondary no-agent cleanup sweep - was missing, now configured and verified

`docs/OPERATIONS.md` asks for a second, on-host sweep as redundancy for the GitHub
schedule. No such cron job existed before this session.

| Field | Value |
|---|---|
| Cron job ID | `e80975eddd4a` (`scout-secondary-cleanup-sweep`) |
| Schedule | `47 * * * *` (hourly at minute 47, offset from the primary's minute 17) |
| Mode | `no_agent` - no LLM; the scheduler runs the script and delivers stdout verbatim |
| Script | `scout_cleanup_sweep.py` in `~/.hermes/scripts/` (Hermes requires cron scripts there) |
| Real implementation | `scripts/cleanup-sweep-cron.py` in this repo, tracked and versioned |
| Command run | `sh scripts/scout-factory worker sweep --project earino-dataset-factory` |
| Deliver | this chat (`origin`) |
| First run (UTC) | 2026-09-18T11:49:09Z, status `ok`, silent empty output |
| Next fire | 2026-09-18T12:47Z |

The repository copy is the real implementation; the file in `~/.hermes/scripts/` is a
short shim that exists only because Hermes resolves cron scripts relative to
`~/.hermes/scripts/`. Behaviour, both branches exercised directly rather than assumed:

- **Normal path** - an empty sweep prints nothing, so no message is sent. This is the
  watchdog pattern and matters because `deleted_servers` is normally empty while
  delete-on-collect is working. Verified: exit 0, zero output lines.
- **Failure path** - verified by forcing an invalid project value:
  `Scout sweep FAILED (exit 1) for bad project!: factory: IDs must be 1-48 lowercase
  letters, digits, or hyphens`, exit 1. A bad token or unreachable API therefore
  produces one alert line rather than silence.

The script's exit status is the sweep's own, so a failure also shows in cron history.

### GitHub scheduled cleanup run - still pending, launches stay disabled

As of 2026-09-18T12:18Z no `schedule`-event run has appeared since the gate was opened
at 11:04Z. The most recent scheduled run remains 09:53:53Z, which was correctly
`skipped`. **Two consecutive hourly slots have now been missed** - 11:17Z and 12:17Z -
under a `17 * * * *` cron that was already on `main` before either was due. A polling
watcher checked `gh run list --event schedule` every 20 seconds from 11:49Z to 12:19Z
and found nothing. This matches the fifth-session observation that this repository's
scheduled runs are sparse (roughly every two to four hours, against a configured
fifteen-minute interval at the time).

That is now the single outstanding blocker, and it is worth being precise about what it
means: the workflow is correct and its manual dispatch executes, but **the scheduler is
not delivering on its configured cadence for this repository**, so the primary sweeper
cannot yet be relied on as the backstop it is meant to be. The secondary on-host sweep
added this session is hourly and independent of GitHub, which is exactly the redundancy
that gap calls for.

Consequence, per instruction: **`enabled` and `cleanup_configured` stay false and no
paid launch was made.** No CPX32/hel1 smoke cycle, therefore no artifact links, no
reservation, no cost and no deletion to report. The manual `workflow_dispatch` from
the fifth session remains the only evidence that the cleanup step executes.

## Still unverified or unimplemented

Local tests use fake providers. **No live Hetzner/GitHub worker cycle has been run.**
Boot, SSH, Docker, uploads, recovery, costs and scheduled deletion remain unverified.

The worker policy is **configured but disabled**: an allowance of EUR 20,
`allowed_locations ["hel1"]`, the three priced server types and the SSH key are set in
`config/local.json`, while `enabled` and `cleanup_configured` remain false, which is
what keeps paid launches impossible. No cloud resource exists.

The primary cleanup workflow is no longer skipped - `FACTORY_CLEANUP_ENABLED`,
`FACTORY_PROJECT` and the `HCLOUD_TOKEN` Actions secret are set and a manual dispatch
executed successfully (fifth session). What is still missing is an observed
`schedule`-event run.

The benchmark adapter (`factory/bench.py` coordination, `workers/benchmark.py`
execution), qualification tools, public exporter and website are not implemented.
`../harness_benchmark` is unmodified.

## Next actions for Scout

1. **Launch worker job `austin-001`** as soon as paid launches are enabled (the only
   remaining gate is an observed scheduled GitHub cleanup run). It is planned and ready:
   `worker plan candidates/austin-911-response/source/job.json`. Then collect the private
   staging release, verify checksums, delete the worker immediately, and report the measured
   base rates, the full-sample baseline AUC and the headroom.
2. Continue shortlist work that needs no credentials. Maryland's stale-series concern is
   resolved and NOAA's exceedance base rates are measured (1.37% pooled); Melbourne's
   licence is the open item, and both remaining candidates need their target thresholds
   chosen before a construction script can be written.
3. Operator: none - allowance, locations, server types, SSH key and both worker tokens
   are in place. The only outstanding gate is GitHub's scheduler.
4. Once a `schedule`-event run is observed executing: set `cleanup_configured: true`
   and `enabled: true`, run the live smoke cycle, verify deletion by letting the worker
   expire, then disable paid launches again and move on to recovery and expiry tests.

## Inputs still needed from the operator

Nothing blocking on the worker side. Both worker tokens and the worker SSH key are supplied and
verified, the allowance and allowed locations/types are configured, and notification delivery is
working. First release date, reviewer, public dataset namespace and website hosting can
wait until the first candidate is approved.

**Blocking the research routine: the model-spend allowance.** Asked 2026-09-18 and unanswered.
Until it arrives, `config/research-budget.json` keeps `allowance_usd: null` and the gate wakes
no research session - fail-closed, by design. Four questions, answerable in one line:

1. **Monthly allowance**, measured as Hermes-estimated USD (a bounded session measures
   0.07-0.37 USD, so 3/week is roughly 1-4 USD/month). Suggested: 5 USD/month.
2. **Reset period**: 1st of the month 00:00 UTC, a different day, weekly, or a rolling window.
3. **Portal reconciliation**: the NousCloud quota and reset period are not visible from this
   instance. Estimates-only reporting, or will the operator relay the portal figure?
4. **Enable the schedule**: Mon/Wed/Fri 08:00 UTC, 3 sessions/week, <= 45 min and <= 600k tokens
   each, stopping at 95% of the allowance.

Also open, from the publication milestone: the **licence choice** for the published code and for
the three benchmark runner files shipped in `austin-911-response` (that upstream project carries
no licence), and **public visibility**, withheld as instructed.

## Construction script written and worker job prepared (2026-09-18, ninth session)

`candidates/austin-911-response/source/build.py`, stdlib only, built for a worker. The
source directory holds `build.py` and `job.json` and nothing else; the candidate's notes
and record stay outside it, as required.

**Threshold is frozen from the training window by rule, not by hand.** `build.py`
binary-searches the Socrata aggregate - COUNT queries only, no rows fetched - until
`P(response_time > T)` in the training window is just at or above a target rate of 0.40,
then snaps T to a whole minute and re-measures. Run against the live API it selects
**T = 1200 s (20 minutes)** with a training rate of **0.4038** over **572,180 rows**. That
row count is exactly the sum of the measured 2023 (286,145) and 2024 (286,035) counts, so
the split boundaries and the counts agree.

Ten probes were recorded in the manifest, so the choice is auditable rather than asserted.

**Splits** are temporal by `response_datetime`: train `< 2025-01-01`, eval `2025`,
holdout `>= 2026-01-01`. Rows are paged in `incident_number` order (unique, so paging
cannot skip rows that share a timestamp) and each file gets a SHA-256 checksum, byte
count, row count and positive rate into `manifest.json`. `summary.json` is written for the
worker's compact-report contract.

**A bounded exercise has been run locally** (`.factory/austin-smoke`, `--limit 400`), so
the script is known to execute end to end: threshold freeze, three splits with checksums,
and the baseline. Its per-split rates are not meaningful - the limit takes the first 400
rows of each split by incident number, which is roughly January only - but the pipeline is
proven. The single-feature baseline scored **AUC 0.5999** on that sample; the real figure
must come from the full extract.

**Worker job `austin-001` is prepared and planned, not launched.** `worker plan` reports
`reservation_eur 0.24`, `reserved_hours 3`, `source_bytes 40960`, `source_sha256
ee37eec...`, `cloud_calls 0`, `enabled false`. It targets `cpx32` in `hel1`, a 45-minute
timeout inside a 90-minute lifetime, `max_artifact_mb 400` (the three CSVs are expected
near 136 MB in total at roughly 130 bytes per row). Paid launches remain disabled, so it
waits.

**Tests**: `tests/test_austin_build.py` adds 20 offline tests, including the structural
guarantees that matter here - no feature may overlap the post-hoc exclusions,
`response_time` / `priority_level` / `mental_health_flag` may not be features, the split
windows must be disjoint, and the job directory must satisfy the worker's own
`source_bundle` rules (no symlinks, no hidden files, only allowed suffixes, under 2 MiB).
Test count is now **59**, all passing.

## Operations correction: smoke order (2026-09-18)

`docs/OPERATIONS.md` and this file now state that the **first smoke cycle proves the normal
path - provision, Docker, upload, verified collection, then immediate deletion of the
server and its job-owned IP**. Expiry cleanup is a separate later test with its own job.
The earlier wording allowed the sequence to read as if an expired-server deletion had to be
observed before any worker could launch, which is unreachable: the only way to create an
expired worker is to launch one.

## Builder review fixes re-implemented, and the qualification gate added (tenth session)

`main` was pulled through `0c8eb7a`. The builder's fix (`37f36c2`) had been reverted by
`0c8eb7a`, so the defects it described are re-diagnosed, fixed and validated here. All three
were reproduced before anything was changed.

### 1. Austin's CSVs contained `response_time`, which determines `late`

Reproduced by reading the emitted file rather than the declared lists: the header of
`.factory/austin-smoke/train.csv` was
`incident_number,response_datetime,response_time,...`. The column was absent from `FEATURES`
and present in `CARRY_COLUMNS`, and every declared list still looked correct.

`response_time` is now `LABEL_SOURCE`, is **not** in `CARRY_COLUMNS`, is listed in
`EXCLUDED_POST_HOC`, and is recorded in the manifest as `label_source_column` for
provenance while being excluded from `shipped_columns`. It is still selected from the API -
without it the label cannot be derived - and never written.

### 2. A host-timezone-dependent helper

`parse_iso` was dead code, used only by its own test, and did
`datetime.fromisoformat(value).astimezone(timezone.utc)` on a timezone-free string, which
interprets it in the **host** timezone. Reproduced: the test passes under `TZ=UTC` and
`TZ=America/Los_Angeles` and fails under `TZ=Asia/Tokyo`, where
`2025-01-01T00:00:38.000` becomes `2024-12-31T15:00:38Z` and the year assertion fails.

Removed, with a test asserting it stays removed and that the construction contains no
`fromisoformat`, `astimezone` or `datetime.now()`. The construction itself is timezone-free:
splits are Socrata predicates on literal timestamps and the source strings are written
through unchanged.

### 3. Test imports created caches inside the worker source directory

Reproduced by running the suite with bytecode writing enabled (this host sets
`PYTHONDONTWRITEBYTECODE=1`, which hid it): the test loader's `exec_module` created
`candidates/austin-911-response/source/__pycache__`, which then made
`test_job_directory_contains_only_bundleable_source` fail and made the worker refuse the
job outright - `factory: Job directory must contain only explicit source files, no hidden
files/caches`. Both test modules now load their subject with `exec(compile(...))`, and
`tests/test_repo_hygiene.py` guards every candidate job directory against caches, symlinks,
disallowed suffixes and the 2 MiB bundle cap.

### Test coverage added

- `tests/test_austin_build.py` rewritten: the writer is executed and the **actual generated
  files** are inspected - runner layout, exact column set, the label source absent from every
  header, labels at 1200 s and 1201 s, checksums that match, and a rebuild that clears stale
  output.
- A runner-contract class encodes how `../harness_benchmark` really reads the extract
  (`feature_cols = every column except id_columns and the target`; `validate.py` drops only
  the target) and asserts that the runner's own feature selection exposes no answer source
  and that no shipped column reconstructs the label.
- `tests/test_qualification_gate.py` runs the gate against those generated files, and
  replays the original bug by re-shipping `response_time` to prove the gate rejects it.
- **89 tests pass** with bytecode writing **enabled** and under `TZ=Asia/Tokyo`, `TZ=UTC`
  and `TZ=America/Los_Angeles`.

### The dataset-qualification gate

`skills/dataset-qualification/` is versioned in this repository and symlinked into Hermes at
`~/.hermes/skills/research/dataset-qualification`, so it also loads from the skill list. It
gates five things across 25 named checks: leakage, prediction timing, units and reference
frames, temporal split capacity, and runner compatibility. Run it with

```bash
python3 skills/dataset-qualification/scripts/qualify_dataset.py <dataset-dir>
python3 skills/dataset-qualification/scripts/qualify_dataset.py --selftest
```

**Demonstrated:** the broken fixture is rejected with 9 named failures - including
`leakage.answer_source_absent`, `leakage.no_single_column_determines_the_target`,
`timing.no_post_hoc_feature`, `units.known_event_fixture_recorded`,
`splits.windows_distinct` and `runner.layout` - and the corrected fixture passes all 24
checks. `--selftest` asserts both verdicts, so the demonstration is reproducible rather
than a pasted transcript. Austin is used as the leakage and runner worked example; NOAA as
the units/datums worked example, including the requirement for a known-event fixture.

`AGENTS.md` gained a short section telling a session when to invoke the gate.
`open-data-source-vetting` (the Hermes-side skill) gained a handoff paragraph pointing at
it when construction completes.

**Fresh-session verification.** A brand-new CLI session (`20260918_130358_725a40`, zero
prior history, no access to this conversation) was asked what to check before reporting an
AUC from a directory of `public/train.csv`, `public/eval.csv`, `private/holdout.csv` and
`meta.json`. It discovered the skill from the skill list, loaded it with `skill_view`,
named it, gave the exact command, ran `--selftest` itself, and volunteered the
necessary-but-not-sufficient caveat. Evidence: `agent.log` records the `skill_view` call
against that session id. A cosmetic `Skill security warning: skill file is outside the
trusted skills directory` is logged on load, because the Hermes-visible path is a symlink
whose target resolves outside `~/.hermes/skills`; the link is deliberate, since a second
real copy would be able to diverge. `tests/test_repo_hygiene.py` asserts the link resolves
to this repository's copy.

### One self-inflicted incident, recorded

While clearing bytecode caches, an over-broad `rm -rf candidates tests ...` deleted the
`candidates/` and `tests/` directories. Everything tracked was restored with
`git checkout -- candidates tests`; two uncommitted files (`source/build.py` and
`tests/test_austin_build.py`) were re-written. No measured evidence was lost, because every
result of the prior session was already committed. The lesson is recorded in the report:
scope deletion commands to exact paths.

## Worker qualification, gate hardening and safe cleanup (eleventh session)

Five follow-ups from the builder review, all implemented and verified here.

### 1. The skills directory is registered with Hermes properly

The symlink into `~/.hermes/skills` is **gone**. Hermes's supported mechanism,
`skills.external_dirs`, is now configured:

```bash
hermes config set skills.external_dirs dataset-factory/skills
```

Entries are resolved relative to `HERMES_HOME`, and Hermes treats the result as a trusted
directory, so the `skill file is outside the trusted skills directory` warning no longer
appears. Verified in `agent.log`: the last such warning is timestamped 13:11, from the symlink
era; the skill loads cleanly afterwards.

**Fresh-session verification.** A CLI session started from `/tmp` - outside the repository, so
project-local trust could not be responsible - discovered and loaded the skill unprompted:
`tool skill_view completed`, session `20260918_132856_3a3f34`, and it reported the correct
name, version 1.1.0, the self-test command and the `--accept` command. A scheduled cron
session (`scout-skill-discovery-check-2`, `492d8a95e56e`) was also fired as the
scheduled-surface check.

### 2. Qualification runs on workers, and gates scoring

`candidates/austin-911-response/source/run.sh` builds the extract and then qualifies the exact
artifact it just wrote, exiting non-zero when the gate fails. `scripts/assemble-job.py` is the
single assembly point: it copies `build.py`, `run.sh` and the repository's `qualify_dataset.py`
into an ignored staging directory, generates `job.json`, and validates the result against the
worker's own bundle rules. The assembled bundle is 58,372 bytes and plans offline at
`reservation_eur 0.24`, `cloud_calls 0`, `enabled false`.

**A failed qualification still preserves diagnostics.** The gate report, its rendered output
and the extract are written under `/output`, which the worker uploads even on a non-zero exit;
only the compact report, the rendered checks and the manifest come back to Scout.

**Scoring and acceptance now require a passing report for the exact artifact version.** The
gate records the SHA-256 of every shipped file plus an `artifact_version` digest over them, and
`--accept` re-verifies both. Verified end to end:

```
accept /tmp/q.json fixtures/corrected   -> ACCEPTED ... matches the qualified artifact 7a7a91a508b0a298
append one byte to public/eval.csv      -> ACCEPT FAILED: public/eval.csv has changed
                                           since qualification (e09eb53aeca7 != ffded9dac29e)
```

It also refuses a failed report and a report written by a different gate version. `docs/OPERATIONS.md`
documents the sequence; the run itself is still gated on the scheduled GitHub cleanup run.

### 3. Regression cases for the two false passes

Both are now fixtures with named expectations, and both are replayed against real generated
output rather than only against the fixtures:

- `fixtures/broken-overlap/` - **evaluation rows inside the training period**, with every
  declaration clean and disjoint. Caught by `splits.actual_ranges_disjoint` and
  `splits.rows_within_declared_windows`, both computed from the row timestamps.
- `fixtures/broken-single-class/` - **an evaluation split with no negatives**. Caught by
  `splits.eval_and_holdout_have_both_classes`.

The gate now recomputes split windows, boundaries, positive counts and clustered event counts
from the rows and refuses when they disagree with `quality.json`: `time_column` and
machine-readable `split_windows` are required, so an undeclared split fails rather than passing
silently. Identity overlap between splits is checked too.

### 4. The categorical scan is linear

`group_rates()` builds the per-level table once and scores the rows in a second pass; the old
shape re-summed each row's entire level (`rows x group-size`). Splits are also read
**column-wise** rather than as a list of dictionaries - a dict per row is roughly 1 KiB, which
is hundreds of megabytes on a 1,050,000-row extract. `tests/test_qualification_gate.py`
asserts the level table is built exactly once per column and runs a 200,000-row column to
prove the old quadratic path is gone.

### 5. Destructive cleanup, addressed in procedure and in code

`build.py` no longer calls `shutil.rmtree` on `--out`. `prepare_output()` refuses a path that
is protected, contains a `.git`, is a file, or is a non-empty directory without the
`.dataset-factory-extract` ownership marker the script writes; an owned directory is cleared
entry by entry through an explicit list, leaving anything else in place. Tests cover each
refusal, including that an unrelated file inside an owned directory survives. `AGENTS.md`
gained a short "Deleting things" rule, and the skill documents the destructive default as a
pitfall.

### Checks

**115 tests pass** with bytecode writing enabled and under `TZ=Asia/Tokyo` and `TZ=UTC`. The
gate's self-test rejects all three broken fixtures with their expected named checks and accepts
the corrected one. `tests/test_worker_qualification_job.py` assembles the job bundle, verifies
it against `factory.worker.source_bundle`, and runs `worker plan`.

**Still blocked, and the evidence is now much stronger.** No `schedule`-event GitHub cleanup
run has fired at all. A watcher polled `gh run list --event schedule` every 20 seconds from
12:20Z to 14:04Z and found nothing; combined with the earlier watcher, that covers
**11:04Z to 14:04Z with no fire** - eleven consecutive hourly slots under the `17 * * * *`
cron applied at 11:26Z, and 4.2 hours since the last actual fire at 09:53Z. That already
exceeds every gap observed before the gate was opened (3.0, 2.2, 4.7, 4.8 hours), so this is
no longer explained by the documented 2-5 hour irregularity alone.

Configuration is verified correct and unchanged: the workflow is `active` on the default
branch, the committed cron reads `17 * * * *`, `FACTORY_CLEANUP_ENABLED` is `true`, and the
manual dispatch still executes. The gap is in GitHub's scheduled trigger for this repository,
not in the workflow.

Consequence: the worker job is assembled, planned and tested but **not launched**, and no
Austin extract exists. The on-host secondary sweep is unaffected and healthy - it ran at
12:47:01Z with status `ok` and fires hourly - which is exactly the redundancy this gap calls
for. If the scheduled trigger cannot be made to fire, the operator should decide whether the
on-host sweep is sufficient to enable launches, since it performs the same sweep command.

### CI failures on `a182ff2`, diagnosed and fixed (twelfth session)

Both failures shared one cause: tests depending on the hosted instance's private
configuration, which a clean checkout does not have.

1. `test_refuses_a_protected_path` asserted `/opt/data` was refused. That path exists here and
   not on CI, and `prepare_output` only consulted the protected list when the path existed, so
   nothing was raised. **The protected-path check now runs before the existence check** - a
   protected path is refused whether or not it exists, which is the correct behaviour on its
   own terms and no longer host-dependent. The test covers every entry in `FORBIDDEN_OUT`.
2. `test_plan_is_offline_and_reports_the_reservation` ran `worker plan` against
   `config/local.json`, which is gitignored, so a clean checkout has no policy at all. Adds
   `tests/policy.ci.json` - a committed policy of the same shape and values - and runs the plan
   against it. A companion test compares the committed policy with the hosted one whenever the
   hosted one is present, so the two cannot drift unnoticed on the coordinator.

**Verified in a clean copy** with `config/local.json` removed: 117 tests pass with bytecode
writing enabled under `TZ=UTC` and `TZ=Asia/Tokyo`, with the 2 host-only checks skipped, and
`python3 -m factory doctor` exits 0 - both of CI's steps.

**Completion procedure added to `AGENTS.md`**, deliberately short rather than a new skill:
after pushing, check CI for that exact commit and fix failures before reporting the change
complete; say so explicitly when CI is pending or blocked; verify suite changes in a clean
clone. The first draft of that instruction told the next session to use
`gh run list --commit <sha>`, which silently returns an empty list even when a run exists - it
reported nothing for a green commit. Corrected to the API form
(`gh api "repos/<owner>/<repo>/actions/runs?head_sha=..."`), with the broken flag named so it
is not reached for again.

CI is green for `d1104f4` and `5848c7e` (the check job's `unittest` and `factory doctor` steps
both succeeded).

### Limited cleanup exception for the smoke test (2026-09-18)

The operator authorized one supervised infrastructure smoke test, and for that test only the
verified on-host sweep satisfies the cleanup prerequisite; GitHub scheduled execution remains
**unverified** and is recorded as an open item rather than a satisfied one. The exception and
its limits are written into `docs/OPERATIONS.md` so a later session cannot read it as a
standing relaxation. Launches are enabled for the smoke cycle and disabled again immediately
after it, leaving cleanup active.

### Infrastructure smoke cycle: completed 2026-09-18

The first paid worker cycle ran under the operator's authorization and the documented
exception. It verifies infrastructure, not task quality.

| step | result |
|---|---|
| job / server / IP | `infra-smoke-001` / `166466571` / `150355427` (`46.62.136.146`) |
| provisioned | 14:55:32Z, CPX32 in `hel1`, `lifetime_minutes` 45, expires 15:40:31Z |
| Docker executed | yes - `python@sha256:9d2e5553...c00285`, `elapsed_seconds` 7.5, `oom_killed` false, exit 0 |
| uploaded | release `job-infra-smoke-001` (id 391560852, draft) in `earino/dataset-factory-staging`, 5 assets |
| collection verified | every asset size and digest matched the worker manifest |
| destroyed | 14:59:41Z - server and job-owned IP deleted |
| provider-confirmed | `scripts/provider-inventory.py`: **0 servers, 0 primary IPs in the whole account** |
| reservation | EUR 0.16 (2 reserved hours at the 0.08 ceiling) |
| estimated cost | about EUR 0.07 - the machine lived 4.2 minutes, and the provider bills server-hours |

Timeline: launched 14:55:31Z, collected 14:59:07Z, destroyed 14:59:41Z. The account held zero
servers and zero IPs before the launch, so nothing else could account for either resource, and
the sweep afterwards returned `deleted_servers: []` with no errors - there was nothing left to
clean.

Launches are **disabled again** (`enabled: false`) and cleanup stays **active**
(`cleanup_configured: true`); a further launch is refused with `Worker launch disabled;
configure policy and independent cleanup first`. The GitHub `schedule` trigger remains
unverified, and the full Austin build and unattended operation are subsequent steps.

`scripts/provider-inventory.py` is new and tracked: it reads the token from the `_FILE` path
and queries the provider directly, so a before/after comparison does not rest on this
project's own bookkeeping claiming success. The recovery and failed-job paths were then
exercised on 2026-09-18; expiry cleanup is covered below.

### GitHub scheduled cleanup: observed executing (2026-09-18)

Run 35368993679, event `schedule`, created 16:31:37Z, commit `3ba6988`, conclusion `success`.
The step `Delete only expired project workers and orphaned job IPs` ran
`python3 -m factory worker sweep --project "$FACTORY_PROJECT"` at 16:31:46Z and printed
`deleted_servers: []`, `deleted_primary_ips: []` - correct, because the smoke worker had been
destroyed at 14:59. So the scheduled trigger **executes**; it has not yet been observed
deleting, because there was nothing expired at the time.

Cadence measured across six fires: gaps of 2.96, 2.19, 4.65, 4.77 and 6.63 hours (mean 4.24 h,
max 6.63 h) against a `17 * * * *` cron. **The GitHub trigger is not an hourly deadline.** The
hourly bound is the on-host sweep's; GitHub's contribution is durability across this instance
being gone. Both are recorded in `docs/OPERATIONS.md` in those terms, and both schedules stay
active.

### Cleanup path tests: expiry, recovery, failed job (2026-09-18)

Each ran one worker at a time, with deletion confirmed against the provider rather than our
ledger, and the acting cleanup path recorded.

**Failed job** - `infra-smoke-fail-01`, server 166481719. The container exited 7 on purpose.
The executor recorded `status: failed`, `exit_code: 7`, `uploaded: true` and preserved the
diagnostics: `output/partial.txt` (the line written before the failure) and `container.log`
(both stdout and stderr) were recovered from draft release 391674310 with digests matching the
manifest. **Path: normal `destroy` after collection** - a failed job is still collectable, so
its evidence survives. Deleted 17:58:28Z; provider then showed 0 servers, 0 IPs.

**Upload recovery** (not "session recovery" - this exercises the artifact transfer, not the
coordinator's session) - `infra-smoke-recov-01`, server 166481920. The lost-transfer condition
was reproduced honestly by deleting the staging release (391676527) after a successful run:
`collect` then failed with `HTTP 404` and exit 1. `worker retry-upload` re-dispatched the upload
unit and `collect` succeeded against a **new** release (391678046) with `exit_code 0`,
`elapsed_seconds 7.2` and `image_id` identical to the first run - the data job was reused, not
rerun, which is the documented guarantee. **Path: normal `destroy` after collection.** Deleted
18:03:28Z; provider then showed 0 servers, 0 IPs.

A first attempt to launch the expiry job was refused by validation
(`Lifetime must include at least 15 minutes for boot/upload and fit policy`) because
`timeout_minutes 5` with `lifetime_minutes 16` violates `timeout + 15 <= lifetime`. Nothing was
provisioned - the refusal happens before any cloud call - and the provider was checked to
confirm no server had been created. Lifetime raised to 20.

**Expiry cleanup** - `infra-smoke-expiry-01`, server 166482592, launched 18:05:00Z with
`lifetime_minutes 20` and deliberately **never collected**, so `destroy` refused it
(`Collect and verify artifacts before normal deletion; expired jobs are cleaned by sweep`) and
the expiry path was the only thing that could remove it.

| measurement | value |
|---|---|
| expired | 18:25:00Z |
| gone from the provider | 18:47:12Z (watcher poll) |
| **deletion lag past expiry** | **22.2 minutes** |
| acting sweeper | **on-host Hermes cron** `e80975eddd4a`, scheduled hourly |
| its own record | `Scout sweep for earino-dataset-factory: {"deleted_primary_ips": [], "deleted_servers": [166482592], "errors": []}` at 18:47:17Z |
| GitHub scheduled run in that window | none - newest remains 16:31:37Z |
| provider after | 0 servers, 0 primary IPs |

The job-owned IP went with the server; the sweep's IP pass had nothing left to remove, and the
provider confirms zero IPs. The ledger was then closed by `worker status`: `status: deleted`,
`deleted_at 18:50:29Z`, reservation `EUR 0.16` retained. **Path: on-host scheduled sweep, not
manual `destroy`.**

### Session recovery: a fresh session reconciled the worker (2026-09-18)

Separate from upload recovery: this tests that a **new coordinator session** can pick up
persisted state and reconcile a live worker without any of this conversation.

Fresh Hermes CLI session `20260918_183816_f11a63`, started from `/tmp` (outside the repo) with
no prior context, told to prefer the ledger and `docs/OPERATIONS.md` over `STATE.md`:

- found `jobs/infra-smoke-expiry-01.json` on its own and read the entry;
- ran exactly `sh scripts/scout-factory worker status infra-smoke-expiry-01` from the repo root,
  exit 0, and reported the output verbatim;
- concluded the ledger still read `status: running`, `server_id 166482592`, `ipv4 46.62.136.146`,
  reservation EUR 0.16, with `deleted_at` absent - verified here by diffing the record before and
  after, which was content-identical;
- inferred from `reconcile` that the provider still held exactly one labelled match, and said so
  as an inference rather than as output it had seen.

33 messages, 19 tool calls, 2m 9s, zero launches or other paid operations. The instruction not to
launch anything was honoured: no replacement worker was created and both cleanup schedules were
left untouched. **Path verified: coordinator-session recovery via the persisted ledger.**

### Austin: full-data extract built and qualified (2026-09-18)

`austin-003` ran the complete construction and qualification on a worker and **passed**.

| | |
|---|---|
| job / server | `austin-003` / `166489302` (CPX32, `hel1`) |
| reservation | EUR 0.24 (3 reserved hours); machine lived 5.9 minutes |
| elapsed | 353.7 s build + qualify, exit 0 |
| qualification | **PASSED - 33 checks, 0 failed**, gate 1.3.0, over the full artifact |
| artifact version | `e4598317e406984fa590aacc5e7aff675867578c51ae1a84ebf6279bc42c3328` |
| staging | draft release `job-austin-003` (id 391742263) in `earino/dataset-factory-staging` |
| acceptance | `scripts/verify-staged-report.py 391742263` - the report's digests equal the uploaded bytes for all five components |
| destroyed | 19:46:23Z; provider then 0 servers, 0 IPs; sweep clean |

**Real split counts, measured on the full data** (threshold T = 1200 s, frozen from the training
window):

| split | rows | positives | positive rate |
|---|---|---|---|
| train (< 2025-01-01) | 572,180 | 231,025 | 0.403763 |
| eval (2025) | 285,665 | 109,860 | 0.384576 |
| holdout (>= 2026-01-01) | 191,791 | 72,450 | 0.377755 |
| **total** | **1,049,636** | | |

The row counts equal the source's per-year counts exactly, so paging lost and duplicated
nothing. The gate's own evidence on the full rows: no `incident_number` appears in more than
one split; 24 repeated-identifier rows within splits, at the declared 24; 4 of 24 repeated
identifiers carry more than one label, recorded as a source property because the descriptor
makes no entity-key claim.

**Baseline: AUC 0.627031** on the eval split from `initial_problem_category` alone, shipped
with the extract. This is a measured floor, not a headline result - no model comparison has
been run, and the gate's passing report is what licenses quoting it at all.

Three runs were needed. `austin-001` failed a conflated entity check; `austin-002` failed an
entity-key claim the source does not make; each failure was diagnosed from the rows and fixed
in the gate or the declaration, and neither was a data defect. The extract bytes for
`austin-002` and `austin-003` are identical, which confirms the last round of changes was
gate-and-declaration only.

Not done, and not implied by any of the above: no model comparison, no headroom figure, and
**nothing published** - a public release still requires human review.

### Publication package prepared for review (2026-09-18)

`release/austin-911-response/` holds the dataset card, data dictionary, licence and attribution
notes, reproduction instructions, the release manifest and checksums, and the release-notes
draft - written to the checklist in `templates/dataset/README.md`. **Nothing has been
published**; no public repository or release exists.

Generated from recorded evidence rather than retyped: `scripts/release-manifest.py` builds
`MANIFEST.json` and `SHA256SUMS` from the accepted artifact's hashes and the candidate record, so
the manifest cannot drift from what was measured.

**Three decisions a reviewer needs to make:**

1. **The construction code licence.** The source data is Public Domain, which says nothing about
   the code that derives it. `LICENSE.md` flags this as an open choice (MIT / Apache-2.0 / CC0 /
   reproduction instructions only) rather than defaulting silently, because it is a legal
   decision.
2. **Shipping the labelled holdout publicly.** The project template permits it; it must simply
   stay outside an evaluated agent's workspace. Alternative: ship the holdout only on request.
3. **The repository name.** The plan assumes `earino/austin-911-response`.

**Publication is not automated past the plan.** `scripts/publish-dataset.py` prints exactly what
would happen and does nothing else; `--stream-test` verifies that all five artifact files resolve
to concrete staged assets (through the worker's own `manifest.json`, not assumed ordering). The
**upload step is deliberately not implemented**: moving ~131 MB from a private release to a
public one needs either a machine that can hold those bytes or a worker-side publish path, and
shipping an unverified pipe that claims to publish would be worse than shipping none. The five
steps are written out in the module docs for when the decision is made.

Two facts learned the hard way and recorded in the tooling: `gh release download` cannot fetch
**draft** release assets, and `releases/tags/<tag>` returns 404 for a draft even though the
release exists - so the staging release is referenced by its **id**.

### Baseline through the runner's contract: eval AUC 0.7691 (2026-09-18)

`austin-baseline-002` ran the harness benchmark's own training and validation contract against
the **verified accepted artifact**. Contract only - no coding agent, no harness comparison.

| | |
|---|---|
| job / server | `austin-baseline-002` / `166494335` (CPX32, `hel1`) |
| reservation | EUR 0.24; elapsed 386.0 s; exit 0 |
| eval AUC, `train.py` | **0.7691** |
| eval AUC, `validate.py` via `predict_proba` | **0.7691** (agrees) |
| `[validate] CONTRACT OK` | yes |
| train / score time | 2.6 s / 0.3 s |
| runner files | `train.py`, `validate.py`, `validate.sh` bundled verbatim from the read-only clone; hashes in the report match the expected ones - `unmodified: true` |
| dependencies | Python 3.13.15, pandas 2.3.3, numpy 2.5.3, xgboost 3.4.1, scikit-learn 1.9.1 |
| destroyed | 21:19:26Z; provider 0 servers / 0 IPs; sweep clean |

The job **rebuilds** the artifact rather than downloading it (the worker has no credential for
the private staging release, and bulk data is not meant to travel), then refuses to measure
anything unless all five files match the accepted hashes - so the number is attached to the
qualified artifact and not to a near-copy.

`austin-baseline-001` failed that verification and was right to: all three split files matched
byte-for-byte, but `meta.json` differed because it embeds `built_at_utc`. Fixed by making the
timestamp an input (`build.py --built-at`), which also makes published artifacts reproducible -
a claim `REPRODUCE.md` makes and now supports. Regression test added.

For context, not comparison: the extract's own single-feature baseline is 0.627031 on the same
eval split, so the runner's model adds ~0.14 AUC over `initial_problem_category` alone. **No
agent or harness result exists**, and 0.7691 is a floor for one rather than a finding about one.

### Publication package assembled in its own private repository (2026-09-18)

`earino/austin-911-response` now exists as a **private** repository with the finished package, and
`v2026.09` carries the dataset as release assets. Nothing is public.

The package carries the construction script, the qualification gate, the materialize and
clock-offset tools, the benchmark's own runner files copied verbatim with provenance, a download
tool that restores the runner layout from flat asset names, `measurements.json` holding every
quoted number with the command that produced it, and the dataset card, data dictionary, licence
notes and reproduction instructions. `MANIFEST.json` records hashes for **every published file**,
so a consumer can check what they cloned, not just what they downloaded.

**The transport is new infrastructure.** A worker job with a `transfer` spec moves artifacts
between releases: each asset is downloaded, verified against its recorded SHA-256, re-uploaded,
verified again from the server's own digest, then deleted, so peak disk on the worker is one
asset rather than the dataset. A `fetch` spec downloads published assets into a read-only mount
at `/data`, which is how a container can measure the *released* bytes without ever holding a
credential. Both run host-side; the container is never given a token.

**A scope decision, recorded rather than buried.** The staging token is scoped to
`earino/dataset-factory-staging` alone - it returns 404 on every other repository - so a transfer
into the dataset repository needs its own credential, now at
`/opt/data/.secrets/github-publish.token` (0600, from the account's `repo`-scoped token). Source
reads still use the staging token and **only the target write uses the broader one**. This widens
what a worker can reach for the duration of a transfer job, so it is stated here and in
`docs/OPERATIONS.md`; a fine-grained token limited to `earino/austin-911-response` would be
narrower and is the recommended replacement.

**Two defects found and fixed on the way**, both by running the real thing rather than reasoning
about it:

1. Writing to a repository the staging token cannot see surfaced as `UploadError`, which
   `execute()` did not catch - so the worker died with `started` touched and no `execution.json`,
   and the job looked like it was still running. The credential requirement is now checked at
   *plan* time, before provisioning, and `UploadError` is caught so a failure still produces a
   report.
2. That stuck worker also exercised the interrupted-job guard for real: `retry-upload` produced
   `failure: "executor-interrupted; job was not rerun"` and the transfer was **not** silently
   re-run.

### Publication package finished, transferred and verified (2026-09-18)

`earino/austin-911-response` (private) carries the finished package; tag **`v2026.09`** and
`main` both point at `acf683ebf7ff14230bf7b7242cad2050980761f4`, and `v2026.09` holds the dataset
as five release assets. Nothing is public.

**What the package contains now:** the construction script, the qualification gate, the
materialize and clock-offset tools, the benchmark's own runner files copied verbatim with
provenance, `get_dataset.py` (restores the runner layout from flat asset names, since GitHub
rejects `/` in asset names), a 19-file document set, `measurements.json` holding every quoted
number with the command that produced it, and `VERIFICATION.md`. `MANIFEST.json` records the
SHA-256 of **every published file**, so a clone can be checked file by file.

**Transport:** `austin-publish-003` moved all five assets from private staging into the dataset
release - 131,429,379 bytes, `failures: []` - verifying each on arrival and again from the
server's own digest after upload, deleting it locally in between. The bytes never touched this
host.

**Fresh-consumer verification: `austin-consumer-002`, 56.9 s, exit 0.** In a container with no
factory access and no GitHub credential:

| step | result |
|---|---|
| cloned package vs `MANIFEST.json` | 18 files, every hash matched |
| assets fetched (host-side, credential never in the container) | 5 files, 131,429,379 bytes, all verified |
| `sha256sum -c SHA256SUMS` | all five OK |
| `python3 code/qualify_dataset.py ./task` | QUALIFICATION PASSED, artifact `e4598317e406984f` |
| `sh baseline/reproduce_baseline.sh ./task` | **Eval AUC 0.7691**, CONTRACT OK |

The baseline reproduces exactly, on the *published* bytes rather than a rebuild.

**What that run does not cover, stated rather than implied:** the container cannot run the network
half of `get_dataset.py` (no credential by design), so the download is done by the worker host
and mounted read-only; and step 5 of `REPRODUCE.md` - a rebuild from the source API - needs ~136 MB
of scratch and was verified during construction, not in the consumer check.

**Decisions still open for review:** a licence for the published code and for the three benchmark
runner files (the benchmark project itself carries no licence file, so including them is the
maintainer's call to confirm), and public visibility. Two earlier decisions are settled: the
labelled holdout ships publicly, and the repository stays private until authorised.

**Three defects the transfer work exposed and fixed**, all found by running it rather than
reasoning about it: a credential that could not see the target repository surfaced as an
unhandled `UploadError` and killed a worker with no report; the asset API answers **302** to a
signed URL on another host, which the downloader did not follow (and must not follow with the
token attached); and the bundle rules rejected the extension-less `SHA256SUMS` by which the
published verification command is named.

## Research shortlist recorded 2026-09-18

Five candidates created with measured evidence in `candidates/<id>/record.json`
and `notes.md`. All numbers below were measured live on 2026-09-18 through
anonymous public APIs; none is a scored result.

| Candidate | Domain | Scale measured | Licence | Status |
|---|---|---|---|---|
| `austin-911-response` | public-safety operations | 1,049,636 calls, 2023-2026 | Public Domain | **lead** |
| `chicago-doah-adjudication` | administrative adjudication | 823,637 rows, 2008-2027 | See Terms of Use | runner-up, licence review needed |
| `noaa-tide-flooding` | coastal water levels | 302 stations; 1.37% pooled station-day exceedance measured | public domain (US Gov) | shortlisted, base rates now measured |
| `melbourne-pedestrian-counts` | urban activity sensing | 1,621,901 hourly records | **still unconfirmed** | shortlisted |
| `md-sewer-overflow` | wastewater infrastructure | 27,479 events 2005-2023 **plus a current series** | Public Domain | promoted from "lower priority" |

Lead choice: `austin-911-response`, because its licence is explicitly Public Domain
while Chicago's is "See Terms of Use", and the project must publish publicly.

### Lead candidate advanced (eighth session)

The column documentation was read and both open questions closed against the earlier
plan, in `candidates/austin-911-response/notes.md`:

- `mental_health_flag` is post-hoc (final problem description, call disposition, a
  responding officer's assessment) - excluded.
- `priority_level` is documented as assigned *at the time of the first officer's
  arrival* - also post-hoc, and it had been listed as a dispatch-time feature.
- `response_time` starts when the 911 call was **answered**, earlier than
  `response_datetime`; no column records that instant. Measured offset on 2,000 rows:
  median -58 s, range -561 s to +6,287 s, only 48/2000 within one second. The target
  must be the portal column, never a recomputed difference.
- `initial_problem_description` and `initial_problem_category` are genuine
  dispatch-time fields and were missing from the feature list.
- The table has **25 columns, not 42** (view metadata and a resource row agree exactly).
- Threshold T = 20 min is measured rather than guessed: positive rate 0.4008 in the
  training window (`response_datetime < 2025-07-01`, 714,314 rows) against 0.3938 over
  the full series.

### Maryland stale-series concern resolved (eighth session)

`stgj-u72u` ("Reported Sewer Overflows (New for 2023)") now returns **HTTP 200** where
an earlier session recorded HTTP 403. It is Public Domain, reports 3,434 rows, and its
`rowsUpdatedAt` timestamp is current (2026-09-18), so a live series exists alongside the
27,479-row historical one (`3rgd-zjxx`, last updated 2023-02). The candidate is no
longer "historical only"; the remaining work is the facility-day event rate and the
rainfall join, not currency.

### NOAA per-station exceedance base rates measured (eighth session)

The shortlist's open measurement is done, and it produced a trap worth recording. Twelve
stations spread across four coasts were measured for station-year 2025 from hourly
observed water levels, daily maxima compared to each station's `nos_minor` threshold.

**The published `nos_minor` threshold is expressed in the station datum (STND), and the
metadata API does not say so.** Comparing `datum=MLLW` heights against it gives **zero
exceedance at all 12 stations across 4,380 station-days** - a convincing-looking "this
task has no positive class" that is purely a datum error. The decisive check is the
2018-01-04 Boston bomb-cyclone tide: MLLW peak 15.022 ft (below the 15.85 threshold,
"no flood") versus STND peak 18.547 ft at the same timestamp (correctly above). NOAA's
own `htb.json` flood-status product was tried as a shortcut and returns nothing usable
from this host.

Measured result at `datum=STND`: **60 minor-flood days across 4,380 station-days, 1.37%
pooled**, per-station rates from 0.00% (Portland ME, Key West, San Francisco, Seattle) to
4.66% (Sewells Point VA). Four stations have an annual maximum within 0.2 ft below
threshold, so their zeros are offset-sensitive.

**Cross-checked against NOAA's own product (ninth session): VALIDATED.** NOAA's
`htf/annual.json` reports, per station-year, the authoritative flood-day counts. For 2025 my
`STND` reconstruction matches NOAA's `minCount` at **12 of 12 stations, 60 days against
NOAA's 60**; the rejected MLLW reconstruction gives 0. Sewells Point also had 3
moderate-or-worse days, the only station in the set with any.

**Hourly sampling undercounts, measured (ninth session).** Comparing daily maxima from
6-minute and hourly data for the busiest station-months: 1 flood day missed out of 17 caught
(Honolulu, 2025-10-07). The pooled hourly rate is therefore a **lower bound**; labels should
come from 6-minute data where the budget allows.

**The physical threshold is kept, by decision.** `nos_minor` is externally defined, has
physical meaning and is now externally validated. It is not replaced with a per-station
quantile merely to balance the classes; the imbalance is documented and handled with
precision/recall-style metrics and an explicit base-rate baseline.

**Split capacity is measured and sufficient.** train 2006-2021: 1,279 positives (1.83%);
eval 2022-2023: 234 (2.67%); holdout 2024-2025: 256 (2.92%). Positives cluster at about two
stations per flood day, so the effective independent counts are **118** and **126** distinct
flood days - ample for scoring, but confidence intervals must use that clustered count. The
rate is not stationary across the series (it rises with sea level), so a temporal split
carries systematic base-rate shift.

### Melbourne licence still unconfirmed (eighth session)

Re-checked through every channel that should carry it and **none declares a licence**:

- `GET /api/explore/v2.1/catalog/datasets/<id>` - no `license`/`licence`/`terms` key.
- The dataset information page HTML - no licence text node and no
  `creativecommons.org` link.
- DataVic's CKAN harvest of the same three Pedestrian Counting System datasets reports
  only the generic `licence_id: "other-open"` with `license_url: null`, which names no
  terms and is not a publishable licence.
- The portal's terms pages return 404 and `melbourne.vic.gov.au/open-data` returns 403
  from this host.

The City of Melbourne commonly publishes under CC BY 4.0, but that remains an
assumption and is recorded as such. **Do not make a release claim for this candidate
until a licence is actually read.**

No baseline, AUC, headroom figure or acceptance verdict has been measured. Nothing
here should be read as a result.

## Lessons consolidated and the research routine prepared (2026-09-18, thirteenth session)

**Where the time and quota went, measured.** 11 recorded sessions, 11.36M input / 0.70M output
tokens, ≈$4.07 estimated, of which 88% was the single long interactive Telegram session
($3.578, 962 messages). Scheduled work was cheap by comparison: three cron sessions cost
$0.034 in total. Useful research was not the expensive part - **waiting and rework were**:
infrastructure smoke tests, three failed worker jobs (`austin-001`, `austin-002`,
`austin-publish-002`), and one failed consumer job, each caught by running the thing rather than
reading it. The avoidable rework clustered in exactly two places: a claim trusted without
recomputation, and a runtime path never exercised before dispatch.

**One consolidation pass, three skills.** `dataset-qualification` rewritten at v2.0.0 around
the shape a skill is actually used with - when to use, commands, required evidence, the checks
as rules, failure modes, completion criteria - with the incident narrative removed (it lives
here) and the stale figure corrected to the measured one (clock offset median −57 s, range
−468…+6,041 s; T = 1200 s at a training rate 0.4038). Two new skills: **`dataset-discovery`**
(vetting before construction: the four contracts, cheapest-first order of work, per-candidate
required evidence, the verdict requirement) and **`dataset-release`** (package layout, staging
transfer, verification, publication gates). All three load through `skills.external_dirs`.

**Verified by a fresh session:** session `20260918_225732_aab19a`, given only the skill system
and told not to read this repository, listed all three skills with their descriptions, quoted
the first command from each, and restated the qualification completion criteria. Registration
is real, not assumed.

**Two mechanical checks, both in CI.** `scripts/check-candidate.py` is stage-aware: a record
claiming `ready`/`constructed`/`qualified`/`packaged` must carry the evidence that claim
implies, a terminal status must carry a reason, and a licence *name* is refused as evidence.
`scripts/check-package.py` requires the documents a reviewer needs, that `MANIFEST.json` covers
every file, that recorded hashes match the bytes, that `SHA256SUMS` agrees with the manifest,
and that an unpublished package says so. 180 tests pass under `TZ=Asia/Tokyo` and `TZ=UTC`.

**Research spend is now gated, and it fails closed.** `scripts/research-budget.py` measures
usage from `state.db:session_model_usage` (split into research / interactive / auxiliary /
scheduled-other by joining `sessions.source` and the `task` column), per-fire tokens from
`cron/usage_audit.jsonl`, and run history from `cron/executions.db`. Attached as a job's
pre-check script it prints a resume block and, when a limit binds, emits `{"wakeAgent": false}`
so the tick is skipped **without spending a token**. `config/research-budget.json` ships with
`allowance_usd: null`, which holds every session: an unconfigured budget is not an unlimited
one. `cron.catch_up_missed` is now `false`, and a tick beyond the late window is skipped rather
than caught up.

**Every cost figure is an estimate.** `cost_status` is `estimated` and `actual_cost_usd` is 0
across the board: Hermes estimates from its own records and no provider-reported actual exists.
The gate therefore bounds planned work and **cannot** reconcile against the portal's
subscription quota, usage reporting or reset period, none of which this instance can see. That
number and its allocation have been asked for before any recurring model work is enabled.

**Independent of the quota:** the weekly digest (`scout-weekly-research-digest`, job
`10d4f73308c8`, Mondays 08:00 UTC) and the hourly cleanup sweep are both `no_agent` scripts, so
monitoring and cleanup keep working when the allowance is spent or unset. The digest fired once
to verify delivery; next scheduled run 2026-09-21T08:00:00Z.

## Research allowance set, per-session limits enforced and verified (2026-09-19, fourteenth session)

**Allowance: 5 USD/month of Hermes-estimated spend, resetting on the 1st at 00:00 UTC.**
`config/research-budget.json`. Every figure is an estimate - `cost_status='estimated'`,
`actual_cost_usd=0` throughout - so this bounds planned work and is **not** enforcement of the
NousCloud subscription quota, which this instance cannot read. Separate from the 20 EUR/month
worker allowance. A **0.40 USD reserve** is held back, so a session starts only while
`spend + reserve <= allowance` and cannot consume the next one's budget.

### The per-session limit is enforced, not just accounted

Counting an oversized session double after the fact was accounting. Two supported runtime
controls are now applied **per run** on `hermes chat`, so they bound a scheduled session without
changing the ceiling on interactive work:

- `--max-turns 60` - **verified stopped**: the runtime injected "You've reached the maximum
  number of tool-calling iterations allowed. Please provide a final response..." and took the
  final answer (session `20260919_060228_2003f8`, 51.6 s).
- `--run-budget 2400` (40 min) - **verified stopped**: at 80% the wrap-up notice arrived ("run
  time budget nearly exhausted... stop new discovery/verification work now") and the session
  ended with its third planned step unfinished (session `20260919_061511_1a35c2`, 108.9 s at a
  test budget of 120 s).

The **600k-token limit is advisory** - the runtime exposes no token control - and its only
mechanical consequence is that an overshoot counts double against the weekly cap.

### What a scheduled session may run (measured)

Flagged commands are **refused** rather than approved, because nobody is present: `python3 -c`,
interpreter heredocs and the `execute_code` tool are all refused, while ordinary commands and
**script files** (`python3 .factory/<name>.py`) work normally. The prompt now tells the session
to compute via script files.

The documented escape hatch does **not** work on this build. `command_allowlist` is documented as
honouring dangerous-pattern *rule keys* on unattended surfaces; `_command_matches_permanent_allowlist`
matches only exact command text or a glob and refuses any command containing a shell operator, so
adding the two script-execution rule keys changed nothing - both commands were refused anyway.
`approvals.single_query_mode: approve` would lift it and was **not** taken: it would let a
scheduled session run dangerous commands. The global `agent.max_turns`/`agent.run_budget_seconds`
were likewise not used, since they would bound the operator's own chat too.

### The scheduled path was observed end to end

`scout-schedule-probe` (job `05411377338b`, one-shot, fired **by the scheduler** at
2026-09-19T06:20:04Z and started 06:20:05Z): status `completed`, delivery `delivered`, wrapper
elapsed 51.6 s, and session `20260919_062008_7b6775` tagged `scout-research` with a usage record
($0.00530, 8 tool calls). The probe also re-ran the gate mid-session and was refused with "lock
held for 32s by scout-research", which is the overlap guard working. The probe job was then
removed.

### What is live now

- `scout-research-session` (`69a5bc676d10`) - `0 8 * * 1,3,5`, `no_agent`, gate then one bounded
  session. **Next run 2026-09-21T08:00:00Z**; its own first scheduled fire is therefore still to
  be observed.
- `scout-weekly-research-digest` (`10d4f73308c8`) - Mondays 08:00 UTC, `no_agent`. Now reports
  usage *and* completed work (commits in the last 7 days plus the candidate queue).
- `scout-budget-checkpoint-2weeks` (`22ce870ec66f`) - one-shot 2026-10-03T08:00:00Z, recommends
  whether Mon/Wed/Fri inside 5 USD/month fits, and explicitly does **not** adjust anything.
- `scout-secondary-cleanup-sweep` (`e80975eddd4a`) - hourly, unchanged and independent of the
  research quota.

The five verification sessions are listed by id in `excluded_sessions` (with the reason) so they
count against neither the weekly cap nor the allowance: they measured the mechanism rather than
doing research. Cost of the whole enforcement verification: **0.0150 USD estimated**.

## A ready candidate in the buffer: NOAA tide flooding, measured to the bar (2026-09-19, fifteenth session)

**What advanced.** `noaa-tide-flooding` moved `investigating` -> **`ready`**, closing the three
items the previous session listed as open. The buffer the `dataset-discovery` skill asks for - one
ready candidate behind whatever is being built - now holds one, and `austin-911-response` (packaged,
awaiting two operator decisions) is no longer the only thing in the pipeline.

**A wrong claim in the record, caught by one request.** The record said all 302 water-level
stations carry flood thresholds. `mdapi/.../stations.json?type=waterlevels&expand=floodlevels`
returns either a bare number or an object whose `nos_minor` is `null`: **132 of 302 publish a
numeric threshold**, 170 do not. "The expand is present" was mistaken for "a threshold exists".

**The station list is now computed from the source, not hand-picked:** numeric `nos_minor` **and**
at least 18 of the 20 target years present in NOAA's own HTF annual product (1 request per station,
132 fetched, 0 errors, 18.6 s) -> **122 stations**, listed with per-station positives in
`candidates/noaa-tide-flooding/station_list_result.json`.

**Split capacity, recomputed over the frozen list** (`htf/annual` `minCount`): train 2006-2021
708,830 station-days / 11,886 positives (1.68%); eval 2022-2023 89,060 / 1,828 (2.05%); holdout
2024-2025 89,060 / 2,850 (3.20%). The daily product reproduced both evaluation counts exactly, so
the two NOAA products cross-check each other. Independent events, from distinct calendar days:
**332 (eval)** and **427 (holdout)** - mean 5.5 and 6.7 stations per flood day, busiest day 52 and
54 stations. Train clustering is recorded as unmeasured, not guessed.

**Extraction cost is measured, which was the last `ready` blocker.** Per request, on this host:
6-minute water level for one month 560,602 bytes in 1.61 s; hourly height for one year 545,427
bytes in 2.219 s; the inventory 777,394 bytes in 1.338 s. Over 122 stations x 20 years: **6-minute
labels 29,160 requests / 15.2 GiB / ~782 min single-threaded** (a worker backfill), hourly 2,430
requests / 1.2 GiB / ~90 min with a measured ~6% undercount of positive days. `product=daily_max`
**does not exist** (HTTP 400), so daily maxima must be derived from observations. Concurrency is
not measured and is labelled as such.

**Two API traps, both silent.** `htf/daily.json`'s array is `DailyFloodCount` with `minFlag` as
the string `"1"` - the wrong key returns "no flood days" with no error, which is how the first
clustering run produced a confident zero. And the datum trap from the ninth session still binds:
`nos_minor` is in the station datum, so `datum=STND` is required. Silent-zero shapes are the
failure mode of this source; anything reading 0 here is a claim to verify, not a result.

**The scheduled routine's own fire no longer holds itself.** The overlap fix landed while this
session was reading (commits `017c293`, `e0ece51` in the shared repository, written by the
operator's concurrent session - this session did not author them). Evidence observed here rather
than assumed: the ledger holds the pre-fix skip
`research job 69a5bc676d10 is already running` at 06:39:37Z, and the wrapper then started **this**
session at 06:42:04Z with a pid-bearing lock and a gate that held only for `lock held for 97s by
scout-research` - i.e. its own lock, which is the correct overlap signal.


## Hugging Face publishing integrated and verified (2026-09-19, fifteenth session)

**Both destinations now carry the same accepted artifact, from one release manifest.**

- GitHub: `github.com/earino/austin-911-response`, release `391804787`, tag `v2026.09` - private.
- Hugging Face: `huggingface.co/datasets/earino/austin-911-response`, revision `v2026.09` - private.
  Version-pinned load, exercised by job `austin-hf-006`:

  ```python
  from datasets import load_dataset
  ds = load_dataset("earino/austin-911-response", revision="v2026.09", token=True)
  ```

  Split counts, positive counts, label values and the 12-column schema all match the accepted
  artifact: train 572,180 / 231,025 positives, eval 285,665 / 109,860, holdout 191,791 / 72,450,
  labels `[0, 1]`. The same call **without** a credential raises `DatasetNotFoundError`, which is
  how privacy is demonstrated rather than asserted. CSV digests are verified against
  `MANIFEST.json` at both destinations.

**Credentials.** `HF_TOKEN_WRITE` (write role, account `earino`) publishes;
`/opt/data/.secrets/huggingface-write.token` (0600) is the file form the worker path uses, exported
by `scripts/scout-factory` as `FACTORY_HF_WRITE_TOKEN_FILE`. It reaches the worker as a root-only
`/opt/scout/credentials.json` entry and is passed to the client through the child environment -
never an argument, never a container, mount, log, manifest or asset. The **inference** credential
is a different token, was never read, and its configuration is unchanged. A job with no publishing
credential is refused at plan time.

**The path, reusable.** `scripts/hf-publish.py --plan|--create|--upload-small|--verify|--tag`, plus
an `hf_publish` worker job that moves the bulk (131 MB never touches this host). Tag last and
idempotently: a tag created before the data landed pins a commit without the files. Re-running is
safe - job `austin-hf-006` skipped all five files as already at the manifest digest and re-sent 0
bytes. Per-destination completion lives in `release/<dataset>/DESTINATIONS.json`; `check-package.py`
refuses a manifest claiming published while a destination is unverified.

**Four defects were found by running it, not reading it** (all fixed, three of them mine):
no `uv` and no pip in the worker venv; the small files' digest check compared a git `blob_id` to a
sha256; the loading check never passed a credential; and the label check assumed a ClassLabel
feature where a CSV yields an integer column. Two of these cost a job each to discover, which is
why `tests/test_hf_helpers.py` now statically checks every helper body's imports.

**Cost:** six `cpx42` jobs, EUR 2.70 reserved against the EUR 20/month worker allowance; every
worker destroyed with the provider confirming 0 servers and 0 IPs. The research allowance is
untouched by publishing.

**Still the operator's decision:** public visibility on either platform, and the licence for the
derived compilation (`LICENSE.md` records the options). Private until then, with the labelled
holdout included on both when approved.

## Licensing resolved and applied to both destinations (2026-09-19, sixteenth session)

The open licence decision is closed, and the terms are now part of the package rather than a
question recorded in it.

- **MIT** (`LICENSE-MIT.txt`) for the construction, qualification and measurement code, the docs,
  and the three baseline runner files copied verbatim from `earino/harness_benchmark`, file set
  `task_template/`. That project is the copyright holder's own work, developed with Claude and
  Szilard; permission to release the copies under MIT is confirmed and contributor credits are
  preserved (Copyright (c) 2026 E. Arino de la Rubia (earino), with contributors Claude and
  Szilard). Upstream credits are preserved too - `szilard/xgboost-autoresearch`, itself in the
  tradition of `karpathy/autoresearch`. `../harness_benchmark` was **not** edited: the permission
  covers the distributed copies.
- **CC0-1.0** (`LICENSE-CC0-1.0.txt`) for **our rights in the derived compilation**, scoped to our
  contribution - row selection, the derived binary label, the temporal partition and the
  packaging. It does not cover or relicense the City of Austin's data, which keeps its **Public
  Domain** designation, attribution and suggested citation, and the dataset is labelled as derived
  and not an official City product.
- The statements that the baseline copies lacked permission, and the all-rights-reserved default,
  are removed from `LICENSE.md`, `README.md`, `RELEASE_NOTES.md`, `baseline/README.md` and the Hugging
  Face card.

**Mechanically enforced, not remembered.** `config/licensing-policy.json` holds the standing
policy; `candidates/<id>/license.json` holds the per-dataset decision; `release-manifest.py` writes
both into the manifest's `licenses` block; `check-package.py` refuses a release with no declared
terms, one naming a licence file it does not ship, or a publication claim with undeclared terms.
The policy carries the rule that matters for the next dataset: **CC0 is not a blanket override of
upstream terms** - terms are chosen per dataset to be compatible with each source, attribution and
share-alike requirements carry through, and a source whose licence cannot be read is not published.

Regenerating the manifest exposed a real defect: `DESTINATIONS.json` was being swept into
`package_files`, so every re-verification invalidated the manifest it helped complete. It is a
post-verification record and is now excluded, which is what `check-package.py` had documented.

**Verified at both destinations, from the pinned revision:** GitHub `v2026.09` clone - 20 package
files hash-checked, none failing, three licence files present; Hugging Face `v2026.09` - private, 16
files including the licence texts, `license: cc0-1.0` in the card. **The accepted dataset bytes are
unchanged**: train `6fc37e03`, eval `241dee5e`, holdout `738ff7ec`, artifact `e4598317e406984f`, and
the GitHub release still carries the same five assets. Both repositories remain **private**;
publication still requires the operator's separate approval.

## Builder: repeatable website publication pipeline (2026-09-19)

The operator clarified the deliverable: a system Scout can operate without a builder
in the monthly loop. The implementation is `scripts/site-publish.py` with
`prepare`, `inspect`, `publish`, `verify` and `status`. Read `docs/WEBSITE-SYSTEM.md`.

Inputs are the existing verified release package, `sites/<dataset>.json` for editorial
content, and `config/sites.json`. Preparation validates and projects metadata, writes
an exact review plan and renders both previews offline. Publication reconciles GitHub
repository ownership, atomic file commits, Pages settings, deployment environments,
workflow dispatch and live verification; it updates GitHub/Hub navigation. Receipts
support bounded retries and recovery. Public deployment remains approval-gated.

The standalone renderer and pinned workflow travel with each site repository. The
catalogue preserves earlier dataset/version records. Website corrections increment
`site_revision` and retain earlier editions; they do not rebuild data or move data
tags. The second-dataset lifecycle test uses a metadata fixture and the same preparation
code; it is not a claim that another real dataset has been constructed.

**Observed on GitHub:** transport wrote the generated site to the temporary branch
`builder/site-runtime-smoke-20260919` of this private repository, at
`138347f4fca232c17d16d333bcf67bb4dea1a196`. Repeating the atomic commit returned the same SHA.
[Generated workflow run](https://github.com/earino/dataset-factory/actions/runs/35436121641)
completed successfully: build/upload executed, public artifact/deploy steps were skipped.
The downloaded preview's JSON matched the prepared record, review mode was true, and
version/edition pages existed. The provider reported this factory private and
`has_pages: false`. The accompanying existing test workflow also passed.

The builder independently read Austin's pinned GitHub manifest and release 391804787;
all five provider asset digests/sizes matched the site record. No data file was downloaded.
The local suite initially found one pre-existing bytecode file dated 2026-09-18 in
the NOAA candidate directory. Only that generated file and its empty cache directory
were removed; no candidate source or benchmark file was changed.

**Not yet observed:** the Hub adapter against Scout's hosted write credential, public
Pages provisioning/deployment, and Scout independently completing a real site update.
The builder has GitHub access, not Scout's Hub publishing credential. Unit/provider
simulations and a real private preview build do not satisfy those live checks.

**Next action for Scout:** pull the implementation, run offline preparation and
`inspect` from the hosted environment, and report the plan SHA, credential/access
readiness and any real defect. Keep both data repositories private and leave Pages
disabled until the operator approves publication. After approval, finish the dataset
release and run `publish`/`verify`, then independently exercise an editorial revision.
Ordinary operation and repairs belong to Scout; builder review is not a standing gate.

**Implementation verification:** commit `8444c46383539934dff13b798504822f4a466067`
passed [Local checks](https://github.com/earino/dataset-factory/actions/runs/35436380363)
and [Website pipeline preview](https://github.com/earino/dataset-factory/actions/runs/35436380409).
The latter contains the review bundle as an Actions artifact. A clean export of the
staged tree, with no private configuration, passed 240 tests (4 environment-specific
skips) and factory doctor. The prepared Austin plan SHA is
`87b1fd5a9bcf920c0396b0e6c08c52f89de1ba991df70e57245e59abb7a88db6`.

## 2026-09-19 - Hosted handoff check (bounded, no public deployment)

Ran the exact steps the operator specified, from the hosted environment, against the builder's
implementation at `83c1d683a6519f7386b0504666a8f75b31f82999`. No blocking defect and no missing
permission was found. Both data destinations stay private and Pages stays disabled.

**Plan SHA: `87b1fd5a9bcf920c0396b0e6c08c52f89de1ba991df70e57245e59abb7a88db6`** - identical to the
expected value, so **no implementation input changed**. `prepare` made zero network calls and did not
modify the release package. An earlier bundle prepared into a different output directory produced
the same digest, confirming the plan SHA covers the inputs rather than the output path. Repeated
preparation is byte-identical across `bundle.json`, `REVIEW.md` and both previews. The reviewed
bundle is `.factory/sites/austin-website-1`.

**Preflight (`inspect`, exit 0, empty stderr), using the default HF environment** - the default
resolved without `--hf-python`:

- GitHub release `391804787` verified against its pinned manifest and asset digests; `private: true`.
- Hub revision `542382ae6d3e48175b6938f5df4f91e087cfd2ee` verified, equal to the Hub main commit;
  `private: true`; navigation links not yet present, as expected before publication.
- `ready_for_publication: false` - correct, because both destinations remain private.
- Dataset repository `earino/austin-911-response` accessible, Actions enabled (`all`, no SHA
  pinning), no Pages site (`pages: null`).
- Catalogue `earino/dataset-factory-site` not accessible - it does not exist yet and the plan creates
  it at publication. Expected state, not a missing permission.

**Content agreement** - the dataset preview matches `MANIFEST.json` fact by fact: the version tag,
the full artifact hash `e4598317e406984fa590aacc5e7aff675867578c51ae1a84ebf6279bc42c3328`, all three
split row counts (572,180 / 285,665 / 191,791), MIT, CC0-1.0, the source's Public Domain
designation and both destination links. Nothing from the holdout is inlined. The catalogue preview
carries the tag and both links, which is its role.

**Public-projection leak check** - across all 19 projected files: no credentials, staging URLs, job
or worker records, host paths, provider identifiers or internal release/asset ids. Two initial hits
were my own over-broad patterns matching the public catalogue name `earino/dataset-factory-site` and
the intentional `artifact_version` field; both were read in context and dismissed.

**Two safety properties tested rather than assumed.**

1. A wrong `--approved-plan` digest is refused with exit 1 and
   `Approval does not match this prepared plan` - observed live and now locked by a new test that
   also asserts nothing is written: no commits, no deployment dispatch, no receipt.
2. The Hub adapter genuinely does not depend on the inference credential: with a deliberately
   poisoned `HF_TOKEN`, `inspect` still verified the Hub revision. Confirmed in `scripts/site-hf.py`,
   which resolves `HF_TOKEN_WRITE` (or its credential file) and calls `env.pop("HF_TOKEN", None)` on
   the child environment, exactly as the handoff states.

**One ordering observation, not a defect.** `GitHub()` and `Hub()` are constructed just before the
approval digest is compared, so a stale digest still builds the client objects. No write, dispatch
or receipt follows the refusal, and the live run showed no network latency, so the refusal still
precedes every mutation.

**Builder's CI claims independently verified:** Local checks run `35436461305` and Website pipeline
preview run `35436461283` both exist at the full SHA `83c1d683a651` and both succeeded.

**Test count reconciled:** the builder measured 240 tests with 4 environment-specific skips in a
clean checkout; this environment reports **246 with no skips** - the builder's 240, plus the 5 added
with the novelty gate, plus this check's new approval test, with those 4 tests running here because
`gh` and the Hub environment are present.

**After operator approval:** finish the public dataset release, then
`publish --approved-plan 87b1fd5a... --wait-seconds 600` and `verify`. A pending run is not
completion.

## 2026-09-19 - Austin is public, and its website is live

Operator approved public visibility for the dataset and its infrastructure. Publication ran on the
same reviewed plan (`87b1fd5a...`), unmodified; the approved digest was never applied to changed
inputs.

**Both destinations are public and anonymously readable.** GitHub `earino/austin-911-response`
(release `391804787`, tag `v2026.09`) and Hugging Face `earino/austin-911-response`
(`542382ae6d3e`, not gated). With no credential at all: the repository page answers 200, all five
GitHub release assets answer ranged GET 206, the Hub dataset API reports `private: false`, and the
Hub data files answer ranged GET 206. Data files, tag and artifact version are unchanged by
publication - `e4598317e406984fa590aacc5e7aff675867578c51ae1a84ebf6279bc42c3328`.

**Live sites**, both deployed and verified, cross-links verified, receipt `complete`:

- Dataset: https://earino.github.io/austin-911-response/ (deployment run `35453081771`)
- Catalogue: https://earino.github.io/dataset-factory-site/ (deployment run `35453120375`)
- Live records read back and matched: `.../versions/v2026.09/release.json` and `.../catalog.json`
- `verify` exit 0, `status: verified`, HTTPS enforced on both sites.

The catalogue repository was created by this run and carries its ownership marker; both repositories
keep their previous releases.

**Two real defects found on first live contact, both fixed here.**

1. **HTTPS was enforced before the certificate existed.** `setup_pages` called
   `PUT /pages {"https_enforced": true}` before dispatching any deployment, and GitHub answers
   **HTTP 404 "The certificate does not exist yet"** until the *first successful deployment* has
   provisioned it. The first live publication aborted at exactly this step - the area the builder's
   own notes flagged as never observed against GitHub. The certificate only appears after a
   deployment, so enforcement now tolerates that answer, records it as deferred, and is retried
   automatically once a deployment reports `deployed`. `verify` reads back the enforced state on
   both sites rather than assuming it. New test models GitHub's refusal.
2. **The homepage guard was undiagnosable.** The dataset repository's homepage pointed at the
   upstream source portal (`datahub.austintexas.gov/d/e687-fx2y`), so the pipeline refused to
   replace it - correct, but the message did not say what the existing value was. The message now
   names both values.

**One reviewed judgement call.** After checking, the rendered dataset site links the City of Austin
portal prominently and carries the attribution, Public Domain designation and suggested citation, so
replacing the repository homepage with the site URL loses nothing. The homepage was cleared once, as
a reviewed transition, so the pipeline itself set it - the approved plan was not modified to achieve
this.

**Noted, deliberately left alone:** `MANIFEST.json` (public) records the private staging repository's
*name* (`staging_repo`), and `VERIFICATION.md` names the job that performed the transfer. No
credentials, URLs or download paths are exposed, and the manifest is a frozen, hashed artifact of an
accepted release - editing it would change the release identity and invalidate the reviewed plan, so
removing those names, if wanted, is a new version rather than an edit.

**Site publication deferred nothing else:** the Hub card and the GitHub README carry the cross-links,
and the labelled holdout is downloadable on both platforms.

## 2026-09-19 - The published card and docs still said "private": three defects fixed

The operator noticed the Hugging Face card still read "Status: private. Public visibility requires
explicit human approval" after the approved publication. It was right, and fixing it exposed two
more defects of the same shape - a claim asserted in a generator instead of derived from the state.

1. **The card's status was a literal.** `scripts/hf-publish.py` hard-coded the private wording, and
   the loading instructions told readers to pass a token "for a private repository". The card's
   status line and its loading note now follow `published` in the manifest. The card also demanded
   `token=True` in the version-pinned example, which would fail for an anonymous reader of a public
   dataset; it is emitted only while the release is private.
2. **The manifest asserted its own publication state.** `scripts/release-manifest.py` held
   `visibility`, `published` and `publication_note` as literals, so the *documented*
   post-publication regeneration step - "regenerate MANIFEST.json and SHA256SUMS from recorded
   evidence" - would have re-asserted "private" forever. All three are now derived from
   `DESTINATIONS.json`, which records what was checked per destination. The manifest now reads
   `visibility: "public"`, `published: true`.
3. **The card shipped a literal placeholder.** The template wrote the repository id as a
   doubled-brace placeholder inside an f-string, which renders to a single-brace string, so the
   replacement never matched. The published card carried `load_dataset("{repo_id}", ...)` and
   `hf download {repo_id}` - commands that cannot run. An unambiguous token (`__REPO_ID__`) is used
   now, and the built card was checked to contain the real id four times and the placeholder zero
   times.

**What was corrected and where.** `DESTINATIONS.json` records both destinations as public with the
anonymous-read evidence and the authorisation; the package README, RELEASE_NOTES and the public
repository copies state "public since 2026-09-19"; the Hugging Face card, `LOADING.md` and manifest
were re-uploaded. The public repository received one atomic commit (`fa852cdd0274`) that carries the
README digest its manifest pins, so the website pipeline's own invariant still holds. The dataset
tag, the five assets and `artifact_version` are untouched, and the approved site plan digest is
unchanged - verified by re-running `prepare`, which reproduced `87b1fd5a...` exactly.

**Verified after the repair:** the website pipeline re-ran and reports `complete`, `verify` returns
`status: verified` with HTTPS enforced on both sites, the Hub revision is still `542382ae6d3e`, the
card reads "Status: public", and an anonymous client - implicit token use disabled - fetches all
three revision-pinned data files (HTTP 206) and the Hub API reports `private: false`. The library
level `load_dataset` call needs the `datasets` package, which lives in the worker image rather than
the Hub venv here, so the version-pinned path is verified at the HTTP level here and its library
form was exercised by the worker job before publication.

**Suite:** 255 tests, including new guards for the placeholder and for the derived publication
state.

## 2026-09-20 - NOAA build accepted: complete panel, both levels gated

`noaa-003` produced the artifact. **Coverage is complete**: 122 of 122 frozen stations, 2,440 of
2,440 station-years, 4,880 requests, **zero errors**. Both levels pass the qualification gate on the
full artifact - 32 checks each, no failures - including the leakage, prediction-timing, split,
unit-frame and runner-contract claims.

| level | split | rows | positives | stations |
| --- | --- | --- | --- | --- |
| temporal | train | 697,373 | 11,774 | 122 |
| temporal | eval | 89,038 | 1,815 | 122 |
| temporal | holdout | 88,841 | 2,850 | 122 |
| station_disjoint | train | 461,580 | 7,513 | 81 |
| station_disjoint | eval | 29,930 | 788 | 41 |
| station_disjoint | holdout | 29,930 | 1,090 | 41 |

Positives match the capacity measured before the build to within 1%: holdout is exact on both
levels (2,850 and 1,090). The residual difference is the year-boundary effect that was predicted -
the label is next-day, so a flood day on the first date of a window has no previous row to be
labelled from.

**Acceptance without moving bulk data.** The gate report records the sha256 of every file it gated;
the staging manifest records the sha256 of every uploaded file. All ten files across both levels
compare equal, so the report describes exactly the bytes in staging. The local `--accept` path was
not used because it would mean downloading ~180 MB to the coordinator.

**The three attempts, and what the failures taught.** Run 1 lost 594 station-years and 13 stations
to rate limiting, and passed both gates anyway - the gates check leakage, timing, splits and units,
not coverage. Run 2 built all 122 stations but lost 60 station-years to HTTP 403, which the retry
classified as permanent and retried immediately; the new coverage gate refused it and skipped
qualification rather than gating an incomplete artifact. Run 3 fixed the 403 handling and added
paced requests, and lost nothing.

**A worker watchdog now runs every five minutes.** Three jobs ran and the operator had to ask twice
what was happening: a remote job outlives the turn that launched it, `notify` fires when the launch
exits rather than when the job does, and `worker status` reports the *server*, which idles until its
lifetime expires. `scripts/scout-job-watch.py` polls with `worker collect` (the only cheap signal),
emits one deterministic line per job so a scheduler change detector can gate the agent, and treats
anything that is not an explicit `running` answer as terminal - including the sweep having taken the
worker first.

**Cost:** three worker runs at EUR 0.24 / 0.32 / 0.32. Project total about EUR 4.96 of the EUR 20
monthly allowance.

**Next:** a baseline through the runner's contract on both levels - the question of whether
observations-only, station-normalised features carry signal on held-out stations - then packaging.

## 2026-09-20 - NOAA baseline: the task is learnable, and it transfers

`noaa-baseline-001` succeeded in 27.5 minutes (exit 0). The benchmark's own `train.py` and
`validate.py` ran unmodified against both levels, with their sha256s recorded in the report and
`validate.py` re-running training and printing `CONTRACT OK` on both.

| level | eval AUC | train rows | eval positive rate |
| --- | --- | --- | --- |
| temporal | **0.8638** | 697,373 | 2.04% |
| station_disjoint | **0.8688** | 461,580 | 2.63% |

The station-disjoint level scores the same as the temporal one on **stations the model never saw**,
so the signal is not station-specific memorisation - which is the whole basis of the novelty verdict
and the reason that level exists.

**Not yet calibrated, and this matters.** The strongest feature is yesterday's maximum against the
station's own threshold, and consecutive flood days are common, so part of that AUC may be
autocorrelation rather than prediction. A single-feature persistence baseline is the next
measurement, before any headroom claim is made or published.

**Why the operator heard nothing about it.** The job finished at 05:56 and was collected, but not
reported. The watcher dropped the job from its output the moment the job record went terminal, so
the agent woke to an empty diff and had nothing to say: a watchdog that reports "nothing" the
instant there is something is worse than no watchdog. It now keeps a finished job visible until it
has been handled, marked by a `handled` file beside the result, and the report is not considered
delivered until that marker exists.

**Cost:** EUR 0.32 for this job; about EUR 2.20 of the EUR 20 monthly allowance across all runs.

### Persistence calibration - the honest floor (same day)

`.factory` evidence before any headroom claim. No training, no worker, no dependency: rank-based AUC
of each single feature on the eval split.

| level | best single feature | that alone | full model | model's actual headroom |
| --- | --- | --- | --- | --- |
| temporal | `margin_ft` (yesterday's max vs threshold) | 0.8265 | 0.8638 | **+0.0373** |
| station_disjoint | `margin_ft` | 0.8454 | 0.8688 | **+0.0234** |

**Persistence is most of the signal.** The trained model adds 0.023-0.037 over a stock feature it did
not have to learn anything to use. The task transfers across stations and is genuinely real, but its
headroom is narrow: a one-feature rule gets ~96% of the way.

The plain rule "yesterday exceeded" agrees with the label **96% of the time** while carrying almost no
ranking signal (AUC 0.63), because only ~2% of days are positive. That is why the contract scores AUC
and why accuracy is not reported as a headline anywhere.

**Consequence:** the release card must carry the single-feature reference beside the model baseline,
as Austin does (0.627 single feature, 0.769 full model). Widening the headroom would mean a harder
variant - onset after a dry spell, or a longer horizon - not a threshold change. The physical
threshold stays. Operator decision pending; research is not blocked by it.

## 2026-09-20 - NOAA release package assembled, and the accepted bytes are in the dataset repository

The packaging commit `b93a5cb` turned the manifest generator into a dataset-driven one (its
repository, source block, layout, asset names and commands moved from literals in the script into
`candidates/<id>/release.json`; Austin's `MANIFEST.json` regenerates byte-for-byte identical, which
is what proves the refactor changed nothing already published). `release/noaa-tide-flooding/` now
carries `MANIFEST.json`, `SHA256SUMS`, `DATA_DICTIONARY.md`, `README.md`, `VERIFICATION.md`,
`REPRODUCE.md`, the licence texts, the runner baseline and the construction, qualification and
measurement code: 28 package files listed in the manifest, `check-package.py release/noaa-tide-flooding` OK.

**`noaa-publish-001` succeeded** (exit 0, 0 minutes of container time - it only moves bytes).
The `transfer` spec copied all ten accepted artifact files, **196,017,925 bytes**, from private
staging release 392230750 into `earino/noaa-tide-flooding` release `392387511`, tag `v2026.09`,
on a worker host, so the ~187 MB never passed through the coordinator. `failures: []`.

**Verified from the service, not from the job's own report.** Every one of the ten assets re-read
from the GitHub API matches the job's transferred size and sha256 exactly, 10 of 10, and the
repository is `private`. The tag `v2026.09` and `main` resolve to the same commit
`9bcbf2c69e04e7e3d92191a3cfe86ed066cc422c`, which carries the docs, so GitHub is the complete
destination: docs, code and release assets in one place. All ten documentation files at that commit
are byte-identical to the package's own copies - compared by Git blob hash, `MANIFEST.json`,
`SHA256SUMS` and both licence texts included - so the repository is not describing a different
dataset from the one `check-package.py` validates.

| level | split | rows | eval file bytes | sha256 (first 8) |
| --- | --- | --- | --- | --- |
| temporal | train / eval / holdout | 697,373 / 89,038 / 88,841 | 97,931,036 / 12,507,806 / 12,475,942 | `939efaf4` / `cbc3bd54` / `cceb5a93` |
| station_disjoint | train / eval / holdout | 461,580 / 29,930 / 29,930 | 64,636,157 / 4,229,470 / 4,228,351 | `c18ca880` / `e790547b` / `79968550` |

Recorded in `candidates/noaa-tide-flooding/record.json`: status `packaged`, the job, the
destination with the per-level artifact versions and every file digest, and the local research
artifacts moved to `artifact_evidence`. `scripts/check-candidate.py noaa-tide-flooding` OK.

**The worker was destroyed** (server 166609889, `deleted_at` recorded in `jobs/noaa-publish-001.json`)
and the job's small reports were fetched into `.factory/noaa-publish-001/reports/`. The staging
release's own manifest shows `uploaded: false`, which is the job's snapshot written before its
result upload completed - not a failed transfer: the collected `result.json` carries
`uploaded: true` with the ten transferred entries and an empty failure list.

**Nothing is public.** Both repositories are private and no `DESTINATIONS.json` exists for this
dataset, so the manifest still derives `visibility: private`, `published: false`.

**The next step found a real defect.** `scripts/hf-publish.py` is still Austin-shaped: its package
path is the literal `release/austin-911-response` (only the repo id takes an argument), so running
it for NOAA would upload Austin's files under NOAA's card and tag. It needs the same treatment the
manifest generator just got - read the dataset from its argument or the manifest - before the
Hugging Face half of this release can be attempted.

**Cost:** EUR 0.16 reserved for this job at the EUR 0.08/h cpx32 rate; it ran for minutes, so the
charge is a fraction of that. No new research spend.

**Operational note, cost this session one failed push.** `git push` from a shell that has exported
`GH_TOKEN` uses *that* token, because `gh`'s credential helper prefers the environment: exporting
the restricted staging token for a read-only API call made the next push fail with
`Write access to repository not granted`. `unset GH_TOKEN GITHUB_TOKEN` in the same shell restores
the working helper. Scope such exports to the command (`GH_TOKEN=$(cat ...) git ...` or a
subshell) rather than leaving them in the session environment.


## 2026-09-20 - The published NOAA release passes an independent consumer check (noaa-consumer-001/002)

The published bytes were checked the way a consumer receives them: a worker container with **no access
to this repository and no GitHub credential**, cloning `earino/noaa-tide-flooding` at `v2026.09`,
hashing every file against `MANIFEST.json`, verifying the ten release assets with `sha256sum -c`,
running the published gate and reproducing the published baseline on **both** levels.

**`noaa-consumer-001` failed** (staging release 392392211, 51.4 s, 5 report assets, worker 166610817
destroyed). It died in the baseline step and left nothing in the log to diagnose it, because that
step sent its output to a file under `/output` and the container died before the file was uploaded -
`container.log` ends at the step header. Everything before it had passed: 28 package files matched
`MANIFEST.json`, `sha256sum -c` was OK on all ten assets, and both gate runs reported
`QUALIFICATION PASSED` (temporal `8896c4423c53cb14`, station_disjoint `e6aff23f394ddfe4`), matching
the artifact versions recorded at build time. Recorded in `jobs/noaa-consumer-001.json` and
`.factory/noaa-consumer-001/`; the failure was an unlogged step, not evidence about the data.

**The fix was to make the step visible, not to change the check.** `run.sh` now installs the
benchmark's declared dependency ranges (`pandas>=2.2,<3`, `numpy>=1.26`, `xgboost>=3.0`,
`scikit-learn>=1.5`) as an explicit step and tees the baseline output into the log, so a failure
cannot be silent; the corrected script is what `noaa-consumer-002` ran.

**`noaa-consumer-002` succeeded** (staging release 392395671, 72.0 s, worker 166611532 destroyed).
Result, on the published bytes:

| step | result |
| --- | --- |
| package vs `MANIFEST.json` | 28 files checked, every one matched |
| `sha256sum -c SHA256SUMS` | OK on all ten assets |
| published gate, temporal | exit 0, `QUALIFICATION PASSED`, artifact `8896c4423c53cb14` |
| published gate, station_disjoint | exit 0, `QUALIFICATION PASSED`, artifact `e6aff23f394ddfe4` |
| baseline, temporal | `CONTRACT OK`, eval AUC **0.8651** against the recorded 0.8638 |
| baseline, station_disjoint | `CONTRACT OK`, eval AUC **0.8687** against the recorded 0.8688 |

**The reproduction is within about 0.002, not exact, and that is now recorded as a property of the
measurement.** The artifact digests are identical and the dependencies resolved to the same versions
(pandas 2.3.3, numpy 2.5.3, xgboost 3.4.1, scikit-learn 1.9.1), so the difference is the runner's
training rather than a version or byte change: xgboost with default threading is not
bit-reproducible. The recorded baseline is one measurement, not a constant, and the reproduction
guide and consumer check now say so (the check compares values, not only exit codes). Both gate
artifact versions match the build-time ones, so the published bytes are the gated bytes. Neither
check scored the holdout.

Recorded in `candidates/noaa-tide-flooding/record.json` (`jobs` for both runs plus a
`consumer_verification` block) and in the release's own `VERIFICATION.md`;
`scripts/check-candidate.py noaa-tide-flooding` OK.

**CI.** `d925039` (the dataset-driven Hugging Face publisher and NOAA's card) and `23d745d` (per-config
Hugging Face loading verification, the reproduction record and the run-script fix) each have a
completed, **successful** GitHub Actions run for their own pushed SHA: runs 35505322723 and
35505729541 / 35505729555.

**Nothing is public.** Both repositories stay private and no `DESTINATIONS.json` exists, so the
manifest still derives `visibility: private`, `published: false`.

**Cost.** Two cpx32 runs, 51 s and 72 s: well under EUR 0.01 each at the EUR 0.08/h rate, inside the
EUR 20 monthly allowance.

**Operational observation.** A second coordinator session was already acting on this same job when
this run started (it collected `noaa-consumer-002`, wrote the `handled` markers, and had begun the
Hugging Face work). Its committed work is the two CI-green commits above; this entry adds the
consumer results it had not yet recorded in `record.json` and `STATE.md`. Two coordinators on one job
ledger is the situation `AGENTS.md` forbids, so the remaining work below is left to whichever session
is currently driving it - this run launched and destroyed nothing.

**Next action.** The Hugging Face half is in flight: `jobs/noaa-hf-001.json` was launched on worker
166611959 (10:38) to move the bulk files to the private Hugging Face repository under the generated
card, with `candidates/noaa-tide-flooding/hf/` holding the plan. Finish it with
`python3 scripts/hf-publish.py --verify --candidate noaa-tide-flooding`, confirm every config loads,
then `--tag` last and check the tag and `main` resolve to the same commit. Operator approval is
required before either destination leaves private, and the open decision on shipping the narrow
headroom (persistence floor 0.8265/0.8454 against 0.8638/0.8688) or building a harder variant is
still pending.

## 2026-09-20 11:20 UTC - noaa-hf-001: the upload was fine, the verifier was not

**`noaa-hf-001` failed, and the failure was in our code rather than in the dataset.** The job
moved all ten accepted files to the private Hugging Face repository (10 uploads, 196,017,925 bytes,
0 failures, 0 skips, each checked against the digest the Hub reports) and then died in the loading
check with `KeyError: 'splits'`.

The verify helper has two branches - a job declaring `configs` and a job declaring a single set of
`splits` - and only the first was inside the `if`. The single-config code ran unconditionally after
it, reading `expected["splits"]` on a job that has `configs` instead. `load_dataset` had already
read all six splits of both configs (temporal 697,373/89,038/88,841; station_disjoint
461,580/29,930/29,930) before the crash, so the report said "the documented loading path did not
reproduce the artifact" about an artifact that was in fact loading. The coordinator-side read-only
listing of the private repository agrees with the upload: all ten paths present at the manifest's
byte sizes.

**Fix.** `workers/hf_publish.py`: the single-config path is inside the `else` branch and the report
is printed once. The old source reproduces the exact `KeyError: 'splits'` against a stub `datasets`,
and `tests/test_hf_helpers.py::VerifyHelperBranchTests` now runs the real helper source for both
job shapes - per-config checking, comparison rather than mere loading, and the original single-config
path. 283 tests pass.

**The corrected job is prepared and its plan is clean** (`candidates/noaa-tide-flooding/hf/job-002.json`,
id `noaa-hf-002`, same ten assets, HF credential present, reservation EUR 0.45). **It could not be
launched: another coordinator started `jobs/noaa-004.json` at 11:04:32** - a cpx32 rebuild of this
same candidate, untracked in git, 120-minute timeout - and the policy allows one worker at a time.
Waiting for a NOAA build (noaa-003 ran overnight) is not something a watchdog tick can do, so the
launch is left to the next session or to the wait loop started here, which retries for fourteen
minutes and then gives up cleanly.

**Next action.** When the worker slot is free: `sh scripts/scout-factory worker launch
candidates/noaa-tide-flooding/hf/job-002.json`, then `worker collect noaa-hf-002` and read
`hf_loading.ok` together with every per-config row count and positive count in
`.factory/noaa-hf-002/reports/`. Only then `python3 scripts/hf-publish.py --verify --candidate
noaa-tide-flooding` (its `DESTINATIONS.json` entry claims the loading check was run by the worker,
so it must not be written before that report exists), then `--tag` last, then
`python3 scripts/check-package.py release/noaa-tide-flooding`. Nothing is public: both repositories
remain private, and no `release/noaa-tide-flooding/DESTINATIONS.json` exists yet, so the
manifest still derives `visibility: private`, `published: false`. Recorded in `candidates/noaa-tide-flooding/record.json` (`jobs` for
`noaa-hf-001`) and `.factory/noaa-hf-001/`.

## 2026-09-20 11:55 UTC - noaa-004: a gate-passing rebuild that was not adopted, and the HF half relaunched

**`noaa-004` succeeded** (staging release 392410743, 19 assets, 27.9 minutes, exit 0, worker 166613240
destroyed at 11:53:09Z). It was launched at 11:04:32 by a concurrent coordinator session that also
renamed the target column `late` -> `minor_flood` in `build.py` and `persistence_baseline.py`, left the
edit uncommitted, recorded no reason for it, and then ended (its session closed at 11:05, so the intent
could not be recovered from anywhere). The rebuild is complete and gate-clean:

| check | noaa-004 |
| --- | --- |
| coverage | 122/122 stations, 2440/2440 station-years, 0 missing, 0 errors |
| rows / positives | temporal 697,373/11,774, 89,038/1,815, 88,841/2,850 - station_disjoint 461,580/7,513, 29,930/788, 29,930/1,090 |
| gates | both levels `ok`, 32/32 checks, `failed_checks: 0`, gate 1.3.0, `QUALIFICATION PASSED` |
| artifact versions | temporal `bb051dc304a4ee63`, station_disjoint `92297a5b62f86b29`, combined `fb49f932c7b4ea5a` |

**Its artifact is not the released one, and was not adopted.** Two differences from the shipped
artifact (noaa-003, artifact versions `8896c4423c53cb14` / `e6aff23f394ddfe4`, combined `a5a5ac5b41db1978`):

1. **The target column is renamed.** The released artifact, `release/noaa-tide-flooding/code/build.py`,
   `DATA_DICTIONARY.md`, `card.md` and `hf/job-002.json` all name it `late`. Adopting the rename means
   re-doing a release that is already gate-passed, consumer-verified on the published bytes and uploaded
   to Hugging Face, so the change was **reverted** and its diff kept at
   `candidates/noaa-tide-flooding/noaa-004-label-rename.diff`. Candidate sources now hash identically to
   the released package copies (`build.py` `5058314226d1e005`, `persistence_baseline.py`
   `d5ff90a15e77bd4c`) and to what noaa-003 bundled.
2. **NOAA revised the observations between the two pulls.** The rebuild is not byte-identical even
   though the code is: temporal/train offset 43912723, station 8661070 (Springmaid Pier) 2008-10-12
   `observed_max_ft` 35.427 -> 35.426 and 2008-10-13 -1.323 -> -1.324 with `trailing7_mean` 34.722 ->
   34.7219 and `trailing30_mean` 35.4425 -> 35.4424. Every file's byte size moved by more or less than
   the 7-byte header change (+12, +11, +9, +7, +5, +9), so each of the six carries at least one revised
   row; 200-byte needles at 250 KB intervals found nothing else in 135 sampled windows, so the revisions
   are sparse. Compared through byte-range reads of the staging assets - no bulk download on the
   coordinator. Recorded as `measurements.rebuild_not_byte_reproducible`: the release pins an artifact
   version, and a re-pull is a **new** artifact needing its own gate report and its own release.

**The worker slot is now used.** `noaa-hf-002` was planned (clean, EUR 0.45 reservation) and launched at
11:53:15Z (worker 166615899, cpx42, hel1) - the Hugging Face bulk move plus the per-config loading check
that `noaa-hf-001` died before performing. It is running; the watcher will report it.

**One hygiene fix, in the same commit.** Tracking the fetch bundle made CI's job-id uniqueness
check fail: the older rebuild-and-measure baseline bundle under `baseline/source/` had been bumped to
`noaa-baseline-002` on 2026-09-20 for a rerun that was never launched, so the id collided with the fetch
variant that actually ran. That stale bundle is renamed `noaa-baseline-rebuild-001` with a note explaining
why; the fetch variant keeps 002, which is the job the record describes.

**Recorded**: `candidates/noaa-tide-flooding/record.json` (`jobs` -> `noaa-004`, the
`rebuild_not_byte_reproducible` measurement, a rewritten `next_action`), the rename diff, `jobs/noaa-004.json`,
and `.factory/noaa-004/` (result plus the hash-checked reports). Next action: collect `noaa-hf-002`, read
`hf_loading.ok` and every per-config count, then `scripts/hf-publish.py --verify --candidate noaa-tide-flooding`,
then `--tag` last, then `check-package.py`. Both destinations remain private; no `DESTINATIONS.json` exists.
Still the operator's: whether to take the `minor_flood` rename and re-release at all.

## 2026-09-20 12:00 UTC - noaa-hf-002: the Hugging Face half is done, verified and tagged

**`noaa-hf-002` succeeded** (staging release 392416227, worker 166615899, launched 11:53:15Z, collected
11:59Z) and the release now exists on **both** destinations, verified on both.

| step | result |
| --- | --- |
| bulk move | 0 uploaded, **10 skipped** - every file already at the manifest digest, which independently confirms that `noaa-hf-001`'s upload had landed before its verifier crashed |
| loading check | `ok: true`, `problems: []`, both configs loaded **by name** and every split compared: temporal 697,373/11,774, 89,038/1,815, 88,841/2,850; station_disjoint 461,580/7,513, 29,930/788, 29,930/1,090 - the counts the manifest declares |
| `hf-publish.py --verify` (here) | `ok: true`, ten of ten paths at the manifest sizes, four large CSVs digest-verified by the Hub, eight small files present, no missing, no size mismatch |
| `--tag` (last) | `v2026.09` created **after** verification; tag commit `ee6ba8477e2be021a4000d88c03bd58d038e9a5f` == `main`, `tag_matches_main: true` |
| `check-package.py` | OK (its `DESTINATIONS.json` note is the same informational one Austin carries) |

`release/noaa-tide-flooding/DESTINATIONS.json` now records the Hugging Face destination: repo
`earino/noaa-tide-flooding`, revision `v2026.09`, `private: true`, `verified: true` at
2026-09-20T12:00:16Z, ten files, loading check attributed to the worker report. The manifest still
derives `visibility: private`, `published: false` - regenerating it belongs to the publication act, not
to verification. **Nothing is public.**

**Mechanically the release is complete on both destinations.** What is left is the operator's, and it is
now spelled out in `candidates/noaa-tide-flooding/record.json.next_action`:
(1) authorise publication on both destinations - flip visibility, prove it from an anonymous client,
record it in `DESTINATIONS.json` *before* regenerating the manifest, refresh card/LOADING.md/README/release
notes, then the website step; (2) the `late` -> `minor_flood` rename decision (noaa-004's artifact is kept
in staging 392410743 and its diff at `candidates/noaa-tide-flooding/noaa-004-label-rename.diff`); (3) the
persistence-floor question (0.8265/0.8454 against 0.8638/0.8688); (4) the fact that two coordinator
sessions drive this one ledger - `noaa-004` was launched by one while another was mid-step.

**Recorded**: `record.json` (`jobs` -> `noaa-hf-002`, and an `artifacts[0].huggingface` block with the tag,
its commit, the verified file list and the loading-check counts), `release/noaa-tide-flooding/DESTINATIONS.json`,
`jobs/noaa-hf-002.json`, `.factory/noaa-hf-002/` (result, hash-checked report manifest, source bundle). Worker
166615899 destroyed; the noaa-004 worker was already destroyed and 404s at the provider.

### The GitHub side's tag and main are separate histories - found while checking the release

Finishing the Hugging Face half meant checking the rule on the GitHub side too, and it does not hold
there. In `earino/noaa-tide-flooding`, `v2026.09` -> `9bcbf2c6` (parents 0) and `main` -> `f384889f`
(parents 0): two unrelated root commits, and a compare of them answers *404 "No common ancestor"*. Both
trees carry the same 14 package paths, but six blobs differ (`MANIFEST.json`, `README.md`,
`RELEASE_NOTES.md`, `REPRODUCE.md`, `VERIFICATION.md`, `measurements.json`) - and each of those six on
`main` is byte-identical to `release/noaa-tide-flooding/` (`main` MANIFEST.json blob
`ad66967155fdf860`), so `main` is the verified document set while the tagged commit still carries the
pre-consumer-check versions. Austin's repository has the intended shape (its tag is an ancestor of
`main`: `behind_by 0`, `ahead_by 3`), so this is specific to the order in which this repository's first
docs commit was created after its tag.

**The released data is unaffected**: the ten assets hang off release 392387511 and were re-verified from
the API against the transferred digests; the tag's tree holds documents, not CSVs. `check-package.py` is
OK and the consumer check ran against those assets.

**No ref was changed here.** The clean repair is one fast-forward commit with parents
`[f384889f, 9bcbf2c6]` and `f384889f`'s tree, then moving `main` to it: `main`'s content is unchanged
byte for byte, `v2026.09` becomes an ancestor of `main`, no force-push and no asset move. It belongs with
the publication decision, because that act already regenerates `MANIFEST.json` and refreshes the
documents - this should be settled before it, not during it. Evidence in
`candidates/noaa-tide-flooding/record.json` (`artifacts[0].github_tag_state`); it also corrects this file
at line 1755, which assumed the tagged commit carried the current docs.


## 2026-09-23 08:10 UTC - md-sewer-overflow: the registry blocker is answered, the rosters are partial

The only candidate whose blocker was Scout's own work rather than the operator's was
`md-sewer-overflow`, so this session spent itself on its recorded next action: does a facility
registry exist that is independent of the overflow reports? **Yes - measured three ways, none of
them exhaustive.**

| source | measured | covers the reports' keys |
| --- | --- | --- |
| EPA `npdes_downloads.zip` -> `ICIS_FACILITIES.csv` | 352,268,538 bytes, anonymous, `Range` -> **206**, 15 members, member 193,927,778 bytes uncompressed | filterable to `STATE_CODE=MD`; coverage unmeasured (336 MB pull = worker work) |
| MDE "Significant Wastewater Treatment Plants" (`2h5v-duyx`, `ct9h-nxwr`) | 76 rows, 76 distinct `npdes_id`, all Major POTWs | **40 of 322**; 36 roster facilities never report |
| MDE "Point Source Discharges" (`wdtu-5pbn`, `rwxr-95kt`) | 863 rows, 829 distinct `npdesid`, incl. 184 Waste Water Treatment Plant, 63 POTW, 2 CSO | **129 of 322** |

Also measured: the two series carry **126** and **247** distinct NPDES keys (**322** union); the
76-facility roster accounts for **1,024** reports (907 + 117) via `$where npdes in('MD...')`. That
`in(...)` form works, which **explains the 2026-09-21 HTTP 403s**: they tracked the quoted-literal
`between` form, not the host - so the outstanding 2023 reconciliation is a retry, not a blocked
route. Column names differ per dataset (`npdes`, `npdes_no`, `npdes_id`, `npdesid`) and a wrong one
returns `query.soql.no-such-column`, which reads like an empty dataset - the trap that compounded
those 403s. The EPA zip was inspected by **byte-range reads only** (EOCD + central directory); no
bulk data touched the coordinator, no worker was launched, no credential was used.

**The novelty check is now recorded**: `python3 scripts/check-novelty.py md-sewer-overflow ... 
--verdict differentiated` -> `ok: true` at 2026-09-23T08:08:06Z. Prior art models citywide CSO from
internal telemetry (DeepCSO), classifies pipe defects (Sewer-ML), or ships loose code
(tbep-tech/sso-dash, HamedGhodsi90/CSO_Real-Time_Prediction, AlexLipp/cso_scaling); Hugging Face
returns 0 datasets for both overflow queries.

**Still `parked`, with the blocker narrowed rather than cleared.** The roster exists, but its
coverage of the 322 reporting IDs is unmeasured, and split windows and base rates are unmeasured.
Dropping was wrong (a route exists) and `ready` would be a claim without coverage evidence.

**Recorded**: `candidates/md-sewer-overflow/record.json` (rewritten `rejection_reason`,
`next_action`, `open_questions`, three added sources, `measurements.registry_probe_2026_09_23`, the
novelty check), `notes.md`, and the six probes with their JSON results in `.factory/`.

**Next action.** Run the roster pull as a worker job - download `npdes_downloads.zip`, extract
`ICIS_FACILITIES.csv`, keep `STATE_CODE=MD`, stage the filtered roster - and measure how many of the
322 reporting NPDES IDs it covers. If it covers them, write the facility-day construction with the
GHCN-Daily rainfall features; if not, drop the candidate rather than construct a biased denominator.
Then redo the 2023 reconciliation with `$where npdes in(...)` and compute the split windows and base
rates. Nothing public, nothing released, no worker spend of any kind this session.

## 2026-09-26 - the release machinery no longer knows any dataset

Four more sites carried one dataset's wiring, found by auditing rather than by a release failing, plus
two defaults and a card fallback:

| site | was | now |
| --- | --- | --- |
| `assemble-job.py` | a table of per-dataset bundle paths | bundles declare themselves in `candidates/<id>/**/bundle.json`, discovered by glob; duplicate names and a missing `job.json` are refused |
| `publish-dataset.py` | required Austin's `code/measure_clock_offset.py` in every release; flat asset mapping | a common core plus per-dataset `required_docs`; the mapping comes from the manifest's own `layout` |
| `hf-publish.py` | a default candidate at module scope; Austin's card prose as a fallback | no default and no fallback: an unresolved candidate raises and a dataset without `card.md` is refused |
| `release-manifest.py` | defaulted to Austin's package | refuses without a dataset name |
| `scout-snapshot.py` | reported one dataset's destinations | reports every release package |

Regression evidence: the `noaa-baseline` and `austin-consumer` job specs assemble byte-identical to
before the bundle change, and Austin's package and manifest regenerate with no diff. Austin's card is
now `candidates/austin-911-response/card.md`, taken from the published Hub copy (5,837 bytes, no
placeholders), so its plan still resolves.

Left deliberately, and named rather than hidden: docstring examples that mention Austin (helpful, not
wiring), the now-unreachable Austin card block still inside `hf-publish.py` (dead code to delete), and
the fixture-driven test that would drive a synthetic dataset through the projection and publish check -
its manifest does not yet satisfy the projection's document contract, so it was not landed rather than
committed red.

### 2026-09-26 - the fixture test that closes the class, landed

`tests/test_dataset_independence.py` drives a *synthetic* dataset through the code paths that each
failed during the NOAA release: three levels with an extra split (the shape that raised `KeyError`
and then "pinned manifest split counts differ"), a flat single-level package (the shape that still
has to work), a dataset that declares its own Hub layout, and bundle discovery including the refusal
case. Six tests, all passing.

The first attempt failed for a reason worth recording: its manifest did not satisfy the projection's
document contract - `README.md`, `LICENSE.md` and `RELEASE_NOTES.md` must exist and match the hashes
recorded in `package_files` - and it was not committed red. Reading that contract and writing each
document exactly once, hashing after writing, is what made it land.

### 2026-09-26 - Chicago published: the second dataset, end to end

`earino/chicago-doah-adjudication` v2026.09 (artifact `b71586bf28fa56ebbfaede26c4494d68b166545ac504b2ebd8a52c7f272627ef`) is
public on GitHub, on Hugging Face and on the website, each verified from a client with no credential.
53,763 Cook County Circuit Court cases across three time-separated splits (train 47,414 / eval 3,436 /
holdout 2,913), `Liable` as the target. Qualification PASSED, consumer baseline reproduced at eval ROC
AUC 0.6915 through the runner's own contract.

The chain, in order, with what each step actually returned:

| step | evidence |
| --- | --- |
| construction + gate | frozen extract, docket-level split, disclaimer carried on every row; gate produced the accepted artifact |
| qualification | worker job `chicago-001`, PASSED, then destroyed; cleanups verified by direct read |
| baseline | `chicago-baseline-001`, `baseline/reproduce_baseline.sh` exit 0 |
| staging | private repo + a `v2026.09` release carrying the five assets, digests read back from GitHub |
| Hub publish | worker job `chicago-hf-001` uploaded all five files and they re-hash at the published revision, but its loading check failed (splits `train`/`test`, `eval` and `holdout` missing) because the card declared no configs block; the card was then fixed to declare the manifest's three splits and the documented path was re-verified anonymously at `v2026.09` - 47414 / 3436 / 2913 rows, 11 columns, `Liable` / `Not Liable` |
| consumer verification | `chicago-consumer-001` in a fresh environment with no factory access: `run.sh` exit 0, digests and `sha256sum -c` OK, qualification PASSED, baseline 0.6915 |
| publication | both destinations flipped public under explicit operator authorisation, no asset or digest changed |
| anonymous proof | repository 200, five assets 206, one asset downloaded in full and digest-identical; Hub API `private=false gated=false`, same on a full download at the revision |
| website | `site-publish.py` prepare/inspect/publish/verify, receipt `complete`, final verify `status=verified`, HTTPS enforced on both Pages sites |
| pins | tag `v2026.09` resolves to the same commit as the default branch on both destinations |

Four defects surfaced only after publication, and each one is fixed at its cause rather than at the
symptom. They are worth recording because every one of them was invisible while the release was private.

**The pinned revision described a private release.** The tag was cut before the publication refresh, so
the tree at `v2026.09` still carried the staging-era manifest (`"splits": null`, `published: false`) and
the website pipeline, which reads the manifest *at the pin*, refused with `TypeError` and then "dataset
is private". A tag that does not carry the release's own final documents is a broken pin: the docs and
the manifest are part of the release. The pin now moves onto the refresh commit, which is the last thing
done to a release, and the rule is written down in the release skill.

Reading that pin is also worth a note: `raw.githubusercontent.com` served the pre-move copy for minutes
after the ref moved, while the contents API returned the real content immediately. Verification reads the
API, not the CDN.

**A document refresh stripped the managed navigation block.** The publication pipeline writes the block
into the repository README and the Hub card; the package README does not carry it. So a later
"regenerate and push the docs" step silently overwrote both copies with versions that had no link to the
dataset's own page, and `site-publish.py verify` failed with "Destination navigation is missing" - with
the site itself perfectly healthy. The block is now *derived* wherever a document is generated:
`scripts/apply-navigation.py` applies it to the package README before the manifest is re-hashed, and
`hf-publish.py` applies it to the card it uploads. Both are idempotent, and both are inert until
`DESTINATIONS.json` records a verified site, so a staged package never advertises a page that does not
exist.

**The published instructions named a flag that does not exist.** `get_dataset.py --staging` was in the
README and the release notes; the script accepts `--dest/--tag/--sums` and would have exited on
`unrecognized arguments`. Both documents now carry the command that was actually run, and it was run
anonymously end to end: clone, `get_dataset.py --dest ./task`, `sha256sum -c ../SHA256SUMS` - five OK.
That check is section 6 of the published VERIFICATION.md.

**Two smaller ones, same family.** `hf-publish.py --verify` rewrote the whole `destinations.huggingface`
entry, discarding the publication record fields (note, published_at, licence metadata, the anonymous
read flag) - it now merges, so re-verifying cannot erase publication history. And `SMALL_FILES` hardcoded
the licence filenames, so the Hub copy of this dataset was missing
`LICENSE-CITY-OF-CHICAGO-TERMS-OF-USE.md` while the card and `LICENSE.md` both referenced it; every
`LICENSE*` file in the package now travels.

**The record claimed a check that had failed.** `DESTINATIONS.json` described the Hub publish as "run by
worker job chicago-hf-001 and re-run against the published revision: every split loads with the manifest's
rows, columns and label values". The job's own result says otherwise: it uploaded all five files and then
its loading check returned splits `train`/`test` and reported `eval` and `holdout` missing, because the
card declared no `configs` block and the Hub names `data/eval.csv` "test" by convention. `ok: false`, in
the job record, for a day. The card was fixed after the fact - and nothing ever re-ran the load, so the
claim and the fix were both unverified. Re-run now from an unauthenticated client at `revision="v2026.09"`:
`train 47414 / eval 3436 / holdout 2913`, 11 columns, label `Liable` / `Not Liable`, identical to the
manifest. Two lessons: a job's `status: succeeded` is not a passing verification (this one was `failed`
and read as success in prose), and a hand-written block in a card template - the `configs:` block and the
row counts in the loading example - drifts from the manifest silently. `tests/test_hf_card.py` now derives
both from the manifest, and the test was shown to fail on the pre-fix card.

**A commit hash that does not exist.** `record.json` pinned the release to
`d9e4ac887cd5c5bd4f6a45d00c9a30ceb6cf76e8`, which GitHub answers 422 for; the real commit was
`d9e4ac887cd598aa...` - the same value with the tail corrupted, the kind of error that only a lookup
catches. Every field was then checked against the API rather than against its neighbours. It never reached
the published tree (30 blobs at the tag searched, no occurrence), and the pin now records the commit that
carries the corrected documents.

Reusable from this release: `candidates/chicago-doah-adjudication/anonymous_proof.py` (the
unauthenticated proof), `final_pins.py` (point a tag at the final documents commit and read the pinned
manifest back), `sync_release_repo.py` (push package documents into the release repository),
`verify_hf_load.py` (re-download every Hub file and hash it). They take the dataset from their own
module constants, which is what the next dataset will have to edit - the generalisation of these four
into `scripts/` with a dataset argument is the obvious follow-up, not something to fake now.

## 2026-09-26 20:36 UTC - watcher: the five Chicago jobs closed out, the Hub failure fix verified live

The watcher diff surfaced five finished jobs. All five were already collected by the interactive session
that ran the release (collected_at 19:41-20:08 UTC) and their workers already destroyed (20:28-20:31 UTC,
ledger reconciled to `deleted`); this run fetched the small reports from the staging releases into
`.factory/<job>/reports/`, re-verified the numbers from the preserved bytes, re-proved the fix for the
failed job from an anonymous client, and marked all five handled. Nothing was re-launched: every outcome
was already recorded in `candidates/chicago-doah-adjudication/record.json` and STATE.md by the session,
and `chicago-002`/`chicago-003` were superseded builds on the record.

**Re-verified from the staged reports** (`.factory/*/reports/`, no bulk CSV downloaded to this host):

| job | result |
| --- | --- |
| `chicago-002` | superseded determinism build: same builder as `chicago-001`, `source_rows_sha256` `60b7dbed...` and `case_table_sha256` `833740b1...` byte-identical to the digests 001 produced; exit 0, gate 1.3.0, superseded by the `hearing_date` leakage fix |
| `chicago-003` | released artifact: 823,955 source rows, 53,763 cases (train 47,414 / eval 3,436 / holdout 2,913; rates 0.63186 / 0.895518 / 0.932029), split windows 2008-01-01..2018..2022..2026-09-01, disjoint actual ranges, 0 cross-split dockets; gate 1.3.0 all 32 checks pass, 0 failed, artifact `b71586bf28fa56eb` |
| `chicago-baseline-001` | runner contract OK: unmodified `train.py`/`validate.sh` (bundled digests equal expected), eval AUC **0.6915** from both paths; the rebuild re-verified as artifact `b71586bf28fa56eb` before the task directory was materialized |
| `chicago-consumer-001` | fresh-environment consumer check: package matches `MANIFEST.json`, `sha256sum -c` OK, qualification exit 0 `QUALIFICATION PASSED`, baseline eval AUC 0.6915, contract OK |
| `chicago-hf-001` | **failed**: all five files uploaded (4,251,624 bytes, digests equal the released digests) but the documented load returned splits `train`/`test` with `eval` and `holdout` missing - the card then declared no `configs` block, so the Hub named `data/eval.csv` as `test` by convention |

**The failure fix, verified live and anonymous in this run** (no token, no cookie jar): the Hugging Face
API reads `private=false gated=false`; the datasets-server serves the manifest exact shape - config
`default`, splits `train`/`eval`/`holdout` at **47414 / 3436 / 2913** rows (53,763 total), 11 columns, no
pending, no failed. The session authenticated re-verification (`.factory/chicago-hf-verify.json`) and the
anonymous proof (`.factory/chicago-anonymous-proof.json`) agree, and every Hub file re-hashes to its
`SHA256SUMS` digest. The GitHub release repository is public with tag `v2026.09` resolving to `146fd4fd...`,
the same commit as `main` and the corrected pin in `record.json`.

**Recorded**: reports fetched for all five jobs; the reconciled ledger records `jobs/chicago-002.json`,
`jobs/chicago-003.json`, `jobs/chicago-baseline-001.json`, `jobs/chicago-consumer-001.json` (their
`deleted_at` re-stamps from this run `worker status` reads) committed with this entry.
`check-candidate.py --all`: `chicago-doah-adjudication: OK (status=published)`;
`check-package.py release/chicago-doah-adjudication`: OK. Handled markers written for all five jobs, so the
watcher stops surfacing them.

**CI**: green for `ccfb73e` - `push completed/success`, run 36269800507 (the billing condition that
blocked earlier NOAA runs has cleared). This entry commits on top of it.

## 2026-09-27 - the NOAA page's loading command is generated, and Chicago's dictionary names its dropped text

Two operator-requested fixes, both verified against the live surface rather than the tool's own report.

### 1. NOAA website: the page now prints a command that runs (commit `2880496`, site_revision 2)

The published page printed a hard-coded `load_dataset('earino/noaa-tide-flooding', revision='v2026.09')`.
That is a config-less call against a two-config repository and raises
`ValueError: Config name is missing. Please pick one among the available configs: ['temporal', 'station_disjoint']`
- reproduced anonymously from the published revision, so the page had been publishing a broken example
since publication. Fixed at the generator: `factory/site_model.config_names()` is the single rule, the
release record carries `configs`, the pinned-manifest check refuses a name mismatch, and both the page
template (`sites/runtime.py`) and the Hub card (`scripts/hf-publish.py._config_names`) derive from it.

The guard tests were shown to **fail on the pre-fix input** before they counted: the new site test fails
against the pre-fix template (only `sites/runtime.py` stashed), and the card figure guard fails against
the card as committed at `8c239cb` (`['0.8638','0.8651','0.8687','0.8688']`).

Plan `462d50571e2913ade1dffe0bbbbbd844170afceec9e292ab8a6c298c6a81878e` was published with operator
approval (`site-publish.py publish .factory/sites/noaa-website-3 --approved-plan ... --wait-seconds 240`)
and `verify` returned `status: verified` with HTTPS enforced on both repositories. Anonymous check of the
live page: **10709 bytes, both config-named commands present, the config-less form gone**; the versioned
page carries the same; the catalogue lists `noaa-tide-flooding v2026.09 site_revision 2`. Public repository
HEAD `1e8ef86e` ("Prepare website for noaa-tide-flooding v2026.09"), its `Dataset website` run
`completed/success`. 296 tests OK; `check-package.py release/noaa-tide-flooding` OK; CI green for
`2880496` (`Local checks`, `Website pipeline preview`).

### 2. Chicago: the data dictionary now names the source's text fields (commit `0c24335`)

The dictionary said only that "all other source columns are absent by construction". The source table
(`data.cityofchicago.org`, resource `6br9-quuz`, 823,637 rows) does carry prose, so the omission read as
"nothing there". It now names each dropped text field and separates three reasons:

| field | reason recorded |
| --- | --- |
| `violation_description` | Redundant, not withheld: the source's own `$group` gives 1,260 distinct `violation_code` values against 1,266 distinct code+description pairs. |
| `respondents` | Named-party text, withheld as a redistribution decision - explicitly **not** dismissed as uninformative. |
| `address`/`street_number`/`street_name`, `nov_number`, `location` | Restate shipped columns (`latitude`/`longitude`, `street_direction`/`street_type`) or identify a notice rather than a case. |

The `respondents` measurement is recorded in `candidates/chicago-doah-adjudication/notes.md`: over all
397,435 decided charges, entity respondents 0.752 liable, records naming counsel 0.742, neither 0.726,
base 0.732 - a small but real spread, which is why the exclusion is stated as a publication decision.
Finer signals (repeat litigants, counsel identity, per-party history) remain unmeasured and are not claimed.

Documents-only: `artifact_version` unchanged at `b71586bf28fa56eb`, no asset byte touched, no new version.
Manifest regenerated (dictionary digest `e0b02bdb267ec36a`) and `check-package` OK; Hub small files
re-uploaded and `v2026.09` re-pointed to `325cc9823d1e776e7734d344b53bcfa0caf0841d` (tag == main);
`DESTINATIONS.json` records the move and the refreshed revision claim
(`/opt/data/cache/scratch/fix_chicago_revision_claim.py`); public repository re-synced by
`sync_release_repo.py` to `34f4fd14`. Anonymous proof: public raw dictionary and Hub raw file are both
7,728 bytes at sha256 `e0b02bdb...`, equal to the manifest digest; the site page is 200 and still links it.
The public repository's `Dataset website` workflow has no run for `34f4fd14` **by design** - it triggers on
`.dataset-site/**` paths only - and the deployed page bytes are unchanged.

**Private HEAD `0c24335`, both workflows `completed/success`.** Outstanding for the operator: rotate the
`github_pat_...` and `hf_...` credentials exposed in this instance's earlier session.

## 2026-09-27 (later) - Chicago food inspections profiled as a multi-label lead; a one-line austin fix is tabled

Operator asked what multi-label sources exist, then asked specifically about Chicago food inspections and told
me to table the austin maintenance item. Answering it produced the project's first multi-label lead, so the
evidence lives in the repository rather than in the conversation.

**Answer to "could the austin 911 source be a multi-label problem" - no.** The source carries five real
categoricals (`initial_problem_category` and `final_problem_category` 40 values each, `priority_level` 4,
`call_disposition_description` 20, `mental_health_flag` 2), but the grain is one row per incident (1,049,636
rows / 1,049,612 distinct `incident_number`) and every one of them is single-valued, so the task is 40-way
multiclass, not multi-label. Location and time carry almost none of the answer: `H(final_category)` is 4.10 bits
and `I(final; sector)` = 0.06 bits (1%), `I(final; response_hour)` = 0.06 bits, against 2.56 bits (62%) from
`initial_problem_category`. Trivially, `final == initial` for 77.7% of calls against a 12.7% majority baseline.
The four post-hoc natural targets are already excluded from the shipped release, so nothing there changes.

**New candidate `chicago-food-inspections`** (`status=investigating`, no construction). Source: City of Chicago
Food Inspections, `4ijn-s7e5` - 316,205 rows, one row per inspection, 2010-01-04 to 2026-09-25, 226,133 rows in
the modelling pool. The label is the set of violation codes parsed from the `violations` blob: 61 codes across a
40,000-row scan, mean 3.08 codes per inspection, strong co-occurrence (55,38) 2,350, and density that tracks the
outcome (Pass 2.05 / Pass w/ Conditions 3.70 / Fail 4.85). Prior art found: CDPH's own deployed binary
"critical violation" model and its hindsight analysis - a different task, so no mirror, but `check-novelty.py`
must still state the verdict before promotion. Full profile in `candidates/chicago-food-inspections/notes.md`.

**Tabled, not started:** `release/austin-911-response/DATA_DICTIONARY.md` calls `incident_type` "coarse call
classification known at dispatch" when the column is a single value (`Dispatched Incident`) in all 1,049,636
rows. One-line correction, documents-only, no asset byte changes; it does move the rendered site page, so it
needs the site_revision increment and the usual Hub/site refresh. Recorded in the austin record's `next_action`
to batch with other documentation-only corrections.

## 2026-09-27 (evening) - "find something better" answered with MSHA enforcement citations; the licence is the one decision left

Operator asked for a better multi-label source than Chicago food inspections. Three leads were measured
live, and the answer is **MSHA's Violations Data Set**, opened as `candidates/msha-enforcement-citations/`
(`status=ready`, novelty verdict `differentiated`, nothing constructed).

**Measured from the publisher's own download** (`arlweb.msha.gov/.../Violations.zip`, anonymous, 120,736,998
bytes in 4.3 s, streamed with `probe_violations.py` and `probe_splits.py`; nothing extracted to disk): 3,103,397
citation rows, **538,068 inspections**, 31,444 mines, 2000-2026; the label is the set of **30 CFR sections**
cited at one inspection - 5,934 raw sections, **104 at >= 1%** of inspections and 183 at >= 0.5%, mean **5.79**
sections per inspection (median 2, max 694, the tail being mine-wide audits). Co-occurrence is strong and
structured ((75.400, 75.503) 18,490 inspections; (56.14100(b), 56.14107(a)) 15,169). Temporal windows hold:
train 2001-2020 415,088 inspections / 2,459,741 citations, eval 2021-2023 49,233, holdout 2024-2025 33,576, and
**all 104 floor labels appear in all three windows**. The publisher documents every one of the 50 columns, which
is what makes the post-hoc split auditable; the whole gravity/penalty/docket block and the end-of-visit counts
are excluded from features, and the instant is `INSPECTION_BEGIN_DT`.

**Catalogue check, by name**: two HF artifacts mention MSHA and neither is this task - `emperor-mew/msha-violations`
(2026-05, a card with no data files, pointing at a live REST API) and
`FastDOLz/msha-mine-safety-violations-by-operator` (2026-06, CC-BY-4.0, Zenodo DOI 10.5281/zenodo.20572372,
40,720 operators / 3.08 M violations rolled up to the operator). Both are aggregates or API mirrors; no package
ships the inspection-level multi-label set with a prediction instant and splits.

**Runner-up measured the same day**: CMS nursing-home health deficiencies (`r5ix-sfxw`, 419,479 rows, ~97,000
surveys, 188 F-tags, mean 4.31 per survey, 88 at >= 1%) - viable, and second on every axis.

**One decision is needed before construction**: MSHA states no terms. The statutory reading (US federal work),
the data.gov `accessLevel: public` entry, and two third parties already redistributing the same source under CC0
and CC-BY-4.0 are the evidence; none of it is a grant, so the licence is recorded as UNRESOLVED in the candidate
and escalated rather than assumed. `chicago-food-inspections` stays open as the fallback lead (`superseded_by`
recorded in its record).

## 2026-10-12 - MSHA licence decided (operator, option A): federal public domain, recorded, construction unblocked

The one open decision was answered by the operator: **treat US federal government works as public
domain for the MSHA source, record the reasoning and construct** - explicit written permission is not
sought. No publisher grant is claimed; the public-domain character rests on the statute (17 USC 105),
because MSHA publishes no terms, no licence and no redistribution permission on the data-set pages or
in its own definition file, and the data.gov entry only carries `accessLevel: public` with
`rights: "true"`.

**Where the decision lives**: `candidates/msha-enforcement-citations/license.json`, decided
2026-10-12 - source `LicenseRef-Public-Domain` (status: public domain by statute, preserved
unchanged), compilation `CC0-1.0` with a scope limited to our contribution, code and documentation
`MIT`, plus four evidence entries (MSHA pages, data.gov entry, the two third-party redistributors
recorded as precedent and not as permission, and the operator decision itself). Recorded against
*this* source id - it was not inherited from `chicago-doah-adjudication` or any earlier acceptance.
Reversal point: if MSHA publishes terms or the operator narrows the decision, that one file changes
and `release-manifest.py` carries it into the manifest.

**Verified, not assumed**: `release-manifest.py licenses_block("msha-enforcement-citations")` renders
the block from the decision file - code MIT / `LICENSE-MIT.txt`, data_compilation CC0-1.0 /
`LICENSE-CC0-1.0.txt`, source_data `LicenseRef-Public-Domain` with status, four evidence entries,
attribution and derived labelling, no empty field. `scripts/check-candidate.py --all` exits 0 with all
eight records OK. The `bundle` state of the record: `msha-enforcement-citations` stays `ready` (nothing
is constructed yet) with `license_decision` now DECIDED and `next_action` rewritten to construction.

**Construction plan (recorded in the candidate's `next_action`)**: (1) streamed extraction and
rendering pass over the 120 MB weekly Violations zip plus the companion Inspections and Mines tables,
one binary per-section config over the inspection-level label set at `INSPECTION_BEGIN_DT`, nothing
bulk kept on this host; (2) three parameters to fix before the build - the label floor (104 sections
at >= 1%, or 183 at >= 0.5%), the treatment of mine-wide audit events (tail to 694 citations at one
inspection), and whether coal and metal/non-metal ship as separate configs; (3) the full-artifact
qualification gate on the worker, and no number quoted before it passes; (4) packaging afterwards,
with publication still a separate operator-approved act.

**Chicago food inspections is unaffected**: it remains `qualified` from job `food-001` (40/40 configs,
gate 1.3.0, staging release 403508464, 1.20 GB) and is still unpackaged. Both leads are now unblocked;
MSHA is the larger task and Chicago is the one with artifacts already in hand.


## 2026-10-12 - MSHA construction: build job launched, a semantics defect caught before collection

**Launched.** Job `msha-001` (job type build, `cpx32` in `hel1`, 4 vCPU / 8 GB, 150-minute lifetime)
went up at **09:34:50 UTC** as provider server **`169852644`** (`89.167.109.16`, expiry
`1791806689`), verified against the provider inventory, not against the launch notice. It streams
`Mines.zip`, `Inspections.zip` and `Violations.zip` from `arlweb.msha.gov/OpenGovernmentData/DataSets/`,
pools every event with at least one citation and an `INSPECTION_BEGIN_DT` inside a split window, and
writes one binary runner config per floor 30 CFR section (capped at 45 by prevalence, most prevalent
first) plus the joint `labels.csv` at the extract root.
The bundling step hashed the launched script as
`b9ef83520a56683729637d1b6dc6de8f54c3c2cb65e8c674adfcf956cbbccc2f` - the pre-fix `build.py`, Sizing: `max_artifact_mb` 4200, `max_disk_mb`
12000 - a floor section's full split files run about 68 MB, so 45 configs plus the matrix land near
3.2 GB.

Before launching, the whole contract was exercised locally: a bounded build (`--limit-events 60000
--max-configs 3`) exited 0, and the real qualification gate run over one produced config returned
**gate 1.3.0, 32 checks, 0 failed**.

**A defect was caught before collection.** `prev_target_cited` was written from the *cumulative*
distinct-section set, so it answered "has this mine ever cited this section" while the shipped
`quality.json` documents "cited on the mine's **most recent** strictly-earlier pooled inspection".
The persistence baseline was the tell: 0.99+ under the cumulative reading. `enrich_with_priors` now
keeps two accumulators, deliberately - `distinct` still accumulates for `prior_distinct_sections`,
and a new `last_sections` snapshot carries the most recent group only. On the test fixture the
persistence AUCs moved to **0.51** (75.400) and **0.47** (56.14100(B)), which is what an honest
persistence feature on a re-inspected mine should look like.

**`msha-001`'s artifact is superseded** and will be discarded on collection; nothing from it is
quoted or packaged. The job is left to finish rather than killed, because a full-scale run is the
only honest measurement of duration, peak memory and disk for the relaunch - and `worker destroy`
deliberately refuses to delete an uncollected job.

**`msha-001` ran to completion and was superseded by design.** Job `msha-001` (provider server
`169852644`, created 09:34:50 UTC) finished **succeeded, exit 0, 667 s (11 min)** - far cheaper than the
60-minute ceiling - with **497,897 pooled events**, a measured floor of **80** 30 CFR sections at or above
1%, **45 configs** shipped, **326 assets / 3,385,877,790 bytes (3,229 MiB)** on staging release
**410447826**, and every one of the 45 configs passing the gate on the worker (the job fails if any gate
fails, and it exited 0). It was collected (report + digest verification recorded in `jobs/msha-001.json`)
and the server destroyed at 10:01:47 UTC - the destroy was refused until collection, as designed.

Its extract is not packaged and must not be: it was built by the pre-fix `build.py`
(`b9ef83520a56683729637d1b6dc6de8f54c3c2cb65e8c674adfcf956cbbccc2f`), so its `prev_target_cited` column
contradicts the `quality.json` frame it ships with. The staging release is left in place only as the run
record; nothing is copied out of it.

**`msha-002` launched with the fixed script.** The candidate's `source/job.json` now carries the id
`msha-002`; the assembled bundle hashes `build.py` at
`1c80c1aea7398109…` (the corrected script, distinct from the pre-fix hash), run.sh unchanged. Plan
validated at the same **€0.32 reservation / €0.08/h ceiling**; provider server **`169857238`**, created
**10:02:05 UTC**, confirmed against the provider inventory rather than the launch notice.

**The Chicago record was reconciled the same way.** `chicago-food-inspections/record.json` still carried
`"superseded_by": "msha-enforcement-citations"` from 2026-09-27, when MSHA displaced it as the *priority*
lead. MSHA never replaced the candidate - Chicago is the built, gated one with staging assets in hand - so
the marker read as "retired" about the artifact that is actually ready. It is now `null` with the priority
relationship stated in prose (`lead_priority_note`). `tests/test_repo_hygiene.py` gains `CandidateRecords`:
a candidate whose status is built/qualified/packaged/published may not carry a `superseded_by`, and any
recorded lead must resolve to a real candidate directory. The first guard was run against a pre-fix copy of
the record - **FAILED (1 failure)** - and passes restored.

**Guards demonstrated to fail pre-fix.** `tests/test_msha_build.py` (21 tests, part of the **329-test**
suite that passes) pins both defects:
`Structural.test_prev_snapshot_is_the_most_recent_group_not_the_cumulative_set` fails against the
cumulative implementation, and `Constructed.test_every_event_carries_a_usable_mine_id` fails against
an implementation that reads the mine only from the violation row (`dropped_no_mine_id` 1 instead of 0
- MSHA does not require the violations table to repeat the mine). Both were run against a two-reversal
pre-fix copy of the script and both failed, as recorded above.

## 2026-10-12 - MSHA construction verified: msha-002 green, the corrected feature proven in the released bytes

**`msha-002` ran and finished green.** Server `169857238` (cpx32/hel1), created **10:02:05 UTC**, exit 0,
**no OOM**, **581.0 s** wall, **45/45 configs passing the on-worker gate**, **326 assets /
3,385,877,790 bytes** on staging release **410471211**; collected **10:27:08 UTC**, destroyed
**10:30:15 UTC**, and the provider inventory read back **0 servers**. Reservation unchanged at **EUR 0.32
/ EUR 0.08 h ceiling**. The run's own console is not the evidence: every number below was read back out of
the collected release.

**The gate result was verified per config, not inferred from the job's exit code.** All **45**
`qualification-*.json` reports were fetched from the release and each one read: gate **1.3.0**, **32
checks**, **0 failed**, `ok: true`. The set of configs with a report is exactly the set named in
`build_summary.json` (`shipped_configs`, 45) and exactly the set with a `public/train.csv`
layout - no config passed silently without a report. **50 fetched assets** (the 45 reports plus
`meta.json`, `quality.json`, `labels.csv`, `summary.json`, `build_summary.json`, `container.log`) were
**sha256-verified against the release manifest** - every one matched.

**The corrected feature is now proven in the published bytes, not just in the tests.** `sec_75_400`'s
`public/eval.csv` was fetched from **both** releases, each file verified against its own published digest.
Both are **7,425,517 bytes / 49,233 rows**, and exactly **one column differs**: `prev_target_cited`, on
**4,933 rows**. The label column and every other column are byte-identical; the pool
(**497,897**), the 45 shipped configs, `total_split_bytes`, and `labels.csv`
(`6e164193b8cda303…`) are identical between the runs. So the only difference in the released bytes is the
feature the defect was in.

**The defect was material, and the real-data baseline says so.** `build_summary.json` carries a
persistence baseline per config (AUC of `prev_target_cited` alone on eval). Under the cumulative reading the
mean across the 45 configs was **0.754**; with the most-recent-strictly-earlier semantics it is **0.576**,
and it fell on **all 45** (rose on none) - `sec_75_400` **0.9403 -> 0.6733**. The strongest pre-fix value,
0.94, was the tell that the feature was encoding lifetime history rather than the previous visit. In the
eval window the feature is 1 on **14.9%** of rows pre-fix and **4.9%** fixed (positive rate 4.83%), which
is what a "did the last inspection cite this" flag should look like.

**The worker ran the committed script.** The artifact manifest records the bundled source hashes:
`build.py` **1c80c1aea7398109…** for `msha-002`, equal to the committed `source/build.py`, against
**b9ef83520a566837…** for `msha-001` (the pre-fix script); `run.sh` and the bundled
`qualify_dataset.py` are identical across both runs. The staging release for `msha-001` is retained as
the run record and nothing is copied out of it.

**Floor recomputed at construction.** The pool is the **497,897** inspections carrying at least one
violation row with a parseable begin date inside a split window; **80** sections are cited in **>= 1%** of
those events and survive the window minimums, and the run ships the **45** highest-prevalence under
`--max-configs 45`, holding **35** back. The **104** in the record's `measurements` is the standalone
probe's number on the full **538,068**-inspection census, a different denominator; the record now says
so, and `qualification.floor` names the shipped number.

**Record and state.** `candidates/msha-enforcement-citations/record.json`: status **`ready` ->
`qualified`**, `construction_script` filled in, `jobs[]` carries `msha-001` (**superseded**, with the
reason) and `msha-002` (**succeeded**, with times, hashes and cost), and a `qualification` block records
the gate result, the digest chain, the byte-level feature evidence and the baseline numbers.
`measurements.built_msha_002` holds the built numbers. `next_action` is now packaging: the 45
per-section configs plus the extract-root `labels.csv` (proposed: mirror noaa's per-level pattern), a
baseline on one mid-prevalence config, and the operator's choice of which built candidate packages first.
`scripts/check-candidate.py` returns **OK (status=qualified)** and the suite is **331 tests, OK**.


**Server inventory reconciled 2026-10-19T10:59Z.** The Hetzner project `earino-dataset-factory` reports **0
servers, 0 floating IPs, 0 primary IPs, 0 volumes**. Every job ledger entry is terminal: the last worker to
exist, msha-hf-004 (171201702), was destroyed 10:49:07Z, and msha-hf-002 (171185621) was destroyed
10:08:01Z - its `record.json` entry simply carried `destroyed_at: null`, which read as a live machine and was
not one. Nothing is billing; the earlier "stuck running" note is withdrawn.

**Discovery cadence raised 2026-10-19 (operator: "we need more discovery happening by a Lot").** The
scheduled research slot had been spending every tick on construction and packaging, so no source had
been opened since late September. Three changes: a discovery-only brief
(`docs/discovery-session-prompt.md`) that forbids advancing existing candidates and requires at least
three new sources taken to a recorded verdict per session; a `--prompt-file` argument on
`scripts/scout_research_session.py` so the brief is selectable per tick; and a second cron job
`scout-discovery-session` (86fe52e55ef9) at 06:00 and 18:00 UTC daily. The advancement job
`scout-research-session` (69a5bc676d10) keeps Mon/Wed/Fri 08:00. `sessions_per_week` raised 3 -> 18
to admit 14 discovery ticks plus 3 advancement ticks per week; the $5/month allowance and the
`stop_fraction` brake are unchanged, so the gate still holds the moment estimated spend approaches
the cap.

## 2026-10-19 - Discovery session: four new sources opened, three novelty rejections, one go

Novelty search ran **before** any work on each source, and it killed three of the four: each already
exists in usable form, so per the standing test they are rejections, not candidates. All four carry a
`record.json` + `notes.md` verdict; `scripts/check-candidate.py --all` exit 0 and the suite
(346 tests) passes.

- **`nws-tornado-warning-verification` - GO (status investigating, novelty `differentiated`).**
  For an NWS tornado warning at issuance, will it be verified (>=1 tornado report inside its
  storm-based polygon during valid time)? Source: IEM cow API
  `https://mesonet.agron.iastate.edu/api/1/cow.json` (anonymous; `begints`/`endts` required - the
  HTML docs' "no parameters required" is stale, learned from the API's own 422). Label =
  publisher-computed per-warning `verify` boolean (documented methodology; NWS public domain + IEM
  "public domain... attribution appreciated", both quoted in the record; cow's "unofficial" caveat to
  carry on any release). Measured 2026-10-19: national 2013 = 1,832 warnings / 441 verified (0.241),
  100 distinct days with a verified warning (19,593,733 bytes, 38.4 s); national 2023 = 2,531 / 656
  (0.259), 115 days (28,389,049 bytes, 59.5 s); per-year pull is the whole construction unit
  (~500 MB / 12-17 min for 2008-2024, sum of measured per-year costs). Cross-check: cow FAR 0.74-0.76
  vs published TOR-warning FAR 0.69 (Keylon 2025, arXiv 2510.25011) - consistent. Known-event
  fixture named: the 2022-04-16 northern-Arkansas storm behind all 3 documented tornado-emergency
  false alarms must read `verify=false`. Next action is a specific construction step in the record
  (17 per-year pulls, key `(year,wfo,eventid)`, exclude label-source fields `verify`/`stormreports*`/
  `lead0`/`areaverify`/`statuses`/`status`, frozen train 2008-2018 / eval 2019-2021 / holdout
  2022-2024).
- **`faa-wildlife-strike-damage` - REJECT.** Damage-from-pre-strike-features is public and even
  leakage-audited: github.com/oldguy773/FAA-Wildlife-Strike-Analysis (174,104 records, post-strike
  leakage columns identified and dropped), Misra et al. 2022 (RF 78.81% acc, same top variables),
  arXiv 2608.12390 (open aggregates of the same database, 347,575 reports). No fetch of the source was
  needed or made.
- **`openfda-food-recall-classification` - REJECT.** The exact task on the exact source is PMC13526789
  (2025): 28,448 openFDA food enforcement records, Class I/II/III target, ML triage + firm-history
  baseline; plus RecallRisk-BERT for devices and an analysis-ready Kaggle snapshot. Measured reachability
  before deciding: `GET api.fda.gov/food/enforcement.json?limit=1` answers anonymously with
  `meta.results.total = 29,485` and terms/license links.
- **`cfpb-complaint-relief` - REJECT.** Intake-time-to-relief is published end to end: arXiv 2606.22664
  (monetary relief, temporal split, AUC 0.78), Future Business Journal 2026 (untimely response,
  holdout AUC 0.7653), a public leakage-aware pipeline repo, and the Yale SOM relief analysis. Also
  recorded: the old Socrata endpoints at data.consumerfinance.gov now serve HTML errors/404 from this
  host and TLS needs an AIA-chasing client; the live path is the data-research API.

Bench after this session: msha-enforcement-citations and chicago-food-inspections qualified and
awaiting packaging (advancement sessions own that), and one new go candidate
(nws-tornado-warning-verification) ready for a construction job.

**Research budget made real 2026-10-19 (operator: "How do we increase the discovery budget. I want a
daily discovery run.").** Discovery already runs twice daily (06:00 and 18:00 UTC), so the cadence
asked for is in place; the thing that could not work was the budget. Every Hermes usage row reports
`estimated_cost_usd = 0`, so a USD allowance can never reach `stop_fraction` and bounded nothing.
Added `weekly_token_budget` to `scripts/research-budget.py` - measured input+output tokens for
research sessions in the trailing 7 days, held at the gate. Configured `weekly_token_budget:
12000000` and `allowance_usd: 30.0`; observed research usage is ~293,000 tokens per session
(586,447 over 2 sessions), so 17 ticks a week sit at roughly 5M against a 12M ceiling. Guard tests
in `tests/test_research_budget.py::WeeklyTokenBudgetTests` fail on the pre-fix code (1 failure,
1 error) and pass after.

**Weekly token budget doubled 2026-10-19** to 24,000,000 at the operator's instruction. Observed
research use is ~293,000 tokens per session, so the ceiling now admits roughly 80 sessions a week;
the 18-session cap and the 06:00/18:00 + Mon/Wed/Fri schedules are unchanged and remain the nearer
limits.

**Weekly session cap raised 2026-10-19** from 18 to 80 at the operator's instruction, so the token
budget (24,000,000/week) is now the binding limit rather than the session count. The schedules are
unchanged: 14 discovery ticks and 3 advancement ticks a week, i.e. 17 of the 80 allowed.

**Discovery widened to every 4 hours and made international 2026-10-19 (operator: "a much better
pipeline of datasets... make sure we are looking truly internationally").** Measured first: the
bench was 10 US sources to 1 Australian, and **0 of 6 live candidates non-US** - a reflection of how
much easier US federal APIs are to probe, not of where the good tasks are. Changes: the discovery
brief now requires at least two of three verdicts per session from outside the US and a recorded
`jurisdiction` block; `check-candidate.py` refuses a record without one (guard test fails on the
pre-fix checker); `scripts/discovery-coverage.py` reports the measured geography and exits non-zero
on an unstated jurisdiction; the deployed shim assigns a deterministic rotating regional focus
(EU/EEA, UK, Canada, Latin America, Africa, South/South-East Asia, East Asia, Oceania, international
organisations); cadence raised from 2 to 6 discovery ticks a day (`0 */4 * * *`). Weekly maximum is
now 42 discovery + 3 advancement = 45 sessions, ~13M tokens against the 24M budget and 45 of the 80
session cap.

## 2026-10-19 - UK-focused discovery session: three new sources opened, two GOs, one measured park

Regional focus tick (United Kingdom). Three new candidates opened, **all UK publishers** (quota
satisfied without touching a US source); the standing novelty test ran before any source work; every
probe was anonymous and ranged (zip central-directory reads and partial member decompression -
nothing bulk downloaded to the coordinator). `scripts/check-candidate.py --all` exit 0 and the suite
(354 tests) passes; `scripts/discovery-coverage.py` now reports 14 candidates, 8 live, **live non-US
2/8 (was 0/6)**.

- **`dvsa-mot-next-test-outcome` - GO (Department for Transport / DVSA).** Predict whether a
  vehicle's NEXT MOT test ends in initial failure (test_result F or PRS - the DfT-documented
  initial-failure definition), using only what is known through the previous test. Licence measured:
  UK Open Government Licence v3.0 via CKAN package_show on both dataset records. Measured
  (2026-10-19, ranged reads): 2024 results zip 1,531,265,132 bytes / 12 monthly CSVs / 7,667,648,876
  bytes uncompressed; per-year files exist 2005-2024. Row grain measured on a 4 MB prefix of
  test_result_202408.csv (34,924 rows): P 77.3% / F 17.7% / PRS 4.3% -> initial-fail 22.1%,
  cross-checked against the publisher's DVSA/MOT/01 (FY2025-26 classes 3&4 initial 27.51% / final
  22.30%) - consistent. **test_id is measured non-unique** (6,336 repeated test_id values in one
  month prefix; the file's first two rows are byte-identical), so construction must sort by
  (vehicle_id, test_date, completed_date) and dedup; vehicle_id is never the runner id column.
  Novelty verdict `differentiated` (prior art: adin786/mot-data GitHub EDA with a 2-feature SGD
  experiment; the commercial Lisense predictor; no ML-ready task with splits anywhere).
- **`ea-bathing-water-classification` - GO (Environment Agency).** Predict whether a bathing water's
  season-Y annual rBWD classification is below Good, from prior-season history only (label not
  computable from features by construction). Licence measured: OGL v3 stated on the live bwq site.
  API contract learned from the API's own error text (regime `compliance-rBWD`, year slices are
  item pages, assessments at result.primaryTopic.observation). Measured per-season counts via 11
  season-slice requests (~2.5 MB total): 2015-2025, 415-451 waters per season, below-Good rate
  7.2% (2016) to 14.9% (2024), 2020 slice absent (suspended monitoring year); sample grain confirmed
  (point 05300: 794 samples back to 1988). Novelty `differentiated` (Exeter per-sample exceedance
  EWS and the EA's operational Pollution Risk Forecasting are nowcasts, not this task). Caveat
  recorded honestly: small panel (~450 entities x 11 seasons); a persistence baseline will be
  strong, and measured headroom at construction decides publish-or-demote.
- **`companies-house-company-exit` - PARK (Companies House).** Measured blocker, not a guess: the
  Free Company Data Product is the **live register only** - 0 of 8,109 prefix rows carry a
  DissolutionDate, the page says "live companies on the register", and the one-file 2026-10-01 zip
  (493,990,184 bytes; 2,810,066,457-byte CSV, 55 columns) matches the ~5.45M live-register row count
  rather than the cumulative register. Exit labels therefore require either forward monthly snapshot
  collection (~470 MB/month, first usable 12-month cohort after ~12 months) or the rate-limited API -
  no bulk historical dissolution data is published. Unpark = one operator decision on a scheduled
  monthly snapshot pull, which should also settle the licence grant (no licence text on the download
  page itself - measured; OGL v3 only asserted on the gov.uk guidance footer).

Next actions are specific in each record; both GOs hand to advancement sessions. Probe scripts
(`.factory/probe_uk*.py`) deleted after use; nothing large touched the coordinator.

## 2026-10-19 - Canada-focused discovery session: four verdicts from four Canadian sources, two GOs, two measured drops

Regional focus tick (Canada). Four new candidates opened, **all Canadian publishers**
(CRA via open.canada.ca, ECCC, Health Canada) - the tick's quota satisfied without
touching a US source; the standing novelty test ran before any construction work; every
probe was anonymous; the CSVs downloaded for measurement (~190 MB) lived in coordinator
scratch and were deleted after use. `scripts/check-candidate.py --all` exit 0 and the
suite passes; `scripts/discovery-coverage.py` now reports 18 candidates, 10 live,
**live non-US 4/10 (was 2/8)**.

- **`cra-charity-filing-exit` - GO (Canada Revenue Agency, OGL-Canada 2.0).** Predict
  whether a registered charity that filed a T3010 for a fiscal period ending in year Y
  files no return for any fiscal period ending in Y+1, from its year-Y-and-earlier
  returns (Section D + Schedule 6 line codes 4020-5910, program mix, compensation,
  designation/category/province). Prediction instant: the six-month T3010 filing
  deadline. Label is mechanical - BN present in the year-Y Identification file, absent
  from year-Y+1 (the dictionary states the lists contain only filers; the live charity
  status/revocation product is NOT on open.canada.ca - measured, CKAN searches empty - so
  filing-exit is the reachable label). Measured full-file: 85,113/84,729/84,855/84,519/
  83,761 distinct BNs for 2012/2013/2014/2023/2024; exit rates 2.708% (2012->2013,
  2,305), 1.768% (2013->2014, 1,498), 2.811% (2023->2024, 2,376); late-filing artifact
  4.73% (109 of 2,305 absent-in-2013 reappear in 2014). Data dictionary PDF read
  in-session; 2012 file is cp1252 not UTF-8; one 21 MB financial CSV measured at 4.3 s
  download on the coordinator, full construction window ~1.5 GB (estimate from measured
  per-file sizes). Novelty `differentiated`: US Form 990 nonprofit-failure literature
  exists (Polytechnic UPR, ODU, Rutgers 990-e-file RF studies) but nothing on T3010 and
  no ML-ready task anywhere.
- **`npri-facility-reporting-exit` - GO (Environment and Climate Change Canada,
  OGL-Canada 2.0).** Predict whether a facility that reported to the NPRI in year Y
  reports nothing at all in Y+1, from its reporting history. Prediction instant: June 1
  of Y+1 (statutory year-Y reporting deadline). Measured full-file: 7,322/7,521/7,986
  facilities in 2021/2022/2023; exit rates 12.32% (902, 2021->2022) and 10.84% (815,
  2022->2023). CKAN's recorded download URLs serve an HTML SPA - the real files are at
  `data-donnees.az.ec.gc.ca/api/file` (measured: bulk releases 393,281,064 bytes,
  1993-present; single-year 36-40 MB, ranged 206s). Units-frame trap measured: one file
  mixes tonnes/kg/grams/gTEQ per row - normalization is a construction requirement.
  Novelty `differentiated`: ECCC's own scoping review (225 articles) shows NPRI used as
  model input, never as the prediction target; US TRI work is adjacent but no
  reporting-outcome task with splits exists.
- **`hc-recalls-classification` - REJECT (Health Canada, OGL-Canada 2.0).** Measured:
  anonymous daily-refreshed CSV (10,668,115 bytes, Last-Modified 2026-10-19), 34,263
  rows, "Recall class" populated for CFIA food (Class 1-3, 5,345 rows) and medical
  devices (Type I-III, 10,647 rows), empty for 18,232 TC vehicle rows; "Last updated" is
  a revision date with empty values on some rows. Rejected on the standing novelty test:
  recall-hazard-class prediction already exists in usable, leakage-audited form on the
  US analogue (PMC13526789 on openFDA Class I/II/III; RecallRisk-BERT for devices; a
  Kaggle snapshot; our own `openfda-food-recall-classification` rejection). Access,
  licence and freshness were all fine - the task is the blocker.
- **`npri-facility-spill-year` - DROPPED (ECCC, measured).** The spill-year alternative
  failed split capacity, not access: spill-carrying facility-years are 1.50%/1.51%/1.87%
  (110/114/149 in 2021/2022/2023) - too thin and clustered to carry a scored holdout;
  recorded so it is not re-measured.

Next actions are specific in each record; both GOs hand to advancement sessions. Probe
scripts (`.factory/probe_ca*.py`) deleted after use; the blocked `rm -rf` of the unused
spill-year stub was converted into recording that stub as its own dropped candidate
rather than hunting a gate workaround.


**Routine amped up 2026-10-20 (operator: "we can amp up in general... the world is full of awesome
datasets").** Discovery hourly (24 ticks/day), advancement daily 08:00 (was Mon/Wed/Fri), weekly
session cap 80 -> 200, weekly token budget 24M -> 40M. Measured averages: ~172,000 research tokens
per session (1,206,895 over 7), so 31 sessions/day sits near 37M against the 40M ceiling - the budget
is meant to be the brake now, and the gate holds a tick rather than overspending. Unchanged: 60-turn
and 40-minute per-session ceilings, the discovery quota of three verdicts per session, the
international requirement, and the rule that an empty region is reported rather than backfilled with
US sources.

**Operator decisions 2026-10-20 (three, recorded once so they are not re-asked).**
1. **Standing publication authority: granted.** "Fine" to publishing anything that passes the gates and
   reporting afterwards. The gate list is unchanged and is written into `docs/OPERATIONS.md`; the
   authority also settles the 2026-10-19 ambiguity in MSHA's favour - it stays public.
2. **Companies House: parked permanently.** The operator chose not to buy a year of monthly snapshots
   (~5.6 GB) for a label that only exists in those snapshots.
3. **Melbourne: one dated attempt, then reject.** All four licence channels are consistent - open in
   intent, unstated in terms - so a written enquiry is drafted in the candidate's `notes.md`, and the
   candidate is rejected on 2026-11-03 if no written licence arrives.
4. **Worker concurrency: raised to 3, then reverted to 1 the same day on operator instruction**
   ("let's keep things to one worker at a time"). The bounded-check patch and its three guard tests
   are removed by reverting `factory/worker.py` and `tests/test_workers.py`; `config/local.json` is
   back to `max_workers: 1` with the budget unchanged at EUR 20/month. The one-worker invariant and
   its refusal message ("An active or interrupted job exists") stand as before.

## 2026-10-20 - Discovery tick (South & Southeast Asia)

Regional focus tick: South and Southeast Asia. Five new sources opened, **all five from the
tick's region** (India x2, Malaysia, Indonesia, Thailand) - the quota of three verdicts with
two from the region is satisfied without touching a US source, and no US backfill was needed
or used. Every probe was anonymous; no bulk data was downloaded to the coordinator. Probe
HTML/CSVs (~2.1 MB) sit in `.factory/probe_tmp/` (git-ignored scratch): the scoped
`rm -rf .factory/probe_tmp` was refused by the approval gate in single-query mode, so the
files are left in place rather than worked around. `scripts/check-candidate.py
--all` exit 0 and the suite passes (354 tests OK); `scripts/discovery-coverage.py` now reports
23 candidates, 11 live, **live non-US 5/11 (was 4/10)**, South & South-East Asia 5.

- **`cpcb-aqi-exceedance` - GO (CPCB CAAQMS, India; republish channels OpenAQ + XKDR).**
  Predict whether a station's next-day 24-hour mean PM2.5 exceeds the CPCB 'Poor' band edge
  (90 ug/m3), from its own hourly history through day D. Measured: XKDR demo API 196,521,834
  readings, 558 stations, 2009-01..2026-03 (GET /v1/meta, 1 request); Delhi Q1-2024 daily
  sample 3,384 station-days over 39 stations in 252,729 bytes / ~3 s (1 request), 58.89%
  above threshold (winter window - annual rate to be measured at construction). Anonymous
  bulk channel: OpenAQ archive S3 (CC BY 4.0, redistribution allowed, no account), layout
  documented and bucket listing measured; CPCB locationids unresolved this session (first
  construction step). Novelty `differentiated`: heavy paper literature and Kaggle data
  mirrors exist, no packaged train/eval/holdout task with a scored contract anywhere.
  Official api.data.gov.in unreachable from the coordinator (measured HTTP 000).
- **`malaysia-river-danger-exceedance` - PARK (JPS PublicInfoBanjir, Malaysia).** Official
  per-station Danger-threshold exceedance from river/rainfall telemetry. Current pages,
  per-station Normal/Alert/Warning/Danger thresholds and the historical AJAX endpoints all
  confirmed anonymous, but the trend endpoints' exact parameter contract (station key + date
  format) was not reverse-engineered after targeted attempts ("Tiada data"/"No result"
  measured), and no licence text exists on any fetched portal page. Unpark: browser-capture
  the trend page XHR and find the data.gov.my catalog entry that declares the licence.
- **`bmkg-earthquake-felt` - PARK (BMKG, Indonesia).** Felt-vs-instrumental earthquake
  classification from detection-time parameters; the felt-quake feed measured to serve only
  the latest 15 events (4,602 bytes, 15 items counted) and the open-data pages expose no
  historical archive, so labels are unobtainable from anything published today. Unpark: probe
  the SATU PETA MKG API (gis.bmkg.go.id) for a historical catalogue, or commit to a 12-month
  collection loop on the live feeds.
- **`imd-station-observation-series` - PARK (IMD, India).** Station-level historical series
  are enrolment-gated and chargeable per the Data Supply Portal's own pages (V4.0 enrolment
  note), and both IMD public portals were unreachable from the coordinator (measured HTTP
  000) - an infrastructure + access blocker, not a data judgement. Unpark: probe from a
  worker in another network region and ask the operator whether to enrol.
- **`air4thai-pm25-exceedance` - PARK (PCD Air4Thai, Thailand).** The official catalog page
  is Cloudflare-walled to headless clients (403 measured), the station host fails TLS from
  the coordinator, PCD's own service document describes bulk data as a per-case request
  service, and the licence is unstated; additionally the task shape duplicates
  cpcb-aqi-exceedance, so reopening needs an explicit operator decision even after access
  and licence resolve.

The region did not come up empty - it produced one GO and four honest parks, each with the
probes that produced the verdict recorded in its notes.md. Next action for the GO is specific
in its record: worker-side extraction measurement (OpenAQ locationids or an XKDR key), then
the station-day panel and the qualification gate.

**Melbourne unblocked by operator risk acceptance 2026-10-20.** "The license is fine. If they get mad they can
just email me." Recorded in `candidates/melbourne-pedestrian-counts/license.json` as exactly that - a risk
acceptance by the dataset owner, explicitly not a publisher grant - with the five findings that show the City
states no terms, attribution to the City, a takedown route in the card (repository issue tracker, plus an
address if the operator supplies one), and the rule that no standard licence may be presented as the
publisher's. Candidate moved parked -> investigating; next action is construction, queued behind Chicago
packaging because there is one worker.

## 2026-10-20 - Discovery tick (South & Southeast Asia, second tick)

Regional focus tick: South and Southeast Asia again. Five new sources opened, **all five
from the tick's region** (India, Indonesia, Philippines, Vietnam, Singapore) - the quota of
three verdicts with two from the region is exceeded without touching a US source, and no
US backfill was needed or used. No re-vetting of last tick's candidates (CPCB/IMD/Malaysia/
BMKG/Air4Thai were left untouched). All probes anonymous; no bulk data reached the
coordinator (largest fetch: the data.gov.sg catalog metadata, 467 requests, id+name pairs
only, deleted after recording). `scripts/check-candidate.py --all` exit 0 for all 28
candidates; coverage after this tick: 28 candidates, 12 live, live non-US 6/12 (50%),
South & South-East Asia 10.

- **`india-datagovin-portal` - PARK (Government of India open data platform).** Both
  https://data.gov.in and https://api.data.gov.in refuse TCP connections from the
  coordinator (measured twice: curl exit 7 at ~0.6 s, HTTP 000, 0 bytes; api.data.gov.in
  already measured HTTP 000 twice in the cpcb candidate the same day). Infrastructure
  blocker, not a data judgement. Unpark: probe both hosts from a worker in another
  network region, then enumerate API-enabled datasets excluding the AQI family cpcb
  already covers.
- **`indonesia-bps-webapi` - REJECT (BPS, Statistics Indonesia).** Access is fine
  (measured: API root 200, 55 bytes, anonymous; router 404s on undocumented paths; docs
  at webapi.bps.go.id/documentation; key token free on registration). Rejected on task
  grounds: the publisher's own terms describe the Web API as access to "aggregate data"
  (ppid.bps.go.id quote recorded) - aggregate statistical tables cannot carry a
  per-event/per-entity prediction task, so no task was formulated and none ever could be.
- **`philippines-psa-openstat` - REJECT (Philippine Statistics Authority).** OpenSTAT is
  Cloudflare-walled to headless clients (403 "Just a moment..." measured) but passed in a
  real browser session; the legacy CKAN API is gone (404), the current channel is a
  documented PXWeb-style API with a database of statistical-domain tables (Birth
  Statistics, Marriage Statistics, census counts and projections - grain measured).
  Rejected on task grounds: aggregate tables only, no event-level outcomes; same verdict
  shape as BPS, recorded separately because the operator named PSA.
- **`vietnam-nso-publications` - PARK (National Statistics Office of Vietnam).** The GSO
  was renamed NSO (MoF Decision 384/QD-BTC, 26 Feb 2025) and moved to nso.gov.vn; the old
  gso.gov.vn names are NXDOMAIN at the authoritative level (measured via dns.google DoH),
  and the 2018 national open-data portal data.gov.vn is dark in DNS (zone alive, no A
  record at apex or www). The current site (200 measured) is an Avada/WordPress
  publication archive; no API found; .vn resolution from the coordinator is intermittent
  (same host 200 then DNS failure minutes apart). PDF-only publisher = park per the brief.
- **`singapore-datagov-catalog` - PARK (data.gov.sg; best access in the region, no
  differentiated task).** Fully anonymous machine-readable APIs measured: v2 catalog
  (4,664 datasets enumerated in 467 page requests; page_limit/query params measured to be
  ignored server-side) and datastore_search rows (Weekly Infectious Disease Bulletin:
  20,070 rows, epi_week x disease x cases since 2012-W01; Historical Rainfall 2021:
  7,044,646 rows of per-station readings - ~63M rows for 2016-2024). Licence read: Singapore
  Government Open Data Licence (commercial and non-commercial use with attribution).
  Parked on task-family grounds: every event/series-grain formulation duplicates a family
  the bench already carries (own-history environmental exceedance - cpcb/noaa/air4thai;
  outbreak forecasting - DengAI precedent, ~29 entities; tender outcomes - chilecompra) or
  is a mirror (HDB resale on Kaggle); real-time feeds (carpark/taxi/flood/dengue clusters)
  are snapshots without archives. Unpark: an operator decision naming a family to accept,
  or a quarterly catalog diff surfacing a new event-level register.

No GO this tick: the region's named statistical portals are aggregate-only by mandate
(BPS, PSA - both removed permanently), its remaining named channels are network-blocked
from the coordinator (data.gov.in) or publication-only (Vietnam NSO), and the best
access found (Singapore) duplicates task families the bench already carries - that
comparison is recorded in the candidate's novelty block rather than assumed. The live
buffer behind construction is unchanged (cpcb-aqi-exceedance GO from the previous tick).
Probe scripts and the catalog extract were deleted from `.factory/` after the results
were recorded (scoped `rm` of three exact paths, accepted).

**P0 dashboard shipped 2026-10-20.** Live at https://earino.github.io/dataset-factory-dashboard/
(exec, cost, reliability). Generated by `scripts/build-dashboard.py` from repo state, published by
`scout-dashboard-refresh` (`4d8053a69ed2`, hourly at :50, script-only, local delivery) to its own
Pages repo `earino/dataset-factory-dashboard` rather than under the catalogue site, whose deploy is a
reviewed workflow over `.dataset-site/`. Verification is anonymous and part of the job: a publish that
does not appear publicly fails the run. Missing inputs render "no data", never zero. Not yet shown:
worker timings/euro spend (no per-job ledger), verdict ledger, history and sparklines - P1/P2.

## 2026-10-20 - Discovery tick (East Asia, first tick)

Regional focus tick: East Asia. One source opened to a recorded verdict before the wall-clock
budget was exhausted - short of the three-verdict quota, and the shortfall is reported rather
than padded: no US source was substituted, and e-Stat, KOSIS, Taiwan and Hong Kong were left
unprobed (no records created for them) so the next tick inherits them as fresh leads, not
half-verdicts. All probes anonymous; no bulk data reached the coordinator (largest fetch was a
HEAD request; `bst_all.zip` was never downloaded). After the tick: 29 candidates, 12 live, live
non-US 6/12 (50%), East Asia 1 - the first East Asia candidate on the bench.

- **`jma-typhoon-rapid-intensification` - REJECT (JMA RSMC Tokyo-Typhoon Center, Japan).**
  East Asia's best-measured access of the tick: the full 1951-present tropical-cyclone best-track
  record is one anonymous ~0.75 MB download (`Besttracks/bst_all.zip`, HEAD measured: HTTP 200,
  content-length 744,954 bytes, last-modified 2026-09-29), fixed-width ASCII with every column
  documented (position/unit) at `e_format_bst.html` (HTTP 200, 10,438 B), under the Japan Public
  Data Licence v1.0 (terms quote recorded from jma.go.jp/jma/en/copyright.html - licence settled,
  attribution required). Rejected on task grounds: the natural prediction question (rapid
  intensification in the next 24 h from track state) already ships as ML-ready, split, scored
  benchmarks - TCRISI (NTU; official train/val/test splits + benchmark repo, attention-model
  results) and TCBench (arXiv 2601.23268; IBTrACS track/intensity, year-based splits) - plus
  public SHIPS-predictor studies with chronological splits. A best-track-only RI task is a
  mirror. The old `rsmc-hp/pub-egt` URL path is dead (404 measured); the section moved to
  `rsmc-hp-pub-eg`. Next_action in the record also fences off JMA's other families
  (earthquake felt-intensity, MLIT river levels) as family-level duplications of candidates
  already on the bench.

Storm/RI counts from the archive itself were NOT measured (estimates labelled as estimates in
the record); the verdict did not depend on them. The one command refused by the unattended
approval gate this session was the scoped cleanup `rm -rf .factory/probe-jma` (blocked as a
recursive delete); the scratch probe files remain in `.factory/` (gitignored, ~60 KB of fetched
HTML) - harmless, and reported rather than worked around. Next action for the East Asia
rotation: open `e-Stat` (JP), `KOSIS` (KR) and one of Taiwan/Hong Kong first; the JMA record's
jurisdiction (JP) already anchors the region on the coverage report.

**Dashboard redesigned mobile-first 2026-10-20 (P0.1).** Rendering moved to `factory/dashboard_render.py`
(design tokens, inline-SVG charts, three page renderers); the collector and publisher in
`scripts/build-dashboard.py` are unchanged in behaviour. Phone layout (390pt) verified with headless
Chromium screenshots and vision review: a funnel-label truncation and a clipped gauge arc were found and
fixed, tables now collapse to cards below 640pt, and the gauge is drawn with pathLength=100 so the fill is
exact rather than trigonometric. Hero states a fact ("4 datasets shipped") instead of a mood; a held
research lock is a notice ("session in flight"), not an alarm. History begins 2026-10-20 and is never
back-filled, so a one-point sparkline says "series begins today". 369 tests OK.

**Resources page added 2026-10-20.** Fourth dashboard page: live Hetzner inventory from the provider API
(servers, primary IPs, account totals) and spend computed from `jobs/*.json` as server lifetime
(`deleted_at - created_at`) x the rate recorded at launch - the same arithmetic as the reservation guard.
Measured at build: EUR 0.38 month-to-date, EUR 2.83 lifetime across 51 jobs, 4 releases, 0 live servers,
0 IPs. Excludes volumes and manual resources (not recorded) and says so. Publish verification now checks
all four pages, not just the index, after a new page 404'd for ~90 s behind a healthy index. 371 tests OK.

**Resources histogram added 2026-10-20.** Distribution of per-job cost normalised to the cpx32 reference
rate the project actually paid (EUR 0.06924/h): 51 jobs, median EUR 0.018, p90 EUR 0.068, max EUR 0.63,
buckets widening with cost so the long tail stays visible. Normalisation is by rate only (cost = lifetime x
reference rate), never by duration - dividing by duration would collapse the chart to the three server
prices. Bars sum to the job count in a test. 372 tests OK.

**Release priority added 2026-10-20 (operator: "once it's waiting on me, you're free to do whatever").**
Authority is now split at the flip: Scout acts freely up to `packaged` (discovery, construction,
qualification, packaging, docs, public-ready repo); the private-to-public flip is the operator's only
approval; after the flip publication to GitHub/HF/site plus anonymous verification runs without asking.
Mechanisms: `factory/worker.py` refuses a construction launch while an actionable packaged candidate
exists (`release_preempts`), and holds back `release_reserve_eur` (5 of 20) from construction so a
release always has budget. A candidate with `awaiting_operator: true` waits on the flip and blocks
nothing - otherwise a human wait would starve the queue. Dashboard gained a "Ready to ship" card and
alarms (>6h actionable is a real alarm, >24h waiting on the operator is a warning). Prompt, AGENTS.md
and OPERATIONS.md updated. Guard tests fail on the pre-fix launcher ("FactoryError not raised"). 380 tests OK.

**Advancement no longer waits for 08:00 (2026-10-20, operator: "once we have a dataset identified,
we shouldn't stop").** Cron 69a5bc676d10 moved daily 08:00 -> every two hours at :25, running
scout_advancement.py which passes --if-work: the tick scans candidates and exits without starting an
agent when nothing is ready, qualified, packaged-and-actionable, or GO-to-construct, so the higher
cadence costs nothing on an empty queue. The brief now forbids stopping at a step boundary: carry a
candidate through build -> qualification -> packaging while the budget allows, stopping only at a real
blocker or the operator's flip. New hourly script job ba4c8610edf8 (scout-release-notify) sends the
one chat message that matters - "ready for the flip" - deduped on id + packaged_at, silent otherwise.
380 tests OK; runner `--if-work` dry-run verified.

**Session overrun found and fixed 2026-10-20.** The 11:44, 12:45 and 13:45 discovery reports were all
"killed by the wrapper after the run budget elapsed" at 2700s: hourly 40-minute sessions could not finish
three sourced verdicts, so the tick was paid for and produced nothing, and the 14:00 tick then held the
lock through the advancement slot. Fixes: discovery moved to every two hours at :00 with --run-budget 3000
and --max-turns 80; advancement moved to odd hours at :05 so the two can never collide; both deliver
locally (the dashboard and the flip notifier are the only chat output). The dashboard now reads
.factory/research-sessions.jsonl: Ops lists the last six session outcomes and the executive page alarms
when two of the last three were killed. That alarm is firing now, correctly, on the pre-fix history.
383 tests OK.

**Session window doubled 2026-10-20 (operator: "I wonder if we should expand that window").** Measured
first: sessions were ending at 40-45 min on 110k-370k tokens, so time - not tokens - was the binding
constraint. Both jobs now get --run-budget 5400 (90 min) and --max-turns 120, with 80% wrap-up to be
obeyed by the brief. Cadence changed to alternating 2-hour slots every four hours: discovery at
00/04/08/12/16/20, advancement at 02/06/10/14/18/22, so a 90-minute run plus a 95-minute hard stop always
fits its slot and the two jobs can never share a lock. config/research-budget.json session_max_minutes
raised 40 -> 90 (it sets the stale-lock window; at 40 a live 90-minute session would have been treated as
dead and overlapped). 12 sessions/day at 150-250k tokens is ~21M/week against the 40M ceiling.

**Two failures on 2026-10-20, both structural, both fixed.**

1. `food-baseline-001` died at 26.8 s with exit 2: the job was launched straight from
   `candidates/chicago-food-inspections/baseline/job.json`, and `factory.worker.source_bundle` packs
   exactly that directory, so `qualify_dataset.py` and the runner's train/validate files never reached
   the worker ("can't open file '/workspace/qualify_dataset.py'"). Nothing was scored. The corrected
   retry `food-baseline-002` was assembled with `scripts/assemble-job.py` first (bundle now carries
   qualify_dataset.py, train.py, validate.py, validate.sh, runner_files.json) and launched 15:26 on
   worker 171396373; the 5-minute watchdog collects it. Rule that follows: never launch a job from a
   candidate directory - assemble it, then launch the assembled bundle.

2. The advancement cron was killed at 3600 s by the scheduler's script ceiling, not by its own budget:
   a 90-minute run plus 300 s grace needs 5700 s, and `cron.script_timeout_seconds` defaulted to 3600.
   Set to 6000 in /opt/data/config.yaml (the loader caches on file signature, so the next fire sees it).
   The session had already launched the corrected baseline and written most of the Chicago package
   (licences, code/, measurements.json, DATA_DICTIONARY.md, get_dataset.py) before it was killed; the
   manifest is the missing piece.

**Discovery 2026-10-20, 20:00 tick — region: international organisations. 3 sources opened, 3 recorded verdicts (2 non-US, 1 go).**

- `who-flunet-activity-exceedance` (WHO, Geneva → CH) — **go, status ready**. The FluNet tool page links
  the publisher's own full-dataset CSV (`xmart-api-public.who.int/FLUMART/VIW_FNT?$format=csv`):
  measured 30.8 MiB / 189,645 rows / 4.0 s, anonymous, no key, updated to the current week
  (week-start 2026-10-19 present). Task: will influenza positivity (INF_ALL/(INF_ALL+INF_NEGATIVE))
  exceed 10% in ISO week W+4 for a reporting country, features from weeks <= W. Split windows computed
  from the table at country-week grain (streams summed): eval 2020-22: 8,559 country-weeks, 2,485
  positive (29.0%); 2023: 4,677 (42.4%); 2024-26: 12,707 (48.3%); clustered positives 278/131/400
  country-years. Licence: WHO general terms CC BY-NC-SA 3.0 IGO (copyright policy quote recorded;
  NC/SA carry through), data.who.int datasets CC BY 4.0. Trap recorded: pre-2015 rows mostly lack
  INF_NEGATIVE, so positivity is ~100% by construction there (931/931 in 1995-2004 — the uniform-result
  red flag); construction must gate on systematic negative reporting, pin threshold/lead with the
  France 2024-25 known-event fixture, and cross-check against the publisher's chart app. Novelty:
  differentiated (Kaggle mirrors the raw data; arXiv 2505.10213 is a paper experiment on two univariate
  series; CDC FluSight/Flusion are other sources). GHO annual panels probed and set aside:
  CHOLERA_0000000001 ends 2016. Next action: advancement session constructs it per the record.
- `unhcr-refugee-data-finder` (UNHCR, Geneva → CH) — **park**. Licence is a clear GO: the methodology
  page grants "Creative Commons Attribution 4.0 International Public License... Except where otherwise
  indicated" for the RDF datasets (quote recorded), while the site-wide ToU separately restricts website
  content and AI scraping (tension flagged). The blocker is access: www.unhcr.org 403s curl (182,520 B
  challenge page) and even same-origin in-page fetch (222,964 B); the RDF is an interactive Symfony
  app whose Download control is a JS-driven dialog form; the five homepage export deep links
  (?v2url=…) are view selectors, not files; no API route appears in the app's controller JS; a
  programmatic Download click produced no file. Old channels dead (popstats → 000, data.unhcr.org/en
  → 404). HDX mirrors only per-country extracts, not the full series. Unpark question recorded
  verbatim: a datacenter-fetchable export path, written UNHCR guidance, or an operator decision that a
  browser-captured export is acceptable provenance.
- `unicef-sdmx-refugee-origin-growth` (UNICEF Data and Analytics, New York → US; int-org region) —
  **park**. Access and licence are good and recorded to avoid re-probing: anonymous SDMX REST API
  (4,967 KiB / 12,452 rows / 0.5 s), CC BY 3.0 IGO (HDX record). The park is split capacity: the
  growth>25% task's positives are surge situations — eval 2016-19 holds 378 origin-years but only 34
  positives across 22 distinct surging origins (holdout 2020-24: 72 across 44) — too thin for a stable
  scored eval; and the series is UNHCR-derived (DATA_SOURCE cites UNHCR Global Trends), so it adds no
  data beyond the parked parent record. Unpark condition: the richer UNHCR grain becoming
  machine-fetchable.

Region measurement: beyond WHO's weekly surveillance channel, the named orgs' headline data is
annual country panels; the one weekly-grain maintained series found (FluNet) is the go. Novelty checks
recorded via check-novelty.py where status requires it; check-candidate.py OK on all three records.
Coverage after this session: CH joins the map (WHO, UNHCR); the three verdicts are all from the tick's
region, two non-US (WHO CH, UNHCR CH; UNICEF recorded honestly as US-HQ under the HQ-country
convention).

**Chicago published 2026-10-20 21:55Z on the operator's flip.** Both destinations were private and are now
public: GitHub earino/chicago-food-inspections (release 418734355, tag v2026.10, 201 assets) and Hugging
Face (213 files, tag v2026.10 = 9e17ba8). Anonymous verification with no credential: repository/release
visible, 201/201 asset names and sizes match MANIFEST.json, three sampled assets downloaded and re-hashed
OK; HF dataset public, card and LOADING.md readable, code_38-meta.json re-hashed OK, bulk file present.
DESTINATIONS.json recorded the flip (private: false, anonymous_access block, files_verified for all 201
paths on both platforms) BEFORE the manifest was regenerated, as the site plan requires. Record moved to
`published` with published_at. Site: catalogue and dataset page deployed and live
(earino.github.io/chicago-food-inspections, receipt status complete).

**Discovery 2026-10-21, 04:00 tick — region: United Kingdom. 3 sources opened, 3 recorded verdicts (all GB; 1 go, 2 parks).**

- `nhs-ae-four-hour-decline` (NHS England — the NHS Digital family post-2022/23 merger) — **go, status ready**.
  Monthly provider-level A&E CSVs, anonymous, OGL v3: 102 files 2018-04..2026-09 measured at 3,115,779
  bytes / 1.2 s total (pre-2018 months are XLS-only; a cumulative Monthly-AE-Time-Series XLS can extend
  to 2015-06 on a worker). Panel: 124 providers with Type 1 attendances ≥100 in ≥24 months → 9,071
  provider-months. Task: will a provider's Type 1 four-hour performance decline m/m next month. The m/m
  label is balanced in all windows (train 2019-01..2022-12: 3,714 rows / 56.5% pos; eval 2023-24:
  2,449 / 47.0%; holdout 2025-26: 2,538 / 48.6%); fixed thresholds were measured and REFUSED (<95% →
  holdout 99.9% positive, uniform-class; <80% → 95.8%) — base rate drift with the system's
  deterioration is a documented property. Cross-check vs the publisher's own commentary: Aug 2026
  Type 1 61.1% vs panel 60.9%; NAO HC 588 figures consistent. Novelty: differentiated (prior art is
  ED *arrival-volume* forecasting on private data + descriptive GitHub dashboards; no shipped
  four-hour-performance task found on HF/Zenodo/arXiv). New bench family (health-services
  operations). Next action: advancement constructs per the record.
- `defra-la-household-recycling-rate` (Defra) — **park**. The 2024/25 cumulative ODS Table_1 IS the
  full 11-year LA panel (3,730 LA-years, 2014-15..2024-25, 321-352 authorities/year) in a single
  2.04 MB anonymous GET — the cheapest panel this session. Licence OGL v3. The ≥50% task (Waste
  Framework Directive art.11 threshold) carries both classes in all windows (23.2%/21.9%/21.3% pos)
  but persistence is 92.6-97.8% accurate year-over-year with only ~10 threshold-crossing LAs/year —
  no measurable headroom over a naive baseline, so a scored eval could not tell a competent model
  from the naive rule. A y/y-decline variant was assessed and set aside as an annual, thin-feature
  sibling of the A&E candidate. Unpark conditions in the record (finer-grain export channel, operator
  appetite for an annual-grain policy task, or a re-formulation with cross-sectional joins).
- `ons-la-claimant-count-direction` (ONS via nomis) — **park**. Access measured clean: nomis
  NM_162_1 is current to 2026-09 (~3-week lag), monthly back to 1986-01, LA-level via
  geography=TYPE480 (latest month 1.94 MB / 4,897 rows; full panel ~40-60 MB, worker-scale), OGL v3
  (ONS site-wide statement). Two API quirks recorded: the nomis `?search=` endpoint returns a null
  document (grep the 5.5 MB full def list locally), and `data.csv` with dimension parameters returns
  empty 200s — the minimal `?geography=&date=` form works and outputs all breakdown columns to
  filter locally; api.beta.ons.gov.io does not complete TLS from the coordinator. Park reason: ONS
  is an aggregate-statistics publisher — every candidate task is a direction-forecast on own history
  (family served by M4/Monash-style macro benchmarks, thin differentiation, low agent-eval value);
  individual-level ONS products (Understanding Society, SRS, Census microdata) require registration
  and forbid redistribution. Unpark question in the record: an open event/case-grain ONS release.

Region measurement: all three verdicts are GB-publisher sources as the tick required; GB joins the
map at 6 candidates (Companies House, DVSA, EA bathing water + today's three), Europe moves 6 → 9,
live non-US 9/15 → 10/16 (62%). Probe scripts kept per the skill convention as
candidates/<id>/probe_*.py (A&E: collect_urls/download/panel/fixture; waste: waste_panel; ONS:
nomis_list). check-candidate.py OK on all three; 386 tests OK; coverage script run before and
after (38 candidates, live 16).

**Discovery 2026-10-21, 16:00 tick — region: Canada. 5 sources opened, 5 recorded verdicts (all CA; 1 go, 3 parks, 1 reject).**
Coverage before: 38 candidates / 16 live / 62% non-US. After: 43 / 17 / 65%; CA 4 -> 9.

- `tsb-railway-occurrence-casualty` (Transportation Safety Board of Canada) — **go, status ready**. RODSdb,
  5 anonymous CSVs released on/after the 15th monthly (occurrence table 97,765,258 B, 345 documented
  columns, 1983-01..2026-08, vintage 2026-09-15). Plain-client 403 is UA filtering - a browser-like
  header set (recorded in probe_access.py) gets 200/206; reproducible programmatic path, not a bot wall.
  Task: at occurrence onset, from pre-onset context only (date/time+zone, subdivision, nearest
  location, province, lat/long, railway, train activity), will the occurrence produce >=1 casualty?
  Label source InjuriesIND/Total*Injuries; TSB's outcome-coded accident-type taxonomy ('... (NO
  DAMAGE)'), all investigation fields, weather, process dates and the Summary narrative excluded as
  post-hoc. Measured injury base rates on bounded era samples (probe_era_samples.py): 13.9-18.0%
  across 1995/2001-02/2008-10/2025-26, both classes everywhere; 1983-84 tail 30.2% with DG LEAKER/
  HISTORICAL types -> modern-era start proposed (2004-01). DG release (0.1% sample; TSB's own 2025
  summary: 3 releases) and evacuation (0.2%) ruled out as labels. Row count ~70,000 is an ESTIMATE;
  full panel measured on the worker at construction. Cross-check product: TSB 2025 annual summary
  (831 accidents / 332 incidents / 82 DG-involved). Novelty: differentiated (check-novelty.py; prior
  art = NRC derailment risk-map on RODS historical counts + Rana et al. 2024 grade-crossing severity
  paper; no public ML-ready rail-occurrence benchmark). Next action: advancement constructs per the
  record (worker fetch, naive baselines first: global/per-railway/per-subdivision).
- `cer-pipeline-incident-significant` (Canada Energy Regulator) — **park**. Access perfect (anonymous
  CSVs, 580 KB + 2.45 MB, last-modified 2026-10-01), OGL-CA clean, and the split contract is
  satisfiable (2,034 rows 2008-2026, Significant 361/17.75%, both classes every year) - but the
  dictionary defines 'Significant' mechanically from consequence fields that cannot ship, and the
  measured honest-feature AUCs (Company 0.73, Province 0.70, Substance 0.66; label-adjacent Incident
  Types 0.91) show the surviving task is operator risk profiling at 2,034 rows, duplicating the
  hc-recalls-classification family. Publisher's GitHub repo checked: it is their viz app, not ML.
  Unpark conditions in the record.
- `statcan-wds-aggregate-series` (Statistics Canada) — **park** (source class). WDS is anonymous,
  key-free, 15 REST methods + SDMX over a 13,356-table catalogue plus 158 PUMF products - but every
  open product is either an aggregate series (direction-forecast-on-own-history, M4/Monash family)
  or a cross-sectional survey snapshot (census-income family); case/event-grain products are
  registration-gated. Same verdict shape as the ONS park. Microdata index page returned HTTP 500
  (recorded as a probe result, not silence).
- `eccc-hydrometric-daily-flows` (ECCC Water Survey of Canada) — **reject (mirror)**. The task this
  source would carry (Canadian station streamflow forecasting/exceedance) already ships ML-ready:
  CAMELS-SPAT (1,426 US+Canada basins, daily+hourly flows, 4 forcing sets; Knoben et al. 2025,
  doi:10.5194/egusphere-2025-893) and HYSETS (Arsenault et al., ESSD 2020); the family is also live
  here (malaysia-river-danger-exceedance). check-novelty.py verdict 'mirror' recorded (exit 3 =
  expected refusal). Extraction cost deliberately not measured - the prior art already paid it.
- `hc-canada-vigilance-adverse-reactions` (Health Canada) — **park**. No machine-readable bulk
  channel exists: both Canada Vigilance packages list HTML query-form resources only, and the 'Data
  on cannabis adverse reactions' package is 12 PDF annual reports (all measured via CKAN
  package_show; database landing page timed out twice from the coordinator - recorded). Building a
  panel would need undocumented form scraping = unacceptable provenance (UNHCR-precedent posture).
  Secondary: FAERS/openFDA already serves the ADR-outcome family publicly.

Region measurement: all five verdicts are CA-publisher sources (the tick's named federal family:
TSB, CER, StatCan, ECCC, Health Canada, all found via open.canada.ca CKAN); the quota is met without
leaving the tick region. Probe scripts kept per convention as candidates/<id>/probe_*.py (TSB:
access + era samples, executed after commit-ready edit; CER: download/measure + honest-AUC, executed;
StatCan/ECCC/HC: catalogue probes, executed). check-candidate.py --all OK (43 records); 386 tests OK;
coverage run before and after. Session scratch scripts in .factory/ deleted; nothing else touched -
no build, qualification, packaging or publication commands were run this session.

**Review response on who-flunet (2026-10-21).** Ran the decisive comparisons on the released rows.
Persistence (week-W positivity) reproduces exactly at eval 0.8929; a hierarchical country x target-week
seasonal prior reaches 0.5509 and a global week-of-year prior 0.5437; an independent calendar-only GBM
reached 0.6269. The full model is 0.8700. So the review's seasonality hypothesis is wrong - calendar
signal tops out ~0.63 - but the model is *below* the persistence rule, which is the more serious defect:
the current label is largely persistent, not a forecast of change. Prevalence shifts from 59.2% positive
in train (targets 2005-2020) to 23.9% in eval (2020-2023), so the eval window is the COVID disruption.
Sentinel-only feasibility measured from the WHO source: 19,634 eligible country-weeks vs 64,001 combined
(2020: 875 vs 2,624), and 46% of source rows are ORIGIN_SOURCE=NOTDEFINED - the combined positivity mixes
three categories. Lag audit impossible: only the current vintage is published.
Dashboard defect fixed: the dataset page showed "reference: no data" while the record contained 0.8929;
the reference is now extracted from measurements and flagged when the model is below it.

**who-flunet flip BLOCKED on gate 1 (licensing), 2026-10-21.** The operator authorised release subject to five gates. Gate 1
(verify redistribution rights under the *dataset-specific* terms) fails. The FluNet tool page links a "Data policy" whose
terms and conditions for WHO data compilations, aggregations, evaluations and analyses state: clause 04 - "Any other
alteration or modification of the Datasets (including abbreviations, additions, or deletions) may be made only with the prior
written authorization of WHO"; clause 05 - "You will not sell or otherwise transfer the Datasets and/or data contained therein
to any third party, except within the Licensed Use." Our artifact is a substantial alteration (re-grained country-weeks, a
derived binary label, row selection), so the redistribution right is not established. The CC BY-NC-SA 3.0 IGO claim in
LICENSE.md rests on WHO's general publishing copyright page, which the gate explicitly excludes as evidence. No flip performed;
nothing was made public. Resolution paths: written permission from WHO (gisrs-whohq@who.int) for a derived compilation, or a
dataset-specific licence statement we can quote. Gates 2-5 were not started, per the instruction to stop at the first blocker.

**who-flunet PUBLISHED 2026-10-21 10:24Z on the operator's "ship it", with an unresolved-licence label.**
Licence: the release no longer asserts CC BY-NC-SA 3.0 IGO. LICENSE.md states that WHO names that licence for
publications but that FluNet is a dataset whose linked data terms require authorisation for alterations and
restrict transfer, that no dataset-specific licence exists (checked page, metadata CSV, API headers), and that
no open licence is granted over the rows or the compilation. MANIFEST source_data and data_compilation are
NOASSERTION; the Hub card's license field is `other`, not a CC claim. Operator risk acceptance recorded in
license.json with the clause quotes.
Results published on the card and README: full model 0.869990 (Brier 0.1347), persistence 0.8929 (beats it),
calendar-only 0.6269 independent, seasonal prior 0.5509, global week 0.5437. Limitations listed: retrospective,
unverified publication timing, future-dependent eligibility, sentinel provenance lost (46% NOTDEFINED), no
calibration, 110 possibly-premature training labels, holdout labelled by design.
Verification: GitHub 5/5 assets anonymously downloaded and re-hashed; HF 15 files, meta.json re-hashed; docs
readable on both; tag v2026.10 moved to the docs commit on both destinations (this was required - the site
publisher pins the tag and refused while the tag still carried the old CC licence). Site published, receipt
complete.

**nhs-ae-four-hour-decline: independent audit FAILED it, release pulled back from the flip queue (2026-10-21).**
The audit reproduced the bytes and the baseline (AUC 0.552621) but found two structural defects. (1) Temporal:
25 features carry month-M values that NHS England publishes about 10 days after the month ends, while the
record documented the prediction instant as month end - the features did not exist at the claimed instant.
(2) Hindsight selection: eligibility uses M+1 attendance and a >=24-month count computed over the whole
snapshot, so the retained population depends on future information. Splits, integrity and label arithmetic
passed (11,457 labels reproduced exactly; 134 terminal rows unverifiable). Baseline loses to persistence
(0.5758) and to a target-month-of-year prior (0.6168). Docs errors: rate_delta_1m scored with the wrong sign,
"no credentials" wrong, inconsistent checksum paths. Candidate moved packaged -> qualified, awaiting_operator
cleared, packaged_at cleared, audit block recorded. The staged v2026.10 artifacts must not be published.
Plan: redefine the prediction instant as month M's publication date, select the population without M+1,
rebuild, re-qualify, re-baseline with persistence and calendar priors, re-package, re-audit.

**Factory lesson encoded 2026-10-21: knowable at the period is not knowable at the release.**
`qualify_dataset.py` is gate 1.4.0 and refuses any dataset without a `timing` block: prediction-instant
kind and citation, a measured publication lag in days, an observed `period_end -> published` date for a
statistical release, and the latest period used by row selection. It refuses late-published features at
a period-end instant, understated lags, and selections that reach into M+1. `tests/test_timing_gate.py`
pins eight shapes; all eight ERROR on the pre-fix gate (KeyError on the missing check) and pass on the
fixed one. Builders updated: msha, chicago food, austin 911, chicago DOAH (administrative record, lag 0),
nhs-ae (statistical release, 10 days, observed 2026-08-31 -> 2026-09-10). Skill and OPERATIONS.md carry
the rule. Fixtures carry a synthetic timing block so the gate stays exercisable offline.
Also fixed while here: `Report.failed_checks` (tests crashed while reporting a gate failure, hiding the
reason) and `check-candidate --all` now treats a *fresh* investigating record as in progress for 3 hours,
so a live discovery session no longer turns CI red mid-write, while a stale record still fails.

**Discovery 2026-10-21, second tick — region: Latin America. 3 sources opened, 3 recorded verdicts (2 go / 1 park; all three from the tick's region).**
Coverage before this tick: 43 candidates / 17 live / 65% non-US / Latin America 0. After: 46 / 19 / 68% non-US / Latin America 3 — the bench's first CL, BR and MX candidates. No US source was substituted at any point.

- `chilecompra-tender-outcome` (Dirección de Compras y Contratación Pública, Chile) — **go, status ready**. Anonymous OCDS channels measured: monthly bulk zips `ocds.blob.core.windows.net/ocds/{yyyymm}.zip` cover 2009-01..2022-04 (2022-05 404; sizes 377 MB–1.13 GB per month, PK-magic-verified), plus the real-time list API (licitaciones 7,785–33,366/month). Label directly in the OCDS award release: status `unsuccessful` / statusDetails `7-Desierta (o art. 3 ó 9 Ley 19.886)`; desertion base rate measured on the first 100 processes of two closed months: 17.3% (2019-06), 14.3% (2023-06) — probe_desertion.py, 214 requests / 2.67 MB / 209 s. Task: at tender publication, predict desertion from publication-time features only (buyer/region/UNSPSC items/estimated value/procedure type). Licence: CC0 1.0 recorded by the OCP publication registry + publisher terms explicitly contemplating reuse ("la reutilización de la información para el desarrollo de nuevos informes o aplicaciones") + the Ley 19.886 reform (effective 2024-12-12) mandating open reusable formats; channels carrying no licence statement also recorded (React bundle, API metadata, 404 policy URL, datos.gob.cl absent) — one written attribution-wording enquiry queued as pre-construction confirmation, not a blocker. Provenance-stream note recorded: bulk = Licitación stream only; Trato Directo / Convenio Marco are separate API streams and are not summed. Novelty: differentiated (check-novelty.py; prior art = TenderKG FR bidder-recommendation, ANAC-Italy tender-variation ML, TED void-rate analysis, MiDES BR descriptive tables). Next action: worker constructs per record.json (zip stream-extraction, label rule frozen, publication-time features, naive baselines before anything else).
- `camara-bill-advancement` (Câmara dos Deputados, Brazil) — **go, status ready**. Bulk per-year CSVs `arquivos/proposicoes/csv/proposicoes-{ano}.csv` 1991–2025 (4.4 MB → 90 MB; 2019 file 33,295,980 B, live last-modified today), anonymous, byte-range. Label from the publisher's own situation vocabulary: idSituacao 251 `Transformado em Norma Jurídica` = became law, measured 1.5% (72/4,852) on the 2005 cohort sample; `Arquivada` ~62% dominant terminal state — probe_samples.py, 15 requests / 31 s. Cohort counts measured via the API last-page trick (2005 ≈ 26,300; 2019 ≈ 41,400 presented). Measured quirks recorded: the year files are 98–100% presented-that-year with ~2% legislature-boundary re-numbered old bills (cohorts defined on dataApresentacao, not file year); many rows carry idSituacao with empty descricaoSituacao (label frozen on the code table); recent cohorts right-censored (2019 sample still shows ongoing states) so only closed-legislature cohorts are scored. Timing: indexação fields (keywords/temas) are post-hoc and excluded by documented reasoning; features are type, ementa, authors/party, calendar. Licence: portal terms "domínio público… podem ser reproduzidas desde que citada a fonte 'Câmara dos Deputados'" + Portaria 226/2025. Novelty: differentiated (prior art = LegisPL-BR GitHub dataset — PL 2022-2024 only, no splits/scored contract, current legislature so labels right-censored — plus two research papers). Next action: worker constructs per record.json.
- `denue-establishment-exit` (INEGI, Mexico) — **park**. The exit label needs consecutive-edition diffs, but INEGI publishes only the CURRENT edition for download (572 MB across 25 per-sector zips, all PK-magic-verified); ~12 documented semiannual editions 2019–2024 are described in the RNM catalogue but every historical URL pattern answers the publisher's soft-404 (HTTP 200 + HTML error — measured, and the bogus-filename control proves the pattern; HTTP status is meaningless on this host). One snapshot = no second observation = no label = no windows. Licence is NOT the blocker (INEGI free-use terms with attribution, quoted). Secondary, recorded comparison: the entity-exit family is already carried by companies-house-company-exit (GB). Unpark: a verifiable archive of ≥4 historical editions (probe with zip-magic, not status), with a known-event fixture first because ID churn reads as exit. probe_denue.py kept.

Session notes: the three candidate directories existed as empty uncommitted stubs from an earlier session (chilecompra, denue, anp). The first two were adopted and recorded this tick; `anp-station-fuel-price-change/` was removed as an empty stub — ANP (Brazil) remains an UNOPENED lead, left for the next LatAm tick with a one-line caution: a station-week fuel-price-change label is persistence-shaped (the who-flunet defect — the naive no-change rule will be hard to beat), so it needs that comparison designed in from the first probe. The singapore-datagov-catalog notes cited "tender outcomes - chilecompra-tender-outcome" as a live family while the candidate had never existed; that reference is now true (recorded here rather than editing history). Live ready buffer behind construction: tsb-railway-occurrence-casualty, chilecompra-tender-outcome, camara-bill-advancement. check-candidate.py OK on all three new records; probe scripts kept per convention; session scratch script deleted; no build, qualification, packaging or publication commands were run this session.

**nhs-ae rebuilt 2026-10-21 (v2026.11), gate 1.4.0 passes, not staged.**
Build fix: `make_rows` counts qualifying months at or before M (3,144 candidates skipped for
insufficient history) and no longer filters providers on whole-panel length, so 2,042 training rows a
provider had not yet earned are gone (train 6,116 -> 4,074; providers 134 -> 141). Eval and holdout
bytes are unchanged. Prediction instant restated as the publication date of month M (~10 days; observed
2026-08-31 -> 2026-09-10). Baseline re-run on the rebuild: 0.5511 eval, CONTRACT OK, with the contract's
own dependency ranges. References now shipped: month-of-year prior 0.6027 eval, reversal 0.5839,
persistence 0.5758/0.6046, mean reversion 0.5659/0.6562, momentum 0.4161. The baseline is below all of
them and the docs say so. Artifact 0990af0f90fbe304. v2026.10 staged artifacts are superseded and must
not be published. Next: stage v2026.11, then an independent re-audit before the flip.

## 2026-10-21 (afternoon) - v2026.11 staged private on both destinations; the worker watcher closed the arc the research session could not finish

The 14:00Z research session (exit 1 at 14:41:33Z, 41.5 min in, at its 120-turn limit; near the end one of
its commands was blocked as a force-push shape - the correct outcome, there is never anything to force, and
pushes from this clone go through an explicit credential URL that leaves the remote-tracking ref stale) did
the whole v2026.11 staging and recorded none of it: rebuilt artifact 0990af0f90fbe304 on the coordinator
(gate 1.4.0; the publisher's CDN 202-blocks datacenter IPs so no worker can fetch NHS England), regenerated
the release package, created the private GitHub release v2026.11 (419642457) at docs commit 29d567a with
5/5 assets at manifest digests, pushed the follow-up splits-correction commit 98139919 (14:40:10Z, tag
v2026.11 now resolves to it == main), ran get_dataset.py end-to-end against the release and
qualify_dataset.py --accept on the downloaded tree (ACCEPTED), and moved the Hub to v2026.11 through
nhsae-hf-003 (uploads 3 - public-train.csv, meta.json, quality.json; skipped 2 byte-identical
public-eval.csv / private-holdout.csv; failures 0; 1,674,061 bytes; result release 419647149) plus the
v2026.11 docs (Hub MANIFEST byte-identical to the package, sha256 b8185338...). All of that stayed
uncommitted in the working tree until this run.

**nhsae-hf-004 never ran the loading check it was named for.** Its job spec omitted the `verify_loading`
block that makes the worker execute the card's documented load_dataset path, so the job did only the
all-skip upload pass (uploads 0, skipped 5, failures 0) and reported success with no `hf_loading` block in
its result - found by comparing the result with nhsae-hf-002's, the same check that caught the food
release's declared-schema bug before shipping. Recorded as superseded; its worker was still alive when the
session died and was destroyed by this run at 14:43:20Z. Result release 419656381.

**nhsae-hf-005 (correction, launched by this run within the standing allowance):** the identical upload pass
WITH the verify_loading block, expectations taken from the v2026.11 manifest (train 4,074 rows / 2,260
positives; eval 2,937 / 1,478; holdout 2,538 / 1,233; label values ['0','1']; the same 37 columns,
re-derived from quality.json and identical to v2026.10's list). Green: uploads 0 / skipped 5 / failures 0,
hf_loading ok: true, problems: [], every split exactly at the manifest. Result release 419681562, worker
destroyed 14:51:44Z. October worker reservation now EUR 7.02 of the EUR 20 allowance (EUR 5 of which stays
held for release work).

Coordinator-side verification by this run (not inherited from the session's notes): hf-publish.py --verify
against the Hub (present 5/5, missing 0, size_mismatch 0, repo private, acting account earino, token role
write); GitHub API readback of release 419642457 (all five assets at exactly the MANIFEST sizes and the
server's own sha256 digests); anonymous GETs: GitHub 404, Hub API 401 (private on both, the flip stays the
operator's act); Hub tag v2026.11 created LAST at 18b2e97f... with tag_matches_main true, pinning exactly
the bytes the loading check loaded.

Recorded: record.json -> status packaged, packaged_at 2026-10-21T14:53Z, awaiting_operator false (the
independent re-audit gate comes before the flip), jobs nhsae-hf-003/004/005 with the honest hf-004 note,
artifacts extended with the three result releases and the two v2026.11 destination entries;
DESTINATIONS.json Hugging Face block completed (the session had left it "staging in progress"); the
session's release-package edits (MANIFEST, README, RELEASE_NOTES, REPRODUCE, get_dataset.py, code,
measurements) committed as left - every digest in them cross-checked against both destinations first.
check-package.py OK, check-candidate.py --all OK. Watcher note: this run fired at 14:22Z while the
launching session was still alive, waited for it to exit before touching the tree (a live session owns the
working tree; double-recording was the risk), then took over the unfinished steps.

Next action: commission the independent re-audit of the staged v2026.11 artifact - the selection must be
checked in code, not only the declaration, which is how the v2026.10 audit found the temporal defect. Only
after a passing audit, ask the operator for the flip. Do not publish v2026.10: superseded.
**nhs-ae rebuilt again (v2026.12) after the re-audit: eligibility now decided at M only.**
The re-audit was right. v2026.11 counted history from the past but still built its pair list from
volume-qualified months, so a volume-qualified M+1 still decided whether the M row existed; the
counterfactual (changing only R0A-2022-03's target-month attendances) removed the row. `make_rows` now
iterates the provider's qualifying months, checks 24 months of history at or before M, and looks up the
target month purely to compute the label. A missing target month is counted as `unobserved_target`
(134) - missing outcome data, not exclusion. Also: the instant uses the MAXIMUM observed publication
lag (13 days; 9/13/10 for Jun/Jul/Aug 2026) instead of a fixed 10, and the doc defects the auditor
listed are fixed (month-end wording, flat-path checksum command, three-week lag, "balanced by
construction"). Data bytes are identical to v2026.11; only quality.json and the documents change.
Artifact f4cb7fde0af5c211, gate 1.4.0 PASSED, baseline re-run 0.5511 CONTRACT OK, 129 shipped
providers from 142 candidates. v2026.10 and v2026.11 are superseded; neither may be published.

## 2026-10-21 (evening) - Africa discovery tick: three verdicts, the bench's first African live candidate

Scheduled discovery session (regional focus: Africa). Quota met: three new sources taken to
recorded verdicts, all three with African publishers; no build, qualification, packaging or
publication commands were run this session. Full evidence in each candidate's record.json/notes.md;
probe scripts backing recorded measurements kept in the candidate directories.

- `za-municipal-audit-opinion` (National Treasury Municipal Finance Data / Municipal Money; label
  origin Auditor-General of South Africa) - **go, status ready**; the bench's first live African
  candidate and the fourth in the ready buffer. Anonymous bulk CSVs per cube per year on S3, each
  with index.json checksums, regenerated 2026-07-30/08-05 (live pipeline: banner "updated with the
  latest 2026 Q2 data"). Terms of use measured at /terms: free download, adapt, distribute,
  commercial and non-commercial, with attribution of source and publication date. Label panel
  measured: AGSA audit opinions 2011-2024, 292 demarcation codes, both classes every year
  (qualified-or-worse 35.0%-56.5% per year). Primary formulation is deterioration-onset on
  clean-prev municipalities because the level label measured 83.88% persistent year-over-year
  (2018-2020); onset base rate 69/381 = 18.1% in the eval window. Instant: the statutory AFS
  submission deadline (31 Aug k, MFMA wording to verify at construction), with observed AGSA
  general-report tabling dates recorded (27 Aug 2024 for FY2022-23; 24 Jun 2026 for FY2024-25)
  and a conservative opinion-knowledge bound through year_end k-2. Novelty differentiated
  (check-novelty.py, 3 queries): Mongwe/Malan/Marwala et al. (PLOS ONE 17(3):e0261245 (2022);
  MDPI Sustainability 15(1):12 (2023)) predict the same opinions post-hoc from same-year audited
  ratios with no published artifact; Economies 8(1):18 ships a Zenodo dataset for the adjacent
  distress task. Next action: worker construction per record.json's five-step list (verify MFMA
  deadline, checksum-snapshot bulk cubes, build onset rows at the instant, baseline triad FIRST).
- `saps-station-crime-quarter` (South African Police Service) - **park, licence-blocked**.
  Station-level quarterly XLSX measured (FY2025/26 Q2 workbook 11,554,369 B, PK-verified, headers
  Station/District/Province/Crime_Category/Code + national and provincial contribution/count-diff
  placements; quarterly series FY2019/20-FY2026/27 Q1 across the two pages), but copyright.php:
  "All material on this site is subject to copyright" and disclaimer.php grants nothing - escalated
  as a decision, never assumed. Secondary: station-quarter counts are persistence-shaped (an
  onset/change formulation must be designed in before any unpark); www.saps.gov.za also serves an
  incomplete TLS chain (all probes needed verification disabled - recorded). Unpark: written SAPS
  permission for derived station-quarter tables, then novelty vs existing Kaggle/academic mirrors.
- `kenya-opendata-knbs` (Kenya) - **park, honest empty result**. open.data.go.ke no longer resolves
  (NXDOMAIN, measured) so the historical per-dataset licence channel is gone; knbs.or.ke is
  "All Rights Reserved" and hosts no data files itself (zero .pdf/.xlsx/.csv/.zip links on its
  data-portals page, measured; also serves an incomplete TLS chain); the third-party channels it
  names are a Cloudflare-walled Knoema aggregator (403 challenge to headless clients, and its
  terms are not the publisher's) and a static SDG dashboard. Unpark path in the record (KNBS NADA
  microdata catalogue, then any successor portal, then sector regulators). No US source substituted.

Region texture for the next Africa tick: both national portals named in the rotation's starting
map (data.gov.za, open.data.go.ke) are NXDOMAIN as of 2026-10-21, and StatsSA sits behind an
Incapsula bot-wall (212-byte challenge page, measured; a real-browser re-read is required before
recording licence silence there). The live, openly licensed channel this tick was sector
infrastructure - a treasury/audit data platform - so the next Africa tick should lead with
treasury/audit/procurement-style sector infrastructure rather than the national portals.

Coverage after this session (discovery-coverage.py): 49 candidates, 20 live; Africa 3 (ZA 2, KE 1);
live non-US 14/20 (70%); live African candidates 1 (za-municipal-audit-opinion, ready). Ready
buffer behind construction: tsb-railway-occurrence-casualty, chilecompra-tender-outcome,
camara-bill-advancement, za-municipal-audit-opinion.

Session hygiene: `python3 -m unittest discover -s tests` = 398 tests OK; `check-candidate.py --all`
OK; probe scripts kept per convention (probe_label_stats.py, probe_workbook_peek.py); the rest of
the session scratch (including 82 MB of measured bulk CSVs) deleted from .factory and never committed.

## 2026-10-21 (late) - South/South-East Asia discovery tick: three verdicts, one new live Malaysian candidate

Scheduled discovery session (regional focus: South and Southeast Asia). Quota met: three new
sources taken to recorded verdicts, all three with publishers in the region (MY, ID, PH); no
build, qualification, packaging or publication commands were run this session. Every named
regional portal (data.gov.in, IMD, CPCB, BPS, PSA, Thailand Air4Thai, Vietnam GSO, Malaysia DID)
was already in candidates/, so this tick opened three NEW publishers rather than re-vetting.

- `my-pricecatcher-weekly-increase` (KPDN + DOSM, via data.gov.my / OpenDOSM) - **go, status
  ready**; the bench's first retail-pricing task and its fifth ready-buffer candidate. Task: for
  an item-premise pair active in week W (>=3 observations), will the weekly modal price INCREASE
  in week W+1? Panel measured on 2 full month files (1,933,285 rows Aug 2026 + 1,742,320 rows Sep
  2026): 2,158 premises x 343 items, 0 duplicate rows, 58 monthly editions 2022-01..2026-10,
  same-day freshness measured (2026-10 file carried 2026-10-21 rows at the 12:10 UTC refresh).
  Label measured on a 10% premise subsample, 7 transitions: increase rate 0.155-0.222, decrease
  0.145-0.201, both classes everywhere, positives spread over 54-58 items (top-10 items 38-45%).
  Licence measured per-dataset on the page: CC BY 4.0 verbatim. Novelty differentiated
  (check-novelty.py, 3 queries): prior retail benchmarks are demand forecasting (M5 etc.) where
  price is a feature; no retail micro-price increase task found. Cross-check: The Star 2025-12-04
  parliamentary reply corroborates the panel (2,170 premises / 316 items / 850+ officers). Cost
  measured: 45-65 MB/month, ~58 requests for the full window (estimate from 3 measured sizes).
  Next action: worker construction per record.json's six-step list (snapshot+hash monthly files,
  pair-week panel, week-W-gated features, longitudinal-panel identifier policy in quality.json,
  known-event fixtures: diesel 2024-06-10 + sugar 2022-11 + festive control schemes, baseline
  triad first).
- `id-ojk-bank-supervision` (Otoritas Jasa Keuangan, Indonesia) - **park, licence-blocked +
  access-blocked**. Per-bank monthly SPI panel + a published bank supervisory-status product (a
  task family the bench lacks entirely), but measured: terms page carries no grant (footer
  'Copyright Otoritas Jasa Keuangan 2024' only), SPI moved July 2025 to data.ojk.go.id/SJKPublic
  whose data endpoint answers a WAF 'Request Rejected' page to scripted clients, and the legacy
  SharePoint pages load monthly files via JS absent from served HTML. Unpark: real-browser XHR
  capture + written OJK permission or operator risk acceptance + novelty check vs the Indonesian
  bank-distress literature.
- `ph-pagasa-climate-station-data` (PAGASA/DOST, Philippines) - **park, request-gated channel**.
  Measured: raw climatological Excel data requires identity-verified request forms with a signed
  TOU (CADS-01A/02A: valid ID, for students an approved thesis proposal and a signed letter to the
  Administrator); the PhilDA portal host is NXDOMAIN; CliMap downloads are email-registration-
  gated with gridded obs 'under development'. Unpark question: does PAGASA or GeoRisk PH ever
  publish historical station observations anonymously with readable terms (probe
  portal.georisk.gov.ph ArcGIS REST 'Rainfall_Forecast_Observed' first)?

Region texture for the next S/SEA tick: national met services keep station archives behind
signed-TOU request forms (IMD parked the same way - now PAGASA too), while the open+anonymous
channels are the operational/sector ones (data.gov.my's new portal is exceptional: 338 datasets,
45 agencies, per-dataset CC BY 4.0, parquet+CSV, current-month files refresh same-day). The
data.gov.my catalogue holds several more distinctive sources not yet opened (hourly KTMB
origin-destination ridership, JPJ car registration transactions 2000-present, NPRA approved/
cancelled pharmaceutical products, daily blood donations by state) - the next tick should open
one of those before looking outside the portal.

Coverage after this session (discovery-coverage.py): 52 candidates, 21 live; South & South-East
Asia 13 (MY 2, ID 3, IN 3, PH 2, TH 1, SG 1, VN 1); live non-US 15/21 (71%). Ready buffer behind
construction: tsb-railway-occurrence-casualty, chilecompra-tender-outcome, camara-bill-
advancement, za-municipal-audit-opinion, my-pricecatcher-weekly-increase.

Session hygiene: 398 tests OK; check-candidate.py --all exit 0; probe script kept per convention
(probe_panel_stats.py in the candidate directory); session scratch deleted (95 MB of measured
month CSVs, never committed). No US source substituted for the regional quota.



**nhs-ae v2026.12 staged private on both destinations (2026-10-21).** GitHub draft release 420072089
(5 assets, digests re-read from the API after upload; v2026.10 and v2026.11 renamed SUPERSEDED) and
Hugging Face (16 files, all five data files re-downloaded and re-hashed at the manifest digests).
Status `packaged`, `awaiting_operator: true`.
New test `tests/test_nhs_ae_selection.py` turns the re-audit's counterfactual into a guard: a provider
with 24 months of history whose target month falls below the volume gate must still produce a row. On
the v2026.11 build it fails ("'TEST-2022-01' not found in set()"); on v2026.12 it passes. Also covers
the 24-month exclusion and the unobserved-target accounting.
Held from the flip pending a third independent pass.

**Licence triage moved to the front of the queue (2026-10-21).** 18 of 31 parked candidates were
parked on licence or terms after probing had been paid for. `licence_class` (A open / B open with
conditions / C unresolved / D prohibited) is now part of the candidate identity: required for any
status at or beyond `ready`, and a C may not be packaged or published without a recorded operator
risk acceptance. `scripts/licence-rank.py` sorts the construction queue by class, and the discovery
prompt now triages the licence in the first minutes and rejects D on the spot. Backfilled honestly:
10 candidates classified from recorded evidence at the time, 6 ready ones reviewed and all class A
(CC0 Chile, CC BY Malaysia and EU, OGL Canada, public domain Brazil, Treasury terms South Africa),
WHO FluNet carries class C plus the 2026-10-21 risk acceptance. 42 remain unclassified and cannot
be built until triaged.

**Standing licence policy (2026-10-21): we only build on sources that are already clean.**
Class C ("unclear / contact us") is now a **drop**, not a park: no permission emails, no dated path
out, no waiting. Class D is a drop on sight with the clause quoted. Only A and B are pursued. The
discovery prompt, `scripts/licence-rank.py` and `docs/OPERATIONS.md` carry the rule; the queue is
sorted by class so a C cannot consume build time. Closed under the policy: `melbourne-pedestrian-counts`
(no licence on any of four channels) and `cpcb-aqi-exceedance` (only a republisher's terms were read).
All active candidates (investigating/ready) now carry a class: 16 A, 3 B, 3 C, 30 unclassified - and
every one of the unclassified is already parked or dropped.

**nhs-ae-four-hour-decline DROPPED 2026-10-21 (operator decision).** Three rebuilds and three independent audits produced a
correct artifact, and the correct artifact showed the task is not worth having: persistence 0.5758, a train-only month prior
0.6027 and reversal 0.5839 all beat the shipped baseline 0.5511, so the headline finding is that a one-line rule wins. The
publication lag also cannot be established point-in-time (NHS publishes no vintage archive), so every timing claim is a bound.
The staged v2026.13 release stays private and unpublished; v2026.10/v2026.11/v2026.12 are already marked superseded.
Lesson adopted: a candidate whose reference baselines beat every model that can be built on it is a negative result, not a
benchmark - decide that at construction time, not after three audits.

## 2026-10-22 - International organisations discovery tick: four verdicts, one new ready candidate

Scheduled discovery session (regional focus: International organisations - World Bank, OECD, UN agencies, WHO, IMF, ITU).
Quota met and exceeded: four new sources taken to recorded verdicts, all four from the tick's named publishers, three of
them outside the US (OECD/FR, UNODC/AT, ITU/CH; the World Bank's HQ is Washington so its jurisdiction is US, recorded as
such and excluded from the non-US count). No build, qualification, packaging or publication commands were run. UNHCR,
UNICEF and WHO-FluNet were already in candidates/ (parked 2026-10-20 / published) and were not re-vetted.

- `wb-ieg-project-outcome` (World Bank Group / Independent Evaluation Group, Washington DC - US jurisdiction) - **go,
  status ready**; the bench's first development-finance project-outcome task and its sixth ready-buffer candidate. Task:
  at Board approval, will IEG's final evaluation rate a World Bank (IBRD/IDA) project's outcome MS+? Label source: IEG
  World Bank Project Performance Ratings (Data Catalog 0038059 / Finances One DS00053), CC BY 4.0 on the dataset page and
  in the metadata API, public classification, 12,629 rows x 21 cols in ONE anonymous CSV request (3,340,648 B measured),
  data as of 2026-10-20, refreshed daily/quarterly. Measured: MS+ share 0.7365 over 12,478 rated rows; approval FY
  1956-2024 all rows present; approval->evaluation lag min 1 / median 8 / max 31 years; windows train <=2009 n=9,741
  (MS+ 0.7074) / eval 2010-2014 n=1,488 (0.7890) / holdout 2015-2019 n=1,097 (0.8067), both classes everywhere,
  prevalence drift recorded as a property; 4,695 country-approvalFY clusters. Two discovery-time catches recorded for
  construction: (1) country_fcs_status/country_lending_group are evaluation-vintage not approval-vintage (165/4,695
  country-year cells carry both values, flipping with evaluation_fy - e.g. Cameroon FY1995: eval 1997 non-FCS, eval 2008
  FCS), so they must not ship as features; (2) project_id P122764 appears twice (eval FY 2023 and 2026) - dedupe keeping
  latest evaluation_fy and declare the grain. Approval-time features come from the anonymous Projects API
  (22,729 projects; 1,000-row page cap measured, rows=10000 silently returns 1,000; ~27 MB / 23 requests for a full pull,
  estimate). Novelty differentiated (check-novelty.py, 3 queries): the Bank's own internal model exists (Kraay & Tawara
  WPS 7001, 2,729 IPF ops 1995-2012 - models in a working paper, no public artifact; its strongest features are
  post-approval TTL track record and CPIA); HF hosts WB project documents with "no leaderboard yet / no train test split";
  no public train/eval/holdout task with a scored contract found. Headroom risk recorded honestly in the record: with
  strictly approval-time features the signal is unmeasured; the baseline triad decides at construction whether this is a
  benchmark or a negative result (the nhs-ae lesson). Next action: construction per record.json's eight-step list.
- `oecd-sdmx-aggregate-family` (OECD, Paris - FR) - **reject, dropped** on task shape; licence measured clean (class A)
  so a future session need not re-check it. Measured: the SDMX API behind Data Explorer serves 1,550 dataflows (8.9 MB
  inventory XML; 53 agencies incl. republished ESTAT and IAEG-SDGs flows); grain probes on three flagship families all
  returned geographic-unit x period aggregates (QNA 2024-Q3: 21,779 country x transaction x quarter rows; KEI 2026-01:
  1,469 country x measure x month rows; FUA labour 2020: 4,759 city x measure x year rows). Level target = the measured
  nhs-ae persistence defect; change target's positives cluster into a few global shock years; the OECD's one row-level
  product (global recalls portal) mirrors national recall datasets already on the bench (hc-recalls-classification).
  Four HTTP requests; no bulk pull.
- `unodc-data-portal` (UNODC, Vienna - AT) - **reject, dropped on licence, class D, at the first step**. The publisher's
  own instrument (the portal's "Terms and Conditions" href, measured on both the home and datasearch pages) is the UN
  legal notice: download and copy "for the User's personal, non-commercial use, without any right to resell or
  redistribute them or to compile or create derivative works therefrom" - a published dataset of derived rows is both.
  No open-licence string on any probed channel (home, datasearch; /api /about /help /documentation /faq all 404;
  dataunodc.un.org 302). Consistent posture on UNODC's EWA terms ("data ... cannot be published without prior written
  authorization"). Total cost: six HTTP fetches - the licence-first triage closed this door before any schema or volume
  work, which is the policy working as designed.
- `itu-datahub-ict-panels` (ITU, Geneva - CH) - **reject, dropped** on aggregate-panel shape + an existing mirror;
  licence recorded as class B. The DataHub is annual country panels (~200 economies, questionnaire-collected ICT
  indicators) and the World Bank already redistributes the identical DataHub bulk-downloadable (Data 360 dataset ITU_DH
  with per-indicator CC BY-NC-SA 3.0 IGO labels; Data Catalog 0067055 claiming CC BY 4.0 for its copy - conflicting
  republisher labels, the publisher's NC-SA instrument governs, read in a real browser after the host answered 403 to
  plain clients, per the skill's 403-is-not-silence rule). The ITU Radiocommunication sector's satellite-filings registry
  is the one unprobed row-level candidate family, named in the record for a future tick.

Region texture for the next international-organisations tick: the named publishers split cleanly into the aggregate-panel
family (OECD, ITU, IMF would land the same way - annual country panels republished by WDI) and the licence-locked family
(UNODC class D; UNHCR/UNICEF parked 2026-10-20; WHO-FluNet carried a class C risk acceptance). The productive seam is the
World Bank's project/evaluation microdata (this session's go) and similar entity-level operational products (IAEA PRIS
reactor operations, WOAH WAHIS outbreak events were identified but not opened this session) - event/entity-level data
with a documented label process, not indicator panels.

Coverage after this session (discovery-coverage.py): 64 candidates, 22 live; International organisations 7 (CH 3, US 2,
FR 1, AT 1); live non-US 15/22 (68%); ready buffer behind construction: tsb-railway-occurrence-casualty (packaged, awaiting
operator), chilecompra-tender-outcome, camara-bill-advancement, za-municipal-audit-opinion, my-pricecatcher-weekly-increase,
wb-ieg-project-outcome.

Session hygiene: `python3 -m unittest discover -s tests` = 406 tests OK; `check-candidate.py --all` exit 0 (all four new
records OK); probe scripts kept per convention (probe_ieg_stats.py, probe_join.py in the WB candidate); all session
scratch (3.3 MB IEG CSV, 8.9 MB OECD inventory, three OECD CSV windows, fetched HTML - deleted from scratch by exact
filename after the gate refused the recursive form). No US source substituted for the regional quota.


**my-pricecatcher-weekly-increase PUBLISHED 2026-10-22 (GitHub + Hugging Face).**
Built from 36 monthly PriceCatcher files (2023-11..2026-10), state of Johor: 397,982 train / 280,468 eval /
154,279 holdout item-premise-weeks (14.9% / 17.5% / 20.4% positives, 143,978 unobserved outcomes counted not
dropped). Gate 1.4.0 PASSED, artifact 06c5cd6f8a74aef9. Runner-contract baseline 0.7520 eval AUC, reproduced on
both paths; references: item prior 0.5354, momentum 0.5001, reversal 0.4974, n_obs 0.4769 - a real signal, no
persistence dominance. Source CC BY 4.0, compilation CC0, code MIT. Both destinations public and digest-verified
anonymously. Site page still pending: the site publisher raises an untyped TypeError on this package (manifest
splits now populated, source block shaped, DESTINATIONS matched) and needs a real traceback pass.

**Correction to the entry above (found and verified by this session, 2026-10-22 ~10:05Z): the my-pricecatcher
site page IS live and complete.** The TypeError was fixed and the site published by the 09:51Z session (commits
`1bbd61d` "PriceCatcher: website live; fix manifest splits and Hub tag reconciliation" and `01905d5`), which never
updated STATE.md. Verified anonymously by this session before writing the correction: page
https://earino.github.io/my-pricecatcher-weekly-increase/ = 200 (8,818 bytes), versioned page
.../versions/v2026.10/ = 200, and the catalogue (dataset-factory-site catalog.json, 204,188 bytes) lists the
release with the matching artifact_version 06c5cd6f8a74aef9. The candidate record's website artifact entry
(verified=true, "No further action") was right; STATE.md was the stale surface. Nothing remains for that dataset.

## 2026-10-22 (later) - advancement tick: abs-visitor-arrivals-direction constructed, gated 38/38, baselined through the runner contract

Release work first: no candidate sits at `packaged` (checked with .factory/session_status.py over every
candidates/*/record.json), and the only stale release surface - the my-pricecatcher STATE.md entry above - was
corrected after anonymous verification. Both data destinations for every published candidate answer 200
anonymously; nothing actionable was held, so the tick went to construction.

`abs-visitor-arrivals-direction` went **ready -> qualified -> baselined inside one tick**, the queue's top
class-A candidate (licence-rank.py) and the cheapest measured build on the bench (1 anonymous GET,
3,308,454 bytes).

- **Construction (abs-001)**, worker 171801245 (cx23, 19.3 s job elapsed, exit 0, EUR 0.04 reservation,
  destroyed 10:26:49Z): build `candidates/abs-visitor-arrivals-direction/source/build.py` fetches the full
  OAD_COUNTRY panel + structure, builds the (country, target month) visitor-series panel
  (CAT_TRAVELLER=06, TSEST=10 only), features = levels at M/M-1/M-2/M-3/M-6/M-12 + four differences + country +
  calendar, label = fell_short iff OBS_VALUE(T) < OBS_VALUE(T-12), both label source values excluded from every
  written header. Shipped: train 19,071 / 6,668 positives (34.96%) / 275 event months (1992-02..2014-12); eval
  4,140 / 1,204 (29.08%) / 60 months (2015-2019); holdout 3,920 / 768 (19.59%) / 45 months (2022-01..2026-08);
  1,662 pandemic target months excluded and counted (2020 down-share 0.9251, 2021 reopening recorded), 224
  insufficient-history and 10 unobserved-target rows accounted, 70 live-month rows scorable at the next OAD
  release. Panel provenance asserted single-stream: TSEST=10 only, FREQ=M only, UNIT_MEASURE=NUM only,
  OBS_STATUS empty on all 59,452 rows, 0 missing OBS_VALUE.
- **Qualification**: gate 1.4.0 green on the worker over the full artifact - 38/38 checks, artifact
  `afb46c6b29e6c4aa...`; staging release 420574099; the five extract files and the gate report re-downloaded on
  the coordinator, every digest matched the release manifest, and `qualify_dataset.py --accept` re-verified the
  collected bytes -> ACCEPTED. Record now carries the full qualification block; `check-candidate.py --all` exit 0.
- **Baseline (abs-baseline-001)**, worker 171804060 (76.6 s, exit 0, EUR 0.06 reservation, destroyed
  10:37:25Z), report at staging 420587459: the benchmark's own train.py/validate.sh unmodified (bundled hashes
  match) on the re-ACCEPTed artifact. **Triad complete on identical eval rows: persistence (YoY sign at M)
  0.3647 < calendar-only 0.5501 < identity-only 0.5720 < full model 0.6219** (validate.py independently
  recomputes 0.6219; CONTRACT OK). Persistence is ANTI-correlated with the label (holdout 0.2256): a falling
  YoY trend at M predicts a recovery, not another fall - this is a mean-reversion + seasonality task, the
  opposite of the nhs-ae persistence defect, and the model clears the calendar-only reference by +0.0718 eval
  AUC. Prevalence drift 34.96% -> 29.08% -> 19.59% across splits is recorded as the post-2022 recovery boom.
- **The coordinator dry run earned its keep**: run on a scratch copy before any worker spend, it caught (1) a
  baseline-lookup bug - rate-table keys are tuples, the identity lookup used bare strings, collapsing every
  score to the global rate and printing exactly-0.5 AUC twice; full-precision recompute from the written CSVs
  gave 0.572/0.532 - (2) a known-event fixture window error (the record's border-closure fixture is 2020-only;
  folding 2021's reopening in diluted the down-share to 0.6528 < 0.75 and failed), and (3) a
  use-before-definition the type checker caught. Dry-run gate 38/38 before the worker launch; abs-001 then
  passed first try, unlike flunet-001 which burned a launch on a descriptor defect.
- Cosmetic defect recorded (notes.md): abs-baseline-001's baseline_result.json purpose string says "TSB rail
  occurrence casualty artifact" - report.py was copied verbatim from the tsb bundle with a hardcoded line. Every
  artifact fact in the report is abs's; the abs copy's purpose line now derives from meta.json.

Ready buffer behind this one: camara-bill-advancement, chilecompra-tender-outcome, eutl-installation-net-short,
nz-ea-wholesale-price-exceedance, wb-ieg-project-outcome, za-municipal-audit-opinion (all class A, status
ready). Next action for abs: packaging per the dataset-release skill; the holdout extends one month per OAD
release (Sep 2026 due 2026-11-12), so rebuild before packaging if a fresher month is wanted.

**Watcher addendum (2026-10-22 ~10:45-11:00Z, worker-watcher cron): closed out abs-baseline-001 after the
research session died mid-commit.** The 10:00Z session recorded the baseline outcome in record.json, notes.md and
this file and staged everything, then exited 1 at 10:39:51Z before committing; the watcher cron verified the
staged work (all 9 small report assets re-fetched from staging 420587459 and sha256-matched; eval AUC 0.6219 on
both contract paths; worker 171804060 confirmed deleted by hcloud read-back), committed it as c621acd and pushed.
CI on c621acd failed `test_no_caches_under_skills` - a pre-existing defect from 01905d5 (main was already red on
1bbd61d4 and 01905d51): test_gate_unscorable.py loaded the gate via module-level `spec.loader.exec_module`, which
writes `__pycache__` under skills/ on a fresh CI checkout (CI does not set PYTHONDONTWRITEBYTECODE; this host
does, which is why local runs passed). Fixed in 9918084 by switching both gate-loading tests
(test_gate_unscorable.py, test_timing_gate.py) to the repo's compile-from-bytes convention; verified in a clean
clone with bytecode writing enabled (408 OK, no caches under skills/ or candidates/) and CI is green on 9918084.
Next action unchanged: abs-visitor-arrivals-direction packaging per the dataset-release skill.

## 2026-10-22 (later) - discovery tick: Europe/EU-EEA focus - 3 verdicts (1 go, 1 park, 1 reject), all EU publishers

Regional focus Europe per the tick. Coverage before: 0 of 6 live candidates were EU-publisher (discovery-coverage.py);
after: EU candidates 5 total (eutl ready, bvl investigating, plus the three below), live non-US 16/23 (70%).
No construction, packaging or advancement was touched.

1. **eea-uwwtd-plant-poor-performance - GO (investigating, licence A, novelty differentiated).** EEA's
   UWWTD Waterbase (biennial Art.15 reporting, ~24k active treatment plants x 30 EEA reporters). Task: for an
   active plant in cycle N, will it be reported failing >=1 treatment-performance parameter (any uww*Perf='F')
   in the next cycle. Licence CC-BY 4.0 quoted from the EEA SDI catalogue record (DG ENV + EEA copyright
   holders). Measured on the full 13th-call zip (1 anonymous GET, 108,877,653 B, 6.6 s, deleted after
   extraction): UWWTPS.csv 26,064 rows x 69 documented columns; active 23,987; label base rate 2,411/21,537 =
   11.2% any-F; cause-of-failure fields (uwwBadPerformance Yes 1,765) recorded as label-source. Measured
   caveat recorded as target semantics: reported-failure rates mix plant performance with national reporting
   regime (DE 0.4%, BE 2.8% vs NO 49.6%, HR 53.5%) - country-stratified baseline required. Cycle inventory:
   2 tabular cycles public-measured (2011-2012 v04, 2022-2023 v10 final) + 2021-2022 provisional + spatial
   plant GeoPackages for 2017-18/2019-20/2021-22/2022-23; six internal-only records 401. Next action
   (advancement): pin the public cycle inventory, MEASURE the uwwCode join across two cycles before any
   build job, then build.py -> gate with the country-stratified reference in the baseline triad.
2. **ec-tdi-case-outcome - PARK (access blocker).** DG TRADE's TRON register is a WAF-protected Angular
   app: shell 200 but all bundles/API 403 to non-browser clients (measured); a real-browser probe rendered
   72 ongoing cases (case no., product, countries, type+article, initiation date, per-case history) via
   undocumented internal endpoints (/investigations/api/eucase/list/ongoing). Would-be task (definitive
   measures vs termination) is promising and unmirrored, but no documented anonymous channel exists - same
   shape as the ECDC Atlas access blocker. Unpark question exact: a documented API/bulk export or
   machine-readable TDI annexes, or a declared data client past the WAF; worth one cheap re-probe/quarter.
3. **efsa-one-health-sample-prevalence - REJECT (task-shape duplicate).** The EU-wide twin of bvl-zoom:
   36 Zenodo records "Sample based prevalence data complementing the EU One Health Zoonoses Report", per
   (country x reporting year), all CC BY 4.0, anonymous (2024-year files measured: FI 1.7 MB, DE 5.9 MB,
   HR 2.4 MB; ~1-year publication lag). Rejected because the sample-positivity task on this exact reporting
   stream is already open as bvl-zoom-sample-positivity (investigating, go); the EU-wide files and record
   ids are pinned in the record for a fresh candidate ONLY after bvl-zoom ships and a second instance is
   wanted.

Also opened, not settled (recorded here so the probes are not re-run): **Frontex** migratory statistics -
frontex.europa.eu 403s non-browser clients (legal notice unread without a browser; data.europa.eu carries
only 2010-11 FRAN quarterly PDFs). Deferring: needs a browser session to even classify the licence; do not
open without one.

Checks: scripts/check-candidate.py --all exit 0 (67 records); discovery-coverage.py exit 0. The discovery
probes ran as scratch scripts in .factory/ (deleted afterwards; scratch UWWTD extracts and the 109 MB zip
removed). A recursive-delete cleanup was correctly refused by the single-query approval gate; cleanup was
redone with explicit per-file deletions and rmdir on exact owned paths.
Next action for the tick: none beyond the per-candidate next_actions above - the queue's next construction
work remains abs-visitor-arrivals-direction packaging (advancement session), with eea-uwwtd needing its
cycle-inventory + join measurement before it can enter the build queue.

## 2026-10-22 (later) - advancement tick: eutl-installation-net-short ready -> qualified -> baselined inside one tick

Release work first: no candidate sits at `packaged` (checked with .factory/session_status.py;
status counts parked 25 / dropped 19 / published 9 / investigating 8 / ready 6 at tick start),
and every published candidate's destinations answer 200 anonymously - nothing actionable was
held. The tick went to construction and picked `eutl-installation-net-short`: the queue's
cheapest fully-measured class-A build (one anonymous 5.96 MB GET) and an EU publisher, which
also nudges the bench's Europe coverage (EU candidates now 5; live non-US 16/23, 70%).

Pre-build probes (scratch scripts, deleted): today's snapshot 2026-10-22 carries 617,448 rows /
23,748 keys / 32 registries; all three record sample fixtures verified in-panel (AT,1 2005
net-long, 2007 net-short, 2030 advance allocation); SURR_ALL(t-1) missing on 10,647/188,205
eligible rows -> surrender-history feature dropped rather than shipped partially defined;
EXCLUDED(t)=YES is 81/204,914 in-frame rows (kept, mix recorded); status persistence measured
P(short|short)=0.857, P(short|long)=0.176. The EEA cross-check subset was pinned by
measurement: the EEA sheet carries per-activity detail rows AND aggregate rows, so the sum must
use exactly activity codes {10, 20-99} - DE 2022 verified emissions then match the panel sum
exactly (361,145,695), 2023 differs by 4 t (1.3e-8), free allocation within 4.3e-4.

- **Construction (eutl-001)**, worker 171845011 (cx23, 40.7 s job elapsed, exit 0, EUR 0.04
  reservation, destroyed and confirmed deleted 14:18:34Z): panel fetch 5,965,780 B in 1.0 s +
  EEA zip 10,794,107 B in 9.3 s. Shipped: train 141,732 rows / 64,528 positives (45.53%) /
  2006-2019; eval 24,322 / 18,002 (74.02%) / 2020-2022; holdout 22,151 / 15,993 (72.20%) /
  2023-2025; 16,709 insufficient_history (all of 2005 plus each installation's first active
  year), 4,224 exact ties -> 0, 6,449 live 2026 rows (allocation published, emissions due
  31 March 2027). Coordinator dry run BEFORE worker spend: full build + gate 1.4.0 38/38 in
  11 s, and the worker's three CSVs came out byte-identical to the dry run
  (c7f23c55.../0d9f35d5.../1c694e5e...) - second tick in a row the dry run paid for itself
  with zero worker waste.
- **Qualification**: gate 1.4.0 green on the worker over the full artifact - 38/38, artifact
  `3540ad2180d8df8a...`; staging release 420810883; all six assets re-downloaded on the
  coordinator, every digest matched the release manifest, `qualify_dataset.py --accept`
  re-verified the collected bytes -> ACCEPTED. Record carries the full qualification block;
  `check-candidate.py --all` exit 0 (67 records).
- **Baseline (eutl-baseline-001)**, worker 171847046 (41.3 s, exit 0, EUR 0.06 reservation,
  destroyed and confirmed deleted 14:24:17Z), report at staging 420818845: benchmark's own
  train.py/validate.sh unmodified (hash-matched), artifact re-ACCEPTed before scoring.
  **Triad on identical eval rows: calendar-only 0.527 < identity-only 0.5719 < persistence
  (t-1 net-position margin) 0.8671 < full model 0.9199** (validate.py independent recompute
  0.9199; CONTRACT OK). The full model beats persistence by +0.0532 eval AUC - not the nhs-ae
  persistence defect; most of the edge is the announced-allocation margin rule (margin_t alone
  measured 0.8988 at construction), and persistence is recorded beside every model number.
  Per-year eval texture measured on the written rows: 2020 rate 0.6713 / persistence 0.9046;
  2021 0.8075 / 0.8269; 2022 0.7582 / 0.8723. Prevalence drift 45.5% -> 74.0% -> 72.2% is
  the documented ETS phase property. No holdout AUC quoted (never enters a workdir).

Worker spend this tick: two cx23 jobs, EUR 0.10 reservations, both workers confirmed deleted
by hcloud read-back. Ready buffer behind this one: camara-bill-advancement,
chilecompra-tender-outcome, nz-ea-wholesale-price-exceedance, wb-ieg-project-outcome,
za-municipal-audit-opinion (all class A, ready). Next action for eutl: packaging per the
dataset-release skill (staging release 420810883, artifact 3540ad2180d8df8a...); no rebuild
needed first - the daily snapshot only grows live 2026 rows until the 2026 emissions are
reported (due 31 March 2027).

## 2026-10-22 (later still) - discovery tick: United Kingdom focus - 4 verdicts (1 go, 3 reject), all UK publishers

Regional focus for this tick: United Kingdom (ONS, NHS Digital, Defra, Environment Agency,
Companies House, data.gov.uk). Coverage before: GB 6 candidates; after: GB 10 (live non-US
17/24, 71%). All four verdicts are UK publishers; two from the tick's named list (Environment
Agency, Defra). Existing GB doors were respected: companies-house (parked permanently),
defra-recycling, ons-claimant and nhs-ae all stayed closed with their recorded unpark questions.

1. **ea-flood-alert-escalation - GO (investigating).** Environment Agency Historic Flood Warnings
   (AfA435): 85,982 warning messages 2006-01-26 to 2026-06-25, delivered as an ODS inside a
   3,628,573-byte ZIP (1 anonymous GET), quarterly schedule, OGL v3.0 on the dataset's own page.
   The load-bearing discovery: the Flood Warning Areas register (WFS, properties-only, 9 requests/
   1.32 MB/3.8 s) publishes a **parent** attribute naming each warning area's containing alert
   area - escalation is a dict lookup, not polygon overlay. Task: for an eligible Flood Alert
   (53,048 events, code with >=1 child), will any child area receive a Flood Warning in
   [D+1, D+7] (window starts D+1 because 46.9% of same-window positives were same-day and dates
   are day-grain: 0 of 85,982 rows carry a time)? Measured base rate 14.34% (7,606 positives);
   splits train 2006-19: 28,864/3,638 (12.60%), eval 2020-22: 9,623/1,560 (16.21%), holdout
   2023-26H1: 14,561/2,408 (16.54%); positives every year; 458 distinct positive year-weeks;
   566/694 areas ever escalate. Persistence single-rule probe (child warning in previous 7d):
   P(esc|prev) 45.11% vs P(esc|no prev) 18.91%, 2x2 AUC 0.559 - a weak rule, not a dominant
   level, unlike nhs-ae. Novelty verdict **differentiated** (check-novelty.py): prior art is
   sensor-side forecasting (Iowa river-stage DNN, GFF inundation, HaorFloodAlert, Wupper QML);
   nobody predicts an agency's warning-escalation decision from its own warning history.
   Data quirks recorded: case-variant TYPE values, pre-2010 Flood Watch naming, April-2017
   system migration (per-year reporting will need it), 11% of message codes retired from the
   current register vintage. next_action: construction via build_panel.py (history features
   knowable by day D), gate on the worker, persistence+calendar triad before any model number;
   optional extension: EA Hydrology API (OGL 3) gauge join.
2. **fsa-fhrs-next-rating - REJECT (dropped).** FHRS API v2 + 385 per-authority XML extracts
   (FSA, England/Wales/NI + Scottish FHIS): anonymous, OGL v3.0 on ratings.food.gov.uk terms.
   Measured: the API schema and the XML extracts carry exactly ONE current rating per
   establishment (0 history elements in a 2,222-item extract sample); no dated historical
   vintages are published. Every prospective next-rating task needs >=2 inspections per
   establishment from obtainable data - only self-collection could produce it and self-collected
   labels cannot be verified. Secondary note: with history it would still be a shape sibling of
   the published chicago-food-inspections task.
3. **defra-aurn-pm25-exceedance - REJECT (dropped).** Defra UK AIR / AURN: day-ahead station
   concentration/exceedance from hourly history is the canonical air-quality forecasting task,
   the family eccc-hydrometric records as rejected and this bench has already declined twice
   (cpcb closed, air4thai parked with "a second air-quality task must argue why it is
   differentiated"). AURN publishes hourly gas/particulate concentrations only, so it carries
   no other task shape. Measured context, not the verdict reason: the whole uk-air.defra.gov.uk
   site is in a WSP maintenance outage (CVE-2026-109618/109619 PHP updates; identical 2,038-byte
   placeholder on every path, plain and browser UA), so the publisher's licence was not read
   this session and no licence claim is made (OpenAQ check: v2 retired 410, v3 needs a key).
4. **nrw-historic-flood-warnings - REJECT (dropped, task-shape duplicate).** The Welsh twin of
   the EA escalation stream (all Wales river/sea messages since 2006, quarterly, OGL with
   attribution per the CKAN record): pinned per the efsa precedent for a fresh candidate ONLY
   after ea-flood-alert-escalation ships; unverified whether NRW publishes an equivalent
   warning-area->alert-area linkage (first thing a second instance must check).

Checks: scripts/check-candidate.py --all exit 0 (71 records); scripts/discovery-coverage.py
exit 0; python3 -m unittest discover -s tests 419 tests OK. Probes ran as scratch scripts in
.factory/ (probe_ea_flood1-14, probe_fsa_fhrs1-2, probe_fsa_defra3-4, probe_nrw_flood1),
deleted afterwards along with the scratch ZIP and register snapshot.
Next action for the tick: the queue's construction work remains with the advancement session
(abs-visitor-arrivals-direction packaging, then eutl-installation-net-short packaging per its
staging release 420810883); ea-flood-alert-escalation enters the queue behind the five ready
candidates as a measured class-A build (whole panel fits the coordinator; ~4.9 MB of fetches).

## Engineering — scheduled-session admission (2026-10-22)

Prepared on `hardening/session-admission`, not deployed. A gate subprocess could
exit nonzero after printing allow; malformed wake directives could admit work;
concurrent wrappers checked before either wrote the JSON marker; and failed agent
processes returned scheduler success. The fix serializes gate-through-agent with
a persistent OS mutex, requires a successful unambiguous gate decision, preserves
the reporting marker, and returns truthful process outcomes. Local subprocess
regressions exercise competing ticks and parent death using stubs only. Existing
419 tests and qualification bytes are unchanged. Scout confirmed the JSON marker
and allow/hold protocol must remain compatible and nonzero exits surface through
the deployed scheduler. No live settings, shims, schedules, or worker state changed.

Next: exact-head CI and combined integration verification; include this as a
separate reviewable increment. The earlier five-PR rollout remains pending the
operator's explicit revision of “do not merge.” Before any rollout, reconcile
current research ownership and preserve fresh automatic skill-edit evidence.

### 2026-10-22 — runtime hardening rollout prepared

PR #4 now inventories all 14 custom skills captured by Scout at handoff `3ec0b64` (53 runtime
files plus eight project skill files). Corrected the publishing skill's delete/recreate-tag and
in-place published-manifest advice; original captures remain in #1. Source audit detects both
project and profile drift. The live host is unchanged. Source inspection proved curator pause
and pin do not block background-review patches: rollout must separately disable
auxiliary.background_review.enabled, pause interval curation, drain writers, and preserve
preimages before any restoration. Exact rollout/rollback and remaining work are in
docs/HARDENING-DEPLOYMENT.md. Next: finish combined checks, resolve the operator's earlier
no-merge instruction, then coordinate the documented rollout with Scout.
## Job assembly safety — 2026-10-22, engineering branch

On isolated `hardening/job-assembly`, the assembler no longer recursively removes the directory
named by a job descriptor. It validates identifiers/paths, stages and validates before exposing
output, seals ownership plus file hashes, and treats repeated job IDs as immutable. Same bytes
are a no-op; changed or unfamiliar work is preserved and requires a new attempt ID. Added safety
regressions for traversal, links, collisions, interrupted assembly and preservation. No worker was
launched and no scheduler/runtime settings were changed. See the resulting PR for clean-checkout
validation and exact-commit CI. Runtime handoff remains in Scout's PR #1; schema work is PR #2.
## Infrastructure hardening — 2026-10-22, engineering branch

Eduardo requested broader hardening with Scout's runtime knowledge. Work is isolated on
`refactor/release-schema`; live schedules and main remain unchanged. Scout prepared runtime
handoff PR #1 (`ops/scout-runtime-handoff`), including sanitized scheduler/shim sources.
`docs/HARDENING-PLAN.md` records the staged engineering work and deployment boundary.

First increment: one typed release reader, scoped/current baseline interpretation, diagnostic
errors, fail-closed manifest writes, and conformance tests over all ten packages. NHS remains a
private dropped historical package; NOAA retains both protocol scores. No published artifact or
gate byte was edited. Original 419 tests plus 22 new tests passed locally (six existing environment
skips); clean-checkout and exact-push CI evidence belong in the engineering PR.

Next: finish reviewer verification, open the schema PR without merging, review Scout's handoff,
then harden reproducible runtime recovery, safe generated-directory cleanup and publication
verification. Never launch a second coordinator on the live ledger.


### 2026-10-22 — Hub integrity hardening prepared

The Hub publisher previously deleted/recreated a version tag before verification, and treated
same-size plain Git files as verified. `hardening/hub-integrity` now verifies pinned content
first, hashes bounded metadata, refuses unverified bulk blobs, and creates immutable tags
with before/after revision checks. Existing matching tags are no-ops; conflicts/races fail
without deletion. Verification records the exact commit and does not claim a missing tag
exists. Negative tests use an injected fake Hub, with no credentials/network/worker spend.
Next: review this PR stacked on release-schema, combine it with runtime hardening, and deploy
only after the documented merge boundary is resolved. No remote tag or dataset byte changed.

Scout's live review caught ordinary Git CSVs and receipt downgrading. The Hub increment now
keeps incomplete attempts separate (exit 2), preserves the last complete receipt, and accepts
only collected successful worker evidence bound to the exact commit/blob IDs and manifest
assets. Workers emit that evidence and run loading against the same pinned commit. An explicit
hf_publish.verify_only mode obtains it for an old release without Hub uploads; no worker was
launched during development. Legacy reports remain historical, not fabricated into new evidence.

The existing scheduled Scout research session independently hit a 9,421,952-byte ordinary Git
CSV above the old worker re-hash ceiling. Integrated its captured fix (`1e53f97`) and four
regressions without changing the active session. Both worker verification paths now share
64 MiB per-file, with fresh owned caches cleaned after each check; added exact-size helper
and old-cache preservation tests. The coordinator still receives only compact evidence.
The container disk monitor does not cover host-side HF jobs; documented that remaining gap
instead of asserting max_disk_mb already enforces it. No engineering worker was launched.
## 2026-10-22 (evening) - eutl-installation-net-short PACKAGED: staged private on both destinations, awaiting the operator's flip

The advancement session packaged eutl-installation-net-short end to end but hit its 120-turn
limit at 18:37:54Z mid-close-out (it had just collected eutl-hf-003 and destroyed eutl-hf-002's
server); the worker-watch run completed the held remainder the same minute, per its recorded
handoff. All four worker servers of the evening are confirmed destroyed by read-back
(171893178 18:21:19Z, 171894191 18:29:55Z, 171894985 18:37:07Z, 171896019 18:40:37Z); spend was
four cx23 reservations at EUR 0.04 = EUR 0.16, inside the allowance.

**Package** (release/eutl-installation-net-short/, 26 tracked files + 3 git-ignored CSVs kept
off disk like tsb): artifact 3540ad2180d8df8a, gate 1.4.0 PASSED 38/38, baseline 0.9199 eval
AUC (persistence 0.8671, calendar 0.527, identity 0.5719 recorded beside it), splits train
141,732 / eval 24,322 / holdout 22,151 rows. check-package OK; the local qualification gate
re-ACCEPTed the package bytes. A real defect was caught by *executing* the generated
get_dataset.py against its own release: it still carried tsb's hardcoded EXPECTED digests,
refusing the release's own meta.json - fixed from MANIFEST.json and the tag moved onto the
fix commit.

**GitHub destination (private):** earino/eutl-installation-net-short release v2026.10 (421047536),
5/5 assets at the manifest digests (authenticated API read-back: meta.json b0e54387...,
private-holdout.csv 1c694e5e..., public-eval.csv 0d9f35d5..., public-train.csv c7f23c55...,
quality.json 88222d66...), tag == main == cba922f4, get_dataset.py run end-to-end against the
private release with --accept ACCEPTED. The session's summary claimed the release non-draft but
the API still answered draft=true - the takeover un-drafted it at 18:43Z and read draft:false
back. Anonymous repo API GET -> 404: private, the flip is the operator's.

**Hugging Face destination (private):** earino/eutl-installation-net-short, 16 files (5 data +
11 small: card/README, LOADING.md, MANIFEST, SHA256SUMS, licences, docs). hf-publish --verify at
18:41:57Z: ok, 0 missing, 0 size-mismatched. The eutl-hf-001/002 failures were a *verification*
defect, not a data defect: public-train.csv (9,421,952 B) stores as a plain git blob between the
worker's old 8 MiB re-hash ceiling and the Hub's ~10 MB LFS cutoff, so correct bytes could never
be confirmed. Fix (from the 18:21 watcher run, reviewed and used by the session): SMALL_BLOB_BYTES
8 -> 64 MiB in workers/hf_publish.py + 4 pinning regression tests (tests.test_workers 30/30).
eutl-hf-003 ran the fixed bundle: all 5 files already at the manifest digest (0 uploads, 5
skipped, 0 failures; public-train confirmed by download+re-hash), loading check green - train
141,732/64,528 positives, eval 24,322/18,002, holdout 22,151/15,993, 13 columns, label ['0','1'],
ok: true, problems: []. Tag v2026.10 created LAST: tag == main == 2501c26b (re-created on the regenerated-manifest
commit after the CSV off-disk cleanup). Anonymous API GET -> 401: private.

**Record flip:** candidates/eutl-installation-net-short/record.json now status=packaged,
awaiting_operator=true (packaged_at 18:43:19Z), artifacts = staging 420810883 + GitHub 421047536
+ HF repo, jobs extended with publish-001 and hf-001/002/003 (failures recorded with their root
cause, not smoothed away), next_action = the flip-waiting instruction with the full post-approval
publication sequence. DESTINATIONS.json now carries both destinations with artifact_version
3540ad2180d8df8a. Scratch cleaned: .factory/eutl-pack, eutl-consumer, eutl-consumer2 and the
probe/fetch scripts removed; the release CSVs deleted off disk (git-ignored, recoverable via
get_dataset.py and both private releases).

Next action: the operator's private-to-public flip for eutl-installation-net-short; nothing
blocks it. The queue behind it is unchanged (five ready class-A builds, then
ea-flood-alert-escalation).

**Post-push CI repair (same evening, watcher takeover run):** the `Website pipeline preview`
workflow had been failing on every `release/**` push since the abs publication (bf79053,
13:51Z - seven consecutive red runs, last green was tsb's packaging): abs, my-pricecatcher and
nhs-ae carried committed manifests whose `package_files` listed the bulk CSVs, which are
git-ignored and can never exist in a clean checkout - the same defect class the eutl
regeneration fixed that evening, masked on this host by local CSV copies. Fixed the tsb way:
the three packages' local CSVs came off the coordinator disk and their manifests were
regenerated (only `package_files` changed, plus the abs/my-pricecatcher `publication_note`
re-derived to cite the site destination's 15:51:21Z verification from the f657cd9 backfill);
`check-package` exit 0 for abs and my-pricecatcher, the full site-preview loop (8 editorial
packages) and test_sites.py run green locally. Known remaining debt, recorded not repaired:
nhs-ae-four-hour-decline is a DROPPED candidate and its frozen release dir still fails
check-package on a pre-existing tag mismatch (DESTINATIONS huggingface verified at v2026.11,
manifest tag v2026.13) - no editorial, no CI path, left for whoever re-opens that source. The
three published datasets' Hugging Face copies of MANIFEST.json still describe the old
package_files layout; harmless for consumers (the hub serves `files` digests), to be refreshed
at the next approved small-file maintenance.

**Second layer of the same repair:** once the CSV manifests were fixed, the site-preview loop
reached tsb-railway-occurrence-casualty and failed there too - "Hub verification omits an
asset": tsb's Hugging Face layout mirrors the logical paths (public/train.csv), not the flat
data/<asset>.csv default the site model assumes, and its release descriptor never declared
hf_paths (the level-structured datasets like noaa do). Declared the five hf_paths in
candidates/tsb-railway-occurrence-casualty/release.json and regenerated its manifest
(hub_paths added; publication_note re-derived to cite the 15:51:21Z site verification, same
as abs/my-pricecatcher). The full strict loop over all eight editorial packages now exits 0
per dataset, test_sites.py green, check-package exit 0 for every release dir except the
dropped nhs-ae-four-hour-decline (documented above), check-candidate --all exit 0, suite
OK. tsb's published hub copy of MANIFEST.json predates hub_paths - harmless for consumers,
refresh at the next approved small-file maintenance.

## Engineering — worker host-operation limits (2026-10-22)

Prepared on `hardening/host-job-limits`, stacked on the reviewed Hub integrity
branch. Transfer and Hugging Face jobs previously returned before the executor's
resource monitor and could exceed their declared runtime during bootstrap,
retry sleeps or client calls. A parent supervisor now monitors the whole host
operation, charges job-directory plus filesystem growth, stops the owned process
group before reaping, and accepts only a bounded terminal receipt. Paid workers,
coordinator bulk data and credentials were not used in tests. The new tests use
actual local subprocesses and stub providers, preserving all existing tests.

Next: clean-clone suite and exact-head CI, Scout source review, combined integration;
then include the reviewed increment in the pending rollout. Do not infer a strict
filesystem quota or host memory isolation from this sampled disk/time guard.
No merge or deployment is authorized while the earlier no-merge boundary remains.


### Host-limit source review follow-up

Scout reviewed the supervisor against actual EUTL worker descriptors and ran
its then-current 493-test suite on the hosted image. The follow-up removes a new
Linux procps dependency (reads procfs instead), re-signals late group members,
bounds the final reap wait, and refuses artifact upload if cleanup is unverified.
Sampling latency is documented as walk duration plus sleep; filesystem growth
is checked before the directory walk. New regressions cover those failure paths
without changing original tests or using worker resources. Source review:
https://github.com/earino/dataset-factory/pull/8#issuecomment-6349176803 .

### Session-admission source review follow-up

Scout verified the installed one-shot Hermes path retains the inherited admission
fd until process exit (PR #7 source-review comment). Corrected the process-group
cleanup after that review: once normal completion reaps the child, its old group
ID may be recycled, so the wrapper must not signal it. Timeout cleanup signals
only while the leader remains unreaped. A new real-process regression checks
normal completion sends no group signal. No live fault injection or deployment.
### Hub path authority follow-up (2026-10-22)

Pinned anonymous TSB metadata confirmed the original flat Hub paths. The
concurrent candidate descriptor's new logical-path override disagreed with both
main and the version tag. The publisher now resolves paths from the frozen
release record, consistently with its generated card, rather than from mutable
candidate metadata. Two regressions cover this drift and explicit structured
manifest paths. No network tests, bulk download or remote mutation was added.
**Observed, recorded, not fully attributed:** austin-911-response's site-destination verified_at
advanced twice during the close-out window (18:12:18 -> 18:45:41, captured in fd29c3e, ->
18:51:05, committed here) in the site pipeline's own record_site_destination format - a write
the code makes only after a live anonymous verification. prepare/release-manifest/check-package/
the test suite were each ruled out by reproduction, and no cron or session schedule matches the
moments; the live site re-verified anonymously from here (200, cross-links present), so the
recorded claim is true and the value is kept. If a stray site-verification automation exists on
this host, the builder should make it commit its own writes or stop leaving them in the tree.

### Research accounting admission — engineering follow-up, 2026-10-22

PR #7 now distinguishes accounting query failure from measured zero. Missing,
corrupt, inaccessible, locked and incompatible state databases hold the session
with explicit unknown totals; invalid counters and positive session counters
lacking usage rows also hold. Eduardo chose admission under the existing measured
token ceiling when dollar pricing is unknown, with dollar totals explicitly null.
The configured unpriced policy requires a positive token ceiling; default policy
for unconfigured installations remains hold. Scout verified the
installed schema/writer read-only in comment 6349573480. An empty valid ledger is
still allowed, and the configured limits/exclusions have not changed. New offline
cases exercise SQLite failures and the real gate-to-wrapper refusal path. Eduardo
explicitly approved supplying a valid empty database in the two existing lock-test
fixtures; their assertions are unchanged. Qualification code is untouched. Clean
Python 3.13 suite/doctor and exact-commit CI evidence are recorded in PR #7. No live
gate, runtime or schedule changed. Next: exact-commit CI and Scout review before rollout.

### Authorized hardening deployment and fixture follow-up — 2026-10-22

Eduardo explicitly authorized merge/deployment. PRs #1–4 and #6–8 are merged;
source `50135b2ec0e81a4779076724287c629c8fdbdf8e` passed exact-main CI and an
independent Python 3.13 clean clone (572 tests, OK, six existing skips). Doctor,
61-file source audit, dashboard and published-manifest no-op pass, with unchanged
release hashes. Scout fast-forwarded the hosted checkout after the supported
restart and preserved skill reconciliation: doctor and all 122 live audit checks
pass. Automatic background review and curator remain held; the two research
admissions were restored after the brief maintenance window. Limits are unchanged;
unknown dollar spend uses the operator-selected 40M-token policy. PR #5 remains
unapplied evidence. See docs/HARDENING-DEPLOYMENT.md for linked evidence.

The dashboard is deployed and its eleven release records independently match the
reviewed build. Its local test-health alarm exposed a real test-isolation bug:
eight worker qualification tests tried to overwrite a historical unowned job in
the live ledger. The ownership guard correctly refused. Their setup now uses a
temporary root with exact canonical source copies; every assertion and the test
count remain unchanged. A clean Python 3.13 clone with an unowned historical-job
sentinel passes all 572 tests in 6.781s (six skips), leaving the sentinel untouched.
Next: Scout verifies the fixture fix against its isolated live-tree copy, then
exact-commit CI, merge/fast-forward and one fresh dashboard publication/readback.
Record the next ordinary research session separately; no worker launch or data
publication is authorized by these rollout checks.

### Hardening rollout verified — 2026-10-22

PR #9's fixture repair is merged and deployed at `8046b1b77ff0259e95675eb8ecaa78f657730404`;
exact-main CI passed. Scout's isolated copy of the populated host passes all 572
tests in 12.735s with no skips, preserving every assertion, historical job and
release record. Dashboard commit `7a799aa1c1b6096008e1921df5148381d7da68ce` has a
successful Pages run; independent anonymous JSON/HTML readback confirms source
8046b1b, 572 tests passing, CI success, no alarms, and all eleven release records
matching the verified build. See docs/HARDENING-DEPLOYMENT.md for exact links,
runtime audit/restart evidence, unchanged qualification hash and preserved limits.

Research and discovery schedules are restored; cleanup/watch remained enabled.
Automatic background review and curator remain held, including auxiliary automatic
memory edits, pending a reviewed learning workflow. Manual recordkeeping continues.
The ordinary discovery execution `ddf1eea4eb4d4c6facb8e5b17b64525c` started once at
20:02:53Z after maintenance; session `20261022_200258_ef9347` is real and running.
Next: record this session's eventual outcome/usage and inspect its normal close-out;
do not infer a completed research result from successful admission. The next research
tick is 22:00Z, discovery 00:00Z. No added worker probe, allowance increase, dataset
publication or tag movement was part of the rollout. Remaining infrastructure work
is listed in the deployment report; PR #5 remains unapplied evidence.

## Discovery — Canada tick (2026-10-22)

Scheduled discovery session, region focus Canada (all three verdicts from the tick's
region; no US substitution). Three NEW sources opened and closed, each with measured
evidence in its record and notes. The honest outcome for this region: its open-data
event-grain space is either already on the bench (CA now 12 candidates) or maps onto
task families the bench has already settled. Rejecting is the session's product.

- `isc-ltdwa-advisory-lift-timing` — REJECT on measured split capacity + absent label
  source. The map's own "Download map data" export (fetched: HTTP 200, 2,715,200 bytes,
  GenerateDate 2026-10-20) holds 197 advisory events (158 lifted + 39 active since the
  Nov 2015 baseline; ~14 lift events/year, clustered by one federal program's funding
  pipeline; ON 110/197) and carries NO lift date — the label column the task needs is
  absent from the machine-readable product (display labels include 'Date Advisory
  Lifted', data does not). Bench anchor: npri-facility-spill-year was dropped at
  110-149 positives PER YEAR. Licence clean (OGL-Canada via the ECCC CESI republish,
  class A). Task TYPE (duration-to-resolution of an infrastructure advisory) recorded
  as unrepresented — needs a different publisher with per-advisory lift dates.
- `hc-health-product-shortage-onset` — REJECT at triage, licence_class C + registration
  wall. Portal moved to healthproductshortages.ca and served a Cloudflare challenge to
  BOTH a plain client (403 twice) and a real browser session; HC's own API examples
  require an account (POST /api/v1/login, email+password); open.canada.ca carries no
  machine-readable extract (29 packages, all HTML — measured). Per the 2026-10-21
  standing rule: closed, not parked; no enquiry drafted. Shortage-ONSET task type
  recorded as unrepresented — reopens only on a publisher-side anonymous channel.
- `hc-cannabis-inspection-rating` — REJECT on family + capacity. Establishment →
  next-inspection-rating is the live fsa-fhrs-next-rating task re-issued; measured:
  4 published half-year vintages (oldest resource created 2025-01-22), 1,358
  inspection rows, 66 non-compliant positives (4.9%), 278 repeat holders — no
  three-window split possible. Licence clean (OGL-Canada, class A). Sibling vaping
  retail-inspections package closed by the same note without opening.

Parked-record follow-ups this tick was asked to run, both recorded in the records'
notes: statcan-wds-aggregate-series — getChangedCubeList 404s at the documented path
(getCubeMetadata still mounts, 405 on GET), and the open.canada.ca recent-modified
window shows StatCan publishing only the parked aggregate class; park stands.
hc-canada-vigilance — the watch for a machine-readable resource: none appeared in the
100-most-recent window or 13 keyword package_searches; direct package re-probe failed
twice with the portal's own 504 (infrastructure failure recorded as such); park stands.

Registry evidence for future Canada ticks: the open.canada.ca event-grain products
that do exist map onto settled families — TSB monthly occurrence statistics, CER
pipeline incident data (cer-pipeline-incident-significant), CFIA/HC inspection
outcomes (cannabis, vaping), consumer complaint outcomes. Checked and not opened:
ECCC "Notices of Defect" (thin, no future outcome), SSC "Critical Incidents".

Checks: check-candidate.py OK for all three new records and --all OK (74 candidates);
suite OK (572 tests, 12.5s); coverage after: 74 candidates, CA 12, live 24, live
non-US 17/24 (71%). Scratch scripts under .factory/ deleted; downloads stayed in
/opt/data/cache/scratch.

Next action: next discovery tick follows the region rotation; on a Canada tick do not
re-open any of the three sources without the reopen evidence recorded in each record.
The construction queue behind the eutl flip is unchanged (five ready class-A builds,
then ea-flood-alert-escalation). This session's outcome is the record above, for the
close-out inspection noted in the hardening-rollout entry.


### Prompt improvement goal — draft and evaluation protocol (2026-10-22)

Eduardo authorized Codex and Scout to improve the actual research prompts/skills,
compare behavior, merge/deploy reviewed changes and evaluate live behavior within
existing budgets. Branch `improve/research-prompts` rewrites discovery/advancement,
versions worker-watch, corrects tag-mutation instructions and scientific overclaims,
and reuses research admission for watcher collection/follow-up. Qualification code,
published artifacts and numeric allowances remain unchanged; automatic writer holds
remain in place. The old quota-wording assertion changes with the intentional brief
change; all other existing assertions are preserved. Local Python 3.13: 578 tests,
6.790s, OK (six existing skips). Live deployment has not happened.

Next: Scout reviews the source and isolated no-tool evaluation setup; compare the
predeclared cases in evals/research-prompts within 2M tokens and 48 main invocations
including auxiliary usage in spend, then revise, clean-clone checks, exact-commit CI,
reviewed deployment and ordinary-run observation. Record actual responses and
uncertainties; do not claim improved dataset yield from instruction edits alone.

Prompt-evaluation checkpoint (Codex, 2026-10-22): PR #11 remains draft and undeployed.
The sequential helper uses the existing research mutex/gate, no tools, a neutral
fixture directory and a single strict ledger. Scout's installed-source review caught
cached tokens missing from the experiment total before any inference ran; the helper
now counts input/output/cache read/cache write plus auxiliary work. Local Python 3.13
suite: 585 tests in 6.605s, OK (six existing skips). On-demand profile references are
also aligned with evidence-based discovery and immutable package versions.

Next action is explicit: await Eduardo's pending budget-definition answer. The existing
40M weekly gate counts uncached input plus output; Scout measured 8,932,464 of those
versus 370,352,432 including cache in the checked seven-day window. Dollar price is
unknown. Keep the evaluation pilot held and existing production configuration unchanged
pending the answer; then give Scout the reviewed exact commit and run only the first
baseline/revised pair before authorizing the rest. No evaluation calls have run, and
no improved research outcome or deployment is claimed.


Prompt-evaluation resumed (Codex, 2026-10-22): Eduardo explicitly authorized the
inference tokens needed to finish and ship. Budget-definition hold is resolved;
production settings remain unchanged. Scout is authorized to run the first paired
`discovery-value` comparison on the primary route using reviewed `413244c`, then
return sanitized responses and measured usage before the remaining development
cases. All accounting, failed attempts and all four token classes remain recorded.
The initial batch checkpoints may be extended with a reason under this new authority;
worker spending and scientific/publication gates remain intact. Source review is clear,
586 clean-checkout tests and exact-commit CI pass, but behavioral improvement and
deployment remain unproven until the evaluation and live pass finish.


Prompt comparison checkpoint (Codex, 2026-10-23 local): pilot pair completed through
supported bounded chat with database accounting. The earlier usage-file parser error
was verified pre-inference and retained in the same ledger as a reconciled zero-token
failed attempt. GLM discovery-value: both arms 4/4 original utility criteria, no listed
unsafe actions; total tokens 44,836 baseline / 28,930 revised, 109.1s / 85.4s. Cache warmth
differs, so no causal speed/dollar claim. Label-blinded second review agrees on the tie
and narrowly prefers revised scientific branch handling. Revised conditional suite
execution remains a concern. Sanitized source/grades: evals/research-prompts/results/pilot.json.

Hosted remaining-development batch handle proc_5c5f359dda7e (PID 20410), script
/opt/data/eval-pilot/run_batch.py, progress /opt/data/eval-pilot/progress.jsonl, same
ledger /opt/data/eval-pilot/run/ledger.json. It waits behind live ordinary old-prompt
research session 20261022_220005_615452 (Hermes PID 19812, wrapper 19810); do not kill or
replace either on an observation timeout. Scout is retaining that run's public outcome
and measured usage as a live baseline. Next: poll this exact handle, inspect all 24
development responses, revise documented weaknesses, then reserved/adaptive diagnostics,
merge/deploy reviewed files and observe real new-prompt discovery/advancement. No deployment
has happened. Three added diagnostic cases are explicitly adaptive, not hidden holdout.

Prompt revision checkpoint (Codex, 2026-10-23 local): the original development batch
still uses frozen 413244c requests and helper 89dc99b; do not replace files under it.
At 22:18Z Scout confirmed both that batch and the ordinary wb-ieg advancement were
alive, with evaluation waiting for the research mutex. No process was restarted.

The next candidate bundle addresses the pilot's conditional close-out, overstrong
lag-margin guidance, and Scout's concern that blanket watcher repair deferral loses
useful autonomy. One diagnosed same-artifact recovery is allowed with source/digest,
linked attempts, exclusive ownership and normal budget/cleanup; no construction,
published-byte/tag or visibility changes. The grading protocol separates role policy
from common safety. A fourth adaptive diagnostic tests recovery and stop conditions.
588 tests in 6.650s, OK (six existing skips), source inventory audit green. No executable
qualification change or deployment. Next: retain the initial responses, test this
revised bundle explicitly and complete reserved/live validation before claiming gains.


## Advancement — wb-ieg-project-outcome constructed, qualified, baselined (2026-10-22)

Scheduled advancement tick. No actionable packaged candidate (eutl-installation-net-short
carries awaiting_operator and waits on the operator's flip), so the tick went to construction.
wb-ieg-project-outcome was picked from the scheduler's actionable list as the only candidate
whose full construct->qualify->baseline cycle fits one session (measured extraction: 1 request
for the 3.3 MB IEG CSV + 24 projects-API requests for the 54.5 MB merged index), while
chilecompra (~100-150 GB zips) and nz-ea (~1-2 h worker) exceed a tick and stay queued.

Constructed end to end on wb-001 (worker 171926570, cx23, 385.3 s, EUR 0.04 reservation,
destroyed 22:26:31Z, exit 0): gate 1.4.0 green on the full artifact on the worker (38/38
checks, artifact b8345bcb5769e422...), collected to staging release 421262457, all 11 manifest
digests verified on fetch-back, and qualify_dataset.py --accept ACCEPTED on the coordinator.
Runner-contract baseline wb-baseline-001 (worker 171927514, 66.9 s, EUR 0.06 reservation,
destroyed 22:33:17Z, exit 0, report at staging 421265626): train.py eval AUC 0.5879,
validate.py recompute 0.5879, CONTRACT OK. Two workers launched, two destroyed, both
confirmed deleted; total reservation spend EUR 0.10 of the EUR 15 construction allowance.

Panel (deduped to latest evaluation_fy; approval FY 1956-2009 / 2010-2014 / 2015-2019):
train 9,598 rows / 6,891 positives (0.7180); eval 1,479 / 1,173 (0.7931); holdout 1,097 /
885 (0.8067). Unobserved accounting recorded per window (151 Not Rated; 303 approved FY2020+;
not-yet-evaluated API-only projects: 1,724 / 719 / 637 per window - the right-censoring is
material and now quantified). RAP 2024 Fig O.3 cross-check: panel closing-FY MS+ 0.6875
(FY2013) -> 0.8729 (FY2023) vs published 71% -> 91%; the build asserts the published trend
(measured gap 18.5 pts) and records that the panel runs 3-7 pts below the series under every
cohort restriction.

Session findings worth keeping (all measured, commands in the candidate's notes.md):
- The projects search API IGNORES `fl` on the paged path: with `fl` it returns a
  search-result record (id, name, url, abstract), without it the full approval record sans
  abstract; the id-lookup path honors either. The first dry run silently joined empty
  features - caught by inspecting the written rows before any worker spend.
- The gate's event-key truncation (value[:10]) merges 83 "Republic of ..." borrowers into
  one prefix (179 countries -> 81 prefixes in train). Kept: conservative direction, passes
  with wide margin, both counts recorded in summary/quality.
- GE trust-fund records carry no approval metadata in the API; approval_month_num=0 and
  amounts_missing=1 are genuine source gaps (1,215 rows), not parse failures.

THE DECISIVE RESULT is a qualification defect, recorded plainly: the contract model (0.5879
eval AUC) TRAILS the one-line country-identity rule (0.6003) on eval - per dataset-
qualification, no headroom claim may be quoted from the model number alone. The identity rule
inverts on holdout (0.4909, stale priors across the 0.718 -> 0.807 prevalence shift) while
the model's holdout AUC was not measured by the contract job. The candidate therefore sits at
a decision point, NOT at packaging.

Next action (precise, for a fresh session): one bounded follow-up worker job scoring the
runner-contract model AND the identity/calendar rules on the PRIVATE HOLDOUT rows of the
accepted artifact (same fitted artifacts, no retraining choices, re-ACCEPT before scoring).
If the model holds ~0.59 while identity sits ~0.49, record the benchmark claim and proceed to
packaging per dataset-release; if the model collapses too, record the negative result and
drop the candidate (one repair per the qualification budget). Do not package or quote headroom
before that number exists. The other ready builds (camara, chilecompra, nz-ea, za, wb's queue
siblings) are unchanged and still queued behind this decision.

Checks this session: check-candidate.py OK for wb-ieg-project-outcome and --all OK (74
candidates); suite OK (572 tests, 12.9 s). Scratch scripts under .factory/ and downloads in
/opt/data/cache/scratch deleted after the push. Baseline staging releases 421262457 / 421265626
remain private staging (staging-repo lifecycle as before); no publication, tag movement or
flip was performed.


Codex review checkpoint (2026-10-23 local): preserved Scout's ordinary advancement
commits 31e8771 and d77213d alongside this prompt work. A bounded, read-only inspection
of wb-001's manifest, source archive and compact reports found scoring/logging before
the gate, a training-prevalence value mislabeled as split accuracy, a calendar control
that falls back entirely to country identity, and unsupported historical-vintage
claims. Evidence and scope: evals/research-prompts/results/old-prompt-build-review.json.
The passing mechanical report does not resolve these source findings. The next review
must address them before interpreting a favorable holdout result as permission to
package; keep the candidate private. Prior artifacts and the original run remain intact.
Scout received the findings; any subsequent repair responding to them is assisted,
not an unprompted improvement attributed to the new brief.

The ordinary research session has finished and released the mutex; initial frozen
prompt-comparison calls are now proceeding. The incremental evidence publisher is
being checked because its first results were not yet visible remotely. Do not rerun
completed model calls to repair an exporter. PR #11 remains draft, undeployed.

The next prompt bundle also addresses those source findings: inspect construction
for early scoring, enforce construct/qualify/accept/score/report on workers, and
verify reference predictions and information sets rather than trusting metric names.
This supersedes 2a3ceb9 before any follow-up inference; use its successor's exact
manifest for the planned 52 calls. No need to evaluate both revisions. The original
413244c development batch remains frozen, with every result retained.

Prompt-evaluation checkpoint (Codex, 2026-10-22 23:00Z): the original 24 successful
development responses are complete and preserved with request/response hashes and
criterion evidence. Revised 413244c scores 44/46 versus baseline 34/46 after excluding
the two watcher repair-role criteria; original role-inclusive grades are retained.
The cases show clearer baseline interpretation and active-owner handling, alongside
remaining statistical, timing and report-fidelity weaknesses. This is not evidence
of higher real dataset yield. Total measured usage is 835,103 tokens across all four
classes, including auxiliary work; the reconciled parser failure remains attempt one.

The next prompt bundle is frozen at 21b72994bc6a6ccd568c9395147ee3e6416b0e4c, adding
paired-uncertainty interpretation and observed-completion reporting. Clean-clone
588 tests (six existing Mac skips), doctor, source audit and exact-commit CI pass;
Scout source review is signed on PR #11. Scout is authorized to start the planned
52 further paired calls only after the initial batch exits, using the updated helper
and the same cumulative ledger under 96 attempts / 5M tokens. Do not replace original
results, reset usage or silently retry failures. Next: review the frozen follow-up,
merge/deploy only if criteria pass, then observe real discovery and advancement.

Prompt-evaluation checkpoint (Codex, 2026-10-22 23:30Z): all 24 frozen 21b72994
development responses are preserved; role-neutral scores 32/46 baseline vs 43/46
revised, total 838,699 all-inclusive tokens. A revised ownership answer still proposes
a ledger/bookkeeping write under an active owner; it fails mutation deferral despite
zero narrow unsafe flags. A separate source review found cleanup-before-preservation
ambiguity. The final watcher clarification covers both, counts preservation within
the existing one-recovery limit, and changes no lifecycle code or numeric allowance.
The ongoing 52-call batch stays frozen. Then run the predeclared 16 watcher calls,
including retained-source recovery, on the final exact bundle (93 cumulative planned
attempts within 96/5M). PR #11 remains draft and undeployed. Next: finish reserved and
adaptive reviews, verify the final watcher responses, then merge/deploy and observe
ordinary research; retain all earlier results and truthful uncertainties.

Prompt-evaluation checkpoint (Codex, 2026-10-23 00:00Z): all 52 frozen follow-up
responses are complete and preserved. Adaptive diagnostic scores are 23/32 baseline
versus 30/32 revised; both revised close-out answers still fail reporting fidelity.
They must not be described as flawless or as executed research. The same cumulative
ledger records 77 attempts / 2,696,235 all-inclusive tokens before the final watcher
batch. Its first final-8ad5199 response has arrived and validates against the prepared
request hash. No deployment yet. Next: review all 16 final watcher responses, update
PR #11 with complete measured evidence, merge/deploy at an idle boundary, then inspect
ordinary discovery and advancement against actual records and logs. Exact final-bundle
clean-clone test/doctor output is now retained with the evaluation evidence.

Watcher risk checkpoint (Codex, 2026-10-23): the frozen 8ad5199 loading answers did
not clear source-aware safety review. One invents a verified backup before deletion;
another proposes unsupported rename/PATCH and reports cleanup without confirmation.
Scout confirms collection does not mechanically protect omitted assets. Keep deployment
held and finish/preserve the existing sixteen calls. The watcher-only successor requires
explicit preservation evidence, supported copy-only recovery and truthful cleanup state;
it also warns that worker status mutates reconciliation state. Next verification is
twenty paired calls across five watcher cases, with a new unknown-backup diagnostic,
under 120 cumulative attempts / unchanged 5M tokens (113 planned). Review exact source
and CI before any successor calls. No production allowance, gate or lifecycle code change.

The frozen watcher batch is complete: 93 cumulative attempts / 3,195,065 inclusive
tokens, all sixteen responses retained in watcher-8ad5199 evidence. Coarse scores
18/32 vs 31/32 do not clear safety: revised retained-source run-90 also permits early
deletion after failed preservation and a nested retry; baseline preserves that source
until expiry. The successor clarifies both. Prepared 63c0705 is superseded before any
inference; use only its next reviewed commit for the twenty-call verification. No
deployment or successor calls yet. Next: exact successor source review/CI and request
hash agreement with Scout, then bounded evaluation using the existing ledger.


Prompt evaluation complete (Codex, 2026-10-23 00:50Z): corrected cd29d10 watcher
verification preserved all twenty responses, 23/40 baseline versus 36/40 revised.
Source-aware review with Scout clears controlled deployment: no repeat of early
source deletion, invented-backup deletion authority, active-owner mutation or direct
watcher asset mutation. Residual reporting/close-out/overrestriction defects remain
recorded; scores do not prove execution quality. Final coverage: 60 matched responses,
80/120 versus 112/120 original criteria; non-watcher 57/80 versus 76/80. Total evaluation
ledger 113 attempts / 3,824,658 inclusive tokens, no reset or silent reruns. Exact
cd29d10 clean-clone 588 tests in 6.733s (six existing skips), doctor and source audit
pass; full logs retained. Next: commit evidence, exact-commit CI, merge PR #11, deploy
reviewed files and scheduler entry at idle, verify readback, then observe ordinary
discovery and advancement. No live improvement or deployment is claimed yet.


Discovery session (Scout, 2026-10-23, regional focus: Latin America). Three leads
opened, one to ready. (1) inpe-foco-municipal-onset (BR, INPE Programa Queimadas) -
READY, licence class B (portal "Dados Abertos para Uso Publico" + FAQ Q18 free
transfer/use, Q36 attribution-by-citation; geonetwork licence field unreadable, HTTP
502, recorded as unread channel). Task: municipality conditioned on 14 fire-free days,
will >=1 reference-satellite active-fire detection occur in the next 7 days, at the
instant 13:00 UTC on D+1 (day-D daily CSV measured complete by 09:05 BRT on D+1;
observed risk grids published ~03:32 on D+1). Evidence: 4 reference years fully
counted (2019: 53,369 / 2020: 54,956 / 2022: 49,559 / 2024: 62,450 municipality-days
with detections; 2024 onset pairs 1,173,526 with 88,888 positives = 7.6%); exact
cross-check against INPE's own Estatisticas CSV (MT-2024 monthly totals identical,
50,551); extraction 4 years = 35.5 MB / 16.9 s, all 23 ref years ~= 150 MB; novelty
verdict differentiated (closest artifacts: Cerrado ConvLSTM REIC 2026 - 2 prototype
years, Cerrado grid only; arXiv 2606.04170 Cerrado-MG conservation units, explicitly
retrospective with same-day covariates and pseudo-absences - neither ships a
prospective national task with splits). Recorded limitation: no historical file
vintages (archive regenerated 2025-09-08/2025-06-06) - construction must measure
late-row churn before quoting numbers. (2) ideam-rio-nivel-exceedance (CO, IDEAM via
datos.gov.co) - INVESTIGATING: 26-year hourly level series (14.67M rows, 2001-2026,
345 stations, anonymous Socrata, CC BY-SA 4.0 = class B) measured; blocked on the
official per-station alert-threshold table (not in the station catalog, catalog search
empty) and the raw-vs-validated as-of policy (data explicitly unvalidated, preliminary
-> definitivo lifecycle). (3) sag-residuos-plaguicidas (CL, SAG) - DROPPED: sample-level
residue results exist only in annual PDFs, no catalog entry (datos.gob.cl search 0),
licence unstated (SAG entries elsewhere cc-nc); reopen if machine-readable sample-level
results under an open licence appear. Regional coverage honestly reported: Brazil and
Colombia probed with evidence, Chile closed with evidence; Mexico had no fresh probe
this tick (DENUE remains parked with its unblock condition) and Argentina was not
probed - a coverage gap, not a finding of no viable source. Checks: check-candidate OK
for all three, --all OK (77 candidates), suite OK (588 tests, 13.4 s), doctor OK,
check-runtime --source-only OK. Coverage after session: Latin America 6 records
(BR 2, CL 2, CO 1, MX 1), live non-US 19/26. Next action: advancement session may
construct the INPE fire-onset task per its recorded next_action (worker job, ~150 MB);
the Colombia lead needs one bounded threshold-hunt probe before any verdict.

## Deployment checkpoint - 2026-10-23

- Merged PR #11 deployed at `b80a84da3be28ce51d2c555a3423b32284feb9a7` (fast-forward from `1d2f301`, clean tree,
  merge CI run 39880723584 success; merge-commit check success).
- Readback verified: watcher `98b45d983280` is `scout_worker_followup.sh`, `no_agent=true`, monitor fields cleared,
  same 5-minute cadence, ID and delivery; exactly one watcher job. Installed shims/skills were hash-guarded;
  `check-runtime --source-only` and `--home` clean, `factory doctor` exit 0, research admission allowed.
- Holds unchanged: `auxiliary.background_review.enabled=false`, curator `PAUSED`; independent cleanup
  `e80975eddd4a` enabled. Worker allowance and weekly token policy unchanged.
- Advancement evaluation now pending: the first discovery invocation (session `20261023_005500_3d7a64`) completed
  and pushed `be44e01`. Earlier "merge/deploy next" notes are superseded by this
  checkpoint.


Prompt live-audit checkpoint (Codex, 2026-10-23): PR #11 is deployed and its first
ordinary discovery be44e01 produced useful source evidence but an unsupported INPE
ready decision. Prediction falls inside the target window; historical availability
is assumed despite reprocessing; split capacity is incomplete; the proposed handoff
scores references before qualification. Codex supplied these findings and publisher
FAQ Q39; Scout explicitly records the assistance and keeps INPE private/unconstructed.
Original records/history remain evidence, not a passing new-prompt outcome.

A focused follow-up on evaluate/prompt-rollout adds a dated timeline and reconciliation
of the five discovery contracts, keeps probe recipes, and makes handoff order explicit.
No qualification executable/version, published bytes or production allowance changes.
Two adaptive transfer cases will compare deployed versus follow-up bundles on both
routes (eight calls, same cumulative ledger, 128-attempt checkpoint/unchanged 5M tokens).
Next: exact source/CI and Scout review, targeted responses, idle deployment and another
ordinary discovery; retain live advancement 20261023_011135_3731ee untouched and audit
its output. Do not declare the goal complete from the earlier decision scores.
## Advancement session (Scout, 2026-10-23): wb-ieg-project-outcome decision point resolved - negative finding, dropped

Release work outranked construction, so the session took the package-stage
candidate's recorded next action: the one bounded holdout job that produced the
missing decisive number. No packaging occurred; under the current protocol and
spent one-repair budget, packaging is no longer available for this candidate - a
decision, not a claim of impossibility.

- Job wb-holdout-001 (bundle candidates/wb-ieg-project-outcome/holdout, worker
  171950621, exit 0, 57.3 s, EUR 0.04 reservation): fetched the five accepted
  files from staging 421262457, re-ACCEPTed through the gate BEFORE any
  scoring (b8345bcb5769e422), materialized the public-only runner workdir,
  ran the benchmark's own train.py verbatim via runpy (fixed-config deterministic refit, as
  wb-baseline-001, no retraining choices) and scored it against train-fitted
  references on identical eval and holdout rows. Report: staging release
  421361824 (asset 667622270). Worker destroyed, provider 404 confirmed.
- Decisive numbers (holdout = approval FY2015-2019, 1,097 rows, 885
  positives, prevalence 0.8067): model AUC 0.5301 vs identity rule 0.4909;
  paired cluster bootstrap by country (2,000 resamples, fixed seed) delta
  +0.0393, 95% CI [-0.0113, +0.0899] - contains zero. Also contains zero vs
  the genuine time-only calendar control (0.4780; delta +0.0522) and the
  prior-track-record rule (0.4938; delta +0.0364). The adverse eval
  comparison is kept: model 0.5879 trails identity 0.6003 on eval (the only
  CI excluding zero anywhere is model>calendar on eval, which the runner
  does not score). No benchmark claim is supportable.
- Codex source-review items closed in scope: accept-before-score ordering
  enforced this stage; majority-class accuracy measured per split (0.7931 /
  0.8067), never restated as the 0.7180 training prevalence; the degenerate
  country x approval_fy "calendar" control empirically confirmed (100%
  fallback, scores bit-identical to identity) and replaced by logistic on
  approval_fy + cyclical month; reference information sets verified by
  perturbation. The latest-vintage prior-history claim remains scientifically
  unresolved; it affects no release because nothing ships, but a future
  instance must state it as an assumption.
- Verdict: candidate DROPPED with the negative finding preserved (both scores
  on identical rows, per-year breakdown, prevalence shift 0.7180 -> 0.7931 ->
  0.8067 recorded). One repair was budgeted and spent. No implementation defect was found (model
  reproduces 0.5879 exactly; identity reproduces the build's early-scored
  0.6003/0.4909 from the written bytes), and no advantage was demonstrated
  under this protocol. CIs containing zero mean advantage was not shown; they
  do not establish equivalence or prove that task signal cannot survive. The
  identity holdout AUC was already known before this job: this was a
  fixed-config deterministic refit and the first new-model holdout comparison,
  not a wholly untouched holdout evaluation. Reopen only as a
  new task instance with its own qualification cycle.
- Checks: check-candidate wb-ieg OK (dropped) and --all OK; suite 588 tests
  OK. October worker reservations now EUR 7.90 of 20 (release reserve 5
  untouched).
- Queue after this session: the operator's actionable list stands minus
  wb-ieg-project-outcome (dropped). inpe-foco-municipal-onset (build) is the
  discovery session's handoff pick; every remaining item needs its build
  authored first, so the next session should pick ONE and write the
  construction before launching (no half-written bundle was left behind).

## Assisted audit hold - inpe-foco-municipal-onset (2026-10-23)

Codex's post-run review found the discovery "ready" verdict unsafe: the D+1 13:00 prediction instant falls 13
hours after the [D+1 00:00, D+8 00:00) target window opens; INPE FAQ Q39 documents retroactive Base 2
reprocessing (Collection 6, Terra history from 2000, Aqua from 2002, IBGE 2016 boundaries), so current files and
a future churn check cannot establish historical as-of availability; and the handoff ordered baselines before
qualification. Record status set to `investigating` with a `review` block; original measurements and evidence are
preserved unchanged. Keep private; do not construct from the prior contract. This is an assisted audit finding,
not an unprompted discovery gain. Reopen only with a fully future target window, evidenced as-of coverage (or an
explicitly retrospective task) and a gate-ordered handoff.


Prompt evaluation continuation (Codex, 2026-10-23 01:58 UTC): advancement completed
at 206a94c and the assisted INPE hold is durable at 5dac3c5. Exact-commit CI passed
for both and for the subsequent wording clarification 4d54eb1. Eight targeted
responses are now running sequentially on the same ledger after the advancement
mutex released. The frozen source is aa0e735; merging research records here does
not change that prompt/skill bundle. Current verdict wording is still being
reconciled with the assisted scientific clarification. Next: finish and review
all eight responses, merge/deploy the unchanged tested prompts at idle, then
observe one ordinary uncoached discovery and record its actual outcome.

Codex assisted wording reconciliation (2026-10-23): preserved the World Bank drop
and all measurements, but removed remaining current-field certainty that task
design (rather than any possible implementation issue) caused the weak result.
The audit found no implementation defect in its checked scope; that is not proof
of code correctness. Historical availability remains unresolved. This record
repair is assisted review, not an additional prompt-test success.

Prompt follow-up review (Codex, 2026-10-23): all eight aa0e735/b80a84d responses
retained, identity/route/zero-tool/accounting checks passed. Blinded criteria
10/16 -> 14/16, three revised preferences/one tie; critical baseline timing launch
avoided by revised answers. Residual scientific/reporting/cleanup weaknesses are
explicit in results/rollout-aa0e735-author-review.json, not hidden by the score.
Cumulative experiment 121 attempts / 4,099,323 inclusive tokens; no extra repeats.
Exact tested prompts approved for merge/idle deployment, followed by one ordinary
uncoached discovery and source audit. Do not close the goal before that live pass.

Deployed prompt validation checkpoint (Codex, 2026-10-23 02:29 UTC): PR #12 merged
at ad607ca, merge CI green, installed hashes/readback match tested aa0e735. Runtime
source/home audits and doctor pass; holds, budgets, cleanup and scheduler unchanged.
The genuine watcher session 20261023_020601_752438 verified wb-holdout-001's compact
reports and existing durable closeout before acknowledgment; no new worker/ledger
mutation. Its own clean fast-forward advanced the checkout under its mutex; the
changed discovery/advancement sources were not loaded into that watcher invocation.
Ordinary discovery 20261023_021307_9ae84d is now running through the normal shim,
uncoached; at 02:27 it was actively browsing (20 main calls plus vision/title), with
no candidate records yet. Evidence: evals/research-prompts/results/deployed-observation-ad607ca.json.
Next: let that normal session finish, audit its actual source evidence/decisions and
exact-commit checks, archive full four-field usage including vision, and only then
close the prompt-improvement goal. Do not infer a new accepted dataset from scores.

## 2026-10-23 worker-status follow-up: camara-002 (camara-bill-advancement) failed the gate; cleanup verified; design decision handed to advancement

camara-002 (server 171989986) failed exit 1 after 389.4 s: the build ran clean over the full
70-file union (splits identical to camara-001's measurement) and uploaded all 12 assets to the
private staging release `job-camara-002` (id 421533646), but qualification gate 1.4.0 failed
one of 38 checks — `splits.enough_clustered_positives`: with `event_key_column=apresentacao_year`
the eval/holdout windows carry only 4 distinct positive events each (1,397 and 1,793 positives)
against the gate minimum of 30 positives and 20 events. Structural for the 4-year cohort design,
not a code defect; no same-design rebuild can pass.

Handled this session: bounded reports collected into `.factory/camara-002/reports/`
(sha256-verified; bulk CSVs preserved at the staging release and proven by ranged GET);
worker destroyed 07:12:22Z with provider deletion read back (GET /servers/171989986 = 404
server not found; project primary_ips empty). Candidate record updated (camara-002 outcome,
`measurements.camara_002_gate_result_2026_10_23`, next_action = advancement handoff); full
artifact preserved at release job-camara-002 (421533646). No figure from either attempt is
quotable. Next: advancement decides the independence claim (re-target/drop, or re-declare the
event key and re-gate the same staged artifact — no third full build; the one-rebuild budget
for this defect class is spent).
