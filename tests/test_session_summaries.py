from datetime import timedelta
from pathlib import Path
import tempfile,unittest
from database.validation_repository import ValidationRepository
from services.session_summaries import SessionSummaryService
from services.decision_quality import DecisionQualityService
from services.trade_report_cards import TradeReportCardService
from tests.test_trade_report_cards import NOW,cycle,trade
class SummaryTests(unittest.TestCase):
 def setUp(self): self.s=SessionSummaryService()
 def decision(self,action="WAIT",approved=False,move=-1):
  c=cycle(action=action,approved=approved); c["cycle_id"]=action+str(move); return DecisionQualityService().evaluate(c,({"timestamp":NOW+timedelta(hours=1),"price":100+move},),horizon_seconds=3600,evaluated_at=NOW+timedelta(hours=1))
 def card(self,price): return TradeReportCardService().build(trade(price,0 if price==100 else 1),cycle(),cycle())
 def test_empty_and_no_closed_trades(self):
  result=self.s.build("hourly",NOW,NOW+timedelta(hours=1),starting_equity=10000,ending_equity=10000); self.assertEqual(0,result.completed_trades); self.assertIsNone(result.win_rate)
 def test_mixed_correct_aggregation_and_risk(self):
  result=self.s.build("daily",NOW,NOW+timedelta(days=1),starting_equity=10000,ending_equity=10001,cards=(self.card(110),self.card(90),self.card(100)),decisions=(self.decision("BUY",True,5),self.decision()),fills=3)
  self.assertEqual((1,1,1),(result.winners,result.losers,result.break_even)); self.assertEqual(1,result.risk_rejections); self.assertEqual(3,result.paper_fills)
 def test_utc_boundary_and_persistence(self):
  with self.assertRaises(ValueError): self.s.build("daily",NOW,NOW+timedelta(hours=23),starting_equity=1,ending_equity=1)
  summary=self.s.build("weekly",NOW,NOW+timedelta(days=7),starting_equity=1,ending_equity=1)
  with tempfile.TemporaryDirectory() as tmp:
   repo=ValidationRepository(Path(tmp)/"v.sqlite3"); repo.initialize(); repo.save_session_summary(summary); self.assertEqual(summary,repo.session_summaries()[0])
if __name__=="__main__":unittest.main()
