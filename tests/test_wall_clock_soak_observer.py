from datetime import datetime,timezone
from pathlib import Path
import tempfile,unittest
from services.wall_clock_soak import WallClockSoakService
from services.wall_clock_soak_observer import WallClockSoakObserver
from core.settings import RuntimeSettings
from scripts.paper_service import build_soak_observer
NOW=datetime(2026,7,13,12,tzinfo=timezone.utc)
class Result:
 def __init__(self,status): self.status=status
class ObserverTests(unittest.TestCase):
 def test_dormant_until_operator_start_then_tracks_runtime(self):
  with tempfile.TemporaryDirectory() as tmp:
   service=WallClockSoakService(Path(tmp)/"state.json",clock=lambda:NOW,rss_provider=lambda:None); observer=WallClockSoakObserver(service); observer.observe(Result("PROVIDER_FAILURE")); self.assertIsNone(service.load())
   service.start("24h"); observer.observe(Result("PROVIDER_FAILURE")); state=service.load(); self.assertEqual(1,state.cycle_count); self.assertEqual(1,state.provider_failover_count); self.assertEqual(1,state.error_count)
 def test_restart_recovery_is_counted(self):
  with tempfile.TemporaryDirectory() as tmp:
   service=WallClockSoakService(Path(tmp)/"state.json",clock=lambda:NOW,rss_provider=lambda:None); service.start("72h"); WallClockSoakObserver(service); self.assertEqual(1,service.load().restart_count)
 def test_paper_service_uses_runtime_log_directory(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp); settings=RuntimeSettings("PAPER",root/"data.sqlite3",root/"logs",1000,1)
   observer=build_soak_observer(settings,lambda:NOW,root/"soak.json")
   self.assertEqual(settings.log_directory,observer.service.log_path)
if __name__=="__main__":unittest.main()
