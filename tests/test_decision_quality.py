from datetime import datetime,timedelta,timezone
from pathlib import Path
import tempfile,unittest
from database.validation_repository import ValidationRepository
from services.decision_quality import DecisionQualityService
from tests.test_trade_report_cards import cycle,NOW
def value(action="LONG",approved=True):
 c=cycle(action=action,approved=approved); c["cycle_id"]="C-1"; return c
def points(change): return ({"timestamp":NOW+timedelta(hours=1),"price":100+change},)
class DecisionQualityTests(unittest.TestCase):
 def setUp(self): self.s=DecisionQualityService(); self.end=NOW+timedelta(hours=1)
 def test_buy_and_sell_outcomes(self):
  self.assertEqual("GOOD_ENTRY",self.s.evaluate(value("BUY"),points(5),horizon_seconds=3600,evaluated_at=self.end).outcome_classification)
  self.assertEqual("GOOD_ENTRY",self.s.evaluate(value("SELL"),points(-5),horizon_seconds=3600,evaluated_at=self.end).outcome_classification)
 def test_wait_avoids_loss_and_misses_gain(self):
  self.assertTrue(self.s.evaluate(value("WAIT",False),points(-5),horizon_seconds=3600,evaluated_at=self.end).wait_hold_avoided_bad_trade)
  self.assertEqual("MISSED_GAIN",self.s.evaluate(value("WAIT",False),points(5),horizon_seconds=3600,evaluated_at=self.end).outcome_classification)
 def test_risk_rejection_quality(self):
  self.assertEqual("REJECTION_AVOIDED_LOSS",self.s.evaluate(value("BUY",False),points(-5),horizon_seconds=3600,evaluated_at=self.end).outcome_classification)
  self.assertEqual("WOULD_HAVE_GAINED",self.s.evaluate(value("BUY",False),points(5),horizon_seconds=3600,evaluated_at=self.end).rejected_trade_result)
 def test_no_lookahead_horizon_and_stale(self):
  with self.assertRaises(ValueError): self.s.evaluate(value(),({"timestamp":NOW,"price":105},),horizon_seconds=3600,evaluated_at=self.end)
  with self.assertRaises(ValueError): self.s.evaluate(value(),({"timestamp":NOW+timedelta(minutes=10),"price":105},),horizon_seconds=3600,evaluated_at=self.end)
  accepted=self.s.evaluate(value(),({"timestamp":NOW+timedelta(hours=1,seconds=30),"price":105},),horizon_seconds=3600,evaluated_at=NOW+timedelta(hours=1,seconds=30)); self.assertEqual(3600,accepted.evaluation_horizon_seconds)
 def test_stable_persistence(self):
  record=self.s.evaluate(value(),points(5),horizon_seconds=3600,evaluated_at=self.end)
  with tempfile.TemporaryDirectory() as tmp:
   repo=ValidationRepository(Path(tmp)/"v.sqlite3"); repo.initialize(); repo.save_decision_quality(record); self.assertEqual(record,repo.decision_quality()[0])
if __name__=="__main__":unittest.main()
