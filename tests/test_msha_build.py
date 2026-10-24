"""Offline tests for the msha-enforcement-citations construction script.

Three levels of checking, mirroring tests/test_food_build.py:

* **Structural** - the label source must not ship, the prior-history features
  must come only from strictly-earlier dates of the same mine, a same-day
  group must not serve as its own history, and the runner-contract decision
  this build implements (per-section configs, no cross-section label
  columns, one binary target each) must hold in the written files.
* **Constructed output** - the writer is executed against synthetic MSHA zips
  written by the test itself (real `zip_member` / `iter_rows` / cp1252 path),
  and every config is run through the REAL qualification gate. Declared
  lists alone are not evidence.
* **Floor rule** - sections below the gate's own scoring minimums are dropped
  with their names recorded, never written as unscoreable configs.

The module is loaded with `exec(compile(...))` rather than through an import,
because a normal import writes `__pycache__` into the job's source directory,
which breaks the worker's `source_bundle` rules.

MSHA_BUILD_PATH (env) lets a caller point these tests at a variant of the
script - used once to demonstrate that the mine-id fallback guard fails
against the pre-fix implementation.
"""
import csv
import importlib.util
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "candidates" / "msha-enforcement-citations" / "source"
BUILD = Path(os.environ.get("MSHA_BUILD_PATH") or (SOURCE / "build.py"))
GATE = ROOT / "skills" / "dataset-qualification" / "scripts" / "qualify_dataset.py"

spec = importlib.util.spec_from_file_location("msha_build", BUILD)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load build.py from {BUILD}")
msha_build = importlib.util.module_from_spec(spec)
sys.modules["msha_build"] = msha_build
exec(compile(BUILD.read_bytes(), str(BUILD), "exec"), msha_build.__dict__)

gate_spec = importlib.util.spec_from_file_location("qualify_dataset_shared", GATE)
if gate_spec is None or gate_spec.loader is None:
    raise RuntimeError(f"cannot load the qualification gate from {GATE}")
gate = importlib.util.module_from_spec(gate_spec)
sys.modules["qualify_dataset_shared"] = gate
exec(compile(GATE.read_bytes(), str(GATE), "exec"), gate.__dict__)


MINE_COLUMNS = ["MINE_ID", "COAL_METAL_IND", "CURRENT_MINE_TYPE", "STATE",
                "FIPS_CNTY_CD", "PRIMARY_CANVASS", "COMPANY_TYPE", "DAYS_PER_WEEK",
                "HOURS_PER_SHIFT", "PROD_SHIFTS_PER_DAY", "PORTABLE_OPERATION"]
INSPECTION_COLUMNS = ["EVENT_NO", "MINE_ID", "INSPECTION_BEGIN_DT", "ACTIVITY_CODE",
                      "PROGRAM_AREA", "INSPECT_OFFICE_CD"]
VIOLATION_COLUMNS = ["EVENT_NO", "MINE_ID", "PART_SECTION", "VIOLATION_NO"]


def pipe_zip(path, member, columns, rows):
    """Write a publisher-shaped zip: one pipe-delimited cp1252 .txt member."""
    lines = ["|".join(columns)]
    for row in rows:
        lines.append("|".join("" if value is None else str(value) for value in row))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member, ("\r\n".join(lines) + "\r\n").encode("cp1252"))
    return path


def mine_row(mine_id, state="KY", mine_type="Underground"):
    return [mine_id, "M", mine_type, state, "021", "M", "Corporation",
            "5", "8", "2", "N"]


def pool_dates():
    """60 mining days inside each split window, plus two out-of-window days."""
    from datetime import date, timedelta

    days = []
    for start, stop in (("2001-01-01", "2021-01-01"), ("2021-01-01", "2024-01-01"),
                        ("2024-01-01", "2026-01-01")):
        first, last = date.fromisoformat(start), date.fromisoformat(stop)
        step = (last - first).days // 62
        for index in range(60):
            days.append(first + timedelta(days=5 + index * step))
    days.append(date(2000, 6, 1))   # before every window: dropped
    days.append(date(2026, 3, 1))   # after every window: dropped
    return [day.isoformat() for day in days]


