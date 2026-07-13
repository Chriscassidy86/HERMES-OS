from datetime import datetime,timedelta,timezone
import json,unittest
from reports.local_dashboard import ReadOnlyDashboardApplication
from services.visualization import VisualizationService
NOW=datetime(2026,7,13,12,tzinfo=timezone.utc)
class VisualizationTests(unittest.TestCase):
 def test_empty_and_one_point_states(self):
  service=VisualizationService(); self.assertEqual("EMPTY",service.build("price",(),value_key="price",source_label="PAPER").state); self.assertEqual("INSUFFICIENT_DATA",service.build("price",({"timestamp":NOW,"price":1},),value_key="price",source_label="FIXTURE").state)
 def test_malformed_and_naive_time_rejected(self):
  for row in ({"timestamp":NOW,"price":float("nan")},{"timestamp":NOW.replace(tzinfo=None),"price":1}):
   with self.assertRaises(ValueError): VisualizationService().build("price",(row,),value_key="price",source_label="PAPER")
 def test_utc_stable_order_and_source(self):
  rows=({"timestamp":NOW+timedelta(hours=1),"price":2},{"timestamp":NOW,"price":1}); result=VisualizationService().build("price",rows,value_key="price",source_label="REPLAY"); self.assertEqual(1,result.points[0].value); self.assertEqual("REPLAY",result.source_label); self.assertIn("+00:00",result.points[0].timestamp)
 def test_disclaimer_and_metadata(self):
  result=VisualizationService().build("regime",({"timestamp":NOW,"value":1,"regime":"BULL"},),value_key="value",source_label="PUBLIC_OBSERVATION"); self.assertIn("does not guarantee",result.disclaimer); self.assertIn(("regime","BULL"),result.points[0].metadata)
 def test_pagination_and_downsampling(self):
  rows=tuple({"timestamp":NOW+timedelta(minutes=i),"price":i} for i in range(1000)); result=VisualizationService().build("price",rows,value_key="price",source_label="PAPER",offset=100,limit=500,max_points=50); self.assertLessEqual(len(result.points),50); self.assertEqual(1000,result.total_points); self.assertEqual(100,result.offset)
 def test_chart_endpoint_get_only(self):
  chart=VisualizationService().build("price",({"timestamp":NOW,"price":1},),value_key="price",source_label="FIXTURE"); app=ReadOnlyDashboardApplication(lambda:None,lambda:(chart,)); payload=json.loads(app.handle("GET","/api/charts")[2]); self.assertEqual("FIXTURE",payload["charts"][0]["source_label"]); self.assertEqual(405,app.handle("POST","/api/charts")[0])
if __name__=="__main__":unittest.main()
