from datetime import datetime,timezone
from pathlib import Path
import unittest
from data_providers.public_adapters import PublicCandle
from services.public_snapshot_provider import PublicSnapshotProvider
from reports.operator_reports import OperatorReports
ROOT=Path(__file__).resolve().parent.parent;NOW=datetime(2026,7,13,tzinfo=timezone.utc)
class Redundancy:
 def get_candle(self,symbol,timeframe): return type("Value",(),{"candle":PublicCandle("Binance.US","BTC/USD",timeframe,NOW,100,10),"source":"Binance.US"})()
class LaunchTests(unittest.TestCase):
 def test_public_snapshot_is_attributed_observation(self):
  provider=PublicSnapshotProvider(Redundancy(),clock=lambda:NOW); snapshot=provider.get_snapshot("BTCUSDT"); self.assertEqual("Binance.US",snapshot.source); self.assertEqual(NOW,snapshot.source_timestamp); self.assertTrue(provider.health.healthy)
 def test_compose_publishes_dashboard_on_host_loopback_only(self):
  text=(ROOT/"docker-compose.yml").read_text(); self.assertIn('127.0.0.1:8765:8765',text); self.assertIn('BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT',text)
 def test_operator_entrypoint_has_required_commands(self):
  text=(ROOT/"scripts"/"hermes.ps1").read_text();
  for command in ("start","stop","restart","status","logs","health","dashboard","backup","verify-backup","portfolio","trades","provider","alerts"): self.assertIn(command,text)
 def test_default_service_is_continuous_not_health_only(self):
  text=(ROOT/"scripts"/"paper_service.py").read_text(); self.assertIn("MultiSymbolScheduler",text); self.assertIn("RedundantPublicProvider",text); self.assertNotIn("StartupChecks",text)
 def test_persisted_provider_attribution_is_reported(self):
  class Journal:
   def recent_cycles(self,_): return [{"snapshot":{"source":"Binance.US"}}]
  self.assertEqual("Binance.US",OperatorReports(Journal()).provider_health()["status"])
 def test_backup_verification_command_checks_both_files(self):
  self.assertIn("verify-backup $db $backup",(ROOT/"scripts"/"hermes.ps1").read_text())
if __name__=="__main__":unittest.main()
