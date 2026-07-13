"""Catalog and verify one deterministic artificial fixture dataset."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from core.research.provenance import DatasetCatalog
NOW=datetime(2026,7,13,12,tzinfo=timezone.utc)
rows=tuple({"id":str(i),"timestamp":NOW+timedelta(minutes=i),"close":100+i} for i in range(5))
record=DatasetCatalog().catalog(dataset_id="fixture-btc-5m",source="bundled fixture",symbol="BTC/USD",timeframe="5m",start_time=NOW,end_time=NOW+timedelta(minutes=4),rows=rows,trust_score=1.0,reliability_notes=("Artificial deterministic fixture.",),ingested_at=NOW,label="FIXTURE")
print(record.dataset_id,record.checksum); print("Verified:",DatasetCatalog.verify(record,rows)); print("PAPER RESEARCH ONLY")

