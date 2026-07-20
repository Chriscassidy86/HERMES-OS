"""
Unit tests for the Market Intelligence specialists (Phase 2).

Verifies:
  - Trend Specialist produces advisory-only reports with EMA/SMA/swing evidence
  - Momentum Specialist produces advisory-only reports with RSI/MACD/Stochastic
  - Volume Specialist produces advisory-only reports with rvol/spikes/OBV
  - Volatility Specialist produces advisory-only reports with ATR/Bollinger/regime
  - All specialists reject invalid inputs
  - All specialists handle insufficient data gracefully
  - All reports are deterministic and immutable
  - No specialist produces buy/sell directives
"""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import unittest

from agents.market_intelligence.momentum_specialist import MomentumSpecialist
from agents.market_intelligence.trend_specialist import TrendSpecialist
from agents.market_intelligence.volatility_specialist import (
    VolatilitySpecialist,
)
from agents.market_intelligence.volume_specialist import VolumeSpecialist
from models.market_intelligence import (
    Candle,
    MarketIntelligenceReport,
    MomentumInputs,
    TrendInputs,
    VolatilityInputs,
    VolumeInputs,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

NOW = datetime(2026, 7, 13, 12, 0, 0, tzinfo=timezone.utc)
FRESH = NOW - timedelta(minutes=5)


def _make_candle(
    offset_minutes: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: float,
) -> Candle:
    """Create a candle at NOW - offset_minutes."""
    ts = NOW - timedelta(minutes=offset_minutes)
    return Candle(
        timestamp=ts,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def _bullish_candles(n: int = 30) -> tuple[Candle, ...]:
    """Generate a deterministic bullish series of n candles."""
    candles: list[Candle] = []
    base = 100.0
    for i in range(n):
        close = base + i * 1.5
        open_ = close - 0.5
        high = close + 0.8
        low = open_ - 0.8
        volume = 1000.0 + i * 10
        candles.append(
            _make_candle(
                offset_minutes=(n - i) * 60,
                open_=open_,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )
    return tuple(candles)


def _bearish_candles(n: int = 30) -> tuple[Candle, ...]:
    """Generate a deterministic bearish series of n candles."""
    candles: list[Candle] = []
    base = 200.0
    for i in range(n):
        close = base - i * 1.5
        open_ = close + 0.5
        high = open_ + 0.8
        low = close - 0.8
        volume = 1000.0 + i * 10
        candles.append(
            _make_candle(
                offset_minutes=(n - i) * 60,
                open_=open_,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )
    return tuple(candles)


def _high_volatility_candles(n: int = 30) -> tuple[Candle, ...]:
    """Generate a deterministic high-volatility series of n candles."""
    candles: list[Candle] = []
    base = 100.0
    for i in range(n):
        close = base + (i % 2) * 10 - 5
        open_ = base + ((i + 1) % 2) * 10 - 5
        high = max(open_, close) + 5
        low = min(open_, close) - 5
        volume = 2000.0
        candles.append(
            _make_candle(
                offset_minutes=(n - i) * 60,
                open_=open_,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )
    return tuple(candles)


def _low_volatility_candles(n: int = 30) -> tuple[Candle, ...]:
    """Generate a deterministic low-volatility series of n candles."""
    candles: list[Candle] = []
    base = 100.0
    for i in range(n):
        close = base + i * 0.05
        open_ = close - 0.02
        high = close + 0.03
        low = open_ - 0.03
        volume = 500.0
        candles.append(
            _make_candle(
                offset_minutes=(n - i) * 60,
                open_=open_,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )
    return tuple(candles)


def _volume_spike_candles(n: int = 40) -> tuple[Candle, ...]:
    """Generate candles with volume spikes in the recent window."""
    candles: list[Candle] = []
    base = 100.0
    for i in range(n):
        close = base + i * 0.5
        open_ = close - 0.2
        high = close + 0.3
        low = open_ - 0.3
        if i >= n - 5:
            volume = 5000.0
        else:
            volume = 1000.0
        candles.append(
            _make_candle(
                offset_minutes=(n - i) * 60,
                open_=open_,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )
    return tuple(candles)


# ---------------------------------------------------------------------------
# Trend Specialist tests
# ---------------------------------------------------------------------------


class TrendSpecialistTests(unittest.TestCase):
    def setUp(self):
        self.specialist = TrendSpecialist()

    def test_produces_advisory_report(self):
        inputs = TrendInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        report = self.specialist.analyze(inputs)
        self.assertIsInstance(report, MarketIntelligenceReport)
        self.assertTrue(report.advisory_only)
        self.assertEqual(report.agent_name, "Trend Intelligence Specialist")
        self.assertEqual(report.symbol, "BTC/USD")
        self.assertEqual(report.timeframe, "4H")

    def test_bullish_candles_produce_bullish_evidence(self):
        inputs = TrendInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        report = self.specialist.analyze(inputs)
        joined = " ".join(report.evidence).lower()
        self.assertIn("above", joined)

    def test_bearish_candles_produce_bearish_evidence(self):
        inputs = TrendInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bearish_candles(),
        )
        report = self.specialist.analyze(inputs)
        joined = " ".join(report.evidence).lower()
        self.assertIn("below", joined)

    def test_confidence_is_bounded(self):
        inputs = TrendInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        report = self.specialist.analyze(inputs)
        self.assertGreaterEqual(report.confidence, 0.0)
        self.assertLessEqual(report.confidence, 1.0)

    def test_insufficient_data_handled_gracefully(self):
        single = _make_candle(60, 100.0, 101.0, 99.0, 100.5, 1000.0)
        inputs = TrendInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=(single,),
        )
        report = self.specialist.analyze(inputs)
        self.assertTrue(report.advisory_only)
        self.assertGreater(len(report.warnings), 0)

    def test_rejects_wrong_input_type(self):
        with self.assertRaises(ValueError):
            self.specialist.analyze("not inputs")

    def test_report_is_immutable(self):
        inputs = TrendInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        report = self.specialist.analyze(inputs)
        with self.assertRaises(FrozenInstanceError):
            report.confidence = 0.99

    def test_no_buy_sell_directives(self):
        inputs = TrendInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        report = self.specialist.analyze(inputs)
        text = report.to_json().lower()
        for forbidden in ("buy", "sell", "order", "execute", "trade"):
            self.assertNotIn(forbidden, text)

    def test_deterministic_serialization(self):
        inputs = TrendInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        r1 = self.specialist.analyze(inputs)
        r2 = self.specialist.analyze(inputs)
        self.assertEqual(r1.to_json(), r2.to_json())


# ---------------------------------------------------------------------------
# Momentum Specialist tests
# ---------------------------------------------------------------------------


class MomentumSpecialistTests(unittest.TestCase):
    def setUp(self):
        self.specialist = MomentumSpecialist()

    def test_produces_advisory_report(self):
        inputs = MomentumInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        report = self.specialist.analyze(inputs)
        self.assertIsInstance(report, MarketIntelligenceReport)
        self.assertTrue(report.advisory_only)
        self.assertEqual(report.agent_name, "Momentum Intelligence Specialist")

    def test_bullish_candles_produce_momentum_evidence(self):
        inputs = MomentumInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        report = self.specialist.analyze(inputs)
        joined = " ".join(report.evidence).lower()
        self.assertTrue(
            "rsi" in joined or "macd" in joined or "stochastic" in joined
        )

    def test_confidence_is_bounded(self):
        inputs = MomentumInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        report = self.specialist.analyze(inputs)
        self.assertGreaterEqual(report.confidence, 0.0)
        self.assertLessEqual(report.confidence, 1.0)

    def test_insufficient_data_handled_gracefully(self):
        single = _make_candle(60, 100.0, 101.0, 99.0, 100.5, 1000.0)
        inputs = MomentumInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=(single,),
        )
        report = self.specialist.analyze(inputs)
        self.assertTrue(report.advisory_only)
        self.assertGreater(len(report.warnings), 0)

    def test_rejects_wrong_input_type(self):
        with self.assertRaises(ValueError):
            self.specialist.analyze(42)

    def test_report_is_immutable(self):
        inputs = MomentumInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        report = self.specialist.analyze(inputs)
        with self.assertRaises(FrozenInstanceError):
            report.confidence = 0.99

    def test_no_buy_sell_directives(self):
        inputs = MomentumInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        report = self.specialist.analyze(inputs)
        text = report.to_json().lower()
        for forbidden in ("buy", "sell", "order", "execute", "trade"):
            self.assertNotIn(forbidden, text)

    def test_deterministic_serialization(self):
        inputs = MomentumInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        r1 = self.specialist.analyze(inputs)
        r2 = self.specialist.analyze(inputs)
        self.assertEqual(r1.to_json(), r2.to_json())


# ---------------------------------------------------------------------------
# Volume Specialist tests
# ---------------------------------------------------------------------------


class VolumeSpecialistTests(unittest.TestCase):
    def setUp(self):
        self.specialist = VolumeSpecialist()

    def test_produces_advisory_report(self):
        inputs = VolumeInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        report = self.specialist.analyze(inputs)
        self.assertIsInstance(report, MarketIntelligenceReport)
        self.assertTrue(report.advisory_only)
        self.assertEqual(report.agent_name, "Volume Intelligence Specialist")

    def test_volume_spikes_detected(self):
        inputs = VolumeInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_volume_spike_candles(),
        )
        report = self.specialist.analyze(inputs)
        joined = " ".join(report.evidence).lower()
        self.assertIn("spike", joined)

    def test_obv_evidence_present(self):
        inputs = VolumeInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        report = self.specialist.analyze(inputs)
        joined = " ".join(report.evidence).lower()
        self.assertIn("obv", joined)

    def test_confidence_is_bounded(self):
        inputs = VolumeInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        report = self.specialist.analyze(inputs)
        self.assertGreaterEqual(report.confidence, 0.0)
        self.assertLessEqual(report.confidence, 1.0)

    def test_insufficient_data_handled_gracefully(self):
        single = _make_candle(60, 100.0, 101.0, 99.0, 100.5, 1000.0)
        inputs = VolumeInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=(single,),
        )
        report = self.specialist.analyze(inputs)
        self.assertTrue(report.advisory_only)
        self.assertGreater(len(report.warnings), 0)

    def test_rejects_wrong_input_type(self):
        with self.assertRaises(ValueError):
            self.specialist.analyze(None)

    def test_report_is_immutable(self):
        inputs = VolumeInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        report = self.specialist.analyze(inputs)
        with self.assertRaises(FrozenInstanceError):
            report.confidence = 0.99

    def test_no_buy_sell_directives(self):
        inputs = VolumeInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        report = self.specialist.analyze(inputs)
        text = report.to_json().lower()
        for forbidden in ("buy", "sell", "order", "execute", "trade"):
            self.assertNotIn(forbidden, text)

    def test_deterministic_serialization(self):
        inputs = VolumeInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        r1 = self.specialist.analyze(inputs)
        r2 = self.specialist.analyze(inputs)
        self.assertEqual(r1.to_json(), r2.to_json())


# ---------------------------------------------------------------------------
# Volatility Specialist tests
# ---------------------------------------------------------------------------


class VolatilitySpecialistTests(unittest.TestCase):
    def setUp(self):
        self.specialist = VolatilitySpecialist()

    def test_produces_advisory_report(self):
        inputs = VolatilityInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        report = self.specialist.analyze(inputs)
        self.assertIsInstance(report, MarketIntelligenceReport)
        self.assertTrue(report.advisory_only)
        self.assertEqual(
            report.agent_name, "Volatility Intelligence Specialist"
        )

    def test_high_volatility_regime_detected(self):
        inputs = VolatilityInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_high_volatility_candles(),
        )
        report = self.specialist.analyze(inputs)
        joined = " ".join(report.evidence).lower()
        self.assertTrue("high" in joined or "bollinger" in joined)

    def test_low_volatility_regime_detected(self):
        inputs = VolatilityInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_low_volatility_candles(),
        )
        report = self.specialist.analyze(inputs)
        joined = " ".join(report.evidence).lower()
        self.assertTrue("low" in joined or "bollinger" in joined)

    def test_confidence_is_bounded(self):
        inputs = VolatilityInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        report = self.specialist.analyze(inputs)
        self.assertGreaterEqual(report.confidence, 0.0)
        self.assertLessEqual(report.confidence, 1.0)

    def test_insufficient_data_handled_gracefully(self):
        single = _make_candle(60, 100.0, 101.0, 99.0, 100.5, 1000.0)
        inputs = VolatilityInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=(single,),
        )
        report = self.specialist.analyze(inputs)
        self.assertTrue(report.advisory_only)
        self.assertGreater(len(report.warnings), 0)

    def test_rejects_wrong_input_type(self):
        with self.assertRaises(ValueError):
            self.specialist.analyze([])

    def test_report_is_immutable(self):
        inputs = VolatilityInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        report = self.specialist.analyze(inputs)
        with self.assertRaises(FrozenInstanceError):
            report.confidence = 0.99

    def test_no_buy_sell_directives(self):
        inputs = VolatilityInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        report = self.specialist.analyze(inputs)
        text = report.to_json().lower()
        for forbidden in ("buy", "sell", "order", "execute", "trade"):
            self.assertNotIn(forbidden, text)

    def test_deterministic_serialization(self):
        inputs = VolatilityInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        r1 = self.specialist.analyze(inputs)
        r2 = self.specialist.analyze(inputs)
        self.assertEqual(r1.to_json(), r2.to_json())


