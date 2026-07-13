from datetime import datetime, timezone
from pathlib import Path
import tempfile, unittest
from core.decision_cycle import DecisionCycle
from data_providers.market_data import FixtureMarketDataProvider, ProviderHealth, SnapshotBuilder
from database.journal import SQLiteAuditJournal
from paper_trading.portfolio import PaperPortfolio
from reports.market_snapshot import MarketSnapshot
from services.command_center import CommandCenterService

NOW=datetime(2026,7,12,12,tzinfo=timezone.utc)
def cycle(trend="Bullish"):
    directional=trend=="Bullish"
    snap=MarketSnapshot("BTC/USD",102 if directional else 100,1500 if directional else 1000,trend,2,55,100,1000,101 if directional else 100,99 if directional else 100,"4H",NOW)
    return DecisionCycle(clock=lambda:NOW).run(snap)
class Provider:
    def __init__(self,healthy=True): self.health=ProviderHealth(healthy,"HEALTHY" if healthy else "UNAVAILABLE",1)

class CommandCenterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.journal=SQLiteAuditJournal(Path(self.tmp.name)/"db.sqlite3"); self.journal.initialize()
    def tearDown(self): self.tmp.cleanup()
    def view(self,provider=None,**values): return CommandCenterService(self.journal,provider,lambda:NOW).build(**values)
    def populate(self,close=False,rejected=False):
        result=cycle("Sideways" if rejected else "Bullish"); self.journal.save_cycle(result); book=PaperPortfolio(clock=lambda:NOW)
        if result.paper_execution_eligible:
            order=book.propose(result,102); book.execute_market(order.order_id)
            if close: book.close_position("BTC/USD",105)
        self.journal.save_portfolio(book,result.cycle_id); return book
    def test_empty_state(self): self.assertEqual("NO_CYCLE",self.view().paper_execution_status)
    def test_normal_paper_portfolio(self): self.populate(); self.assertGreater(self.view().equity,0)
    def test_open_position(self): self.populate(); self.assertEqual(1,len(self.view().open_positions))
    def test_completed_trade(self): self.populate(True); self.assertEqual(1,len(self.view().closed_trades))
    def test_rejected_cycle(self): self.populate(rejected=True); self.assertTrue(self.view().rejected_decisions)
    def test_unhealthy_provider(self): self.assertEqual("UNHEALTHY",self.view(Provider(False)).system_health)
    def test_unhealthy_database(self):
        class Broken: 
            def validate_schema(self): raise OSError("broken")
        self.assertEqual("UNHEALTHY",CommandCenterService(Broken()).build().system_health)
    def test_learning_recommendation_display(self):
        view=self.view(learning_recommendations=({"rule":"weight"},)); self.assertTrue(view.notices)
    def test_actions_cannot_place_orders(self): self.assertEqual((),self.view().actions)

if __name__=="__main__": unittest.main()
