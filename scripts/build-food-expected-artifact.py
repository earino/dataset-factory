#!/usr/bin/env python3
"""Build candidates/chicago-food-inspections/baseline/expected_artifact.json from the
40 collected per-code gate reports of job food-001.

Everything comes from recorded evidence: each level's artifact_version, checks and file digests
are read from the gate's own qualification reports (collected from staging release 403508464);
every component digest is then cross-checked against the worker's own uploaded-asset list
(jobs/food-001.json result.assets) by (bytes, sha256), so a report describing bytes that were
never uploaded cannot pass. The extract-root labels.csv entry is read from the same asset list
and must appear exactly once at the size recorded in the candidate record.

    python3 scripts/build-food-expected-artifact.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / ".factory" / "food-001" / "reports"
JOB = ROOT / "jobs" / "food-001.json"
OUT = ROOT / "candidates" / "chicago-food-inspections" / "baseline" / "expected_artifact.json"
LABELS_BYTES = 24319192
# The 40 shipped codes, in the build summary's own order (floor_codes, ascending).
CODES = [
    1, 2, 3, 5, 6, 8, 9, 10, 11, 14, 16, 21, 22, 23, 25, 29, 32, 33, 35, 36,
    37, 38, 39, 40, 41, 43, 44, 45, 47, 48, 49, 51, 52, 53, 54, 55, 56, 57, 58, 60,
]


def main() -> int:
    assets = json.loads(JOB.read_text())["result"]["assets"]
    by_pair = {}
    for asset in assets:
        by_pair.setdefault((asset["size"], asset["sha256"]), []).append(asset)
    # food-001 uploaded each gate report twice (its .json and its .txt twin carry identical
    # bytes), so (bytes, sha256) pairs are NOT unique across the release. The digest chain
    # therefore asserts *presence* - every component the gate hashed must be among the bytes
    # the worker actually uploaded - and labels.csv below is asserted unique at its size,
    # which it is: no other asset is 24 MB.
    labels_matches = by_pair.get((LABELS_BYTES, "c891fd333a1691912a37aad1c4f9bfd3df1671aeecd3966ef052f08b511982d1"))
    if not labels_matches or len(labels_matches) != 1:
        raise SystemExit("labels.csv (24,319,192 B, c891fd33...) is not exactly once in the "
                         "uploaded asset list")

    levels, files = {}, {}
    for code in CODES:
        name = f"code_{code:02d}"
        report = json.loads((REPORTS / f"qualification-{name}.json").read_text())
        if not report.get("ok"):
            raise SystemExit(f"{name}: gate report is not ok")
        if report["gate_version"] != "1.3.0":
            raise SystemExit(f"{name}: unexpected gate version {report['gate_version']!r}")
        artifact = report["artifact"]
        version = artifact["artifact_version"]["digest"]
        if len(version) != 64:
            raise SystemExit(f"{name}: unexpected artifact version {version!r}")
        entry_files = {}
        for key in ("train", "eval", "holdout", "meta.json", "quality.json"):
            info = artifact[key]
            relative = f"{name}/{info['file']}"
            # The digest chain: every component the gate hashed must be a byte-identical
            # asset the worker actually uploaded to the staging release.
            if (info["bytes"], info["sha256"]) not in by_pair:
                raise SystemExit(f"{name}/{relative}: not present in the uploaded asset list "
                                 f"at ({info['bytes']}, {info['sha256'][:12]}...)")
            entry_files[relative] = {"bytes": info["bytes"], "sha256": info["sha256"]}
        levels[name] = {
            "artifact_version": version,
            "gate_version": report["gate_version"],
            "checks": len(report["results"]),
            "failed_checks": report["failed_checks"],
            "ok": report["ok"],
            "files": entry_files,
        }
        files.update(entry_files)

    files["labels.csv"] = {
        "bytes": labels_matches[0]["size"],
        "sha256": labels_matches[0]["sha256"],
    }

    missing = [f"code_{c:02d}" for c in CODES if f"code_{c:02d}" not in levels]
    if missing:
        raise SystemExit(f"codes without a gate report: {missing}")
    if len(files) != len(CODES) * 5 + 1:
        raise SystemExit(f"expected {len(CODES) * 5 + 1} files, collected {len(files)}")
    bad = [name for name, level in levels.items()
           if not level["ok"] or level["failed_checks"] or level["checks"] != 32]
    if bad:
        raise SystemExit(f"gate reports not clean (ok, 0 failed, 32 checks): {bad}")

    payload = {
        "job": "food-001",
        "staging_release": 403508464,
        "gate_version": "1.3.0",
        "note": "The food-001 artifact: 40 per-code runner configs, each gated on the worker "
                "(gate 1.3.0, 32 checks, 0 failed), plus the extract-root joint multi-label "
                "matrix labels.csv. Every digest here was read from the gate's own collected "
                "reports and cross-checked against the worker's uploaded asset list "
                "(jobs/food-001.json result.assets) by (bytes, sha256); labels.csv is that "
                "list's own entry. artifact_version for the package is derived by the manifest "
                "generator from the 40 per-config gate digests.",
        "labels_csv": dict(files["labels.csv"]),
        "levels": levels,
        "files": files,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  configs: {len(levels)}; files: {len(files)} "
          f"({len(CODES) * 5} config files + labels.csv)")
    total = sum(v["bytes"] for v in files.values())
    print(f"  total bytes: {total:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
