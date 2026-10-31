"""Offline tests for the acnc diag: the charity-cluster resampler and the
identity rate-table key type.

diag.py (candidates/acnc-charity-ais-deadline-compliance/diag/diag.py) computes
the dependence-aware model-vs-persistence interval by resampling CHARITIES
(abn) rather than rows, because eval rows of this panel cluster by charity - a
declared property (a charity may appear in multiple target years).

The coordinator has no numpy, so this test mirrors the resampler's expansion
arithmetic in pure Python (identical draw protocol: random.Random(31),
n_c draws of n_c charities per resample) and checks three things:

  * whole-charity assignment: a drawn charity increments ALL its rows, and
    every row of one charity carries the same count;
  * the analogous positional defect (counts built from DRAW POSITIONS, the
    same defect class that collapsed the ipo diag-001 row resampler to noise)
    produces a different counts vector on the same draws, so the guard bites;
  * on a perfectly separated charity panel the mirrored cluster bootstrap
    preserves the observed gap (interval [1, 1], mean 1) instead of collapsing
    it to noise.

The numpy transcription itself is guarded on the worker instead: diag.py
refuses to exit 0 unless the recomputed references match the recorded acnc-002
figures and the momentum_vs_calendar canary reproduces job acnc-002's
recorded interval on the real 80,298 eval rows.

diag.py is loaded with exec(compile(...)) rather than an import so no
__pycache__ lands in the candidate's source directory.
"""
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIAG = ROOT / "candidates" / "acnc-charity-ais-deadline-compliance" / "diag" / "diag.py"
SEED = 31


def mirror_interval(differences):
    """Pure-Python mirror of diag._interval's percentile rule.

    diag.py is NOT loaded here: it imports numpy/pandas/sklearn, which the
    coordinator does not have. The numpy transcription is guarded on the
    worker instead - diag.py refuses to exit 0 unless the recomputed
    references match the recorded acnc-002 figures and the
    momentum_vs_calendar canary reproduces job acnc-002's recorded interval
    on the real eval rows.
    """
    differences = sorted(differences)
    if not differences:
        return {"resamples": 0, "ci95": None}
    low = differences[int(0.025 * len(differences))]
    high = differences[int(0.975 * len(differences)) - 1] if len(differences) > 1 \
        else differences[-1]
    return {"resamples": len(differences),
            "mean_difference": round(sum(differences) / len(differences), 6),
            "ci95": [round(low, 6), round(high, 6)],
            "interval_excludes_zero": bool(low > 0 or high < 0)}


def mirror_charity_counts(clusters, drawn):
    """Pure-Python mirror of the fixed expansion: counts[r] = times charity(r) drawn."""
    uniq = sorted(set(clusters))
    position = {c: i for i, c in enumerate(uniq)}
    rows_of = [[] for _ in uniq]
    for i, c in enumerate(clusters):
        rows_of[position[c]].append(i)
    counts = [0] * len(clusters)
    for d in drawn:
        for r in rows_of[d]:
            counts[r] += 1
    return counts, rows_of


def mirror_defective_counts(clusters, drawn):
    """The positional defect: bincount over DRAW POSITIONS, not drawn charities."""
    counts = [0] * len(clusters)
    for position in drawn:
        counts[position % len(clusters)] += 1
    return counts


def mirror_rate_table_second(keys, ys):
    """Pure-Python mirror of diag.rate_table_second.

    Keys are kept exactly as given (diag.py passes raw strings for single
    columns and tuples for compound keys), so the table's key type is whatever
    the caller used to build it - and the eval lookup must use the same type.
    """
    totals, positives = {}, {}
    for key, y in zip(keys, ys):
        totals[key] = totals.get(key, 0) + 1
        if y:
            positives[key] = positives.get(key, 0) + 1
    table = {key: positives.get(key, 0) / total for key, total in totals.items()}
    global_rate = (sum(ys) / len(ys)) if ys else 0.5
    return table, global_rate


