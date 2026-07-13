from dataclasses import replace
from datetime import datetime,timedelta,timezone
import unittest
from models.performance_analytics import PerformanceObservation
from services.performance_analytics import PerformanceAnalyticsService
NOW=datetime(2026,1,1,tzinfo=timezone.utc)
def item(index,symbol="BTC/USD",pnl=1,**changes):
 value=PerformanceObservation(str(index)+symbol,NOW+timedelta(days=index),"PAPER",symbol,"BULL","4H","trend",pnl,0,100+pnl,20,10,.1,.1,.7,pnl>0,"WIN" if pnl>0 else "LOSS",3600)
 return replace(value,**changes)
class PortfolioExpansionTests(unittest.TestCase):
 def setUp(self): self.service=PerformanceAnalyticsService()
 def test_empty_and_single_trade(self):
  self.assertEqual("INSUFFICIENT_DATA",self.service.portfolio_projection((),starting_equity=100).correlation_state)
  report=self.service.portfolio_projection((item(0),),starting_equity=100); self.assertEqual(1,len(report.equity_curve)); self.assertEqual(3600,report.average_holding_seconds)
 def test_curves_and_concentration(self):
  report=self.service.portfolio_projection((item(0,exposure=30),item(1,"ETH/USD",exposure=10)),starting_equity=100); self.assertEqual(.75,report.concentration_risk); self.assertEqual(2,len(report.cash_curve))
 def test_correlation_when_enough_data(self):
  values=(item(0,pnl=1),item(1,pnl=2),item(0,"ETH/USD",pnl=2),item(1,"ETH/USD",pnl=4)); report=self.service.portfolio_projection(values,starting_equity=100); self.assertEqual("AVAILABLE",report.correlation_state); self.assertEqual(1,report.correlations[0][2])
 def test_source_separation_and_stable_serialization(self):
  report=self.service.portfolio_projection((item(0),item(1,source="REPLAY")),starting_equity=100); self.assertEqual(("PAPER","REPLAY"),report.source_labels); self.assertEqual(self.service.serialize(report),self.service.serialize(report))
 def test_nonfinite_and_negative_holding_rejected(self):
  with self.assertRaises(ValueError): self.service.portfolio_projection((item(0,holding_seconds=-1),),starting_equity=100)
if __name__=="__main__": unittest.main()
