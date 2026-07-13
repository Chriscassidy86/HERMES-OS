from datetime import datetime,timezone
from decimal import Decimal
import unittest
from agents.trend.trend_specialist import TrendSpecialist
from core.decision_cycle import DecisionCycle
from paper_trading.portfolio import PaperPortfolio
from reports.market_snapshot import MarketSnapshot
from services.paper_execution import PaperExecutionEngine
NOW=datetime(2026,7,13,12,tzinfo=timezone.utc)
def snap(trend,price=100): return MarketSnapshot("BTC/USD",price,1000,trend,.1,50,90,900,105,95,"4H",NOW)
class ExecutionTests(unittest.TestCase):
 def test_buy_sell_and_audit_context(self):
  portfolio=PaperPortfolio(clock=lambda:NOW); engine=PaperExecutionEngine(portfolio); cycle=DecisionCycle((TrendSpecialist(),),clock=lambda:NOW).run(snap("Bullish")); result=engine.execute(cycle,100)
  self.assertEqual("PAPER_FILLED",result.status); self.assertTrue(result.risk_approved); self.assertTrue(result.specialist_summary); self.assertEqual("PAPER", "PAPER" if result.paper_only else "LIVE")
  sell=DecisionCycle((TrendSpecialist(),),clock=lambda:NOW).run(snap("Bearish",101)); closed=engine.execute(sell,101); self.assertEqual("PAPER_CLOSED",closed.status); self.assertEqual(1,len(portfolio.trades))
 def test_wait_is_noop(self):
  portfolio=PaperPortfolio(clock=lambda:NOW); cycle=DecisionCycle((TrendSpecialist(),),clock=lambda:NOW).run(snap("Sideways")); result=PaperExecutionEngine(portfolio).execute(cycle,100); self.assertEqual("RISK_REJECTED",result.status); self.assertEqual({},portfolio.orders)
if __name__=="__main__": unittest.main()
