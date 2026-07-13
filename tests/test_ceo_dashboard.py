from datetime import datetime, timezone
from pathlib import Path
import json
import tempfile
import unittest

from core.decision_cycle import DecisionCycle
from database.journal import SQLiteAuditJournal
from reports.ceo_dashboard import CEODashboardRenderer
from reports.market_snapshot import MarketSnapshot
from services.ceo_dashboard import CEODashboardService
from services.command_center import CommandCenterService


NOW = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)


class CEODashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.journal = SQLiteAuditJournal(Path(self.temp.name) / "dashboard.sqlite3")
        self.journal.initialize()

    def tearDown(self): self.temp.cleanup()

    def service(self):
        return CEODashboardService(CommandCenterService(self.journal, clock=lambda: NOW))

    def populate(self):
        snapshot = MarketSnapshot("BTC/USD", 102, 1500, "Bullish", 2, 55,
                                  100, 1000, 101, 99, "4H", NOW)
        self.journal.save_cycle(DecisionCycle(clock=lambda: NOW).run(snapshot))

    def test_empty_dashboard_displays_all_safe_operational_sections(self):
        view = self.service().build()
        self.assertEqual("PAPER MODE ONLY", view.banner)
        self.assertEqual("WAIT", view.current_recommendation)
        self.assertEqual("REJECTED", view.risk_manager_decision)
        self.assertEqual((), view.actions)
        self.assertEqual((), view.experiment_status)

    def test_populated_dashboard_contains_decision_risk_and_explanation(self):
        self.populate(); view = self.service().build()
        self.assertEqual("LONG", view.current_recommendation)
        self.assertEqual("APPROVED", view.risk_manager_decision)
        self.assertGreater(view.confidence, 0)
        self.assertIsNotNone(view.decision_explanation)
        self.assertTrue(view.specialists)

    def test_learning_recommendations_require_human_notice_upstream(self):
        recommendation = ({"rule": "specialist weight", "human_approval_required": True},)
        view = self.service().build(learning_recommendations=recommendation)
        self.assertEqual(recommendation, view.learning_recommendations)
        self.assertEqual((), view.actions)

    def test_renderer_is_serialization_only_and_json_safe(self):
        self.populate(); view = self.service().build()
        payload = json.loads(CEODashboardRenderer().to_json(view))
        self.assertEqual("PAPER MODE ONLY", payload["banner"])
        self.assertNotIn("place_order", payload)
        self.assertEqual([], payload["actions"])

    def test_unhealthy_database_is_visible(self):
        class BrokenJournal:
            def validate_schema(self): raise OSError("unavailable")
        view = CEODashboardService(CommandCenterService(BrokenJournal(), clock=lambda: NOW)).build()
        self.assertEqual("UNHEALTHY", view.system_health)
        self.assertIn("UNHEALTHY", view.database_health)

    def test_renderer_rejects_non_view_input(self):
        with self.assertRaises(ValueError): CEODashboardRenderer().to_dict({})


if __name__ == "__main__": unittest.main()
