from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from core.briefing.executive_brief import ExecutiveBrief
from core.decision_cycle import DecisionCycle
from core.explanation import DecisionExplainer
from agents.trend.trend_specialist import TrendSpecialist
from database.journal import SQLiteAuditJournal
from reports.market_snapshot import MarketSnapshot
from services.command_center import CommandCenterService


NOW = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)


def snapshot(trend="Bullish"):
    directional = trend == "Bullish"
    return MarketSnapshot("BTC/USD", 102 if directional else 100, 1500, trend, 2, 55,
                          100, 1000, 101 if directional else 100,
                          99 if directional else 100, "4H", NOW)


class DecisionExplanationTests(unittest.TestCase):
    def test_explanation_answers_human_decision_questions(self):
        result = DecisionCycle(clock=lambda: NOW).run(snapshot())
        value = DecisionExplainer().explain(result)
        self.assertIn("BTC/USD", value.what_is_happening)
        self.assertTrue(value.why)
        self.assertTrue(value.agreeing_specialists)
        self.assertIn("Risk Manager approved", value.risk_explanation)
        self.assertTrue(value.assumptions)
        self.assertTrue(value.uncertainties)

    def test_rejection_and_ignored_evidence_are_explained(self):
        result = DecisionCycle((TrendSpecialist(),), clock=lambda: NOW).run(snapshot("Sideways"))
        value = DecisionExplainer().explain(result)
        self.assertIn("Risk Manager rejected", value.risk_explanation)
        self.assertTrue(value.uncertainties)

    def test_persisted_mapping_has_same_explanation(self):
        result = DecisionCycle(clock=lambda: NOW).run(snapshot())
        with tempfile.TemporaryDirectory() as directory:
            journal = SQLiteAuditJournal(Path(directory) / "journal.sqlite3")
            journal.initialize(); journal.save_cycle(result)
            persisted = journal.recent_cycles(1)[0]
        self.assertEqual(DecisionExplainer().explain(result), DecisionExplainer().explain(persisted))

    def test_command_center_exposes_explanation_and_summary(self):
        result = DecisionCycle(clock=lambda: NOW).run(snapshot())
        with tempfile.TemporaryDirectory() as directory:
            journal = SQLiteAuditJournal(Path(directory) / "journal.sqlite3")
            journal.initialize(); journal.save_cycle(result)
            view = CommandCenterService(journal, clock=lambda: NOW).build()
        self.assertEqual(result.cycle_id, view.decision_explanation.cycle_id)
        self.assertIn("Recommendation", view.executive_summary)

    def test_executive_brief_includes_explanation(self):
        result = DecisionCycle(clock=lambda: NOW).run(snapshot())
        explanation = DecisionExplainer().explain(result)
        text = ExecutiveBrief().create(result.evidence_summary, explanation)
        self.assertIn("Explanation", text)
        self.assertIn("Risk Manager", text)

    def test_explanation_is_immutable_and_future_time_fails(self):
        value = DecisionExplainer().explain(DecisionCycle(clock=lambda: NOW).run(snapshot()))
        with self.assertRaises(FrozenInstanceError): value.recommendation = "WAIT"
        malformed = DecisionCycle(clock=lambda: NOW).run(snapshot())
        with self.assertRaises(ValueError):
            DecisionExplainer().explain(replace(malformed, timestamp=NOW.replace(tzinfo=None)))


if __name__ == "__main__": unittest.main()
