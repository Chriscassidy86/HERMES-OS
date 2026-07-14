from datetime import datetime, timedelta, timezone
import unittest

from data_providers.consensus_adapters import CoinGeckoFixtureAdapter, ConsensusAdapterError, ExistingMarketEvidenceAdapter, FearGreedFixtureAdapter, FixtureConsensusAdapter, ManualImportConsensusAdapter
from data_providers.public_adapters import ProviderComparison, PublicCandle, RateLimitError
from reports.market_snapshot import MarketSnapshot
from services.consensus_source_registry import ConsensusSourceRegistry


NOW = datetime(2026, 7, 14, 12, tzinfo=timezone.utc)


class Transport:
    def __init__(self, values):
        self.values = iter(values)
        self.calls = 0

    def get(self, url, timeout):
        self.calls += 1
        value = next(self.values)
        if isinstance(value, Exception):
            raise value
        return value


def snapshot(symbol="BTC/USD", price=105, previous=100, trend="Bullish"):
    return MarketSnapshot(symbol, price, 120, trend, 0.2, 50, previous, 100, 110, 90, "4H", NOW, "Binance.US", NOW)


class ConsensusAdapterTests(unittest.TestCase):
    def setUp(self):
        self.registry = ConsensusSourceRegistry(enabled_source_ids=("hermes-public-market", "derivatives-fixture", "onchain-manual-import", "analyst-community-import"))

    def test_existing_validated_snapshots_create_metrics_and_breadth(self):
        adapter = ExistingMarketEvidenceAdapter(self.registry.get("hermes-public-market"), clock=lambda: NOW)
        values = adapter.observations((snapshot(), snapshot("ETH/USD", 95, 100, "Bearish")), timeframe="4H")
        self.assertEqual(9, len(values))
        self.assertEqual(1, sum(item.symbol == "MARKET-WIDE" for item in values))
        self.assertTrue(all(item.data_label == "PUBLIC" for item in values))

    def test_provider_agreement_and_disagreement_are_attributed(self):
        adapter = ExistingMarketEvidenceAdapter(self.registry.get("hermes-public-market"), clock=lambda: NOW)
        candles = (PublicCandle("Binance.US", "BTC/USD", "4H", NOW, 100, 1), PublicCandle("Coinbase", "BTC/USD", "4H", NOW, 102, 1))
        item = adapter.provider_comparison(ProviderComparison(candles, 2, 0, (), (), "Binance.US", "test"), symbol="BTC/USD", timeframe="4H")
        self.assertIn("Binance.US", item.reference)
        self.assertTrue(item.warnings)

    def test_fear_greed_fixture_parser_is_broad_low_influence_and_fresh(self):
        record = self.registry.get("fear-greed-public")
        payload = {"data": [{"value": "75", "value_classification": "Greed", "timestamp": str(int(NOW.timestamp()))}]}
        adapter = FearGreedFixtureAdapter(record, Transport((payload,)), clock=lambda: NOW, retries=0)
        item = adapter.fetch("MARKET-WIDE", "1D")
        self.assertEqual("FIXTURE", item.data_label)
        self.assertLessEqual(item.signal.confidence, 0.45)
        self.assertEqual("HEALTHY", adapter.health.status)

    def test_public_parser_timeout_retry_malformed_rate_limit_and_future_fail_closed(self):
        record = self.registry.get("fear-greed-public")
        good = {"data": [{"value": "50", "timestamp": str(int(NOW.timestamp()))}]}
        retry = Transport((TimeoutError(), good))
        self.assertEqual("NEUTRAL", FearGreedFixtureAdapter(record, retry, clock=lambda: NOW).fetch("MARKET-WIDE", "1D").signal.direction.value)
        self.assertEqual(2, retry.calls)
        for payload in ({}, {"data": [{"value": "nan", "timestamp": str(int(NOW.timestamp()))}]}, {"data": [{"value": "50", "timestamp": str(int((NOW + timedelta(minutes=2)).timestamp()))}]}):
            with self.assertRaises(ConsensusAdapterError):
                FearGreedFixtureAdapter(record, Transport((payload,)), clock=lambda: NOW, retries=0).fetch("MARKET-WIDE", "1D")
        limited = FearGreedFixtureAdapter(record, Transport((RateLimitError("429"),)), clock=lambda: NOW, retries=0)
        with self.assertRaisesRegex(ConsensusAdapterError, "rate limited"):
            limited.fetch("MARKET-WIDE", "1D")
        self.assertTrue(limited.health.rate_limited)

    def test_coingecko_fixture_parser_and_unsupported_dimensions(self):
        record = self.registry.get("coingecko-public-metadata")
        payload = {"price_change_percentage_24h": 5, "market_cap_rank": 1, "total_volume": 1000, "last_updated": NOW.isoformat()}
        adapter = CoinGeckoFixtureAdapter(record, Transport((payload,)), clock=lambda: NOW, retries=0)
        self.assertEqual("BULLISH", adapter.fetch("BTC/USD", "1H").signal.direction.value)
        with self.assertRaises(ConsensusAdapterError):
            CoinGeckoFixtureAdapter(record, Transport((payload,)), clock=lambda: NOW).fetch("DOGE/USD", "1H")

    def test_derivatives_fixture_is_labeled_and_deterministic(self):
        adapter = FixtureConsensusAdapter(self.registry.get("derivatives-fixture"), clock=lambda: NOW)
        value = {"observation_id": "D-1", "symbol": "BTC/USD", "timeframe": "1H", "observed_at": NOW, "score": -0.6, "confidence": 0.7, "raw_value": "funding=high"}
        first = adapter.observation(value)
        self.assertEqual(first, adapter.observation(value))
        self.assertEqual("FIXTURE", first.data_label)

    def test_manual_import_requires_attribution_bounds_and_excludes_stale(self):
        adapter = ManualImportConsensusAdapter(self.registry.get("analyst-community-import"), clock=lambda: NOW)
        value = {"observation_id": "A-1", "symbol": "BTC/USD", "timeframe": "1H", "observed_at": NOW, "direction": "LEAN_BULLISH", "score": 0.2, "confidence": 0.4, "author": "Analyst", "reference": "user-export:1", "summary": "Public opinion summary."}
        item = adapter.observation(value)
        self.assertTrue(item.eligible_for_consensus)
        self.assertIn("Analyst", item.reference)
        stale = dict(value, observation_id="A-2", observed_at=NOW - timedelta(hours=2))
        self.assertEqual("STALE_IMPORT", adapter.observation(stale).exclusion_reason)
        for invalid in (dict(value, author=""), dict(value, summary="x" * 281)):
            with self.assertRaises(ConsensusAdapterError):
                adapter.observation(invalid)

    def test_onchain_import_and_all_adapters_expose_no_trading_or_credentials(self):
        adapter = ManualImportConsensusAdapter(self.registry.get("onchain-manual-import"), clock=lambda: NOW)
        value = {"observation_id": "O-1", "symbol": "BTC/USD", "timeframe": "1H", "observed_at": NOW, "direction": "NEUTRAL", "score": 0, "confidence": 0.4, "author": "Licensed export owner", "reference": "export:1", "summary": "Net flow is balanced."}
        self.assertEqual("EXPORT", adapter.observation(value).data_label)
        for item in (adapter, ExistingMarketEvidenceAdapter(self.registry.get("hermes-public-market"), clock=lambda: NOW)):
            self.assertFalse(any(hasattr(item, name) for name in ("credentials", "authenticate", "place_order", "withdraw", "scrape_html")))


if __name__ == "__main__":
    unittest.main()