# ---------------------------------------------------------------------------
# Input validation tests
# ---------------------------------------------------------------------------


class InputValidationTests(unittest.TestCase):
    def test_candle_rejects_high_below_low(self):
        with self.assertRaises(ValueError):
            Candle(
                timestamp=FRESH,
                open=100.0,
                high=99.0,
                low=100.0,
                close=100.0,
                volume=1000.0,
            )

    def test_candle_rejects_negative_volume(self):
        with self.assertRaises(ValueError):
            Candle(
                timestamp=FRESH,
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.0,
                volume=-1.0,
            )

    def test_candle_rejects_naive_timestamp(self):
        with self.assertRaises(ValueError):
            Candle(
                timestamp=datetime(2026, 7, 13, 12, 0, 0),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.0,
                volume=1000.0,
            )

    def test_candle_rejects_nan_price(self):
        with self.assertRaises(ValueError):
            Candle(
                timestamp=FRESH,
                open=float("nan"),
                high=101.0,
                low=99.0,
                close=100.0,
                volume=1000.0,
            )

    def test_trend_inputs_reject_empty_candles(self):
        with self.assertRaises(ValueError):
            TrendInputs(
                symbol="BTC/USD",
                timeframe="4H",
                observed_at=FRESH,
                candles=(),
            )

    def test_trend_inputs_reject_unordered_candles(self):
        c1 = _make_candle(120, 100.0, 101.0, 99.0, 100.5, 1000.0)
        c2 = _make_candle(60, 101.0, 102.0, 100.0, 101.5, 1100.0)
        with self.assertRaises(ValueError):
            TrendInputs(
                symbol="BTC/USD",
                timeframe="4H",
                observed_at=FRESH,
                candles=(c2, c1),
            )

    def test_momentum_inputs_reject_empty_symbol(self):
        with self.assertRaises(ValueError):
            MomentumInputs(
                symbol="",
                timeframe="4H",
                observed_at=FRESH,
                candles=_bullish_candles(),
            )

    def test_volume_inputs_reject_empty_timeframe(self):
        with self.assertRaises(ValueError):
            VolumeInputs(
                symbol="BTC/USD",
                timeframe="",
                observed_at=FRESH,
                candles=_bullish_candles(),
            )

    def test_volatility_inputs_reject_naive_timestamp(self):
        with self.assertRaises(ValueError):
            VolatilityInputs(
                symbol="BTC/USD",
                timeframe="4H",
                observed_at=datetime(2026, 7, 13, 12, 0, 0),
                candles=_bullish_candles(),
            )

    def test_inputs_are_immutable(self):
        inputs = TrendInputs(
            symbol="BTC/USD",
            timeframe="4H",
            observed_at=FRESH,
            candles=_bullish_candles(),
        )
        with self.assertRaises(FrozenInstanceError):
            inputs.symbol = "ETH/USD"


