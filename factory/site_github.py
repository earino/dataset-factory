"""GitHub reconciliation through the authenticated gh CLI. No tokens in arguments or receipts."""
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from urllib.parse import quote

from .common import FactoryError
from .site_model import dump, require, repository, digest, linked_readme, check_manifest


class GitHub:
    def request(self, method, path, body=None, missing_ok=False):
        require(path.startswith(("repos/", "user", "orgs/", "users/")), "Unexpected GitHub API path")
        cmd = ["gh", "api", "--method", method, path, "-H", "Accept: application/vnd.github+json"]
        if body is not None:
            cmd += ["--input", "-"]
        result = subprocess.run(cmd, input=dump(body) if body is not None else None,
                                text=True, capture_output=True, timeout=60)
        if result.returncode:
            try:
                code = str(json.loads(result.stdout).get("status", "unknown"))
            except ValueError:
                code = "unknown"
            if missing_ok and code == "404":
                return None
            # CLI errors can contain request details; keep those out of saved state.
            raise FactoryError(f"GitHub {method} {path.split('?')[0]} failed (HTTP {code}); check access or conflicts")
        require(len(result.stdout.encode()) <= 4 * 1024 * 1024, "GitHub metadata response exceeds 4 MiB")
        return json.loads(result.stdout) if result.stdout.strip() else {}

    def repo(self, repo, missing_ok=False):
        return self.request("GET", f"repos/{repository(repo)}", missing_ok=missing_ok)

    def file(self, repo, path, ref=None, missing_ok=False):
        suffix = f"?ref={quote(ref, safe='')}" if ref else ""
        result = self.request("GET", f"repos/{repo}/contents/{quote(path, safe='/')}{suffix}", missing_ok=missing_ok)
        if result is None:
            return None
        require(result.get("type") == "file" and result.get("size", 999999) <= 256 * 1024,
                f"Expected a small regular GitHub file: {path}")
        require(result.get("encoding") == "base64", f"GitHub did not return metadata content: {path}")
        return base64.b64decode(result["content"]).decode()

    def create_catalog(self, repo, plan_sha):
        owner, name = repository(repo).split("/")
        who = self.request("GET", "user")
        if who["login"].lower() == owner.lower():
            endpoint = "user/repos"
        else:
            account = self.request("GET", f"users/{owner}")
            require(account.get("type") == "Organization", "Cannot create a repository for another user")
            endpoint = f"orgs/{owner}/repos"
        self.request("POST", endpoint, {"name": name, "private": False, "auto_init": True,
                                       "description": f"Dataset Factory catalogue [site-plan:{plan_sha}]"})
        return self.repo(repo)

    def commit(self, repo, files, message, expected=None, branch=None):
        """One atomic commit on the default branch; optimistic ref update, never force-push."""
        info = self.repo(repo)
        branch = branch or info["default_branch"]
        require(isinstance(branch, str) and branch, "Repository needs an initialized default branch")
        ref = f"repos/{repo}/git/ref/heads/{quote(branch, safe='')}"
        head = self.request("GET", ref)["object"]["sha"]
        base = self.request("GET", f"repos/{repo}/git/commits/{head}")["tree"]["sha"]
        tree = self.request("GET", f"repos/{repo}/git/trees/{base}?recursive=1")
        require(not tree.get("truncated"), "Repository tree is too large for safe reconciliation")
        existing = {e["path"]: e for e in tree["tree"]}
        for path, content in (expected or {}).items():
            data = content.encode() if content is not None else None
            sha = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() if data is not None else None
            require((existing.get(path) or {}).get("sha") == sha,
                    f"Concurrent edit at {path}; rerun to preserve the newer content")
        entries = []
        for path, content in sorted(files.items()):
            data = content.encode()
            sha = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            current = existing.get(path)
            require(not current or current.get("mode") == "100644", f"Refusing to replace non-regular file {path}")
            if not current or current["sha"] != sha:
                entries.append({"path": path, "mode": "100644", "type": "blob", "content": content})
        if not entries:
            return head
        tree_sha = self.request("POST", f"repos/{repo}/git/trees", {"base_tree": base, "tree": entries})["sha"]
        commit = self.request("POST", f"repos/{repo}/git/commits", {
            "message": message, "tree": tree_sha, "parents": [head]})["sha"]
        # GitHub rejects a non-fast-forward update if someone else advanced the branch.
        self.request("PATCH", f"repos/{repo}/git/refs/heads/{quote(branch, safe='')}", {"sha": commit, "force": False})
        return commit

    def check_ownership(self, repo, kind, missing_ok=False):
        marker = self.file(repo, ".dataset-site/owner.json", missing_ok=True)
        if marker is None:
            collision = self.request("GET", f"repos/{repo}/contents/.dataset-site", missing_ok=True)
            workflow = self.file(repo, ".github/workflows/dataset-site.yml", missing_ok=True)
            require(collision is None and workflow is None, "Unmanaged files occupy the site's reserved paths")
            require(missing_ok, "Existing catalogue repository is not owned by this pipeline")
            require(self.request("GET", f"repos/{repo}/pages", missing_ok=True) is None,
                    "Repository already has an unmanaged Pages site; adoption needs review")
        else:
            require(json.loads(marker) == {"schema_version": 1, "kind": kind, "repository": repo},
                    "Website ownership marker does not match this target")

    def dataset_navigation(self, record, managed=None):
        repo = record["github_repository"]
        original = self.file(repo, "README.md")
        remote_manifest = self.file(repo, "MANIFEST.json")
        manifest = json.loads(remote_manifest)
        require(manifest.get("artifact_version") == record["artifact_version"] and
                manifest.get("release_tag") == record["release_tag"],
                "Default branch is a different dataset release; resume from its current package")
        readme = linked_readme(original, record)
        require(digest(original) == manifest.get("package_files", {}).get("README.md"),
                "Default-branch README already disagrees with its manifest")
        manifest["package_files"]["README.md"] = digest(readme)
        for path, content in (managed or {}).items():
            manifest["package_files"][path] = digest(content)
        # The default branch may advance; the immutable dataset tag is never edited.
        return ({"README.md": readme, "MANIFEST.json": dump(manifest)},
                {"README.md": original, "MANIFEST.json": remote_manifest})

    def setup_pages(self, repo):
        pages = self.request("GET", f"repos/{repo}/pages", missing_ok=True)
        if pages is None:
            self.request("POST", f"repos/{repo}/pages", {"build_type": "workflow"})
            pages = self.request("GET", f"repos/{repo}/pages")
        require(pages.get("build_type") == "workflow" and not pages.get("cname"),
                "Existing Pages source/domain differs from the project-site plan; configuration needs review")
        env = self.request("GET", f"repos/{repo}/environments/github-pages", missing_ok=True)
        if env is None:
            self.request("PUT", f"repos/{repo}/environments/github-pages", {})
        # Existing protection rules are left intact. A run may legitimately wait for review.
        self.request("PUT", f"repos/{repo}/pages", {"https_enforced": True})

    def homepage(self, repo, url):
        info = self.repo(repo)
        require(info.get("homepage") in (None, "", url), "An existing repository homepage differs; review before replacing it")
        update = {}
        if info.get("homepage") != url:
            update["homepage"] = url
        if str(info.get("description", "")).startswith("Dataset Factory catalogue [site-plan:"):
            update["description"] = "Reproducible prediction datasets, source documentation and release notes."
        if update:
            self.request("PATCH", f"repos/{repo}", update)

    def dispatch(self, repo, commit):
        info = self.repo(repo)
        require(self.request("GET", f"repos/{repo}/commits/{quote(info['default_branch'], safe='')}")["sha"] == commit,
                "Default branch advanced before dispatch; reconcile the publication again")
        self.request("POST", f"repos/{repo}/actions/workflows/dataset-site.yml/dispatches", {
            "ref": info["default_branch"], "inputs": {"publish": True, "commit": commit}})

    def deployment(self, repo, commit):
        response = self.request("GET", f"repos/{repo}/actions/workflows/dataset-site.yml/runs?head_sha={commit}&event=workflow_dispatch&per_page=20", missing_ok=True)
        runs = (response or {}).get("workflow_runs", [])
        for run in runs:
            if run["head_sha"] != commit:
                continue
            jobs = self.request("GET", f"repos/{repo}/actions/runs/{run['id']}/jobs?per_page=100")["jobs"]
            deploy = next((j for j in jobs if j["name"] == "deploy"), None)
            if deploy and deploy.get("conclusion") == "success":
                return {"status": "deployed", "run_url": run["html_url"], "commit": commit}
            if run["status"] != "completed":
                return {"status": "pending", "run_url": run["html_url"], "commit": commit}
        return {"status": "not_deployed", "commit": commit}

    def verify_dataset(self, record, public=False):
        repo, tag = record["github_repository"], record["release_tag"]
        info = self.repo(repo)
        require(not public or info.get("private") is False, "GitHub dataset is private; complete the approved dataset release first")
        manifest = json.loads(self.file(repo, "MANIFEST.json", ref=tag))
        check_manifest(record, manifest)
        release = self.request("GET", f"repos/{repo}/releases/tags/{quote(tag, safe='')}")
        require(not release.get("draft"), "GitHub release is still a draft")
        assets = {a["name"]: a for a in release["assets"]}
        for filename, expected in record["assets"].items():
            actual = assets.get(filename, {})
            require(actual.get("size") == expected["bytes"] and actual.get("digest") == "sha256:" + expected["sha256"],
                    f"GitHub asset size/digest unavailable or different: {filename}")
        return {"private": info["private"], "release_id": release["id"], "verified": True}
