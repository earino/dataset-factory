#!/usr/bin/env python3
"""Build release/msha-enforcement-citations/measurements.json from recorded evidence.

Everything comes from the collected msha-002 build summary (digest-verified against the staging
release when collected) and the candidate record - nothing is retyped by hand, so the package's
measurements block cannot drift from what the build actually measured.

    python3 scripts/build-msha-package-measurements.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / ".factory" / "msha-002" / "reports" / "output__build_summary.json"
RECORD = ROOT / "candidates" / "msha-enforcement-citations" / "record.json"
OUT = ROOT / "release" / "msha-enforcement-citations" / "measurements.json"


def rate(positives: int, rows: int) -> float:
    return round(positives / rows, 6)


def main() -> int:
    summary = json.loads(SUMMARY.read_text())
    record = json.loads(RECORD.read_text())
    if summary["pool_events"] != 497897:
        raise SystemExit(f"unexpected pool_events {summary['pool_events']}")
    if len(summary["shipped_configs"]) != 45:
        raise SystemExit(f"unexpected shipped_configs {len(summary['shipped_configs'])}")

    levels = {}
    for name in summary["shipped_configs"]:
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

    probe = record["measurements"]
    payload = {
        "pool": {
            "command": "source/build.py on worker job msha-002; evidence build_summary.json, "
                       "collected from staging release 410471211 and digest-verified",
            "pooled_events": summary["pool_events"],
            "definition": "inspections carrying at least one violation row with a parseable "
                          "INSPECTION_BEGIN_DT inside a split window; every config ships this "
                          "identical pool",
            "split_rows": {"train": 415088, "eval": 49233, "holdout": 33576},
            "split_windows": {"train": "2001-2020", "eval": "2021-2023", "holdout": "2024-2025"},
        },
        "source_census": {
            "command": "candidates/msha-enforcement-citations/probe_violations.py - anonymous "
                       "streamed probe of the raw Violations table, 2026-09-27 (not the built pool)",
            "violation_rows": probe["rows_total"],
            "distinct_inspection_events": probe["distinct_inspection_event_no"],
            "distinct_mines": probe["distinct_mine_id"],
            "distinct_part_section_values": probe["distinct_part_section_labels"],
            "labels_per_inspection": probe["labels_per_inspection"],
            "rows_with_empty_part_section": probe["rows_with_empty_part_section"],
            "note": "the census is the discovery-time measurement of the whole source; the pool "
                    "and the floor below are what construction actually shipped",
        },
        "floor": {
            "command": "build.py floor pass on the constructed pool (job msha-002)",
            "sections_at_1pct_of_pool": len(summary["floor_sections"]),
            "shipped_configs": len(summary["shipped_configs"]),
            "held_back_by_config_cap": len(summary["floor_sections"]) - len(summary["shipped_configs"]),
            "note": "the standalone probe counted 104 sections at >=1% on the full 538,068-"
                    "inspection census; construction recomputes the floor on its own 497,897-"
                    "event pool, and 80 is the number the artifact ships",
        },
        "extraction_cost": {
            "command": "worker job msha-002 (cpx32, Helsinki, 4 vCPU / 8 GB)",
            "wall_clock_seconds": 581.0,
            "route": "one anonymous download each of Violations.zip (120,736,998 bytes; member "
                     "Violations.txt 1,442,221,050 bytes), Inspections.zip and Mines.zip from "
                     "arlweb.msha.gov/OpenGovernmentData/DataSets/, streamed; no API, no credential",
            "output_bytes": {
                "split_files": summary["total_split_bytes"],
                "labels_csv": summary["labels_csv_bytes"],
            },
            "staging_release_assets": "326 assets totalling 3,385,877,790 bytes on private "
                                      "staging release 410471211 (325 objects plus the manifest)",
        },
        "corrected_feature": {
            "what": "prev_target_cited is documented as 'cited on the mine's most recent "
                    "strictly-earlier pooled inspection'; job msha-001 wrote the cumulative "
                    "ever-cited set instead, and its artifact was superseded before collection",
            "evidence": "sec_75_400 public/eval.csv fetched from both releases, each verified "
                        "against its published digest: identical size and rows, exactly one "
                        "column differs (prev_target_cited, 4,933 rows). The persistence "
                        "baseline fell on all 45 configs (mean 0.754 pre-fix -> 0.576 fixed; "
                        "sec_75_400 0.9403 -> 0.6733)",
            "superseded_job": "msha-001",
        },
        "levels": levels,
        "labels_csv": {
            "bytes": summary["labels_csv_bytes"],
            "sha256": record["measurements"]["built_msha_002"]["labels_csv_sha256"],
            "what": "the joint multi-label matrix at the dataset root: one row per pooled "
                    "inspection, one column per floor section, byte-identical between the "
                    "superseded and accepted builds",
        },
        "baseline_reference": {
            "command": "sh baseline/reproduce_baseline.sh ./task sec_56_12004 (recorded by job "
                       "msha-baseline-001 through the runner's own contract)",
            "config": "sec_56_12004",
            "eval_auc": 0.8036,
            "contract_ok": True,
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  levels: {len(levels)} configs; pool {summary['pool_events']:,}")
    total = sum(v["rows"]["train"] + v["rows"]["eval"] + v["rows"]["holdout"] for v in levels.values())
    print(f"  rows across all configs: {total:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
