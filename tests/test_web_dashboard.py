from datetime import datetime, timezone
from pathlib import Path
import json
import tempfile
import unittest

from core.decision_cycle import DecisionCycle
from database.journal import SQLiteAuditJournal
from reports.local_dashboard import ReadOnlyDashboardApplication
from reports.market_snapshot import MarketSnapshot
from services.command_center import CommandCenterService
from services.web_dashboard import WebDashboardService

NOW = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)


class WebDashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.journal = SQLiteAuditJournal(Path(self.tmp.name) / "db.sqlite3")
        self.journal.initialize()
        self.service = WebDashboardService(
            CommandCenterService(self.journal, clock=lambda: NOW), "V6 launch"
        )
        self.app = ReadOnlyDashboardApplication(self.service.build)

    def tearDown(self): self.tmp.cleanup()

    def populate(self, *, timestamp=NOW, source="Binance.US"):
        snapshot = MarketSnapshot(
            "BTC/USD", 102, 1500, "Bull trend", 2, 55, 100, 1000, 101, 99,
            "4H", timestamp, source, timestamp,
        )
        self.journal.save_cycle(DecisionCycle(clock=lambda: NOW).run(snapshot))

    def test_root_is_polished_html_not_raw_json(self):
        status, headers, body = self.app.handle("GET", "/")
        text = body.decode()
        self.assertEqual(200, status)
        self.assertIn("text/html", headers["content-type"])
        self.assertIn("Hermes Quant Labs", text)
        self.assertIn("PAPER MODE ONLY", text)
        self.assertIn("Why Hermes Made This Decision", text)
        self.assertNotIn("<pre>", text)
        self.assertNotIn('http-equiv="refresh"', text)

    def test_localhost_default_and_explicit_container_bridge(self):
        server = self.app.serve(port=0)
        self.assertEqual("127.0.0.1", server.server_address[0])
        server.server_close()
        with self.assertRaises(ValueError): self.app.serve("0.0.0.0", 0)
        bridged = ReadOnlyDashboardApplication(
            self.service.build, allow_container_bridge=True
        ).serve("0.0.0.0", 0)
        bridged.server_close()

    def test_stable_json_and_read_only_endpoints(self):
        first = self.app.handle("GET", "/api/dashboard")[2]
        self.assertEqual(first, self.app.handle("GET", "/api/dashboard")[2])
        self.assertEqual("PAPER", json.loads(first)["mode"])
        for path in (
            "/health", "/api/dashboard", "/api/portfolio", "/api/providers",
            "/api/trades", "/api/alerts",
        ):
            self.assertEqual(200, self.app.handle("GET", path)[0])

    def test_mutations_rejected_on_html_and_api_routes(self):
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            for path in ("/", "/api/dashboard", "/api/portfolio"):
                self.assertEqual(405, self.app.handle(method, path)[0])

    def test_no_secret_order_or_live_controls(self):
        text = self.app.handle("GET", "/")[2].decode().lower()
        self.assertNotIn("api-key", text)
        self.assertNotIn("password", text)
        self.assertNotIn("withdraw", text)
        self.assertNotIn("place order", text)
        self.assertNotIn("live trading", text)
        self.assertNotIn("<button", text)
        self.assertNotIn("<form", text)

    def test_empty_states_and_charts_are_explicit(self):
        text = self.app.handle("GET", "/")[2].decode()
        payload = json.loads(self.app.handle("GET", "/api/dashboard")[2])
        self.assertIn("No open PAPER positions", text)
        self.assertIn("No closed PAPER trades yet", text)
        self.assertIn("No PAPER history available", text)
        self.assertEqual([], payload["open_positions"])
        self.assertEqual([], payload["closed_trades"])
        self.assertEqual("WAIT", payload["risk_status"])

    def test_populated_decision_specialists_and_provider_render(self):
        self.populate()
        payload = json.loads(self.app.handle("GET", "/api/dashboard")[2])
        self.assertEqual("Binance.US", payload["active_provider"])
        self.assertTrue(payload["specialists"])
        self.assertIsNotNone(payload["explanation"])
        self.assertEqual("BTC/USD", payload["markets"][0]["symbol"])
        self.assertTrue(payload["charts"]["prices"])

    def test_stale_provider_failure_and_risk_rejection_labels(self):
        stale = {"final_status": "REJECTED_INVALID_EVIDENCE", "rejection_reasons": ("Snapshot market data is stale.",)}
        failure = {"final_status": "REJECTED_INVALID_EVIDENCE", "rejection_reasons": ("Provider unavailable.",)}
        rejected = {"final_status": "REJECTED_BY_RISK", "recommendation": {"action": "LONG"}, "risk_assessment": {"approved": False}}
        self.assertEqual("DATA STALE", self.service._risk_status(stale))
        self.assertEqual("PROVIDER FAILURE", self.service._risk_status(failure))
        self.assertEqual("REJECTED", self.service._risk_status(rejected))

    def test_auto_refresh_retains_last_display_on_failure(self):
        text = self.app.handle("GET", "/")[2].decode()
        self.assertIn('fetch("/api/dashboard"', text)
        self.assertIn("setInterval(refresh,REFRESH_SECONDS*1000)", text)
        self.assertIn("Retaining the last known display", text)
        self.assertIn("catch(error)", text)

    def test_business_logic_remains_outside_renderer(self):
        self.assertFalse(hasattr(self.app.web_renderer, "command_center"))
        self.assertEqual((), self.service.build().actions)


if __name__ == "__main__": unittest.main()
