"""Run a deterministic offline research job over a cataloged fixture."""
import argparse
from datetime import datetime,timedelta,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
ROOT=Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from core.research.provenance import DatasetCatalog
from database.research_repository import ResearchRepository
from models.research_provenance import ResearchConfiguration
from services.research_reproducibility import ResearchRunOrchestrator
parser=argparse.ArgumentParser(); parser.add_argument("--run-id",default="RUN-DEMO"); args=parser.parse_args()
NOW=datetime(2026,7,13,12,tzinfo=timezone.utc); rows=tuple({"id":str(i),"timestamp":NOW+timedelta(minutes=i),"close":100+i,"confidence":0.7,"prediction":"LONG"} for i in range(5))
with TemporaryDirectory() as directory:
 repo=ResearchRepository(Path(directory)/"research.sqlite3"); repo.initialize(); catalog=DatasetCatalog(repo)
 catalog.catalog(dataset_id="fixture-btc-5m",source="fixture",symbol="BTC/USD",timeframe="5m",start_time=NOW,end_time=NOW+timedelta(minutes=4),rows=rows,trust_score=1.0,reliability_notes=("Artificial fixture",),ingested_at=NOW,label="FIXTURE")
 result=ResearchRunOrchestrator(repo,clock=lambda:NOW).run(run_id=args.run_id,code_commit="example",dataset_rows={"fixture-btc-5m":rows},configurations=(ResearchConfiguration("baseline","base",0.0),ResearchConfiguration("candidate","candidate",0.005)),reproducibility_seed=7,strategy_versions=(("fixture","1"),),specialist_versions=(("trend","1"),))
 print(result.manifest.run_id,result.metrics); print("Mode:",result.manifest.mode)

