#!/usr/bin/env python3
"""Plan release transfers, or execute an explicitly approved staged visibility change.

The default legacy transfer plan is read-only. Bulk transfer belongs on workers;
--execute still cannot upload data from this coordinator.

For a current verified private package, --flip-plan prints the exact artifact,
independent review and both destination commits for the operator. After the
operator approves that plan, record their words and source in the candidate's
approval.json. --flip checks it and uses the common two-platform path. No
manifest, data file or tag is changed. See docs/PUBLICATION-APPROVALS.md.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from factory.license_contract import validate as validate_license
from factory.frozen import historical_files
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
    from factory.suitability import publication_check
    errors, _ = publication_check(ROOT, manifest, package=release_dir)
    if errors:
        raise SystemExit('; '.join(errors))
    declared = json.loads((ROOT / "candidates" / candidate / "release.json").read_text())
    docs = tuple(DOCS) + tuple(declared.get("required_docs", ()))
    if not historical_files(release_dir):
        terms=validate_license(release_dir,manifest=manifest)
        evidence=('LICENSE-EVIDENCE.json','license-receipt.json','card.md')
        evidence += tuple(name for name in sorted(terms['receipt']['inputs']) if name.startswith('licensing/'))
        docs=tuple(dict.fromkeys(docs+evidence))
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
    parser.add_argument("--flip-plan", action="store_true", help="print the exact two-destination approval plan")
    parser.add_argument("--flip", action="store_true", help="execute the recorded digest-bound approval on both destinations")
    args = parser.parse_args()
    if args.flip or args.flip_plan:
        if args.execute or args.stream_test or args.confirm_publication or (args.flip and args.flip_plan):
            parser.error("use the approved flip operation by itself")
        from factory import publication
        result = publication.execute(ROOT, args.candidate) if args.flip else publication.review_plan(ROOT, args.candidate)
        print(json.dumps(result, indent=2))
        return 0

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
    from factory.publication import approved_plan
    approved_plan(ROOT, args.candidate)
    if not args.confirm_publication:
        raise SystemExit("refusing to publish: pass --confirm-publication with --execute")
    raise SystemExit("the legacy upload step is not implemented; use worker transfers and the "
                     "documented digest-bound --flip workflow for verified private staging")


if __name__ == "__main__":
    sys.exit(main())
