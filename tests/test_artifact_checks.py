"""Tests for the mechanical checks the discovery and release skills rely on.

Both checks exist so that a *claim* is refused when its evidence is absent - the same principle
as the qualification gate. So the tests are mostly negative: a record that claims a stage
without the evidence, a package whose hashes no longer match, a package that implies
publication without stating it.

Loaded with `exec(compile(...))` so no bytecode cache lands next to a bundled script.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_CHECK = ROOT / "scripts" / "check-candidate.py"
PACKAGE_CHECK = ROOT / "scripts" / "check-package.py"
REAL_PACKAGE = ROOT / "release" / "austin-911-response"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


candidate_check = load("check_candidate_script", CANDIDATE_CHECK)
package_check = load("check_package_script", PACKAGE_CHECK)


def good_record(**overrides):
    record = {
        "id": "example", "status": "investigating", "domain": "civic",
        "prediction_question": "Will X happen?", "prediction_time": "At dispatch",
        "target_definition": "Late arrival beyond T",
        "sources": [{"name": "Example open data", "url": "https://example.org/data",
                     "license": "CC0"}],
        "jurisdiction": {"country": "NZ", "region": "Oceania", "publisher": "Example"},
        "license_evidence": [{"quote": "Released under CC0", "url": "https://example.org/terms"}],
        "construction_script": None, "split_strategy": None, "measurements": {},
        "jobs": [], "artifacts": [], "rejection_reason": None, "review": None,
        "next_action": "Probe the source",
    }
    record.update(overrides)
    return record


class CandidateCheckTests(unittest.TestCase):
    def test_a_minimal_investigating_record_passes(self):
        missing, _ = candidate_check.check_record(good_record())
        self.assertEqual([], missing)

    def test_a_record_without_a_jurisdiction_is_refused(self):
        """Geography is a required field, not decoration.

        The bench was 10 US sources to 1 Australian and 0 of 6 live candidates non-US; a field
        that is optional is a field that stays empty. This fails on the pre-fix checker, which
        had no jurisdiction in IDENTITY_FIELDS and returned no missing fields.
        """
        record = good_record()
        del record["jurisdiction"]
        missing, _ = candidate_check.check_record(record)
        self.assertTrue(any("jurisdiction" in item for item in missing), missing)

    def test_a_status_outside_the_vocabulary_is_a_note_not_a_failure(self):
        missing, notes = candidate_check.check_record(good_record(status="thinking-about-it"))
        self.assertEqual([], missing)
        self.assertTrue(any("outside the documented vocabulary" in note for note in notes))

    def test_a_packaged_claim_without_artifacts_is_refused(self):
        missing, _ = candidate_check.check_record(good_record(status="packaged"))
        joined = " ".join(missing)
        self.assertIn("construction_script", joined)
        self.assertIn("split_strategy", joined)
        self.assertIn("measurements", joined)
        self.assertIn("qualification", joined)
        self.assertIn("artifacts", joined)

    def test_a_qualified_claim_without_a_qualification_record_is_refused(self):
        missing, _ = candidate_check.check_record(good_record(
            status="qualified", construction_script="candidates/example/source/build.py",
            split_strategy={"train": "2024"}, measurements={"rows": 10}))
        self.assertTrue(any("qualification" in problem for problem in missing))

    def test_an_empty_identity_field_is_refused(self):
        missing, _ = candidate_check.check_record(good_record(prediction_question=None))
        self.assertTrue(any(problem.startswith("prediction_question") for problem in missing))

    def test_a_licence_name_is_not_evidence(self):
        missing, _ = candidate_check.check_record(good_record(license_evidence=["MIT"]))
        self.assertTrue(any("is not evidence" in problem for problem in missing))

    def test_a_substantive_evidence_sentence_is_accepted(self):
        missing, _ = candidate_check.check_record(good_record(license_evidence=[
            "Socrata catalog reports license = 'Public Domain' "
            "(api.us.socrata.com catalog v1, queried 2026-09-18)."]))
        self.assertFalse(any("is not evidence" in problem for problem in missing))

    def test_a_terminal_status_requires_a_reason(self):
        missing, _ = candidate_check.check_record(good_record(status="dropped"))
        self.assertTrue(any("terminal" in problem for problem in missing))
        missing, _ = candidate_check.check_record(
            good_record(status="dropped", rejection_reason="No licence for redistribution"))
        self.assertFalse(any("terminal" in problem for problem in missing))

    def test_a_ready_candidate_without_a_novelty_check_is_refused(self):
        missing, _ = candidate_check.check_record(good_record(
            status="ready", construction_script="build.py", split_strategy={"train": "2024"},
            measurements={"rows": 10}))
        self.assertTrue(any("novelty_check: absent" in problem for problem in missing))

    def test_a_mirror_verdict_is_refused(self):
        missing, _ = candidate_check.check_record(good_record(
            status="ready", construction_script="build.py", split_strategy={"train": "2024"},
            measurements={"rows": 10},
            novelty_check={"verdict": "mirror", "ours": "a copy of an existing dataset"}))
        self.assertTrue(any("must not be published" in problem for problem in missing))

    def test_a_verdict_without_what_is_ours_is_refused(self):
        missing, _ = candidate_check.check_record(good_record(
            status="ready", construction_script="build.py", split_strategy={"train": "2024"},
            measurements={"rows": 10}, novelty_check={"verdict": "differentiated"}))
        self.assertTrue(any("novelty_check.ours" in problem for problem in missing))

    def test_a_differentiated_verdict_passes(self):
        missing, _ = candidate_check.check_record(good_record(
            status="ready", construction_script="build.py", split_strategy={"train": "2024"},
            measurements={"rows": 10},
            novelty_check={"verdict": "differentiated", "ours": "a leak-free task",
                           "theirs": "the publisher ships raw data only"}))
        self.assertFalse(any("novelty" in problem for problem in missing))

    def test_an_investigating_candidate_does_not_need_a_novelty_check_yet(self):
        missing, _ = candidate_check.check_record(good_record())
        self.assertFalse(any("novelty" in problem for problem in missing))

    def test_a_release_without_an_openable_url_is_refused(self):
        missing, _ = candidate_check.check_record(good_record(
            status="packaged", construction_script="build.py", split_strategy={"train": "2024"},
            measurements={"rows": 10}, qualification={"result": "PASSED"},
            artifacts=[{"name": "release"}]))
        self.assertTrue(any("openable" in problem or "url/tag/repo" in problem
                            for problem in missing))

    def test_every_committed_candidate_record_passes(self):
        """The repository's own records must satisfy the check CI runs."""
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = candidate_check.main(["--all", "--root", str(ROOT)])
        self.assertEqual(0, code, buffer.getvalue())


