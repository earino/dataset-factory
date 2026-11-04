"""Synthetic rehearsal for the unhcr-corridor-entry-surge construction.

Real build.py (--rehearsal: the real-data anchor/fixture asserts are for the
pinned HDX vintage and cannot run on synthetic bytes) over a synthetic HDX
panel -> the real qualification gate over the full synthetic artifact ->
exact-byte --accept -> score.py references (score.py's FIRST execution
happens here, on synthetic bytes only - its real run is inside the worker
job, strictly after the worker's gate and acceptance) -> structural
one-shot assertions -> byte-identical rebuild -> red/green mutations the
gate must catch. No real data, no network.

The P0 properties this test pins (the design decisions of
unhcr-corridor-001):

  * ONE ROW PER CORRIDOR across all splits (the operator's recorded reopen
    condition for the dropped panel task: no corridor ships two rows);
  * the corridor-grain cross-row probe reads coverage 0 in every split
    (the parent task's exact self-answering exposure is structurally gone);
  * labels equal the two-year cumulative doubling rule recomputed from the
    generator's corridor parameters;
  * the exclusion machinery is exercised on real shapes: left-censored
    panel-start entry, published-prior-cell of value ZERO (the probe-exact
    truthiness rule), host-silent outcome year, live-edge entries whose
    outcome window extends beyond the vintage;
  * a smuggled outcome-sum column (the parent task's failure mode: a
    shipped value that IS the label operand) is REFUSED by the gate's
    leakage check;
  * an eval row outside the declared entry-year window is REFUSED; the
    timing block is never optional; a stale report against different bytes
    is REFUSED; a duplicated row id is REFUSED.
"""

import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUILD = REPO / "candidates" / "unhcr-corridor-entry-surge" / "source" / "build.py"
SCORE = REPO / "candidates" / "unhcr-corridor-entry-surge" / "source" / "score.py"
GATE = REPO / "skills" / "dataset-qualification" / "scripts" / "qualify_dataset.py"

HEADER = ["Year", "Country of Origin Code", "Country of Asylum Code",
          "Procedure Type", "Application Data Type", "Application Type Code",
          "Number of Applications"]


