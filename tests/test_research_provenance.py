from dataclasses import replace
from contextlib import closing
from datetime import datetime,timedelta,timezone
from pathlib import Path
import json,sqlite3,tempfile,unittest

from core.research.provenance import DatasetCatalog,stable_checksum,stable_json
from database.journal import SQLiteAuditJournal
from database.research_repository import (DuplicateResearchRunError,ResearchRepository,
 ResearchSchemaVersionError)
from models.research_provenance import (CalibrationObservation,ResearchConfiguration,
 ResearchMetricSet,ResearchRunManifest)
from reports.local_dashboard import ReadOnlyDashboardApplication
from services.ceo_dashboard import CEODashboardService
from services.command_center import CommandCenterService
from services.research_reproducibility import (CalibrationMonitor,ResearchComparisonService,
 ResearchRunOrchestrator,ReproducibilityExporter,WalkForwardEvaluator)

NOW=datetime(2026,7,13,12,tzinfo=timezone.utc)
def rows(count=8,offset=0): return tuple({"id":f"r{i}","timestamp":NOW+timedelta(minutes=i),"close":100+offset+i,"confidence":0.8,"prediction":"LONG"} for i in range(count))

class ResearchProvenanceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.path=Path(self.tmp.name)/"research.sqlite3"; self.repo=ResearchRepository(self.path); self.repo.initialize()
 def tearDown(self): self.tmp.cleanup()
 def catalog(self,dataset_id="btc-5m",symbol="BTC/USD",timeframe="5m",values=None,label="FIXTURE"):
  values=values or rows(); return DatasetCatalog(self.repo).catalog(dataset_id=dataset_id,source="test fixture",symbol=symbol,timeframe=timeframe,start_time=values[0]["timestamp"],end_time=values[-1]["timestamp"],rows=values,trust_score=1.0,reliability_notes=("Artificial",),ingested_at=NOW,label=label)
 def research_run(self,run_id="RUN-1",datasets=None,configs=None):
  datasets=datasets or {"btc-5m":rows()}; configs=configs or (ResearchConfiguration("baseline","base",0.0),)
  return ResearchRunOrchestrator(self.repo,clock=lambda:NOW).run(run_id=run_id,code_commit="abc",dataset_rows=datasets,configurations=configs,reproducibility_seed=7,strategy_versions=(("strategy","1"),),specialist_versions=(("trend","1"),))

 def test_dataset_checksum_stability_and_tamper_detection(self):
  first=self.catalog(); second=DatasetCatalog().catalog(dataset_id="btc-5m",source="test fixture",symbol="BTC/USD",timeframe="5m",start_time=NOW,end_time=NOW+timedelta(minutes=7),rows=rows(),trust_score=1.0,reliability_notes=("Artificial",),ingested_at=NOW,label="FIXTURE")
  self.assertEqual(first.checksum,second.checksum); self.assertTrue(DatasetCatalog.verify(first,rows()))
  with self.assertRaises(ValueError): DatasetCatalog.verify(first,rows(offset=1))

 def test_schema_migration_and_version_rejection(self):
  legacy=Path(self.tmp.name)/"legacy.sqlite3"
  with closing(sqlite3.connect(legacy)) as db: db.execute("CREATE TABLE research_schema_metadata(version INTEGER NOT NULL)"); db.execute("INSERT INTO research_schema_metadata VALUES(0)"); db.commit()
  migrated=ResearchRepository(legacy); migrated.initialize(); migrated.validate_schema()
  invalid=Path(self.tmp.name)/"invalid.sqlite3"
  with closing(sqlite3.connect(invalid)) as db: db.execute("CREATE TABLE research_schema_metadata(version INTEGER NOT NULL)"); db.execute("INSERT INTO research_schema_metadata VALUES(99)"); db.commit()
  with self.assertRaises(ResearchSchemaVersionError): ResearchRepository(invalid).initialize()

 def test_idempotent_artifacts_reload_all_versioned_types(self):
  artifact_types=("DECISION_EXPLANATION","MARKET_REGIME","MULTI_TIMEFRAME","CEO_DASHBOARD","LEARNING_EXPLANATION","EXECUTIVE_BRIEFING","EXPERIMENT_RESULT")
  for index,kind in enumerate(artifact_types):
   identifier=f"A-{index}"; value={"kind":kind,"mode":"PAPER"}
   self.assertTrue(self.repo.save_artifact(identifier,kind,value,NOW)); self.assertFalse(self.repo.save_artifact(identifier,kind,value,NOW)); self.assertEqual(value,self.repo.load_artifact(identifier)["payload"])

 def test_manifest_determinism_duplicate_run_and_reload(self):
  self.catalog(); result=self.research_run(); payload=stable_json(result.manifest)
  self.assertEqual(payload,stable_json(result.manifest)); self.assertEqual(result.manifest.run_id,self.repo.load_run("RUN-1")["run_id"])
  with self.assertRaises(DuplicateResearchRunError): self.research_run()

 def test_missing_dataset_rejected(self):
  with self.assertRaises(ValueError): self.research_run(datasets={"missing":rows()})

 def test_multi_symbol_and_multi_timeframe_run_is_deterministic(self):
  eth=rows(offset=50); self.catalog(); self.catalog("eth-4h","ETH/USD","4h",eth,"REPLAY")
  data={"btc-5m":rows(),"eth-4h":eth}; first=self.research_run("RUN-A",data); second=self.research_run("RUN-B",data)
  self.assertEqual(("BTC/USD","ETH/USD"),first.manifest.symbols); self.assertEqual(("4h","5m"),first.manifest.timeframes)
  self.assertEqual(first.metrics,second.metrics); self.assertEqual(first.dataset_checksums,second.dataset_checksums)

 def test_walk_forward_split_no_lookahead_and_insufficient_history(self):
  split=WalkForwardEvaluator().split(rows(),split_id="WF",training_size=4,validation_size=2,test_size=2,artificial_fixture=True)
  self.assertEqual(("r0","r1","r2","r3"),split.training_ids); self.assertEqual(("r6","r7"),split.test_ids); self.assertTrue(split.no_lookahead_enforced)
  with self.assertRaises(ValueError): WalkForwardEvaluator().split(rows(7),split_id="WF",training_size=4,validation_size=2,test_size=2,artificial_fixture=True)
  reversed_rows=tuple(reversed(rows()))
  with self.assertRaises(ValueError): WalkForwardEvaluator().split(reversed_rows,split_id="WF",training_size=4,validation_size=2,test_size=2,artificial_fixture=True)

 def test_baseline_candidate_and_run_comparison(self):
  self.catalog(); result=self.research_run(configs=(ResearchConfiguration("baseline","base",0),ResearchConfiguration("candidate","candidate",0.02)))
  comparison=ResearchComparisonService().compare(result.metrics[0],result.metrics[1],baseline_manifest=result.manifest,candidate_manifest=result.manifest)
  self.assertEqual("baseline",comparison.baseline_label); self.assertTrue(comparison.reproducibility_confirmed); self.assertIsInstance(comparison.total_return_delta,float)

 def test_run_dataset_and_configuration_comparisons(self):
  first_record=self.catalog(); first=self.research_run("RUN-A")
  other_rows=rows(offset=5); second_record=self.catalog("btc-other","BTC/USD","5m",other_rows); second=self.research_run("RUN-B",{"btc-other":other_rows},(ResearchConfiguration("candidate","candidate",0.02),))
  service=ResearchComparisonService()
  self.assertFalse(service.compare_runs(first,second).identical)
  self.assertIn("Checksum differs.",service.compare_datasets(first_record,second_record).differences)
  self.assertIn("Signal threshold differs.",service.compare_configurations(ResearchConfiguration("base","base",0),ResearchConfiguration("candidate","candidate",0.02)).differences)

 def test_stable_export_and_checksum_verification(self):
  self.catalog(); manifest=self.research_run().manifest; first=ReproducibilityExporter().export(manifest,(("python","3.11"),)); second=ReproducibilityExporter().export(manifest,(("python","3.11"),))
  self.assertEqual(first,second); self.assertTrue(ReproducibilityExporter.verify(first)); self.assertIn("--run-id RUN-1",first.rerun_command)
  with self.assertRaises(ValueError): ReproducibilityExporter.verify(replace(first,checksum="0"*64))

 def test_calibration_minimum_gate_overconfidence_and_no_mutation(self):
  observations=tuple(CalibrationObservation(str(i),0.9,False,NOW+timedelta(minutes=i)) for i in range(10))
  with self.assertRaises(ValueError): CalibrationMonitor().report(observations[:5],min_samples=10)
  report=CalibrationMonitor().report(observations,min_samples=10)
  self.assertEqual("OVERCONFIDENT",report.status); self.assertFalse(report.proposal.configuration_modified); self.assertTrue(report.proposal.human_approval_required)

 def test_dashboard_delivery_is_read_only(self):
  journal=SQLiteAuditJournal(Path(self.tmp.name)/"dashboard.sqlite3"); journal.initialize(); service=CEODashboardService(CommandCenterService(journal,clock=lambda:NOW)); app=ReadOnlyDashboardApplication(service.build)
  status,_,body=app.handle("GET","/dashboard"); self.assertEqual(200,status); payload=json.loads(body); self.assertEqual("PAPER MODE ONLY",payload["banner"]); self.assertEqual([],payload["actions"])
  for method in ("POST","PUT","DELETE"): self.assertEqual(405,app.handle(method,"/dashboard")[0])
  text=body.decode().lower(); self.assertNotIn("api_key",text); self.assertNotIn("place_order",text)

 def test_repository_import_has_no_write_side_effect(self):
  untouched=Path(self.tmp.name)/"untouched.sqlite3"; ResearchRepository(untouched); self.assertFalse(untouched.exists())

 def test_research_persistence_rejects_secret_shaped_fields(self):
  with self.assertRaises(ValueError): self.repo.save_artifact("secret","COMPARISON",{"api_key":"forbidden"},NOW)

if __name__=="__main__": unittest.main()
