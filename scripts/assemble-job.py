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
and the sizing that fits the job), copies the canonical files into an ignored staging directory,
verifies the result against the worker's own bundle rules, and prints the directory to launch:

    python3 scripts/assemble-job.py austin-911-response
    sh scripts/scout-factory worker plan .factory/jobs/austin-003/job.json
    sh scripts/scout-factory worker launch .factory/jobs/austin-003/job.json

The job **id comes from the candidate's `source/job.json`**, not from this file. OPERATIONS
says each attempt gets a new job id, and the first version of this script hardcoded the id in
two places, which made a second attempt impossible to express.

The `austin-baseline` bundle additionally copies the harness benchmark's own `train.py`,
`validate.py` and `validate.sh` **verbatim** out of the read-only benchmark clone, and records
their hashes so the report can prove the runner was not modified. If the clone is absent the
assembler fails rather than substituting a stand-in.

Nothing here touches the network or the cloud, and the staging directory is regenerated from
scratch on every run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_SUFFIXES = (".py", ".sh", ".json", ".txt", ".toml", ".yaml", ".yml", ".md")
# Standard checksum files have no suffix; mirrors factory.worker.BARE_ALLOWED_NAMES.
BARE_ALLOWED_NAMES = {"SHA256SUMS", "SHA256SUMS.txt"}
BUNDLE_LIMIT = 2 * 1024 * 1024
BENCHMARK = Path(os.environ.get("FACTORY_BENCHMARK_ROOT", "/opt/data/harness_benchmark"))
RUNNER_TEMPLATE = "task_template"

