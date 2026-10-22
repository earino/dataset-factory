#!/usr/bin/env python3
"""Generate the release manifest and SHA256SUMS for a prepared dataset.

Everything comes from recorded evidence - the accepted artifact's expected hashes, the candidate
record, and (when it exists) the collected baseline report. Nothing is retyped by hand, so the
manifest cannot drift from what was actually measured.

Usage: python3 scripts/release-manifest.py <dataset>
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from factory.release_schema import (ReleaseShapeError, load_release, from_manifest,
                                    normalise_destinations, normalise_splits,
                                    combined_artifact_version, atomic_write)


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
    # The licence *text* a dataset ships is normally the standing default, but a dataset whose
    # source does not permit a standard open dedication must be able to name its own file - the
    # policy default is CC0-1.0, and a manifest that names LICENSE-CC0-1.0.txt for a compilation
    # the candidate record forbids declaring as CC0 is a false licence claim in a published
    # artifact. The declaration wins; the default is only a fallback.
    code_file = code.get("file") or (policy.get("code_default") or {}).get("file")
    compilation_file = compilation.get("file") or (policy.get("compilation_default") or {}).get("file")
    return {
        "policy_version": policy.get("policy_version"),
        "decided": declared.get("decided"),
        "code": {"spdx": code.get("spdx"), "file": code_file,
                 "copyright": code.get("copyright"),
                 "third_party": code.get("third_party") or []},
        "data_compilation": {"spdx": compilation.get("spdx"), "file": compilation_file,
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
    entries = list(normalise_destinations(load(path), path).values())
    if not entries or any(entry.private is not False or not entry.verified for entry in entries):
        return False, private_claim, private_note
    verified = sorted(entry.verified_at for entry in entries if entry.verified_at)
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
    for key in ("release_version", "release_tag", "repository", "construction_commit",
                "source", "commands"):
        if key not in data:
            raise SystemExit(f"candidates/{candidate}/release.json must declare {key}")
    return data


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("name the dataset package to manifest, e.g. release/<id>")
    argument = Path(sys.argv[1])
    candidate = argument.name
    release = ROOT / "release" / candidate
    if not candidate or candidate in (".", "..") or (len(argument.parts) > 1 and
            argument.resolve() != release.resolve()):
        raise SystemExit("name a dataset or its directory under release/")
    if (release / "MANIFEST.json").exists():
        existing = load_release(release)
        if existing.published or any(d.private is False for d in existing.destinations.values()):
            print(f"validated {release}/MANIFEST.json; published bytes preserved (no writes)")
            return 0
    desc = descriptor(candidate)
    published, visibility, publication_note = publication_state(release)
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
        # One identity for the artifact: the gate's digest. It is what staging, verification and
        # every audit reference. The packaging digest is recorded separately so the two can never
        # again disagree about which bytes were qualified.
        "artifact_version": (qualification or {}).get("artifact", {}).get(
            "artifact_version", {}).get("digest")
        or expected.get("artifact_version")
        or (levels and combined_artifact_version(levels)),
        "package_digest": combined_artifact_version(levels) if levels else None,
        "artifact_job": expected["job"],
        # The staging release id, because a *draft* release has no tag namespace: looking it up
        # with releases/tags/<tag> returns 404 even though the release exists.
        "staging_release": expected.get("staging_release"),
        "staging_release_tag": f"job-{expected['job']}",
        "staging_repo": "earino/dataset-factory-staging",
        # The commit that carries the construction script the artifact was built from - per
        # dataset, because a literal here described one release and would be wrong for the next.
        "construction_commit": desc["construction_commit"],
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
        # Qualification comes from the gate report beside the artifact, not from the candidate
        # record: the record can lag a rebuild, and a stale digest here is exactly how the manifest
        # ended up naming two different artifacts.
        "qualification": {
            "gate_version": (qualification or {}).get("gate_version"),
            "ok": (qualification or {}).get("ok"),
            "failed_checks": (qualification or {}).get("failed_checks", []),
            "result": ("PASSED" if (qualification or {}).get("ok")
                       else "FAILED"),
            "artifact_version": (((qualification or {}).get("artifact") or {})
                                 .get("artifact_version") or {}).get("digest"),
            "report": "qualification.json",
        } if qualification else (record or {}).get("qualification"),
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
    # The site pipeline requires a passing qualification for *this* artifact version. A per-level
    # manifest derives that version here from the gate-produced level versions, so the qualification
    # block has to carry the same derived value or the page can never be built for such a release.
    if manifest.get("qualification") and manifest.get("artifact_version"):
        manifest["qualification"].setdefault("artifact_version", manifest["artifact_version"])
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
    sums_text = "\n".join(sums_lines) + "\n"

    POST_VERIFICATION = {"DESTINATIONS.json"}
    package_files = {}
    for path in sorted(release.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.json":
            relative = path.relative_to(release).as_posix()
            if relative in POST_VERIFICATION:
                continue
            package_files[relative] = sha256_of(path)
    package_files["SHA256SUMS"] = hashlib.sha256(sums_text.encode()).hexdigest()
    manifest["package_files"] = package_files
    # Every supported fallback is interpreted by the same schema as the readers.
    split_sources = []
    for filename, keys in (("quality.json", ("split_stats", "splits")),
                           ("summary.json", ("splits",))):
        source = release / filename
        doc = load(source) or {}
        split_sources.extend((doc.get(key), source, key) for key in keys)
    split_sources.append((((record or {}).get("qualification") or {}).get("splits"),
                          ROOT / "candidates" / candidate / "record.json", "qualification.splits"))
    if baseline is None and desc.get("baseline_reason"):
        manifest["baseline_reason"] = desc["baseline_reason"]
    manifest["licenses"] = licenses_block(candidate)
    # The Hub path for each file, when the dataset declares its own. Emitted only when it differs
    # from the flat default, so a single-level release's manifest is unchanged.
    declared_hub = desc.get("hf_paths")
    if declared_hub:
        manifest["hub_paths"] = {relative: declared_hub[relative]
                                 for relative in sorted(expected["files"])}

    release_record = from_manifest(manifest, path=release / "MANIFEST.json",
                                   destinations=load(release / "DESTINATIONS.json"),
                                   split_sources=split_sources)
    for section in ("code", "data_compilation", "source_data"):
        if not (release_record.licences.get(section) or {}).get("spdx"):
            raise ReleaseShapeError(release / "MANIFEST.json", "licenses." + section,
                                    "missing explicit licence designation")
    # Keep protocol grouping; shared pools are stored once, irrespective of config count.
    split_doc = {}
    for split in release_record.splits.values():
        group = split_doc.setdefault(split.config, {}) if split.config else split_doc
        group[split.name] = split.counts()
        if split.positive_rate is not None:
            group[split.name]["positive_rate"] = split.positive_rate
    manifest.update(splits=split_doc)
    text = json.dumps(manifest, indent=2, allow_nan=False) + "\n"
    # All shape/licence checks precede the first write. Each replace is atomic; manifest last.
    release.mkdir(parents=True, exist_ok=True)
    atomic_write(release / "SHA256SUMS", sums_text)
    atomic_write(release / "MANIFEST.json", text)

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
    try:
        raise SystemExit(main())
    except ReleaseShapeError as exc:
        raise SystemExit(str(exc)) from None