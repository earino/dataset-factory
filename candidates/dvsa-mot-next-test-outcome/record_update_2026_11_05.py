#!/usr/bin/env python3
"""Record the pre-launch construction decision for dvsa-mot-next-test-outcome.

Written BEFORE the dvsa-mot-build-001 launch (no score has ever existed for this
candidate). Asserts the current record state, applies the pre-registered design
decisions, and refuses to overwrite a record that has already moved on.
"""
import json
import sys
from pathlib import Path

RECORD = Path(__file__).resolve().parent / "record.json"
REQUIRED_STATUS = "investigating"

updates = {
    "status": "constructing",
    "construction_script": "candidates/dvsa-mot-next-test-outcome/source/build.py (job dvsa-mot-build-001)",
    "split_strategy": (
        "Temporal on the PREDICTION INSTANT (the prior completed class-4 test's date, "
        "the latest shipped knowable date): train priors 2009-01-01..2018-12-31, eval "
        "2019-01-01..2021-12-31, holdout 2022-01-01..2023-11-30. CHANGED from the "
        "original next-test-year windows (train next-tests 2010-2018 / eval 2019-2021 / "
        "holdout 2022-2024) BEFORE any construction or score: the gate checks split "
        "windows against the declared time_column, and the next test's date is "
        "label-side timing information that cannot ship, so next-test-year windows "
        "are unverifiable from the rows; prior-year windows keep every check coherent "
        "with available data (label years shift ~+1, boundary lead-time overlap "
        "documented). Right-censoring cutoff: priors on/after 2023-12-01 are excluded "
        "wholesale (counted) so no row needs a next test beyond the 2024-12 data end - "
        "the excluded tail is exactly where short-gap post-failure retests would "
        "otherwise survive an annual-cycle censoring and bias prevalence. Population "
        "bounds (all pre-registered before any score): class 4 only (both sides of "
        "every pair; other classes counted and skipped), vehicles deterministically "
        "hash-sampled md5(vehicle_id) mod 1000 == 0 (~0.1%, outcome-independent, fixed "
        "before any split), completed tests only (ABR/ABA <0.6% measured - excluded "
        "from both sides and counted), pairs are consecutive completed class-4 tests "
        "in (test_date, completed_date, file order) after dedup of exact duplicate "
        "projected rows (test_id is NOT unique - measured 2026-10-19). Tests "
        "2005-2008 are prior-history priming only. vehicle_id ships as a declared "
        "high-cardinality feature and is the event/cluster key; the runner id column "
        "is row_key (vehicle_id + pair ordinal, unique by construction)."
    ),
    "next_action": (
        "Collect dvsa-mot-build-001 (worker cpx32, hel1). Expected /output reports: "
        "summary.json (per-file receipts + population + per-year tables), "
        "qualification-dvsa-mot-next-test-outcome.json (gate 1.5.0), "
        "acceptance-*.txt, references-*.json (pre-registered triad, post-acceptance). "
        "Require gate exit 0 on the FULL artifact on the worker and exact-byte "
        "--accept BEFORE quoting any number. Then assemble + launch "
        "dvsa-mot-baseline-001 (baseline bundle: fetch the artifact from the staging "
        "release, re-accept against the bundled gate report BEFORE any score, run the "
        "benchmark's train.py/validate.sh unmodified, then the pre-registered deciding "
        "check: model vs every triad member, cluster-aware paired bootstrap, cluster = "
        "vehicle_id). A failed gate is a recorded finding: diagnose first, at most one "
        "rebuild per structural defect. No re-tuning of threshold, window, label or "
        "features after any score."
    ),
}


