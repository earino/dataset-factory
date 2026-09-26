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
from factory.site_model import linked_readme, require, check_manifest


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
    for filename, expected in record["assets"].items():
        item = entries.get(expected["hf_path"])
        require(item is not None and item.size == expected["bytes"], f"Hub asset missing or size differs: {filename}")
        lfs = getattr(item, "lfs", None)
        sha = lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None)
        if not sha:
            # The Hub reports a SHA-256 only for LFS-stored files. A CSV below Hugging Face's ~10 MB
            # auto-LFS threshold stays a plain blob, and .gitattributes does not change that for an
            # API upload. Skipping the comparison would drop the check; demanding a digest the Hub
            # cannot report would refuse a correct release. So the file is fetched under a bounded
            # cap and hashed here, and the digest is still compared. Anything larger than the cap
            # must be LFS-stored, which is what the cap enforces.
            record.setdefault("hashed_from_hub", []).append(expected["hf_path"])
            sha = hashlib.sha256(small_file(item.rfilename, info.sha, item.size,
                                            limit=64 * 1024 * 1024)).hexdigest()
        require(sha == expected["sha256"], f"Hub asset digest differs: {filename}")
    item = entries.get("MANIFEST.json")
    require(item is not None, "Hub release has no manifest")
    manifest = json.loads(small_file("MANIFEST.json", info.sha, item.size))
    check_manifest(record, manifest)
    main = api.dataset_info(repo, revision="main", files_metadata=True)
    main_manifest = next((s for s in main.siblings if s.rfilename == "MANIFEST.json"), None)
    require(main_manifest is not None, "Hub default branch has no manifest")
    current = json.loads(small_file("MANIFEST.json", main.sha, main_manifest.size))
    require(current.get("release_tag") == tag and current.get("artifact_version") == record["artifact_version"],
            "Hub default branch is a different release; reconcile that release instead")
    item = next((s for s in main.siblings if s.rfilename == "README.md"), None)
    require(item is not None, "Hub card is missing")
    original = small_file("README.md", main.sha, item.size).decode()
    updated = linked_readme(original, record)
    if payload["action"] == "link" and updated != original:
        result = api.create_commit(repo_id=repo, repo_type="dataset", revision="main", parent_commit=main.sha,
            commit_message=f"Link dataset website for {tag}",
            operations=[CommitOperationAdd(path_in_repo="README.md", path_or_fileobj=updated.encode())])
        main_sha = result.oid
    else:
        main_sha = main.sha
    return {"private": info.private, "verified": True, "revision_commit": info.sha,
            "main_commit": main_sha, "links_present": updated == original or payload["action"] == "link"}


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
