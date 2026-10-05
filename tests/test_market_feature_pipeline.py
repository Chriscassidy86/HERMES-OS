"""
Hermes OS - Deterministic Market Feature Pipeline tests.
"""

import unittest
from datetime import datetime, timedelta, timezone

from data_providers.public_adapters import PublicCandle
from agents.market_intelligence.feature_pipeline import (
    MarketFeatures,
    build_market_features,
)


class TestMarketFeaturePipeline(unittest.TestCase):

    def _candles(self, count=60, volume=True):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        candles = []

        price = 100.0

        for index in range(count):
            close = price + (index * 0.5)
            low = close - 2.0
            high = close + 2.0
            open_price = close - 0.5

            candles.append(
                PublicCandle(
                    provider="TEST",
                    symbol="BTC/USD",
                    timeframe="4H",
                    timestamp=start + timedelta(hours=4 * index),
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=(1000.0 + index * 10.0) if volume else None,
                )
            )

        return candles

    def test_builds_complete_feature_snapshot(self):
        features = build_market_features(self._candles())

        self.assertIsInstance(features, MarketFeatures)
        self.assertEqual(features.symbol, "BTC/USD")
        self.assertEqual(features.timeframe, "4H")
        self.assertEqual(features.provider, "TEST")
        self.assertEqual(features.candle_count, 60)
        self.assertEqual(features.price, 129.5)

        self.assertIsNotNone(features.sma_10)
        self.assertIsNotNone(features.sma_20)
        self.assertIsNotNone(features.ema_12)
        self.assertIsNotNone(features.ema_26)
        self.assertIsNotNone(features.rsi_14)

        self.assertIsNotNone(features.macd_line)
        self.assertIsNotNone(features.macd_signal)
        self.assertIsNotNone(features.macd_histogram)

        self.assertIsNotNone(features.stochastic_k)
        self.assertIsNotNone(features.stochastic_d)
        self.assertIsNotNone(features.atr_14)

        self.assertIsNotNone(features.bollinger_middle)
        self.assertIsNotNone(features.bollinger_upper)
        self.assertIsNotNone(features.bollinger_lower)

        self.assertIsNotNone(features.relative_volume_20)
        self.assertIsNotNone(features.volume_spikes_20)
        self.assertIsNotNone(features.obv)

        self.assertIsNotNone(features.realized_volatility)
        self.assertIsNotNone(features.buy_volume_estimate)
        self.assertIsNotNone(features.sell_volume_estimate)

    def test_reference_high_and_low_are_deterministic(self):
        features = build_market_features(self._candles())

        self.assertEqual(features.reference_high, 131.5)
        self.assertEqual(features.reference_low, 98.0)

    def test_buy_and_sell_volume_reconcile(self):
        candles = self._candles()
        features = build_market_features(candles)

        total_volume = sum(candle.volume for candle in candles)

        self.assertAlmostEqual(
            features.buy_volume_estimate
            + features.sell_volume_estimate,
            total_volume,
            places=8,
        )

    def test_missing_volume_does_not_create_fake_volume_features(self):
        features = build_market_features(
            self._candles(volume=False)
        )

        self.assertIsNone(features.relative_volume_20)
        self.assertIsNone(features.volume_spikes_20)
        self.assertIsNone(features.obv)
        self.assertIsNone(features.buy_volume_estimate)
        self.assertIsNone(features.sell_volume_estimate)

    def test_candles_must_be_chronological(self):
        candles = self._candles()
        candles[10], candles[11] = candles[11], candles[10]

        with self.assertRaises(ValueError):
            build_market_features(candles)

    def test_mixed_symbols_are_rejected(self):
        candles = self._candles()
        candles[-1] = PublicCandle(
            provider="TEST",
            symbol="ETH/USD",
            timeframe="4H",
            timestamp=candles[-1].timestamp,
            open=candles[-1].open,
            high=candles[-1].high,
            low=candles[-1].low,
            close=candles[-1].close,
            volume=candles[-1].volume,
        )

        with self.assertRaises(ValueError):
            build_market_features(candles)

    def test_mixed_timeframes_are_rejected(self):
        candles = self._candles()
        candles[-1] = PublicCandle(
            provider="TEST",
            symbol="BTC/USD",
            timeframe="1H",
            timestamp=candles[-1].timestamp,
            open=candles[-1].open,
            high=candles[-1].high,
            low=candles[-1].low,
            close=candles[-1].close,
            volume=candles[-1].volume,
        )

        with self.assertRaises(ValueError):
            build_market_features(candles)

    def test_empty_history_is_rejected(self):
        with self.assertRaises(ValueError):
            build_market_features([])


if __name__ == "__main__":
    unittest.main()
