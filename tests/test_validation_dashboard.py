from datetime import timedelta
from pathlib import Path
import json,tempfile,unittest
from database.validation_repository import ValidationRepository
from reports.local_dashboard import ReadOnlyDashboardApplication
from services.validation_dashboard import ValidationDashboardService
from services.trade_report_cards import TradeReportCardService
from services.decision_quality import DecisionQualityService
from tests.test_trade_report_cards import NOW,cycle,trade
class View: refresh_seconds=5
class ValidationDashboardTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.repo=ValidationRepository(Path(self.tmp.name)/"v.sqlite3"); self.repo.initialize(); self.service=ValidationDashboardService(self.repo,lambda:NOW)
  self.app=ReadOnlyDashboardApplication(lambda:View(),validation_provider=self.service.build)
 def tearDown(self): self.tmp.cleanup()
 def populate(self):
  self.repo.save_report_card(TradeReportCardService().build(trade(),cycle(),cycle()))
  c=cycle(); c["cycle_id"]="C-1"; self.repo.save_decision_quality(DecisionQualityService().evaluate(c,({"timestamp":NOW+timedelta(hours=1),"price":105},),horizon_seconds=3600,evaluated_at=NOW+timedelta(hours=1)))
 def test_empty_and_stable_endpoints(self):
  for path in ("/api/validation","/api/specialists","/api/report-cards","/api/decisions","/api/session-summary","/api/performance"): self.assertEqual(200,self.app.handle("GET",path)[0])
  self.assertEqual(self.app.handle("GET","/api/validation")[2],self.app.handle("GET","/api/validation")[2])
 def test_filter_behavior_invalid_filter_and_order(self):
  self.populate(); yes=json.loads(self.app.handle("GET","/api/report-cards?symbol=BTC%2FUSD")[2]); no=json.loads(self.app.handle("GET","/api/report-cards?symbol=ETH%2FUSD")[2])
  self.assertEqual(1,len(yes["report_cards"])); self.assertEqual(0,len(no["report_cards"])); self.assertEqual(400,self.app.handle("GET","/api/validation?unknown=x")[0])
 def test_get_only_and_no_mutation(self):
  for method in ("POST","PUT","PATCH","DELETE"): self.assertEqual(405,self.app.handle(method,"/api/report-cards")[0])
  self.assertEqual((),self.service.build()["actions"])
 def test_polished_validation_markup_no_raw_dump(self):
  from reports.web_dashboard import WebDashboardRenderer
  text=WebDashboardRenderer().html(View()); self.assertIn("Specialist scoreboard",text); self.assertIn("Searchable decision history",text); self.assertNotIn("<pre>",text); self.assertNotIn("place order",text.lower())
if __name__=="__main__":unittest.main()
