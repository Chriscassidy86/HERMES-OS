from datetime import datetime,timezone
from pathlib import Path
import json,tempfile,unittest
from database.journal import SQLiteAuditJournal
from reports.local_dashboard import ReadOnlyDashboardApplication
from services.command_center import CommandCenterService
from services.web_dashboard import WebDashboardService
NOW=datetime(2026,7,13,12,tzinfo=timezone.utc)
class WebDashboardTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); journal=SQLiteAuditJournal(Path(self.tmp.name)/"db.sqlite3"); journal.initialize(); self.service=WebDashboardService(CommandCenterService(journal,clock=lambda:NOW),"V4.1"); self.app=ReadOnlyDashboardApplication(self.service.build)
 def tearDown(self): self.tmp.cleanup()
 def test_localhost_default(self):
  server=self.app.serve(port=0); self.assertEqual("127.0.0.1",server.server_address[0]); server.server_close()
  with self.assertRaises(ValueError): self.app.serve("0.0.0.0",0)
 def test_get_html_and_stable_json(self):
  self.assertIn(b"PAPER MODE ONLY",self.app.handle("GET","/")[2]); first=self.app.handle("GET","/api/dashboard")[2]; self.assertEqual(first,self.app.handle("GET","/api/dashboard")[2]); self.assertEqual("PAPER",json.loads(first)["mode"])
 def test_empty_healthy_and_failure_states(self):
  payload=json.loads(self.app.handle("GET","/api/dashboard")[2]); self.assertEqual("HEALTHY",payload["system_health"]); self.assertIsNone(payload["latest_decision"])
 def test_mutations_rejected(self):
  for method in ("POST","PUT","PATCH","DELETE"): self.assertEqual(405,self.app.handle(method,"/api/dashboard")[0])
 def test_no_controls_or_secrets(self):
  text=self.app.handle("GET","/")[2].decode().lower(); self.assertNotIn("api-key",text); self.assertNotIn("withdraw",text); self.assertNotIn("place order",text); self.assertNotIn("live mode",text)
 def test_business_logic_outside_renderer(self): self.assertFalse(hasattr(self.app.web_renderer,"command_center")); self.assertEqual((),self.service.build().actions)
 def test_live_dashboard_auto_refresh_is_read_only(self):
  status,_,body=self.app.handle("GET","/"); self.assertEqual(200,status); self.assertIn(b'http-equiv="refresh"',body)
  for method in ("POST","PUT","PATCH","DELETE"): self.assertEqual(405,self.app.handle(method,"/")[0])
if __name__=="__main__":unittest.main()
