"""Repository hygiene guards.

The defects these catch are invisible on a host that sets PYTHONDONTWRITEBYTECODE=1 and are
harmful on one that does not:

* A test that imports a candidate's worker source by path leaves `__pycache__` inside the
  job directory, which makes `factory.worker.source_bundle` refuse the directory and
  contaminates the bundle that would be shipped to a worker.
* The same applies to any file the source directory must not contain.

Run the suite with bytecode writing enabled to exercise this: `env -u
PYTHONDONTWRITEBYTECODE python3 -m unittest discover -s tests`.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "candidates"
SKILLS = ROOT / "skills"
ALLOWED_SUFFIXES = (".py", ".sh", ".json", ".txt", ".toml", ".yaml", ".yml", ".md")
BUNDLE_LIMIT = 2 * 1024 * 1024


def job_directories() -> list[Path]:
    """Directories that hold a worker job, identified by the presence of job.json."""
    return sorted({path.parent for path in CANDIDATES.rglob("job.json")})


class NoBytecodeInArtefacts(unittest.TestCase):
    def test_no_caches_under_candidates(self):
        found = [str(p) for p in CANDIDATES.rglob("__pycache__")] + \
                [str(p) for p in CANDIDATES.rglob("*.pyc")]
        self.assertEqual(found, [], "test imports left caches inside candidate directories")

    def test_no_caches_under_skills(self):
        found = [str(p) for p in SKILLS.rglob("__pycache__")] + \
                [str(p) for p in SKILLS.rglob("*.pyc")]
        self.assertEqual(found, [], "test imports left caches inside the skill directory")


class JobBundles(unittest.TestCase):
    def test_there_is_at_least_one_prepared_job(self):
        self.assertTrue(job_directories(), "no candidate has a prepared worker job")

    def test_every_job_directory_satisfies_the_worker_bundle_rules(self):
        for directory in job_directories():
            with self.subTest(job=directory.relative_to(ROOT)):
                job = directory / "job.json"
                self.assertTrue(job.is_file())
                total = 0
                for path in sorted(directory.rglob("*")):
                    self.assertFalse(path.is_symlink(), f"symlink not allowed: {path}")
                    if path == job or path.is_dir():
                        continue
                    relative = path.relative_to(directory)
                    self.assertFalse(any(part.startswith(".") or part == "__pycache__"
                                         for part in relative.parts),
                                     f"hidden file or cache not allowed: {relative}")
                    self.assertIn(path.suffix, ALLOWED_SUFFIXES,
                                  f"unexpected source file: {relative}")
                    total += path.stat().st_size
                self.assertLessEqual(total, BUNDLE_LIMIT,
                                     f"{directory} exceeds the worker bundle cap")

    def test_job_json_is_parseable_and_targets_a_configured_type(self):
        policy_path = ROOT / "config" / "local.json"
        if not policy_path.is_file():
            self.skipTest("local policy is not present on this machine")
        policy = json.loads(policy_path.read_text())
        for directory in job_directories():
            job = json.loads((directory / "job.json").read_text())
            if job["server_type"] in ("configure-me", ""):
                continue  # the example job is intentionally unconfigured
            with self.subTest(job=job["id"]):
                self.assertIn(job["server_type"], policy.get("server_types", {}))
                self.assertIn(job["location"], policy.get("allowed_locations", []))
                self.assertLessEqual(job["timeout_minutes"], job["lifetime_minutes"])

    def test_job_ids_are_unique(self):
        ids = [json.loads((d / "job.json").read_text())["id"] for d in job_directories()]
        self.assertEqual(len(ids), len(set(ids)), f"duplicate job ids: {ids}")


class SkillExposure(unittest.TestCase):
    """The qualification gate must be versioned here AND loadable by Hermes.

    Hermes exposes it through `skills.external_dirs`, which is the supported way to register a
    skills directory outside the profile. Hermes then treats it as a trusted directory, so
    loading the skill raises no security warning - unlike the symlink into `~/.hermes/skills`
    that this replaced.
    """

    HERMES_HOME = Path("/opt/data")
    EXPECTED_ENTRY = "dataset-factory/skills"
    RETIRED_SYMLINK = Path("/opt/data/skills/research/dataset-qualification")

    def test_the_gate_is_versioned_in_this_repository(self):
        self.assertTrue((SKILLS / "dataset-qualification" / "SKILL.md").is_file())
        self.assertTrue((SKILLS / "dataset-qualification" / "scripts"
                         / "qualify_dataset.py").is_file())
        self.assertTrue((SKILLS / "dataset-qualification" / "fixtures"
                         / "build_fixtures.py").is_file())

    def test_hermes_registers_the_repository_skills_directory(self):
        config = self.HERMES_HOME / "config.yaml"
        if not config.is_file():
            self.skipTest("no Hermes config on this machine")
        text = config.read_text()
        self.assertIn("external_dirs", text, "skills.external_dirs is not configured")
        block = text.split("external_dirs", 1)[1].splitlines()[0]
        self.assertIn(self.EXPECTED_ENTRY, block,
                      f"skills.external_dirs does not contain {self.EXPECTED_ENTRY}")

    def test_the_retired_symlink_is_gone(self):
        if not self.RETIRED_SYMLINK.parent.exists():
            self.skipTest("Hermes skills directory is not present on this machine")
        self.assertFalse(self.RETIRED_SYMLINK.is_symlink(),
                         "the symlinked exposure was replaced by skills.external_dirs")


if __name__ == "__main__":
    unittest.main()
