#!/usr/bin/env python3
"""Check a copy of the published repository against MANIFEST.json's recorded hashes.

This is what makes "clone and verify" a real check rather than a claim: every published file -
code, baseline runner, docs, download tooling - is hashed and compared with the manifest, so a
consumer can tell that what they cloned is what was released.

Usage: verify_package.py <repo-root>
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
    root = Path(sys.argv[1])
    manifest = json.loads((root / "MANIFEST.json").read_text())
    expected = manifest["package_files"]
    problems, checked = [], 0
    for relative, digest in sorted(expected.items()):
        path = root / relative
        if not path.is_file():
            problems.append(f"{relative}: missing")
            continue
        checked += 1
        actual = sha256_of(path)
        if actual != digest:
            problems.append(f"{relative}: {actual[:16]} != recorded {digest[:16]}")

    # Anything shipped that the manifest does not list is also worth knowing about.
    extra = [path.relative_to(root).as_posix() for path in sorted(root.rglob("*"))
             if path.is_file() and path.name != "MANIFEST.json"
             and path.relative_to(root).as_posix() not in expected
             and ".git" not in path.parts]
    print(f"  checked {checked} files against MANIFEST.json")
    if extra:
        print(f"  note: {len(extra)} file(s) present but not in the manifest: {extra[:5]}")
    if problems:
        print("PACKAGE VERIFICATION FAILED:", file=sys.stderr)
        for problem in problems:
            print(f" - {problem}", file=sys.stderr)
        return 1
    print("  PACKAGE OK: every listed file matches its recorded hash")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
