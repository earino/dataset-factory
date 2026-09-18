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

    The Hermes-visible path is a symlink to this repository's copy, so there is exactly one
    source of truth and no drift. Hermes resolves the link and loads the skill (verified by
    a fresh session), but logs a cosmetic security warning because the resolved file sits
    outside `~/.hermes/skills`. A duplicate real directory would silence the warning at the
    cost of two copies that can diverge, so the link is deliberate.
    """

    HERMES_SKILL_LINK = Path("/opt/data/skills/research/dataset-qualification")

    def test_the_gate_is_versioned_in_this_repository(self):
        self.assertTrue((SKILLS / "dataset-qualification" / "SKILL.md").is_file())
        self.assertTrue((SKILLS / "dataset-qualification" / "scripts"
                         / "qualify_dataset.py").is_file())

    def test_the_hermes_visible_path_resolves_to_the_repository_copy(self):
        link = self.HERMES_SKILL_LINK
        if not link.exists():
            self.skipTest("Hermes skill directory is not present on this machine")
        self.assertTrue(link.is_symlink(), f"{link} should be a symlink, not a copy")
        self.assertEqual(link.resolve(),
                         (SKILLS / "dataset-qualification").resolve())

    def test_the_two_skill_copies_cannot_diverge_because_there_is_only_one(self):
        link = self.HERMES_SKILL_LINK
        if not link.exists():
            self.skipTest("Hermes skill directory is not present on this machine")
        self.assertEqual(link.resolve(), (SKILLS / "dataset-qualification").resolve())


if __name__ == "__main__":
    unittest.main()
