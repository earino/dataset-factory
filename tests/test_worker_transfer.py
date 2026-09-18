"""Artifact transfer and fetch between releases, and the job spec that drives them.

These run offline against fake GitHub clients, so they exercise the verification and the refusal
paths without a network or a paid worker.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from factory import worker
from factory.common import FactoryError, read_json
from workers import upload

ROOT = Path(__file__).resolve().parents[1]


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class FakeClient:
    """A release repository just real enough: assets go in, assets come out, verified."""

    def __init__(self, repo, contents, private=True, releases=None):
        self.repo, self.contents, self.private = repo, contents, private
        self.releases = {7: {"id": 7, "tag_name": "v-test"}} if releases is None else releases
        self.uploads, self.downloads = [], []

    def request(self, method, path, body=None):
        if path == f"/repos/{self.repo}":
            return {"private": self.private}
        if path.startswith(f"/repos/{self.repo}/releases/"):
            return self.releases.get(int(path.rsplit("/", 1)[-1]))
        return None

    def download(self, asset_id, dest, sha256, size=None):
        raw = self.contents[asset_id]
        if digest(raw) != sha256:
            raise upload.UploadError("Downloaded asset digest differs")
        if size is not None and len(raw) != size:
            raise upload.UploadError("size mismatch")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        self.downloads.append(asset_id)
        return len(raw)

    def ensure_asset(self, release_id, path, name, offset, size, sha256):
        raw = path.read_bytes()[offset:offset + size]
        if digest(raw) != sha256:
            raise AssertionError("uploader received the wrong bytes")
        self.uploads.append((name, raw))
        return {"id": len(self.uploads), "size": size,
                "browser_download_url": f"https://example.invalid/{name}"}


def credentials(base: Path, repo="owner/staging"):
    (base / "credentials.json").write_text(json.dumps({"token": "fake", "repo": repo}))


class Transfer(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        credentials(self.base)

    def run_transfer(self, spec, source_contents, target_private=True, releases=None):
        source = FakeClient("owner/staging", source_contents)
        target = FakeClient("owner/dataset", {}, private=target_private, releases=releases)
        clients = {source.repo: source, target.repo: target}
        job = {"id": "job", "transfer": spec}
        with patch("workers.upload.GitHub", side_effect=lambda token, repo: clients[repo]):
            report: dict = {"job_id": "job"}
            upload.transfer(self.base, job, report)
        return report, source, target

    def spec(self, items, allow_public=False):
        spec = {"source_repo": "owner/staging", "source_release": 1,
                "target_repo": "owner/dataset", "target_release": 7, "assets": items}
        if allow_public:
            spec["allow_public"] = True
        return spec

    def test_copies_every_asset_and_reports_verified_hashes(self):
        payloads = {11: b"train" * 100, 12: b"eval" * 50}
        items = [{"source_asset_id": asset, "target_name": name, "size": len(raw),
                  "sha256": digest(raw)}
                 for (asset, raw), name in zip(sorted(payloads.items()),
                                               ["task/public/train.csv", "task/public/eval.csv"])]
        report, _, target = self.run_transfer(self.spec(items), payloads)
        self.assertEqual(len(report["transfer"]["transferred"]), 2)
        self.assertEqual(report["transfer"]["failures"], [])
        self.assertEqual([name for name, _ in target.uploads],
                         ["task/public/train.csv", "task/public/eval.csv"])
        self.assertEqual(report["transfer"]["bytes"], sum(len(r) for r in payloads.values()))

    def test_leaves_nothing_behind_in_the_worker_cache(self):
        payload = {11: b"x" * 4096}
        items = [{"source_asset_id": 11, "target_name": "task/meta.json", "size": 4096,
                  "sha256": digest(payload[11])}]
        self.run_transfer(self.spec(items), payload)
        leftovers = list((self.base / "cache").iterdir())
        self.assertEqual(leftovers, [], "the transferred bytes must not stay on the worker")

    def test_refuses_a_public_target_without_explicit_authorisation(self):
        payload = {11: b"x"}
        items = [{"source_asset_id": 11, "target_name": "task/meta.json", "size": 1,
                  "sha256": digest(b"x")}]
        with self.assertRaisesRegex(upload.UploadError, "public"):
            self.run_transfer(self.spec(items), payload, target_private=False)

    def test_allows_a_public_target_only_when_the_job_says_so(self):
        payload = {11: b"x"}
        items = [{"source_asset_id": 11, "target_name": "task/meta.json", "size": 1,
                  "sha256": digest(b"x")}]
        report, _, target = self.run_transfer(self.spec(items, allow_public=True), payload,
                                              target_private=False)
        self.assertEqual(len(target.uploads), 1)

    def test_refuses_a_target_release_that_does_not_exist(self):
        with self.assertRaisesRegex(upload.UploadError, "Target release"):
            self.run_transfer(self.spec([{"source_asset_id": 11, "target_name": "n", "size": 1,
                                          "sha256": digest(b"x")}]), {11: b"x"}, releases={})

    def test_records_a_failure_and_refuses_to_call_the_transfer_complete(self):
        # The recorded hash does not match what the source actually holds.
        items = [{"source_asset_id": 11, "target_name": "task/meta.json", "size": 1,
                  "sha256": digest(b"other")}]
        with self.assertRaisesRegex(upload.UploadError, "did not transfer"):
            self.run_transfer(self.spec(items), {11: b"x"})

    def test_an_asset_that_arrives_wrong_is_never_uploaded(self):
        items = [{"source_asset_id": 11, "target_name": "task/meta.json", "size": 1,
                  "sha256": digest(b"other")}]
        source = FakeClient("owner/staging", {11: b"x"})
        target = FakeClient("owner/dataset", {})
        clients = {source.repo: source, target.repo: target}
        with patch("workers.upload.GitHub", side_effect=lambda token, repo: clients[repo]):
            with self.assertRaises(upload.UploadError):
                upload.transfer(self.base, {"id": "job", "transfer": self.spec(items)},
                                {"job_id": "job"})
        self.assertEqual(target.uploads, [], "a bad download must not reach the target release")


class Fetch(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        credentials(self.base)

    def test_downloads_into_the_cache_with_verified_digests(self):
        payload = b"train" * 10
        client = FakeClient("owner/dataset", {5: payload})
        job = {"id": "job", "fetch": {"repo": "owner/dataset", "release": 7, "assets": [
            {"asset_id": 5, "dest": "extract/public/train.csv", "size": len(payload),
             "sha256": digest(payload)}]}}
        with patch("workers.upload.GitHub", return_value=client):
            report: dict = {"job_id": "job"}
            upload.fetch(self.base, job, report)
        written = (self.base / "cache" / "extract/public/train.csv").read_bytes()
        self.assertEqual(written, payload)
        self.assertEqual(report["fetch"]["bytes"], len(payload))
        self.assertEqual(report["fetch"]["failures"], [])

    def test_refuses_when_the_released_bytes_do_not_match(self):
        client = FakeClient("owner/dataset", {5: b"tampered"})
        job = {"id": "job", "fetch": {"repo": "owner/dataset", "assets": [
            {"asset_id": 5, "dest": "extract/public/train.csv", "sha256": digest(b"expected")}]}}
        with patch("workers.upload.GitHub", return_value=client):
            with self.assertRaisesRegex(upload.UploadError, "did not download"):
                upload.fetch(self.base, job, {"job_id": "job"})
        self.assertFalse((self.base / "cache" / "extract/public/train.csv").exists())


class DownloadRedirects(unittest.TestCase):
    """The asset endpoint 302s to a signed URL on another host."""

    def test_follows_the_redirect_without_sending_the_token_to_the_new_host(self):
        from unittest.mock import MagicMock
        payload = b"payload"
        first, second = MagicMock(), MagicMock()
        first.getresponse.return_value.status = 302
        first.getresponse.return_value.getheader.return_value = \
            "https://objects.example.invalid/blob?sig=abc"
        second.getresponse.return_value.status = 200
        second.getresponse.return_value.read.side_effect = [payload, b""]
        with patch("workers.upload.http.client.HTTPSConnection",
                   side_effect=[first, second]) as connections:
            with tempfile.TemporaryDirectory() as tmp:
                dest = Path(tmp) / "asset"
                written = upload.GitHub("secret-token", "owner/private").download(
                    5, dest, digest(payload), len(payload))
                self.assertEqual(written, len(payload))
                self.assertEqual(dest.read_bytes(), payload)
        self.assertEqual(connections.call_args_list[0].args[0], "api.github.com")
        self.assertEqual(connections.call_args_list[1].args[0], "objects.example.invalid")
        self.assertIn("Authorization", first.request.call_args.kwargs["headers"])
        self.assertNotIn("Authorization", second.request.call_args.kwargs["headers"],
                         "the token must not follow a redirect to another host")

    def test_a_non_200_after_the_redirect_is_refused(self):
        from unittest.mock import MagicMock
        first, second = MagicMock(), MagicMock()
        first.getresponse.return_value.status = 302
        first.getresponse.return_value.getheader.return_value = "https://objects.example.invalid/x"
        second.getresponse.return_value.status = 403
        with patch("workers.upload.http.client.HTTPSConnection", side_effect=[first, second]):
            with tempfile.TemporaryDirectory() as tmp:
                dest = Path(tmp) / "asset"
                with self.assertRaisesRegex(upload.UploadError, "403"):
                    upload.GitHub("t", "owner/private").download(5, dest, digest(b"x"), 1)
                self.assertFalse(dest.exists(), "a refused download must leave nothing behind")


class JobValidation(unittest.TestCase):
    """A transfer job runs no container, so the spec is what has to be validated."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = read_json(ROOT / "config/worker.example.json")
        self.config.update(server_types={"test-type": "0.03"}, allowed_locations=["test-place"],
                           enabled=True, cleanup_configured=True, monthly_budget_eur=10)
        self.job = read_json(ROOT / "examples/smoke/job.json")
        self.job.update(server_type="test-type", location="test-place")
        # A transfer needs its own credential; point it at a fixture so the tests do not depend on
        # this host's secrets.
        publish = self.root / "publish.token"
        publish.write_text("fixture-not-a-token\n")
        publish.chmod(0o600)      # the credential reader refuses a world-readable token file
        os.environ["FACTORY_PUBLISH_TOKEN_FILE"] = str(publish)
        self.addCleanup(os.environ.pop, "FACTORY_PUBLISH_TOKEN_FILE", None)

    def validate(self, job):
        worker.validate(job, self.config)

    def test_a_transfer_job_needs_no_command_and_no_image(self):
        job = dict(self.job, transfer={"source_repo": "owner/staging", "target_repo": "owner/d",
                                       "target_release": 7,
                                       "assets": [{"source_asset_id": 1, "target_name": "n",
                                                   "size": 1, "sha256": "a" * 64}]})
        job.pop("command")
        self.validate(job)

    def test_a_container_job_still_needs_a_command(self):
        job = {key: value for key, value in self.job.items() if key != "command"}
        with self.assertRaisesRegex(FactoryError, "command"):
            self.validate(job)

    def test_a_malformed_transfer_spec_is_refused_at_launch(self):
        job = dict(self.job, transfer={"source_repo": "owner/staging", "assets": []})
        with self.assertRaisesRegex(FactoryError, "missing"):
            self.validate(job)

    def test_a_transfer_asset_missing_its_hash_is_refused(self):
        job = dict(self.job, transfer={"source_repo": "owner/staging", "target_repo": "owner/d",
                                       "target_release": 7,
                                       "assets": [{"source_asset_id": 1, "target_name": "n",
                                                   "size": 1}]})
        with self.assertRaisesRegex(FactoryError, "missing"):
            self.validate(job)

    def test_a_fetch_asset_missing_its_destination_is_refused(self):
        job = dict(self.job, fetch={"repo": "owner/d", "assets": [{"asset_id": 1, "sha256": "a"}]})
        with self.assertRaisesRegex(FactoryError, "missing"):
            self.validate(job)

    def test_a_transfer_without_its_own_credential_is_refused_before_provisioning(self):
        """The staging token is scoped to staging, so a transfer needs the publish credential.

        Checked here rather than on a paid worker: a 404 on the target repository used to surface
        as a dead worker with no report at all.
        """
        os.environ["FACTORY_PUBLISH_TOKEN_FILE"] = str(self.root / "absent.token")
        self.addCleanup(os.environ.pop, "FACTORY_PUBLISH_TOKEN_FILE", None)
        job = dict(self.job, transfer={"source_repo": "owner/staging", "target_repo": "owner/d",
                                       "target_release": 7,
                                       "assets": [{"source_asset_id": 1, "target_name": "n",
                                                   "size": 1, "sha256": "a" * 64}]})
        with self.assertRaisesRegex(FactoryError, "FACTORY_PUBLISH_TOKEN"):
            self.validate(job)

    def test_a_container_job_does_not_need_the_publish_credential(self):
        os.environ["FACTORY_PUBLISH_TOKEN_FILE"] = str(self.root / "absent.token")
        self.addCleanup(os.environ.pop, "FACTORY_PUBLISH_TOKEN_FILE", None)
        self.validate(self.job)          # no transfer, so the staging token is enough


if __name__ == "__main__":
    unittest.main()
