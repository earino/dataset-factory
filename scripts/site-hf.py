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

    def small_file(path, revision, size):
        require(isinstance(size, int) and size <= 256 * 1024, "Hub metadata file exceeds 256 KiB")
        downloaded = hf_hub_download(repo, filename=path, repo_type="dataset", revision=revision, token=token)
        raw = Path(downloaded).read_bytes()
        require(len(raw) <= 256 * 1024, "Hub metadata exceeded its declared size")
        return raw

    entries = {s.rfilename: s for s in info.siblings}
    for filename, expected in record["assets"].items():
        item = entries.get(expected["hf_path"])
        require(item is not None and item.size == expected["bytes"], f"Hub asset missing or size differs: {filename}")
        lfs = getattr(item, "lfs", None)
        sha = lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None)
        if not sha:
            require(not filename.endswith(".csv"), "CSV needs a Hub SHA-256; bulk download is forbidden here")
            sha = hashlib.sha256(small_file(item.rfilename, info.sha, item.size)).hexdigest()
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
