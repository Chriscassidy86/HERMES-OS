from datetime import datetime,timedelta,timezone
import tempfile,unittest
from backtests.replay import FixtureCandleLoader,HistoricalCandle,ReplayConfig,ReplaySession
NOW=datetime(2026,7,11,tzinfo=timezone.utc)
def candles(prices=(100,105,110),trend="Bullish"):
    values=[]
    for i,price in enumerate(prices):
        directional=trend!="Sideways"
        previous=(prices[i-1] if i else price*0.98) if directional else price
        values.append(HistoricalCandle("BTC/USD",NOW+timedelta(hours=4*i),price,1500 if directional else 1000,1000,2 if directional else 4,trend,previous,price*1.01 if directional else price,price*.99 if directional else price))
    return tuple(values)
class ReplayTests(unittest.TestCase):
    def replay(self,prices=(100,105,110),**config): return ReplaySession(FixtureCandleLoader(candles(prices)),ReplayConfig(**config)).run()
    def test_deterministic_replay(self): self.assertEqual(self.replay(),self.replay())
    def test_no_lookahead_access(self):
        first=self.replay((100,105,110)); changed=self.replay((100,50,110))
        self.assertEqual(first.decisions[0],changed.decisions[0]); self.assertNotEqual(first.outcomes[0].pnl,changed.outcomes[0].pnl)
    def test_fee_impact(self): self.assertGreater(self.replay(fee_bps=0).strategy.total_pnl,self.replay(fee_bps=50).strategy.total_pnl)
    def test_slippage_impact(self): self.assertGreater(self.replay(slippage_bps=0).strategy.total_pnl,self.replay(slippage_bps=50).strategy.total_pnl)
    def test_losing_strategy(self): self.assertLess(self.replay((100,90,80)).strategy.total_pnl,0)
    def test_profitable_fixture_not_claimed_live(self): self.assertGreater(self.replay().strategy.total_pnl,0); self.assertEqual(2,self.replay().strategy.sample_size)
    def test_restart_consistency_and_exports(self):
        first=self.replay(); second=self.replay(); self.assertEqual(first.equity_history,second.equity_history)
        with tempfile.TemporaryDirectory() as directory:
            ReplaySession.export(first,directory); import pathlib; self.assertTrue((pathlib.Path(directory)/"trades.csv").exists()); self.assertTrue((pathlib.Path(directory)/"decisions.json").exists())
    def test_no_trade_and_rejection_counts(self):
        result=ReplaySession(FixtureCandleLoader(candles((100,100,100),"Sideways"))).run(); self.assertEqual(2,result.no_trade_count); self.assertEqual(2,result.risk_rejections)
if __name__=="__main__": unittest.main()
