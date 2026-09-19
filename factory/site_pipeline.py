"""Prepare, publish and verify repeatable dataset websites. Provider state is authoritative."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time
import urllib.request

from .common import FactoryError
from .site_model import digest, dump, project, read, require, links, pages_url
from .site_github import GitHub

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ".github/workflows/dataset-site.yml"
PREFIX = ".dataset-site"


def prepare(package, editorial, config, out):
    problems, _ = runpy.run_path(str(ROOT / "scripts/check-package.py"))["check_package"](package)
    require(not problems, "Package check failed: " + "; ".join(problems))
    record = project(package, editorial, config)
    renderer = (ROOT / "sites/runtime.py").read_text()
    workflow = (ROOT / "sites/pages.yml").read_text()
    targets = {}
    for kind, repo in (("dataset", record["github_repository"]), ("catalog", config["catalog_repository"])):
        site_config = {"schema_version": 1, "kind": kind, "title": config["catalog_title"],
                       "description": config["catalog_description"], "catalog_url": record["urls"]["catalog"]}
        files = {f"{PREFIX}/build.py": renderer, f"{PREFIX}/config.json": dump(site_config),
                 f"{PREFIX}/owner.json": dump({"schema_version": 1, "kind": kind, "repository": repo}),
                 f"{PREFIX}/records/{record['dataset']}/{record['release_tag']}.json": dump(record),
                 f"{PREFIX}/editions/{record['dataset']}/{record['release_tag']}/{record['site_revision']}.json": dump(record),
                 f"{PREFIX}/LICENSE-MIT.txt": (ROOT / "sites/LICENSE-MIT.txt").read_text(),
                 WORKFLOW: workflow}
        targets[kind] = {"repository": repo, "url": pages_url(repo), "files": files}
    plan = {"schema_version": 1, "record": record, "targets": targets,
            "operations": ["verify published dataset destinations", "create catalogue if absent",
                           "commit managed website files and navigation", "link Hub card",
                           "configure Pages and deployment environment", "deploy dataset",
                           "verify dataset site", "deploy catalogue", "verify all destinations"],
            "publication": "Operator approval required. Dataset destinations must already be public. "
                           "Catalogue repository will be public. No dataset tags or assets are modified."}
    plan["plan_sha256"] = digest(dump(plan))
    out = Path(out)
    require(not out.is_symlink(), "Bundle directory cannot be a symlink")
    if out.exists():
        require(out.is_dir() and (not any(out.iterdir()) or (out / "bundle.json").is_file()),
                "Refusing to overwrite an unrelated directory")
        if (out / "bundle.json").exists():
            previous = read(out / "bundle.json")
            require(previous.get("plan_sha256") == plan["plan_sha256"],
                    "Prepared bundle differs; use a new output directory so review and recovery state survive")
    require(not any(p.is_symlink() for p in out.parents), "Bundle path cannot pass through a symlink")
    out.mkdir(parents=True, exist_ok=True)
    (out / "bundle.json").write_text(dump(plan))
    runtime = runpy.run_path(str(ROOT / "sites/runtime.py"))
    for kind, target in targets.items():
        # Review builds contain only this release. Remote catalogue builds preserve all existing records.
        site_config = json.loads(target["files"][f"{PREFIX}/config.json"])
        runtime["write_output"](out / "preview" / kind, runtime["render"](site_config, [record], preview=True, editions=[record]))
    (out / "REVIEW.md").write_text(f"# Website publication plan\n\nPlan: {plan['plan_sha256']}\n\n" +
        plan["publication"] + "\n\n" + "\n".join(f"- {k}: {t['repository']} → {t['url']}" for k, t in targets.items()) +
        "\n\nNavigation to be added to GitHub and Hugging Face:\n\n" + links(record) + "\n")
    return {"plan_sha256": plan["plan_sha256"], "bundle": str(out), "network_calls": 0,
            "preview": str(out / "preview"), "publication": plan["publication"]}


def load_bundle(folder):
    plan = read(Path(folder) / "bundle.json")
    saved = plan.pop("plan_sha256", None)
    require(saved == digest(dump(plan)), "Prepared bundle changed after review")
    plan["plan_sha256"] = saved
    require(plan.get("schema_version") == 1, "Unsupported publication bundle")
    return plan


class Hub:
    def __init__(self, python=None):
        hosted = Path("/opt/data/.venvs/hf/bin/python")
        self.python = python or (str(hosted) if hosted.is_file() else sys.executable)

    def run(self, action, record, public=False):
        # The interpreter is an explicit executable path, never interpolated shell code.
        env = dict(os.environ)
        env.pop("HF_TOKEN", None)
        if not env.get("HF_TOKEN_WRITE_FILE"):
            env["HF_TOKEN_WRITE_FILE"] = env.get("FACTORY_HF_WRITE_TOKEN_FILE", "/opt/data/.secrets/huggingface-write.token")
        result = subprocess.run([self.python, str(ROOT / "scripts/site-hf.py")], text=True, env=env,
            input=dump({"action": action, "record": record, "public": public}), capture_output=True, timeout=180)
        try:
            response = json.loads(result.stdout)
        except ValueError:
            raise FactoryError("Hub adapter failed without a JSON response; check the configured HF Python environment") from None
        require(not result.returncode and not response.get("error"), "Hub adapter: " + response.get("error", "failed"))
        return response


def public_json(url):
    require(url.startswith("https://") and ".github.io/" in url, "Expected a public GitHub Pages URL")
    req = urllib.request.Request(url, headers={"User-Agent": "dataset-factory-site-verifier", "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
        require(len(raw) <= 2 * 1024 * 1024, "Site verification response exceeded 2 MiB")
        return json.loads(raw) if url.endswith(".json") else raw.decode()
    except (OSError, ValueError):
        return None


def page_has_links(text, urls):
    if not isinstance(text, str):
        return False
    class Links(HTMLParser):
        def __init__(self):
            super().__init__()
            self.urls = set()
        def handle_starttag(self, tag, attrs):
            if tag == "a":
                self.urls.add(dict(attrs).get("href"))
    parser = Links()
    parser.feed(text)
    return set(urls).issubset(parser.urls)


def inspect(plan, gh, hub):
    """Read-only preflight. Does not treat a 404 as proof that a name is available."""
    r = plan["record"]
    results = {"github": gh.verify_dataset(r), "huggingface": hub.run("read", r), "targets": {}}
    for kind, target in plan["targets"].items():
        repo = target["repository"]
        info = gh.repo(repo, missing_ok=True)
        results["targets"][kind] = {"repository": repo, "accessible": info is not None}
        if info:
            results["targets"][kind].update({"private": info["private"], "default_branch": info["default_branch"],
                "pages": gh.request("GET", f"repos/{repo}/pages", missing_ok=True),
                "actions": gh.request("GET", f"repos/{repo}/actions/permissions")})
    results["ready_for_publication"] = (results["github"]["private"] is False and
                                         results["huggingface"]["private"] is False)
    return results


def ensure_record(gh, target, plan, kind):
    repo = target["repository"]
    record_path = f"{PREFIX}/records/{plan['record']['dataset']}/{plan['record']['release_tag']}.json"
    old = gh.file(repo, record_path, missing_ok=True)
    if old is not None and old != target["files"][record_path]:
        prior, new = json.loads(old), plan["record"]
        fixed = ("dataset", "release_tag", "artifact_version", "github_repository", "hf_repository", "assets",
                 "splits", "source", "qualification", "baseline", "licenses", "release_date")
        require(all(prior.get(k) == new.get(k) for k in fixed),
                "Existing dataset version has different facts; publish a new dataset version")
        require(new["site_revision"] > prior["site_revision"],
                "Website content changed; increment site_revision. Older site revisions cannot overwrite newer ones.")
    r = plan["record"]
    edition = f"{PREFIX}/editions/{r['dataset']}/{r['release_tag']}/{r['site_revision']}.json"
    existing = gh.file(repo, edition, missing_ok=True)
    require(existing is None or existing == target["files"][edition], "Existing website edition is immutable")
    gh.check_ownership(repo, kind, missing_ok=(kind == "dataset"))


def save_receipt(folder, receipt):
    receipt["observed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    temporary = Path(folder) / "receipt.json.tmp"
    temporary.write_text(dump(receipt))
    temporary.replace(Path(folder) / "receipt.json")


def reconcile(plan, folder, gh, hub, fetch=public_json):
    """One bounded pass. Re-run the same approved bundle to resume; never trust a local 'done'."""
    record = plan["record"]
    prior_path = Path(folder) / "receipt.json"
    prior = read(prior_path) if prior_path.is_file() else {}
    require(not prior or prior.get("plan_sha256") == plan["plan_sha256"], "Receipt belongs to a different plan")
    receipt = {"plan_sha256": plan["plan_sha256"], "status": "running", "steps": {},
               "dispatches": prior.get("dispatches", {})}
    steps = receipt["steps"]

    def done(step, value):
        steps[step] = value
        save_receipt(folder, receipt)

    try:
        done("github_dataset", gh.verify_dataset(record, public=True))
        done("huggingface_dataset", hub.run("read", record, public=True))
        catalog = plan["targets"]["catalog"]["repository"]
        info = gh.repo(catalog, missing_ok=True)
        if info is None:
            info = gh.create_catalog(catalog, plan["plan_sha256"])
        if gh.file(catalog, f"{PREFIX}/owner.json", missing_ok=True) is None and info.get("description") == f"Dataset Factory catalogue [site-plan:{plan['plan_sha256']}]":
            # Claim the new repository before other steps; a retry can recognize it.
            gh.commit(catalog, {f"{PREFIX}/owner.json": plan["targets"]["catalog"]["files"][f"{PREFIX}/owner.json"]},
                      "Initialize Dataset Factory catalogue ownership")
        require(info["private"] is False, "Catalogue is private; its visibility requires a separate reviewed change")
        for kind in ("dataset", "catalog"):
            target = plan["targets"][kind]
            ensure_record(gh, target, plan, kind)
            info = gh.repo(target["repository"])
            require(not info["private"], "Site target is private")
            actions = gh.request("GET", f"repos/{target['repository']}/actions/permissions")
            require(actions.get("enabled") is True, "Actions is disabled; an administrator must resolve that policy")
        # Both read-only checks happen before committing content or altering Pages settings.
        for kind in ("dataset", "catalog"):
            target, files = plan["targets"][kind], dict(plan["targets"][kind]["files"])
            record_path = f"{PREFIX}/records/{record['dataset']}/{record['release_tag']}.json"
            expected = {record_path: gh.file(target["repository"], record_path, missing_ok=True)}
            edition_path = f"{PREFIX}/editions/{record['dataset']}/{record['release_tag']}/{record['site_revision']}.json"
            expected[edition_path] = gh.file(target["repository"], edition_path, missing_ok=True)
            if kind == "dataset":
                navigation, originals = gh.dataset_navigation(record, files)
                files.update(navigation)
                expected.update(originals)
            else:
                files["README.md"] = f"# Dataset Factory\n\n" + links(record) + "\n\nWebsite sources and release records are managed by the dataset publication pipeline.\n"
            commit = gh.commit(target["repository"], files, f"Prepare website for {record['dataset']} {record['release_tag']}", expected=expected)
            done(kind + "_commit", {"repository": target["repository"], "commit": commit})
        done("huggingface_navigation", hub.run("link", record, public=True))
        for kind in ("dataset", "catalog"):
            target = plan["targets"][kind]
            repo, commit = target["repository"], steps[kind + "_commit"]["commit"]
            gh.setup_pages(repo)
            gh.homepage(repo, target["url"])
            done(kind + "_pages", {"configured": True})
            deployment = gh.deployment(repo, commit)
            if deployment["status"] == "not_deployed":
                # GitHub's workflow registration/dispatch is asynchronous. A later pass reads it back.
                last = receipt["dispatches"].get(repo, {})
                now = datetime.now(timezone.utc)
                recent = last.get("commit") == commit and (now - datetime.fromisoformat(last["at"])).total_seconds() < 120
                if not recent:
                    attempts = last.get("attempts", 0) if last.get("commit") == commit else 0
                    require(attempts < 3, "Three deployment dispatch attempts did not succeed; inspect Actions before retrying")
                    # Record intent before the API call, so an uncertain response doesn't cause an immediate duplicate.
                    receipt["dispatches"][repo] = {"commit": commit, "at": now.isoformat(), "attempts": attempts + 1}
                    save_receipt(folder, receipt)
                    gh.dispatch(repo, commit)
                deployment = {"status": "pending", "commit": commit}
            done(kind + "_deployment", deployment)
            url = (record["urls"]["version"] + "release.json" if kind == "dataset" else target["url"] + "catalog.json")
            live = fetch(url)
            records = ([live] if kind == "dataset" else (live or {}).get("releases", []))
            matches = any(r == record for r in records)
            page_url = record["urls"]["version"] if kind == "dataset" else target["url"]
            wanted_links = ([record["urls"][k] for k in ("github_release", "huggingface_version", "catalog")]
                            if kind == "dataset" else [record["urls"]["version"]])
            matches = matches and page_has_links(fetch(page_url), wanted_links)
            if deployment["status"] != "deployed" or not matches:
                receipt["status"] = "pending"
                receipt["next_action"] = "Re-run publish with the same bundle and approved plan SHA after Actions finishes; inspect any failed run."
                save_receipt(folder, receipt)
                return receipt
            done(kind + "_live", {"url": url, "record_sha256": record["record_sha256"], "verified": True})
        require(links(record) in gh.file(record["github_repository"], "README.md"), "GitHub navigation was not applied")
        hf = hub.run("read", record, public=True)
        require(hf.get("links_present") is True, "Hub navigation was not applied")
        done("cross_links", {"verified": True})
        receipt["status"] = "complete"
    except Exception as exc:
        receipt["status"] = "failed"
        receipt["error"] = str(exc) if isinstance(exc, FactoryError) else type(exc).__name__
        receipt["next_action"] = "Resolve the reported condition and rerun the same approved bundle. Do not delete resources or move tags."
        save_receipt(folder, receipt)
        raise
    save_receipt(folder, receipt)
    return receipt


def verify(plan, gh, hub, fetch=public_json):
    r = plan["record"]
    gh.verify_dataset(r, public=True)
    hf = hub.run("read", r, public=True)
    require(hf.get("links_present") and links(r) in gh.file(r["github_repository"], "README.md"),
            "Destination navigation is missing")
    dataset = fetch(r["urls"]["version"] + "release.json")
    catalog = fetch(r["urls"]["catalog"] + "catalog.json")
    require(dataset == r and any(entry == r for entry in (catalog or {}).get("releases", [])),
            "Live website/catalogue records do not match the approved release")
    require(page_has_links(fetch(r["urls"]["version"]), [r["urls"][k] for k in ("github_release", "huggingface_version", "catalog")]) and
            page_has_links(fetch(r["urls"]["catalog"]), [r["urls"]["version"]]), "Live HTML is missing required cross-links")
    return {"status": "verified", "plan_sha256": plan["plan_sha256"], "artifact_version": r["artifact_version"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    p = commands.add_parser("prepare", help="Offline validation, plan and review build; no network")
    p.add_argument("package", type=Path)
    p.add_argument("--editorial", required=True, type=Path)
    p.add_argument("--config", type=Path, default=ROOT / "config/sites.json")
    p.add_argument("--out", required=True, type=Path)
    for name in ("inspect", "publish", "verify", "status"):
        p = commands.add_parser(name)
        p.add_argument("bundle", type=Path)
        if name != "status":
            p.add_argument("--hf-python", help="Python with huggingface_hub; defaults to Scout's existing HF venv")
        if name == "publish":
            p.add_argument("--approved-plan", required=True, help="Exact SHA from the operator-reviewed plan")
            p.add_argument("--wait-seconds", type=int, default=0,
                           help="Bounded deterministic polling, 0–600 seconds; pending exits 2")
            p.add_argument("--retry-failed", action="store_true",
                           help="Reset the bounded dispatch allowance after investigating a failed deployment")
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare":
            result = prepare(args.package, read(args.editorial), read(args.config), args.out)
        else:
            plan = load_bundle(args.bundle)
            if args.action == "status":
                path = args.bundle / "receipt.json"
                result = read(path) if path.exists() else {"status": "prepared", "plan_sha256": plan["plan_sha256"]}
            else:
                gh, hub = GitHub(), Hub(args.hf_python)
                if args.action == "publish":
                    require(args.approved_plan == plan["plan_sha256"], "Approval does not match this prepared plan")
                    require(0 <= args.wait_seconds <= 600, "Wait must be 0–600 seconds")
                    with (args.bundle / "publish.lock").open("w") as lock:
                        try:
                            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        except BlockingIOError:
                            raise FactoryError("Another publisher is using this bundle") from None
                        path = args.bundle / "receipt.json"
                        if args.retry_failed and path.is_file():
                            receipt = read(path)
                            require(receipt.get("plan_sha256") == plan["plan_sha256"], "Receipt belongs to another plan")
                            receipt["dispatches"] = {}
                            save_receipt(args.bundle, receipt)
                        deadline = time.monotonic() + args.wait_seconds
                        while True:
                            result = reconcile(plan, args.bundle, gh, hub)
                            if result["status"] != "pending" or time.monotonic() + 30 > deadline:
                                break
                            time.sleep(30)
                elif args.action == "inspect":
                    result = inspect(plan, gh, hub)
                else:
                    result = verify(plan, gh, hub)
        print(dump(result), end="")
        return 2 if result.get("status") == "pending" else 0
    except (FactoryError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        error = str(exc) if isinstance(exc, FactoryError) else type(exc).__name__
        print(dump({"status": "failed", "error": error}), end="")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
