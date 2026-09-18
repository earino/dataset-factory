#!/usr/bin/env python3
"""Assemble a worker job directory from the repository's canonical files.

Why this exists
---------------
A worker job directory must be self-contained: the worker has no access to this private
repository, so `build.py` and the qualification gate both have to be copied into the bundle.
Copying them by hand, or vendoring a second copy of the gate into the candidate directory,
creates two versions that can drift - and a stale gate is worse than no gate.

This script is the single assembly point. It reads the candidate's own `source/job.json` for
the job's size and identity, overrides only what a full worker run needs (the container command
and the sizing that fits the gate), copies the canonical files into an ignored staging
directory, verifies the result against the worker's own bundle rules, and prints the directory
to launch:

    python3 scripts/assemble-job.py austin-911-response
    sh scripts/scout-factory worker plan .factory/jobs/austin-002/job.json
    sh scripts/scout-factory worker launch .factory/jobs/austin-002/job.json

The job **id comes from the candidate's `source/job.json`**, not from this file. OPERATIONS
says each attempt gets a new job id, and the first version of this script hardcoded the id in
two places, which made a second attempt impossible to express.

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

# Assembled from the candidate's own source/job.json, so the job id lives in exactly one place.
CANDIDATES = {
    "austin-911-response": {
        "job_file": "candidates/austin-911-response/source/job.json",
        "files": [
            ("build.py", "candidates/austin-911-response/source/build.py"),
            ("run.sh", "candidates/austin-911-response/source/run.sh"),
            ("qualify_dataset.py", "skills/dataset-qualification/scripts/qualify_dataset.py"),
        ],
        # A full worker run builds the whole extract and then qualifies it, so it needs the
        # entrypoint that does both and sizing that fits; the small local sample job does not.
        "overrides": {
            "command": ["sh", "/workspace/run.sh"],
            "timeout_minutes": 60,
            "lifetime_minutes": 120,
            "max_disk_mb": 3072,
            "max_artifact_mb": 600,
        },
    },
}


def load_job(spec: dict) -> dict:
    """The candidate's own job.json is the source of truth for identity and sizing."""
    path = ROOT / spec["job_file"]
    if not path.is_file():
        raise SystemExit(f"candidate job file is missing: {spec['job_file']}")
    job = json.loads(path.read_text())
    job.update(spec["overrides"])
    if job.get("candidate") not in CANDIDATES:
        raise SystemExit(f"job candidate {job.get('candidate')!r} is not assembled here")
    return job


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
    parser.add_argument("candidate", nargs="?", default="austin-911-response",
                        choices=sorted(CANDIDATES),
                        help="whose source/job.json supplies the job id and sizing")
    args = parser.parse_args(argv)

    spec = CANDIDATES[args.candidate]
    job = load_job(spec)
    target = ROOT / ".factory" / "jobs" / job["id"]
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