# ---------------------------------------------------------------------------
# Indicator function tests
# ---------------------------------------------------------------------------


class IndicatorFunctionTests(unittest.TestCase):
    def test_sma_basic(self):
        from agents.market_intelligence.indicators import sma

        self.assertAlmostEqual(sma([1.0, 2.0, 3.0], 3), 2.0)

    def test_sma_insufficient_data(self):
        from agents.market_intelligence.indicators import sma

        self.assertIsNone(sma([1.0, 2.0], 3))

    def test_ema_basic(self):
        from agents.market_intelligence.indicators import ema

        result = ema([1.0, 2.0, 3.0, 4.0, 5.0], 3)
        self.assertIsNotNone(result)
        self.assertGreater(result, 3.0)

    def test_ema_insufficient_data(self):
        from agents.market_intelligence.indicators import ema

        self.assertIsNone(ema([1.0], 3))

    def test_rsi_all_gains(self):
        from agents.market_intelligence.indicators import rsi

        closes = [100.0 + i for i in range(20)]
        result = rsi(closes, 14)
        self.assertEqual(result, 100.0)

    def test_rsi_all_losses(self):
        from agents.market_intelligence.indicators import rsi

        closes = [100.0 - i for i in range(20)]
        result = rsi(closes, 14)
        self.assertEqual(result, 0.0)

    def test_rsi_insufficient_data(self):
        from agents.market_intelligence.indicators import rsi

        self.assertIsNone(rsi([100.0, 101.0], 14))

    def test_macd_returns_tuple(self):
        from agents.market_intelligence.indicators import macd

        closes = [100.0 + i * 0.5 for i in range(40)]
        result = macd(closes)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)

    def test_macd_insufficient_data(self):
        from agents.market_intelligence.indicators import macd

        self.assertIsNone(macd([100.0, 101.0]))

    def test_stochastic_returns_tuple(self):
        from agents.market_intelligence.indicators import stochastic

        highs = [101.0 + i for i in range(20)]
        lows = [99.0 + i for i in range(20)]
        closes = [100.0 + i for i in range(20)]
        result = stochastic(highs, lows, closes)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)

    def test_atr_positive(self):
        from agents.market_intelligence.indicators import atr

        highs = [102.0, 103.0, 101.0, 104.0, 105.0, 103.0, 106.0, 107.0]
        lows = [98.0, 99.0, 97.0, 100.0, 101.0, 99.0, 102.0, 103.0]
        closes = [100.0, 101.0, 100.0, 102.0, 103.0, 101.0, 104.0, 105.0]
        result = atr(highs, lows, closes, 5)
        self.assertIsNotNone(result)
        self.assertGreater(result, 0)

    def test_bollinger_bands_returns_tuple(self):
        from agents.market_intelligence.indicators import bollinger_bands

        closes = [100.0 + i * 0.5 for i in range(25)]
        result = bollinger_bands(closes)
        self.assertIsNotNone(result)
        middle, upper, lower = result
        self.assertGreater(upper, middle)
        self.assertLess(lower, middle)

    def test_relative_volume_basic(self):
        from agents.market_intelligence.indicators import relative_volume

        volumes = [1000.0] * 20 + [2000.0]
        result = relative_volume(volumes, 20)
        self.assertAlmostEqual(result, 2.0)

    def test_relative_volume_insufficient(self):
        from agents.market_intelligence.indicators import relative_volume

        self.assertIsNone(relative_volume([1000.0], 20))

    def test_volume_spikes_counts(self):
        from agents.market_intelligence.indicators import volume_spikes

        volumes = [1000.0] * 5 + [3000.0] * 5
        result = volume_spikes(volumes, 5, 2.0)
        self.assertEqual(result, 5)

    def test_obv_rising(self):
        from agents.market_intelligence.indicators import obv

        closes = [100.0, 101.0, 102.0]
        volumes = [1000.0, 2000.0, 3000.0]
        result = obv(closes, volumes)
        self.assertEqual(result, 5000.0)

    def test_obv_falling(self):
        from agents.market_intelligence.indicators import obv

        closes = [100.0, 99.0, 98.0]
        volumes = [1000.0, 2000.0, 3000.0]
        result = obv(closes, volumes)
        self.assertEqual(result, -5000.0)

    def test_obv_series_length(self):
        from agents.market_intelligence.indicators import obv_series

        closes = [100.0, 101.0, 102.0]
        volumes = [1000.0, 2000.0, 3000.0]
        result = obv_series(closes, volumes)
        self.assertEqual(len(result), 3)

    def test_detect_swings_returns_tuple(self):
        from agents.market_intelligence.indicators import detect_swings

        closes = [100.0, 105.0, 95.0, 110.0, 90.0, 115.0, 85.0, 120.0]
        result = detect_swings(closes, 8)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)

    def test_detect_swings_insufficient(self):
        from agents.market_intelligence.indicators import detect_swings

        self.assertIsNone(detect_swings([100.0], 20))


