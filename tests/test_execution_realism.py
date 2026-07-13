from datetime import datetime,timezone
from dataclasses import replace
import unittest
from agents.trend.trend_specialist import TrendSpecialist
from core.decision_cycle import DecisionCycle
from models.paper_execution import SimulationRules
from reports.market_snapshot import MarketSnapshot
from services.paper_execution import RealisticPaperSimulator
NOW=datetime(2026,7,13,tzinfo=timezone.utc)
def cycle(trend="Bullish"):
 snapshot=MarketSnapshot("BTC/USD",100,1000,trend,.1,50,90,900,105,95,"4H",NOW)
 return DecisionCycle((TrendSpecialist(),),clock=lambda:NOW).run(snapshot)
class ExecutionRealismTests(unittest.TestCase):
 def test_market_fee_slippage_impact_and_repeatability(self):
  rules=SimulationRules(impact_bps_per_unit=1); a=RealisticPaperSimulator(rules).submit(cycle(),side="BUY",order_type="MARKET",quantity=1,market_price=100); b=RealisticPaperSimulator(rules).submit(cycle(),side="BUY",order_type="MARKET",quantity=1,market_price=100); self.assertEqual(a,b); self.assertGreater(a[1][0].fee,0); self.assertGreater(a[1][0].slippage,0)
 def test_limit_fill_and_no_fill(self):
  service=RealisticPaperSimulator(); self.assertEqual("FILLED",service.submit(cycle(),side="BUY",order_type="LIMIT",quantity=1,market_price=99,limit_price=100)[0].status); self.assertEqual("OPEN",service.submit(cycle(),side="BUY",order_type="LIMIT",quantity=1,market_price=101,limit_price=100)[0].status)
 def test_partial_fill_no_overfill(self):
  order,fills=RealisticPaperSimulator(SimulationRules(partial_fill_ratio=.5)).submit(cycle(),side="BUY",order_type="MARKET",quantity=2,market_price=100); self.assertEqual("PARTIALLY_FILLED",order.status); self.assertEqual(1,fills[0].quantity)
 def test_timeout_and_cancellation(self):
  service=RealisticPaperSimulator(); order,fills=service.submit(cycle(),side="BUY",order_type="MARKET",quantity=1,market_price=100,elapsed_ms=2000); self.assertEqual("TIMED_OUT",order.status); self.assertEqual((),fills)
  open_order,_=service.submit(cycle(),side="BUY",order_type="LIMIT",quantity=1,market_price=101,limit_price=100); self.assertEqual("CANCELLED",service.cancel(open_order.order_id).status)
 def test_stop_take_profit_and_trailing(self):
  service=RealisticPaperSimulator(); self.assertEqual("FILLED",service.submit(cycle(),side="SELL",order_type="STOP_LOSS",quantity=1,market_price=90,stop_price=95)[0].status); self.assertEqual("FILLED",service.submit(cycle(),side="SELL",order_type="TAKE_PROFIT",quantity=1,market_price=110,stop_price=105)[0].status); self.assertEqual("FILLED",service.submit(cycle(),side="SELL",order_type="TRAILING_STOP",quantity=1,market_price=100,trailing_percent=1)[0].status)
 def test_precision_and_minimum_rejection(self):
  order,_=RealisticPaperSimulator().submit(cycle(),side="BUY",order_type="MARKET",quantity=1.123456789,market_price=100.123); self.assertEqual(1.12345679,order.quantity)
  with self.assertRaises(ValueError): RealisticPaperSimulator().submit(cycle(),side="BUY",order_type="MARKET",quantity=.00000001,market_price=1)
 def test_invalid_and_risk_rejection(self):
  with self.assertRaises(ValueError): RealisticPaperSimulator().submit(cycle(),side="BUY",order_type="MARKET",quantity=float("nan"),market_price=100)
  rejected=cycle("Sideways")
  with self.assertRaises(ValueError): RealisticPaperSimulator().submit(rejected,side="BUY",order_type="MARKET",quantity=1,market_price=100)
 def test_invalid_rules(self):
  with self.assertRaises(ValueError): RealisticPaperSimulator(SimulationRules(slippage_bps=-1))
if __name__=="__main__": unittest.main()