def synthetic_source(tmp_dir):
    """Synthetic Mines/Inspections/Violations zips with the properties the
    build and the gate both need.

    Three mines, 60 days per split window, two inspections per mine-day (so a
    same-day group is exercised for real):

    - ``75.400``: ~75% of events in every window - clears the positives and
      distinct-days minimums in both scored windows;
    - ``56.14100(b)``: ~65% of events in every window - also clears;
    - ``77.999``: drawn only on TRAIN-window events - it clears the 1% pool-rate
      floor but has no eval/holdout positives, so the floor rule must drop it
      by the window minimums and record the drop;
    - ``56.9999``: one event in the whole pool - below the 1% rate floor.

    Codes are drawn PER EVENT with a SEEDED RNG so that ``prev_target_cited``
    is a genuine prior rather than a parity pattern, and (in the MSHA pool) an
    event with no section at all never exists.

    Two extra shape traps are built in deliberately:

    - the 2000 and 2026 dated events fall outside every window and must be
      counted as dropped, never pooled;
    - ``EVENT_NO`` E9000's inspection row names mine M300 while every one of
      its violation rows carries an EMPTY MINE_ID. The violations table is not
      required to repeat the mine, so the event must still be pooled off the
      inspection row - an implementation that trusts the violation row alone
      drops it silently.
    """
    import random
    from datetime import date, timedelta

    rng = random.Random(20261012)
    mines = [mine_row("M100"), mine_row("M200"), mine_row("M300", state="WV"),
             mine_row("M400", state="VA")]
    inspections, violations = [], []
    counter = 0

    def add_event(mine_id, day_text, sections, inspection_mine=None,
                  violation_mine=None):
        nonlocal counter
        counter += 1
        event_no = f"E{counter:05d}"
        stamp = f"{day_text[5:7]}/{day_text[8:10]}/{day_text[0:4]}"
        inspections.append([event_no, inspection_mine or mine_id, stamp,
                            "01", "Coal", "0101"])
        if not sections:
            sections = ["75.400"]
        for section in sorted(sections):
            violations.append([event_no,
                               mine_id if violation_mine is None else violation_mine,
                               section, f"{counter:05d}"])

    window_of_day = {}
    for day_text in pool_dates():
        window = "train" if day_text < "2021-01-01" else (
            "eval" if day_text < "2024-01-01" else (
                "holdout" if day_text < "2026-01-01" else "outside"))
        window_of_day[day_text] = window

    for day_text in pool_dates():
        window = window_of_day[day_text]
        for mine_id in ("M100", "M200", "M300"):
            for _ in range(2):
                sections = set()
                if rng.random() < 0.75:
                    sections.add("75.400")
                if rng.random() < 0.65:
                    sections.add("56.14100(b)")
                if window == "train" and rng.random() < 0.5:
                    sections.add("77.999")
                add_event(mine_id, day_text, sections)

    # A same-day extra: the second event of that mine-day must not see the
    # first as its own history.
    add_event("M100", "2022-06-06", {"75.400"})
    add_event("M100", "2022-06-06", {"56.14100(b)"})
    # The mine-id fallback trap.
    add_event("M300", "2022-07-07", {"75.400"}, inspection_mine="M300",
              violation_mine="")
    # A mine that first appears INSIDE the eval window: its earliest eval rows
    # have no prior inspection at all and must carry the -1 sentinel.
    add_event("M400", "2022-11-11", {"75.400"})
    add_event("M400", "2022-11-11", {"56.14100(b)"})
    add_event("M400", "2022-12-12", {"75.400"})
    # One below-rate section, one event only.
    add_event("M200", "2022-08-08", {"56.9999"})

    work_dir = Path(tmp_dir) / "zips"
    work_dir.mkdir(parents=True, exist_ok=True)
    pipe_zip(work_dir / "Mines.zip", "Mines.txt", MINE_COLUMNS, mines)
    pipe_zip(work_dir / "Inspections.zip", "Inspections.txt",
             INSPECTION_COLUMNS, inspections)
    pipe_zip(work_dir / "Violations.zip", "Violations.txt",
             VIOLATION_COLUMNS, violations)
    return work_dir


def base_record(mine_id, day, sections, event_no, window="train", activity="01",
                program="Coal", office="0101"):
    """One pool record in the layout enrich_with_priors() consumes."""
    year, month, _ = (int(part) for part in day.split("-"))
    from datetime import date as date_cls
    return (mine_id, day) + tuple(["", "Underground", "KY", "021", "M",
                                   "Corporation", "5", "8", "2", "N"]) + (
        activity, program, office, month, date_cls(year, month, 1).weekday()) + (
        frozenset(sections), event_no, window)


