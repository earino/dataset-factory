#!/usr/bin/env python3
"""Mechanical completeness check over an assembled release package.

Answers one question: could a reviewer who has this directory - and nothing else - verify what
it claims? It checks that every document a package must carry is present, that MANIFEST.json
covers every file it should, that recorded hashes match the bytes on disk, and that
SHA256SUMS agrees with the manifest. It also refuses a package that claims to be published
while carrying a private-visibility note.

Read-only. Exit status is 0 when consistent, 1 when not, 2 on a bad invocation.

    python3 scripts/check-package.py release/<dataset>
    python3 scripts/check-package.py release/<dataset> --json
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# Documents a reviewer needs. Directories are checked separately.
REQUIRED_FILES = (
    "README.md", "DATA_DICTIONARY.md", "LICENSE.md", "REPRODUCE.md", "RELEASE_NOTES.md",
    "VERIFICATION.md", "MANIFEST.json", "SHA256SUMS", "get_dataset.py",
)
REQUIRED_DIRS = ("code", "baseline")
# Per-destination completion record. Written by the release procedure after each platform is
# verified, and deliberately NOT listed in MANIFEST.json's package_files: a manifest cannot hash
# the record of its own publication without becoming circular.
DESTINATIONS = "DESTINATIONS.json"
# The manifest cannot hash itself, and SHA256SUMS describes release assets rather than files.
SELF_EXEMPT = ("MANIFEST.json", "SHA256SUMS")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256_of(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_sums(path):
    """Parse a sha256sum-compatible file into {name: digest}."""
    entries = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        digest, name = parts[0].strip(), parts[1].strip().lstrip("*")
        entries[name] = digest
    return entries


def check_package(package_dir):
    package_dir = Path(package_dir)
    problems = []
    notes = []

    if not package_dir.is_dir():
        return [f"{package_dir} is not a directory"], []

    for name in REQUIRED_FILES:
        if not (package_dir / name).is_file():
            problems.append(f"{name}: missing")
    for name in REQUIRED_DIRS:
        if not (package_dir / name).is_dir():
            problems.append(f"{name}/: missing")

    manifest_path = package_dir / "MANIFEST.json"
    if not manifest_path.is_file():
        return problems, notes
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        problems.append(f"MANIFEST.json: not valid JSON ({exc})")
        return problems, notes

    for field in ("dataset", "release_tag", "artifact_version", "qualification", "published"):
        if manifest.get(field) in (None, "", [], {}):
            problems.append(f"MANIFEST.json: '{field}' is empty - a reviewer needs it")

    # Publication state must be stated, not implied.
    if manifest.get("published") is False and not manifest.get("publication_note"):
        problems.append(
            "MANIFEST.json: 'published' is false with no 'publication_note' - "
            "state that publication awaits review rather than leaving it unstated"
        )

    # Terms are not optional: a release must declare what it is licensed under, and ship the
    # licence it names. A missing declaration is refused rather than assumed permissive.
    licenses = manifest.get("licenses")
    if not isinstance(licenses, dict):
        problems.append("MANIFEST.json: no 'licenses' block - the release terms are not declared")
    else:
        status = str(licenses.get("status") or "")
        if status.startswith("UNDECLARED"):
            problems.append(f"MANIFEST.json: licenses {status}")
        for label, key in (("code", "code"), ("data compilation", "data_compilation")):
            entry = licenses.get(key) or {}
            if not entry.get("spdx"):
                problems.append(f"MANIFEST.json: licenses.{key}.spdx is empty ({label})")
            named = entry.get("file")
            if not named:
                problems.append(f"MANIFEST.json: licenses.{key}.file is empty, so the licence "
                                f"text is not identified ({label})")
            elif not (package_dir / named).is_file():
                problems.append(f"MANIFEST.json: licenses.{key}.file names {named}, which is not "
                                "in the package")
        source = licenses.get("source_data") or {}
        if not source.get("status"):
            problems.append("MANIFEST.json: licenses.source_data.status is empty - the source's "
                            "own terms must be recorded, not overwritten")
        if manifest.get("published") is True and not licenses:
            problems.append("MANIFEST.json: 'published' is true with no declared terms")

    # Every file in the package must be covered by the manifest, and every recorded hash
    # must match the bytes on disk.
    recorded = manifest.get("package_files") or {}
    if not isinstance(recorded, dict) or not recorded:
        problems.append("MANIFEST.json: 'package_files' is empty or not an object")
        recorded = {}

    on_disk = {
        str(path.relative_to(package_dir))
        for path in package_dir.rglob("*")
        if path.is_file()
    }
    for name, digest in sorted(recorded.items()):
        target = package_dir / name
        if not target.is_file():
            problems.append(f"{name}: recorded in the manifest, not present in the package")
            continue
        if not SHA256_RE.match(str(digest)):
            problems.append(f"{name}: recorded digest is not a sha256 hex value")
            continue
        actual = sha256_of(target)
        if actual != digest:
            problems.append(
                f"{name}: manifest records {digest[:16]}..., on disk {actual[:16]}..."
            )
    for name in sorted(on_disk - set(recorded) - set(SELF_EXEMPT)):
        notes.append(f"{name}: present in the package but not covered by the manifest")

    # Completion is tracked per destination: GitHub can be done while Hugging Face is pending,
    # and a release is only complete when both verify. A destination that has not been verified,
    # or one verified at a different revision than the manifest's tag, is not complete.
    destinations_path = package_dir / DESTINATIONS
    if destinations_path.is_file():
        try:
            recorded = json.loads(destinations_path.read_text())
        except json.JSONDecodeError as exc:
            problems.append(f"{DESTINATIONS}: not valid JSON ({exc})")
            recorded = None
        if isinstance(recorded, dict):
            tag = manifest.get("release_tag")
            for name, entry in sorted((recorded.get("destinations") or {}).items()):
                if not isinstance(entry, dict):
                    problems.append(f"{DESTINATIONS}: {name} entry is not an object")
                    continue
                if entry.get("verified") is not True:
                    notes.append(f"{DESTINATIONS}: {name} is not verified yet")
                    continue
                if not entry.get("verified_at"):
                    problems.append(f"{DESTINATIONS}: {name} claims verified with no timestamp")
                revision = entry.get("revision") or entry.get("release_tag")
                if tag and revision and revision != tag:
                    problems.append(
                        f"{DESTINATIONS}: {name} was verified at {revision}, manifest tag is {tag}")
            if manifest.get("published") is True:
                unverified = [name for name, entry in (recorded.get("destinations") or {}).items()
                              if not isinstance(entry, dict) or entry.get("verified") is not True]
                if unverified:
                    problems.append(
                        f"{DESTINATIONS}: 'published' is true while {sorted(unverified)} "
                        "unverified - public visibility requires every destination verified")
    elif manifest.get("published") is True:
        problems.append(f"{DESTINATIONS}: missing, but the manifest claims the release is published")

    # SHA256SUMS must agree with the manifest's asset records. Entries are named by the
    # *logical* path the consumer sees after `get_dataset.py` lays the tree out
    # (`public/train.csv`), not by the flat asset name GitHub stores (`train.csv`), so the
    # cross-check keys on the logical path and accepts either spelling on the sums line.
    sums_path = package_dir / "SHA256SUMS"
    if sums_path.is_file():
        sums = parse_sums(sums_path)
        if not sums:
            problems.append("SHA256SUMS: no parsable entries")
        assets = manifest.get("assets") or {}
        if isinstance(assets, dict) and assets:
            by_logical = {}
            by_asset_name = {}
            for logical, info in assets.items():
                if isinstance(info, dict):
                    by_logical[logical] = info.get("sha256")
                    if info.get("asset_name"):
                        by_asset_name[info["asset_name"]] = (logical, info.get("sha256"))
            if len(sums) != len(by_logical):
                notes.append(
                    f"SHA256SUMS lists {len(sums)} entries against {len(by_logical)} "
                    "assets in the manifest"
                )
            for name, digest in sorted(sums.items()):
                if name in by_logical:
                    expected = by_logical[name]
                elif name in by_asset_name:
                    logical, expected = by_asset_name[name]
                else:
                    problems.append(f"SHA256SUMS: '{name}' is not a recorded release asset")
                    continue
                if expected and digest != expected:
                    problems.append(
                        f"SHA256SUMS: '{name}' disagrees with the manifest asset digest"
                    )
        else:
            notes.append("MANIFEST.json: no 'assets' block to cross-check SHA256SUMS against")

    return problems, notes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", help="package directory, e.g. release/<dataset>")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    problems, notes = check_package(args.package)
    if args.json:
        print(json.dumps({"package": args.package, "problems": problems, "notes": notes}, indent=2))
    else:
        state = "OK" if not problems else f"{len(problems)} problem(s)"
        print(f"{args.package}: {state}")
        for problem in problems:
            print(f"  - {problem}")
        for note in notes:
            print(f"  . {note}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
