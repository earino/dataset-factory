"""Validation tests for the hf_publish job type.

The point of validating before provisioning is that a mistake found on a paid worker costs a
worker; the same class of mistake was found that way once already (a job that died without a
report). So these tests assert the refusals happen at plan time:

* a missing Hugging Face credential is refused before anything is provisioned;
* a malformed spec is refused, naming what is missing;
* it needs no container, so no argv and no image are required;
* the spec's digests are what the worker verifies against, so they must be present.
"""
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from factory import worker
from factory.common import FactoryError

POLICY = json.loads((Path(__file__).resolve().parent / "policy.ci.json").read_text())


def hf_job(**overrides):
    job = {
        "id": "austin-hf-test", "candidate": "austin-911-response",
        "server_type": "cpx32", "location": "hel1", "cpus": 2, "memory_mb": 4096,
        "timeout_minutes": 30, "lifetime_minutes": 45, "max_disk_mb": 4096,
        "max_artifact_mb": 8,
        "hf_publish": {
            "repo": "earino/austin-911-response", "revision": "main",
            "source_repo": "earino/austin-911-response",
            "assets": [{"asset_id": 1, "dest": "train.csv", "target": "data/train.csv",
                        "size": 10, "sha256": "a" * 64}],
        },
    }
    job.update(overrides)
    return job


class HfPublishValidationTests(unittest.TestCase):
    def test_a_valid_hf_publish_job_needs_no_argv_or_image(self):
        with patch.object(worker, "credential_status", return_value={"ready": True}):
            result = worker.validate(hf_job(), POLICY)
        self.assertIn("reservation_eur", result)

    def test_a_missing_hugging_face_credential_is_refused_before_provisioning(self):
        """Both credentials are needed: one to read the release, one to write the Hub."""
        def credentials(name):
            return {"ready": name == "FACTORY_PUBLISH_TOKEN"}

        with patch.object(worker, "credential_status", side_effect=credentials):
            with self.assertRaises(FactoryError) as raised:
                worker.validate(hf_job(), POLICY)
        self.assertIn("FACTORY_HF_WRITE_TOKEN", str(raised.exception))

    def test_a_missing_github_publish_credential_is_refused_too(self):
        with patch.object(worker, "credential_status", return_value={"ready": False}):
            with self.assertRaises(FactoryError) as raised:
                worker.validate(hf_job(), POLICY)
        self.assertIn("FACTORY_PUBLISH_TOKEN", str(raised.exception))

    def test_the_inference_credential_is_never_the_publish_credential(self):
        """A ready inference credential must not satisfy the publishing requirement."""
        def only_inference(name):
            return {"ready": name == "HF_TOKEN"}

        with patch.object(worker, "credential_status", side_effect=only_inference):
            with self.assertRaises(FactoryError):
                worker.validate(hf_job(), POLICY)

    def test_a_spec_missing_a_required_key_names_it(self):
        job = hf_job()
        del job["hf_publish"]["revision"]
        with patch.object(worker, "credential_status", return_value={"ready": True}):
            with self.assertRaises(FactoryError) as raised:
                worker.validate(job, POLICY)
        self.assertIn("revision", str(raised.exception))

    def test_an_asset_entry_missing_its_digest_is_refused(self):
        job = hf_job()
        del job["hf_publish"]["assets"][0]["sha256"]
        with patch.object(worker, "credential_status", return_value={"ready": True}):
            with self.assertRaises(FactoryError) as raised:
                worker.validate(job, POLICY)
        self.assertIn("sha256", str(raised.exception))

    def test_an_empty_asset_list_is_refused(self):
        job = hf_job()
        job["hf_publish"]["assets"] = []
        with patch.object(worker, "credential_status", return_value={"ready": True}):
            with self.assertRaises(FactoryError):
                worker.validate(job, POLICY)

    def test_a_job_outside_the_allowed_location_is_refused(self):
        with patch.object(worker, "credential_status", return_value={"ready": True}):
            with self.assertRaises(FactoryError):
                worker.validate(hf_job(location="fsn1"), POLICY)


if __name__ == "__main__":
    unittest.main()