class Structural(unittest.TestCase):
    def test_label_source_never_ships(self):
        self.assertIn(msha_build.LABEL_SOURCE, msha_build.EXCLUDED_POST_HOC)
        self.assertNotIn(msha_build.LABEL_SOURCE, msha_build.FEATURES)

    def test_post_hoc_exclusions_cover_the_citation_record(self):
        # The label source and its neighbours are the post-visit record.
        for column in ("PART_SECTION", "VIOLATION_NO", "PROPOSED_PENALTY",
                       "VIOLATION_ISSUE_DT", "INSPECTION_END_DT",
                       "TOTAL_ON_SITE_HOURS", "CURRENT_OPERATOR_NAME"):
            self.assertIn(column, msha_build.EXCLUDED_POST_HOC)
        overlap = set(msha_build.FEATURES) & set(msha_build.EXCLUDED_POST_HOC)
        self.assertEqual(overlap, set())

    def test_split_windows_disjoint_and_ordered(self):
        windows = msha_build.SPLIT_WINDOWS
        self.assertTrue(windows["train"]["end"] <= windows["eval"]["start"])
        self.assertTrue(windows["eval"]["end"] <= windows["holdout"]["start"])
        self.assertLess(windows["train"]["start"], windows["eval"]["start"])
        self.assertLess(windows["eval"]["start"], windows["holdout"]["start"])

    def test_config_name_slug(self):
        # Sections are normalised (upper-cased, whitespace collapsed) before
        # they become a name, so a lettered section keeps its letter's case.
        self.assertEqual(msha_build.config_name("56.14100(b)"), "sec_56_14100_b")
        self.assertEqual(
            msha_build.config_name(msha_build.normalise_section(" 56.14100(b) ")),
            "sec_56_14100_B")
        self.assertEqual(
            msha_build.config_name(msha_build.normalise_section("75.400")),
            "sec_75_400")
        self.assertEqual(msha_build.config_name("75.400"), "sec_75_400")

    def test_priors_use_strictly_earlier_dates(self):
        rows = [
            base_record("M1", "2022-01-05", {"75.400"}, "E1"),
            base_record("M1", "2022-01-05", {"56.14100(b)"}, "E2"),
            base_record("M1", "2022-03-01", {"75.400"}, "E3"),
        ]
        enriched = msha_build.enrich_with_priors(rows)
        by_event = {record[18]: record for record in enriched}
        # Same-day rows form one group: neither see the other.
        self.assertEqual(by_event["E1"][20], 0)
        self.assertEqual(by_event["E2"][20], 0)
        self.assertEqual(by_event["E1"][21], -1)
        self.assertEqual(by_event["E1"][25], False)
        # The later event sees both earlier inspections of the same mine.
        self.assertEqual(by_event["E3"][20], 2)
        self.assertEqual(by_event["E3"][21], 55)
        self.assertEqual(by_event["E3"][22], 2)
        self.assertEqual(by_event["E3"][24], 2)
        self.assertEqual(by_event["E3"][26], frozenset({"75.400", "56.14100(b)"}))

    def test_prev_snapshot_is_the_most_recent_group_not_the_cumulative_set(self):
        # The shipped quality.json documents prev_target_cited as "cited on the
        # mine's most recent strictly-earlier pooled inspection". A snapshot
        # taken from the cumulative distinct set would answer "ever cited",
        # which is a different feature; against that implementation the first
        # assertion below fails with the two-section set.
        rows = [
            base_record("M1", "2022-01-05", {"75.400"}, "E1"),
            base_record("M1", "2022-02-05", {"56.14100(b)"}, "E2"),
            base_record("M1", "2022-03-05", {"77.999"}, "E3"),
        ]
        enriched = msha_build.enrich_with_priors(rows)
        by_event = {record[18]: record for record in enriched}
        self.assertEqual(by_event["E3"][26], frozenset({"56.14100(b)"}),
                         "the snapshot must be the most recent group only")
        self.assertEqual(by_event["E3"][24], 2,
                         "prior_distinct_sections stays cumulative")

    def test_priors_are_per_mine(self):
        rows = [
            base_record("M1", "2022-01-05", {"75.400"}, "E1"),
            base_record("M2", "2022-02-05", {"75.400"}, "E2"),
        ]
        enriched = msha_build.enrich_with_priors(rows)
        for record in enriched:
            self.assertEqual(record[20], 0, "a mine must never see another mine")


