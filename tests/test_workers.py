import copy
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from factory import candidates, worker
from factory.cloud import Cloud
from factory.common import FactoryError, read_json, write_json
from workers import upload, executor

ROOT = Path(__file__).resolve().parents[1]


class FakeCloud:
    def __init__(self):
        self.servers = []
        self.created = 0
        self.deleted = []
        self.ambiguous = False

    def list_resources(self, resource, project):
        return copy.deepcopy(self.servers) if resource == "servers" else []

    def server(self, server_id):
        return next((s for s in self.servers if s["id"] == server_id), None)

    def request(self, method, path, body=None):
        if path == "pricing":
            price = [{"location": "test-place", "price_hourly": {"gross": "0.01"}}]
            return {"pricing": {"currency": "EUR", "server_types": [{"name": "test-type", "prices": price}],
                                "primary_ips": [{"type": "ipv4", "prices": price}]}}
        if method == "POST" and path == "servers":
            self.created += 1
            server = {"id": 123, "labels": body["labels"], "public_net": {"ipv4": {"ip": "192.0.2.1"}}}
            self.servers.append(server)
            if self.ambiguous:
                raise FactoryError("Lost create response")
            return {"server": server, "action": {"id": 1, "status": "success"}}
        raise AssertionError((method, path))

    def label_ips(self, server):
        pass

    def wait_action(self, action):
        pass

    def clean_job_ips(self, project, job_id):
        pass

    def clean_expired_ips(self, project, now):
        return []

    def delete_owned(self, server, project, job_id):
        self.deleted.append(server["id"])
        self.servers = [s for s in self.servers if s["id"] != server["id"]]


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "jobs").mkdir()
        source = self.root / "source"
        source.mkdir()
        self.path = source / "job.json"
        (source / "run.py").write_text("print('hello')\n")
        key = self.root / "key"
        key.write_text("fixture-not-a-key")
        self.job = read_json(ROOT / "examples/smoke/job.json")
        self.job.update(server_type="test-type", location="test-place")
        write_json(self.path, self.job)
        self.config = read_json(ROOT / "config/worker.example.json")
        self.config.update(enabled=True, cleanup_configured=True, monthly_budget_eur=10,
                           server_types={"test-type": "0.03"}, allowed_locations=["test-place"],
                           ssh_private_key=str(key), ssh_key_name="test", staging_repo="owner/private")
        self.cloud = FakeCloud()
        self.github = patch("factory.worker.github").start()
        self.addCleanup(patch.stopall)

    def launch(self):
        with patch("factory.worker.resume", return_value={"status": "running"}):
            worker.launch(self.root, self.path, self.config, self.cloud)
        return worker.load_record(self.root, self.job["id"])

    def test_disabled_launch_makes_no_api_calls(self):
        self.config["enabled"] = False
        with self.assertRaises(FactoryError):
            self.launch()
        self.github.assert_not_called()
        self.assertEqual(self.cloud.created, 0)

    def test_allowance_blocks_before_creation(self):
        self.config["monthly_budget_eur"] = "0.01"
        with self.assertRaisesRegex(FactoryError, "allowance"):
            self.launch()
        self.assertEqual(self.cloud.created, 0)

    def test_cross_month_reservation_checks_next_month(self):
        write_json(self.root / "jobs/old.json", {"status": "deleted", "reservation_eur": "9.98",
                                                "budget_months": ["2026-10"]})
        with patch("factory.worker.utcnow", return_value=datetime(2026, 9, 30, 23, 50, tzinfo=timezone.utc)):
            with self.assertRaisesRegex(FactoryError, "allowance"):
                self.launch()
        self.assertEqual(self.cloud.created, 0)

    def test_provider_price_above_ceiling_blocks_creation(self):
        self.config["server_types"]["test-type"] = "0.001"
        with self.assertRaisesRegex(FactoryError, "price exceeds"):
            self.launch()
        self.assertEqual(self.cloud.created, 0)

    def test_ambiguous_creation_reconciles_without_duplicate(self):
        self.cloud.ambiguous = True
        with self.assertRaisesRegex(FactoryError, "Lost create"):
            self.launch()
        self.assertIsNone(worker.load_record(self.root, self.job["id"])["server_id"])
        record = worker.reconcile(self.root, self.job["id"], self.config, self.cloud)
        self.assertEqual(record["server_id"], 123)
        with self.assertRaisesRegex(FactoryError, "already recorded"):
            self.launch()
        self.assertEqual(self.cloud.created, 1)

    def test_active_job_blocks_another_id(self):
        self.launch()
        self.job["id"] = "another"
        write_json(self.path, self.job)
        with self.assertRaisesRegex(FactoryError, "interrupted job"):
            self.launch()
        self.assertEqual(self.cloud.created, 1)

    def test_lost_creation_without_server_clears_only_after_expiry(self):
        self.cloud.ambiguous = True
        with self.assertRaises(FactoryError):
            self.launch()
        self.cloud.servers = []
        record = worker.reconcile(self.root, self.job["id"], self.config, self.cloud)
        self.assertEqual(record["status"], "creation-unresolved")
        with patch("factory.worker.time.time", return_value=record["expires"] + 3601):
            record = worker.reconcile(self.root, self.job["id"], self.config, self.cloud)
        self.assertEqual(record["status"], "deleted")
        self.assertEqual(record["reservation_eur"], "0.06")

    def test_bundle_is_identical_across_checkout_mtimes(self):
        first = worker.source_bundle(self.path, self.job)
        os.utime(self.path.parent / "run.py", (1000, 1000))
        (self.path.parent / "run.py").chmod(0o755)
        self.assertEqual(first, worker.source_bundle(self.path, self.job))
        with tarfile.open(fileobj=io.BytesIO(first)) as archive:
            self.assertEqual(set(archive.getnames()), {"source/run.py", "job.json", "executor.py", "upload.py"})

    def test_bundle_rejects_hidden_files_and_symlinks(self):
        bad = self.path.parent / ".env"
        bad.write_text("not-a-secret")
        with self.assertRaises(FactoryError):
            worker.source_bundle(self.path, self.job)
        bad.unlink()
        bad.symlink_to(self.root / "key")
        with self.assertRaisesRegex(FactoryError, "symlinks"):
            worker.source_bundle(self.path, self.job)

    def test_delete_requires_verified_collection(self):
        self.launch()
        with self.assertRaisesRegex(FactoryError, "Collect and verify"):
            worker.destroy(self.root, self.job["id"], self.config, self.cloud)
        self.assertEqual(self.cloud.deleted, [])

    def test_collect_verifies_release_membership_then_allows_cleanup(self):
        self.launch()
        report = {"job_id": self.job["id"], "status": "succeeded", "uploaded": True, "repo": "owner/private",
                  "release_id": 4, "assets": [{"id": 9, "size": 12, "sha256": "abc"}]}
        self.github.return_value.request.side_effect = lambda method, path: (
            [{"id": 9, "size": 12, "digest": "sha256:abc"}] if "/assets?" in path else {"tag_name": "job-" + self.job["id"]})
        with patch("factory.worker.remote", return_value=json.dumps(report).encode()):
            self.assertEqual(worker.collect(self.root, self.job["id"], self.config, self.cloud), report)
            # Repeated collection should replace, not double-count the local report.
            self.config["max_coordinator_reports_bytes"] = len(json.dumps(report, indent=2).encode()) + 1
            worker.collect(self.root, self.job["id"], self.config, self.cloud)
        record = worker.destroy(self.root, self.job["id"], self.config, self.cloud)
        self.assertEqual(record["status"], "deleted")
        self.assertEqual(self.cloud.deleted, [123])

    def test_bad_digest_prevents_normal_cleanup(self):
        self.launch()
        report = {"job_id": self.job["id"], "status": "failed", "uploaded": True, "repo": "owner/private",
                  "release_id": 4, "assets": [{"id": 9, "size": 12, "sha256": "abc"}]}
        self.github.return_value.request.side_effect = lambda method, path: (
            [{"id": 9, "size": 12, "digest": "sha256:different"}] if "/assets?" in path else {"tag_name": "job-" + self.job["id"]})
        with patch("factory.worker.remote", return_value=json.dumps(report).encode()):
            with self.assertRaisesRegex(FactoryError, "mismatch"):
                worker.collect(self.root, self.job["id"], self.config, self.cloud)
        self.assertNotEqual(worker.load_record(self.root, self.job["id"])["status"], "collected")

    def test_sweep_only_expired_owned_workers(self):
        for index, (project, expires) in enumerate([(self.config["project"], 99), (self.config["project"], 101), ("other", 99)]):
            self.cloud.servers.append({"id": index, "labels": {"factory": project, "job": f"job-{index}", "expires": str(expires)}})
        result = worker.sweep(self.config["project"], self.cloud, now=100)
        self.assertEqual(result["deleted_servers"], [0])

    def test_candidate_rejects_traversal_and_overwrite(self):
        with self.assertRaises(FactoryError):
            candidates.create(self.root, "../escape")
        candidates.create(self.root, "lead")
        with self.assertRaises(FactoryError):
            candidates.create(self.root, "lead")


