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


def descriptor(candidate: str) -> dict:
    """The per-dataset facts the generator must not guess.

    Repository, source attribution, release version, layout and commands differ per dataset; they
    live in release/<id>/release.json so adding a dataset needs a descriptor, not a new generator.
    """
    data = load(ROOT / "candidates" / candidate / "release.json")
    if not data:
        raise SystemExit(f"candidates/{candidate}/release.json is missing: the generator is "
                         "data-driven and will not guess a repository, source or layout")
    for key in ("release_version", "release_tag", "repository", "source", "commands"):
        if key not in data:
            raise SystemExit(f"candidates/{candidate}/release.json must declare {key}")
    return data


def combined_artifact_version(levels: dict) -> str:
    """A single label for a multi-level artifact whose levels were gated separately.

    Documented as derived: the two per-level versions are the gate's own, and this only names them
    together. Nothing here is presented as a gate output.
    """
    joined = "\n".join(f"{name}:{data['artifact_version']}" for name, data in sorted(levels.items()))
    return hashlib.sha256(joined.encode()).hexdigest()


def main() -> int:
    candidate = sys.argv[1] if len(sys.argv) > 1 else "austin-911-response"
    desc = descriptor(candidate)
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

    levels = expected.get("levels") or {}
    manifest = {
        "dataset": candidate,
        "release_version": desc["release_version"],
        "release_tag": desc["release_tag"],
        "repository": desc["repository"],
        "visibility": visibility,
        "artifact_version": expected.get("artifact_version") or (levels and
                                                                combined_artifact_version(levels)),
        "artifact_job": expected["job"],
        # The staging release id, because a *draft* release has no tag namespace: looking it up
        # with releases/tags/<tag> returns 404 even though the release exists.
        "staging_release": expected.get("staging_release"),
        "staging_release_tag": f"job-{expected['job']}",
        "staging_repo": "earino/dataset-factory-staging",
        "construction_commit": COMMIT,
        "gate_version": expected.get("gate_version"),
        "gate_command": desc["commands"]["gate"],
        "measurements": load(release / "measurements.json"),
        "assets": {},
        "package_files": {},
        "baseline_command": desc["commands"]["baseline"],
        "get_dataset_command": desc["commands"]["get_dataset"],
        "source": dict(desc["source"],
                       licence_evidence=(record or {}).get("license_evidence")),
        # The layout the download helper restores. A dataset may declare one; otherwise it is the
        # package's own file list under task/, which is what a runner contract expects.
        "layout": desc.get("layout") or {f"task/{relative}": relative
                                        for relative in sorted(expected["files"])},
        "files": expected["files"],
        "splits": (record or {}).get("construction_output", {}).get("splits"),
        "qualification": (record or {}).get("qualification"),
        "baseline": baseline,
        "scope": "One baseline through the runner's training and validation contract. No agent or "
                 "harness comparison was run and none is implied.",
        "published": published,
        "publication_note": publication_note,
    }
    if levels:
        manifest["levels"] = {name: {"artifact_version": data["artifact_version"],
                                     "gate_version": data.get("gate_version"),
                                     "checks": data.get("checks"),
                                     "files": data.get("files")}
                              for name, data in sorted(levels.items())}
        manifest["artifact_version_note"] = (
            "artifact_version is derived here: it names the per-level gate-produced versions "
            "together, because each level is gated and scored as its own task instance. The gate's "
            "own values are in `levels`.")
    # Flat release-asset names: GitHub rejects `/` in asset names, so the download script restores
    # the runner layout. The mapping is recorded here rather than in prose.
    # Flat asset names: GitHub rejects `/` in asset names. A dataset may pin them (published URLs
    # must not move); otherwise the file path with separators replaced is unambiguous and stable.
    asset_for = desc.get("assets") or {relative: relative.replace("/", "-")
                                       for relative in expected["files"]}
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
    # SHA256SUMS is written *before* the package is hashed. It was written after, so
    # package_files recorded the digest of the previous file: harmless while the artifact never
    # changed, and a package-check failure the moment one did - which is exactly when it matters.
    sums_lines = []
    for relative, info in sorted(expected["files"].items()):
        sums_lines.append(f"{info['sha256']}  {relative}")
    (release / "SHA256SUMS").write_text("\n".join(sums_lines) + "\n")

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
    # The Hub path for each file, when the dataset declares its own. Emitted only when it differs
    # from the flat default, so a single-level release's manifest is unchanged.
    declared_hub = desc.get("hf_paths")
    if declared_hub:
        manifest["hub_paths"] = {relative: declared_hub[relative]
                                 for relative in sorted(expected["files"])}

    (release / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # SHA256SUMS was written above, before the package was hashed.

    print(f"wrote {release}/MANIFEST.json and SHA256SUMS")
    # A multi-level artifact has no single gate-produced version; name the per-level ones instead.
    label = manifest["artifact_version"] or "(see levels)"
    print(f"  artifact_version {label[:16]}...")
    for name, data in sorted(manifest.get("levels", {}).items()):
        print(f"    {name}: {data['artifact_version'][:16]}... ({data['checks']} checks)")
    print(f"  files: {len(expected['files'])}")
    print(f"  baseline: {'present' if baseline else 'NOT YET COLLECTED'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())