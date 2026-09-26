#!/usr/bin/env python3
"""Refuse to measure an artifact that is not the one that passed qualification.

The baseline job rebuilds the extract from source rather than downloading it, because the
worker has no credential to read the private staging release and bulk data is not meant to
travel. A rebuild is only acceptable if it is byte-identical to the accepted artifact, so this
checks every component against the recorded hashes and exits non-zero on any difference.

Usage: verify_artifact.py <extract-dir> <expected_artifact.json>
"""
import hashlib
import json
import sys
from pathlib import Path


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    extract, expected_path = Path(sys.argv[1]), Path(sys.argv[2])
    expected = json.loads(expected_path.read_text())
    problems = []
    for relative, want in sorted(expected["files"].items()):
        path = extract / relative
        if not path.is_file():
            problems.append(f"{relative}: missing")
            continue
        size = path.stat().st_size
        digest = sha256_of(path)
        if size != want["bytes"] or digest != want["sha256"]:
            problems.append(f"{relative}: got {digest[:16]} / {size}B, "
                            f"expected {want['sha256'][:16]} / {want['bytes']}B")
        else:
            print(f"  match  {relative:22} {digest[:16]}...")
    if problems:
        print(f"\nREBUILD IS NOT THE ACCEPTED ARTIFACT ({expected['job']}):", file=sys.stderr)
        for problem in problems:
            print(f" - {problem}", file=sys.stderr)
        return 1
    print(f"\nVERIFIED: rebuild matches artifact_version "
          f"{expected['artifact_version'][:16]}... from job {expected['job']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())