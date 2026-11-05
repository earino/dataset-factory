#!/usr/bin/env python3
"""Record update 2026-11-05 (Africa discovery tick): afdb-project-cancellation
investigating -> ready, from the executed discovery next_action steps 1-3.

Inputs, all measured this session:
- check-novelty.py verdict recorded 2026-11-05T16:02:51Z (differentiated, 4 queries).
- afdb-panel-probe-001 worker job (.factory/afdb-panel-probe-001/result.json):
  57/57 XML fetched, 172,488,241 B, full status/count table, per-file sha256 pin.
- Gate minimums read from skills/dataset-qualification/scripts/qualify_dataset.py
  (MIN_EVAL_POSITIVES=30, MIN_DISTINCT_EVENTS=20).
No field is filled with invented evidence; every number below is copied from the job result.
"""
import json
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
CAND = ROOT / "candidates/afdb-project-cancellation"
rec_path = CAND / "record.json"
rec = json.loads(rec_path.read_text())
res = json.loads((ROOT / ".factory/afdb-panel-probe-001/result.json").read_text())
summary = res["summary"]
counts = summary["counts"]
fetches = summary["fetches"]

pin = {f["dataset"]: f["sha256"] for f in fetches if f.get("status") == 200}
largest = max(fetches, key=lambda f: f.get("bytes", 0))
fetch_ok = sum(1 for f in fetches if f.get("status") == 200)

rec["status"] = "ready"

