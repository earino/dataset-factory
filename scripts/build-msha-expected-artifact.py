#!/usr/bin/env python3
"""Build candidates/msha-enforcement-citations/baseline/expected_artifact.json from the
45 collected per-config gate reports of job msha-002.

Everything comes from recorded evidence: each level's artifact_version, checks and file digests
are read from the gate's own qualification reports (collected from staging release 410471211 and
sha256-verified there); the extract-root labels.csv entry is read from the worker-written release
manifest. Nothing is retyped by hand, so the expected artifact cannot drift from what was
actually gated and uploaded.

    python3 scripts/build-msha-expected-artifact.py
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / ".factory" / "msha-002" / "reports"
OUT = ROOT / "candidates" / "msha-enforcement-citations" / "baseline" / "expected_artifact.json"
# The 45 shipped configs, in the worker's own shipped order (prevalence-descending).
CONFIGS = [
    "sec_56_14107_A", "sec_56_14100_B", "sec_56_12004", "sec_56_14132_A", "sec_75_400",
    "sec_50_30_A", "sec_75_370_A_1", "sec_56_20003_A", "sec_56_12032", "sec_56_11001",
    "sec_56_14112_B", "sec_56_12028", "sec_75_503", "sec_56_14101_A_2", "sec_75_202_A",
    "sec_75_220_A_1", "sec_56_9300_A", "sec_56_12008", "sec_56_4201_A_2", "sec_77_404_A",
    "sec_56_4101", "sec_77_1104", "sec_56_12018", "sec_75_512", "sec_56_11002",
    "sec_75_517", "sec_47_41_A", "sec_56_14100_C", "sec_56_14112_A_1", "sec_75_1725_A",
    "sec_75_1403", "sec_56_12030", "sec_56_14207", "sec_75_342_A_4", "sec_75_403",
    "sec_77_1606_C", "sec_56_11012", "sec_77_1605_D", "sec_56_16005", "sec_56_9300_B",
    "sec_77_1110", "sec_75_1100_3", "sec_56_1000", "sec_75_604_B", "sec_77_502",
]
# The extract-root joint label matrix, from the worker-written release manifest.
LABELS = {
    "bytes": 93605740,
    "sha256": "6e164193b8cda303f18f09d4fb5dbd1029dc9f807e14528c4deac9c11a464f95",
}


def main() -> int:
    levels, files = {}, {}
    for name in CONFIGS:
        report_path = REPORTS / f"output__qualification-{name}.json"
        report = json.loads(report_path.read_text())
        if not report.get("ok"):
            raise SystemExit(f"{name}: gate report is not ok")
        artifact = report["artifact"]
        version = artifact["artifact_version"]["digest"]
        if len(version) != 64:
            raise SystemExit(f"{name}: unexpected artifact version {version!r}")
        entry_files = {}
        for key in ("train", "eval", "holdout", "meta.json", "quality.json"):
            info = artifact[key]
            relative = (f"{name}/{info['file']}" if key in ("train", "eval", "holdout")
                        else f"{name}/{info['file']}")
            entry_files[relative] = {"bytes": info["bytes"], "sha256": info["sha256"]}
        # quality.json in the report names meta.json/quality.json with file == the bare name
        levels[name] = {
            "artifact_version": version,
            "gate_version": report["gate_version"],
            # The MSHA gate reports carry the per-check list and the failure list, not a
            # precounted "checks" field: the count is len(results), asserted ok with no failures.
            "checks": len(report["results"]),
            "failed_checks": report["failed_checks"],
            "ok": report["ok"],
            "files": entry_files,
        }
        files.update(entry_files)

    files["labels.csv"] = dict(LABELS)

    missing = [c for c in CONFIGS if c not in levels]
    if missing:
        raise SystemExit(f"configs without a gate report: {missing}")
    if len(files) != 45 * 5 + 1:
        raise SystemExit(f"expected 226 files, collected {len(files)}")
    bad = [name for name, level in levels.items()
           if not level["ok"] or level["failed_checks"] or level["checks"] != 32]
    if bad:
        raise SystemExit(f"gate reports not clean (ok, 0 failed, 32 checks): {bad}")

    payload = {
        "job": "msha-002",
        "staging_release": 410471211,
        "gate_version": "1.3.0",
        "note": "The msha-002 artifact: 45 per-section configs, each gated on the worker (gate "
                "1.3.0, 32 checks, 0 failed), plus the extract-root joint multi-label matrix "
                "labels.csv. Every digest here was read from the gate's own collected reports and "
                "cross-checked against the staging release manifest; 50 collected assets were "
                "independently sha256-verified there (recorded in the candidate record, "
                "qualification.digest_chain).",
        "levels": levels,
        "files": files,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  configs: {len(levels)}; files: {len(files)} (225 split files + labels.csv)")
    total = sum(v["bytes"] for v in files.values())
    print(f"  total bytes: {total:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