class Constructed(unittest.TestCase):
    """Run the real build against synthetic zips, then the real gate."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="msha-build-test-")
        cls.out = Path(cls.tmp) / "extract"
        cls.work = synthetic_source(cls.tmp)

        def fake_download(name, work_dir, attempts=4):
            return Path(work_dir) / msha_build.SOURCES[name]

        with patch.object(msha_build, "download", side_effect=fake_download):
            exit_code = msha_build.main(["--out", str(cls.out),
                                         "--work-dir", str(cls.work),
                                         "--built-at", "2026-10-12T00:00:00+00:00"])
        assert exit_code == 0, "build must succeed against the synthetic zips"
        cls.manifest = json.loads((cls.out / "manifest.json").read_text())
        cls.summary = json.loads((cls.out / "build_summary.json").read_text())

    def test_configs_and_layout(self):
        shipped = self.manifest["shipped_configs"]
        self.assertIn("sec_75_400", shipped)
        # Section identity is normalised upper-case (the publisher writes the
        # same section more than one way), so a lettered section's slug keeps
        # the letter's case.
        self.assertIn("sec_56_14100_B", shipped)
        self.assertNotIn("sec_77_999", shipped, "no eval/holdout positives")
        self.assertNotIn("sec_56_9999", shipped, "below the rate floor")
        for name in shipped:
            config = self.out / name
            self.assertTrue((config / "public" / "train.csv").is_file())
            self.assertTrue((config / "public" / "eval.csv").is_file())
            self.assertTrue((config / "private" / "holdout.csv").is_file())
            self.assertTrue((config / "meta.json").is_file())
            self.assertTrue((config / "quality.json").is_file())

    def test_every_event_carries_a_usable_mine_id(self):
        # The fallback guard: the violations table is not required to repeat
        # the mine, so an event named only by its inspection row must still be
        # pooled. Against the pre-fix implementation this assertion fails with
        # dropped_no_mine_id == 1 and the E-event absent from every split.
        self.assertEqual(self.manifest["pool"]["dropped_no_mine_id"], 0)
        with (self.out / "sec_75_400" / "public" / "eval.csv").open(
                newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        mine_columns = {row["mine_id"] for row in rows}
        self.assertTrue(mine_columns <= {"M100", "M200", "M300", "M400"})
        self.assertNotIn("", mine_columns, "a pooled row shipped an empty mine_id")
        self.assertGreaterEqual(
            self.manifest["pool"]["events"],
            sum(entry["rows"]["eval"] for entry in self.manifest["configs"]),
            "the fallback event must be pooled and counted in every config")

    def test_headers_are_the_declared_contract(self):
        expected = len(msha_build.ID_COLUMNS) + len(msha_build.FEATURES) + 1
        for name in self.manifest["shipped_configs"]:
            for relative in ("public/train.csv", "public/eval.csv",
                             "private/holdout.csv"):
                with (self.out / name / relative).open(newline="",
                                                       encoding="utf-8") as handle:
                    header = next(csv.reader(handle))
                self.assertEqual(len(header), expected, f"{name}/{relative}")
                self.assertEqual(header[:len(msha_build.ID_COLUMNS)],
                                 msha_build.ID_COLUMNS)
                self.assertEqual(header[-1], name)

    def test_no_cross_section_label_columns_ship(self):
        for name in self.manifest["shipped_configs"]:
            for relative in ("public/train.csv", "public/eval.csv",
                             "private/holdout.csv"):
                with (self.out / name / relative).open(newline="",
                                                       encoding="utf-8") as handle:
                    header = next(csv.reader(handle))
                other = [column for column in header
                         if column.startswith("sec_") and column != name]
                self.assertEqual(other, [], f"{name}/{relative} ships {other}")
                for column in ("PART_SECTION", "VIOLATION_NO", "PROPOSED_PENALTY"):
                    self.assertNotIn(column, header)

    def test_labels_csv_carries_the_joint_matrix(self):
        with (self.out / "labels.csv").open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            body = list(reader)
        self.assertEqual(header[:3], ["event_no", "inspection_date", "mine_id"])
        for section in self.manifest["floor_sections"]:
            self.assertIn(msha_build.config_name(section), header)
        self.assertEqual(len(body), self.manifest["pool"]["events"])
        indexes = {name: position for position, name in enumerate(header[3:], start=3)}
        # The joint matrix is the same label information as the per-config
        # targets: an event's row must agree with every shipped config.
        with (self.out / "sec_75_400" / "public" / "eval.csv").open(
                newline="", encoding="utf-8") as handle:
            eval_rows = list(csv.DictReader(handle))
        matrix = {row[0]: {name: row[position]
                           for name, position in indexes.items()} for row in body}
        for row in eval_rows[:50]:
            event = row["event_no"]
            self.assertIn(event, matrix)
            self.assertEqual(int(matrix[event]["sec_75_400"]),
                             int(row["sec_75_400"]))

    def test_meta_matches_files(self):
        for entry in self.manifest["configs"]:
            name = entry["name"]
            meta = json.loads((self.out / name / "meta.json").read_text())
            self.assertEqual(meta["target"], name)
            for split, relative in (("train", "public/train.csv"),
                                    ("eval", "public/eval.csv"),
                                    ("holdout", "private/holdout.csv")):
                with (self.out / name / relative).open(newline="",
                                                       encoding="utf-8") as handle:
                    rows = list(csv.DictReader(handle))
                self.assertEqual(meta["rows"][split], len(rows))
                rate = sum(int(row[name]) for row in rows) / len(rows)
                self.assertAlmostEqual(meta["positive_rate"][split], rate, places=6)

    def test_prev_target_cited_semantics(self):
        name = "sec_75_400"
        sentinel = prior0 = prior1 = 0
        with (self.out / name / "public" / "eval.csv").open(newline="",
                                                           encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                value = int(row["prev_target_cited"])
                if value == -1:
                    sentinel += 1
                    self.assertEqual(int(row["prior_inspections"]), 0)
                elif value == 0:
                    prior0 += 1
                elif value == 1:
                    prior1 += 1
                else:
                    self.fail(f"prev_target_cited must be 1/0/-1, saw {value}")
                self.assertIn(int(row[name]), (0, 1))
        self.assertGreater(sentinel, 0, "no prior-less row in eval: fixture is wrong")
        self.assertGreater(prior0, 0, "the persistence feature never reads 0")
        self.assertGreater(prior1, 0, "the persistence feature never fires")

    def test_legacy_configs_require_new_evaluation_contract(self):
        failures = []
        for name in self.manifest["shipped_configs"]:
            report = gate.qualify(self.out / name)
            self.assertFalse(report.ok)
            if report.failed_checks != ["contract.declared"]:
                failures.append((name, report.failed_checks))
        self.assertEqual(failures, [])

    def test_quality_descriptors_declare_what_the_gate_reads(self):
        for name in self.manifest["shipped_configs"]:
            quality = json.loads((self.out / name / "quality.json").read_text())
            self.assertEqual(quality["time_column"], "inspection_date")
            self.assertEqual(quality["event_key_column"], "inspection_date")
            self.assertEqual(quality["features_documented_at"], "prediction_time")
            self.assertTrue(quality["task"]["prediction_time"])
            columns = [measurement["column"] for measurement in quality["measurements"]]
            for column in ("prior_inspections", "days_since_previous",
                           "prior_citation_count", "prior_mean_citations",
                           "prior_distinct_sections", "prev_target_cited"):
                self.assertIn(column, columns)

    def test_out_of_window_events_are_dropped_and_counted(self):
        # The fixture puts one event in 2000 and one in 2026.
        self.assertGreaterEqual(self.manifest["pool"]["dropped_outside_windows"], 2)

    def test_manifest_records_the_source_bytes_and_attribution(self):
        for name, entry in self.manifest["source_files"].items():
            self.assertTrue(entry["url"].startswith(msha_build.BASE + "/"))
            self.assertGreater(entry["bytes"], 0, name)
        self.assertIn("MSHA", self.manifest["attribution"])


class FloorRule(unittest.TestCase):
    def test_gate_minimums_derived_from_the_gate(self):
        self.assertEqual(msha_build.MIN_POSITIVES, gate.MIN_EVAL_POSITIVES)
        self.assertEqual(msha_build.MIN_DISTINCT_DAYS, gate.MIN_DISTINCT_EVENTS)

    def test_floor_rule_drops_unscoreable_sections(self):
        manifest = Constructed.manifest
        self.assertIn("77.999", manifest["floor_candidates_above_rate"])
        self.assertNotIn("77.999", manifest["floor_sections"])
        self.assertIn("77.999", manifest["floor_dropped_by_window_minimums"])
        self.assertNotIn("56.9999", manifest["floor_candidates_above_rate"])
        self.assertEqual(manifest["floor_sections"],
                         sorted(manifest["floor_sections"],
                                key=lambda section: (-manifest["section_prevalence"][section],
                                                     section)))

    def test_config_cap_keeps_every_floor_section_in_the_matrix(self):
        labels_header = (Constructed.out / "labels.csv").read_text(
            encoding="utf-8").splitlines()[0].split(",")
        self.assertEqual(len(labels_header) - 3,
                         len(Constructed.manifest["floor_sections"]))


if __name__ == "__main__":
    unittest.main()
