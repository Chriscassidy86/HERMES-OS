from datetime import datetime,timezone
import unittest
from data_providers.market_data import MarketDataError
from data_providers.public_adapters import PublicCandle
from services.provider_redundancy import RedundantPublicProvider
NOW=datetime(2026,7,13,tzinfo=timezone.utc)
class Provider:
 def __init__(self,name,values): self.name=name; self.values=iter(values)
 def get_candle(self,symbol,timeframe):
  value=next(self.values)
  if isinstance(value,Exception): raise value
  return PublicCandle(self.name,symbol,timeframe,NOW,value,1)
def group(a,b=(101,),c=(101,)): return RedundantPublicProvider((Provider("Binance.US",a),Provider("Coinbase",b),Provider("Kraken",c)),conflict_tolerance_percent=5,latency_clock=lambda:0)
class RedundancyTests(unittest.TestCase):
 def test_primary_success_and_attribution(self): self.assertEqual("Binance.US",group((100,)).get_candle("BTCUSDT").source)
 def test_second_and_third_fallback(self):
  self.assertEqual("Coinbase",group((MarketDataError("x"),)).get_candle("BTCUSDT").source)
  self.assertEqual("Kraken",group((MarketDataError("x"),),(MarketDataError("x"),)).get_candle("BTCUSDT").source)
 def test_all_fail(self):
  with self.assertRaises(MarketDataError): group((MarketDataError("x"),),(MarketDataError("x"),),(MarketDataError("x"),)).get_candle("BTCUSDT")
 def test_conflict_fails_closed(self):
  with self.assertRaises(MarketDataError): group((100,),(200,),(100,)).get_candle("BTCUSDT")
 def test_compatibility_rejection(self):
  with self.assertRaises(MarketDataError): group((100,)).get_candle("DOGEUSDT")
  with self.assertRaises(MarketDataError): group((100,)).get_candle("BTCUSDT","1H")
 def test_cooldown_and_recovery_probe(self):
  provider=Provider("Binance.US",(MarketDataError("x"),MarketDataError("x"),MarketDataError("x"),100)); fallback=Provider("Coinbase",(101,101,101,101,101,101)); third=Provider("Kraken",(101,101,101,101,101,101)); service=RedundantPublicProvider((provider,fallback,third),cooldown_cycles=2,latency_clock=lambda:0)
  for _ in range(5): service.get_candle("BTCUSDT")
  result=service.get_candle("BTCUSDT"); self.assertEqual("Binance.US",result.source); self.assertTrue(result.states[0].healthy)
 def test_deterministic_priority(self): self.assertEqual("Binance.US",group((100,),(100,),(100,)).get_candle("BTCUSDT").source)
 def test_no_authenticated_or_order_capability(self):
  service=group((100,)); self.assertFalse(hasattr(service,"credentials")); self.assertFalse(hasattr(service,"place_order"))
if __name__=="__main__": unittest.main()
