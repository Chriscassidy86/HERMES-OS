from datetime import datetime, timedelta, timezone
import unittest

from models.market_consensus import ConsensusDirection, ConsensusObservation, ConsensusSignal, ConsensusSource, SourceCategory, stable_json
from services.consensus_normalization import ConsensusNormalizationEngine


NOW = datetime(2026, 7, 14, 12, tzinfo=timezone.utc)


def obs(source_id, score, *, category=SourceCategory.TECHNICAL_CONSENSUS, symbol="BTC/USD", age=0, reliability=0.8, dataset=None, eligible=True, reason=None, confidence=0.8):
    source = ConsensusSource(source_id, source_id, category, reliability, "TEST", "FIXTURE", "test", True)
    direction = ConsensusNormalizationEngine._direction(score)
    signal = ConsensusSignal(direction, score, confidence, abs(score), ())
    return ConsensusObservation.create(observation_id="O-" + source_id, source=source, symbol=symbol, timeframe="1H", observed_at=NOW - timedelta(seconds=age), ingested_at=NOW, raw_value=score, signal=signal, eligible_for_consensus=eligible, exclusion_reason=reason, underlying_dataset=dataset or source_id)


class ConsensusNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.engine = ConsensusNormalizationEngine()

    def normalize(self, values):
        return self.engine.normalize(tuple(values), symbol="BTC/USD", timeframe="1H", evaluated_at=NOW)

    def test_unanimous_bullish_and_bearish_sources(self):
        bullish = self.normalize((obs("a", 0.8), obs("b", 0.7, category=SourceCategory.DERIVATIVES)))
        bearish = self.normalize((obs("a", -0.8), obs("b", -0.7, category=SourceCategory.DERIVATIVES)))
        self.assertGreater(bullish.score, 0)
        self.assertLess(bearish.score, 0)
        self.assertNotEqual(ConsensusDirection.UNKNOWN, bullish.direction)

    def test_mixed_high_confidence_evidence_records_conflict(self):
        result = self.normalize((obs("a", 0.9), obs("b", -0.9, category=SourceCategory.DERIVATIVES)))
        self.assertTrue(result.conflicts)
        self.assertGreater(result.uncertainty, result.confidence)

    def test_stale_ineligible_future_and_malformed_dimension_evidence_is_excluded(self):
        values = (obs("stale", 0.5, age=2000), obs("ineligible", 0.5, eligible=False, reason="UNTRUSTED"), obs("wrong", 0.5, symbol="ETH/USD"))
        result = self.normalize(values)
        reasons = {reason for _, reason in result.excluded_observations}
        self.assertEqual({"STALE_OBSERVATION", "UNTRUSTED", "SYMBOL_MISMATCH"}, reasons)

    def test_duplicate_source_amplification_is_discounted(self):
        first = obs("same", 0.8)
        source = ConsensusSource("same", "same", SourceCategory.TECHNICAL_CONSENSUS, 0.8, "TEST", "FIXTURE", "test", True)
        second = ConsensusObservation.create(observation_id="O-same-2", source=source, symbol="BTC/USD", timeframe="1H", observed_at=NOW, ingested_at=NOW, raw_value=0.7, signal=ConsensusSignal(ConsensusDirection.BULLISH, 0.7, 0.8, 0.7, ()), underlying_dataset="other")
        result = self.normalize((first, second, obs("independent", 0.5, category=SourceCategory.DERIVATIVES)))
        repeated = next(item for item in result.contributions if item.observation_id == "O-same-2")
        self.assertFalse(repeated.independent)
        self.assertIn("source amplification", repeated.explanation)

    def test_correlated_sources_do_not_count_as_independent(self):
        result = self.normalize((obs("a", 0.7, dataset="shared"), obs("b", 0.7, category=SourceCategory.DERIVATIVES, dataset="shared")))
        self.assertEqual(1, result.independent_source_count)
        self.assertEqual(ConsensusDirection.UNKNOWN, result.direction)
        self.assertTrue(result.concentration_warning)

    def test_category_influence_is_capped(self):
        result = self.normalize(tuple(obs(str(index), 0.9) for index in range(5)) + (obs("other", -0.5, category=SourceCategory.DERIVATIVES),))
        technical_weight = sum(item.weight for item in result.contributions if item.category is SourceCategory.TECHNICAL_CONSENSUS)
        self.assertLessEqual(technical_weight, self.engine.CATEGORY_CAP + 0.000001)

    def test_broad_market_evidence_is_discounted_for_symbol(self):
        broad = obs("broad", 0.8, symbol="MARKET-WIDE", category=SourceCategory.SENTIMENT)
        specific = obs("specific", 0.8)
        result = self.normalize((broad, specific))
        by_id = {item.observation_id: item for item in result.contributions}
        self.assertLess(by_id["O-broad"].adjusted_score, by_id["O-specific"].adjusted_score)

    def test_low_reliability_and_freshness_reduce_weight(self):
        result = self.normalize((obs("fresh", 0.7), obs("weak", 0.7, category=SourceCategory.DERIVATIVES, reliability=0.2, age=1500)))
        by_id = {item.observation_id: item for item in result.contributions}
        self.assertLess(by_id["O-weak"].weight, by_id["O-fresh"].weight)
        self.assertTrue(result.freshness_warning)

    def test_insufficient_independent_evidence_fails_closed(self):
        result = self.normalize((obs("only", 0.9),))
        self.assertEqual(ConsensusDirection.UNKNOWN, result.direction)
        self.assertEqual(0, result.confidence)
        self.assertIn("Insufficient independent", result.limitations[-1])

    def test_one_sided_evidence_warns_about_crowding(self):
        result = self.normalize((obs("a", 0.9), obs("b", 0.8, category=SourceCategory.DERIVATIVES), obs("c", 0.7, category=SourceCategory.SENTIMENT)))
        self.assertIsNotNone(result.crowding_warning)

    def test_neutral_evidence_is_recorded_not_directional(self):
        result = self.normalize((obs("a", 0), obs("b", 0, category=SourceCategory.DERIVATIVES)))
        self.assertEqual(2, len(result.neutral_contributions))
        self.assertEqual(ConsensusDirection.NEUTRAL, result.direction)

    def test_output_and_explanation_order_are_deterministic(self):
        values = (obs("z", 0.4, category=SourceCategory.DERIVATIVES), obs("a", -0.2))
        first = self.normalize(values)
        second = self.normalize(tuple(reversed(values)))
        self.assertEqual(first, second)
        self.assertEqual(stable_json(first), stable_json(second))


if __name__ == "__main__":
    unittest.main()
