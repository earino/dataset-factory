"""The dashboard must not flatter the pipeline it reports on.

Load-bearing rules tested here: a missing input renders "no data" rather than zero,
an unmeasured suite is not called a failing one, a single history point is not drawn
as a trend, and a credential can never reach a published page.
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_dashboard", ROOT / "scripts/build-dashboard.py")
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)
ui = dashboard.ui


def snapshot(**overrides):
    base = {
        "schema": dashboard.SNAPSHOT_SCHEMA,
        "generated_at": "2026-10-20T10:00:00+00:00",
        "candidates": {"records": [], "counts": {}, "live": [], "errors": [],
                       "countries": {}, "non_us_share": None},
        "coverage": {"live": 0, "live_non_us": 0, "live_non_us_share": 0.0, "by_country": {}},
        "releases": {"releases": [], "errors": []},
        "budget": {"decision": {}, "config": {}},
        "cron": {"jobs": [], "updated_at": None},
        "health": {"tests": None, "checks": None, "coverage": None, "head": None, "ci": None},
        "history": [],
    }
    base.update(overrides)
    return base


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


class HonestyTests(unittest.TestCase):
    def test_an_unmeasured_suite_is_not_called_a_failure(self):
        html = ui.render_ops(snapshot(), [], [])
        self.assertIn("not run", html)
        self.assertIn("Gates not fully measured", html)

    def test_a_failing_suite_is_called_a_failure(self):
        bad = snapshot(health={"tests": {"ok": False, "count": "354"},
                               "checks": {"ok": True, "passing": 28},
                               "coverage": {"ok": True, "summary": "ok"},
                               "head": None, "ci": {"conclusion": "success"}})
        html = ui.render_ops(bad, [], [])
        self.assertIn("A gate is failing", html)

    def test_a_single_history_point_is_not_drawn_as_a_trend(self):
        svg = ui.sparkline([4])
        self.assertIn("series begins today", svg)
        self.assertNotIn("<polyline", svg)

    def test_two_points_draw_a_line(self):
        self.assertIn("<polyline", ui.sparkline([4, 5]))

    def test_the_gauge_clamps_out_of_range_input(self):
        self.assertIn("100.0%", ui.gauge(140, "x"))
        self.assertIn("0.0%", ui.gauge(-3, "x"))

    def test_an_empty_pipeline_renders_zero_when_zero_is_the_truth(self):
        html = ui.render_overview(snapshot(), [], [])
        self.assertIn("no data", html)
        self.assertIn("0 datasets shipped", html)


class ChromeTests(unittest.TestCase):
    def test_deltas_are_human_readable(self):
        self.assertEqual("12m", ui.humanize(12))
        self.assertEqual("1.2d", ui.humanize(1697))
        self.assertEqual("90d", ui.humanize(129_762))
        self.assertEqual("just now", ui.humanize(0))

    def test_every_page_has_a_bottom_nav_and_a_viewport(self):
        for render in (ui.render_overview, ui.render_ops, ui.render_cost):
            html = ui.page("x", "exec", "2026-10-20T10:00:00+00:00", render(snapshot(), [], []))
            self.assertIn("viewport-fit=cover", html)
            self.assertIn("bottomnav", html)
            self.assertIn("noindex", html)


class ResourceTests(unittest.TestCase):
    """Worker spend is server lifetime x the rate recorded at launch."""

    def ledger(self, root):
        (root / "config").mkdir(parents=True)
        (root / "config" / "local.json").write_text('{"monthly_budget_eur": 20}')
        (root / "jobs").mkdir()
        jobs = {
            "a": {"created_at": "2026-10-02T00:00:00+00:00", "deleted_at": "2026-10-02T02:00:00+00:00",
                  "provider_hourly_eur": "0.06924", "status": "deleted",
                  "job": {"id": "a", "server_type": "cpx32", "location": "hel1"}},
            "b": {"created_at": "2026-10-03T00:00:00+00:00", "deleted_at": "2026-10-03T01:00:00+00:00",
                  "provider_hourly_eur": "0.1", "status": "deleted",
                  "job": {"id": "b", "server_type": "cpx42", "location": "hel1"}},
            "c": {"created_at": "2026-10-04T00:00:00+00:00", "provider_hourly_eur": "0.1",
                  "status": "provisioning", "job": {"id": "c"}},
        }
        for name, record in jobs.items():
            import json as _json
            (root / "jobs" / f"{name}.json").write_text(_json.dumps(record))

    def test_lifetime_and_month_costs_come_from_recorded_intervals(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.ledger(root)
            with mock.patch.object(dashboard, "ROOT", root):
                res = dashboard.collect_resources(published_count=4)
        self.assertAlmostEqual(0.24, res["month_to_date"], places=2)
        self.assertAlmostEqual(0.24, res["lifetime_eur"], places=2)
        self.assertEqual(2, res["jobs_this_month"])
        self.assertAlmostEqual(3.0, res["month_hours"], places=1)
        self.assertEqual(3, res["jobs_total"])
        self.assertAlmostEqual(0.06, res["eur_per_release"], places=2)
        unfinished = [j for j in res["jobs"] if j["id"] == "c"][0]
        self.assertIsNone(unfinished["eur"])

    def test_missing_provider_inventory_is_no_data_not_zero(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.ledger(root)
            with mock.patch.object(dashboard, "ROOT", root):
                res = dashboard.collect_resources()
        self.assertIsNone(res["live"]["servers"])
        html = ui.render_resources({"resources": res, "generated_at": "2026-10-20T10:00:00+00:00"}, [], [])
        self.assertIn("no data", html)


class BuildTests(unittest.TestCase):
    def test_build_writes_pages_and_a_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap, out = dashboard.build(Path(tmp), include_tests=False)
            for name in ("index.html", "cost.html", "reliability.html", "style.css",
                         "dashboard.json", "history.json", "robots.txt"):
                self.assertTrue((out / name).is_file(), name)
            self.assertEqual(dashboard.SNAPSHOT_SCHEMA, snap["schema"])
            self.assertTrue(snap["history"])

    def test_history_does_not_grow_on_every_rebuild(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            dashboard.build(out, include_tests=False)
            first = len(dashboard.read_json(out / "history.json"))
            dashboard.build(out, include_tests=False)
            self.assertEqual(first, len(dashboard.read_json(out / "history.json")))


if __name__ == "__main__":
    unittest.main()
