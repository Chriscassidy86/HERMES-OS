from datetime import datetime,timezone
from dataclasses import replace
import json,unittest
from services.specialist_scoreboard import SpecialistScoreboardService
from tests.test_trade_report_cards import cycle,trade
from services.trade_report_cards import TradeReportCardService
NOW=datetime(2026,7,13,12,tzinfo=timezone.utc)
class ScoreboardTests(unittest.TestCase):
 def card(self,price=110,direction="LONG",included=True):
  entry=cycle(); entry["specialist_reports"][0]["recommendation"]=direction; entry["evidence_summary"]["contributions"][0].update(direction=direction,included=included)
  card=TradeReportCardService().build(trade(price),entry,cycle())
  return card if included else replace(card,entry_specialists=(),correct_specialists=(),incorrect_specialists=())
 def score(self,cards): return SpecialistScoreboardService().build(cards,as_of=NOW).scores[0]
 def test_all_correct_all_incorrect_and_mixed(self):
  self.assertEqual(1,self.score((self.card(110),)).correct_calls); self.assertEqual(1,self.score((self.card(90),)).incorrect_calls)
  self.assertEqual(.5,self.score((self.card(110),self.card(90))).accuracy)
 def test_excluded_neutral_and_insufficient_samples(self):
  self.assertEqual(1,self.score((self.card(included=False),)).excluded_calls)
  self.assertEqual(1,self.score((self.card(direction="WAIT"),)).neutral_calls); self.assertIn("INSUFFICIENT",self.score(()).sample_size_warning)
 def test_groups_calibration_and_stable_json(self):
  board=SpecialistScoreboardService().build((self.card(),),as_of=NOW); score=board.scores[0]
  self.assertEqual("BTC/USD",score.by_symbol[0][0]); self.assertEqual("Bull trend",score.by_regime[0][0]); self.assertIsNotNone(score.calibration_score)
  self.assertEqual(json.dumps(board,default=lambda x:x.__dict__,sort_keys=True),json.dumps(board,default=lambda x:x.__dict__,sort_keys=True))
 def test_no_configuration_mutation(self): self.assertFalse(SpecialistScoreboardService().build((),as_of=NOW).configuration_mutated)
if __name__=="__main__":unittest.main()
