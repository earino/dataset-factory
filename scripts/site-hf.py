#!/usr/bin/env python3
"""Small Hub adapter for the website pipeline. JSON stdin/stdout; HF_TOKEN_WRITE only.

Runs in Scout's existing Hugging Face environment. Never downloads dataset rows or moves tags.
"""
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from factory.http import secret
from factory.release_schema import from_manifest
from factory.site_model import linked_readme, require, check_manifest
from factory.hub_integrity import load_worker_receipt, HubIntegrityError

ROOT = Path(__file__).resolve().parents[1]


def prior_editorial_identity(record, commit):
    """Reviewed continuity of an already verified release, not a fresh data-hash claim."""
    path = ROOT / 'config/editorial-release-baselines.json'
    if not path.is_file():
        return False
    for prior in json.loads(path.read_text()).get('releases', []):
        if all(prior.get(k) == record.get(k) for k in ('dataset', 'release_tag', 'artifact_version')) \
                and prior.get('repository') == record['hf_repository'] and prior.get('hf_commit') == commit:
            return True
    return False


def worker_evidence(record, commit):
    expected = {v['hf_path']: (v['bytes'], v['sha256']) for v in record['assets'].values()}
    for path in sorted((ROOT / 'jobs').glob('*.json')):
        if path.is_symlink() or path.stat().st_size > 1024 * 1024:
            continue
        try:
            candidate = json.loads(path.read_text())
            if (candidate.get('job', {}).get('hf_publish') or {}).get('repo') != record['hf_repository']:
                continue
            receipt = load_worker_receipt(ROOT, path.stem, record['hf_repository'], expected)
            if receipt.get('commit') == commit:
                return receipt
        except (OSError, ValueError, KeyError, HubIntegrityError):
            continue
    return None


