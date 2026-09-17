"""Worker-only, bounded-memory uploads to a private GitHub staging release."""
from __future__ import annotations

import hashlib
import http.client
import json
from pathlib import Path
import re
import time
import urllib.parse

PART_BYTES = 1024**3
MAX_ASSETS = 400  # Leaves room for a compact coordinator report.


class UploadError(Exception):
    pass


def digest(path, offset=0, size=None):
    result = hashlib.sha256()
    remaining = path.stat().st_size - offset if size is None else size
    with path.open("rb") as stream:
        stream.seek(offset)
        while remaining:
            chunk = stream.read(min(1024 * 1024, remaining))
            if not chunk:
                raise UploadError("Artifact changed during hashing")
            result.update(chunk)
            remaining -= len(chunk)
    return result.hexdigest()


class GitHub:
    def __init__(self, token, repo):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise UploadError("Invalid staging repository")
        self.token, self.repo = token, repo

    def request(self, method, path, body=None, upload=None):
        connection = http.client.HTTPSConnection("uploads.github.com" if upload else "api.github.com", timeout=60)
        headers = {"Authorization": "Bearer " + self.token, "User-Agent": "dataset-factory-scout",
                   "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        try:
            if upload:
                file, offset, size = upload
                headers.update({"Content-Type": "application/octet-stream", "Content-Length": str(size)})
                connection.putrequest(method, path)
                for key, value in headers.items():
                    connection.putheader(key, value)
                connection.endheaders()
                with file.open("rb") as stream:
                    stream.seek(offset)
                    remaining = size
                    while remaining:
                        chunk = stream.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise UploadError("Artifact changed during upload")
                        connection.send(chunk)
                        remaining -= len(chunk)
            else:
                headers["Content-Type"] = "application/json"
                connection.request(method, path, json.dumps(body).encode() if body is not None else None, headers)
            response = connection.getresponse()
            raw = response.read(4 * 1024 * 1024 + 1)
            if len(raw) > 4 * 1024 * 1024:
                raise UploadError("GitHub metadata response too large")
            if response.status == 404 and method == "GET":
                return None
            if not 200 <= response.status < 300:
                raise UploadError(f"GitHub {method} returned HTTP {response.status}")
            return json.loads(raw) if raw else {}
        except (OSError, http.client.HTTPException, ValueError) as exc:
            raise UploadError(f"GitHub transfer failed ({type(exc).__name__})") from None
        finally:
            connection.close()

    def assets(self, release_id):
        result = []
        for page in range(1, 12):
            batch = self.request("GET", f"/repos/{self.repo}/releases/{release_id}/assets?per_page=100&page={page}")
            if batch is None:
                raise UploadError("Staging release disappeared")
            result.extend(batch)
            if len(batch) < 100:
                return result
        raise UploadError("Too many assets")

    def ensure_asset(self, release_id, path, name, offset, size, sha256):
        for attempt in range(3):
            existing = next((a for a in self.assets(release_id) if a["name"] == name), None)
            if existing:
                if existing["state"] == "starter":
                    self.request("DELETE", f"/repos/{self.repo}/releases/assets/{existing['id']}")
                elif existing["size"] == size and existing.get("digest") == "sha256:" + sha256:
                    return existing
                else:
                    raise UploadError("Existing asset differs; refusing to overwrite it")
            try:
                asset = self.request("POST", f"/repos/{self.repo}/releases/{release_id}/assets?" +
                                     urllib.parse.urlencode({"name": name}), upload=(path, offset, size))
                if asset["size"] != size or asset.get("digest") != "sha256:" + sha256:
                    raise UploadError("Uploaded size or digest differs")
                return asset
            except UploadError:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)  # Reconcile an ambiguous upload before retrying.


def parts(files, part_bytes=PART_BYTES):
    result = []
    for index, (logical, path) in enumerate(files):
        if path.is_symlink() or not path.is_file():
            raise UploadError("Artifacts must be regular files")
        size = path.stat().st_size
        count = max(1, (size + part_bytes - 1) // part_bytes)
        if len(result) + count > MAX_ASSETS - 1:
            raise UploadError("Too many artifacts; archive small files on the worker first")
        for part in range(count):
            offset = part * part_bytes
            length = min(part_bytes, size - offset)
            result.append({"path": path, "file": logical, "name": f"file-{index:04d}-part-{part:04d}",
                           "offset": offset, "size": length, "sha256": digest(path, offset, length)})
    return result


def publish(base, job, report, client=None):
    credentials = json.loads((base / "credentials.json").read_text())
    client = client or GitHub(credentials["token"], credentials["repo"])
    repo = client.repo
    repository = client.request("GET", f"/repos/{repo}")
    if not repository or repository.get("private") is not True:
        raise UploadError("Staging repository must be private")
    output = base / "output"
    files = []
    for path in sorted(output.rglob("*")):
        if path.is_symlink():
            raise UploadError("Artifact symlinks are not supported")
        if path.is_file():
            files.append(("output/" + path.relative_to(output).as_posix(), path))
        elif not path.is_dir():
            raise UploadError("Non-regular artifact")
    files.extend((name, base / name) for name in ("source.tar", "container.log"))
    if sum(p.stat().st_size for _, p in files) > job["max_artifact_mb"] * 1024**2:
        raise UploadError("Artifacts exceed job allowance; worker expires on schedule")
    planned = parts(files)
    tag = "job-" + job["id"]
    release = None
    for page in range(1, 101):
        batch = client.request("GET", f"/repos/{repo}/releases?per_page=100&page={page}")
        release = next((r for r in batch if r["tag_name"] == tag), None)
        if release is not None or len(batch) < 100:
            break
    else:
        raise UploadError("Staging release history too large to reconcile")
    if release is None:
        # If the response is lost, a later publish reuses this tag, never a new one.
        release = client.request("POST", f"/repos/{repo}/releases", {
            "tag_name": tag, "name": tag, "draft": True,
            "body": "Private worker artifacts for " + job["id"] + ". Not a reviewed dataset release.",
        })
    uploaded = []
    for item in planned:
        asset = client.ensure_asset(release["id"], item["path"], item["name"], item["offset"], item["size"], item["sha256"])
        uploaded.append({key: value for key, value in item.items() if key != "path"} |
                        {"id": asset["id"], "url": asset["browser_download_url"]})
    manifest = base / "manifest.json"
    manifest.write_text(json.dumps({"job": job, "result": report, "assets": uploaded,
                                   "reconstruction": "Concatenate each file's parts in ascending offset order."}, indent=2))
    sha = digest(manifest)
    asset = client.ensure_asset(release["id"], manifest, "manifest.json", 0, manifest.stat().st_size, sha)
    # Keep the coordinator copy compact; full paths/reconstruction are in the manifest.
    compact = [{key: a[key] for key in ("id", "size", "sha256")} for a in uploaded]
    compact.append({"id": asset["id"], "size": asset["size"], "sha256": sha})
    return {"uploaded": True, "repo": repo, "release_id": release["id"], "release_url": release["html_url"],
            "manifest_url": asset["browser_download_url"], "assets": compact}
