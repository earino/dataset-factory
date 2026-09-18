#!/usr/bin/env python3
"""Generate the release manifest and SHA256SUMS for a prepared dataset.

Everything comes from recorded evidence - the accepted artifact's expected hashes, the candidate
record, and (when it exists) the collected baseline report. Nothing is retyped by hand, so the
manifest cannot drift from what was actually measured.

Usage: python3 scripts/release-manifest.py austin-911-response
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "06d7002bc01933e4c094bbe84e4d9899572a893f"
GATE = "skills/dataset-qualification/scripts/qualify_dataset.py"


def load(path: Path):
    return json.loads(path.read_text()) if path.is_file() else None


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
        "artifact_version": expected["artifact_version"],
        "artifact_job": expected["job"],
        # The staging release id, because a *draft* release has no tag namespace: looking it up
        # with releases/tags/<tag> returns 404 even though the release exists.
        "staging_release": expected.get("staging_release"),
        "staging_release_tag": f"job-{expected['job']}",
        "staging_repo": "earino/dataset-factory-staging",
        "construction_commit": COMMIT,
        "gate_version": expected.get("gate_version"),
        "gate_command": f"python3 {GATE} <extract-dir>",
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