"""Create strict deterministic training, validation, and test windows."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent; sys.path.append(str(ROOT))
from services.research_reproducibility import WalkForwardEvaluator
NOW=datetime(2026,7,13,12,tzinfo=timezone.utc); rows=tuple({"id":str(i),"timestamp":NOW+timedelta(days=i)} for i in range(9))
split=WalkForwardEvaluator().split(rows,split_id="WF-1",training_size=5,validation_size=2,test_size=2,artificial_fixture=True)
print(split); print("No look-ahead:",split.no_lookahead_enforced)

