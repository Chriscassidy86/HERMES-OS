from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import json
import unittest

from models.market_consensus import ConsensusDirection, ConsensusObservation, ConsensusSignal, ConsensusSnapshot, ConsensusSource, SourceCategory, stable_json


NOW = datetime(2026, 7, 14, 12, tzinfo=timezone.utc)


def source(source_id="public-price"):
    return ConsensusSource(source_id, "Public Price", SourceCategory.PUBLIC_EXCHANGE_METRICS, 0.8, "VERIFIED_PUBLIC", "PUBLIC", "Validated Hermes public snapshot", True)


def observation(observation_id="O-1", *, src=None, observed=NOW, ingested=NOW, score=0.6, eligible=True, reason=None):
    signal = ConsensusSignal(ConsensusDirection.BULLISH, score, 0.8, 0.7, ("One public observation is limited.",))
    return ConsensusObservation.create(observation_id=observation_id, source=src or source(), symbol="BTC/USD", timeframe="1H", observed_at=observed, ingested_at=ingested, raw_value=101.25, signal=signal, eligible_for_consensus=eligible, exclusion_reason=reason)


class ConsensusModelTests(unittest.TestCase):
    def test_observations_are_immutable_and_use_utc(self):
        item = observation()
        self.assertEqual(timezone.utc, item.observed_at.tzinfo)
        with self.assertRaises(FrozenInstanceError):
            item.symbol = "ETH/USD"

    def test_finite_bounded_values_and_explicit_dimensions(self):
        with self.assertRaises(ValueError):
            ConsensusSignal(ConsensusDirection.BULLISH, float("nan"), 0.5, 0.5, ())
        with self.assertRaises(ValueError):
            ConsensusSignal(ConsensusDirection.BULLISH, 0.5, 1.1, 0.5, ())
        with self.assertRaises(ValueError):
            observation(score=2)
        with self.assertRaises(ValueError):
            ConsensusObservation.create(observation_id="O", source=source(), symbol="", timeframe="1H", observed_at=NOW, ingested_at=NOW, raw_value=1.0, signal=ConsensusSignal(ConsensusDirection.NEUTRAL, 0, 0.5, 0, ()))

    def test_naive_and_future_timestamps_fail_closed(self):
        with self.assertRaises(ValueError):
            observation(observed=NOW.replace(tzinfo=None))
        with self.assertRaises(ValueError):
            observation(observed=NOW + timedelta(minutes=2))

    def test_stale_or_otherwise_ineligible_evidence_requires_reason(self):
        with self.assertRaises(ValueError):
            observation(eligible=False)
        item = observation(observed=NOW - timedelta(hours=2), eligible=False, reason="STALE")
        self.assertFalse(item.eligible_for_consensus)
        self.assertEqual(7200, item.freshness_seconds)

    def test_exact_duplicate_is_deduplicated_and_conflict_rejected(self):
        item = observation()
        snapshot = ConsensusSnapshot.build("BTC/USD", "1H", NOW, (item, item))
        self.assertEqual((item,), snapshot.observations)
        conflict = observation(score=0.2)
        with self.assertRaisesRegex(ValueError, "Conflicting duplicate"):
            ConsensusSnapshot.build("BTC/USD", "1H", NOW, (item, conflict))

    def test_snapshot_order_and_json_are_stable(self):
        second = observation("O-2", src=source("another-source"))
        first = observation()
        snapshot = ConsensusSnapshot.build("BTC/USD", "1H", NOW, (first, second))
        self.assertEqual(("another-source", "public-price"), tuple(item.source_id for item in snapshot.observations))
        payload = stable_json(snapshot)
        self.assertEqual(payload, stable_json(snapshot))
        self.assertEqual("BTC/USD", json.loads(payload)["symbol"])
        self.assertNotIn("BUY", payload)
        self.assertNotIn("SELL", payload)


if __name__ == "__main__":
    unittest.main()
