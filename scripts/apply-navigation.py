#!/usr/bin/env python3
"""Apply the managed website navigation block to a package README, then refresh the manifest.

Usage: python3 scripts/apply-navigation.py <dataset>

The publication pipeline writes the navigation block into the repository and the Hub card, but the
package README on disk does not have it until this runs. A document refresh that pushes the package
README without re-applying the block strips the only link a reader has to the dataset's own page,
and the site verification then fails with "Destination navigation is missing". So: run this after
editing documents and before pushing them, once the site is live.

Nothing is invented: the record comes from the same builder the publication plan uses, the block is
the pipeline's own `links()` text, and the block is only applied when DESTINATIONS.json records a
verified site for this release.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from factory.site_model import links, linked_readme, project  # noqa: E402


def manifest(candidate: str) -> None:
    """Regenerate MANIFEST.json so package_files hash the README that is actually on disk."""
    done = subprocess.run([sys.executable, str(ROOT / "scripts/release-manifest.py"), candidate],
                          capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit("release-manifest.py failed: " + (done.stderr or done.stdout)[-400:])


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply-navigation.py <dataset>")
    candidate = sys.argv[1]
    release = ROOT / "release" / candidate
    destinations = json.loads((release / "DESTINATIONS.json").read_text())
    site = (destinations.get("publication") or {}).get("site") or {}
    if site.get("status") != "verified":
        print(f"{candidate}: no verified site recorded; no navigation block to apply")
        return 0

    # The manifest must describe the current files before the record builder will accept them,
    # so hash first, apply the block, then hash again.
    manifest(candidate)
    editorial = json.loads((ROOT / "sites" / f"{candidate}.json").read_text())
    config = json.loads((ROOT / "config" / "sites.json").read_text())
    record = project(release, editorial, config)
    readme = release / "README.md"
    original = readme.read_text()
    updated = linked_readme(original, record)
    if updated != original:
        readme.write_text(updated)
    manifest(candidate)

    published = json.loads((release / "MANIFEST.json").read_text())
    hashed = published["package_files"].get("README.md")
    from factory.site_model import digest
    print(json.dumps({
        "dataset": candidate,
        "site": site.get("page"),
        "block_applied": updated != original,
        "block_present": links(record) in readme.read_text(),
        "readme_matches_manifest": hashed == digest(readme.read_bytes()),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
