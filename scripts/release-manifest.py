#!/usr/bin/env python3
"""Generate the release manifest and SHA256SUMS for a prepared dataset.

Everything comes from recorded evidence - the accepted artifact's expected hashes, the candidate
record, and (when it exists) the collected baseline report. Nothing is retyped by hand, so the
manifest cannot drift from what was actually measured.

Usage: python3 scripts/release-manifest.py austin-911-response
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "06d7002bc01933e4c094bbe84e4d9899572a893f"


def load(path: Path):
    return json.loads(path.read_text()) if path.is_file() else None


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def licenses_block(candidate: str) -> dict:
    """Terms for this dataset, from the declared decision plus the standing policy.

    Built here rather than edited into the manifest afterwards: a hand-edited block is silently
    lost the next time the manifest is regenerated, which is exactly when it needs to be right.
    """
    policy = load(ROOT / "config" / "licensing-policy.json") or {}
    declared = load(ROOT / "candidates" / candidate / "license.json")
    if not declared:
        return {"policy_version": policy.get("policy_version"),
                "status": "UNDECLARED - candidates/<id>/license.json is missing",
                "rules": policy.get("rules", [])}
    code = declared.get("code") or {}
    compilation = declared.get("compilation") or {}
    source = declared.get("source") or {}
    return {
        "policy_version": policy.get("policy_version"),
        "decided": declared.get("decided"),
        "code": {"spdx": code.get("spdx"), "file": (policy.get("code_default") or {}).get("file"),
                 "copyright": code.get("copyright"),
                 "third_party": code.get("third_party") or []},
        "data_compilation": {"spdx": compilation.get("spdx"),
                             "file": (policy.get("compilation_default") or {}).get("file"),
                             "scope": compilation.get("scope")},
        "source_data": {"spdx": source.get("spdx"), "status": source.get("status"),
                        "evidence": source.get("evidence") or [],
                        "attribution": source.get("attribution"),
                        "citation": source.get("citation"),
                        "derived_labelling": source.get("derived_labelling")},
        "rules": policy.get("rules", []),
    }


def publication_state(release: Path) -> tuple[bool, str, str]:
    """Derive publication state from recorded evidence, never from an assertion.

    `DESTINATIONS.json` records each destination's visibility and verification and is written
    after those checks, so it is the record the manifest has to agree with. Hardcoding "private"
    here meant the documented post-publication regeneration re-asserted a status that had stopped
    being true.
    """
    path = release / "DESTINATIONS.json"
    private_claim = "private (publication requires explicit authorisation)"
    private_note = "Prepared for human review. Nothing here has been published."
    if not path.is_file():
        return False, private_claim, private_note
    destinations = load(path).get("destinations", {})
    entries = [entry for entry in destinations.values() if isinstance(entry, dict)]
    if not entries or any(entry.get("private") is not False or entry.get("verified") is not True
                          for entry in entries):
        return False, private_claim, private_note
    verified = sorted(str(entry.get("verified_at")) for entry in entries if entry.get("verified_at"))
    when = f", both destinations verified {verified[-1]}" if verified else ""
    return True, "public", (
        f"Published after explicit operator authorisation{when}. Data files, tag and artifact "
        "version are unchanged by publication.")


def main() -> int:
    candidate = sys.argv[1] if len(sys.argv) > 1 else "austin-911-response"
    release = ROOT / "release" / candidate
    published, visibility, publication_note = publication_state(release)
    release.mkdir(parents=True, exist_ok=True)
    record = load(ROOT / "candidates" / candidate / "record.json")
    expected = load(ROOT / "candidates" / candidate / "baseline" / "expected_artifact.json")
    qualification = load(release / "qualification.json")
    # The baseline evidence is tracked next to the candidate, not read out of ignored scratch.
    baseline = load(ROOT / "candidates" / candidate / "baseline" / "baseline_result.json")
    if expected is None:
        raise SystemExit(f"no expected_artifact.json for {candidate}; nothing to manifest")

    manifest = {
        "dataset": candidate,
        "release_version": "2026.09",
        "release_tag": "v2026.09",
        "repository": "https://github.com/earino/austin-911-response",
        "visibility": visibility,
        "artifact_version": expected["artifact_version"],
        "artifact_job": expected["job"],
        # The staging release id, because a *draft* release has no tag namespace: looking it up
        # with releases/tags/<tag> returns 404 even though the release exists.
        "staging_release": expected.get("staging_release"),
        "staging_release_tag": f"job-{expected['job']}",
        "staging_repo": "earino/dataset-factory-staging",
        "construction_commit": COMMIT,
        "gate_version": expected.get("gate_version"),
        "gate_command": f"python3 code/qualify_dataset.py <dataset-dir>",
        "measurements": load(release / "measurements.json"),
        "assets": {},
        "package_files": {},
        "baseline_command": "sh baseline/reproduce_baseline.sh ./task",
        "get_dataset_command": "python3 get_dataset.py --dest ./task",
        "source": {
            "name": "Austin Open Data - APD 911 Calls for Service 2023-2026",
            "dataset_id": "e687-fx2y",
            "landing_page": "https://datahub.austintexas.gov/d/e687-fx2y",
            "api": "https://datahub.austintexas.gov/resource/e687-fx2y.json",
            "accessed": "2026-09-18",
            "licence": "Public Domain",
            "licence_evidence": (record or {}).get("license_evidence"),
        },
        "layout": {"task/meta.json": "meta.json",
                   "task/public/train.csv": "public/train.csv",
                   "task/public/eval.csv": "public/eval.csv",
                   "task/private/holdout.csv": "private/holdout.csv",
                   "task/quality.json": "quality.json"},
        "files": expected["files"],
        "splits": (record or {}).get("construction_output", {}).get("splits"),
        "qualification": (record or {}).get("qualification"),
        "baseline": baseline,
        "scope": "One baseline through the runner's training and validation contract. No agent or "
                 "harness comparison was run and none is implied.",
        "published": published,
        "publication_note": publication_note,
    }
    # Flat release-asset names: GitHub rejects `/` in asset names, so the download script restores
    # the runner layout. The mapping is recorded here rather than in prose.
    asset_for = {"public/train.csv": "train.csv", "public/eval.csv": "eval.csv",
                 "private/holdout.csv": "holdout.csv", "meta.json": "meta.json",
                 "quality.json": "quality.json"}
    manifest["assets"] = {
        relative: {"asset_name": asset_for[relative], "bytes": info["bytes"],
                   "sha256": info["sha256"]}
        for relative, info in sorted(expected["files"].items())
    }
    # Hashes of everything published in the repository, so the shipped code and docs can be
    # checked too - MANIFEST.json itself excluded, since a file cannot hash itself.
    # DESTINATIONS.json records per-destination publication state and is written *after* a
    # destination is verified, so it cannot be hashed by the manifest it helps complete - that is
    # circular, and it made the package check fail on every re-verification. It is excluded here
    # and named in check-package.py as the per-destination record it is.
    POST_VERIFICATION = {"DESTINATIONS.json"}
    package_files = {}
    for path in sorted(release.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.json":
            relative = path.relative_to(release).as_posix()
            if relative in POST_VERIFICATION:
                continue
            package_files[relative] = sha256_of(path)
    manifest["package_files"] = package_files
    manifest["licenses"] = licenses_block(candidate)

    (release / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # sha256sum -c format, over the artifact files under the names a downloader sees.
    lines = []
    for relative, info in sorted(expected["files"].items()):
        lines.append(f"{info['sha256']}  {relative}")
    (release / "SHA256SUMS").write_text("\n".join(lines) + "\n")

    print(f"wrote {release}/MANIFEST.json and SHA256SUMS")
    print(f"  artifact_version {expected['artifact_version'][:16]}...")
    print(f"  files: {len(expected['files'])}")
    print(f"  baseline: {'present' if baseline else 'NOT YET COLLECTED'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())