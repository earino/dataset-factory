"""A malformed split must be reported, not crash the gate.

While building the PriceCatcher artifact a duplicate column header produced two value lists for one
name, the lengths stopped aligning, and the gate died with `ValueError: labels and scores must align
and be non-empty` from deep inside the leakage scorer. The cause was obvious only after reading the
traceback; the report said nothing. These tests pin the named failure instead.
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GATE = ROOT / "skills" / "dataset-qualification" / "scripts" / "qualify_dataset.py"
spec = importlib.util.spec_from_file_location("qualify_dataset_unscorable", GATE)
gate = importlib.util.module_from_spec(spec)
sys.modules["qualify_dataset_unscorable"] = gate
# Compile from bytes so no bytecode cache is written inside the skill directory,
# matching test_qualification_gate.py: a normal exec_module writes
# __pycache__/qualify_dataset.cpython-*.pyc under skills/, which fails the
# repo-hygiene gate. CI does not set PYTHONDONTWRITEBYTECODE, so the writing
# path is what the runner sees.
exec(compile(GATE.read_bytes(), str(GATE), "exec"), gate.__dict__)


def build(directory: Path, header: str, rows: list[str]) -> Path:
    for split, name in (("train", "train.csv"), ("eval", "eval.csv")):
        (directory / "public").mkdir(exist_ok=True)
        (directory / "public" / name).write_text(header + "\n" + "\n".join(rows) + "\n")
        (directory / "private").mkdir(exist_ok=True)
        (directory / "private" / "holdout.csv").write_text(header + "\n" + "\n".join(rows) + "\n")
    quality = {
        "name": "fixture", "target": "y", "positive_label": 1,
        "splits": {"train": "public/train.csv", "eval": "public/eval.csv",
                   "holdout": "private/holdout.csv"},
        "features": ["x"], "features_documented_at": "prediction_time",
        "time_column": "t", "event_key_column": "k", "id_columns": ["id"],
    }
    (directory / "quality.json").write_text(json.dumps(quality))
    return directory


class UnscorableColumnTests(unittest.TestCase):
    def test_a_duplicate_header_is_reported_not_raised(self):
        tmp = Path(tempfile.mkdtemp(prefix="gate-dup-"))
        build(tmp, "id,t,x,x,y", ["1,2024-01-01,1,2,3,1", "2,2024-02-01,3,4,5,0"])
        report = gate.qualify(tmp)          # must not raise
        checks = {item["check"]: item for item in report.results}
        self.assertIn("leakage.every_column_could_be_scored", checks)
        self.assertFalse(checks["leakage.every_column_could_be_scored"]["ok"])
        self.assertIn("x", checks["leakage.every_column_could_be_scored"]["detail"])

    def test_a_clean_split_still_scores(self):
        tmp = Path(tempfile.mkdtemp(prefix="gate-clean-"))
        build(tmp, "id,t,x,y", ["1,2024-01-01,1,1", "2,2024-02-01,3,0"])
        report = gate.qualify(tmp)
        checks = {item["check"]: item for item in report.results}
        self.assertTrue(checks["leakage.every_column_could_be_scored"]["ok"], checks["leakage.every_column_could_be_scored"])


if __name__ == "__main__":
    unittest.main()
