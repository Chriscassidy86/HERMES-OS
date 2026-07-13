from datetime import datetime,timezone
import unittest
from core.health import GracefulShutdown
from paper_trading.portfolio import PaperPortfolio
from services.paper_operations import PaperOperationConfig,PaperOperationsService
from services.paper_session import PaperSessionResult
from services.reliability import LongDurationReliabilityHarness
NOW=datetime(2026,7,13,tzinfo=timezone.utc)
class Session:
 def __init__(self): self.portfolio=PaperPortfolio(clock=lambda:NOW)
 def run_cycle(self,symbol,timeframe="4H"): return PaperSessionResult("NO_TRADE",symbol,None)
class Journal:
 def validate_schema(self): pass
 def restore_portfolio(self,_): return True
class ReliabilityTests(unittest.TestCase):
 def test_accelerated_24_hour_run_is_bounded(self):
  operations=PaperOperationsService(Session(),Journal(),GracefulShutdown(),clock=lambda:NOW,wait=lambda _:False)
  report=LongDurationReliabilityHarness(operations).simulate(PaperOperationConfig(("BTC/USD",),interval_seconds=3600,recent_cycle_limit=4))
  self.assertEqual(24,report.simulated_batches); self.assertTrue(report.bounded_memory); self.assertTrue(report.paper_only)
 def test_invalid_duration_fails_closed(self):
  operations=PaperOperationsService(Session(),Journal(),GracefulShutdown(),clock=lambda:NOW)
  with self.assertRaises(ValueError): LongDurationReliabilityHarness(operations).simulate(PaperOperationConfig(("BTC/USD",),interval_seconds=0))
if __name__=="__main__": unittest.main()