rec["measurements"]["worker_panel_probe_2026_11_05"] = {
    "job": "afdb-panel-probe-001",
    "server": "174640740 (cx23/hel1, 2 vCPU, 1024 MB container, EUR 0.04 reserved)",
    "result": ("succeeded, exit 0, oom_killed false; job wallclock "
               f"{summary['wallclock_s']} s; requests {summary['requests_used']}; "
               f"bytes downloaded {summary['bytes_downloaded']}"),
    "staging_release": "435425973 (private earino/dataset-factory-staging; summary.json sha256 a324477c1df5b6b2a5aeb8fa361499be6d227ab04430c8a23769c5fc2da40f93, 63,190 B)",
    "cleanup": ("worker destroyed 2026-11-05T16:20:10Z with provider read-back: "
                "GET /v1/servers/174640740 -> 404 not_found; GET /v1/servers -> 0 total; "
                "GET /v1/primary_ips -> 0 total"),
    "reachability_worker": (f"all {fetch_ok}/57 afdb.org IATI XML URLs answered HTTP 200 from the "
                            "Hetzner worker (the dws.gov.za lesson tested explicitly: worker egress "
                            "2.29.159.168); registry package_search refreshed from the worker: 57 "
                            "datasets, license_id cc-by on 57/57; zero fetch failures, zero retries"),
    "extraction_cost": (f"57 files, {summary['bytes_downloaded']} B (164.5 MiB) total; fetch "
                        "wallclock 7.2 s; job wallclock 20.5 s; largest file "
                        f"{largest['dataset']} {largest['bytes']} B; "
                        "budget used: 62/130 requests, 165/400 MB"),
    "source_vintage_pin_sha256": pin,
    "population": {
        "activities": counts["activities_total"],
        "duplicate_iati_identifiers_across_files": counts["duplicate_identifiers"],
        "status_histogram": counts["status_histogram"],
        "status_outside_1_2_3_5": counts["status_outside_1235"],
    },
    "reconciliation": ("registry XML: 191 cancelled / 3,897 completed / 5,188 activities. "
                       "Code for IATI datastore (2026-11-04 probe): 191 cancelled / 3,896 "
                       "completed / 5,187 activities - the registry XML and the datastore AGREE "
                       "(the 2026-11-04 tick's '230 vs 191' question is resolved: MapAfrica's 230 "
                       "cancelled sits in a larger population, 6,000 activities, i.e. a different "
                       "scope, not a registry defect). The task population is the registry XML, "
                       "as already declared."),
    "terminal_population": {
        "rows_status_3_or_5": 4088,
        "missing_type1_date": counts["terminal_missing_type1"],
        "missing_type3_planned_end": counts["terminal_missing_type3"],
        "completed_with_actual_end": counts["completed_with_actual_end"],
        "completed_without_actual_end": counts["completed_without_actual_end"],
        "cancelled_with_actual_end": counts["cancelled_with_actual_end"],
        "cancelled_without_actual_end": counts["cancelled_without_actual_end"],
    },
    "timing": {
        "type2_minus_type1_days": counts["type2_type1_offset_days"],
        "type2_minus_type1_days_cancelled": counts["type2_type1_offset_days_cancelled"],
        "note": ("the prediction instant is the published activity-date type 1 (planned start), "
                 "present on 100% of scored rows; actual start follows it by median 75 days; the "
                 "~1-day MapAfrica displayed-approval-date offset (one observed pair, 2026-11-04) "
                 "stays a construction-time documentation sample and is declared, not claimed "
                 "resolved"),
    },
    "censoring_eligibility": counts["censored"],
    "split_counts_proposed_measured": {
        "train_le_2000": counts["windows"]["train"],
        "eval_2001_2010": counts["windows"]["eval"],
        "holdout_2011_2023": counts["windows"]["holdout"],
        "recent_2024_plus": counts["windows"]["recent"],
        "gate_finding": ("eval 2001-2010 carries 29 positives; the qualification gate requires "
                         "MIN_EVAL_POSITIVES=30 and MIN_DISTINCT_EVENTS=20 "
                         "(skills/dataset-qualification/scripts/qualify_dataset.py), so the "
                         "proposed window FAILS the gate by one positive"),
    },
    "split_counts_chosen_2026_11_05": {
        "rule": ("chosen BEFORE any construction or score from the measured per-year table, to "
                 "clear the gate minimum: eval end moved 2010 -> 2011; holdout start follows. "
                 "No threshold, label or feature re-tuning: no score exists anywhere."),
        "train_approval_le_2000": {"rows": 1871, "positives": 121, "negatives": 1750,
                                   "positive_rate": 0.0647,
                                   "positive_country_year_cells": 107,
                                   "positives_in_cells_ge2": 26,
                                   "distinct_countries_with_positives": 42},
        "eval_2001_2011": {"rows": 1126, "positives": 32, "negatives": 1094,
                           "positive_rate": 0.0284,
                           "positive_country_year_cells": "27-29",
                           "cells_note": ("26 measured for 2001-2010 plus 1-3 for 2011 (3 "
                                          "positives); exact integer is the construction's "
                                          "declared positive_events"),
                           "distinct_countries_with_positives": "21+ (2011 adds 0-3)"},
        "holdout_2012_2023": {"rows": 1118, "positives": 38, "negatives": 1080,
                              "positive_rate": 0.034,
                              "positive_country_year_cells": "31-33",
                              "cells_note": ("34 measured for 2011-2023 minus 1-3 for 2012 (3 "
                                             "positives)"),
                              "distinct_countries_with_positives": "15-17"},
        "excluded": {"recent_2024_plus": "4 terminal rows / 0 positives (declared, not scored)",
                     "censored_status_1_or_2": "1,100 rows, never scored"},
        "gate_margin": ("eval 32 positives vs 30 minimum; holdout 38 vs 30; events 27-29 and "
                        "31-33 vs 20 minimum - every bound clears the gate"),
    },
    "per_approval_year": counts["per_approval_year"],
    "grain_nuance": ("13 positive rows carry no recipient-country element (11 holdout, 2 eval): "
                     "multinational/regional operations. The construction must define the cluster "
                     "key as country-or-region and declare it as positive_events."),
    "codelist": ("activity-status machine-readable codelist not retrieved: "
                 "raw.githubusercontent.com/IATI/codelists ActivityStatus.xml -> 404; "
                 "iatistandard.org codelist page -> 200 (280,851 B, not parsed). The status "
                 "labels used are the publisher's own from MapAfrica's stats endpoint "
                 "(measured 2026-11-04): 1 Approved, 2 Ongoing, 3 Completed, 5 Cancelled."),
}

rec["split_strategy"] = (
    "Temporal split on approval year (activity-date type 1), chosen 2026-11-05 from the measured "
    "registry-XML table and PRE-REGISTERED before any construction or score: train approvals "
    "<=2000 (1,871 terminal rows / 121 cancelled positives / 107 country-year cells / 6.47%); "
    "eval 2001-2011 (1,126 / 32 / 27-29 cells / 2.84%); holdout 2012-2023 (1,118 / 38 / 31-33 "
    "cells / 3.40%). 2024+ approvals (4 terminal rows, 0 positives) and all right-censored "
    "statuses 1/2 (1,100 rows, approvals 2007+) are excluded and declared. The eval end was "
    "extended from 2010 to 2011 because the originally proposed eval window carried 29 positives, "
    "one short of the gate's 30-positive minimum; the re-cut is measured, not tuned - no score "
    "exists. Positives cluster by country and approval year (clustered share in cells with >=2 "
    "positives: 26/121 train, 6/29 eval, 12/41 holdout); the cluster/event key is "
    "country-or-region x approval year, declared to the gate as positive_events."
)

