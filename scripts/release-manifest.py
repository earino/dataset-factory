#!/usr/bin/env python3
"""Generate the release manifest and SHA256SUMS for a prepared dataset.

Everything comes from recorded evidence - the accepted artifact's expected hashes, the candidate
record, and (when it exists) the collected baseline report. Nothing is retyped by hand, so the
manifest cannot drift from what was actually measured.

Usage: python3 scripts/release-manifest.py austin-911-response
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "06d7002bc01933e4c094bbe84e4d9899572a893f"


def load(path: Path):
    return json.loads(path.read_text()) if path.is_file() else None


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    candidate = sys.argv[1] if len(sys.argv) > 1 else "austin-911-response"
    release = ROOT / "release" / candidate
    release.mkdir(parents=True, exist_ok=True)
    record = load(ROOT / "candidates" / candidate / "record.json")
    expected = load(ROOT / "candidates" / candidate / "baseline" / "expected_artifact.json")
    qualification = load(release / "qualification.json")
    # The baseline evidence is tracked next to the candidate, not read out of ignored scratch.
    baseline = load(ROOT / "candidates" / candidate / "baseline" / "baseline_result.json")
    if expected is None:
        raise SystemExit(f"no expected_artifact.json for {candidate}; nothing to manifest")

    manifest = {
        "dataset": candidate,
        "release_version": "2026.09",
        "release_tag": "v2026.09",
        "repository": "https://github.com/earino/austin-911-response",
        "visibility": "private (publication requires explicit authorisation)",
        "artifact_version": expected["artifact_version"],
        "artifact_job": expected["job"],
        # The staging release id, because a *draft* release has no tag namespace: looking it up
        # with releases/tags/<tag> returns 404 even though the release exists.
        "staging_release": expected.get("staging_release"),
        "staging_release_tag": f"job-{expected['job']}",
        "staging_repo": "earino/dataset-factory-staging",
        "construction_commit": COMMIT,
        "gate_version": expected.get("gate_version"),
        "gate_command": f"python3 code/qualify_dataset.py <dataset-dir>",
        "measurements": load(release / "measurements.json"),
        "assets": {},
        "package_files": {},
        "baseline_command": "sh baseline/reproduce_baseline.sh ./task",
        "get_dataset_command": "python3 get_dataset.py --dest ./task",
        "source": {
            "name": "Austin Open Data - APD 911 Calls for Service 2023-2026",
            "dataset_id": "e687-fx2y",
            "landing_page": "https://datahub.austintexas.gov/d/e687-fx2y",
            "api": "https://datahub.austintexas.gov/resource/e687-fx2y.json",
            "accessed": "2026-09-18",
            "licence": "Public Domain",
            "licence_evidence": (record or {}).get("license_evidence"),
        },
        "layout": {"task/meta.json": "meta.json",
                   "task/public/train.csv": "public/train.csv",
                   "task/public/eval.csv": "public/eval.csv",
                   "task/private/holdout.csv": "private/holdout.csv",
                   "task/quality.json": "quality.json"},
        "files": expected["files"],
        "splits": (record or {}).get("construction_output", {}).get("splits"),
        "qualification": (record or {}).get("qualification"),
        "baseline": baseline,
        "scope": "One baseline through the runner's training and validation contract. No agent or "
                 "harness comparison was run and none is implied.",
        "published": False,
        "publication_note": "Prepared for human review. Nothing here has been published.",
    }
    # Flat release-asset names: GitHub rejects `/` in asset names, so the download script restores
    # the runner layout. The mapping is recorded here rather than in prose.
    asset_for = {"public/train.csv": "train.csv", "public/eval.csv": "eval.csv",
                 "private/holdout.csv": "holdout.csv", "meta.json": "meta.json",
                 "quality.json": "quality.json"}
    manifest["assets"] = {
        relative: {"asset_name": asset_for[relative], "bytes": info["bytes"],
                   "sha256": info["sha256"]}
        for relative, info in sorted(expected["files"].items())
    }
    # Hashes of everything published in the repository, so the shipped code and docs can be
    # checked too - MANIFEST.json itself excluded, since a file cannot hash itself.
    package_files = {}
    for path in sorted(release.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.json":
            package_files[path.relative_to(release).as_posix()] = sha256_of(path)
    manifest["package_files"] = package_files

    (release / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # sha256sum -c format, over the artifact files under the names a downloader sees.
    lines = []
    for relative, info in sorted(expected["files"].items()):
        lines.append(f"{info['sha256']}  {relative}")
    (release / "SHA256SUMS").write_text("\n".join(lines) + "\n")

    print(f"wrote {release}/MANIFEST.json and SHA256SUMS")
    print(f"  artifact_version {expected['artifact_version'][:16]}...")
    print(f"  files: {len(expected['files'])}")
    print(f"  baseline: {'present' if baseline else 'NOT YET COLLECTED'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())