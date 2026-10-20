"""The dashboard must not flatter the pipeline it reports on.

Three rules are load-bearing and are tested here: a missing input renders "no data"
rather than zero, an aged panel is labelled stale rather than healthy, and a
credential can never reach a published page.
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_dashboard", ROOT / "scripts/build-dashboard.py")
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)


class PanelTests(unittest.TestCase):
    def test_a_missing_value_is_no_data_not_zero(self):
        p = dashboard.panel(None, "release/*/MANIFEST.json", "2026-10-20T10:00:00+00:00")
        self.assertEqual("no data", p["status"])
        self.assertIsNone(p["value"])

    def test_an_aged_value_is_stale(self):
        p = dashboard.panel(4, "release/*/MANIFEST.json", "2026-01-01T00:00:00+00:00",
                            stale_after_minutes=60)
        self.assertTrue(p["stale"])
        self.assertEqual("stale", p["status"])

    def test_a_fresh_value_is_ok(self):
        p = dashboard.panel(4, "release/*/MANIFEST.json", dashboard.iso(dashboard.now()),
                            stale_after_minutes=60)
        self.assertFalse(p["stale"])
        self.assertEqual("ok", p["status"])


class SecretTests(unittest.TestCase):
    def test_a_token_in_a_page_aborts_the_build(self):
        """Byte-level guard: if a secret ever reaches a page, nothing is written."""
        secret = (dashboard.SECRETS / "github-publish.token")
        if not secret.is_file():
            self.skipTest("no credential present to test with")
        leaked = secret.read_text().strip()
        with self.assertRaises(SystemExit) as caught:
            dashboard.assert_no_secrets({"index.html": f"<p>{leaked}</p>"})
        self.assertIn("refusing to publish", str(caught.exception))

    def test_a_page_of_ordinary_numbers_passes(self):
        dashboard.assert_no_secrets({"index.html": "<p>354 tests, 4 releases, 1.94M tokens</p>"})


class RenderTests(unittest.TestCase):
    def snapshot(self):
        return {
            "schema": dashboard.SNAPSHOT_SCHEMA,
            "generated_at": "2026-10-20T10:00:00+00:00",
            "candidates": {"records": [], "counts": {}, "live": [], "errors": [],
                           "countries": {}, "non_us_share": None},
            "coverage": {"live": 0, "live_non_us": 0, "live_non_us_share": 0.0},
            "releases": {"releases": [], "errors": []},
            "budget": {"decision": {}, "config": {}},
            "cron": {"jobs": [], "updated_at": None},
            "health": {"tests": None, "checks": None, "coverage": None, "head": None, "ci": None},
        }

    def test_an_unmeasured_value_is_no_data_while_a_true_zero_is_zero(self):
        """Zero live candidates is a fact; an unread budget is not the same thing."""
        body = dashboard.render_exec(self.snapshot())
        self.assertIn("no data", body)
        self.assertIn('<div class="k">Live candidates</div><div class="v">0</div>', body)

    def test_an_empty_table_says_so_instead_of_rendering_blank(self):
        body = dashboard.render_exec(self.snapshot())
        self.assertIn("no candidate records", body)
        self.assertIn("no releases recorded", body)
        self.assertIn("nothing queued", body)

    def test_a_failed_ci_run_becomes_an_alarm(self):
        snapshot = self.snapshot()
        snapshot["health"]["ci"] = {"conclusion": "failure", "head_sha": "abc1234"}
        body = dashboard.render_exec(snapshot)
        self.assertIn("concluded failure", body)


class BuildTests(unittest.TestCase):
    def test_build_writes_the_three_p0_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, out = dashboard.build(Path(tmp), include_tests=False)
            for name in ("index.html", "cost.html", "reliability.html", "style.css",
                         "dashboard.json"):
                self.assertTrue((out / name).is_file(), name)
            self.assertEqual(dashboard.SNAPSHOT_SCHEMA, snapshot["schema"])


if __name__ == "__main__":
    unittest.main()