class DeletionTests(unittest.TestCase):
    def test_deletion_refetches_ownership(self):
        cloud = object.__new__(Cloud)
        with patch.object(cloud, "server", return_value={"id": 3, "labels": {"factory": "other", "job": "ours"}}), \
             patch.object(cloud, "request") as request:
            with self.assertRaisesRegex(FactoryError, "ownership"):
                cloud.delete_owned({"id": 3}, "ours", "ours")
            request.assert_not_called()

    def test_attached_volume_blocks_deletion(self):
        cloud = object.__new__(Cloud)
        with patch.object(cloud, "server", return_value={"id": 3, "labels": {"factory": "ours", "job": "job"}, "volumes": [4]}), \
             patch.object(cloud, "request") as request:
            with self.assertRaisesRegex(FactoryError, "volumes"):
                cloud.delete_owned({"id": 3}, "ours", "job")
            request.assert_not_called()


class ArtifactTests(unittest.TestCase):
    def test_publish_round_trip_reuses_draft_and_verifies_manifest(self):
        class Store:
            repo = "owner/private"
            def __init__(self):
                self.release = None
                self.files = {}
                self.creations = 0
            def request(self, method, path, body=None):
                if path == "/repos/owner/private":
                    return {"private": True}
                if method == "GET":
                    return [self.release] if self.release else []
                self.creations += 1
                self.release = {"id": 7, "tag_name": body["tag_name"], "html_url": "https://github.com/owner/private/releases/7"}
                return self.release
            def ensure_asset(self, release_id, path, name, offset, size, sha256):
                raw = path.read_bytes()[offset:offset + size]
                if hashlib.sha256(raw).hexdigest() != sha256:
                    raise AssertionError("Incorrect artifact digest")
                if name in self.files and self.files[name] != raw:
                    raise AssertionError("Retry would replace artifact")
                self.files[name] = raw
                return {"id": list(self.files).index(name) + 1, "size": size,
                        "browser_download_url": "https://github.com/owner/private/" + name}
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "output").mkdir()
            (base / "output/data.csv").write_text("target,feature\n1,2\n")
            (base / "source.tar").write_bytes(b"source fixture")
            (base / "container.log").write_text("finished\n")
            (base / "credentials.json").write_text('{"token":"fake", "repo":"owner/private"}')
            job = {"id": "job", "max_artifact_mb": 10}
            result = {"job_id": "job", "status": "succeeded", "uploaded": False}
            client = Store()
            first = upload.publish(base, job, result, client)
            self.assertEqual(first, upload.publish(base, job, result, client))
            self.assertEqual(client.creations, 1)
            manifest = json.loads(client.files["manifest.json"])
            self.assertEqual(len(first["assets"]), 4)
            self.assertEqual(manifest["assets"][0]["file"], "output/data.csv")
            self.assertNotIn(b"fake", client.files["manifest.json"])

    def test_http_upload_streams_file_in_bounded_chunks(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data"
            path.write_bytes(b"a" * (3 * 1024**2 + 7))
            connection = MagicMock()
            connection.getresponse.return_value.status = 201
            connection.getresponse.return_value.read.return_value = b'{}'
            with patch("workers.upload.http.client.HTTPSConnection", return_value=connection):
                upload.GitHub("fake", "owner/private").request("POST", "/upload", upload=(path, 0, path.stat().st_size))
            chunks = [call.args[0] for call in connection.send.call_args_list]
            self.assertEqual(sum(map(len, chunks)), path.stat().st_size)
            self.assertLessEqual(max(map(len, chunks)), 1024**2)
            connection.close.assert_called_once()

    def test_split_parts_reconstruct_original_with_expected_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data"
            original = b"arbitrary bytes\x00\x01\xff" * 100
            path.write_bytes(original)
            parts = upload.parts([("data", path)], part_bytes=100)
            recovered = b""
            for item in parts:
                raw = original[item["offset"]:item["offset"] + item["size"]]
                self.assertEqual(hashlib.sha256(raw).hexdigest(), item["sha256"])
                recovered += raw
            self.assertEqual(recovered, original)

    def test_existing_different_asset_is_never_overwritten(self):
        client = upload.GitHub("fake", "owner/repo")
        with patch.object(client, "assets", return_value=[{"id": 1, "name": "a", "state": "uploaded", "size": 1, "digest": "sha256:other"}]), \
             patch.object(client, "request") as request:
            with self.assertRaisesRegex(upload.UploadError, "refusing"):
                client.ensure_asset(1, Path("unused"), "a", 0, 1, "expected")
            request.assert_not_called()

    def test_lost_upload_response_reconciles_without_reupload(self):
        client = upload.GitHub("fake", "owner/repo")
        asset = {"id": 1, "name": "a", "state": "uploaded", "size": 1, "digest": "sha256:expected"}
        with patch.object(client, "assets", side_effect=[[], [asset]]), \
             patch.object(client, "request", side_effect=upload.UploadError("lost response")) as request, \
             patch("workers.upload.time.sleep"):
            self.assertEqual(client.ensure_asset(1, Path("unused"), "a", 0, 1, "expected"), asset)
            self.assertEqual(request.call_count, 1)

    def test_executor_retry_never_reruns_training(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "job.json").write_text('{"id": "job"}')
            (base / "started").touch()
            with patch("workers.executor.execute") as execute, patch("workers.executor.stop_and_capture") as stop, \
                 patch("workers.executor.publish", return_value={"uploaded": True}):
                self.assertEqual(executor.main(base), 0)
                execute.assert_not_called()
                stop.assert_called_once_with(base, "scout-job")
            self.assertIn("interrupted", read_json(base / "result.json")["failure"])


if __name__ == "__main__":
    unittest.main()
