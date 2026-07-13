from datetime import datetime,timedelta,timezone
import unittest
from data_providers.market_data import FixtureMarketDataProvider,MarketDataError,ReadOnlyPublicMarketDataProvider,ReplayMarketDataProvider,SnapshotBuilder,StaleMarketDataError,normalize_symbol
NOW=datetime(2026,7,11,12,tzinfo=timezone.utc)
def record(**updates):
    value={"symbol":"BTCUSD","price":100,"volume_24h":1500,"market_trend":"Bullish","volatility":2,"fear_greed_index":55,"timestamp":NOW,"previous_price":98,"average_volume":1000,"short_moving_average":101,"long_moving_average":99}; value.update(updates); return value
class MarketDataTests(unittest.TestCase):
    def setUp(self): self.builder=SnapshotBuilder(lambda:NOW)
    def test_valid_fixture_snapshot(self):
        provider=FixtureMarketDataProvider({"BTC/USD":record()},self.builder); self.assertEqual("BTC/USD",provider.get_snapshot("btcusd").symbol); self.assertTrue(provider.health.healthy)
    def test_missing_field(self):
        value=record(); del value["price"]
        with self.assertRaises(MarketDataError): self.builder.build(value)
    def test_stale_data(self):
        with self.assertRaises(StaleMarketDataError): self.builder.build(record(timestamp=NOW-timedelta(hours=5)))
    def test_future_data(self):
        with self.assertRaises(MarketDataError): self.builder.build(record(timestamp=NOW+timedelta(minutes=5)))
    def test_malformed_response(self):
        with self.assertRaises(MarketDataError): self.builder.build(record(price="invalid"))
    def test_timeout(self):
        calls=[]
        def fetch(*args): calls.append(args); raise TimeoutError("timeout")
        provider=ReadOnlyPublicMarketDataProvider(fetch,self.builder,retries=2)
        with self.assertRaises(MarketDataError): provider.get_snapshot("BTC/USD")
        self.assertEqual(3,len(calls)); self.assertFalse(provider.health.healthy)
    def test_provider_unavailable(self):
        with self.assertRaises(MarketDataError): FixtureMarketDataProvider({},self.builder).get_snapshot("BTC/USD")
    def test_symbol_normalization(self): self.assertEqual("BTC/USD",normalize_symbol("btc-usdt")); self.assertEqual("ETH/USD",normalize_symbol("ethusd"))
    def test_deterministic_replay(self):
        provider=ReplayMarketDataProvider([record(price=100),record(price=101)],self.builder)
        self.assertEqual([100,101],[provider.get_snapshot("BTC/USD").price,provider.get_snapshot("BTC/USD").price])
        with self.assertRaises(MarketDataError): provider.get_snapshot("BTC/USD")
if __name__=="__main__": unittest.main()