def main() -> int:
    record = json.loads(RECORD.read_text())
    if record.get("status") != REQUIRED_STATUS:
        print(f"REFUSED: record status is {record.get('status')!r}, expected "
              f"{REQUIRED_STATUS!r}; another writer moved this candidate on")
        return 1

    measurements = record.setdefault("measurements", {})
    measurements["construction_preflight_2026_11_05"] = {
        "source_access": (
            "CKAN package_show re-read 2026-11-05 (both datasets OGL v3.0): DfT "
            "package carries 40 resources including all 20 per-year RESULT files - "
            "test_result_2005..2016.txt.gz and dft_test_result_2017..2022.zip at "
            "data.dft.gov.uk/anonymised-mot-test/test_data/, dft_test_result_2023.zip "
            "mirrored at the DVSA S3 origin, MOT+testing+data+results+(2024).zip at "
            "the DVSA S3 origin. Failure-item files exist per year but are NOT used "
            "in v1: they join by test_id, which is measured NOT unique (6,336 repeat "
            "values in one month's prefix), so the join is ambiguous; the reduction is "
            "documented, not silent."
        ),
        "range_header_finding": (
            "MEASURED 2026-11-05: data.dft.gov.uk IGNORES Range headers - a ranged "
            "probe of dft_test_result_2019.zip streamed ~1.08 GB before being killed; "
            "the coordinator-side probe was aborted and no DfT bulk transfer happens "
            "on the coordinator. Consequence: DfT-era schemas (2005-2022) cannot be "
            "pre-measured from the coordinator and are measured BY the build itself, "
            "which records every observed header/delimiter in summary.json and fails "
            "loudly on an unmappable schema. The DVSA S3 origin answers ranged reads "
            "(2026-10-19 measurement unchanged)."
        ),
        "vintage_pin": (
            "The 2024 zip is byte-pinned to the 2026-10-19 measurement: 1,531,265,132 "
            "bytes, 12 monthly members test_result_202401..202412.csv, 15-column "
            "header verified verbatim; the build asserts all three and refuses on "
            "drift. The other 19 files were never fetched before, so the build RECORDS "
            "their sha256 as the construction vintage pin (a rebuild must match)."
        ),
        "dry_run_2026_11_05": (
            "Full build+gate+accept+score machinery exercised on synthetic fixtures "
            "spanning all three file eras (headerless pipe 2005-2008, headered pipe "
            "2009-2016, single-member zips 2017-2023, 12-member pinned 2024 zip), "
            "including duplicate rows, ABR rows, other-class rows and the censoring "
            "cutoff. Gate 1.5.0: 45/45 PASS on the synthetic extract; --accept "
            "ACCEPTED; the declared cross-row probe measured the blind-join exposure "
            "(synthetic eval coverage 420/570 rows, 0 mismatches - a later pair's "
            "prior_initial_fail equals the earlier pair's label by construction, "
            "which is exactly the exposure the probe exists to measure); access is "
            "isolated_rows. Fixture numbers are NOT findings and are never quoted."
        ),
        "pre_registered_triad": (
            "Deciding members (written before any construction or score, mirrored in "
            "source/score.py): persistence_prior_result (the prior test's own "
            "initial-fail flag - the last observed outcome), calendar_make_week "
            "(train-estimated rate per make x ISO week-of-year, make then global "
            "fallback), vehicle_train_rate (train-estimated rate per vehicle_id - the "
            "panel identity prior). Supplementary: global_rate (degenerate, Brier "
            "only), majority_class accuracy. DECIDING RULE: headroom ONLY if the full "
            "model beats EVERY deciding member with a cluster-aware paired bootstrap "
            "95% CI excluding zero in the model's favour AND the model's own "
            "cluster-bootstrap AUC CI lies entirely above 0.5; triad dominance -> "
            "DROP. Clusters = vehicle_id. Per-prior-year reporting mandatory (May-2018 "
            "regime change; 2020-21 pandemic test extensions)."
        ),
        "schema_risk": (
            "The 2005-2022 file schemas are unmeasured until the build runs (Range "
            "ignored at DfT). The build maps by header name with a positional "
            "fallback for headerless eras, asserts test_result values within "
            "{P,F,PRS,ABR,ABA}, requires a non-zero class-4 sampled row count per "
            "year, and records every observed header; an unmappable schema fails the "
            "job loudly with the evidence in the collected logs (one bounded worker "
            "cycle at risk, accepted deliberately)."
        ),
    }
    record.update(updates)
    RECORD.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({"status": record["status"],
                      "measurements_keys": sorted(measurements),
                      "next_action_head": record["next_action"][:80]},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
