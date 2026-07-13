from datetime import datetime,timedelta,timezone
import unittest
from data_providers.market_data import MarketDataError
from data_providers.public_adapters import BinanceUSPublicAdapter,CoinbasePublicAdapter,KrakenPublicAdapter,PublicProviderGroup
NOW=datetime(2026,7,12,12,tzinfo=timezone.utc); TS=int(NOW.timestamp())
class Transport:
    def __init__(self,value): self.value=value
    def get(self,url,timeout):
        if isinstance(self.value,Exception): raise self.value
        return self.value
def binance(price="100",timestamp=None): return [[(timestamp or TS)*1000,"0","0","0",price,"12"]]
def adapter(value,**kw): return BinanceUSPublicAdapter(Transport(value),lambda:NOW,retries=0,**kw)
class PublicAdapterTests(unittest.TestCase):
    def test_valid_normalization(self): self.assertEqual("BTC/USD",adapter(binance()).get_candle("btcusdt").symbol)
    def test_timeout(self):
        with self.assertRaises(MarketDataError): adapter(TimeoutError()).get_candle("BTC/USD")
    def test_malformed_response(self):
        with self.assertRaises(MarketDataError): adapter({}).get_candle("BTC/USD")
    def test_stale_data(self):
        with self.assertRaises(MarketDataError): adapter(binance(timestamp=TS-20000)).get_candle("BTC/USD")
    def test_future_data(self):
        with self.assertRaises(MarketDataError): adapter(binance(timestamp=TS+120)).get_candle("BTC/USD")
    def test_inconsistent_symbol_fails_validation(self):
        item=adapter(binance()); item._parse=lambda payload,symbol,timeframe: BinanceUSPublicAdapter._parse(item,payload,"ETH/USD",timeframe)
        with self.assertRaises(MarketDataError): item.get_candle("BTC/USD")
    def test_provider_disagreement_report(self):
        report=PublicProviderGroup((adapter(binance("100")),adapter(binance("110")))).compare("BTC/USD"); self.assertEqual(10,report.price_spread_percent)
    def test_failover(self):
        report=PublicProviderGroup((adapter(TimeoutError()),adapter(binance()))).compare("BTC/USD"); self.assertTrue(report.unhealthy_providers); self.assertIsNotNone(report.selected_source)
    def test_all_providers_unavailable(self):
        with self.assertRaises(MarketDataError): PublicProviderGroup((adapter(TimeoutError()),)).get_candle("BTC/USD")
    def test_exchange_parsers_and_no_private_capability(self):
        coin=CoinbasePublicAdapter(Transport([[TS,90,110,95,101,5]]),lambda:NOW,retries=0)
        kraken=KrakenPublicAdapter(Transport({"error":[],"result":{"XXBTZUSD":[[TS,"95","110","90","102","0","6",1]],"last":TS}}),lambda:NOW,retries=0)
        self.assertEqual((101,102),(coin.get_candle("BTC/USD").close,kraken.get_candle("BTC/USD").close))
        for value in (adapter(binance()),coin,kraken):
            self.assertFalse(any(hasattr(value,name) for name in ("authenticate","create_order","place_order","api_key")))
if __name__=="__main__": unittest.main()