def mirror_plain_auc_constant_guard(scores):
    """Mirror of diag.plain_auc's first check: a constant vector carries no
    ranking information, so the AUC is None and diag.py refuses to compare
    against it (exit 3 - the observed acnc-diag-001 failure)."""
    return len(set(scores)) == 1


def group_weighted_auc(labels, scores, w_pos, w_neg):
    """Pure-Python tie-aware weighted AUC (same formula as diag.auc_midrank)."""
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


class TestCharityClusterResampler(unittest.TestCase):
    PANEL = (["c0", "c0", "c1", "c1", "c1", "c2", "c2", "c3"],
             [1, 1, 0, 0, 0, 1, 1, 0])  # clusters, labels

    def _fixed_draws(self, n_charities, resamples=8):
        rng = random.Random(SEED)
        return [[rng.randrange(n_charities) for _ in range(n_charities)]
                for _ in range(resamples)]

    def test_whole_charity_assignment(self):
        clusters, _ = self.PANEL
        uniq = sorted(set(clusters))
        for drawn in self._fixed_draws(len(uniq)):
            counts, rows_of = mirror_charity_counts(clusters, drawn)
            for c_index, rows in enumerate(rows_of):
                per_charity = {counts[r] for r in rows}
                self.assertEqual(len(per_charity), 1,
                                 "rows of one charity carry different counts")
                self.assertEqual(per_charity.pop(), drawn.count(c_index),
                                 "charity count != times drawn")
            self.assertEqual(sum(counts), sum(len(rows_of[d]) for d in drawn))

    def test_positional_defect_produces_different_counts(self):
        """The guard bites: the defective construction differs on the same draws."""
        clusters, _ = self.PANEL
        uniq = sorted(set(clusters))
        differs = 0
        for drawn in self._fixed_draws(len(uniq)):
            fixed, _ = mirror_charity_counts(clusters, drawn)
            buggy = mirror_defective_counts(clusters, drawn)
            if fixed != buggy:
                differs += 1
        self.assertGreater(differs, 0,
                           "the positional defect never diverged; this test "
                           "no longer pins anything")

    def test_perfect_panel_preserves_the_gap(self):
        """Whole-charity resampling keeps a perfect panel's gap at 1.0."""
        clusters = [f"c{i}" for i in range(6)]
        labels = [0, 0, 0, 1, 1, 1]                  # label ordered with score_a
        scores_a = [float(i) for i in range(6)]     # ranks charities up
        scores_b = [float(5 - i) for i in range(6)]  # ranks charities down
        auc_a = group_weighted_auc(labels, scores_a, labels, [1 - y for y in labels])
        auc_b = group_weighted_auc(labels, scores_b, labels, [1 - y for y in labels])
        self.assertIsNotNone(auc_a)
        self.assertIsNotNone(auc_b)
        observed = auc_a - auc_b
        self.assertAlmostEqual(observed, 1.0)
        differences = []
        for drawn in self._fixed_draws(6, resamples=20):
            counts, _ = mirror_charity_counts(clusters, drawn)
            w_pos = [c * y for c, y in zip(counts, labels)]
            w_neg = [c * (1 - y) for c, y in zip(counts, labels)]
            auc_a = group_weighted_auc(labels, scores_a, w_pos, w_neg)
            auc_b = group_weighted_auc(labels, scores_b, w_pos, w_neg)
            if auc_a is not None and auc_b is not None:
                differences.append(auc_a - auc_b)
        self.assertTrue(differences)
        for difference in differences:
            self.assertAlmostEqual(difference, 1.0,
                                   msg="a resample lost the perfect separation")

    def test_interval_percentile_rule(self):
        """The mirrored percentile rule matches diag._interval's documented read."""
        result = mirror_interval([0.02, -0.01, 0.05, 0.0, 0.03, 0.04, -0.02, 0.01])
        self.assertEqual(result["resamples"], 8)
        self.assertEqual(result["ci95"], [-0.02, 0.04])
        self.assertAlmostEqual(result["mean_difference"], 0.015, places=6)
        self.assertFalse(result["interval_excludes_zero"])
        again = mirror_interval([0.02, -0.01, 0.05, 0.0, 0.03, 0.04, -0.02, 0.01])
        self.assertEqual(result, again)
        empty = mirror_interval([])
        self.assertEqual(empty, {"resamples": 0, "ci95": None})


