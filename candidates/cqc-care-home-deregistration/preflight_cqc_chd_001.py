#!/usr/bin/env python3
"""Record the cqc-care-home-deregistration framing decision + cqc-chd-001
preflight in the candidate record before the worker launch (advancement
session 2026-11-03). One-shot provenance script, kept beside the candidate.
"""
import json
import datetime
from pathlib import Path

REC = Path("candidates/cqc-care-home-deregistration/record.json")
record = json.loads(REC.read_text())
now = "2026-11-03T18:2xZ"

record["framing_decision"] = {
    "decided_at": "2026-11-03 (advancement session, pre-launch)",
    "decision": "register-event target",
    "target": ("12-month deregistration of the CQC location: Location Status "
               "Inactive-Dereg or Removed with a Location HSCA End Date in "
               "(T, T+365d], joined from the Deactivated Locations file by "
               "Location ID"),
    "why": ("the register event is the publisher's own well-defined, "
            "predictable monthly-product event; successor-linked 'complete "
            "closure' targets need API auth or speculative address/brand "
            "adjacency that cannot be verified from the bulk files"),
    "limitation_stated": ("the register event conflates cessation with "
                          "re-registration (CQC in-file note; BMJ 2024: "
                          "8,346 complete closures vs 14,911 register events "
                          "2011-2023 implies ~40-55% re-registrations) - "
                          "carried in quality.json limitations and every "
                          "package document"),
}

record["preflight_cqc_chd_001"] = {
    "recorded_at": now,
    "row_selection": ("build_panel(): rows = 'Care home?' = Y rows of the "
                     "T vintage (the vintage's own column, read at T); the "
                     "label is looked up afterwards solely to compute the "
                     "label; the 2023 January vintage is excluded by design "
                     "so every train window closes >= 12 months before the "
                     "eval instant; dropped-instant rule: a vintage whose "
                     "required columns do not resolve is DROPPED with a loud "
                     "diagnostic, train needs >= 5 resolved instants"),
    "artifact_writer": ("write_artifact(): ONE column list (COLUMNS) in one "
                        "place; location_key asserted unique across the "
                        "panel; meta.json carries all 8 TASK_KEYS with "
                        "per-split positive_rate"),
    "qualification": ("run.sh stage 2: qualify_dataset.py (gate 1.5.0) on the "
                      "FULL artifact on the worker; stage 3: --accept on the "
                      "exact bytes; both before any reference is computed"),
    "first_performance_metric": ("score.py (run.sh stage 4), post-acceptance, "
                                 "eval rows only, holdout never opened; "
                                 "build.py computes no AUC/accuracy/model "
                                 "(read line by line) - counts, fixture "
                                 "asserts and per-instant diagnostics only"),
    "p0_panel_design": {
        "successor_exposure": (
            "the missing-successor rule (the unhcr P0 class): killed "
            "STRUCTURALLY - every scored frame carries a SINGLE instant "
            "(train 2016-01..2022-01, eval 2024-01, holdout 2025-01, the "
            "last instant), so the successor rows of eval rows exist only in "
            "the sealed holdout and holdout rows have no successor instant "
            "in the artifact"),
        "identity": ("location identity ships as a per-instant pseudonym "
                     "sha256(salt|instant|location_id)[:16]; no name, "
                     "address, postcode, provider id, CH/charity number "
                     "ships; real ids only in auxiliary/location_map.csv "
                     "(staging-side, never solver-visible)"),
        "provider_features": ("no provider-group history feature ships; "
                              "provider sector only"),
        "probes": ("gate probe 0: successor attack over the pseudonym id "
                   "(expected coverage 0); probe 1: successor attack over "
                   "the strongest instant-invariant quasi-key (LA x beds x "
                   "start-year x rating x sector, +12-month offset) - "
                   "coverage on eval/holdout is the measured bound over the "
                   "frames a solver can see; in-train coverage measures the "
                   "quasi-linkage rate where labels are public anyway"),
        "train_label_chronology": ("train instants stop at 2022: every train "
                                   "12-month window closes by 2023-01-13, "
                                   "a year before the eval instant"),
    },
    "timing_block": ("kind=period_end, source_kind=administrative_record, "
                     "lag 0 (the vintage IS the register state at its "
                     "production instant); observations carry every "
                     "vintage's production date; as-of asserted in-build "
                     "(0/14,765 eval rows with rating Publication Date "
                     "after T)"),
    "rehearsal": ("tests/test_cqc_build.py: real build.py over synthetic "
                  "vintages (one XLSX to exercise the stdlib OOXML reader) "
                  "-> gate 1.5.0 with 0 failed checks -> exact-byte accept "
                  "-> score.py references -> byte-identical rebuild -> "
                  "red/green (a second eval instant re-opening the "
                  "successor channel is refused by rows_within_declared_"
                  "windows; removing the timing block is refused; a stale "
                  "report against different bytes is refused) - 10/10 OK"),
    "fixtures_pinned": ("deactivated edition size+sha256 prefix "
                        "(27,644,723 B / 49dc3062) + 2024-01 vintage "
                        "(26,147,266 B / ac40b6f8) asserted against the "
                        "2026-11-03 discovery measurements; eval counts "
                        "14,765/758/2,076 asserted exactly; dated fixtures "
                        "Park Hills / Henley House / Options Hazel House"),
}

record["status"] = "constructing"
record["updated_at"] = now
record["jobs"] = record.get("jobs") or []
record["jobs"].append({
    "id": "cqc-chd-001",
    "launched_by": "advancement session 2026-11-03",
    "state_at_record": "preflight recorded, launch pending",
})

REC.write_text(json.dumps(record, indent=1, ensure_ascii=True) + "\n")
print("record updated: framing_decision + preflight_cqc_chd_001 recorded")
