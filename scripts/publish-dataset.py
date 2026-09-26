#!/usr/bin/env python3
"""Prepare - and only on explicit request, execute - the public release of a dataset.

Publication is a reviewed step, so this script **does nothing by default**: it prints the exact
plan (repository, documents, release, assets, sizes, hashes, provenance) and exits. Actually
publishing needs both `--execute` and `--confirm-publication`, because a public repository and a
public release are not reversible the way a merge commit is.

The token is read from its `_FILE` path and never printed.

    python3 scripts/publish-dataset.py austin-911-response     # the plan, and nothing else

**What is verified and what is not.** `--stream-test` resolves the staged artifact to concrete
asset ids through the worker-written `manifest.json`, so the mapping from artifact files to
release assets is checked against recorded evidence rather than assumed. The **upload step
itself is not implemented here and has not been run**: copying ~131 MB from a private release to
a public one needs either a machine that can hold the bytes or a worker-side publish path, and
neither exists yet. This script therefore stops at a plan instead of pretending to publish.

## The publication steps, for when the operator approves

1. `python3 scripts/release-manifest.py austin-911-response` - regenerate MANIFEST.json and
   SHA256SUMS from recorded evidence.
2. `python3 scripts/publish-dataset.py austin-911-response --stream-test` - confirm the plan and
   that every artifact file maps to exactly one staged asset.
3. Create the public repository `earino/austin-911-response` and commit the documents in
   `release/austin-911-response/` as its initial commit.
4. Create release `v2026.09` and attach the five artifact files under the names in the plan.
   Verify each uploaded asset's SHA-256 against `SHA256SUMS` after upload, not before.
5. Add the public repository URL to the release README, and record the publication in the
   factory's `STATE.md` and the candidate's `record.json`.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = "earino"
STAGING_REPO = "earino/dataset-factory-staging"
TOKEN_FILE = Path(os.environ.get("FACTORY_GITHUB_TOKEN_FILE",
                                 "/opt/data/.secrets/github-staging.token"))
# Everything the published repository carries; `code/` and `baseline/` are trees of these files.
# The documents every release carries. A dataset adds whatever only it needs in
# candidates/<id>/release.json under "required_docs": this list used to name Austin's clock-offset
# script, so a dataset with no such script was refused for not shipping one.
DOCS = ("README.md", "DATA_DICTIONARY.md", "LICENSE.md", "REPRODUCE.md", "MANIFEST.json",
        "SHA256SUMS", "RELEASE_NOTES.md", "VERIFICATION.md", "measurements.json",
        "get_dataset.py", "code/build.py", "code/qualify_dataset.py", "code/materialize.py",
        "baseline/README.md", "baseline/train.py", "baseline/validate.py", "baseline/validate.sh",
        "baseline/reproduce_baseline.sh")
# Artifact path inside the extract -> asset name inside the public release.
ASSET_NAMES = {
    "public/train.csv": "task/public/train.csv",
    "public/eval.csv": "task/public/eval.csv",
    "private/holdout.csv": "task/private/holdout.csv",
    "meta.json": "task/meta.json",
    "quality.json": "task/quality.json",
}


def token() -> str:
    value = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if value:
        return value.strip()
    if not TOKEN_FILE.is_file():
        raise SystemExit(f"no token at {TOKEN_FILE} (set FACTORY_GITHUB_TOKEN_FILE)")
    return TOKEN_FILE.read_text().strip()


def gh(args: list[str], token_value: str) -> str:
    done = subprocess.run(["gh", *args], capture_output=True, text=True,
                          env={**os.environ, "GH_TOKEN": token_value})
    if done.returncode:
        raise SystemExit(f"gh {' '.join(args[:3])} failed: {done.stderr.strip()[:400]}")
    return done.stdout


def plan(candidate: str) -> dict:
    release_dir = ROOT / "release" / candidate
    manifest_path = release_dir / "MANIFEST.json"
    if not manifest_path.is_file():
        raise SystemExit(f"no MANIFEST.json for {candidate}; run scripts/release-manifest.py")
    manifest = json.loads(manifest_path.read_text())
    declared = json.loads((ROOT / "candidates" / candidate / "release.json").read_text())
    docs = tuple(DOCS) + tuple(declared.get("required_docs", ()))
    missing = [name for name in docs if not (release_dir / name).is_file()]
    if missing:
        raise SystemExit(f"release documents are missing: {missing}")
    # The asset mapping is the manifest's own layout, so it follows the dataset instead of the
    # flat single-level shape this file used to hardcode.
    global ASSET_NAMES
    ASSET_NAMES = {relative: key for key, relative in manifest["layout"].items()}
    files = manifest["files"]
    unknown = [path for path in files if path not in ASSET_NAMES]
    if unknown:
        raise SystemExit(f"manifest lists files with no asset mapping: {unknown}")
    return {
        "repository": f"{OWNER}/{candidate}",
        "visibility": "public",
        "tag": f"v{manifest['release_version']}",
        "artifacts": [
            {"asset": ASSET_NAMES[path], "extract_path": path,
             "bytes": files[path]["bytes"], "sha256": files[path]["sha256"]}
            for path in ASSET_NAMES
        ],
        "documents": list(docs),
        "total_bytes": sum(files[path]["bytes"] for path in ASSET_NAMES),
        "artifact_version": manifest["artifact_version"],
        "artifact_job": manifest["artifact_job"],
        "staging_release": manifest.get("staging_release"),
        "staging_release_tag": manifest.get("staging_release_tag"),
        "construction_commit": manifest["construction_commit"],
    }


def render(step: dict) -> None:
    name = step["repository"].split("/")[-1]
    print(f"would create   {step['visibility']} repository {step['repository']}")
    print(f"                 initial commit from release/{name}/: {', '.join(step['documents'])}")
    print(f"would create   release {step['tag']} on {step['repository']}")
    print(f"                 with {len(step['artifacts'])} assets, "
          f"{step['total_bytes'] / 1e6:.1f} MB, streamed from {STAGING_REPO}")
    for item in step["artifacts"]:
        print(f"                   {item['asset']:24} {item['bytes']:>10,} B  "
              f"{item['sha256'][:16]}...")
    print(f"                 artifact_version {step['artifact_version'][:16]}... "
          f"from commit {step['construction_commit'][:8]}")
    print("\nNothing has been done. No token is printed, and no asset is written to this host.")


def load_staging_release(step: dict, token_value: str) -> dict:
    """By id when the manifest records it, else by tag.

    Draft releases 404 through `releases/tags/<tag>`, so the id - captured when the artifact was
    accepted - is the reliable handle.
    """
    release_id = step.get("staging_release")
    if release_id:
        return json.loads(gh(["api", f"repos/{STAGING_REPO}/releases/{int(release_id)}"],
                             token_value))
    return json.loads(gh(["api", f"repos/{STAGING_REPO}/releases/tags/"
                                 f"{step['staging_release_tag']}"], token_value))


def resolve_staged_assets(step: dict, token_value: str) -> dict[str, int]:
    """Map each artifact file to exactly one staged asset, via the worker's own manifest.

    The staging release stores parts named `file-NNNN-part-0000`; the worker-written
    `manifest.json` is what maps them back to original paths, so the mapping is read from the
    evidence rather than inferred from ordering.

    Looked up by **release id**, because the staging release is a draft and drafts have no tag
    namespace: `releases/tags/job-<id>` returns 404 for a release that plainly exists.
    """
    release = load_staging_release(step, token_value)
    assets = json.loads(gh(["api", f"repos/{STAGING_REPO}/releases/{release['id']}/assets",
                            "--paginate"], token_value))
    by_name = {item["name"]: item for item in assets}
    manifest = json.loads(gh(["api", f"repos/{STAGING_REPO}/releases/assets/"
                                     f"{by_name['manifest.json']['id']}",
                              "-H", "Accept: application/octet-stream"], token_value))
    resolved = {}
    for entry in manifest["assets"]:
        for wanted in ASSET_NAMES:
            if entry["file"] == wanted or entry["file"].endswith("/" + wanted):
                resolved[wanted] = by_name[entry["name"]]["id"]
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-publication", action="store_true")
    parser.add_argument("--stream-test", action="store_true",
                        help="resolve the staged artifact to asset ids; publishes nothing")
    args = parser.parse_args()

    step = plan(args.candidate)
    render(step)

    if args.stream_test:
        resolved = resolve_staged_assets(step, token())
        print(f"\n[resolve] {len(resolved)}/{len(ASSET_NAMES)} artifact files map to a staged "
              f"asset:")
        for path in sorted(ASSET_NAMES):
            asset_id = resolved.get(path)
            print(f"  {path:22} -> {'asset ' + str(asset_id) if asset_id else 'NOT FOUND'}")
        if len(resolved) != len(ASSET_NAMES):
            raise SystemExit("not every artifact file resolves to a staged asset")
        print("  every file resolves; the upload step is not implemented (see the module docs)")
        return 0

    if not args.execute:
        return 0
    if not args.confirm_publication:
        raise SystemExit("refusing to publish: pass --confirm-publication with --execute")
    raise SystemExit("the upload step is not implemented; see the module docs for the five "
                     "publication steps and ask the operator to approve before running them")


if __name__ == "__main__":
    sys.exit(main())