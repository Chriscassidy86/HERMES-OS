from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
import unittest

from core.regime import MarketRegimeEngine
from models.market_regime import InsufficientRegimeEvidence, MarketRegime, RegimeInputs


NOW = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)
BASE = RegimeInputs("BTC/USD", 100, 100, 100, 100, 1000, 1000, 2, 2, 110, 90, 0.5, NOW)


class MarketRegimeEngineTests(unittest.TestCase):
    def classify(self, **changes): return MarketRegimeEngine().classify(replace(BASE, **changes))

    def test_breakout_and_breakdown(self):
        self.assertEqual(MarketRegime.BREAKOUT, self.classify(price=112, volume=1300).regime)
        self.assertEqual(MarketRegime.BREAKDOWN, self.classify(price=88, volume=1300).regime)

    def test_high_and_low_volatility(self):
        self.assertEqual(MarketRegime.HIGH_VOLATILITY, self.classify(volatility=3.2).regime)
        self.assertEqual(MarketRegime.LOW_VOLATILITY, self.classify(volatility=1.0).regime)

    def test_accumulation_and_distribution(self):
        self.assertEqual(MarketRegime.ACCUMULATION, self.classify(volume=1300, buy_volume_ratio=0.65).regime)
        self.assertEqual(MarketRegime.DISTRIBUTION, self.classify(volume=1300, buy_volume_ratio=0.35).regime)

    def test_bull_and_bear_trend(self):
        self.assertEqual(MarketRegime.BULL_TREND,
                         self.classify(price=106, previous_price=104, short_moving_average=104,
                                       long_moving_average=100).regime)
        self.assertEqual(MarketRegime.BEAR_TREND,
                         self.classify(price=94, previous_price=96, short_moving_average=96,
                                       long_moving_average=100).regime)

    def test_sideways_and_transition(self):
        self.assertEqual(MarketRegime.SIDEWAYS, self.classify(price=100.5).regime)
        self.assertEqual(MarketRegime.TRANSITION,
                         self.classify(price=103, previous_price=100, short_moving_average=100.8,
                                       long_moving_average=100).regime)

    def test_result_is_explainable_and_immutable(self):
        result = self.classify(price=112, volume=1300)
        self.assertTrue(result.evidence); self.assertTrue(result.explanation)
        self.assertTrue(result.uncertainty); self.assertGreaterEqual(result.confidence, 50)
        with self.assertRaises(FrozenInstanceError): result.confidence = 0

    def test_insufficient_malformed_or_contradictory_evidence_fails_closed(self):
        for changes in ({"average_volume": 0}, {"volatility": float("nan")},
                        {"reference_high": 80}, {"buy_volume_ratio": 1.1}):
            with self.subTest(changes=changes), self.assertRaises(InsufficientRegimeEvidence):
                self.classify(**changes)


if __name__ == "__main__": unittest.main()
