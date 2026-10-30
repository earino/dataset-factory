"""Offline test for the tie-aware weighted AUC shared by the ipo-tm diag.

diag.py (candidates/ipo-trademark-registration-outcome/diag/diag.py) recomputes
the construction references and the paired bootstrap intervals with a
numpy group-form AUC:

    U = sum over tie groups of pos_g * (neg ranked strictly below + 0.5 * tied neg)

The coordinator has no numpy, so this test exercises that arithmetic through a
pure-Python mirror of the same formula (identical group walk, identical
weighting) and checks it against score.py's own rank-sum midrank AUC - the
implementation that produced the recorded reference figures - on tie-heavy
synthetic data. The numpy transcription itself (bincount weights, argsort
groups) is guarded on the worker instead: diag.py refuses to exit 0 unless
every recomputed reference matches the recorded ipo-tm-004 figures within
tolerance on the real 97,274 eval rows.

score.py is loaded with exec(compile(...)) rather than an import so no
__pycache__ lands in the candidate's source directory.
"""
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCORE = ROOT / "candidates" / "ipo-trademark-registration-outcome" / "source" / "score.py"

ipo_score = {"__name__": "ipo_score_module", "__file__": str(SCORE)}
exec(compile(SCORE.read_bytes(), str(SCORE), "exec"), ipo_score)


def group_weighted_auc(labels, scores, w_pos, w_neg):
    """Pure-Python mirror of diag.py's numpy auc_midrank, same formula."""
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    total_pos = sum(w_pos)
    total_neg = sum(w_neg)
    if not total_pos or not total_neg:
        return None
    cum_neg = 0
    u = 0.0
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        pos_in = sum(w_pos[k] for k in order[i:j + 1])
        neg_in = sum(w_neg[k] for k in order[i:j + 1])
        if pos_in:
            u += pos_in * (cum_neg + 0.5 * neg_in)
        cum_neg += neg_in
        i = j + 1
    return u / (total_pos * total_neg)


class TestResamplerAlignment(unittest.TestCase):
    """The diag bootstrap must pair each drawn row with ITS OWN label.

    The first implementation of diag.py's paired_row_bootstrap built resample
    weights with ``np.bincount(idx, weights=y)``: bincount pairs weights with
    the DRAW POSITIONS, so the label of row k was added to the weight of the
    drawn row idx[k] - scrambling label-row alignment and collapsing every AUC
    difference to noise (mean ~1e-4 where the observed gap was ~5.7e-2). The
    numpy code cannot import on this host (no numpy), so this test mirrors both
    the fixed and the defective constructions in pure Python and shows the
    fixed one preserves the observed gap while the defective one destroys it.
    """

    def _mirror(self, labels, scores_a, scores_b, resamples, buggy):
        """Pure-Python mirror of diag.py's resampler; buggy=True reproduces the defect."""
        n = len(labels)
        rng = random.Random(31)
        differences = []
        for _ in range(resamples):
            idx = [rng.randrange(n) for _ in range(n)]
            w_pos = [0.0] * n
            w_neg = [0.0] * n
            for k, i in enumerate(idx):
                if buggy:
                    # the defect: the LABEL OF THE DRAW POSITION goes to the drawn row
                    label = labels[k]
                else:
                    # the fix: the drawn row carries its own label
                    label = labels[i]
                if label:
                    w_pos[i] += 1
                else:
                    w_neg[i] += 1
            auc_a = group_weighted_auc(labels, scores_a, w_pos, w_neg)
            auc_b = group_weighted_auc(labels, scores_b, w_pos, w_neg)
            if auc_a is not None and auc_b is not None:
                differences.append(auc_a - auc_b)
        return sum(differences) / len(differences)

    def test_bootstrap_weights_align_labels_with_drawn_rows(self):
        rng = random.Random(5)
        n = 400
        labels = [rng.randrange(2) for _ in range(n)]
        # a genuine gap: scores_a separates the classes, scores_b is noise
        scores_a = [0.2 + 0.6 * y + 0.05 * rng.random() for y in labels]
        scores_b = [rng.random() for _ in range(n)]
        observed = (ipo_score["auc"](labels, scores_a)
                    - ipo_score["auc"](labels, scores_b))
        self.assertGreater(observed, 0.2, "fixture must carry a real gap")
        fixed_mean = self._mirror(labels, scores_a, scores_b, 60, buggy=False)
        buggy_mean = self._mirror(labels, scores_a, scores_b, 60, buggy=True)
        # the fixed resampler centers on the observed gap (bootstrap bias is small)
        self.assertLess(abs(fixed_mean - observed), 0.05,
                        f"aligned weights must preserve the gap: {fixed_mean} vs {observed}")
        # the defective construction destroys the signal (mean collapses toward
        # zero while the gap is large) - this is the signature diag-001 showed
        # on the real 97k rows (bootstrap means ~1e-4 against observed ~5.7e-2),
        # recorded here so the discrimination is demonstrated, not asserted away
        self.assertGreater(abs(buggy_mean - observed), 0.2,
                           f"the defective mirror must collapse the gap: "
                           f"{buggy_mean} vs observed {observed}")


class TestTieAwareWeightedAuc(unittest.TestCase):
    def test_unit_weights_equal_score_py_midrank_auc_on_tie_heavy_data(self):
        rng = random.Random(7)
        for trial in range(20):
            n = 200
            labels = [rng.randrange(2) for _ in range(n)]
            # heavy ties: a coarse score grid
            scores = [rng.randrange(4) * 0.25 for _ in range(n)]
            if len(set(labels)) < 2 or len(set(scores)) < 2:
                continue
            unit_pos = [float(y) for y in labels]
            unit_neg = [1.0 - y for y in labels]
            self.assertAlmostEqual(
                group_weighted_auc(labels, scores, unit_pos, unit_neg),
                ipo_score["auc"](labels, scores),
                places=12,
                msg=f"trial {trial}: weighted(1) != midrank on tie-heavy data")

    def test_weighted_auc_matches_score_py_weighted_form(self):
        """Same weighted comparison through both group walks must agree."""
        rng = random.Random(11)
        labels = [rng.randrange(2) for _ in range(150)]
        scores_a = [rng.randrange(5) * 0.2 for _ in range(150)]
        scores_b = [rng.randrange(5) * 0.2 for _ in range(150)]
        w_pos = [float(rng.randrange(3)) for _ in range(150)]
        w_neg = [float(rng.randrange(3)) for _ in range(150)]
        # score.py's weighted_auc takes its own precompute structure
        pre_a = ipo_score["precompute"](scores_a)
        pre_b = ipo_score["precompute"](scores_b)
        count_pos, count_neg = w_pos, w_neg
        self.assertAlmostEqual(
            ipo_score["weighted_auc"](scores_a, *pre_a, count_pos, count_neg),
            group_weighted_auc(labels, scores_a, w_pos, w_neg),
            places=12)
        self.assertAlmostEqual(
            ipo_score["weighted_auc"](scores_b, *pre_b, count_pos, count_neg),
            group_weighted_auc(labels, scores_b, w_pos, w_neg),
            places=12)

    def test_missing_class_returns_none(self):
        self.assertIsNone(group_weighted_auc([1, 1], [0.3, 0.6], [1.0, 1.0], [0.0, 0.0]))
        self.assertIsNone(ipo_score["auc"]([1, 1], [0.3, 0.6]))


if __name__ == "__main__":
    unittest.main()
