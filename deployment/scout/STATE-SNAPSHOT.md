# Scout operational snapshot

Observed 2026-10-22T17:13:44+00:00 on the hosted coordinator. Regenerate with `python3 scripts/scout-snapshot.py`; this file is written by that script, not by hand.

## Runtime

- Hermes Agent **v0.22.2 (2026.9.24)** (upstream `d923a5eb`), install `docker` at `/opt/hermes`, Python 3.14.7.
- Source: hermes --version. Full detail in `versions.json`.

## Schedules that exist now

| job | schedule | mode | next run | last |
| --- | --- | --- | --- | --- |
| scout-telegram-delivery-test (`1a66d6af21cc`) | `once in 2m` | agent | — | ok |
| scout-secondary-cleanup-sweep (`e80975eddd4a`) | `*/10 * * * *` | script-only (no model) | 2026-10-22T17:20:00+00:00 | ok |
| scout-weekly-research-digest (`10d4f73308c8`) | `every monday 8am` | script-only (no model) | 2026-10-26T08:00:00+00:00 | ok |
| scout-research-session (`69a5bc676d10`) | `0 2-22/4 * * *` | script-only (no model) | 2026-10-22T18:00:00+00:00 | ok |
| scout-budget-checkpoint-2weeks (`22ce870ec66f`) | `once at 2026-10-03 08:00` | script-only (no model) | — | ok |
| scout-worker-watch (`98b45d983280`) | `every 5m` | agent | 2026-10-22T17:18:37.416490+00:00 | ok |
| scout-discovery-session (`86fe52e55ef9`) | `0 */4 * * *` | script-only (no model) | 2026-10-22T20:00:00+00:00 | ok |
| rotate-scout-credentials (`e2ecb7c4564a`) | `once at 2027-01-18 15:00` | agent | 2027-01-18T15:00:00+00:00 | — |
| scout-dashboard-refresh (`4d8053a69ed2`) | `50 * * * *` | script-only (no model) | 2026-10-22T17:50:00+00:00 | error |
| scout-release-notify (`ba4c8610edf8`) | `55 * * * *` | script-only (no model) | 2026-10-22T17:55:00+00:00 | ok |
| scout-advance-now (`41b1f1d044e9`) | `once in 10m` | script-only (no model) | — | ok |
| scout-resume-chicago (`a9a3c0535165`) | `once at 2026-10-20 15:00` | script-only (no model) | — | ok |
| scout-finish-chicago (`72a7caf292a4`) | `once at 2026-10-20 16:40` | script-only (no model) | — | ok |

Source: /opt/data/cron/jobs.json (fields allowlisted; the delivery chat identifier is not exported). All times UTC; delivery is to the chat each job was created from.
Scheduled jobs run on the coordinator's own scheduler, independently of GitHub Actions.

## Budget (estimates, not the provider's quota)

