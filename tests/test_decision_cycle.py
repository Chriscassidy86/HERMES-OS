"""Tests for the Foundation IV.1 paper-only decision cycle."""

from datetime import datetime, timezone
import unittest
from math import inf

from agents.base.base_specialist import BaseSpecialist
from agents.trend.trend_specialist import TrendSpecialist
from core.decision_cycle import DecisionCycle
from core.risk.risk_manager import RiskManager
from models.recommendation import Recommendation
from models.signal import Signal
from reports.market_snapshot import MarketSnapshot


FIXED_TIME = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)


def snapshot(trend: str) -> MarketSnapshot:
    return MarketSnapshot(
        symbol="BTC/USD", price=108_000.25, volume_24h=42_500_000_000,
        market_trend=trend, volatility=2.8, fear_greed_index=74,
        timestamp=FIXED_TIME,
    )


class MalformedSpecialist(BaseSpecialist):
    def __init__(self) -> None:
        super().__init__("Malformed Specialist")

    def analyze(self, snapshot):
        return "not a report and signal tuple"


class LowConfidenceSpecialist(BaseSpecialist):
    def __init__(self) -> None:
        super().__init__("Momentum Specialist")

    def analyze(self, snapshot):
        return (
            self.create_report("BULLISH", 60.0, ["Weak trend"], [], "CAUTION"),
            Signal(self.name, "LONG", 60.0, 0.55, "4H", 3, FIXED_TIME, ("Weak trend",)),
        )


class DecisionCycleTests(unittest.TestCase):
    def test_risk_manager_rejects_invalid_recommendations(self):
        manager = RiskManager()
        for action, confidence in (("WAIT", 100), ("TRANSFER", 100), ("LONG", inf)):
            with self.subTest(action=action, confidence=confidence):
                assessment = manager.evaluate(
                    Recommendation("BTC/USD", action, confidence, "test")
                )
                self.assertFalse(assessment.approved)
                self.assertEqual(0.0, assessment.max_position_size)

    def cycle(self, specialists) -> DecisionCycle:
        return DecisionCycle(specialists, clock=lambda: FIXED_TIME)

    def test_bullish_cycle_is_paper_eligible(self):
        result = self.cycle([TrendSpecialist()]).run(snapshot("Bullish"))
        self.assertEqual("LONG", result.recommendation.action)
        self.assertEqual("PAPER_EXECUTION_ELIGIBLE", result.final_status)
        self.assertTrue(result.paper_execution_eligible)
        self.assertEqual((), result.rejection_reasons)

    def test_bearish_cycle_is_paper_eligible(self):
        result = self.cycle([TrendSpecialist()]).run(snapshot("Bearish"))
        self.assertEqual("SHORT", result.recommendation.action)
        self.assertTrue(result.paper_execution_eligible)

    def test_neutral_cycle_fails_closed(self):
        result = self.cycle([TrendSpecialist()]).run(snapshot("Sideways"))
        self.assertEqual("WAIT", result.recommendation.action)
        self.assertEqual("REJECTED_BY_RISK", result.final_status)
        self.assertFalse(result.paper_execution_eligible)

    def test_malformed_specialist_result_fails_closed(self):
        result = self.cycle([MalformedSpecialist()]).run(snapshot("Bullish"))
        self.assertEqual("REJECTED_INVALID_EVIDENCE", result.final_status)
        self.assertFalse(result.paper_execution_eligible)
        self.assertIn("expected an (AgentReport, Signal) tuple", result.rejection_reasons[0])

    def test_empty_signals_fail_closed(self):
        result = self.cycle([]).run(snapshot("Bullish"))
        self.assertEqual(0, result.decision_packet.signal_count())
        self.assertEqual("REJECTED_INVALID_EVIDENCE", result.final_status)
        self.assertFalse(result.paper_execution_eligible)

    def test_risk_rejection_prevents_eligibility(self):
        result = self.cycle([LowConfidenceSpecialist()]).run(snapshot("Bullish"))
        self.assertFalse(result.risk_assessment.approved)
        self.assertFalse(result.paper_execution_eligible)
        self.assertEqual("REJECTED_BY_RISK", result.final_status)

    def test_fixed_clock_produces_reproducible_result(self):
        first = self.cycle([TrendSpecialist()]).run(snapshot("Bullish"))
        second = self.cycle([TrendSpecialist()]).run(snapshot("Bullish"))
        self.assertEqual(first, second)
        self.assertEqual("BTC-USD-20260711T120000Z", first.cycle_id)


if __name__ == "__main__":
    unittest.main()
