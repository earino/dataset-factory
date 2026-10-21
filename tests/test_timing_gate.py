"""The timing declaration is the defence against a feature that was published after the forecast.

These tests exist because `nhs-ae-four-hour-decline` reached `packaged` with 25 features that NHS
England publishes about ten days after the month ends, while its record said the prediction was made
at the end of the month. `features_documented_at: "prediction_time"` was true of the *period* and
false of the *release*, and the old gate checked only the string.

Each case below is the shape of a real failure, not a hypothetical.
"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "skills" / "dataset-qualification" / "scripts" / "qualify_dataset.py"

spec = importlib.util.spec_from_file_location("qualify_dataset_timing", GATE_PATH)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def quality(lag=10, instant_kind="period_end", instant_lag=0, selection="M",
            source_kind="statistical_release", observations=None):
    if observations is None:
        observations = [{"period": "2026-08", "period_end": "2026-08-31",
                         "published": "2026-09-10"}]
    return {
        "features_documented_at": "prediction_time",
        "timing": {
            "prediction_instant": {"kind": instant_kind, "period": "M",
                                   "days_after_period_end": instant_lag,
                                   "citation": "publisher release calendar"},
            "features": {"period": "M", "published_days_after_period_end": lag,
                         "source_kind": source_kind},
            "row_selection": {"latest_period_used": selection, "fields": ["rate_m"]},
            "observations": observations,
        },
    }


def checks(record):
    report = gate.Report(Path("/tmp/not-a-dataset"))
    gate.check_prediction_time(record, report)
    return {result["check"]: result for result in report.results}


class TimingGateTests(unittest.TestCase):
    def test_a_feature_published_after_a_month_end_instant_is_refused(self):
        """The nhs-ae shape: features land 10 days after the period, the instant is the period end."""
        results = checks(quality(lag=10, instant_kind="period_end", instant_lag=0))
        self.assertFalse(results["timing.features_available_at_instant"]["ok"])
        self.assertFalse(results["timing.instant_accounts_for_publication_lag"]["ok"])
        self.assertIn("10", results["timing.features_available_at_instant"]["detail"])

    def test_the_same_dataset_passes_once_the_instant_is_the_publication_date(self):
        results = checks(quality(lag=10, instant_kind="publication", instant_lag=10))
        self.assertTrue(results["timing.features_available_at_instant"]["ok"])
        self.assertTrue(results["timing.instant_accounts_for_publication_lag"]["ok"])
        self.assertTrue(results["timing.instant_declared"]["ok"])

    def test_a_claim_that_features_precede_the_measured_publication_is_refused(self):
        """Understating the lag is the way to pass by lying; the observation must not be below it."""
        results = checks(quality(lag=2, instant_kind="publication", instant_lag=2,
                                 observations=[{"period": "2026-08",
                                                "period_end": "2026-08-31",
                                                "published": "2026-09-10"}]))
        self.assertEqual(10, results["timing.publication_lag_measured"]["evidence"]["measured_lag_days"])

    def test_selection_that_reaches_into_the_next_period_is_refused(self):
        results = checks(quality(lag=10, instant_kind="publication", instant_lag=10, selection="M+1"))
        self.assertFalse(results["timing.selection_uses_only_available_data"]["ok"])
        self.assertIn("M+1", results["timing.selection_uses_only_available_data"]["detail"])

    def test_selection_from_history_passes(self):
        results = checks(quality(selection="M"))
        self.assertTrue(results["timing.selection_uses_only_available_data"]["ok"])

    def test_a_statistical_release_must_show_a_measured_publication_date(self):
        results = checks(quality(observations=[]))
        self.assertFalse(results["timing.publication_lag_measured"]["ok"])

    def test_an_administrative_record_may_ship_without_one(self):
        results = checks(quality(lag=0, instant_kind="event_time", instant_lag=0,
                                 source_kind="administrative_record", observations=[]))
        self.assertTrue(results["timing.publication_lag_measured"]["ok"])

    def test_an_undeclared_timing_block_is_refused(self):
        """No declaration is not a neutral state: it is the state that shipped nhs-ae."""
        results = checks({"features_documented_at": "prediction_time"})
        self.assertFalse(results["timing.instant_declared"]["ok"])
        self.assertFalse(results["timing.features_available_at_instant"]["ok"])
        self.assertFalse(results["timing.selection_uses_only_available_data"]["ok"])


if __name__ == "__main__":
    unittest.main()