def build_synthetic_params():
    """Deterministic corridor parameters: (origin, host, t0) -> dict.

    Every regular corridor gets a strictly positive published prior-year
    cell (< 500 so T0 is the FIRST crossing), an entry-year value >= 500,
    pre-prior history cells below 500, and controlled outcome years.
    """
    import random
    rng = random.Random(20261105)
    params = {}
    rows = []  # (year, origin, host, value, split-value-rows)
    used_pairs = set()

    def emit(year, origin, host, value, split_in_two=False):
        if split_in_two and value >= 2:
            share = rng.randint(1, value - 1)
            rows.append((year, origin, host, "G", "P", "N", share))
            rows.append((year, origin, host, "G", "P", "V", value - share))
        else:
            rows.append((year, origin, host, "G", "P", "N", value))

    def unique_pair(year, i):
        """(origin, host) not used by any earlier corridor - a repeated pair
        would make the later year a non-crossing for the same corridor and
        silently shrink the later split (the rehearsal's first run caught
        exactly this)."""
        j = 0
        while True:
            origin = f"O{(year * 7 + i + j * 13) % 40:02d}"
            host = f"H{(year * 3 + i + j * 7) % 20:02d}"
            if (origin, host) not in used_pairs:
                used_pairs.add((origin, host))
                return origin, host
            j += 1

    def add_corridor(origin, host, t0, label, history=1):
        prior = rng.randint(60, 420) if history else None
        value = rng.randint(520, 3800)
        if history:
            emit(t0 - 1, origin, host, prior)
            for back in range(2, history + 1):
                if t0 - back >= 2000:  # keep the synthetic panel within 2000..2025
                    emit(t0 - back, origin, host, rng.randint(20, 450))
        emit(t0, origin, host, value, split_in_two=True)
        if label:
            t1 = int(value * rng.uniform(0.8, 1.3))
            t2 = 2 * value - t1 + rng.randint(1, 150)
        else:
            t1 = int(value * rng.uniform(0.1, 0.7))
            t2 = int(value * rng.uniform(0.1, 0.7))
        if t0 + 2 <= 2025:
            emit(t0 + 1, origin, host, t1)
            emit(t0 + 2, origin, host, t2)
        params[(origin, host, t0)] = {"prior": prior, "value": value,
                                      "t1": t1, "t2": t2, "label": label}

    # train 2001-2014: 8 corridors/year, balanced labels both classes per year
    for year in range(2001, 2015):
        for i in range(8):
            origin, host = unique_pair(year, i)
            add_corridor(origin, host, year, label=(i % 4 in (0, 1)),
                         history=rng.randint(1, 4))
    # eval 2015-2020: 12/year, positives 2/3 -> 48 positives, 48 events
    for year in range(2015, 2021):
        for i in range(12):
            origin, host = unique_pair(year, i)
            add_corridor(origin, host, year, label=(i % 3 != 0),
                         history=rng.randint(1, 4))
    # holdout 2021-2023: 20/year, positives 2/3 -> 40 positives, ~40 events
    for year in range(2021, 2024):
        for i in range(20):
            origin, host = unique_pair(year, i)
            add_corridor(origin, host, year, label=(i % 3 != 0),
                         history=rng.randint(1, 4))

    # left-censored: first (and only) cell at the panel start 2000
    rows.append((2000, "OLC", "HLC", "G", "P", "N", 800))
    # published prior cell of value ZERO: entry excluded by the probe-exact
    # truthiness rule (prior exists but is not > 0)
    rows.append((2012, "OZP", "HZP", "G", "P", "N", 300))
    rows.append((2013, "OZP", "HZP", "G", "P", "N", 0))
    rows.append((2014, "OZP", "HZP", "G", "P", "N", 600))
    # host-silent outcome year: host HSX has cells ONLY in 2014 and 2015
    rows.append((2014, "OHS", "HSX", "G", "P", "N", 120))
    rows.append((2015, "OHS", "HSX", "G", "P", "N", 700))
    # live edge 2024 and 2025: outcome windows extend beyond the vintage
    rows.append((2023, "OLE", "HLE", "G", "P", "N", 400))
    rows.append((2024, "OLE", "HLE", "G", "P", "N", 900))
    rows.append((2024, "OL2", "HL2", "G", "P", "N", 300))
    rows.append((2025, "OL2", "HL2", "G", "P", "N", 600))
    # never-crossing corridors stay out of the population entirely
    rows.append((2016, "ONC", "HNC", "G", "P", "N", 499))
    rows.append((2017, "ONC", "HNC", "G", "P", "N", 480))
    # non-G / non-P rows and an unparseable count: filter + skip exercised
    rows.append((2018, "ONC", "HNC", "U", "P", "N", 9000))
    rows.append((2018, "ONC", "HNC", "G", "C", "N", 9000))
    rows.append((2019, "ONC", "HNC", "G", "P", "N", "n/a"))
    return params, rows