class PackageCheckTests(unittest.TestCase):
    def _build(self, root: Path, *, published=False, note=True, sums=None, extra_file=None):
        for name in package_check.REQUIRED_FILES:
            if name in ("MANIFEST.json", "SHA256SUMS"):
                continue
            (root / name).write_text(f"# {name}\n")
        for name in package_check.REQUIRED_DIRS:
            (root / name).mkdir()
            (root / name / "placeholder.txt").write_text("x\n")
        if extra_file:
            (root / extra_file).write_text("extra\n")

        (root / "LICENSE-MIT.txt").write_text("MIT text\n")
        (root / "LICENSE-CC0-1.0.txt").write_text("CC0 text\n")
        fixture = ROOT/'skills/dataset-qualification/fixtures/corrected'
        gate = load('package_fixture_gate',ROOT/'skills/dataset-qualification/scripts/qualify_dataset.py')
        with tempfile.TemporaryDirectory() as source:
            dataset = Path(source)/'artifact'
            shutil.copytree(fixture,dataset)
            qualification = gate.qualify(dataset,record_battery=True).as_dict()
            shutil.copytree(dataset,root,dirs_exist_ok=True)
        self.assertTrue(qualification['ok'],qualification['failed_checks'])
        (root/'qualification.json').write_text(json.dumps(qualification))
        from factory.claim_contract import compute, render
        claim={'id':'eval-population','kind':'population','split':'eval'}
        (root/'CLAIMS.json').write_text(json.dumps({'version':1,'claims':[claim]}))
        facts=compute(root,qualification=root/'qualification.json')
        (root/'claims-facts.json').write_text(json.dumps(facts))
        (root/'README.md').write_text('<!-- FACTORY-CLAIM eval-population -->\n'+render(claim,facts)+
                                    '\n<!-- /FACTORY-CLAIM -->\n')
        files = {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()
        }
        assets = {entry['file']: {'asset_name':entry['file'].replace('/','-'),
                  'sha256':entry['sha256'],'bytes':entry['bytes']}
                  for key,entry in qualification['artifact'].items()
                  if key in ('train','eval','holdout','meta.json','quality.json')}
        expected = {v['asset_name']: {'sha256': v['sha256'], 'bytes': v['bytes']} for v in assets.values()}
        layout = {v['asset_name']: k for k, v in assets.items()}
        (root/'get_dataset.py').write_text(f'TAG = "v1"\nEXPECTED = {expected!r}\nLAYOUT = {layout!r}\n')
        files['get_dataset.py'] = hashlib.sha256((root/'get_dataset.py').read_bytes()).hexdigest()
        manifest = {
            "dataset": "example", "release_tag": "v1",
            "artifact_version": qualification["artifact"]["artifact_version"]["digest"],
            "qualification": {"result": "PASSED"}, "published": published,
            "package_files": files, "assets": assets,
            "files": {k: {'sha256': v['sha256'], 'bytes': v['bytes']} for k, v in assets.items()},
            "licenses": {
                "code": {"spdx": "MIT", "file": "LICENSE-MIT.txt"},
                "data_compilation": {"spdx": "CC0-1.0", "file": "LICENSE-CC0-1.0.txt"},
                "source_data": {"spdx": "LicenseRef-Public-Domain",
                                "status": "Public Domain, preserved"},
            },
        }
        if note:
            manifest["publication_note"] = "Awaiting review."
        (root / "MANIFEST.json").write_text(json.dumps(manifest, indent=1))
        (root / "SHA256SUMS").write_text(
            "".join(f"{digest}  {name}\n" for name, digest in (sums or
                    {name:entry["sha256"] for name,entry in assets.items()}).items()))
        return root

    def test_a_consistent_package_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(Path(tmp))
            problems, _ = package_check.check_package(root)
            self.assertEqual([], problems)

    def test_manifest_claim_cannot_replace_a_passing_battery_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self._build(Path(tmp))
            path=root/'qualification.json'
            value=json.loads(path.read_text()); value['ok']=False
            path.write_text(json.dumps(value))
            manifest=json.loads((root/'MANIFEST.json').read_text())
            manifest['published']=True
            manifest['package_files']['qualification.json']=hashlib.sha256(path.read_bytes()).hexdigest()
            (root/'MANIFEST.json').write_text(json.dumps(manifest))
            problems,_=package_check.check_package(root)
            self.assertTrue(any('passing gate 1.6' in p for p in problems),problems)

    def test_a_tampered_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(Path(tmp))
            (root / "README.md").write_text("# README.md\nchanged\n")
            problems, _ = package_check.check_package(root)
            self.assertTrue(any("README.md" in problem and "on disk" in problem
                                for problem in problems))

    def test_a_missing_document_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(Path(tmp))
            (root / "VERIFICATION.md").unlink()
            problems, _ = package_check.check_package(root)
            self.assertTrue(any("VERIFICATION.md: missing" in problem for problem in problems))

    def test_unpublished_without_a_note_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(Path(tmp), published=False, note=False)
            problems, _ = package_check.check_package(root)
            self.assertTrue(any("publication_note" in problem for problem in problems))

    def test_sums_disagreeing_with_the_manifest_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(Path(tmp), sums={"public/train.csv": "c" * 64})
            problems, _ = package_check.check_package(root)
            self.assertTrue(any("disagrees with the manifest" in problem for problem in problems))

    def test_a_file_outside_the_manifest_is_noted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(Path(tmp))
            (root / "stray.txt").write_text("stray\n")
            problems, notes = package_check.check_package(root)
            self.assertFalse(any("stray.txt" in problem for problem in problems))
            self.assertTrue(any("stray.txt" in note for note in notes))

    def test_a_release_without_declared_terms_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(Path(tmp))
            manifest = json.loads((root / "MANIFEST.json").read_text())
            del manifest["licenses"]
            (root / "MANIFEST.json").write_text(json.dumps(manifest))
            problems, _ = package_check.check_package(root)
            self.assertTrue(any("no 'licenses' block" in problem for problem in problems))

    def test_a_named_licence_file_must_be_in_the_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(Path(tmp))
            (root / "LICENSE-CC0-1.0.txt").unlink()
            problems, _ = package_check.check_package(root)
            self.assertTrue(any("LICENSE-CC0-1.0.txt" in problem for problem in problems))

    def test_publishing_with_undeclared_terms_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(Path(tmp), published=True)
            manifest = json.loads((root / "MANIFEST.json").read_text())
            manifest["licenses"] = {"status": "UNDECLARED - missing declaration"}
            (root / "MANIFEST.json").write_text(json.dumps(manifest))
            problems, _ = package_check.check_package(root)
            self.assertTrue(any("UNDECLARED" in problem for problem in problems))

    def test_the_committed_package_passes(self):
        problems, _ = package_check.check_package(REAL_PACKAGE, external_assets=True)
        self.assertEqual([], problems)


if __name__ == "__main__":
    unittest.main()
