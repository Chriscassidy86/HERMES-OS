from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import unittest

from core.recommendation.recommendation_engine import RecommendationEngine
from core.timeframes import MultiTimeframeEngine
from models.signal import Signal


NOW = datetime(2026, 7, 13, 12, tzinfo=timezone.utc)
FRAMES = ("5m", "15m", "1h", "4h", "Daily")


def signals(source="Trend Specialist", direction="LONG"):
    return tuple(Signal(source, direction, 80, 0.8, frame, 2, NOW, (f"{frame} evidence",))
                 for frame in FRAMES)


class MultiTimeframeTests(unittest.TestCase):
    def test_all_supported_timeframes_form_three_human_horizons(self):
        result = MultiTimeframeEngine().analyze("BTC/USD", signals(), as_of=NOW)
        item = result.specialists[0]
        self.assertEqual(("5m", "15m"), item.short_term.timeframes)
        self.assertEqual(("1h", "4h"), item.medium_term.timeframes)
        self.assertEqual(("Daily",), item.long_term.timeframes)
        self.assertEqual("LONG", item.aligned_direction)

    def test_aligned_specialists_produce_risk_reviewed_recommendation(self):
        summary = MultiTimeframeEngine().analyze(
            "BTC/USD", signals("Trend Specialist") + signals("Momentum Specialist"), as_of=NOW
        )
        recommendation = RecommendationEngine().recommend_multi_timeframe(summary)
        self.assertEqual("LONG", recommendation.action)
        self.assertTrue(recommendation.requires_risk_review)
        self.assertIn("Risk Manager", recommendation.reason)

    def test_timeframe_conflict_returns_wait_and_explains_conflict(self):
        values = list(signals()); values[-1] = replace(values[-1], direction="SHORT")
        summary = MultiTimeframeEngine().analyze("BTC/USD", tuple(values), as_of=NOW)
        self.assertEqual("WAIT", summary.aligned_direction)
        recommendation = RecommendationEngine().recommend_multi_timeframe(summary)
        self.assertEqual("WAIT", recommendation.action)
        self.assertTrue(summary.conflicts)

    def test_specialist_conflict_returns_wait(self):
        summary = MultiTimeframeEngine().analyze(
            "BTC/USD", signals("Trend Specialist", "LONG") + signals("Momentum Specialist", "SHORT"), as_of=NOW
        )
        self.assertEqual("WAIT", summary.aligned_direction)
        self.assertIn("Specialists disagree", summary.conflicts[-1])

    def test_missing_duplicate_or_unsupported_timeframe_fails_closed(self):
        with self.assertRaises(ValueError): MultiTimeframeEngine().analyze("BTC/USD", signals()[:-1], as_of=NOW)
        with self.assertRaises(ValueError): MultiTimeframeEngine().analyze("BTC/USD", signals() + (signals()[0],), as_of=NOW)
        with self.assertRaises(ValueError):
            MultiTimeframeEngine().analyze("BTC/USD", (replace(signals()[0], timeframe="2h"),), as_of=NOW)

    def test_stale_future_or_missing_evidence_fails_closed(self):
        for value in (
            replace(signals()[0], timestamp=NOW - timedelta(days=3)),
            replace(signals()[0], timestamp=NOW + timedelta(minutes=2)),
            replace(signals()[0], evidence=()),
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                MultiTimeframeEngine().analyze("BTC/USD", (value,), as_of=NOW)

    def test_summary_is_deterministic_and_immutable(self):
        first = MultiTimeframeEngine().analyze("BTC/USD", signals(), as_of=NOW)
        second = MultiTimeframeEngine().analyze("BTC/USD", signals(), as_of=NOW)
        self.assertEqual(first, second)
        with self.assertRaises(FrozenInstanceError): first.confidence = 0


if __name__ == "__main__": unittest.main()