rec["review"] = (
    "Five contracts re-reconciled 2026-11-05 after the worker pass (each with its evidence "
    "source and coverage): "
    "(1) Redistribution SUPPORTED - class A; IATI registry package_search re-run from the worker "
    "this session: 57 datasets, license_id cc-by on 57/57; CC BY 4.0 also stated on MapAfrica's "
    "data-product modal (2026-11-04). Attribution wording carried to LICENSE.md at release. "
    "(2) Prediction timing SUPPORTED for a retrospective task - the instant is the published "
    "activity-date type 1, present on 100% of the 4,088 scored rows (measured); actual start "
    "follows by median 75 days; the archive is re-published in full, so the current-vintage "
    "posture is declared (no operational historical claim); the ~1-day MapAfrica display offset "
    "remains a construction documentation sample, explicitly an assumption. "
    "(3) Target SUPPORTED - label = activity-status 5 vs 3, excludable by construction; statuses "
    "1/2 never scored; the censored backlog is entirely post-2006 (1,100 rows, min type-1 year "
    "2007) so the historical backfill is complete for the scored era; the MapAfrica-230 vs "
    "registry-191 gap is resolved (the registry XML agrees exactly with the Code for IATI "
    "datastore: 191 cancelled; MapAfrica is a larger different population). "
    "(4) Split capacity SUPPORTED - measured per-window counts over the terminal population: "
    "train 1,871/121, eval 1,126/32, holdout 1,118/38, both classes present in every window, "
    "clustered counts recorded, gate minimums cleared under every bound (32, 38 >= 30 positives; "
    "27-29, 31-33 >= 20 events). The 2026-11-04 proposal's eval window (29 positives) was one "
    "short and was re-cut BEFORE any score, with the reason recorded. "
    "(5) Contribution - novelty_check recorded through scripts/check-novelty.py this session "
    "(differentiated; 4 queries; ours/theirs/prior-art stated). The family-risk test is "
    "PRE-REGISTERED as the construction-time deciding check: the reference triad (global rate, "
    "trailing country rate, trailing sector-x-decade rate) computed from TRAIN ONLY on identical "
    "eval rows; if its strongest member is not beaten by a meaningful margin, this is the third "
    "measured instance of the WB at-approval family defect and the candidate DROPS with the "
    "evidence. Bench context: two WB at-approval tasks already died on rate/identity priors; the "
    "triad is feasible from the measured data (42/21+/15-17 countries with positives per window, "
    "57 sectors)."
)

rec["next_action"] = (
    "READY for advancement, standing order (no step may be skipped or reordered): "
    "(1) CONSTRUCTION on a worker from the pinned source vintage - the 57 afdb.org XML URLs must "
    "hash to measurements.worker_panel_probe_2026_11_05.source_vintage_pin_sha256 or the build "
    "refuses; build.py writes the terminal-population panel (statuses 3+5 only; label = "
    "activity-status 5 vs 3; features at-approval attributes only: country/region, sector, "
    "financing instrument, commitment, planned span, era; the label column ships only as the "
    "label), the pre-registered splits (train <=2000 / eval 2001-2011 / holdout 2012-2023), the "
    "declared exclusions (2024+; statuses 1/2), event_key = country-or-region x approval year; "
    "quality.json evaluation_contract = retrospective_research / isolated_rows / declared "
    "current-vintage as-of posture / selection at prediction time. "
    "(2) FULL-ARTIFACT qualification with gate 1.5 on the worker (declared positive_events must "
    "equal the recomputed cells - the 2011/2012 cell integers measured here only as bounds "
    "become exact there). "
    "(3) EXACT-BYTE --accept before any scoring. "
    "(4) REFERENCE TRIAD, the pre-registered DECIDING check, on identical eval rows only: global "
    "cancellation rate, trailing country rate, trailing sector-x-decade rate (train-only "
    "estimates); headroom is demonstrated ONLY if the full model beats EVERY triad member with a "
    "clustered bootstrap 95% CI excluding zero in the model's favour; triad dominance -> DROP "
    "(third instance of the WB family defect, evidence preserved); no re-tuning of threshold, "
    "window, label or features after any score. "
    "(5) Reporting; holdout never opened during development. "
    "Not this session's work: this record ends at the discovery verdict."
)

rec.setdefault("jobs", []).append({
    "id": "afdb-panel-probe-001",
    "kind": "discovery-worker-probe (read-only aggregate; count pass)",
    "server_id": 174640740,
    "server_type": "cx23/hel1",
    "status": "succeeded",
    "exit_code": 0,
    "elapsed_s": summary["wallclock_s"],
    "reserved_eur": "0.04",
    "staging_release": 435425973,
    "deleted_at": "2026-11-05T16:20:10Z",
    "provider_readback": "GET /servers/174640740 -> 404 not_found; /servers 0; /primary_ips 0",
})

rec_path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n")
print("record updated: status =", rec["status"],
      "| pin entries:", len(pin),
      "| jobs:", len(rec["jobs"]))
