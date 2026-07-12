from datetime import datetime,timezone
from pathlib import Path
import tempfile,unittest
from core.decision_cycle import DecisionCycle
from database.journal import SQLiteAuditJournal
from models.performance import SpecialistPrediction,TradeOutcome
from paper_trading.portfolio import PaperPortfolio
from reports.market_snapshot import MarketSnapshot
from reports.operator_reports import OperatorReports
NOW=datetime(2026,7,11,12,tzinfo=timezone.utc)
def cycle(directional=True):
    snap=MarketSnapshot("BTC/USD",102 if directional else 100,1500 if directional else 1000,"Bullish" if directional else "Sideways",2 if directional else 4,55,100,1000,101 if directional else 100,99 if directional else 100,"4H",NOW)
    return DecisionCycle(clock=lambda:NOW).run(snap)
class OperatorReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.journal=SQLiteAuditJournal(Path(self.tmp.name)/"reports.sqlite3"); self.journal.initialize(); self.reports=OperatorReports(self.journal)
    def tearDown(self): self.tmp.cleanup()
    def persist_open_position(self):
        result=cycle(); self.journal.save_cycle(result); book=PaperPortfolio(clock=lambda:NOW); order=book.propose(result,102); book.execute_market(order.order_id); self.journal.save_portfolio(book,result.cycle_id); return book
    def test_report_generation(self):
        result=cycle(); self.journal.save_cycle(result); text=self.reports.to_json(self.reports.latest_decision_cycle()); self.assertIn(result.cycle_id,text); self.assertIn("PAPER",self.reports.to_json(self.reports.system_status()))
    def test_empty_database_state(self):
        self.assertIsNone(self.reports.latest_decision_cycle()); self.assertEqual([],self.reports.open_positions()); self.assertFalse(self.reports.risk_state()["approved"])
    def test_open_position_report(self):
        self.persist_open_position(); self.assertEqual("BTC/USD",self.reports.open_positions()[0]["symbol"])
    def test_completed_trade_report(self):
        book=self.persist_open_position(); book.close_position("BTC/USD",110); self.journal.save_portfolio(book,cycle().cycle_id)
        self.assertEqual(1,len(self.reports.completed_trades())); self.assertNotEqual("0",self.reports.daily_pnl()["realized_pnl"])
    def test_rejected_cycle_report(self):
        result=cycle(False); self.journal.save_cycle(result); self.assertTrue(self.reports.rejected_decisions()); self.assertFalse(self.reports.risk_state()["approved"])
    def test_specialist_scorecard_report(self):
        prediction=SpecialistPrediction("Trend Specialist","LONG",80); outcome=TradeOutcome("1","BTC/USD","LONG",100,110,1,1,NOW,NOW,(prediction,))
        self.assertEqual("Trend Specialist",self.reports.agent_scorecards([outcome])[0]["source"])
if __name__=="__main__": unittest.main()
