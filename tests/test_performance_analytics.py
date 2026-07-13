from dataclasses import replace
from datetime import datetime, timedelta, timezone
from math import inf
import unittest

from models.performance_analytics import PerformanceObservation
from services.performance_analytics import PerformanceAnalyticsService


NOW = datetime(2025, 1, 1, tzinfo=timezone.utc)


def observation(index, pnl=1, outcome="WIN", **changes):
    value = PerformanceObservation(
        str(index), NOW + timedelta(days=index), "PAPER", "BTC/USD", "BULL",
        "5m", "trend", pnl, 0, 100 + pnl + index, 0.2, 1, 0.1, 0.05,
        0.7, pnl > 0, outcome,
    )
    return replace(value, **changes)


class PerformanceAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.service = PerformanceAnalyticsService()

    def test_empty_portfolio(self):
        self.assertIsNone(self.service.analyze((), starting_equity=100).total_return)

    def test_all_winners_and_zero_downside(self):
        report = self.service.analyze((observation(0, 1), observation(1, 2)), starting_equity=100)
        self.assertEqual(1, report.win_rate); self.assertIsNone(report.profit_factor); self.assertIsNone(report.sortino_style)

    def test_all_losers(self):
        report = self.service.analyze((observation(0, -1, "LOSS"), observation(1, -2, "LOSS")), starting_equity=100)
        self.assertEqual(1, report.loss_rate); self.assertEqual(0, report.profit_factor)

    def test_mixed_trades_and_fees_slippage(self):
        report = self.service.analyze((observation(0, 2), observation(1, -1, "LOSS")), starting_equity=100)
        self.assertEqual(2, report.profit_factor); self.assertEqual(0.2, report.fee_impact); self.assertEqual(0.1, report.slippage_impact)

    def test_zero_variance(self):
        report = self.service.analyze((observation(0), observation(1)), starting_equity=100)
        self.assertIsNone(report.sharpe_style)

    def test_drawdown_sequence(self):
        items = (observation(0, equity=100), observation(1, equity=120), observation(2, equity=90))
        self.assertEqual(30, self.service.analyze(items, starting_equity=100).maximum_drawdown)

    def test_insufficient_samples_and_annualization_gate(self):
        self.assertGreaterEqual(len(self.service.analyze((observation(0),), starting_equity=100).warnings), 3)

    def test_annualized_when_justified(self):
        items = (observation(0, equity=100), observation(365, equity=110))
        self.assertEqual(0.1, self.service.analyze(items, starting_equity=100).annualized_return)

    def test_non_finite_input(self):
        with self.assertRaises(ValueError): self.service.analyze((observation(0, fees=inf),), starting_equity=100)

    def test_regime_and_timeframe_grouping(self):
        items = (observation(0), observation(1, regime="BEAR", timeframe="1h"))
        report = self.service.analyze(items, starting_equity=100)
        self.assertEqual(("BEAR", "BULL"), tuple(item.label for item in report.by_regime)); self.assertEqual(("1h", "5m"), tuple(item.label for item in report.by_timeframe))

    def test_source_separation(self):
        report = self.service.analyze((observation(0), observation(1, source="REPLAY")), starting_equity=100)
        self.assertEqual(("PAPER", "REPLAY"), tuple(item.label for item in report.by_source))

    def test_rejection_and_no_trade_quality(self):
        items = (observation(0, 0, "REJECTED", correct=True), observation(1, 0, "NO_TRADE", correct=False))
        report = self.service.analyze(items, starting_equity=100)
        self.assertEqual(1, report.rejection_quality); self.assertEqual(0, report.no_trade_quality)

    def test_stable_serialization(self):
        report = self.service.analyze((observation(0),), starting_equity=100)
        self.assertEqual(self.service.serialize(report), self.service.serialize(report))

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError): self.service.analyze((observation(0, observed_at=NOW.replace(tzinfo=None)),), starting_equity=100)
        with self.assertRaises(ValueError): self.service.analyze((observation(0, observed_at=NOW.astimezone(timezone(timedelta(hours=1)))),), starting_equity=100)


if __name__ == "__main__": unittest.main()
