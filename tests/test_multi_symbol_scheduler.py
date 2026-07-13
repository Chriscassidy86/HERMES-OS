from datetime import datetime,timezone
import unittest
from core.health import GracefulShutdown
from models.multi_symbol import SymbolSchedule
from paper_trading.portfolio import PaperPortfolio
from services.multi_symbol_scheduler import MultiSymbolScheduler
from services.paper_session import PaperSessionResult
NOW=datetime(2026,7,13,tzinfo=timezone.utc)
class Session:
 def __init__(self,fail=()): self.portfolio=PaperPortfolio(clock=lambda:NOW); self.fail=set(fail)
 def run_cycle(self,symbol,timeframe="4H"): return PaperSessionResult("PROVIDER_FAILURE" if symbol in self.fail else "NO_TRADE",symbol,None)
class Journal:
 def validate_schema(self): pass
 def restore_portfolio(self,_): return True
def schedules(): return tuple(SymbolSchedule(item) for item in ("BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT"))
class SchedulerTests(unittest.TestCase):
 def execute(self,values=None,**kwargs): return MultiSymbolScheduler(Session(kwargs.pop("fail",())),Journal(),GracefulShutdown(),clock=lambda:NOW,wait=lambda _:False,history_limit=kwargs.pop("history_limit",100)).run(values or schedules(),interval_seconds=0,**kwargs)
 def test_four_symbols_and_deterministic_fair_order(self):
  result=self.execute(maximum_rounds=2); self.assertEqual(("BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BTCUSDT"),result.ordering)
 def test_symbol_and_provider_failure_isolation(self):
  result=self.execute(maximum_rounds=1,fail=("ETHUSDT",)); states={x.symbol:x for x in result.states}; self.assertEqual(1,states["ETHUSDT"].failed_cycles); self.assertEqual(1,states["BTCUSDT"].successful_cycles)
 def test_disabled_symbol(self):
  result=self.execute((SymbolSchedule("BTCUSDT"),SymbolSchedule("ETHUSDT",False)),maximum_rounds=1); self.assertEqual(("BTCUSDT",),result.ordering); self.assertEqual(1,result.states[1].skipped_cycles)
 def test_restart_recovery_and_bounded_history(self):
  result=self.execute(maximum_rounds=3,history_limit=2); self.assertTrue(result.recovered); self.assertTrue(all(len(x.history)==2 for x in result.states))
 def test_graceful_shutdown(self):
  shutdown=GracefulShutdown(); shutdown.request(); result=MultiSymbolScheduler(Session(),Journal(),shutdown,clock=lambda:NOW).run(schedules()); self.assertEqual(0,result.cycles)
 def test_duplicate_symbols_rejected(self):
  with self.assertRaises(ValueError): self.execute((SymbolSchedule("BTC"),SymbolSchedule("BTC")),maximum_rounds=1)
if __name__=="__main__": unittest.main()
