#!/usr/bin/env python3
"""Assemble a worker job directory from the repository's canonical files.

Why this exists
---------------
A worker job directory must be self-contained: the worker has no access to this private
repository, so `build.py` and the qualification gate both have to be copied into the bundle.
Copying them by hand, or vendoring a second copy of the gate into the candidate directory,
creates two versions that can drift - and a stale gate is worse than no gate.

This script is the single assembly point. It copies the canonical files into an ignored
staging directory, generates `job.json`, verifies the result against the worker's own bundle
rules, and prints the directory to launch:

    python3 scripts/assemble-job.py austin-001
    sh scripts/scout-factory worker plan .factory/jobs/austin-001/job.json
    sh scripts/scout-factory worker launch .factory/jobs/austin-001/job.json

Nothing here touches the network or the cloud, and the staging directory is regenerated from
scratch on every run.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_SUFFIXES = (".py", ".sh", ".json", ".txt", ".toml", ".yaml", ".yml", ".md")
BUNDLE_LIMIT = 2 * 1024 * 1024

# (destination name, source path relative to the repository root)
JOBS = {
    "austin-001": {
        "candidate": "austin-911-response",
        "files": [
            ("build.py", "candidates/austin-911-response/source/build.py"),
            ("run.sh", "candidates/austin-911-response/source/run.sh"),
            ("qualify_dataset.py", "skills/dataset-qualification/scripts/qualify_dataset.py"),
        ],
        "job": {
            "id": "austin-001",
            "candidate": "austin-911-response",
            "image": "python:3.13-slim",
            "command": ["sh", "/workspace/run.sh"],
            "server_type": "cpx32",
            "location": "hel1",
            "cpus": 2,
            "memory_mb": 2048,
            "timeout_minutes": 60,
            "lifetime_minutes": 120,
            "max_disk_mb": 3072,
            "max_artifact_mb": 600,
        },
    },
}


def check_bundle(directory: Path) -> int:
    """Mirror factory.worker.source_bundle so a bad bundle fails here, not at launch."""
    total = 0
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise SystemExit(f"assembled bundle contains a symlink: {path}")
        if path.is_dir():
            continue
        relative = path.relative_to(directory)
        if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
            raise SystemExit(f"assembled bundle contains a hidden file or cache: {relative}")
        if path.suffix not in ALLOWED_SUFFIXES:
            raise SystemExit(f"assembled bundle has an unexpected suffix: {relative}")
        total += path.stat().st_size
    if total > BUNDLE_LIMIT:
        raise SystemExit(f"assembled bundle is {total} bytes, over the {BUNDLE_LIMIT} limit")
    return total


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Assemble a worker job directory")
    parser.add_argument("job_id", nargs="?", default="austin-001", choices=sorted(JOBS))
    args = parser.parse_args(argv)

    spec = JOBS[args.job_id]
    target = ROOT / ".factory" / "jobs" / args.job_id
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    recorded = []
    for name, relative in spec["files"]:
        source = ROOT / relative
        if not source.is_file():
            raise SystemExit(f"canonical source is missing: {relative}")
        shutil.copyfile(source, target / name)
        recorded.append({"bundled_as": name, "source": relative,
                         "bytes": source.stat().st_size})

    job = dict(spec["job"])
    job["source_files"] = recorded
    (target / "job.json").write_text(json.dumps(job, indent=1) + "\n")

    total = check_bundle(target)
    print(json.dumps({
        "job_directory": str(target.relative_to(ROOT)),
        "job_id": job["id"],
        "bundle_bytes": total,
        "files": recorded,
        "next": [
            f"sh scripts/scout-factory worker plan {target.relative_to(ROOT)}/job.json",
            f"sh scripts/scout-factory worker launch {target.relative_to(ROOT)}/job.json",
            f"sh scripts/scout-factory worker collect {job['id']}",
            f"sh scripts/scout-factory worker destroy {job['id']}",
        ],
        "acceptance": "a passing /output/qualification.json is required before the artifact "
                      "is scored or the candidate accepted; verify with "
                      "skills/dataset-qualification/scripts/qualify_dataset.py "
                      "--accept <report> <extract-dir>",
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
