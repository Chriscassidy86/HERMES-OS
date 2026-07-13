import json,unittest
from models.soak_validation import SoakThresholds
from services.soak_validation import AcceleratedSoakHarness
SYMBOLS=("BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT")
class SoakTests(unittest.TestCase):
 def setUp(self): self.harness=AcceleratedSoakHarness()
 def test_24_72_and_week_runs(self):
  self.assertEqual(96,self.harness.run(hours=24,symbols=SYMBOLS).total_cycles); self.assertEqual(288,self.harness.run(hours=72,symbols=SYMBOLS).total_cycles); self.assertEqual(672,self.harness.run(hours=168,symbols=SYMBOLS).total_cycles)
 def test_outage_restart_recovery_and_circuit_metrics(self):
  def inject(index,_): return {"status":"failed","failover":True,"restart":True,"recovery":True,"circuit":True,"alerts":True} if index==0 else {}
  report=self.harness.run(hours=24,symbols=SYMBOLS,injector=inject); self.assertEqual((1,1,1,1),(report.provider_failovers,report.restart_events,report.recovery_events,report.circuit_breaker_events))
 def test_bounded_memory_logs_and_ceiling(self):
  report=self.harness.run(hours=168,symbols=SYMBOLS,thresholds=SoakThresholds(maximum_history=10),log_size=50,database_size=100); self.assertEqual(1280,report.memory_bytes); self.assertEqual((100,50),(report.database_size,report.log_size))
 def test_deterministic_rerun_and_export(self):
  a=self.harness.run(hours=24,symbols=SYMBOLS); b=self.harness.run(hours=24,symbols=SYMBOLS); self.assertEqual(a,b); self.assertEqual(a.checksum,json.loads(self.harness.export(a))["checksum"])
 def test_interruption_is_safe(self):
  report=self.harness.run(hours=24,symbols=SYMBOLS,interrupt_after=3); self.assertTrue(report.interrupted); self.assertEqual(3,report.total_cycles)
 def test_explicit_threshold_failure(self):
  report=self.harness.run(hours=24,symbols=SYMBOLS,thresholds=SoakThresholds(maximum_queue_depth=0),injector=lambda *_:{"queue_depth":1}); self.assertFalse(report.passed); self.assertTrue(report.failures)
 def test_counts_orders_dashboard_learning(self):
  report=self.harness.run(hours=24,symbols=SYMBOLS,injector=lambda *_:{"orders":True,"fills":True,"trades":True,"dashboard":True,"learning":True,"risk":True,"stale":True}); self.assertEqual(report.total_cycles,report.fills); self.assertTrue(report.accelerated_not_wall_clock); self.assertTrue(report.paper_only)
 def test_malformed_injected_metrics_rejected(self):
  with self.assertRaises(ValueError): self.harness.run(hours=24,symbols=SYMBOLS,injector=lambda *_:{"duration_ms":float("nan")})
if __name__=="__main__": unittest.main()
