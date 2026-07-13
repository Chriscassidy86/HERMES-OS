from copy import deepcopy
from datetime import datetime,timezone
import unittest
from agents.learning.learning_engine import LearningEngine
from agents.performance.performance_engine import PerformanceEngine
from core.evidence.config import DEFAULT_EVIDENCE_CONFIG
from models.performance import SpecialistPrediction,TradeOutcome
NOW=datetime(2026,7,11,tzinfo=timezone.utc)
def outcome(identifier,entry,exit,confidence=80,source="Trend Specialist"):
    direction="LONG"; prediction=SpecialistPrediction(source,direction,confidence)
    return TradeOutcome(identifier,"BTC/USD",direction,entry,exit,1.0,1.0,NOW,NOW,(prediction,))
class PerformanceLearningTests(unittest.TestCase):
    def setUp(self): self.performance=PerformanceEngine(); self.learning=LearningEngine()
    def test_winning_trade_scoring(self):
        score=self.performance.strategy_scorecard([outcome("1",100,110)]); self.assertEqual(1,score.wins); self.assertEqual(9,score.total_pnl)
    def test_losing_trade_scoring(self):
        score=self.performance.strategy_scorecard([outcome("1",100,90)]); self.assertEqual(1,score.losses); self.assertEqual(-11,score.total_pnl)
    def test_specialist_accuracy(self):
        cards=self.performance.specialist_scorecards([outcome("1",100,110),outcome("2",100,90)])
        self.assertEqual(0.5,cards[0].accuracy)
    def test_calibration_calculation(self):
        card=self.performance.specialist_scorecards([outcome("1",100,110,80)])[0]; self.assertEqual(0.04,card.brier_score)
    def test_insufficient_sample_rejection(self):
        card=self.performance.specialist_scorecards([outcome("1",100,110)])[0]
        with self.assertRaises(ValueError): self.learning.recommend_weight_change(card,1.0)
    def test_recommendation_generation_requires_approval(self):
        card=self.performance.specialist_scorecards([outcome(str(i),100,110) for i in range(5)])[0]
        patch=self.learning.recommend_weight_change(card,1.0); self.assertEqual(1.1,patch.proposed_value); self.assertTrue(patch.human_approval_required); self.assertTrue(patch.risks)
    def test_production_configuration_not_mutated(self):
        before=deepcopy(DEFAULT_EVIDENCE_CONFIG.specialist_weights)
        card=self.performance.specialist_scorecards([outcome(str(i),100,110) for i in range(5)])[0]; self.learning.recommend_weight_change(card,1.0)
        self.assertEqual(before,DEFAULT_EVIDENCE_CONFIG.specialist_weights)
    def test_reports_and_drawdown(self):
        values=[outcome("1",100,110),outcome("2",100,80)]
        self.assertGreater(self.performance.drawdown_report(values).maximum_drawdown,0); self.assertEqual(2,self.performance.daily_report("2026-07-11",values).strategy.sample_size); self.assertEqual(2,self.performance.weekly_report("2026-W28",values).strategy.sample_size)
if __name__=="__main__": unittest.main()
