"""Eligibility must be decided at month M, never by the target month.

The 2026-10-21 re-audit proved the v2026.11 build still let month M+1 decide whether the M row
existed: changing only R0A-2022-03's target-month attendances removed the row. This is the smallest
form of that counterfactual - a provider with a full history whose target month falls below the
volume gate - and it must produce a row.

Before the fix, `make_rows` built its pair list from volume-qualified months, so a provider-month
below the gate could not be a target and the preceding row vanished. That is hindsight selection:
the population is conditioned on how much the provider attended *after* the prediction was made.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "candidates" / "nhs-ae-four-hour-decline" / "source" / "build.py"

spec = importlib.util.spec_from_file_location("nhs_ae_build", BUILD)
build = importlib.util.module_from_spec(spec)
sys.modules["nhs_ae_build"] = build
spec.loader.exec_module(build)


def month(offset: int, base=(2021, 12)) -> tuple[int, int]:
    year, month_number = base
    total = year * 12 + (month_number - 1) + offset
    return total // 12, total % 12 + 1


def panel_with_target_below_the_gate(target_att1=50):
    """24 qualifying months, then a target month under MIN_ATT1."""
    panel = {}
    for offset in range(-23, 1):          # 24 months ending at M
        key = month(offset)
        panel[("TEST", key)] = {"values": {"att1": 1000, "over4_1": 200}}
    panel[("TEST", month(1))] = {"values": {"att1": target_att1, "over4_1": 5}}
    return panel


class EligibilityAtMTests(unittest.TestCase):
    def test_a_low_volume_target_month_does_not_remove_the_row(self):
        rows, gate = build.make_rows(panel_with_target_below_the_gate())
        ids = {row["row_id"] for row in rows}
        self.assertIn("TEST-2022-01", ids,
                      "the target month's attendance decided whether the M row existed")
        # The first 23 months of a 25-month panel cannot have 24 months of history; only the
        # 24th and 25th can, and the row above is the 25th.
        self.assertEqual(23, gate["skipped"]["insufficient_history"])

    def test_a_provider_without_twenty_four_months_is_still_excluded(self):
        panel = panel_with_target_below_the_gate()
        for offset in range(-23, -11):     # keep only 12 months of history
            panel.pop(("TEST", month(offset)))
        rows, gate = build.make_rows(panel)
        self.assertEqual(set(), {row["row_id"] for row in rows})
        self.assertGreater(gate["skipped"]["insufficient_history"], 0)

    def test_a_missing_target_month_is_counted_as_unobserved_not_excluded(self):
        panel = panel_with_target_below_the_gate()
        panel.pop(("TEST", month(1)))
        rows, gate = build.make_rows(panel)
        self.assertEqual(len(rows), 0)
        self.assertEqual(1, gate["skipped"]["unobserved_target"])


if __name__ == "__main__":
    unittest.main()