class TestIdentityRateTableKeyType(unittest.TestCase):
    """Job acnc-diag-001 (exit 3) failed because the SECOND implementation of
    the identity/history reference mixed key types: rate_table_second built
    the train table from train_s["abn"].tolist() (raw strings) while the eval
    lookup copied the construction score.py's 1-tuple idiom
    (ident_table.get((row["abn"],), ...)) - score.py is consistent because its
    own rate_table builds tuple keys from a column list, but here every key
    missed, each row fell back to the global rate, the vector was constant and
    diag.py correctly refused to compare against a constant.
    """

    TRAIN = (["A", "A", "B", "B", "B"], [1, 1, 0, 0, 0])
    EVAL_ROWS = [{"abn": "A"}, {"abn": "B"}, {"abn": "A"}, {"abn": "C"}]

    def test_fixed_lookup_returns_per_charity_rates(self):
        keys, ys = self.TRAIN
        table, global_rate = mirror_rate_table_second(keys, ys)
        self.assertEqual(table, {"A": 1.0, "B": 0.0})
        fixed = [table.get(r["abn"], global_rate) for r in self.EVAL_ROWS]
        self.assertEqual(fixed, [1.0, 0.0, 1.0, global_rate])
        # both charity rates plus the global fallback are distinct: a real
        # ranking, not a constant
        self.assertEqual(len(set(fixed)), 3)
        self.assertEqual(fixed[3], global_rate)  # unseen charity falls back

    def test_defective_tuple_lookup_collapses_to_constant(self):
        """The diag-001 defect class: a 1-tuple lookup in a string-keyed table."""
        keys, ys = self.TRAIN
        table, global_rate = mirror_rate_table_second(keys, ys)
        self.assertIn("A", table)
        self.assertNotIn(("A",), table)  # the tuple key does not exist
        defective = [table.get((r["abn"],), global_rate) for r in self.EVAL_ROWS]
        self.assertEqual(defective, [global_rate] * len(self.EVAL_ROWS))
        self.assertTrue(mirror_plain_auc_constant_guard(defective))
        # the two lookups diverge on the same table and rows, so this mirror
        # distinguishes the fixed form from the defective one
        fixed = [table.get(r["abn"], global_rate) for r in self.EVAL_ROWS]
        self.assertNotEqual(fixed, defective)
        self.assertFalse(mirror_plain_auc_constant_guard(fixed))

    def test_shipped_identity_lookup_uses_the_tables_key_type(self):
        """Bites on the shipped file itself: diag.py builds the identity table
        from raw abn strings, so its eval lookup must use the raw key. This
        test fails on the pre-fix source diag-001 shipped."""
        source = DIAG.read_text()
        self.assertTrue(
            'rate_table_second(train_s["abn"].tolist(), train_y)' in source,
            "the identity table is no longer built from raw abn strings; "
            "update this guard to the new build form")
        self.assertTrue(
            'ident_table.get(row["abn"], ident_global)' in source,
            "diag.py's identity lookup does not use the raw-string key its "
            "rate table is built with")
        self.assertFalse(
            'ident_table.get((row["abn"],), ident_global)' in source,
            "diag.py still carries the diag-001 defect: a 1-tuple lookup in "
            "the string-keyed identity table misses every key, collapses the "
            "reference to the constant global rate and forces the refusal")


if __name__ == "__main__":
    unittest.main()