def execute(payload):
    from huggingface_hub import HfApi, hf_hub_download, CommitOperationAdd

    # Explicit credentials prevent the inference token or a cached login from being selected.
    token = secret("HF_TOKEN_WRITE")
    api = HfApi(token=token)
    record = payload["record"]
    repo, tag = record["hf_repository"], record["release_tag"]
    info = api.dataset_info(repo, revision=tag, files_metadata=True)
    require(not payload.get("public") or info.private is False,
            "Hugging Face dataset is private; complete its approved release first")

    def small_file(path, revision, size, limit=256 * 1024):
        """Fetch a bounded file and return its bytes.

        Metadata is capped at 256 KiB; an asset with no Hub digest may be larger, but still bounded,
        so the caller passes its own limit rather than the cap being loosened for everything.
        """
        require(isinstance(size, int) and size <= limit, "Hub file exceeds the cap for this check")
        downloaded = hf_hub_download(repo, filename=path, repo_type="dataset", revision=revision, token=token)
        raw = Path(downloaded).read_bytes()
        require(len(raw) <= limit, "Hub file exceeded its declared size")
        return raw

    entries = {s.rfilename: s for s in info.siblings}
    inherited = prior_editorial_identity(record, info.sha)
    receipt = worker_evidence(record, info.sha) if not inherited else None
    continuity_only = []
    for filename, expected in record["assets"].items():
        item = entries.get(expected["hf_path"])
        require(item is not None and item.size == expected["bytes"], f"Hub asset missing or size differs: {filename}")
        lfs = getattr(item, "lfs", None)
        sha = lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None)
        if not sha:
            evidence = (receipt or {}).get('files', {}).get(item.rfilename, {})
            if evidence:
                require(evidence.get('blob_id') == getattr(item, 'blob_id', None)
                        and evidence.get('bytes') == item.size, 'Worker evidence differs from pinned Hub blob')
                sha = evidence.get('sha256')
            elif Path(item.rfilename).suffix.lower() in ('.json', '.md', '.txt') and item.size <= 256 * 1024:
                sha = hashlib.sha256(small_file(item.rfilename, info.sha, item.size)).hexdigest()
            elif inherited:
                # The reviewed commit pins every blob of this previously verified release.
                # Do not download CSVs to manufacture a new byte-verification claim.
                continuity_only.append(filename)
            else:
                require(False, f'Non-LFS bulk asset requires collected worker verification: {filename}')
        if filename not in continuity_only:
            require(sha == expected["sha256"], f"Hub asset digest differs: {filename}")
    item = entries.get("MANIFEST.json")
    require(item is not None, "Hub release has no manifest")
    manifest = json.loads(small_file("MANIFEST.json", info.sha, item.size))
    check_manifest(record, from_manifest(manifest, strict=False))
    main = api.dataset_info(repo, revision="main", files_metadata=True)
    current_entries = {s.rfilename: s for s in main.siblings}
    for expected in record['assets'].values():
        was, now = entries[expected['hf_path']], current_entries.get(expected['hf_path'])
        require(now is not None and now.size == was.size and getattr(now, 'blob_id', None)
                and now.blob_id == getattr(was, 'blob_id', None),
                'Hub current data blob differs from the immutable release')
    main_manifest = next((s for s in main.siblings if s.rfilename == "MANIFEST.json"), None)
    require(main_manifest is not None, "Hub default branch has no manifest")
    current_raw = json.loads(small_file("MANIFEST.json", main.sha, main_manifest.size))
    current = from_manifest(current_raw, strict=False)
    require(current.tag == tag and current.artifact_id == record["artifact_version"],
            "Hub default branch is a different release; reconcile that release instead")
    item = next((s for s in main.siblings if s.rfilename == "README.md"), None)
    require(item is not None, "Hub card is missing")
    original = small_file("README.md", main.sha, item.size).decode()
    updated = linked_readme(original, record)
    updates = {"README.md": updated} if updated != original else {}
    if record.get("suitability"):
        for name in ("DATA_DICTIONARY.md", "RELEASE_NOTES.md", "VERIFICATION.md", "LOADING.md"):
            item = next((s for s in main.siblings if s.rfilename == name), None)
            if item is None:
                continue
            prior = small_file(name, main.sha, item.size).decode()
            expected = current_raw.get("package_files", {}).get(name)
            require(expected is None or hashlib.sha256(prior.encode()).hexdigest() == expected,
                    f"Hub default-branch {name} disagrees with its manifest")
            revised = linked_readme(prior, record)
            if revised != prior:
                updates[name] = revised
                current_raw.setdefault("package_files", {})[name] = hashlib.sha256(revised.encode()).hexdigest()
        if any(name != "README.md" for name in updates):
            updates["MANIFEST.json"] = json.dumps(current_raw, indent=2, ensure_ascii=False) + "\n"
    pending = bool(updates)
    if payload["action"] == "link" and updates:
        result = api.create_commit(repo_id=repo, repo_type="dataset", revision="main", parent_commit=main.sha,
            commit_message=f"Refresh dataset website and use notices for {tag}",
            operations=[CommitOperationAdd(path_in_repo=name, path_or_fileobj=content.encode())
                        for name, content in sorted(updates.items())])
        main_sha = result.oid
    else:
        main_sha = main.sha
    return {"private": info.private, "verified": True, "revision_commit": info.sha,
            "main_commit": main_sha, "links_present": not pending or payload["action"] == "link",
            "verification_basis": "prior_verified_immutable_release" if continuity_only else "asset_digests",
            "inherited_non_lfs_assets": continuity_only, "bulk_downloads": 0}


if __name__ == "__main__":
    try:
        payload = json.loads(sys.stdin.read(512 * 1024))
        require(payload.get("action") in ("read", "link"), "Unknown Hub adapter action")
        print(json.dumps(execute(payload)))
    except Exception as exc:
        # SDK errors sometimes embed URLs/headers; never emit those into a saved receipt.
        from factory.common import FactoryError
        reason = str(exc) if isinstance(exc, FactoryError) else type(exc).__name__
        print(json.dumps({"error": reason}))
        sys.exit(1)
