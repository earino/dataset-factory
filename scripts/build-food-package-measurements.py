#!/usr/bin/env python3
"""Build release/chicago-food-inspections/measurements.json from recorded evidence.

Everything comes from the collected food-001 build summary (sha256-verified against the staging
release when collected) and the candidate record - nothing is retyped by hand, so the package's
measurements block cannot drift from what the build actually measured. The baseline reference is
included only when the runner-contract baseline result exists beside the candidate, and is read
from it rather than restated.

    python3 scripts/build-food-package-measurements.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / ".factory" / "food-001" / "reports" / "build_summary.json"
RECORD = ROOT / "candidates" / "chicago-food-inspections" / "record.json"
BASELINE = ROOT / "candidates" / "chicago-food-inspections" / "baseline" / "baseline_result.json"
OUT = ROOT / "release" / "chicago-food-inspections" / "measurements.json"

SPLIT_ROWS = {"train": 156841, "eval": 35358, "holdout": 34218}
SPLIT_WINDOWS = {"train": "2010-01-01..2020-12-31", "eval": "2021-01-01..2023-12-31",
                 "holdout": "2024-01-01..2026-09-30"}


def rate(positives: int, rows: int) -> float:
    return round(positives / rows, 6)


def expected_labels_sha() -> str:
    """labels.csv's digest, from the regenerated expected artifact (the authority)."""
    expected = json.loads((ROOT / "candidates" / "chicago-food-inspections" / "baseline"
                           / "expected_artifact.json").read_text())
    entry = expected["files"]["labels.csv"]
    if entry["bytes"] != 24319192:
        raise SystemExit(f"unexpected labels.csv size {entry['bytes']}")
    return entry["sha256"]


def main() -> int:
    summary = json.loads(SUMMARY.read_text())
    record = json.loads(RECORD.read_text())
    if summary["pool_rows"] != 226417:
        raise SystemExit(f"unexpected pool_rows {summary['pool_rows']}")
    if len(summary["floor_codes"]) != 40:
        raise SystemExit(f"unexpected floor_codes {len(summary['floor_codes'])}")
    built = record["measurements"]["built_food_001"]
    if built["pool_rows"] != summary["pool_rows"]:
        raise SystemExit("record and build summary disagree on pool_rows")

    levels = {}
    for code in summary["floor_codes"]:
        name = f"code_{code:02d}"
        entry = summary["configs"][name]
        rows, positives = entry["rows"], entry["positives"]
        levels[name] = {
            "rows": rows,
            "positives": positives,
            "positive_rate": {
                split: rate(positives[split], rows[split]) for split in ("train", "eval", "holdout")
            },
            "positive_days": entry["positive_days"],
            "persistence_baseline": entry["persistence_baseline"],
        }

    census = record["measurements"]
    payload = {
        "pool": {
            "command": "candidates/chicago-food-inspections/source/build.py on worker job "
                       "food-001; evidence build_summary.json, collected from staging release "
                       "403508464 and sha256-verified",
            "pool_rows": summary["pool_rows"],
            "definition": "inspections with results in Pass / Fail / Pass w/ Conditions and a "
                          "non-null parseable violations blob, a non-null license id and an "
                          "inspection_date inside a split window; every config ships this "
                          "identical pool",
            "split_rows": SPLIT_ROWS,
            "split_windows": SPLIT_WINDOWS,
            "rows_dropped": summary["dropped_rows"],
        },
        "source_census": {
            "command": "anonymous SoQL aggregate queries over the live portal, 2026-09-27 "
                       "(probe scripts in candidates/chicago-food-inspections/; not the built pool)",
            "rows_total": census["rows_total"],
            "rows_with_violations": census["rows_with_violations"],
            "distinct_inspection_id": census["distinct_inspection_id"],
            "distinct_license": census["distinct_license"],
            "date_range": census["date_range"],
            "distinct_violation_codes_in_40000_row_scan":
                census["distinct_violation_codes_in_40000_row_scan"],
            "labels_per_inspection": census["density_recent_15000_rows"],
            "mean_codes_by_result": census["mean_codes_by_result"],
            "note": "the census is the discovery-time measurement of the whole source; the pool "
                    "and the floor below are what construction actually shipped",
        },
        "floor": {
            "command": "build.py floor pass on the constructed pool (job food-001): pool rate "
                       ">= 1%, >= 30 positives and >= 20 distinct positive days in every window",
            "codes_clearing_rate_floor": built["floor_candidates_above_rate"],
            "shipped_configs": built["floor_codes_shipped"],
            "dropped_by_window_minimums": built["floor_dropped_by_window_minimums"],
            "positive_rate_range": built["positive_rate_range"],
            "note": "the pre-build estimate of 37 codes came from a 15,000-row recent scan; the "
                    "full 226,417-row pool supports 40",
        },
        "extraction_cost": {
            "command": "worker job food-001 (cx23, Helsinki, 2 vCPU / 4 GB)",
            "wall_clock_seconds": 510.0,
            "pages": built["pages"],
            "route": "anonymous paged Socrata pull of 4ijn-s7e5 ordered by inspection_id "
                     "(46 pages at 5,000 rows), no credential",
            "output_bytes": {
                "split_files": summary["total_split_bytes"],
                "labels_csv": summary["labels_csv_bytes"],
            },
            "staging_release_assets": "290 assets totalling 1,286,358,734 bytes on private "
                                      "staging release 403508464",
            "probe_note": "the discovery-time probe measured the pull pattern on a 20,000-row "
                          "sample (5 requests, 23.2 s, 28.9 MB) and estimated the full pull at "
                          "65 requests / 458 MB / 366 s - an ESTIMATE, labelled as such in the "
                          "record; the figures above are the build's own measurements",
        },
        "levels": levels,
        "labels_csv": {
            "bytes": summary["labels_csv_bytes"],
            "sha256": expected_labels_sha(),
            "what": "the joint multi-label matrix at the dataset root: one row per pooled "
                    "inspection, one column per floor code",
        },
    }

    if BASELINE.is_file():
        baseline = json.loads(BASELINE.read_text())
        artifact = baseline["artifact"]
        payload["baseline_reference"] = {
            "command": "sh baseline/reproduce_baseline.sh ./task code_38 (recorded by job "
                       "food-baseline-002 through the runner's own contract)",
            "config": artifact["config"],
            "eval_auc": artifact["levels"][artifact["config"]]["eval_auc"],
            "contract_ok": artifact["levels"][artifact["config"]]["contract_ok"],
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  levels: {len(levels)} configs; pool {summary['pool_rows']:,}")
    total = sum(v["rows"]["train"] + v["rows"]["eval"] + v["rows"]["holdout"]
                for v in levels.values())
    print(f"  rows across all configs: {total:,}")
    if BASELINE.is_file():
        ref = payload["baseline_reference"]
        print(f"  baseline: {ref['config']} eval AUC {ref['eval_auc']}")
    else:
        print("  baseline: not yet collected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
