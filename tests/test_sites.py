"""Website lifecycle acceptance: another dataset, interrupted publication and immutable versions."""
import copy
import json
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
from unittest.mock import patch

from factory.common import FactoryError
from factory.site_model import project, read, dump, digest, linked_readme, links
from factory.site_pipeline import prepare, load_bundle, reconcile, verify, Hub
from factory.site_github import GitHub

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = runpy.run_path(str(ROOT / "sites/runtime.py"))


class FakeGitHub:
    """Persistent service state; receipts may disappear without losing committed work."""
    def __init__(self, record):
        self.repos = {}
        self.files = {}
        self.heads = {}
        self.dispatches = []
        self.deployed = set()
        self.commits = 0
        self.add_dataset(record)

    def add_dataset(self, record):
        repo = record["github_repository"]
        self.repos[repo] = {"private": False, "default_branch": "main"}
        self.files[repo] = {"README.md": "Original dataset documentation\n"}
        self.heads[repo] = "0" * 40

    def repo(self, repo, missing_ok=False):
        return self.repos.get(repo)

    def create_catalog(self, repo, plan_sha):
        self.repos[repo] = {"private": False, "default_branch": "main",
                            "description": f"Dataset Factory catalogue [site-plan:{plan_sha}]"}
        self.files[repo], self.heads[repo] = {}, "0" * 40
        return self.repos[repo]

    def file(self, repo, path, **kwargs):
        return self.files[repo].get(path)

    def request(self, method, path, *args, **kwargs):
        if path.endswith("actions/permissions"):
            return {"enabled": True}
        raise AssertionError((method, path))

    def check_ownership(self, repo, kind, missing_ok=False):
        actual = self.file(repo, ".dataset-site/owner.json")
        if actual is None:
            if not missing_ok:
                raise FactoryError("unmanaged catalogue")
        elif json.loads(actual)["kind"] != kind:
            raise FactoryError("wrong owner")

    def dataset_navigation(self, record, managed=None):
        repo = record["github_repository"]
        old = self.files[repo]["README.md"]
        return {"README.md": linked_readme(old, record)}, {"README.md": old}

    def verify_dataset(self, record, public=False):
        private = self.repos[record["github_repository"]]["private"]
        if public and private:
            raise FactoryError("private dataset")
        return {"private": private, "verified": True}

    def commit(self, repo, files, message, expected=None):
        for path, value in (expected or {}).items():
            if self.files[repo].get(path) != value:
                raise FactoryError("concurrent edit")
        if any(self.files[repo].get(k) != v for k, v in files.items()):
            self.commits += 1
            self.heads[repo] = f"{self.commits:040x}"
            self.files[repo].update(files)
        return self.heads[repo]

    def setup_pages(self, repo):
        pass

    def homepage(self, repo, url):
        self.repos[repo]["homepage"] = url

    def dispatch(self, repo, commit):
        self.dispatches.append((repo, commit))

    def deployment(self, repo, commit):
        return {"status": "deployed" if (repo, commit) in self.deployed else "not_deployed", "commit": commit}

    def settle(self):
        self.deployed.update(self.dispatches)

    def fetch(self, url):
        for repo in self.files:
            if (repo, self.heads[repo]) not in self.deployed:
                continue
            files = self.files[repo]
            records = [json.loads(text) for path, text in files.items() if path.startswith(".dataset-site/records/")]
            for r in records:
                if url == r["urls"]["version"] + "release.json":
                    return r
                if url == r["urls"]["catalog"] + "catalog.json" and repo != r["github_repository"]:
                    return {"schema_version": 1, "releases": records}
                config = json.loads(files[".dataset-site/config.json"])
                if config["kind"] == "dataset" and url == r["urls"]["version"]:
                    return RUNTIME["render"](config, records)[f'versions/{r["release_tag"]}/index.html']
                if config["kind"] == "catalog" and url == r["urls"]["catalog"]:
                    return RUNTIME["render"](config, records)["index.html"]
        return None


class FakeHub:
    def __init__(self):
        self.linked = set()
        self.fail_once = False

    def run(self, action, record, public=False):
        if action == "link":
            if self.fail_once:
                self.fail_once = False
                raise FactoryError("simulated interrupted Hub write")
            self.linked.add(record["record_sha256"])
        return {"verified": True, "private": False, "links_present": record["record_sha256"] in self.linked}


class WebsiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.out = self.root / "prepared"
        self.config = read(ROOT / "config/sites.json")
        self.editorial = read(ROOT / "sites/austin-911-response.json")
        prepare(ROOT / "release/austin-911-response", self.editorial, self.config, self.out)
        self.plan = load_bundle(self.out)
        self.record = self.plan["record"]

    def complete(self, plan, folder, gh, hub):
        for _ in range(4):
            result = reconcile(plan, folder, gh, hub, gh.fetch)
            if result["status"] == "complete":
                return result
            gh.settle()
        self.fail("publication did not converge")

    def test_prepare_is_offline_deterministic_and_preserves_input(self):
        before = (ROOT / "release/austin-911-response/MANIFEST.json").read_bytes()
        with patch("subprocess.run", side_effect=AssertionError("network/tool invocation")), patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            result = prepare(ROOT / "release/austin-911-response", self.editorial, self.config, self.out)
        self.assertEqual(result["network_calls"], 0)
        self.assertEqual(result["plan_sha256"], self.plan["plan_sha256"])
        self.assertEqual(before, (ROOT / "release/austin-911-response/MANIFEST.json").read_bytes())
        self.assertNotIn("staging_repo", dump(self.record))
        self.assertNotIn("artifact_job", dump(self.record))
        self.assertNotIn("earino/dataset-factory-staging", dump(self.plan))
        self.assertEqual(sum(s["rows"] for s in self.record["splits"].values()), 1049636)

    def test_changed_review_bundle_is_refused(self):
        plan = read(self.out / "bundle.json")
        plan["record"]["title"] = "Different title"
        (self.out / "bundle.json").write_text(dump(plan))
        with self.assertRaisesRegex(FactoryError, "changed after review"):
            load_bundle(self.out)

    def test_wrong_destination_version_is_refused(self):
        original = read(ROOT / "release/austin-911-response/DESTINATIONS.json")
        original["release_tag"] = "v9999"
        from factory import site_model
        actual_read = site_model.read
        with patch.object(site_model, "read", side_effect=lambda p: original if p.name == "DESTINATIONS.json" else actual_read(p)):
            with self.assertRaisesRegex(FactoryError, "different release"):
                project(ROOT / "release/austin-911-response", self.editorial, self.config)

    def test_private_data_blocks_before_any_mutation(self):
        gh, hub = FakeGitHub(self.record), FakeHub()
        gh.repos[self.record["github_repository"]]["private"] = True
        with self.assertRaisesRegex(FactoryError, "private dataset"):
            reconcile(self.plan, self.out, gh, hub, gh.fetch)
        self.assertEqual(gh.commits, 0)
        self.assertFalse(gh.dispatches)
        self.assertEqual(read(self.out / "receipt.json")["status"], "failed")

    def test_deploy_dataset_before_catalog_and_rerun_does_nothing(self):
        gh, hub = FakeGitHub(self.record), FakeHub()
        first = reconcile(self.plan, self.out, gh, hub, gh.fetch)
        self.assertEqual(first["status"], "pending")
        self.assertEqual([r for r, _ in gh.dispatches], [self.record["github_repository"]])
        reconcile(self.plan, self.out, gh, hub, gh.fetch)
        self.assertEqual(len(gh.dispatches), 1, "immediate retry must not dispatch again")
        self.complete(self.plan, self.out, gh, hub)
        previous = (gh.commits, len(gh.dispatches))
        self.assertEqual(reconcile(self.plan, self.out, gh, hub, gh.fetch)["status"], "complete")
        self.assertEqual(previous, (gh.commits, len(gh.dispatches)))
        self.assertEqual(verify(self.plan, gh, hub, gh.fetch)["status"], "verified")

    def test_recovers_after_hub_failure_and_lost_local_receipt(self):
        gh, hub = FakeGitHub(self.record), FakeHub()
        hub.fail_once = True
        with self.assertRaisesRegex(FactoryError, "interrupted"):
            reconcile(self.plan, self.out, gh, hub, gh.fetch)
        commits = gh.commits
        (self.out / "receipt.json").unlink()
        self.complete(self.plan, self.out, gh, hub)
        self.assertEqual(gh.commits, commits)

    def test_second_dataset_uses_same_code_and_keeps_first(self):
        gh, hub = FakeGitHub(self.record), FakeHub()
        self.complete(self.plan, self.out, gh, hub)
        old = self.record["dataset"]
        # A second metadata fixture goes through the real preparation contract, not a special renderer path.
        package = self.root / "second-package"
        shutil.copytree(ROOT / "release/austin-911-response", package)
        for filename in ("MANIFEST.json", "DESTINATIONS.json"):
            (package / filename).write_text((package / filename).read_text().replace(old, "second-task").replace("v2026.09", "v2026.10"))
        editorial = copy.deepcopy(self.editorial)
        editorial.update({"title": "Second task fixture", "release_date": "2026-10-01"})
        other = self.root / "second"
        prepare(package, editorial, self.config, other)
        second = load_bundle(other)
        record = second["record"]
        gh.add_dataset(record)
        self.complete(second, other, gh, hub)
        catalog = self.config["catalog_repository"]
        records = [json.loads(v) for k, v in gh.files[catalog].items() if k.startswith(".dataset-site/records/")]
        self.assertEqual({r["dataset"] for r in records}, {old, "second-task"})
        rendered = RUNTIME["render"](json.loads(gh.files[catalog][".dataset-site/config.json"]), records)
        self.assertIn("releases/second-task/v2026.10/index.html", rendered)
        self.assertIn("releases/austin-911-response/v2026.09/index.html", rendered)

    def test_reusing_version_for_different_content_is_refused(self):
        gh, hub = FakeGitHub(self.record), FakeHub()
        self.complete(self.plan, self.out, gh, hub)
        changed = copy.deepcopy(self.plan)
        changed["targets"]["dataset"]["files"][".dataset-site/records/austin-911-response/v2026.09.json"] = "{}"
        with self.assertRaisesRegex(FactoryError, "increment site_revision"):
            reconcile(changed, self.out, gh, hub, gh.fetch)

    def test_editorial_correction_preserves_dataset_and_earlier_edition(self):
        gh, hub = FakeGitHub(self.record), FakeHub()
        self.complete(self.plan, self.out, gh, hub)
        editorial = copy.deepcopy(self.editorial)
        editorial.update({"summary": "Corrected explanation of the same dataset.", "site_revision": 2})
        folder = self.root / "edition2"
        prepare(ROOT / "release/austin-911-response", editorial, self.config, folder)
        second = load_bundle(folder)
        self.complete(second, folder, gh, hub)
        repo = self.record["github_repository"]
        for edition in (1, 2):
            self.assertIn(f".dataset-site/editions/austin-911-response/v2026.09/{edition}.json", gh.files[repo])
        self.assertEqual(second["record"]["artifact_version"], self.record["artifact_version"])
        with self.assertRaisesRegex(FactoryError, "Older site revisions"):
            reconcile(self.plan, self.out, gh, hub, gh.fetch)

    def test_card_navigation_preserves_yaml_and_is_idempotent(self):
        original = "---\nlicense: cc0-1.0\n---\n\n# Card\nOriginal text\n"
        updated = linked_readme(original, self.record)
        self.assertTrue(updated.startswith(original.rstrip()))
        self.assertEqual(updated, linked_readme(updated, self.record))
        self.assertIn(links(self.record), updated)

    def test_renderer_escapes_editorial_and_checks_record_digest(self):
        record = copy.deepcopy(self.record)
        record["title"] = '<script>alert("bad")</script>'
        record.pop("record_sha256")
        record["record_sha256"] = digest(dump(record))
        config = json.loads(self.plan["targets"]["dataset"]["files"][".dataset-site/config.json"])
        text = RUNTIME["render"](config, [record])["index.html"]
        self.assertNotIn("<script>", text)
        self.assertIn("&lt;script&gt;", text)
        record["title"] = "tampered"
        with self.assertRaisesRegex(ValueError, "digest"):
            RUNTIME["render"](config, [record])

    def test_refuses_non_owned_output_and_symlinks(self):
        out = self.root / "unrelated"
        out.mkdir()
        (out / "important.txt").write_text("keep")
        with self.assertRaisesRegex(ValueError, "non-owned"):
            RUNTIME["write_output"](out, {"index.html": "new"})
        self.assertEqual((out / "important.txt").read_text(), "keep")
        alias = self.root / "alias"
        alias.symlink_to(out)
        with self.assertRaisesRegex(ValueError, "symlink"):
            RUNTIME["write_output"](alias, {"index.html": "new"})

    def test_hub_process_isolated_from_inference_token(self):
        import subprocess
        with patch.dict("os.environ", {"HF_TOKEN": "inference-test-sentinel", "HF_TOKEN_WRITE": "write-test-sentinel"}), \
             patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, '{"verified": true}', "")) as run:
            Hub("/example/python").run("read", self.record)
        kwargs = run.call_args.kwargs
        self.assertNotIn("HF_TOKEN", kwargs["env"])
        self.assertNotIn("write-test-sentinel", str(run.call_args.args))
        self.assertNotIn("write-test-sentinel", kwargs["input"])

    def test_verify_refuses_correct_json_with_broken_html_links(self):
        gh, hub = FakeGitHub(self.record), FakeHub()
        self.complete(self.plan, self.out, gh, hub)
        def broken(url):
            return gh.fetch(url) if url.endswith(".json") else "<html>stale page</html>"
        with self.assertRaisesRegex(FactoryError, "HTML"):
            verify(self.plan, gh, hub, broken)

    def test_default_branch_concurrency_check_rejects_overwrite(self):
        class RaceGitHub(GitHub):
            def repo(self, repo, missing_ok=False):
                return {"default_branch": "main"}
            def request(self, method, path, *args, **kwargs):
                if method != "GET":
                    raise AssertionError("must refuse before writing")
                if "/git/ref/" in path:
                    return {"object": {"sha": "head"}}
                if "/git/commits/" in path:
                    return {"tree": {"sha": "tree"}}
                return {"tree": [{"path": "README.md", "mode": "100644", "sha": "newer"}]}
        with self.assertRaisesRegex(FactoryError, "Concurrent edit"):
            RaceGitHub().commit("owner/repo", {"README.md": "proposed"}, "update", expected={"README.md": "old"})


if __name__ == "__main__":
    unittest.main()
