from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
import unittest

from agents.learning import LearningExplanationEngine
from models.performance import SpecialistPrediction, TradeOutcome


NOW = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)


def outcome(trade_id="PT-1", entry=100, exit=110, fees=1, predictions=()):
    return TradeOutcome(trade_id, "BTC/USD", "LONG", entry, exit, 1, fees, NOW, NOW, predictions)


class LearningExplanationTests(unittest.TestCase):
    def test_success_explains_why_trade_worked(self):
        report = LearningExplanationEngine().explain((outcome(),))
        self.assertEqual("SUCCESS", report.trades[0].outcome)
        self.assertIn("supported", report.trades[0].why[0])

    def test_loss_explains_price_failure(self):
        report = LearningExplanationEngine().explain((outcome(exit=90),))
        self.assertEqual("LOSS", report.trades[0].outcome)
        self.assertIn("opposed", report.trades[0].why[0])

    def test_correct_incorrect_specialists_and_calibration(self):
        predictions = (SpecialistPrediction("Trend", "LONG", 80),
                       SpecialistPrediction("Momentum", "SHORT", 70))
        trade = LearningExplanationEngine().explain((outcome(predictions=predictions),)).trades[0]
        self.assertEqual(("Trend",), trade.correct_specialists)
        self.assertEqual(("Momentum",), trade.incorrect_specialists)
        self.assertGreater(trade.specialist_details[1].calibration_error, 0)

    def test_recurring_mistakes_require_repetition(self):
        prediction = (SpecialistPrediction("Trend", "LONG", 90),)
        report = LearningExplanationEngine().explain((
            outcome("PT-1", exit=90, predictions=prediction),
            outcome("PT-2", exit=80, predictions=prediction),
        ))
        patterns = {item.pattern for item in report.recurring_mistakes}
        self.assertIn("POSITION_OPPOSED_REALIZED_MOVE", patterns)
        self.assertIn("OVERCONFIDENT_INCORRECT_SPECIALIST", patterns)

    def test_report_never_modifies_configuration(self):
        report = LearningExplanationEngine().explain((outcome(),))
        self.assertFalse(report.configuration_modified)
        self.assertTrue(report.human_review_required)
        with self.assertRaises(FrozenInstanceError): report.sample_size = 0

    def test_empty_malformed_or_nonfinite_outcomes_fail_closed(self):
        with self.assertRaises(ValueError): LearningExplanationEngine().explain(())
        for value in (replace(outcome(), entry_price=0), replace(outcome(), fees=float("nan")),
                      replace(outcome(), direction="TRANSFER")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                LearningExplanationEngine().explain((value,))


if __name__ == "__main__": unittest.main()
