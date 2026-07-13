from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json, tempfile, unittest
from database.validation_repository import ValidationRepository
from services.trade_report_cards import TradeReportCardService
NOW=datetime(2026,7,13,12,tzinfo=timezone.utc)
def cycle(action="LONG",confidence=80,approved=True,when=NOW,price=100):
 return {"timestamp":when.isoformat(),"snapshot":{"symbol":"BTC/USD","price":price,"market_trend":"Bull trend","source":"Binance.US"},"recommendation":{"action":action,"confidence":confidence},"risk_assessment":{"approved":approved,"reason":"Approved PAPER size $25."},"specialist_reports":[{"agent_name":"Trend Specialist","recommendation":"LONG","confidence":80}],"evidence_summary":{"contributions":[{"source":"Trend Specialist","direction":"LONG","included":True,"reason":"Trend confirmed."}],"excluded_evidence":[],"conflicting_evidence":[]}}
def trade(exit_price=110,fees=1): return {"trade_id":"PT-1","symbol":"BTC/USD","quantity":"1","entry_price":"100","exit_price":str(exit_price),"fees":str(fees),"closed_at":(NOW+timedelta(hours=2)).isoformat()}
class ReportCardTests(unittest.TestCase):
 def setUp(self): self.service=TradeReportCardService()
 def test_winning_losing_and_break_even(self):
  self.assertGreater(self.service.build(trade(110),cycle(),cycle(when=NOW+timedelta(hours=2))).net_pnl,0)
  self.assertLess(self.service.build(trade(90),cycle(),cycle(when=NOW+timedelta(hours=2))).net_pnl,0)
  self.assertEqual(0,self.service.build(trade(100,0),cycle("WAIT"),cycle(when=NOW+timedelta(hours=2))).net_pnl)
 def test_fees_slippage_utc_and_no_profitability_claim(self):
  card=self.service.build(trade(110,1),cycle(),cycle(when=NOW+timedelta(hours=2)),slippage=2)
  self.assertEqual(7,card.net_pnl); self.assertTrue(card.entry_timestamp.endswith("+00:00")); self.assertIn("do not prove profitability",card.limitation)
 def test_missing_entry_evidence_or_risk_rejected(self):
  bad=cycle(); bad["evidence_summary"]={}
  with self.assertRaises(ValueError): self.service.build(trade(),bad,cycle())
  with self.assertRaises(ValueError): self.service.build(trade(),cycle(approved=False),cycle())
 def test_stable_serialization_persistence_and_duplicate(self):
  card=self.service.build(trade(),cycle(),cycle(when=NOW+timedelta(hours=2)))
  self.assertEqual(json.loads(self.service.stable_json(card)),asdict(card))
  with tempfile.TemporaryDirectory() as tmp:
   repo=ValidationRepository(Path(tmp)/"v.sqlite3"); repo.initialize(); repo.save_report_card(card); self.assertEqual(card,repo.report_cards()[0])
   with self.assertRaises(ValueError): repo.save_report_card(card)
if __name__=="__main__":unittest.main()