def write_panel_csv(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        writer.writerows(rows)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


class UNHCRCorridorSyntheticRehearsal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="unhcr-corridor-synth-"))
        cls.panel = cls.tmp / "asylum_applications_residing_world.csv"
        cls.params, synth_rows = build_synthetic_params()
        write_panel_csv(cls.panel, synth_rows)
        cls.out = cls.tmp / "extract"
        cls.summary = cls.tmp / "summary.json"
        proc = run([sys.executable, "-u", str(BUILD), "--out", str(cls.out),
                    "--work-dir", str(cls.tmp / "work"), "--built-at",
                    "2026-11-05T00:00:00Z", "--csv", str(cls.panel),
                    "--summary-out", str(cls.summary), "--rehearsal"])
        assert proc.returncode == 0, f"build failed:\n{proc.stdout}\n{proc.stderr}"
        cls.build_log = proc.stdout
        cls.report = cls.tmp / "qualification.json"
        proc = run([sys.executable, str(GATE), str(cls.out), "--json",
                    "--report", str(cls.report)])
        assert proc.returncode == 0, f"gate failed:\n{proc.stdout}\n{proc.stderr}"
        cls.gate_report = json.loads(cls.report.read_text())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def read_split(self, rel):
        with (self.out / rel).open() as handle:
            return list(csv.DictReader(handle))

    def all_rows(self):
        return (self.read_split("public/train.csv")
                + self.read_split("public/eval.csv")
                + self.read_split("private/holdout.csv"))

    def test_01_gate_passed_with_zero_failed_checks(self):
        self.assertEqual(self.gate_report.get("failed_checks"), [])
        self.assertTrue(self.gate_report.get("ok"))

    def test_02_one_row_per_corridor_across_all_splits(self):
        seen = {}
        for row in self.all_rows():
            key = (row["origin"], row["asylum"])
            self.assertNotIn(key, seen,
                             f"corridor {key} shipped more than one row")
            seen[key] = row["row_id"]
        self.assertGreater(len(seen), 200)

    def test_03_labels_match_two_year_cumulative_doubling(self):
        checked = 0
        for row in self.all_rows():
            key = (row["origin"], row["asylum"], int(row["entry_year"]))
            self.assertIn(key, self.params, f"unexpected row {key}")
            want = self.params[key]
            self.assertEqual(int(row["apps_t0"]), want["value"])
            self.assertEqual(int(row["apps_t0m1"]), want["prior"])
            expect = int(want["t1"] + want["t2"] >= 2 * want["value"])
            self.assertEqual(int(row["cum2_2x"]), expect, row["row_id"])
            checked += 1
        self.assertGreater(checked, 200)

    def test_04_corridor_grain_probe_coverage_zero(self):
        results = self.gate_report["results"]
        probe_results = {c["check"]: c["evidence"] for c in results
                         if c["check"].startswith("contract.cross_row_probe_")}
        self.assertTrue(probe_results, "no probe results in the gate report")
        corridor_probe = probe_results["contract.cross_row_probe_0"]
        for split, entry in corridor_probe.items():
            self.assertEqual(entry["covered"], 0,
                             f"corridor-grain coverage must be 0: {split}")

    def test_05_exclusion_machinery_on_real_shapes(self):
        summary = json.loads(self.summary.read_text())
        exclusions = summary["exclusions"]
        # exactly the two designed corridors: OLC (left-censored panel start)
        # and OZP (published prior cell of value zero)
        self.assertGreaterEqual(exclusions["missing_published_prior"], 2)
        self.assertGreaterEqual(exclusions["host_silent_outcome_year"], 1)
        self.assertGreaterEqual(exclusions["live_edge_outcome_beyond_vintage"], 2)
        detail = summary["exclusion_detail"]
        self.assertIn("missing_published_prior|left_censored_panel_start|train",
                      detail)
        self.assertIn("missing_published_prior|no_positive_published_prior_cell|train",
                      detail)
        self.assertIn("host_silent_outcome_year|label_undefined|eval", detail)
        built = {(r["origin"], r["asylum"]) for r in self.all_rows()}
        for absent in (("OLC", "HLC"), ("OZP", "HZP"), ("OHS", "HSX"),
                       ("OLE", "HLE"), ("OL2", "HL2"), ("ONC", "HNC")):
            self.assertNotIn(absent, built, f"{absent} must not be built")

    def test_06_accept_exact_bytes_then_score_references(self):
        proc = run([sys.executable, str(GATE), "--accept", str(self.report),
                    str(self.out)])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        refs = self.tmp / "references.json"
        proc = run([sys.executable, str(SCORE), "--data", str(self.out),
                    "--accepted-report", str(self.report),
                    "--report", str(refs)])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(refs.read_text())
        self.assertEqual(data["rows"]["eval"],
                          len(self.read_split("public/eval.csv")))
        for name in ("identity_only_origin", "identity_only_host",
                     "identity_combined", "momentum_raw",
                     "momentum_bucket_rate", "persistence_state_rate",
                     "persistence_last_value", "global_rate",
                     "majority_class"):
            self.assertIn(name, data["references"])
        self.assertIn(data["deciding_check"]["verdict"],
                      ("headroom_demonstrated_at_reference_level",
                       "identity_prior_dominates_no_headroom",
                       "no_demonstrated_headroom_inconclusive"))
        # the holdout is never opened by the scoring stage
        for name, entry in data["references"].items():
            self.assertNotIn("holdout_auc", entry)

    def test_07_byte_identical_rebuild(self):
        out2 = self.tmp / "extract2"
        proc = run([sys.executable, "-u", str(BUILD), "--out", str(out2),
                    "--work-dir", str(self.tmp / "work2"), "--built-at",
                    "2026-11-05T00:00:00Z", "--csv", str(self.panel),
                    "--summary-out", str(self.tmp / "summary2.json"),
                    "--rehearsal"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for rel in ("public/train.csv", "public/eval.csv",
                    "private/holdout.csv", "meta.json", "quality.json"):
            a = hashlib.sha256((self.out / rel).read_bytes()).hexdigest()
            b = hashlib.sha256((out2 / rel).read_bytes()).hexdigest()
            self.assertEqual(a, b, f"{rel} not byte-identical on rebuild")

    def test_08_red_eval_row_outside_window_refused(self):
        mutated = self.tmp / "mutated-window"
        shutil.copytree(self.out, mutated)
        with (mutated / "public/eval.csv").open() as handle:
            rows = list(csv.DictReader(handle))
            fields = list(rows[0].keys())
        outside = [dict(rows[0], entry_date="2014-12-31",
                        entry_year="2014", row_id="XX-outside-1")]
        with (mutated / "public/eval.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows + outside)
        proc = run([sys.executable, str(GATE), str(mutated), "--json",
                    "--report", str(self.tmp / "m1.json")])
        self.assertNotEqual(proc.returncode, 0,
                            "an eval row outside the declared window must fail")
        report = json.loads((self.tmp / "m1.json").read_text())
        names = [c["check"] for c in report["results"] if not c["ok"]]
        self.assertTrue(any("rows_within_declared_windows" in n for n in names),
                        f"unexpected failure set: {names}")

    def test_09_red_timing_block_removed_refused(self):
        mutated = self.tmp / "mutated-timing"
        shutil.copytree(self.out, mutated)
        quality = json.loads((mutated / "quality.json").read_text())
        quality.pop("timing")
        (mutated / "quality.json").write_text(json.dumps(quality, indent=1))
        proc = run([sys.executable, str(GATE), str(mutated), "--json",
                    "--report", str(self.tmp / "m2.json")])
        self.assertNotEqual(proc.returncode, 0,
                            "removing the timing block must fail the gate")

    def test_10_red_stale_report_refused(self):
        mutated = self.tmp / "mutated-bytes"
        shutil.copytree(self.out, mutated)
        quality = json.loads((mutated / "quality.json").read_text())
        quality["built_at_utc"] = "2026-11-06T00:00:00Z"
        (mutated / "quality.json").write_text(json.dumps(quality, indent=1))
        proc = run([sys.executable, str(GATE), "--accept", str(self.report),
                    str(mutated)])
        self.assertNotEqual(proc.returncode, 0,
                            "a report for different bytes must be refused")

    def test_11_red_smuggled_outcome_ratio_refused(self):
        # the parent task's failure mode in its sharpest form: a shipped
        # column that DERIVES the label (outcome_ratio = (t1+t2) / (2 x t0);
        # ratio >= 1 IS the label), fully declared in every quality.json
        # block so only the gate's single-column leakage check can catch it
        mutated = self.tmp / "mutated-leak"
        shutil.copytree(self.out, mutated)
        for rel in ("public/train.csv", "public/eval.csv",
                    "private/holdout.csv"):
            path = mutated / rel
            with path.open() as handle:
                rows = list(csv.DictReader(handle))
                fields = list(rows[0].keys())
            for row in rows:
                key = (row["origin"], row["asylum"], int(row["entry_year"]))
                want = self.params[key]
                row["outcome_ratio"] = str(
                    round((want["t1"] + want["t2"]) / (2 * want["value"]), 6))
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields + ["outcome_ratio"])
                writer.writeheader()
                writer.writerows(rows)
        quality = json.loads((mutated / "quality.json").read_text())
        quality["shipped_columns"] = quality["shipped_columns"] + ["outcome_ratio"]
        quality["features"] = quality["features"] + ["outcome_ratio"]
        quality["measurements"] = quality["measurements"] + [
            {"column": "outcome_ratio", "unit": "ratio", "frame": "smuggled"}]
        quality["evaluation_contract"]["feature_evidence"]["outcome_ratio"] = {
            "source": "smuggled derivation of the label operands",
            "availability": "never available at the instant",
            "status": "assumed"}
        (mutated / "quality.json").write_text(json.dumps(quality, indent=1))
        meta = json.loads((mutated / "meta.json").read_text())
        meta["columns"] = meta["columns"] + ["outcome_ratio"]
        (mutated / "meta.json").write_text(json.dumps(meta, indent=1))
        proc = run([sys.executable, str(GATE), str(mutated), "--json",
                    "--report", str(self.tmp / "m3.json")])
        self.assertNotEqual(proc.returncode, 0,
                            "a shipped label-determining column must fail the gate")
        report = json.loads((self.tmp / "m3.json").read_text())
        names = [c["check"] for c in report["results"] if not c["ok"]]
        self.assertTrue(any("no_single_column_determines_the_target" in n
                            for n in names),
                        f"expected the leakage check to bite, got: {names}")

    def test_12_red_duplicate_row_id_refused(self):
        mutated = self.tmp / "mutated-dupe"
        shutil.copytree(self.out, mutated)
        path = mutated / "public/eval.csv"
        with path.open() as handle:
            rows = list(csv.DictReader(handle))
            fields = list(rows[0].keys())
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows + [rows[0]])
        proc = run([sys.executable, str(GATE), str(mutated), "--json",
                    "--report", str(self.tmp / "m4.json")])
        self.assertNotEqual(proc.returncode, 0,
                            "a duplicated row id must fail the gate")


if __name__ == "__main__":
    unittest.main()
