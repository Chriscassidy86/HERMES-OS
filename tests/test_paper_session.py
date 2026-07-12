from datetime import datetime,timezone
from pathlib import Path
import tempfile,unittest
from agents.base.base_specialist import BaseSpecialist
from core.decision_cycle import DecisionCycle
from database.journal import SQLiteAuditJournal
from data_providers.market_data import FixtureMarketDataProvider,SnapshotBuilder
from paper_trading.portfolio import PaperPortfolio
from services.paper_session import PaperTradingSession,ScheduledPaperSession
NOW=datetime(2026,7,11,12,tzinfo=timezone.utc)
def data(trend="Bullish"):
    directional=trend=="Bullish"
    return {"symbol":"BTC/USD","price":102 if directional else 100,"volume_24h":1500 if directional else 1000,"market_trend":trend,"volatility":2 if directional else 4,"fear_greed_index":55,"timestamp":NOW,"previous_price":100,"average_volume":1000,"short_moving_average":101 if directional else 100,"long_moving_average":99 if directional else 100}
class BrokenSpecialist(BaseSpecialist):
    def __init__(self): super().__init__("Broken")
    def analyze(self,snapshot): raise RuntimeError("broken")
class PaperSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.journal=SQLiteAuditJournal(Path(self.tmp.name)/"session.sqlite3"); self.journal.initialize()
    def tearDown(self): self.tmp.cleanup()
    def session(self,record=None,journal=None,cycle=None):
        provider=FixtureMarketDataProvider({"BTC/USD":record or data()},SnapshotBuilder(lambda:NOW))
        return PaperTradingSession(provider,PaperPortfolio(clock=lambda:NOW),journal or self.journal,lambda:NOW,cycle)
    def test_complete_successful_paper_cycle(self):
        result=self.session().run_cycle("BTC/USD"); self.assertEqual("PAPER_FILLED",result.status); self.assertIsNotNone(result.fill)
    def test_no_trade_cycle(self):
        result=self.session(data("Sideways")).run_cycle("BTC/USD"); self.assertEqual("NO_TRADE",result.status); self.assertIsNone(result.order)
    def test_risk_rejected_cycle(self):
        result=self.session(data("Sideways")).run_cycle("BTC/USD"); self.assertFalse(result.cycle.risk_assessment.approved); self.assertEqual("NO_TRADE",result.status)
    def test_provider_failure(self):
        session=self.session(); result=session.run_cycle("ETH/USD"); self.assertEqual("PROVIDER_FAILURE",result.status)
    def test_specialist_failure_isolated(self):
        cycle=DecisionCycle([BrokenSpecialist()],clock=lambda:NOW); result=self.session(cycle=cycle).run_cycle("BTC/USD")
        self.assertEqual("NO_TRADE",result.status); self.assertEqual("REJECTED_INVALID_EVIDENCE",result.cycle.final_status)
    def test_persistence_failure(self):
        class BrokenJournal:
            def save_cycle(self,result): raise OSError("disk unavailable")
        result=self.session(journal=BrokenJournal()).run_cycle("BTC/USD"); self.assertEqual("PERSISTENCE_FAILURE",result.status)
    def test_duplicate_cycle_suppresses_execution(self):
        session=self.session(); self.assertEqual("PAPER_FILLED",session.run_cycle("BTC/USD").status)
        self.assertEqual("DUPLICATE_CYCLE",session.run_cycle("BTC/USD").status); self.assertEqual(1,len(session.portfolio.fills))
    def test_restart_and_state_reload(self):
        session=self.session(); session.run_cycle("BTC/USD")
        restored=PaperPortfolio(clock=lambda:NOW); self.assertTrue(self.journal.restore_portfolio(restored)); self.assertEqual(session.portfolio.account(),restored.account())
    def test_scheduled_run_has_failure_isolation(self):
        results=ScheduledPaperSession(self.session()).run_once(("BTC/USD","ETH/USD")); self.assertEqual(("PAPER_FILLED","PROVIDER_FAILURE"),tuple(r.status for r in results))
if __name__=="__main__": unittest.main()
