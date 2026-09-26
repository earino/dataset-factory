#!/usr/bin/env python3
"""Point both v2026.09 pins at the final documents commit (docs-only move) and read back."""
import base64
import hashlib
import json
import subprocess
from pathlib import Path

from huggingface_hub import HfApi

REPO = "earino/chicago-doah-adjudication"
TAG = "v2026.09"
GH_TOKEN = Path("/opt/data/.secrets/github-publish.token").read_text().strip()
HF_TOKEN = Path("/opt/data/.secrets/huggingface-write.token").read_text().strip()
LOCAL_SUMS = Path("/opt/data/dataset-factory/release/chicago-doah-adjudication/SHA256SUMS").read_bytes()


def gh(*args):
    p = subprocess.run(["/opt/data/.local/bin/gh", *args], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin", "GH_TOKEN": GH_TOKEN, "HOME": "/opt/data"})
    if p.returncode != 0:
        raise SystemExit("gh failed: " + p.stderr[-400:])
    return json.loads(p.stdout)


main_sha = gh("api", f"repos/{REPO}/git/ref/heads/main")["object"]["sha"]
was = gh("api", f"repos/{REPO}/git/ref/tags/{TAG}")["object"]["sha"]
print("github: main", main_sha, "| tag was", was)
if was != main_sha:
    gh("api", "-X", "PATCH", f"repos/{REPO}/git/refs/tags/{TAG}", "-f", f"sha={main_sha}", "-F", "force=true")
now = gh("api", f"repos/{REPO}/git/ref/tags/{TAG}")["object"]["sha"]
print("github: tag now", now, "| tag == main:", now == main_sha)

api = HfApi(token=HF_TOKEN)
hf_main = api.repo_info(REPO, repo_type="dataset").sha
hf_tag = {t.name: t.target_commit for t in api.list_repo_refs(REPO, repo_type="dataset").tags}.get(TAG)
print("hf: main", hf_main, "| tag was", hf_tag)
if hf_tag != hf_main:
    api.delete_tag(REPO, tag=TAG, repo_type="dataset")
    api.create_tag(REPO, tag=TAG, revision="main", repo_type="dataset")
    hf_tag = {t.name: t.target_commit for t in api.list_repo_refs(REPO, repo_type="dataset").tags}.get(TAG)
print("hf: tag now", hf_tag, "| tag == main:", hf_tag == hf_main)

# The pinned manifest and checksums must describe the same release the package does.
pinned_sums = base64.b64decode(gh("api", f"repos/{REPO}/contents/SHA256SUMS?ref={TAG}")["content"])
pinned_manifest = json.loads(base64.b64decode(gh("api", f"repos/{REPO}/contents/MANIFEST.json?ref={TAG}")["content"]))
print("pinned SHA256SUMS identical to the package:", pinned_sums == LOCAL_SUMS)
print("pinned manifest -> published:", pinned_manifest["published"], "| visibility:", pinned_manifest["visibility"])
print("pinned manifest splits:", {k: v["rows"] for k, v in pinned_manifest["splits"].items()})
print("pinned manifest artifact_version:", pinned_manifest["artifact_version"][:16])
print("local SHA256SUMS sha256:", hashlib.sha256(LOCAL_SUMS).hexdigest()[:16])