# ---------------------------------------------------------------------------
# Cross-specialist safety tests
# ---------------------------------------------------------------------------


class CrossSpecialistSafetyTests(unittest.TestCase):
    def test_all_specialists_inherit_from_base(self):
        from agents.market_intelligence.base import (
            MarketIntelligenceSpecialist,
        )

        self.assertTrue(
            issubclass(TrendSpecialist, MarketIntelligenceSpecialist)
        )
        self.assertTrue(
            issubclass(MomentumSpecialist, MarketIntelligenceSpecialist)
        )
        self.assertTrue(
            issubclass(VolumeSpecialist, MarketIntelligenceSpecialist)
        )
        self.assertTrue(
            issubclass(VolatilitySpecialist, MarketIntelligenceSpecialist)
        )

    def test_all_specialists_produce_advisory_reports(self):
        specialists = [
            (TrendSpecialist(), TrendInputs),
            (MomentumSpecialist(), MomentumInputs),
            (VolumeSpecialist(), VolumeInputs),
            (VolatilitySpecialist(), VolatilityInputs),
        ]
        candles = _bullish_candles()
        for specialist, inputs_cls in specialists:
            inputs = inputs_cls(
                symbol="BTC/USD",
                timeframe="4H",
                observed_at=FRESH,
                candles=candles,
            )
            report = specialist.analyze(inputs)
            self.assertTrue(
                report.advisory_only,
                f"{specialist.name} did not produce advisory-only report",
            )

    def test_all_specialists_declare_supported_symbols(self):
        for specialist_cls in (
            TrendSpecialist,
            MomentumSpecialist,
            VolumeSpecialist,
            VolatilitySpecialist,
        ):
            specialist = specialist_cls()
            self.assertGreater(len(specialist.supported_symbols), 0)
            self.assertGreater(len(specialist.supported_timeframes), 0)

    def test_all_specialists_have_valid_metadata(self):
        for specialist_cls in (
            TrendSpecialist,
            MomentumSpecialist,
            VolumeSpecialist,
            VolatilitySpecialist,
        ):
            specialist = specialist_cls()
            meta = specialist.metadata()
            self.assertTrue(meta.advisory_only)
            self.assertEqual(meta.version, specialist.VERSION)


if __name__ == "__main__":
    unittest.main()
