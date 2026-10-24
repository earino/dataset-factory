#!/usr/bin/env python3
"""Assemble the source-only smoke bundle for an adapter smoke job (issue #17).

Reads a smoke job spec, materializes every source it names into ONE JSON file —
the ``source/pinned.json`` payload the runtime places inside the worker source
bundle — and updates the job in place:

  smoke.pinned_sources      {bundle path: sha256}     — exact relative-path→sha256 map
  smoke.source_bundle       {file, sha256, bytes, repo_commit} — the pinned.json
                                                            payload file itself
  smoke.source_provenance   {bundle path: provenance}  — per-file origin binding
  smoke.expected_sha256     {logical name: sha256}     — keyed by the runtime's fetch
                                                        loop names; smoke.asset_names
                                                        maps each to its REAL GitHub
                                                        release asset name
  smoke.artifact_version    the frozen manifest's artifact_version, copied
                            programmatically — never transcribed

The pinned payload carries exactly the runtime schema:

  {"harness_commit": "<40hex>",
   "files": {"image/Dockerfile": {"base64": "...", "sha256": "..."}, ...}}

The harness sources are read from the read-only pinned harness checkout via
``git show <commit>:<path>``, so provenance binds to the commit, never the
worktree state. Repo sources are read from this repository's working tree and
bound to the recorded HEAD commit (kept in the job's provenance sidecar, not in
the runtime payload). The bundle is code-only: ``.git``, ``data``, ``runs``,
``results``, ``auth`` and every ``.csv`` are refused, so no bulk row can enter.
Image-context requirements (Dockerfile, .dockerignore, uv.lock,
pyproject.toml, bench sources) are enforced, not assumed.

With ``--gh-verify`` (default when ``gh`` is available) the assembler also
confirms the release's REAL asset names and sizes from the GitHub API and
re-downloads only the two small metadata assets to confirm their digests live;
the CSVs are never fetched.

Exit status is 0 only when the bundle verifies end to end.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HARNESS = Path("/opt/data/harness_benchmark")
FORBIDDEN_PARTS = {".git", "data", "runs", "results", "auth"}
FORBIDDEN_SUFFIXES = {".csv", ".env"}
REQUIRED_IMAGE_FILES = ("image/Dockerfile", "image/.dockerignore", "image/uv.lock",
                        "image/pyproject.toml")
PUBLIC_LOGICAL = ("public/train.csv", "public/eval.csv", "meta.json", "quality.json")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                            text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:2])} failed in {cwd}: "
                           f"{result.stderr.strip()[:200]}")
    return result.stdout.strip()


def _safe_bundle_path(path: str) -> None:
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts or path.startswith("~"):
        raise ValueError(f"unsafe bundle path: {path!r}")
    parts = set(candidate.parts)
    forbidden = parts & FORBIDDEN_PARTS
    if forbidden:
        raise ValueError(f"forbidden bundle path segment(s) {sorted(forbidden)} "
                         f"in {path!r}")
    if candidate.suffix in FORBIDDEN_SUFFIXES:
        raise ValueError(f"source-only bundle refuses bulk/secret suffix "
                         f"{candidate.suffix!r} in {path!r}")


def read_source(spec: str, harness: Path, harness_commit: str,
                repo_commit: str) -> tuple[bytes, str]:
    """Return (content, provenance) for a source spec.

    Forms: ``harness:<path>`` (read from the pinned harness commit),
    ``repo:<path>`` (read from this checkout's working tree) and
    ``repo:<path>@<ref>`` (read from a resolved repository commit — used to
    bundle the runtime owner's adapter from their branch). Provenance always
    records the 40-hex commit the bytes were read from.
    """
    origin, sep, relative = spec.partition(":")
    if not sep or relative.startswith("/"):
        raise ValueError(f"source spec must be 'harness:<path>' or 'repo:<path>': {spec!r}")
    if origin == "harness":
        # Bind to the commit, not the worktree: the read-only checkout could be
        # dirty or moved, and the bundle must reproduce from the pin alone.
        probe = subprocess.run(["git", "-C", str(harness), "show",
                                f"{harness_commit}:{relative}"],
                               capture_output=True, timeout=120)
        if probe.returncode != 0:
            raise FileNotFoundError(f"harness@{harness_commit[:12]} has no {relative!r}")
        return probe.stdout, f"harness@{harness_commit}:{relative}"
    if origin == "repo":
        path_part, marker, ref = relative.rpartition("@")
        if marker:
            relative, resolved = path_part, _git(["rev-parse", f"{ref}^{{commit}}"],
                                                  REPO_ROOT)
            probe = subprocess.run(["git", "-C", str(REPO_ROOT), "show",
                                    f"{resolved}:{relative}"],
                                   capture_output=True, timeout=120)
            if probe.returncode != 0:
                raise FileNotFoundError(f"repository commit {resolved[:12]} has no "
                                        f"{relative!r}")
            return probe.stdout, f"repo@{resolved}:{relative}"
        path = REPO_ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"repository has no {relative!r}")
        return path.read_bytes(), f"repo@{repo_commit[:12]}:{relative}"
    raise ValueError(f"unknown source origin {origin!r} in {spec!r}")


def fill_expected_assets(smoke: dict, dataset: str) -> None:
    """Pin expected_sha256 by LOGICAL name (the runtime's fetch loop key),
    record the REAL GitHub asset names and sizes from the frozen manifest, and
    carry the manifest's artifact_version programmatically."""
    manifest_path = REPO_ROOT / "release" / dataset / "MANIFEST.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"no frozen manifest for {dataset} at {manifest_path}")
    manifest = json.loads(manifest_path.read_text())
    assets = manifest.get("assets")
    if not isinstance(assets, dict) or not assets:
        raise ValueError(f"manifest for {dataset} carries no assets block; the real "
                         f"asset names cannot be derived without it")
    artifact_version = manifest.get("artifact_version")
    if not isinstance(artifact_version, str) or not re.fullmatch(r"[0-9a-f]{64}",
                                                                 artifact_version):
        raise ValueError(f"manifest for {dataset} carries no 64-hex artifact_version")
    expected, names, sizes = {}, {}, {}
    for logical in PUBLIC_LOGICAL:
        entry = assets.get(logical)
        if not entry or not entry.get("asset_name") or not entry.get("sha256"):
            raise ValueError(f"manifest assets block lacks {logical!r}")
        expected[logical] = entry["sha256"]
        names[logical] = entry["asset_name"]
        sizes[logical] = entry["bytes"]
    smoke["expected_sha256"] = expected
    smoke["asset_names"] = names
    smoke["asset_bytes"] = sizes
    smoke["artifact_version"] = artifact_version


def gh_verify(smoke: dict, dataset: str, release_tag: str) -> list[str]:
    """Confirm real asset names/sizes live; hash only the small metadata assets."""
    proof = []
    gh = shutil.which("gh")
    if not gh:
        return ["gh not available; live asset verification skipped"]
    listing = subprocess.run([gh, "api", f"repos/earino/{dataset}/releases/tags/"
                               f"{release_tag}"], capture_output=True, text=True, timeout=60)
    if listing.returncode != 0:
        raise RuntimeError(f"gh api could not read the {release_tag} release of "
                           f"{dataset}: {listing.stderr.strip()[:200]}")
    live = {asset["name"]: asset for asset in json.loads(listing.stdout).get("assets", [])}
    for logical, digest in sorted(smoke["expected_sha256"].items()):
        name = smoke["asset_names"][logical]
        asset = live.get(name)
        if asset is None:
            raise ValueError(f"release {release_tag} has no asset named {name!r}; the "
                             f"job would fetch from a nonexistent path")
        if asset["size"] != smoke["asset_bytes"][logical]:
            raise ValueError(f"asset {name!r} size {asset['size']} disagrees with the "
                             f"frozen manifest {smoke['asset_bytes'][logical]}")
        proof.append(f"asset {name!r} ({logical}): present, size matches frozen "
                     f"manifest ({asset['size']} bytes)")
        if name.endswith(".json"):
            # Small metadata file: download and confirm the digest live. CSVs are
            # never fetched here — size agreement plus the frozen manifest digest is
            # the bulk-free guarantee.
            fetch = subprocess.run([gh, "api", f"repos/earino/{dataset}/releases/"
                                     f"assets/{asset['id']}", "-H",
                                     "Accept: application/octet-stream"],
                                   capture_output=True, timeout=60)
            if fetch.returncode != 0 or sha256_bytes(fetch.stdout) != digest:
                raise ValueError(f"metadata asset {name!r} does not answer its "
                                f"manifest digest")
            proof.append(f"asset {name!r}: digest confirmed live "
                         f"({digest[:12]}…)")
    return proof


def assemble(job_path: Path, harness: Path, out_path: Path | None,
             verify: bool) -> dict:
    job = json.loads(job_path.read_text())
    smoke = job.get("smoke")
    if not isinstance(smoke, dict):
        raise ValueError("job carries no smoke object")
    dataset = job.get("dataset")
    release_tag = job.get("release_tag") or smoke.get("release_tag")
    harness_commit = smoke.get("harness_commit")
    if not (dataset and release_tag and harness_commit):
        raise ValueError("job needs dataset, release_tag and smoke.harness_commit")
    if not re.fullmatch(r"[0-9a-f]{40}", harness_commit):
        raise ValueError("smoke.harness_commit must be a 40-hex commit ID")

    actual = _git(["rev-parse", "HEAD"], harness)
    if actual != harness_commit:
        raise RuntimeError(f"harness checkout is at {actual[:12]}, job pins "
                           f"{harness_commit[:12]}")
    repo_commit = _git(["rev-parse", "HEAD"], REPO_ROOT)

    bundle_files = smoke.get("bundle_files")
    if not isinstance(bundle_files, dict) or not bundle_files:
        raise ValueError("smoke.bundle_files must map bundle paths to sources")
    fill_expected_assets(smoke, dataset)

    files = {}
    provenance = {}
    for bundle_path, spec in sorted(bundle_files.items()):
        _safe_bundle_path(bundle_path)
        if not isinstance(spec, str):
            raise ValueError(f"bundle source for {bundle_path!r} must be a string")
        content, origin = read_source(spec, harness, harness_commit, repo_commit)
        files[bundle_path] = {
            "base64": base64.b64encode(content).decode("ascii"),
            "sha256": sha256_bytes(content),
        }
        provenance[bundle_path] = origin

    missing_required = [name for name in REQUIRED_IMAGE_FILES if name not in files]
    if missing_required:
        raise ValueError(f"image context is incomplete, missing {missing_required}")
    # The runtime's validator enforces exactly these pins; the artifact module
    # is our addition, required because the runner imports it from the bundle.
    for path in ("image/task_template/train.py", "image/bench/score_holdout.py",
                 "adapter/score_holdout.py", "gate/qualify_dataset.py",
                 "workers/smoke_artifact.py"):
        if path not in files:
            raise ValueError(f"bundle_files must carry {path!r}")

    proof = []
    if verify:
        proof = gh_verify(smoke, dataset, release_tag)

    out_path = out_path or (REPO_ROOT / "ops" / "smoke" /
                            f"{job['id']}.source-bundle.json")
    # Exactly the runtime's source/pinned.json schema: harness pin + files with
    # base64 + sha256. Nothing else may live in this payload.
    bundle = {
        "harness_commit": harness_commit,
        "files": files,
    }
    raw = json.dumps(bundle, indent=1) + "\n"
    # The runtime's materializer refuses a payload over 2 MiB, file and decoded
    # content alike; enforce both bounds at assembly so a failure surfaces here.
    content_total = sum(len(base64.b64decode(entry["base64"]))
                        for entry in files.values())
    if len(raw.encode()) > 2 * 1024 * 1024 or content_total > 2 * 1024 * 1024:
        raise ValueError(f"pinned payload exceeds the runtime's 2 MiB materialization "
                        f"bound ({len(raw.encode())} file bytes, {content_total} "
                        f"decoded)")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(raw)
    smoke["pinned_sources"] = {path: entry["sha256"]
                               for path, entry in sorted(files.items())}
    smoke["source_provenance"] = dict(sorted(provenance.items()))
    try:
        bundle_file = str(out_path.relative_to(REPO_ROOT))
    except ValueError:
        bundle_file = str(out_path)
    smoke["source_bundle"] = {"file": bundle_file,
                              "sha256": sha256_bytes(raw.encode()),
                              "bytes": len(raw.encode()),
                              "repo_commit": repo_commit}
    job_path.write_text(json.dumps(job, indent=2) + "\n")
    return {"bundle": str(out_path), "bundle_sha256": smoke["source_bundle"]["sha256"],
            "files": len(files),
            "content_bytes": sum(len(base64.b64decode(entry["base64"]))
                                 for entry in files.values()),
            "harness_commit": harness_commit, "repo_commit": repo_commit,
            "assets": smoke["expected_sha256"], "proof": proof}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Assemble the source-only smoke bundle for an adapter smoke job.")
    parser.add_argument("job", type=Path, help="smoke job spec (updated in place)")
    parser.add_argument("--harness", type=Path, default=DEFAULT_HARNESS,
                        help="read-only pinned harness checkout")
    parser.add_argument("--out", type=Path, default=None,
                        help="bundle output path (default ops/smoke/<id>.source-bundle.json)")
    parser.add_argument("--no-gh-verify", action="store_true",
                        help="skip live GitHub asset verification")
    args = parser.parse_args(argv)
    try:
        summary = assemble(args.job, args.harness, args.out,
                           verify=not args.no_gh_verify)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"ASSEMBLY FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"bundle: {summary['bundle']}")
    print(f"bundle sha256: {summary['bundle_sha256']}")
    print(f"files: {summary['files']} ({summary['content_bytes']} source bytes)")
    print(f"harness commit: {summary['harness_commit']}")
    print(f"repo commit: {summary['repo_commit']}")
    print("expected assets: " + json.dumps(summary["assets"], indent=1))
    for line in summary["proof"]:
        print(f"verified: {line}")
    print("ASSEMBLY OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
