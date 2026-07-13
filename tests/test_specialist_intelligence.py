from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import unittest

from agents.liquidity import LiquiditySpecialist
from agents.portfolio import PortfolioContextSpecialist
from agents.probability import ProbabilitySpecialist
from models.specialist_intelligence import (
    LiquidityInputs,
    PortfolioContextInputs,
    ProbabilityInputs,
)


NOW = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)


class SpecialistIntelligenceTests(unittest.TestCase):
    def test_liquidity_assessment_is_explainable_and_advisory(self):
        result = LiquiditySpecialist().analyze(
            LiquidityInputs("BTC/USD", 99.9, 100.1, 1200.0, 800.0, NOW)
        )
        self.assertEqual("HEALTHY", result.status)
        self.assertTrue(result.advisory_only)
        self.assertIn("spread", result.facts[0].lower())

    def test_crossed_or_empty_liquidity_fails_closed(self):
        with self.assertRaises(ValueError):
            LiquiditySpecialist().analyze(
                LiquidityInputs("BTC/USD", 101.0, 100.0, 0.0, 0.0, NOW)
            )

    def test_probability_is_bounded_and_not_a_profitability_claim(self):
        result = ProbabilitySpecialist().analyze(
            ProbabilityInputs("BTC/USD", 4, 1, 1, 80.0, NOW)
        )
        self.assertEqual(0.74, result.score)
        self.assertIn("not a calibrated forecast", result.warnings[0])

    def test_probability_rejects_missing_and_malformed_evidence(self):
        with self.assertRaises(ValueError):
            ProbabilitySpecialist().analyze(
                ProbabilityInputs("BTC/USD", 0, 0, 0, 80.0, NOW)
            )
        with self.assertRaises(ValueError):
            ProbabilitySpecialist().analyze(
                ProbabilityInputs("BTC/USD", 1, 0, 0, float("nan"), NOW)
            )

    def test_portfolio_context_reports_concentration_without_mutation(self):
        inputs = PortfolioContextInputs("BTC/USD", 2000.0, 10000.0, 8000.0, 3000.0, 2, NOW)
        result = PortfolioContextSpecialist().analyze(inputs)
        self.assertEqual("CONSTRAINED", result.status)
        self.assertEqual(2, len(result.warnings))
        with self.assertRaises(FrozenInstanceError):
            inputs.cash = 0.0

    def test_portfolio_context_rejects_contradictory_accounting(self):
        with self.assertRaises(ValueError):
            PortfolioContextSpecialist().analyze(
                PortfolioContextInputs("BTC/USD", 100.0, 1000.0, 200.0, 300.0, 1, NOW)
            )


if __name__ == "__main__":
    unittest.main()
