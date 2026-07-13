from datetime import datetime,timedelta,timezone
from pathlib import Path
import json,tempfile,unittest
from services.wall_clock_soak import WallClockSoakService
NOW=datetime(2026,7,13,12,tzinfo=timezone.utc)
class Clock:
 def __init__(self): self.now=NOW
 def __call__(self): return self.now
class WallClockSoakTests(unittest.TestCase):
 def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.clock=Clock(); self.path=Path(self.tmp.name)/"state.json"; self.s=WallClockSoakService(self.path,clock=self.clock,rss_provider=lambda:None)
 def tearDown(self): self.tmp.cleanup()
 def test_creation_elapsed_and_paper_only(self):
  state=self.s.start("24h"); self.assertEqual("PAPER ONLY",state.mode); self.clock.now+=timedelta(hours=2); self.assertEqual(7200,self.s.status().current_duration_seconds)
 def test_repeated_start_restart_recovery_and_rss_fallback(self):
  self.s.start("72h");
  with self.assertRaises(ValueError): self.s.start("24h")
  state=self.s.recover(); self.assertEqual(1,state.restart_count); self.assertIsNone(state.process_rss_bytes)
 def test_record_safe_stop_and_export(self):
  self.s.start("7d"); self.s.record(cycles=4,failovers=1,errors=2); state=self.s.stop(); self.assertEqual("STOPPED",state.completion_status)
  output=Path(self.tmp.name)/"report.json"; text=self.s.export(output); self.assertTrue(output.exists()); self.assertEqual("PAPER ONLY",json.loads(text)["state"]["mode"])
 def test_invalid_target_and_no_live_capability(self):
  with self.assertRaises(ValueError): self.s.start("live")
  self.assertFalse(hasattr(self.s,"place_order"))
if __name__=="__main__":unittest.main()
