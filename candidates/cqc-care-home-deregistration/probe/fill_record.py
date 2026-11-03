#!/usr/bin/env python3
"""One-shot record fill for cqc-care-home-deregistration (UK discovery tick 2026-11-03).

Writes every discovery measurement into record.json from this session's probes.
Re-run is idempotent (overwrites the fields it owns).
"""
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RECORD = HERE / "record.json"

r = json.loads(RECORD.read_text())

r["status"] = "ready"
r["domain"] = "adult social care regulation / 12-month register-exit (deregistration) prediction"
r["prediction_question"] = (
    "For a care home location active on the CQC register at monthly vintage T "
    "(the 'HSCA Active Locations' file produced on that date), will the location's "
    "registration end within the following 12 months (Location Status Inactive-Dereg "
    "with a Location HSCA End Date inside (T, T+365d])?"
)
r["prediction_time"] = (
    "The production instant of a monthly CQC 'HSCA Active Locations' vintage "
    "(Europe/London; the date in the file name, e.g. '05 January 2024 HSCA Active "
    "Locations'; the weekly sibling CSV states 'This data was produced on <date>' - "
    "the same stamping convention). Features are the vintage's own columns only: "
    "HSCA start date, care home beds, service types (with/without nursing), service "
    "user bands, latest overall rating + its publication date (measured as-of: "
    "0/14,765 care-home rows at T=2024-01-05 carry a rating publication date after T), "
    "geography, provider attributes incl. Companies House number. Target = the "
    "register event dated after T, read from the cumulative Deactivated Locations "
    "product. Archive: monthly vintages 2011-2026 (Drive year folders, anonymous)."
)
r["target_definition"] = (
    "Binary: Location HSCA End Date in (T, T+365d]. Label source: CQC Deactivated "
    "Locations file (cumulative; Location HSCA End Date + Location Status; among "
    "care homes all-time: 17,046 Inactive-Dereg vs 131 Removed). Label-source columns "
    "never ship as features. Censoring: instants whose 12-month window extends past "
    "the deactivated file's coverage (2026-11-02 edition) are excluded. FRAMING: the "
    "target is the register event (deregistration of the location), which CQC notes "
    "can include services continuing under a new registration; not necessarily "
    "service cessation - see verdict.uncertainty."
)
r["sources"] = [
    {
        "name": "CQC care directory with filters - 'HSCA Active Locations' (monthly bulk file, all active regulated locations, care home beds, service types, service user bands, latest rating + publication date, provider attributes)",
        "url": "https://www.cqc.org.uk/about-us/transparency/using-cqc-data",
        "api": "current: https://www.cqc.org.uk/system/files/2026-11/02_November_2026_HSCA_Active_Locations.ods ; archive: Google Drive folder 1Y6V6r-q2l4lJYKuZL0DXw25VDUTH6L4N (year subfolders 2011-2026, monthly files, anonymous embeddedfolderview listing + usercontent download)",
        "access": "anonymous; measured 2026-11-03 (26-28 MB per file)",
        "licence": "Open Government Licence v3.0 (publisher's using-cqc-data page)",
    },
    {
        "name": "CQC Deactivated Locations (monthly bulk file, cumulative register of archived locations with Location HSCA start/end dates, Location Status, beds at deactivation, last rating + publication date, provider attributes)",
        "url": "https://www.cqc.org.uk/system/files/2026-11/02_November_2026_Deactivated_Locations.ods",
        "api": "same monthly product line; one current file carries the whole event history back to 2010-08-05",
        "access": "anonymous; 27,644,723 bytes measured 2026-11-03",
        "licence": "Open Government Licence v3.0 (using-cqc-data page + in-sheet statement)",
    },
    {
        "name": "CQC care directory with ratings (monthly bulk file, service-level latest ratings; archive from 2015)",
        "url": "https://www.cqc.org.uk/about-us/transparency/using-cqc-data",
        "api": "current: https://www.cqc.org.uk/system/files/2026-11/02_November_2026_Latest_ratings.ods ; archive: Drive folder 1N9JH4DhoKvb5SO6I9ObqRmhPgxD_m_pS",
        "access": "anonymous; optional deeper rating history for construction (pre-Sep-2023 archive files have missing core-service ratings per publisher)",
        "licence": "Open Government Licence v3.0",
    },
    {
        "name": "CQC care directory weekly CSV (locations census only; no beds/ratings)",
        "url": "https://www.cqc.org.uk/system/files/2026-10/28_October_2026_CQC_directory.zip",
        "api": "weekly product line, archive from 2012",
        "access": "anonymous; 4,401,747 bytes measured 2026-11-03",
        "licence": "Open Government Licence v3.0",
    },
]
r["license_evidence"] = [
    "https://www.cqc.org.uk/about-us/transparency/using-cqc-data (read 2026-11-03): 'Our data is made available under the Open Government Licence [link: nationalarchives.gov.uk/doc/open-government-licence/version/3/]. By using it you are accepting the conditions of this licence. If you use our data, you should also acknowledge on your site or service that you are using CQC information.'",
    "In-sheet statement inside the Deactivated Locations ODS itself (2026-11-02 edition, read 2026-11-03): 'the data we have provided can be used in accordance with the Open Government Licence for Public Sector Information by acknowledging CQC as the data source' plus the disclaimer that CQC 'does not however hold any responsibility for subsequent analysis done from raw data provided as this is seen as creating new information; CQC should not be quoted as the source of the analysis and/or interpretation'.",
    "https://www.cqc.org.uk/about-us/our-policies/terms-conditions (read 2026-11-03): CQC copyright-protected material published on the site 'may be used in accordance with the Open Government Licence for Public Sector Information'.",
    "No dataset-specific restriction found on any product page; the bulk files are register data only (no third-party content).",
]
r["licence_class"] = "A"
r["licence_note"] = (
    "OGL v3 per the publisher's own instruments. Attribution 'Care Quality Commission' "
    "carries into any release; the in-sheet disclaimer (CQC not responsible for "
    "subsequent analysis; must not be quoted as its source) is carried into the "
    "dataset documentation."
)
r["jurisdiction"] = {
    "country": "GB",
    "region": "Europe",
    "publisher": "Care Quality Commission (CQC) - regulator of health and adult social care in England",
    "recorded_at": "2026-11-03",
}
r["split_strategy"] = (
    "Annual January instants with non-overlapping 12-month target windows. Proposed: "
    "train instants Jan 2016-2019 (targets 2016-2020), eval Jan 2020-2021 (targets "
    "2020-2022), holdout Jan 2022-2024 (holdout target windows end by 2025-01, fully "
    "observed by the 2026-11-02 deactivated file). Instants 2011-2015 are usable for "
    "train with the pre-Oct-2014 no-ratings caveat; instants 2025+ are excluded while "
    "either the deactivated file's coverage or the publisher's migration-related "
    "cancellation lag is unresolved. Exact per-instant positives are the first "
    "construction measurement; measured anchor: T=2024-01-05 carries 14,765 eligible "
    "care homes and 758 positives (5.13%)."
)
r["measurements"] = {
    "archive_depth_measured": "monthly 'HSCA Active Locations' vintages 2011-2026 (2019 files .xlsx, 2024+ .ods; 12 per year), 'with ratings' archive 2015-2026, weekly CSV archive 2012-2026; all anonymously listable and downloadable from Google Drive (embeddedfolderview + drive.usercontent download); Drive year-folder IDs and one 2024 file ID recorded in probe/cqc_drive_*.py",
    "population_measured": "weekly CSV produced 2026-10-28: 57,123 active locations; care homes today 15,477 (10,380 Residential homes + 4,497 Nursing homes), all 9 English regions; care homes at T=2024-01-05 vintage: 14,765",
    "label_events_measured": "Deactivated Locations 2026-11-02: 65,830 archived locations, of which 17,177 care homes (Care home?=Y); care-home deregistrations by HSCA end year 2011..2026 = 1656, 1649, 1063, 1227, 1245, 1381, 1352, 970, 949, 822, 967, 803, 827, 768, 801, 697(partial-year); earliest care-home end date 2011-01-19 (earliest overall 2010-08-05); status mix: 17,046 Inactive-Dereg, 131 Removed",
    "prevalence_measured": "T=2024-01-05: 758/14,765 care homes deregister in (T, T+365d] = 5.13%; 2,076 of the 14,765 deregister by 2026-11-02 - label fully observable, no censoring at that instant",
    "clustering_measured": "deregistrations spread across 376-877 distinct providers per year; largest single provider holds 3-12% of a complete year's events (max 74/1656 in 2011, 102/1649 in 2012, 97/697 in the partial 2026); top-3 provider share <= 12.2% in every complete year - mild provider clustering, positives independently numerous",
    "asof_measured": "0/14,765 care-home rows in the Jan-2024 vintage carry a rating Publication Date after T=2024-01-05 - the vintage's ratings are genuinely at-T",
    "feature_availability_measured": "vintage header (118 real columns): Location ID, Location HSCA start date, Care home?, Care homes beds, Registered manager, Location Latest Overall Rating + Publication Date + Inherited Rating flag, geography (region/NHS region/LA/CCG/constituency, lat-long, postcode), Provider Companies House Number, Provider Charity Number, Provider ID/name/type-sector/HSCA dates, 32 Service type Y/N columns (incl. Care home service with/without nursing), 12 Service user band Y/N columns (incl. Dementia, Older People, Learning disabilities). No Location Status column (all rows active by construction)",
    "cost_measured": "discovery: 4 anonymous GETs, 85.9 MB total (4.4 + 27.6 + 26.1 + 27.7 MB), seconds each; construction (January instants): ~10-15 vintage files (~26 MB each, ~390 MB) + 1 deactivated file, worker download, Drive per-file IDs enumerated from year folders; ODS parse ~60 s/file on 4 vCPU warm (one cold run under concurrent I/O took >15 min and was killed - worker sizing should budget generously)",
    "rating_signal_measured": "last overall rating at deactivation (care homes): Good 5,992, blank 7,698, Requires improvement 2,318, Inadequate 1,027, Outstanding 138 - Inadequate is 6.0% of deactivations vs a low single-digit share of the active stock; beds at deactivation small-home-dominated (modes 3-10 beds) - both match the publisher's State of Care closure profile",
    "cross_checks": "CQC/DHSC operational-effectiveness review (June 2024 snapshot): 29,108 social care organisation locations, 23,951 with published ratings vs 57,123 total locations / 15,477 care homes measured here (2026-10-28) - consistent magnitude and mix; BMJ Public Health 2024: 29,548 care homes existed 2011-2023 with 8,346 COMPLETE closures vs 14,911 register events measured here over the same span (the gap = their linkage-filtered subset vs raw deregistrations, per their methodology note); CQC State of Care 2016 small-home closure profile matches the beds-at-deactivation distribution",
    "known_event_fixture": "dated worked example in notes.md: Park Hills Nursing Home (1-113831768, Oldham, 17 beds, HSCA start 01/02/2011, Good published 26/08/2022) present at T=2024-01-05, Location HSCA End Date 01/02/2024 inside the window -> label 1; Henley House (1-10000302982, Suffolk, 66 beds) present at T, absent from the deactivated file as of 2026-11-02 -> label 0; Options Hazel House (end date 05/03/2025, outside the window) -> label 0 at T",
    "measured_on": "2026-11-03, anonymous coordinator-side probes; scripts + outputs in candidates/cqc-care-home-deregistration/probe/ (sha256 of fetched files in notes.md)",
}
r["verdict"] = {
    "status": "ready",
    "contracts": {
        "redistribution": "supported - OGL v3.0 from the publisher's own instruments (using-cqc-data page, in-sheet statement, T&C page; licence_class A); no dataset-specific restriction; attribution and the in-sheet analysis-disclaimer carry to any release",
        "prediction_timing": "supported - monthly vintages 2011-2026 with production-date stamps; features vintage-visible; as-of measured (0/14,765 rating publication dates after T); dated worked example with real named homes on both label sides in notes.md (T = 2024-01-05, Europe/London)",
        "obtainable_target": "supported - Location HSCA End Date + Location Status from the cumulative Deactivated Locations file (whole event history back to 2010 in one product); label-source columns excludable; censoring policy stated; 'Removed' separated from 'Inactive-Dereg' (17,046 vs 131)",
        "split_capacity": "supported - measured per-year care-home deregistrations 697-1,656 every year 2011-2026 with a 5.13% measured prevalence at T=2024-01-05; proposed train/eval/holdout instant windows each carry thousands of eligible homes and hundreds of positives; clustering mild (376-877 distinct providers/year, top-3 share <= 12.2%); exact per-instant counts are named as the first construction measurement",
        "not_a_mirror": "supported (differentiated) - no scored, temporally-split ML-ready benchmark on CQC bulk data exists in catalogue or literature searches; prior art is econometric (BMJ Public Health 2024 logistic regression; Lancet Healthy Longevity involuntary-closures Stata/R replication package for the 816 enforced-closure subset; NIHR multilevel logit) or a different country/regulator (npj Health Systems US nursing-home closures); ours = the vintage-anchored prediction-instant contract, temporal splits, reference triad and gate-qualified artifact; see novelty_check",
    },
    "uncertainty": (
        "1) FRAMING: the register event conflates cessation with re-registration - CQC's "
        "own file note says some deactivations continue under a new registration "
        "(legal entity/address/provider change), and BMJ 2024 (8,346 complete closures "
        "vs 14,911 register events 2011-2023) implies roughly 40-55% of deregistrations "
        "are re-registrations/transfer; advancement must either ship the honest "
        "register-event target with this limitation stated or build successor linkage "
        "(address/UPRN/ODS-code/brand adjacency; the API's linked-organisation data "
        "needs developer-portal auth). 2) HEADROOM UNMEASURED: simple references "
        "(last-rating rate, bed-size, LA, provider-sector) are the plausible strong "
        "priors - the BMJ/npj evidence says ratings+ownership drive closures (US ML "
        "AUROC 0.79 out-of-sample, so learnable structure exists); the reference triad "
        "is the FIRST construction measurement and the task is droppable if a one-line "
        "prior saturates it. 3) The publisher's system migration is delaying reflection "
        "of registration cancellations in current files - recent-window lag check "
        "required. 4) Era breaks: single-assessment rating change (~2024, location-level "
        "overall ratings dropped for multi-service ASC locations) and the 1 April 2019 "
        "regulatory-history inheritance change. 5) Provider-group cross-row exposure if "
        "group-history features ship - strictly-prior events only + declared restricted "
        "protocol. 6) Dormant-but-registered locations may sit in the at-T population "
        "(no dormancy flag in the bulk files; not measured this session)."
    ),
}
r["next_action"] = (
    "Advancement owns construction (no construction while a packaged candidate is "
    "actionable): (1) record the framing decision - register-event target with the "
    "re-registration share stated as a limitation, or a successor-linked 'complete "
    "closure' target (address/UPRN/brand adjacency; API linkage needs auth); (2) "
    "worker build: enumerate the Drive year folders, fetch January vintages 2016-2024 "
    "plus the deactivated file (sha256-pin everything, ~390 MB), assemble one row per "
    "care home per instant with strictly vintage-visible features (beds, service "
    "types, user bands, at-T rating + publication date + inherited flag, provider "
    "attributes, HSCA ages); (3) compute exact per-instant positives and the simple-"
    "reference triad (global rate, LA rate, last-rating rate, bed-size rate, "
    "provider-sector rate) BEFORE any model figure - droppable if a one-line prior "
    "saturates; (4) full-artifact gate 1.5 on the worker, exact-byte acceptance, then "
    "scoring, in the standing order."
)
r["review"] = None
r["rejection_reason"] = None
r["updated_at"] = datetime.now(timezone.utc).isoformat()

RECORD.write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n")
print("record written:", RECORD)
print("status:", r["status"], "| licence_class:", r["licence_class"])
