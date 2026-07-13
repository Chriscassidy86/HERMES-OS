from datetime import datetime, timedelta, timezone
import unittest

from services.operator_workflow import (
    DailyOperatorWorkflow,
    FutureNotificationAdapter,
    LocalAlertManager,
    OperationalAlertDetector,
)


NOW = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)


class OperatorWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.manager = LocalAlertManager(); self.detector = OperationalAlertDetector()

    def test_alert_creation_is_local_and_utc(self):
        alert = self.manager.create(category="TEST", severity="INFO", message="Test", created_at=NOW)
        self.assertTrue(alert.local_only); self.assertEqual(timezone.utc, alert.created_at.tzinfo)

    def test_duplicate_suppression(self):
        first = self.manager.create(category="TEST", severity="INFO", message="Test", created_at=NOW)
        second = self.manager.create(category="TEST", severity="INFO", message="Test", created_at=NOW + timedelta(seconds=1))
        self.assertIs(first, second); self.assertEqual(1, len(self.manager.alerts()))

    def test_acknowledgement(self):
        alert = self.manager.create(category="TEST", severity="INFO", message="Test", created_at=NOW)
        self.assertTrue(self.manager.acknowledge(alert.alert_id, acknowledged_at=NOW).acknowledged)

    def test_severity_ordering(self):
        for severity in ("INFO", "CRITICAL", "WARNING", "HIGH"):
            self.manager.create(category=severity, severity=severity, message=severity, created_at=NOW)
        self.assertEqual(("CRITICAL", "HIGH", "WARNING", "INFO"), tuple(item.severity for item in self.manager.alerts()))

    def test_stale_data_alert(self):
        self.assertEqual("STALE_MARKET_DATA", self.detector.evaluate({"market_data_stale": True}, observed_at=NOW, manager=self.manager)[0].category)

    def test_provider_alert(self):
        self.assertEqual("PROVIDER_UNAVAILABLE", self.detector.evaluate({"provider_unavailable": True}, observed_at=NOW, manager=self.manager)[0].category)

    def test_drawdown_alert(self):
        self.assertEqual("UNUSUAL_DRAWDOWN", self.detector.evaluate({"unusual_drawdown": True}, observed_at=NOW, manager=self.manager)[0].category)

    def test_backup_alert(self):
        categories = tuple(item.category for item in self.detector.evaluate({"backup_rejected": True, "restore_verification_failed": True}, observed_at=NOW, manager=self.manager))
        self.assertEqual(("BACKUP_REJECTED", "RESTORE_VERIFICATION_FAILED"), categories)

    def test_workflow_completion(self):
        workflow = DailyOperatorWorkflow()
        for number in range(1, 13): workflow.complete(number, completed_at=NOW)
        self.assertTrue(workflow.report().complete)

    def test_missing_step_detection(self):
        report = DailyOperatorWorkflow().complete(1, completed_at=NOW)
        self.assertEqual(11, len(report.missing_steps)); self.assertFalse(report.complete)

    def test_no_live_action_or_external_delivery(self):
        report = DailyOperatorWorkflow().report()
        self.assertEqual("PAPER", report.mode); self.assertFalse(report.live_actions_available)
        with self.assertRaises(RuntimeError): FutureNotificationAdapter().send(None)


if __name__ == "__main__": unittest.main()
