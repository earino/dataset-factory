"""The persistence calibration's metric must be right, because its output is a recorded finding."""

import importlib.util
import unittest
from pathlib import Path

MODULE = (Path(__file__).resolve().parent.parent / "candidates" / "noaa-tide-flooding"
          / "persistence_baseline.py")


def load():
    spec = importlib.util.spec_from_file_location("persistence_baseline", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RankAucTest(unittest.TestCase):
    def setUp(self):
        self.module = load()

    def test_perfect_separation_is_one(self):
        self.assertEqual(1.0, self.module.auc([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]))

    def test_reversed_separation_is_zero(self):
        self.assertEqual(0.0, self.module.auc([0, 0, 1, 1], [0.9, 0.8, 0.2, 0.1]))

    def test_uninformative_scores_are_half(self):
        """Every score identical: no ranking information, so 0.5 - not 1.0 from tie handling."""
        self.assertEqual(0.5, self.module.auc([0, 1, 0, 1], [0.5, 0.5, 0.5, 0.5]))

    def test_one_class_returns_none_rather_than_zero(self):
        """A column with no negatives has no ROC; reporting 0.0 would look like a real result."""
        self.assertIsNone(self.module.auc([1, 1, 1], [0.1, 0.2, 0.3]))

    def test_ties_are_averaged(self):
        # One positive ties with one negative; the other pair separates. 3 of 4 pairs ordered.
        self.assertEqual(0.75, self.module.auc([0, 0, 1, 1], [0.2, 0.5, 0.5, 0.9]))

    def test_rounding_helper_keeps_none(self):
        self.assertIsNone(self.module.r2(None))
        self.assertEqual(0.5, self.module.r2(0.49999))


if __name__ == "__main__":
    unittest.main()