# Bundles keyed by the name you pass on the command line. Each reads its job id and sizing from
# its own source/job.json, so identity lives in exactly one place.
BUNDLES = {
    # Build the extract, then qualify the exact artifact on the worker.
    "austin-911-response": {
        "job_file": "candidates/austin-911-response/source/job.json",
        "files": [
            ("build.py", "candidates/austin-911-response/source/build.py"),
            ("run.sh", "candidates/austin-911-response/source/run.sh"),
            ("qualify_dataset.py", "skills/dataset-qualification/scripts/qualify_dataset.py"),
        ],
        "overrides": {
            "command": ["sh", "/workspace/run.sh"],
            "timeout_minutes": 120,
            "lifetime_minutes": 150,
            "max_disk_mb": 3072,
            "max_artifact_mb": 600,
        },
    },
    # Rebuild the accepted artifact, prove it is the accepted artifact, then run the benchmark's
    # own training and validation contract against it. The contract only - no agent harness.
    "austin-baseline": {
        "job_file": "candidates/austin-911-response/baseline/source/job.json",
        "files": [
            ("build.py", "candidates/austin-911-response/source/build.py"),
            ("run.sh", "candidates/austin-911-response/baseline/source/run.sh"),
            ("materialize.py", "candidates/austin-911-response/baseline/source/materialize.py"),
            ("verify_artifact.py", "candidates/austin-911-response/baseline/source/verify_artifact.py"),
            ("report.py", "candidates/austin-911-response/baseline/source/report.py"),
            ("expected_artifact.json",
             "candidates/austin-911-response/baseline/expected_artifact.json"),
        ],
        # Copied verbatim from the read-only harness benchmark clone.
        "runner_files": ["train.py", "validate.py", "validate.sh"],
        "overrides": {
            "command": ["sh", "/workspace/run.sh"],
            "timeout_minutes": 60,
            "lifetime_minutes": 120,
            "max_disk_mb": 3072,
            "max_artifact_mb": 50,
        },
    },
    # Fresh-consumer check: the published repository tree plus the run script, against the release
    # assets fetched by the worker host. No dataset-factory access, and no credential in the
    # container.
    "austin-consumer": {
        "job_file": "candidates/austin-911-response/consumer/source/job.json",
        "files": [
            ("run.sh", "candidates/austin-911-response/consumer/source/run.sh"),
            ("verify_package.py", "candidates/austin-911-response/consumer/source/verify_package.py"),
        ],
        # The whole published package, laid out under repo/ so the container sees the repository
        # exactly as a consumer would after cloning it.
        "trees": [("repo", "release/austin-911-response")],
        "overrides": {
            "command": ["sh", "/workspace/run.sh"],
            "timeout_minutes": 60,
            "lifetime_minutes": 120,
            "max_disk_mb": 3072,
            "max_artifact_mb": 50,
        },
    },
    # Build both levels of the NOAA tide-flooding task, then gate each exact artifact on the worker.
    "noaa-tide-flooding": {
        "job_file": "candidates/noaa-tide-flooding/source/job.json",
        "files": [
            ("build.py", "candidates/noaa-tide-flooding/build.py"),
            ("run.sh", "candidates/noaa-tide-flooding/source/run.sh"),
            # The frozen station list is a build input, not a constant: the panel was computed from
            # the source, so the same list has to travel with the builder.
            ("station_list_result.json",
             "candidates/noaa-tide-flooding/station_list_result.json"),
            ("qualify_dataset.py", "skills/dataset-qualification/scripts/qualify_dataset.py"),
        ],
        "overrides": {
            "command": ["sh", "/workspace/run.sh"],
            "timeout_minutes": 120,
            "lifetime_minutes": 150,
            "max_disk_mb": 3072,
            "max_artifact_mb": 600,
        },
    },
}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_job(spec: dict) -> dict:
    """The candidate's own job.json is the source of truth for identity and sizing."""
    path = ROOT / spec["job_file"]
    if not path.is_file():
        raise SystemExit(f"candidate job file is missing: {spec['job_file']}")
    job = json.loads(path.read_text())
    job.update(spec["overrides"])
    if not (ROOT / "candidates" / str(job.get("candidate"))).is_dir():
        raise SystemExit(f"job candidate {job.get('candidate')!r} has no candidate directory")
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
        if path.suffix not in ALLOWED_SUFFIXES and path.name not in BARE_ALLOWED_NAMES:
            raise SystemExit(f"assembled bundle has an unexpected suffix: {relative}")
        total += path.stat().st_size
    if total > BUNDLE_LIMIT:
        raise SystemExit(f"assembled bundle is {total} bytes, over the {BUNDLE_LIMIT} limit")
    return total


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Assemble a worker job directory")
    parser.add_argument("bundle", nargs="?", default="austin-911-response",
                        choices=sorted(BUNDLES),
                        help="which bundle to assemble; the job id comes from its source/job.json")
    args = parser.parse_args(argv)

    spec = BUNDLES[args.bundle]
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
                         "bytes": source.stat().st_size, "sha256": sha256_of(source)})

    for destination, source_dir in spec.get("trees", []):
        # A whole directory, laid out under a subdirectory of the bundle - used to give a job the
        # published package exactly as a consumer would see it after cloning.
        tree_root = ROOT / source_dir
        if not tree_root.is_dir():
            raise SystemExit(f"canonical tree is missing: {source_dir}")
        for path in sorted(tree_root.rglob("*")):
            if not path.is_file() or ".git" in path.parts:
                continue
            inside = path.relative_to(tree_root)
            out = target / destination / inside
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, out)
            recorded.append({"bundled_as": f"{destination}/{inside.as_posix()}",
                             "source": f"{source_dir}/{inside.as_posix()}",
                             "bytes": path.stat().st_size, "sha256": sha256_of(path)})

    runner = {}
    if spec.get("runner_files"):
        # Taken from the benchmark clone itself. Never vendored, never re-implemented: if the
        # clone is missing the bundle cannot be assembled, because a substitute would not be the
        # runner whose contract this job claims to exercise.
        if not BENCHMARK.is_dir():
            raise SystemExit(f"the harness benchmark clone is missing at {BENCHMARK}; "
                             f"set FACTORY_BENCHMARK_ROOT or skip this bundle")
        for name in spec["runner_files"]:
            source = BENCHMARK / RUNNER_TEMPLATE / name
            if not source.is_file():
                raise SystemExit(f"runner file is missing from the benchmark clone: {source}")
            shutil.copyfile(source, target / name)
            digest = sha256_of(source)
            record = {"bundled_as": name, "source": str(source),
                      "bytes": source.stat().st_size, "sha256": digest}
            recorded.append(record)
            runner[name] = digest
        (target / "runner_files.json").write_text(json.dumps(runner, indent=1) + "\n")

    job["source_files"] = recorded
    (target / "job.json").write_text(json.dumps(job, indent=1) + "\n")
    # One source of truth for the id, readable inside the container, so no script has to pin it.
    (target / "job_id.txt").write_text(job["id"] + "\n")

    total = check_bundle(target)
    print(json.dumps({
        "job_directory": str(target.relative_to(ROOT)),
        "job_id": job["id"],
        "bundle_bytes": total,
        "files": recorded,
        "runner_files": runner,
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