- Research (model spend): allowance 30.0 USD per month from 2026-10-01, spend so far 0.233495 USD, sessions this week 40/200.
- Workers (compute): 84 jobs on file, 18.77 EUR reserved in total; active jobs: none.
- Provider resources live now: 0 servers, 0 primary IPs.
- Coordinator disk: `/dev/vdd         12G  9.1G  2.1G  82% /opt/data`.
- Sources: scripts/research-budget.py --json (Hermes usage records); jobs/*.json (the worker launch ledger; only one coordinator writes it); scripts/provider-inventory.py (live API); df -h /opt/data.

## Destinations and publication state

- **abs-visitor-arrivals-direction:github**: `earino/abs-visitor-arrivals-direction`, revision `v2026.10`, private=False, verified=True at 2026-10-22T13:49:39Z
- **abs-visitor-arrivals-direction:huggingface**: `earino/abs-visitor-arrivals-direction`, revision `v2026.10`, private=False, verified=True at 2026-10-22T13:49:39Z
- **abs-visitor-arrivals-direction:site**: `None`, revision `None`, private=False, verified=True at 2026-10-22T15:51:21Z
- **austin-911-response:github**: `https://github.com/earino/austin-911-response`, revision `v2026.09`, private=False, verified=True at 2026-09-19T15:00:00+00:00
- **austin-911-response:huggingface**: `earino/austin-911-response`, revision `v2026.09`, private=False, verified=True at 2026-09-19T15:00:00+00:00
- **austin-911-response:licensing**: `None`, revision `None`, private=None, verified=None at None
- **austin-911-response:site**: `None`, revision `None`, private=False, verified=True at 2026-10-22T15:52:11+00:00
- **chicago-doah-adjudication:github**: `https://github.com/earino/chicago-doah-adjudication`, revision `v2026.09`, private=False, verified=True at 2026-09-26T20:20:33+00:00
- **chicago-doah-adjudication:huggingface**: `earino/chicago-doah-adjudication`, revision `v2026.09`, private=False, verified=True at 2026-09-27T07:50:52+00:00
- **chicago-doah-adjudication:licensing**: `None`, revision `None`, private=None, verified=None at None
- **chicago-doah-adjudication:site**: `None`, revision `None`, private=False, verified=True at 2026-10-22T15:51:21Z
- **chicago-food-inspections:github**: `earino/chicago-food-inspections`, revision `v2026.10`, private=False, verified=True at 2026-10-20T21:55:26Z
- **chicago-food-inspections:huggingface**: `earino/chicago-food-inspections`, revision `v2026.10`, private=False, verified=True at 2026-10-20T21:55:26Z
- **chicago-food-inspections:site**: `None`, revision `None`, private=False, verified=True at 2026-10-20T22:05:01Z
- **msha-enforcement-citations:github**: `earino/msha-enforcement-citations`, revision `v2026.10`, private=False, verified=True at 2026-10-19T10:48:00+00:00
- **msha-enforcement-citations:huggingface**: `earino/msha-enforcement-citations`, revision `v2026.10`, private=False, verified=True at 2026-10-19T10:48:00+00:00
- **msha-enforcement-citations:site**: `None`, revision `None`, private=False, verified=True at 2026-10-19T11:05:00Z
- **my-pricecatcher-weekly-increase:github**: `earino/my-pricecatcher-weekly-increase`, revision `v2026.10`, private=False, verified=True at 2026-10-22T09:46:46Z
- **my-pricecatcher-weekly-increase:huggingface**: `earino/my-pricecatcher-weekly-increase`, revision `v2026.10`, private=False, verified=True at 2026-10-22T09:46:46Z
- **my-pricecatcher-weekly-increase:site**: `None`, revision `None`, private=False, verified=True at 2026-10-22T15:51:21Z
- **nhs-ae-four-hour-decline:github**: `earino/nhs-ae-four-hour-decline`, revision `v2026.13`, private=True, verified=True at 2026-10-21T21:43:43Z
- **nhs-ae-four-hour-decline:huggingface**: `earino/nhs-ae-four-hour-decline`, revision `v2026.11`, private=True, verified=True at 2026-10-21T21:43:43Z
- **noaa-tide-flooding:github**: `earino/noaa-tide-flooding`, revision `v2026.09`, private=False, verified=True at 2026-09-25T17:09:22+00:00
- **noaa-tide-flooding:huggingface**: `earino/noaa-tide-flooding`, revision `v2026.09`, private=False, verified=True at 2026-09-26T21:02:37+00:00
- **noaa-tide-flooding:licensing**: `None`, revision `None`, private=None, verified=None at None
- **noaa-tide-flooding:site**: `None`, revision `None`, private=False, verified=True at 2026-10-22T15:51:21Z
- **tsb-railway-occurrence-casualty:github**: `earino/tsb-railway-occurrence-casualty`, revision `v2026.10`, private=False, verified=True at 2026-10-22T09:05:57Z
- **tsb-railway-occurrence-casualty:huggingface**: `earino/tsb-railway-occurrence-casualty`, revision `v2026.10`, private=False, verified=True at 2026-10-22T09:05:57Z
- **tsb-railway-occurrence-casualty:site**: `None`, revision `None`, private=False, verified=True at 2026-10-22T15:51:21Z
- **who-flunet-activity-exceedance:github**: `earino/who-flunet-activity-exceedance`, revision `v2026.10`, private=False, verified=True at 2026-10-21T10:19:36Z
- **who-flunet-activity-exceedance:huggingface**: `earino/who-flunet-activity-exceedance`, revision `v2026.10`, private=False, verified=True at 2026-10-21T10:20:21+00:00
- **who-flunet-activity-exceedance:site**: `None`, revision `None`, private=False, verified=True at 2026-10-22T15:51:21Z

Licensing: code None, compilation None, source None.
Source: release/abs-visitor-arrivals-direction/DESTINATIONS.json, release/austin-911-response/DESTINATIONS.json, release/chicago-doah-adjudication/DESTINATIONS.json, release/chicago-food-inspections/DESTINATIONS.json, release/msha-enforcement-citations/DESTINATIONS.json, release/my-pricecatcher-weekly-increase/DESTINATIONS.json, release/nhs-ae-four-hour-decline/DESTINATIONS.json, release/noaa-tide-flooding/DESTINATIONS.json, release/tsb-railway-occurrence-casualty/DESTINATIONS.json, release/who-flunet-activity-exceedance/DESTINATIONS.json. **Public visibility on either platform still requires the operator's approval.**

## Queue and next action

- `abs-visitor-arrivals-direction` — published: PUBLISHED on GitHub, Hugging Face and the website; all verified anonymously.
- `air4thai-pm25-exceedance` — parked: If the operator wants a Thai air-quality task: (1) load the Envilink catalog page in a real browser, record the actual resource URLs and any per-dataset licence statement; (2) obtain written licence c
- `atsb-aviation-occurrence-triage` — dropped: None - closed. Reopens only if the ATSB publishes a bulk occurrence extract under an open licence (e.g. on data.gov.au with CC BY), which would re-vet as a new source.
- `austin-911-response` — published: Released and verified. Nothing outstanding for this release: further work would be a new release, not a correction to this one. CORRECTED 2026-09-26: the previous text still awaited the visibility aut
- `bmkg-earthquake-felt` — parked: Probe https://gis.bmkg.go.id/portal/dataapi for a historical earthquake catalogue with felt annotations; if none exists, ask the operator whether to start a 12-month collection loop on the live feeds 
- `bom-cyclone-best-track` — dropped: None - closed. Reopens only if (a) BoM puts a CC BY (or other redistribution-permitting) statement on the cyclone database's own page, or (b) a redistributor with a verifiable rights-holder grant (e.g
- `bvl-zoom-sample-positivity` — investigating: Construction (advancement session): read the Datensatzbeschreibung PDF column-by-column and pin every feature's documented meaning; write source/build.py (three year zips -> Campylobacter frame -> run
- `camara-bill-advancement` — ready: Advancement session constructs: (1) worker downloads proposicoes-YYYY.csv 1991-2025 plus proposicoesAutores-YYYY.csv, unions by id, filters cohorts by dataApresentacao, asserts id uniqueness; (2) fetc
- `cer-pipeline-incident-significant` — parked: Parked. Unpark only if: (1) a formulation is wanted that ships the company's initial notification free text with verified timing (the comprehensive file's 'Detailed what happened' is likely post-inves
- `cfpb-complaint-relief` — dropped: None - dropped on novelty (2026-10-19). Do not reopen for outcome prediction from intake-time fields. Reopening would only make sense for a materially different task (e.g. cross-firm panel analysis ra
- `chicago-doah-adjudication` — published: Released. Both destinations are public and verified from an unauthenticated client, the site is live and verified, and tag v2026.09 resolves to the same commit as the default branch on both. Remaining
- `chicago-food-inspections` — published: PUBLISHED 2026-10-20T21:55:35Z - GitHub (public repo earino/chicago-food-inspections, tag v2026.10, release 418734355, 201/201 assets) and Hugging Face (public, 213 files, tag v2026.10) verified anony
- `chilecompra-tender-outcome` — ready: Advancement session constructs: (1) worker job fetches the monthly zips for the three windows (~100-150 GB - size the worker disk, stream-extract per month, keep publication-stage tender fields + awar
- `companies-house-company-exit` — parked: None. Parked permanently unless a free historical dissolution feed appears.
- `cpcb-aqi-exceedance` — dropped: None - closed on licence grounds. Re-open only if CPCB publishes its own explicit reuse licence.
- `cra-charity-filing-exit` — investigating: GO to construction (advancement session owns it). Construction step: on a worker, download the per-year Identification + Financial + General (+ Programs/Compensation/Foundations as decided) packages f
- `defra-aurn-pm25-exceedance` — dropped: None. Re-opened only by a genuinely different task formulation on AURN data (not day-ahead concentration or exceedance forecasting), with the site back online and its licence read from the publisher's
- `defra-la-household-recycling-rate` — parked: Parked. Unpark only if one of these becomes true: (1) a finer-grain export channel opens (WasteDataFlow quarterly exports at LA grain would make movement measurable at sub-annual scale - check whether
- `denue-establishment-exit` — parked: Unpark conditions (any one): (1) a verifiable archive of >=4 historical DENUE editions appears on an INEGI download channel - probe with the PK-magic check, never HTTP status (this publisher soft-404s
- `dvsa-mot-next-test-outcome` — investigating: GO to construction (advancement session owns it). Construction step: on a worker, download per-year results and failure-item zips for the chosen window (2010-2024), sort by (vehicle_id, test_date, com
- `ea-bathing-water-classification` — investigating: GO to construction (advancement session owns it). Construction step: pull the 11 season slices 2015-2025 via the measured compliance-rBWD endpoint (~2.5 MB total, coordinator-class is fine), pull wate
- `ea-flood-alert-escalation` — investigating: Construction (worker build, class A): write candidates/ea-flood-alert-escalation/build_panel.py - (1) fetch Historic_Flood_Warnings.zip (3.6 MB, 1 GET) and both registers via WFS properties-only (9 re
- `ec-tdi-case-outcome` — parked: PARKED on an access blocker, not on licence or task novelty. The unpark question, exactly: does DG TRADE expose the case register through a documented anonymous channel (public API, bulk export, or ma
- `eccc-hydrometric-daily-flows` — dropped: Dropped. Do not re-open while CAMELS-SPAT and HYSETS remain downloadable. A genuinely different formulation (e.g. real-time flood-warning verification against ECCC's own issued warnings - a warnings-o
- `ecdc-atlas-surveillance` — dropped: None for this record (terminal). Do not re-probe ECDC surveillance for activity-exceedance tasks; the flunet prior art settles them. If a future ECDC product publishes event-level data with an anonymo
- `eea-uwwtd-plant-poor-performance` — investigating: Construction (advancement session), in order: (1) pin the public cycle inventory - probe each tabular cycle's record/share link (2007-2008 v01 ... 2019-2020 v08/v09) and fall back to the spatial plant
- `efsa-one-health-sample-prevalence` — dropped: Terminal for now. If and only if bvl-zoom-sample-positivity reaches publication and a second geographic instance is wanted, open a fresh candidate on these Zenodo records (the 36 record ids and file s
- `eutl-installation-net-short` — qualified: Packaging per the dataset-release skill: package the accepted eutl-001 artifact (staging release 420810883, artifact 3540ad2180d8df8a...) with license.json (Commission CC BY 4.0 source terms preserved
- `faa-wildlife-strike-damage` — dropped: None - dropped on novelty (2026-10-19). Do not reopen for damage prediction from pre-strike strike-report fields. A re-open would need a materially different task on this source (e.g. something about 
- `fsa-fhrs-next-rating` — dropped: None. Re-open only if the FSA begins publishing per-establishment rating history or dated snapshot vintages of the FHRS/FHIS extracts (check ratings.food.gov.uk/open-data and the API schema for histor
- `hc-canada-vigilance-adverse-reactions` — parked: Parked. Unpark only if Health Canada publishes a machine-readable export of Canada Vigilance (watch the two open.canada.ca packages for a CSV/API resource appearing, e.g. on the next Canada tick), or 
- `hc-recalls-classification` — dropped: None - dropped. Do not reopen for any recall-classification formulation; if someone proposes a genuinely different task on this source (not hazard-class prediction), open a new candidate with a novelt
- `hk-datagov-portal` — parked: Unpark only by operator decision, same shape as the Singapore catalog park: (a) accept a second own-history environmental-exceedance family member (cleanest candidate: WSD Storage Position of Impoundi
- `id-ojk-bank-supervision` — parked: Unpark steps, in order: (1) load https://data.ojk.go.id/SJKPublic in a real browser, capture the exact XHRs (URL, method, headers, cookies) the app issues for a per-bank SPI table, and measure whether
- `imd-station-observation-series` — parked: Unpark steps: (1) probe dsp.imdpune.gov.in and mausam.imd.gov.in from a worker in another network region and enumerate the free products (if any station-level series are free, this reopens); (2) other
- `india-datagovin-portal` — parked: Unpark path: (1) from a Hetzner worker (EU/US network), probe https://data.gov.in and api.data.gov.in; if reachable, enumerate the API-enabled datasets via the catalog API and shortlist task families 
- `indonesia-bps-webapi` — dropped: None - dropped. Re-open only if BPS starts publishing register-level or event-level data through the Web API (contrary to its statistics mandate), which is the steady state working against that ever h
- `itu-datahub-ict-panels` — dropped: None - closed on task-shape and mirror grounds. Re-open only if ITU ships a row-level or event-level product (the satellite-filings registry in the Radiocommunication sector is the only such candidate
- `jma-typhoon-rapid-intensification` — dropped: None - terminal. Recorded so a future tick does not re-open JMA blind: the other JMA families are also family-level duplications of candidates already on the bench - JMA earthquake felt-intensity dupl
- `kenya-opendata-knbs` — parked: Unpark question (exact): does any KNBS-published channel offer anonymous bulk/API access with stated licence terms? Concretely, probe in this order: (a) a KNBS microdata/NADA catalogue (IHSN family) -
- `kr-kosis-kma-access` — parked: Unpark by operator decision: register a KOSIS account, obtain an OpenAPI key, and store it as a mode-0600 credential file under /opt/data/.secrets (the existing convention); then open a candidate on a
- `malaysia-river-danger-exceedance` — parked: Unpark steps, in order: (1) load https://publicinfobanjir.water.gov.my/trend-hujan-aras-air/?lang=en in a real browser, pick a state/district/station and a date range, and capture the exact XHR the pa
- `md-sewer-overflow` — parked: Narrowed 2026-09-23 by the registry probes: a roster exists (EPA npdes_downloads.zip, 336 MB, anonymous and ranged-readable; Maryland's own rosters are partial - 76 major POTWs, 829 point sources, cov
- `melbourne-pedestrian-counts` — dropped: None - closed. Re-open only if Melbourne publishes an explicit data licence.
- `msha-enforcement-citations` — published: PUBLISHED 2026-10-19. Both data destinations were flipped to public after the operator asked for the dataset to be taken over the line, and both were then verified with no credential in the environmen
- `my-pricecatcher-weekly-increase` — published: PUBLISHED on GitHub, Hugging Face and the website; all three verified anonymously. No further action.
- `nhs-ae-four-hour-decline` — dropped: None - dropped. Re-open only if a task is found on this source whose label is not dominated by persistence or seasonality, and only with a publication-date archive.
- `noaa-tide-flooding` — published: The release is public and verified; what remains is documentation-only and touches no asset byte. In order: (1) DATA_DICTIONARY.md's label row still names the column `late` where the shipped target co
- `npri-facility-reporting-exit` — investigating: GO to construction (advancement session owns it). Construction step: on a worker, download the bulk releases CSV (az.ec.gc.ca api/file path, ~393 MB) plus geolocations, or the per-year single-year CSV
- `npri-facility-spill-year` — dropped: None - dropped on measured capacity. Revisit only if the exit task's construction reveals the spill signal is needed as a feature, in which case it is a column of the exit task, not a task of its own.
- `nrw-historic-flood-warnings` — dropped: None now. If a second instance of the escalation task is wanted after ea-flood-alert-escalation ships: (1) verify NRW publishes a warning-area -> alert-area linkage equivalent to the EA register 'pare
- `nws-tornado-warning-verification` — investigating: GO to construction (advancement session owns it). Construction step: per-year cow.json pull 2008-2024 with phenomena=TO&significance=W (17 requests, measured 20-28 MB / 40-60 s each on this host class
- `nz-ea-wholesale-price-exceedance` — ready: Construction on the worker: (1) enumerate the 728 files via the container listing, download all monthly+daily price files (or stream and aggregate), join POC->Island/Network-reporting-region via the N
- `oecd-sdmx-aggregate-family` — dropped: None - closed on task-shape grounds with the probes recorded; the licence is clean (class A) so a future session need not re-check it. Re-open only if the OECD ships a row-level product that is neithe
- `ons-la-claimant-count-direction` — parked: Parked. Unpark question: does ONS publish (or begin publishing) an open, redistributable dataset at event or case grain with a documented schedule - e.g. business demography at firm grain, an open ins
- `openfda-food-recall-classification` — dropped: None - dropped on novelty (2026-10-19). Do not reopen for classification triage from initiation-time fields. If a need ever arises in this family, it must be a different task (e.g. predicting *termina
- `ph-pagasa-climate-station-data` — parked: Unpark question, exact: does PAGASA (or a successor portal such as PhilDA relaunched, or the GeoRisk PH platform) ever publish historical station observations anonymously and bulk-downloadable with re
- `philippines-psa-openstat` — dropped: None - dropped. Re-open only if PSA publishes a register-level or event-level dataset on OpenSTAT (e.g., establishment registers with outcomes); its statistics mandate makes aggregate-only the steady 
- `saps-station-crime-quarter` — parked: Unpark question (exact): written licence confirmation from SAPS (via the saps.gov.za contact/feedback channel) permitting redistribution of derived station x quarter x crime-category tables, including
- `singapore-datagov-catalog` — parked: Unpark path (a decision, not a re-probe): the operator names which, if any, family to accept - (a) Singapore rainfall exceedance (access/licence settled, extraction measured at ~63M rows for 2016-2024
- `statcan-wds-aggregate-series` — parked: Parked. Unpark only if an open case/event-grain StatCan release appears (per-month incident- or record-level data with a documented schema, no registration wall) - check the WDS getChangedCubeList end
- `tsb-railway-occurrence-casualty` — published: PUBLISHED 2026-10-22T09:05:57Z - GitHub public (v2026.10, 5/5 assets digest-verified anonymously), Hugging Face public (16 files), site live at earino.github.io/tsb-railway-occurrence-casualty. Baseli
- `tw-reservoir-drought-storage` — parked: Unpark only if (a) the routine seeds a standing snapshot collector (fetch 45501/41568 daily, one row per major reservoir, into the private staging; splits become usable after ~2-3 typhoon/drought cycl
- `tw-typhoon-day-closure` — investigating: Construction (coordinator-side scripts first, then worker): (1) PIN THE MODERN-ERA LABEL EXTRACTION - try DGPA daily-view query variants (the server-rendered /typh/daily/nds.html answers per-county st
- `unhcr-refugee-data-finder` — parked: Unpark question (exact): can the RDF population CSV be fetched by a non-interactive client - a documented export URL, an API, or a fetch pattern that passes the WAF from a Hetzner worker IP? Concretel
- `unicef-sdmx-refugee-origin-growth` — parked: Unpark condition (exact): a machine-fetchable richer grain of the same phenomenon - UNHCR RDF's monthly asylum applications or host-country x origin population series - at which point the task should 
- `unodc-data-portal` — dropped: None - closed on licence grounds. Re-open only if UNODC attaches an explicit open licence (e.g. CC BY 3.0 IGO) to the data portal or a named dataset; no permission email, no waiting, per the standing 
- `vietnam-nso-publications` — parked: Unpark path: (1) identify the current machine-readable channel, if any - probe from a worker for Vietnamese-language data sections (XLSX monthly releases), and watch for a relaunch of data.gov.vn or a
- `wb-ieg-project-outcome` — ready: GO to construction (advancement session owns it; this was a discovery-only session). Construction steps: (1) snapshot the IEG CSV and the Projects API pages with hashes and record the as_of_date; (2) 
- `who-flunet-activity-exceedance` — published: PUBLISHED 2026-10-21T10:24:48Z - GitHub public (tag v2026.10, 5/5 assets digest-verified anonymously), Hugging Face public (license field 'other', 15 files), site live. Licence unresolved and stated i
- `za-municipal-audit-opinion` — ready: Construction (worker): (1) verify the exact MFMA statutory AFS-submission deadline wording (s127 area) and pin observed AGSA release dates per label year, including the FY2023-24 tabling date; (2) sna

Source: candidates/*/record.json. The newest section of `STATE.md` carries the narrative.

## Recovery notes

- Reconcile before resuming: read `jobs/*.json` for non-deleted jobs and check the provider inventory above. Do not launch a second coordinator or re-run a job whose record says `running`.
- The worker allowance is counted from `jobs/*.json`; deleting records to 'tidy up' would reset that accounting. Records are evidence, not scratch files.
- Secrets are supplied at run time (dashboard environment or mode-0600 files under `.secrets/`); nothing here references a value. See `deployment/scout/README.md`.
