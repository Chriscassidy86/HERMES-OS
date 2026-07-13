from datetime import datetime,timezone
import unittest
from models.performance import TradeOutcome
from services.continuous_learning import ContinuousLearningLoop
NOW=datetime(2026,7,13,tzinfo=timezone.utc)
def outcome(identifier): return TradeOutcome(identifier,"BTC/USD","LONG",100,101,1,0,NOW,NOW,())
class ContinuousLearningTests(unittest.TestCase):
 def test_completed_trade_updates_recommendation_only_report(self):
  report=ContinuousLearningLoop().record(outcome("1")); self.assertEqual(1,report.sample_size); self.assertFalse(report.configuration_modified); self.assertTrue(report.human_review_required)
 def test_duplicate_and_bounded_history(self):
  loop=ContinuousLearningLoop(history_limit=1); loop.record(outcome("1")); report=loop.record(outcome("2")); self.assertEqual(1,report.sample_size)
  with self.assertRaises(ValueError): loop.record(outcome("2"))
if __name__=="__main__": unittest.main()
