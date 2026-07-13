from datetime import datetime,timedelta,timezone
from pathlib import Path
import tempfile,unittest
from core.decision_cycle import DecisionCycle
from database.journal import SQLiteAuditJournal
from database.validation_repository import ValidationRepository
from reports.market_snapshot import MarketSnapshot
from services.paper_validation_coordinator import PaperValidationCoordinator
NOW=datetime(2026,7,13,12,tzinfo=timezone.utc)
class Result:
 def __init__(self,cycle): self.cycle=cycle
class CoordinatorTests(unittest.TestCase):
 def test_persisted_cycles_generate_later_horizon_quality_and_summaries(self):
  with tempfile.TemporaryDirectory() as tmp:
   journal=SQLiteAuditJournal(Path(tmp)/"v.sqlite3"); journal.initialize(); repo=ValidationRepository(journal.path); repo.initialize()
   def make(when,price): return DecisionCycle(clock=lambda:when).run(MarketSnapshot("BTC/USD",price,1000,"Bull trend",2,55,price-1,900,price,price-2,"4H",when,"Binance.US",when))
   first=make(NOW,100); later=make(NOW+timedelta(hours=1),105); journal.save_cycle(first); journal.save_cycle(later)
   PaperValidationCoordinator(journal,repo,lambda:NOW+timedelta(hours=2)).observe(Result(later))
   self.assertEqual(1,len(repo.decision_quality())); self.assertEqual(3,len(repo.session_summaries()))
 def test_validation_failure_cannot_stop_paper_observer(self):
  class Broken:
   def recent_cycles(self,_): raise OSError("unavailable")
  coordinator=PaperValidationCoordinator(Broken(),object(),lambda:NOW); coordinator.observe(Result(object())); self.assertTrue(coordinator.errors)
if __name__=="__main__":unittest.main()
